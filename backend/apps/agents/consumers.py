"""
WebSocket consumer for real-time edge agent communication.

Protocol (JSON text messages):
- Agent → Server:
  - {"type": "heartbeat", "status": "online", ...}
  - {"type": "sync_files", "files": [...], "stats": {...}}
  - {"type": "command_result", "command_id": "...", "status": "completed", "result": {...}}

- Server → Agent:
  - {"type": "heartbeat_ack", "pending_commands": [...], "config": {...}}
  - {"type": "sync_ack", "accepted": N, "rejected": N, ...}
  - {"type": "command", "command_id": "...", "command_type": "...", "payload": {...}}
  - {"type": "config_update", "config": {...}}
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for edge agent communication."""

    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close(code=4401)
            return

        # Find the agent for this user (agents are 1:1 with users via ApiKey)
        agent = await self._get_agent_for_user(user)
        if agent is None:
            logger.warning("No agent found for user %s", user.pk)
            await self.close(code=4404)
            return

        self.agent_id = agent.agent_id
        self.agent_pk = agent.pk
        self.group_name = f"agent_{self.agent_id}"

        # Join agent group for server-push (commands, config updates)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Update agent status to online
        await self._update_agent_status(self.agent_pk, "online")

        logger.info("Agent %s connected via WebSocket", self.agent_id)

    async def disconnect(self, code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if hasattr(self, "agent_pk"):
            await self._update_agent_status(self.agent_pk, "offline")
            logger.info("Agent %s disconnected (code=%s)", self.agent_id, code)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is None:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))
            return

        msg_type = data.get("type")

        if msg_type == "heartbeat":
            await self._handle_heartbeat(data)
        elif msg_type == "sync_files":
            await self._handle_sync_files(data)
        elif msg_type == "command_result":
            await self._handle_command_result(data)
        else:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"Unknown message type: {msg_type}",
            }))

    # ----------------------------------------------------------------
    # Agent → Server message handlers
    # ----------------------------------------------------------------

    async def _handle_heartbeat(self, data: dict[str, Any]) -> None:
        """Process heartbeat: update agent status, return pending commands + config."""
        agent = await self._get_agent(self.agent_pk)
        if agent is None:
            return

        # Update agent fields
        fields = ["status", "last_seen"]
        agent.status = data.get("status", "online")
        agent.last_seen = timezone.now()

        for field in ("platform", "hostname", "ip_address", "agent_version",
                       "files_count", "total_size_bytes"):
            if field in data:
                setattr(agent, field, data[field])
                fields.append(field)

        await database_sync_to_async(agent.save)(update_fields=fields)

        # Sync monitored folders
        folders_monitored = data.get("folders_monitored", [])
        if folders_monitored:
            await self._sync_folders(agent, folders_monitored)

        # Get and mark pending commands
        pending = await self._get_pending_commands(self.agent_pk)
        pending_data = await self._serialize_commands(pending)

        for cmd in pending:
            cmd.status = "delivered"
            await database_sync_to_async(cmd.save)(update_fields=["status"])

        # Send ack with pending commands + config
        await self.send(text_data=json.dumps({
            "type": "heartbeat_ack",
            "status": "ok",
            "sync_interval_minutes": agent.sync_interval_minutes,
            "pending_commands": pending_data,
            "config": {
                "max_file_size_mb": agent.max_file_size_mb,
            },
        }))

        # Notify dashboard consumers
        await self._notify_dashboard(agent)

    async def _handle_sync_files(self, data: dict[str, Any]) -> None:
        """Process file sync — same logic as the REST sync endpoint."""
        files = data.get("files", [])
        if not files:
            await self.send(text_data=json.dumps({
                "type": "sync_ack", "accepted": 0, "rejected": 0,
            }))
            return

        result = await self._process_sync(self.agent_pk, files)

        await self.send(text_data=json.dumps({
            "type": "sync_ack",
            **result,
        }))

        if result.get("accepted", 0) > 0:
            agent = await self._get_agent(self.agent_pk)
            if agent:
                await self._notify_dashboard(agent)

                # Notify processing consumers (frontend dashboard)
                try:
                    await self.channel_layer.group_send(
                        f"processing_{agent.user_id}",
                        {
                            "type": "processing.update",
                            "data": {
                                "type": "files_synced",
                                "agent_id": agent.agent_id,
                                "accepted": result.get("accepted", 0),
                                "rejected": result.get("rejected", 0),
                                "document_ids": result.get("document_ids", []),
                            },
                        },
                    )
                except Exception:
                    logger.debug("Failed to notify processing group for agent %s", self.agent_id)

    async def _handle_command_result(self, data: dict[str, Any]) -> None:
        """Agent reports the result of executing a command."""
        cmd_id = data.get("command_id")
        if not cmd_id:
            return

        await self._update_command_result(
            cmd_id,
            data.get("status", "completed"),
            data.get("result"),
        )

    # ----------------------------------------------------------------
    # Server → Agent handlers (called via group_send)
    # ----------------------------------------------------------------

    async def push_command(self, event: dict[str, Any]) -> None:
        """Push a command to the connected agent."""
        await self.send(text_data=json.dumps({
            "type": "command",
            "command_id": event["command_id"],
            "command_type": event["command_type"],
            "payload": event.get("payload", {}),
        }))

    async def agent_config_update(self, event: dict[str, Any]) -> None:
        """Push config update to the connected agent."""
        await self.send(text_data=json.dumps({
            "type": "config_update",
            "config": event.get("config", {}),
        }))

    # ----------------------------------------------------------------
    # Database helpers (all wrapped in database_sync_to_async)
    # ----------------------------------------------------------------

    @database_sync_to_async
    def _get_agent_for_user(self, user):
        from apps.agents.models import Agent
        try:
            return Agent.objects.get(user=user)
        except Agent.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_agent(self, agent_pk):
        from apps.agents.models import Agent
        try:
            return Agent.objects.get(pk=agent_pk)
        except Agent.DoesNotExist:
            return None

    @database_sync_to_async
    def _update_agent_status(self, agent_pk, status):
        from apps.agents.models import Agent
        try:
            agent = Agent.objects.get(pk=agent_pk)
            agent.status = status
            agent.last_seen = timezone.now()
            agent.save(update_fields=["status", "last_seen"])
        except Agent.DoesNotExist:
            pass

    @database_sync_to_async
    def _get_pending_commands(self, agent_pk):
        from apps.agents.models import AgentCommand
        return list(
            AgentCommand.objects.filter(
                agent_id=agent_pk, status="pending"
            ).order_by("created_at")[:20]
        )

    @database_sync_to_async
    def _serialize_commands(self, commands):
        from apps.agents.serializers import AgentCommandSerializer
        return AgentCommandSerializer(commands, many=True).data

    @database_sync_to_async
    def _sync_folders(self, agent, folders_monitored):
        from apps.agents.models import AgentFolder
        existing = {f.local_path: f for f in agent.folders.all()}
        for path in folders_monitored:
            if path not in existing:
                AgentFolder.objects.create(agent=agent, local_path=path)

    @database_sync_to_async
    def _update_command_result(self, cmd_id, cmd_status, result):
        from apps.agents.models import AgentCommand
        try:
            cmd = AgentCommand.objects.get(id=cmd_id, agent_id=self.agent_pk)
            cmd.status = cmd_status
            cmd.result = result
            cmd.executed_at = timezone.now()
            cmd.save(update_fields=["status", "result", "executed_at"])
        except AgentCommand.DoesNotExist:
            logger.warning("Command %s not found for agent %s", cmd_id, self.agent_id)

    @database_sync_to_async
    def _process_sync(self, agent_pk, files_data):
        """Process file sync — mirrors the REST sync endpoint logic."""
        from apps.agents.models import AgentCommand
        from apps.agents.serializers import AgentSyncSerializer

        # Validate via serializer
        serializer = AgentSyncSerializer(data={"files": files_data, "stats": {}})
        if not serializer.is_valid():
            return {
                "accepted": 0,
                "rejected": len(files_data),
                "errors": [{"error": str(serializer.errors)}],
            }

        validated = serializer.validated_data
        files = validated["files"]

        accepted = 0
        rejected = 0
        errors = []
        document_ids = []

        from apps.files.models import FileRecord
        from apps.documents.models import Document

        with transaction.atomic():
            for file_data in files:
                try:
                    local_path = file_data["local_path"]
                    file_hash = file_data["file_hash"]

                    fr, _created = FileRecord.objects.update_or_create(
                        content_hash=file_hash,
                        defaults={
                            "path": local_path,
                            "mime_type": file_data.get("mime_type", ""),
                            "size_bytes": file_data.get("file_size", 0),
                            "status": "completed",
                            "source": FileRecord.Source.AGENT,
                            "agent_id": agent_pk,
                            "tags": file_data.get("metadata", {}).get("tags", []),
                            "metadata": {
                                **file_data.get("metadata", {}),
                                "agent_id": str(agent_pk),
                                "agent_version": file_data.get("agent_version", ""),
                                "processing_version": file_data.get("processing_version", ""),
                                "parser_version": file_data.get("parser_version", ""),
                                "ocr_engine": file_data.get("ocr_engine", ""),
                                "ocr_used": file_data.get("ocr_used", False),
                                "extracted_text": file_data.get("extracted_text", ""),
                                "markdown": file_data.get("markdown", ""),
                                "content_blocks": file_data.get("content_blocks", []),
                                "tables": file_data.get("tables", []),
                                "images": file_data.get("images", []),
                            },
                        },
                    )

                    doc = Document.objects.create(
                        file_id=fr.id,
                        doc_type=Document.DocType.UNKNOWN,
                        processing_status=Document.Status.PENDING,
                        title=Path(local_path).stem,
                        language=file_data.get("language", "unknown"),
                        word_count=file_data.get("word_count", 0),
                        char_count=file_data.get("char_count", 0),
                        page_count=file_data.get("page_count", 0),
                        extracted_text=file_data.get("extracted_text", "")[:10000],
                        summary=file_data.get("summary", ""),
                        markdown=file_data.get("markdown", ""),
                        content_blocks=file_data.get("content_blocks", []),
                        tables=file_data.get("tables", []),
                        images=file_data.get("images", []),
                        ocr_used=file_data.get("ocr_used", False),
                        agent_version=file_data.get("agent_version", ""),
                        processing_version=file_data.get("processing_version", ""),
                        parser_version=file_data.get("parser_version", ""),
                        ocr_engine=file_data.get("ocr_engine", ""),
                        tags=file_data.get("metadata", {}).get("tags", []),
                    )

                    entities = file_data.get("entities", [])
                    if entities:
                        from apps.documents.models import ExtractedEntity
                        ExtractedEntity.objects.bulk_create([
                            ExtractedEntity(
                                document=doc,
                                entity_type=e.get("entity_type", "unknown"),
                                name=e.get("name", ""),
                                context=e.get("context", ""),
                                confidence=e.get("confidence"),
                                source="agent",
                            )
                            for e in entities if e.get("name")
                        ])

                    document_ids.append(str(doc.id))
                    accepted += 1
                except Exception as e:
                    rejected += 1
                    errors.append({"file": file_data.get("local_path", "?"), "error": str(e)})
                    logger.warning("WS sync error for %s: %s", file_data.get("local_path"), e)

            # Update agent sync timestamp
            from apps.agents.models import Agent
            try:
                agent = Agent.objects.get(pk=agent_pk)
                agent.last_sync_at = timezone.now()
                agent.save(update_fields=["last_sync_at"])
            except Agent.DoesNotExist:
                pass

        # Get pending commands
        pending = list(
            AgentCommand.objects.filter(
                agent_id=agent_pk, status="pending"
            ).order_by("created_at")[:20]
        )
        for cmd in pending:
            cmd.status = "delivered"
            cmd.save(update_fields=["status"])

        from apps.agents.serializers import AgentCommandSerializer
        return {
            "accepted": accepted,
            "rejected": rejected,
            "errors": errors,
            "document_ids": document_ids,
            "pending_commands": AgentCommandSerializer(pending, many=True).data,
        }

    async def _notify_dashboard(self, agent) -> None:
        """Send agent update to the user's dashboard WebSocket group."""
        try:
            await self.channel_layer.group_send(
                f"dashboard_{agent.user_id}",
                {
                    "type": "dashboard.update",
                    "data": {
                        "type": "agent_status_changed",
                        "agent_id": agent.agent_id,
                        "status": agent.status,
                        "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
                        "files_count": agent.files_count,
                        "total_size_bytes": agent.total_size_bytes,
                    },
                },
            )
        except Exception:
            logger.debug("Failed to notify dashboard for agent %s", agent.agent_id)
