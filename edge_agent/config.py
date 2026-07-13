"""Edge Agent configuration — loaded from YAML + env overrides."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


@dataclass
class ServerConfig:
    url: str = "http://localhost:8000"
    web_url: str = ""
    api_key: str = ""
    jwt_token: str = ""


@dataclass
class OCRConfig:
    engine: str = "paddleocr"
    lang: str = "en"
    use_gpu: bool = False
    timeout_seconds: int = 120
    auto_detect: bool = True


@dataclass
class ParserConfig:
    backend: str = "pipeline"
    effort: str = "medium"
    language: str = "en"
    formula_enable: bool = True
    table_enable: bool = True
    auto_detect: bool = True


@dataclass
class WatcherConfig:
    enabled: bool = True
    debounce_seconds: float = 2.0
    recursive: bool = True


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096


@dataclass
class EdgeAgentConfig:
    agent_name: str = "edge-agent"
    agent_id: str = ""
    agent_version: str = ""
    data_dir: str = str(Path.home() / ".edge-agent")
    db_path: str = str(Path.home() / ".edge-agent" / "agent.db")
    log_level: str = "INFO"
    server: ServerConfig = field(default_factory=ServerConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    parser: ParserConfig = field(default_factory=ParserConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    watcher: WatcherConfig = field(default_factory=WatcherConfig)
    plugin_dir: str = ""
    folders: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.agent_version:
            from edge_agent import __version__
            object.__setattr__(self, "agent_version", __version__)


def load_config(config_path: str | Path | None = None) -> EdgeAgentConfig:
    """Load config from YAML file, with env var overrides."""
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    raw: dict = {}

    if path.exists():
        try:
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
        except Exception:
            logger.warning("Failed to load config from %s", path)

    cfg = EdgeAgentConfig()

    # Server
    server_raw = raw.get("server", {})
    cfg.server = ServerConfig(
        url=server_raw.get("url", os.getenv("EDGE_SERVER_URL", "http://localhost:8000")),
        web_url=server_raw.get("web_url", os.getenv("EDGE_WEB_URL", "")),
        api_key=server_raw.get("api_key", os.getenv("EDGE_API_KEY", "")),
        jwt_token=server_raw.get("jwt_token", os.getenv("EDGE_JWT_TOKEN", "")),
    )

    # Agent
    cfg.agent_name = raw.get("agent_name", os.getenv("EDGE_AGENT_NAME", "edge-agent"))
    cfg.agent_id = raw.get("agent_id", os.getenv("EDGE_AGENT_ID", ""))
    raw_data_dir = raw.get("data_dir", os.getenv("EDGE_DATA_DIR", ""))
    cfg.data_dir = str(Path(raw_data_dir).expanduser()) if raw_data_dir else str(Path.home() / ".edge-agent")
    raw_db_path = raw.get("db_path", os.getenv("EDGE_DB_PATH", ""))
    cfg.db_path = str(Path(raw_db_path).expanduser()) if raw_db_path else str(Path(cfg.data_dir) / "agent.db")
    cfg.log_level = raw.get("log_level", os.getenv("EDGE_LOG_LEVEL", "INFO"))

    # Plugin dir
    raw_plugin_dir = raw.get("plugin_dir", os.getenv("EDGE_PLUGIN_DIR", ""))
    cfg.plugin_dir = str(Path(raw_plugin_dir).expanduser()) if raw_plugin_dir else str(Path(cfg.data_dir) / "plugins")

    # Folders
    cfg.folders = [str(Path(f).expanduser()) for f in raw.get("folders", [])]

    # OCR
    ocr_raw = raw.get("ocr", {})
    cfg.ocr = OCRConfig(
        engine=ocr_raw.get("engine", cfg.ocr.engine),
        lang=ocr_raw.get("lang", cfg.ocr.lang),
        use_gpu=ocr_raw.get("use_gpu", cfg.ocr.use_gpu),
        timeout_seconds=ocr_raw.get("timeout_seconds", cfg.ocr.timeout_seconds),
        auto_detect=ocr_raw.get("auto_detect", cfg.ocr.auto_detect),
    )

    # Parser
    parser_raw = raw.get("parser", {})
    cfg.parser = ParserConfig(
        backend=parser_raw.get("backend", cfg.parser.backend),
        effort=parser_raw.get("effort", cfg.parser.effort),
        language=parser_raw.get("language", cfg.parser.language),
        formula_enable=parser_raw.get("formula_enable", cfg.parser.formula_enable),
        table_enable=parser_raw.get("table_enable", cfg.parser.table_enable),
        auto_detect=parser_raw.get("auto_detect", cfg.parser.auto_detect),
    )

    # Watcher
    watcher_raw = raw.get("watcher", {})
    cfg.watcher = WatcherConfig(
        enabled=watcher_raw.get("enabled", cfg.watcher.enabled),
        debounce_seconds=watcher_raw.get("debounce_seconds", cfg.watcher.debounce_seconds),
        recursive=watcher_raw.get("recursive", cfg.watcher.recursive),
    )

    # LLM
    llm_raw = raw.get("llm", {})
    cfg.llm = LLMConfig(
        provider=llm_raw.get("provider", os.getenv("EDGE_LLM_PROVIDER", cfg.llm.provider)),
        model=llm_raw.get("model", os.getenv("EDGE_LLM_MODEL", cfg.llm.model)),
        api_key=llm_raw.get("api_key", os.getenv("EDGE_LLM_API_KEY", cfg.llm.api_key)),
        base_url=llm_raw.get("base_url", os.getenv("EDGE_LLM_BASE_URL", cfg.llm.base_url)),
        temperature=llm_raw.get("temperature", cfg.llm.temperature),
        max_tokens=llm_raw.get("max_tokens", cfg.llm.max_tokens),
    )

    return cfg
