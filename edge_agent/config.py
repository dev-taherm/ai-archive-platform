"""Edge Agent configuration — loads from YAML + env overrides."""

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
    api_key: str = ""
    jwt_token: str = ""


@dataclass
class ScannerConfig:
    ignore_patterns: list[str] = field(default_factory=lambda: [
        ".git", ".svn", ".hg", "__pycache__", "node_modules",
        ".DS_Store", "Thumbs.db", "*.pyc", "*.pyo", "*.swp",
    ])
    max_file_size_mb: int = 100


@dataclass
class OCRConfig:
    lang: str = "en"
    use_gpu: bool = False
    timeout_seconds: int = 120


@dataclass
class ParserConfig:
    backend: str = "pipeline"
    effort: str = "medium"
    language: str = "en"
    formula_enable: bool = True
    table_enable: bool = True


@dataclass
class SyncConfig:
    interval_minutes: int = 30
    push_original_files: bool = False
    batch_size: int = 50
    retry_attempts: int = 3
    retry_delay_seconds: int = 60


@dataclass
class WatcherConfig:
    enabled: bool = True
    recursive: bool = True
    debounce_seconds: float = 2.0


@dataclass
class EdgeAgentConfig:
    agent_name: str = "edge-agent"
    agent_id: str = ""
    data_dir: str = str(Path.home() / ".edge-agent")
    log_level: str = "INFO"
    server: ServerConfig = field(default_factory=ServerConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    parser: ParserConfig = field(default_factory=ParserConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    watcher: WatcherConfig = field(default_factory=WatcherConfig)
    folders: list[str] = field(default_factory=list)

    @property
    def db_path(self) -> str:
        return str(Path(self.data_dir) / "agent.db")

    @property
    def log_file(self) -> str:
        return str(Path(self.data_dir) / "agent.log")


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
        api_key=server_raw.get("api_key", os.getenv("EDGE_API_KEY", "")),
        jwt_token=server_raw.get("jwt_token", os.getenv("EDGE_JWT_TOKEN", "")),
    )

    # Agent
    cfg.agent_name = raw.get("agent_name", os.getenv("EDGE_AGENT_NAME", "edge-agent"))
    cfg.agent_id = raw.get("agent_id", os.getenv("EDGE_AGENT_ID", ""))
    cfg.data_dir = raw.get("data_dir", os.getenv("EDGE_DATA_DIR", str(Path.home() / ".edge-agent")))
    cfg.log_level = raw.get("log_level", os.getenv("EDGE_LOG_LEVEL", "INFO"))

    # Folders
    cfg.folders = raw.get("folders", [])

    # Scanner
    scanner_raw = raw.get("scanner", {})
    cfg.scanner = ScannerConfig(
        ignore_patterns=scanner_raw.get("ignore_patterns", cfg.scanner.ignore_patterns),
        max_file_size_mb=scanner_raw.get("max_file_size_mb", cfg.scanner.max_file_size_mb),
    )

    # OCR
    ocr_raw = raw.get("ocr", {})
    cfg.ocr = OCRConfig(
        lang=ocr_raw.get("lang", cfg.ocr.lang),
        use_gpu=ocr_raw.get("use_gpu", cfg.ocr.use_gpu),
        timeout_seconds=ocr_raw.get("timeout_seconds", cfg.ocr.timeout_seconds),
    )

    # Parser
    parser_raw = raw.get("parser", {})
    cfg.parser = ParserConfig(
        backend=parser_raw.get("backend", cfg.parser.backend),
        effort=parser_raw.get("effort", cfg.parser.effort),
        language=parser_raw.get("language", cfg.parser.language),
        formula_enable=parser_raw.get("formula_enable", cfg.parser.formula_enable),
        table_enable=parser_raw.get("table_enable", cfg.parser.table_enable),
    )

    # Sync
    sync_raw = raw.get("sync", {})
    cfg.sync = SyncConfig(
        interval_minutes=sync_raw.get("interval_minutes", cfg.sync.interval_minutes),
        push_original_files=sync_raw.get("push_original_files", cfg.sync.push_original_files),
        batch_size=sync_raw.get("batch_size", cfg.sync.batch_size),
        retry_attempts=sync_raw.get("retry_attempts", cfg.sync.retry_attempts),
        retry_delay_seconds=sync_raw.get("retry_delay_seconds", cfg.sync.retry_delay_seconds),
    )

    # Watcher
    watcher_raw = raw.get("watcher", {})
    cfg.watcher = WatcherConfig(
        enabled=watcher_raw.get("enabled", cfg.watcher.enabled),
        recursive=watcher_raw.get("recursive", cfg.watcher.recursive),
        debounce_seconds=watcher_raw.get("debounce_seconds", cfg.watcher.debounce_seconds),
    )

    return cfg
