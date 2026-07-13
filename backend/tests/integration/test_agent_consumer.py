"""Tests for apps.agents.consumers — AgentConsumer WebSocket.

Patches SyncToAsync to run sync DB functions in the event loop thread instead
of a thread pool. This eliminates SQLite lock contention with :memory: databases.
DB correctness is covered by test_api_agents.py integration tests.
"""
import functools
import json
from unittest.mock import MagicMock, patch

from channels.testing import WebsocketCommunicator

import pytest

from apps.agents.consumers import AgentConsumer


# ── Helpers ─────────────────────────────────────────────────────────────────


def _run_sync_directly(self, loop, exc_info, task_context, func, *args, **kwargs):
    """Drop-in replacement for DatabaseSyncToAsync.thread_handler that runs
    the sync function directly in the event loop thread instead of dispatching
    to a thread pool. This eliminates SQLite lock contention with :memory: DBs."""
    return func(*args, **kwargs)


@pytest.fixture(autouse=True)
def _no_thread_pool():
    """Patch DatabaseSyncToAsync.thread_handler so all @database_sync_to_async
    calls run synchronously in the event loop thread (no thread pool)."""
    from channels.db import DatabaseSyncToAsync
    with patch.object(DatabaseSyncToAsync, "thread_handler", _run_sync_directly):
        yield


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def setup_user_and_agent(db):
    """Create a user and agent in the DB, return (User, Agent) instances."""
    from apps.accounts.models import User
    from apps.agents.models import Agent

    user = User.objects.create_user(
        email="ws@test.com", username="wsuser", password="pass123"
    )
    agent = Agent.objects.create(
        user=user,
        agent_id="ws-agent-001",
        name="WS Agent",
        status="offline",
    )
    return user, agent


@pytest.fixture
def setup_user_agent_with_command(db):
    """Create a user, agent, and a pending command."""
    from apps.accounts.models import User
    from apps.agents.models import Agent, AgentCommand

    user = User.objects.create_user(
        email="cmd@test.com", username="cmduser", password="pass123"
    )
    agent = Agent.objects.create(
        user=user,
        agent_id="cmd-agent-001",
        name="Cmd Agent",
        status="offline",
    )
    AgentCommand.objects.create(
        agent=agent,
        command_type="restart",
        payload={},
        status="pending",
    )
    return user, agent


def _make_communicator(user):
    """Create a WebsocketCommunicator for the AgentConsumer."""
    communicator = WebsocketCommunicator(
        AgentConsumer.as_asgi(),
        "/ws/agent/",
    )
    communicator.scope["user"] = user
    return communicator


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_authenticated(setup_user_and_agent):
    user, agent = setup_user_and_agent
    communicator = _make_communicator(user)

    connected, _ = await communicator.connect()
    assert connected

    # Agent should be online now
    await agent.refresh_from_db()
    assert agent.status == "online"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_connect_anonymous_rejected():
    user = MagicMock()
    user.is_anonymous = True

    communicator = WebsocketCommunicator(
        AgentConsumer.as_asgi(),
        "/ws/agent/",
    )
    communicator.scope["user"] = user

    connected, close_code = await communicator.connect()
    # Anonymous users should be disconnected
    assert not connected or close_code == 4401


@pytest.mark.asyncio
async def test_heartbeat_updates_agent(setup_user_and_agent):
    user, agent = setup_user_and_agent
    communicator = _make_communicator(user)

    connected, _ = await communicator.connect()
    assert connected

    # Send heartbeat
    await communicator.send_json_to({
        "type": "heartbeat",
        "status": "online",
        "platform": "linux",
        "hostname": "test-host",
        "files_count": 10,
        "folders_monitored": ["/tmp/docs"],
    })

    # Receive ack
    response = await communicator.receive_json_from(timeout=5)
    assert response["type"] == "heartbeat_ack"
    assert response["status"] == "ok"
    assert "pending_commands" in response

    # Agent should be updated
    await agent.refresh_from_db()
    assert agent.status == "online"
    assert agent.files_count == 10
    assert agent.hostname == "test-host"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_heartbeat_returns_pending_commands(setup_user_agent_with_command):
    user, agent = setup_user_agent_with_command
    communicator = _make_communicator(user)

    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({
        "type": "heartbeat",
        "status": "online",
    })

    response = await communicator.receive_json_from(timeout=5)
    assert response["type"] == "heartbeat_ack"
    assert len(response["pending_commands"]) == 1
    assert response["pending_commands"][0]["command_type"] == "restart"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_sync_files_accepted(setup_user_and_agent):
    user, agent = setup_user_and_agent
    communicator = _make_communicator(user)

    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({
        "type": "sync_files",
        "files": [
            {
                "local_path": "/tmp/test.txt",
                "file_hash": "hash123",
                "file_size": 100,
                "mime_type": "text/plain",
                "modified_at": 1000.0,
                "extracted_text": "hello world",
                "markdown": "hello world",
                "language": "en",
                "word_count": 2,
                "char_count": 11,
                "page_count": 1,
            }
        ],
        "stats": {},
    })

    response = await communicator.receive_json_from(timeout=5)
    assert response["type"] == "sync_ack"
    assert response["accepted"] == 1
    assert response["rejected"] == 0
    assert len(response["document_ids"]) == 1

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_sync_files_empty(setup_user_and_agent):
    user, agent = setup_user_and_agent
    communicator = _make_communicator(user)

    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({
        "type": "sync_files",
        "files": [],
        "stats": {},
    })

    response = await communicator.receive_json_from(timeout=5)
    assert response["type"] == "sync_ack"
    assert response["accepted"] == 0
    assert response["rejected"] == 0

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_disconnect_sets_offline(setup_user_and_agent):
    user, agent = setup_user_and_agent
    communicator = _make_communicator(user)

    connected, _ = await communicator.connect()
    assert connected

    # Verify online
    await agent.refresh_from_db()
    assert agent.status == "online"

    await communicator.disconnect()

    # Verify offline
    await agent.refresh_from_db()
    assert agent.status == "offline"
