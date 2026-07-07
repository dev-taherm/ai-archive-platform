"""Shared fixtures for edge agent tests."""
import os
import tempfile
from pathlib import Path

import pytest

from edge_agent.config import EdgeAgentConfig, LLMConfig, SyncConfig, ScannerConfig


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def default_config(tmp_dir):
    cfg = EdgeAgentConfig(
        agent_name="test-agent",
        agent_id="test-agent-id-001",
        data_dir=tmp_dir,
    )
    cfg.server.url = "http://localhost:9999"
    cfg.server.api_key = "test-key"
    cfg.llm.api_key = "test-llm-key"
    cfg.llm.provider = "openai"
    return cfg


@pytest.fixture
def sample_yaml_config(tmp_dir):
    config_path = Path(tmp_dir) / "config.yaml"
    config_path.write_text("""
agent_name: yaml-agent
server:
  url: http://localhost:8000
  api_key: yaml-key
llm:
  provider: openai
  model: gpt-4o
sync:
  interval_minutes: 15
  batch_size: 25
folders:
  - /tmp/docs
""")
    return str(config_path)
