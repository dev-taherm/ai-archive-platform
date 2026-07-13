"""Tests for edge_agent.config — YAML loading, dataclass defaults, env overrides."""
import os
from pathlib import Path

import pytest

from edge_agent.config import (
    EdgeAgentConfig,
    LLMConfig,
    ServerConfig,
    WatcherConfig,
    load_config,
)


class TestEdgeAgentConfigDefaults:
    def test_default_agent_name(self):
        cfg = EdgeAgentConfig()
        assert cfg.agent_name == "edge-agent"

    def test_default_data_dir(self):
        cfg = EdgeAgentConfig()
        assert ".edge-agent" in cfg.data_dir

    def test_db_path_property(self, tmp_dir):
        cfg = EdgeAgentConfig(data_dir=tmp_dir)
        assert cfg.db_path == str(Path(tmp_dir) / "agent.db")

    def test_agent_version_auto_populated(self):
        cfg = EdgeAgentConfig()
        assert cfg.agent_version  # should be set from __version__

    def test_sub_configs_default(self):
        cfg = EdgeAgentConfig()
        assert isinstance(cfg.server, ServerConfig)
        assert isinstance(cfg.llm, LLMConfig)
        assert isinstance(cfg.watcher, WatcherConfig)


class TestLoadConfig:
    def test_load_default_config(self):
        cfg = load_config()
        assert isinstance(cfg, EdgeAgentConfig)

    def test_load_yaml_config(self, sample_yaml_config):
        cfg = load_config(sample_yaml_config)
        assert cfg.agent_name == "yaml-agent"
        assert cfg.server.url == "http://localhost:8000"
        assert cfg.llm.provider == "openai"
        assert cfg.llm.model == "gpt-4o"

    def test_load_missing_file(self, tmp_dir):
        cfg = load_config(str(Path(tmp_dir) / "nonexistent.yaml"))
        assert cfg.agent_name == "edge-agent"  # defaults

    def test_env_override_server_url(self, monkeypatch, sample_yaml_config):
        monkeypatch.setenv("EDGE_SERVER_URL", "http://env-host:3000")
        cfg = load_config(sample_yaml_config)
        assert cfg.server.url == "http://env-host:3000"

    def test_env_override_llm_provider(self, monkeypatch):
        monkeypatch.setenv("EDGE_LLM_PROVIDER", "anthropic")
        cfg = load_config()
        assert cfg.llm.provider == "anthropic"

    def test_env_override_agent_name(self, monkeypatch):
        monkeypatch.setenv("EDGE_AGENT_NAME", "env-agent")
        cfg = load_config()
        assert cfg.agent_name == "env-agent"


class TestAutoDetectConfig:
    def test_ocr_auto_detect_default(self):
        from edge_agent.config import OCRConfig
        cfg = OCRConfig()
        assert cfg.auto_detect is True

    def test_parser_auto_detect_default(self):
        from edge_agent.config import ParserConfig
        cfg = ParserConfig()
        assert cfg.auto_detect is True

    def test_config_load_auto_detect(self, tmp_path):
        from edge_agent.config import load_config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ocr:
  lang: en
  auto_detect: false
parser:
  language: en
  auto_detect: false
""")
        cfg = load_config(str(config_file))
        assert cfg.ocr.auto_detect is False
        assert cfg.parser.auto_detect is False
