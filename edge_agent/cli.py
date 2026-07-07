"""Edge Agent CLI — main entry point.

Commands:
    edge-agent register     Register with the SaaS platform
    edge-agent scan         Scan a folder and process files
    edge-agent watch        Watch folders for changes
    edge-agent sync         Push pending files to the platform
    edge-agent status       Show agent status
    edge-agent run          Full loop: watch + process + sync
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

from edge_agent import __version__
from edge_agent.config import EdgeAgentConfig, load_config, ServerConfig
from edge_agent.core.scanner import FileScanner
from edge_agent.db.local_db import LocalDB
from edge_agent.parsers.router import ParserRouter
from edge_agent.ocr.engine import OCREngine
from edge_agent.sync.manager import SyncManager

logger = logging.getLogger("edge_agent")

PROCESSING_VERSION = "edge-document-pipeline-v2"


def setup_logging(config: EdgeAgentConfig) -> None:
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    log_path = Path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(str(log_path)))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _save_config(config: EdgeAgentConfig, path: Path) -> None:
    """Save config back to YAML."""
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "agent_name": config.agent_name,
        "agent_id": config.agent_id,
        "data_dir": config.data_dir,
        "log_level": config.log_level,
        "server": {
            "url": config.server.url,
            "api_key": config.server.api_key,
            "jwt_token": config.server.jwt_token,
        },
        "folders": config.folders,
        "scanner": {
            "ignore_patterns": config.scanner.ignore_patterns,
            "max_file_size_mb": config.scanner.max_file_size_mb,
        },
        "ocr": {
            "engine": config.ocr.engine,
            "lang": config.ocr.lang,
            "use_gpu": config.ocr.use_gpu,
            "timeout_seconds": config.ocr.timeout_seconds,
        },
        "parser": {
            "backend": config.parser.backend,
            "effort": config.parser.effort,
            "language": config.parser.language,
            "formula_enable": config.parser.formula_enable,
            "table_enable": config.parser.table_enable,
        },
        "sync": {
            "interval_minutes": config.sync.interval_minutes,
            "push_original_files": config.sync.push_original_files,
            "batch_size": config.sync.batch_size,
            "retry_attempts": config.sync.retry_attempts,
            "retry_delay_seconds": config.sync.retry_delay_seconds,
        },
        "watcher": {
            "enabled": config.watcher.enabled,
            "recursive": config.watcher.recursive,
            "debounce_seconds": config.watcher.debounce_seconds,
        },
    }
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _process_file(
    file_info: dict,
    db: LocalDB,
    parser: ParserRouter,
    ocr: OCREngine,
    agent_version: str = "",
    processing_version: str = "",
    parser_version: str = "",
    ocr_engine: str = "",
) -> None:
    """Process a single file: parse, OCR if needed, store pre-processed data in DB.

    Chunking and embedding are SaaS-only responsibilities — the edge agent
    only sends extracted text and structural metadata.
    """
    file_id = db.upsert_file(file_info)
    record = db.get_file(file_id)
    if not record:
        return

    if record["processing_status"] == "completed" and record["extracted_text"]:
        return

    db.update_file(file_id, processing_status="processing")
    try:
        parsed = parser.parse(file_info["path"])
        text = parsed.markdown or ""

        if not text or len(text.strip()) < 50:
            suffix = Path(file_info["path"]).suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp", ".pdf"):
                content = Path(file_info["path"]).read_bytes()
                ocr_text = ocr.extract_text(content, content_type=file_info.get("mime_type", "application/pdf"))
                if ocr_text and len(ocr_text) > len(text):
                    text = ocr_text

        db.update_file(
            file_id,
            extracted_text=text[:10000],
            markdown=text,
            content_blocks=[b.to_dict() if hasattr(b, "to_dict") else vars(b) for b in parsed.content_blocks],
            tables=[t.to_dict() if hasattr(t, "to_dict") else vars(t) for t in parsed.tables],
            images=[i.to_dict() if hasattr(i, "to_dict") else vars(i) for i in parsed.images],
            language=getattr(parsed, "language", "unknown"),
            word_count=parsed.word_count,
            char_count=parsed.char_count,
            page_count=parsed.page_count,
            ocr_used=bool(ocr_text and len(ocr_text) > len(text)),
            agent_version=agent_version,
            processing_version=processing_version,
            parser_version=parser_version,
            ocr_engine=ocr_engine,
            processing_status="completed",
        )
    except Exception as e:
        logger.exception("Failed to process %s", file_info["path"])
        db.update_file(file_id, processing_status="failed", last_error=str(e))


def cmd_register(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Register this agent with the platform.

    Requires a JWT token from the user's login (pass --jwt or use config).
    On success, the server creates an API key for the agent which is saved to config.
    """
    jwt_token = args.jwt or config.server.jwt_token
    if not jwt_token:
        print("ERROR: Pass --jwt <token> or set server.jwt_token in config")
        print("  Get a JWT by logging in: POST /api/v1/auth/login {\"email\": ..., \"password\": ...}")
        sys.exit(1)

    db = LocalDB(config.db_path)
    sync = SyncManager(config, db)
    try:
        result = sync.register(name=args.name or config.agent_name, jwt_token=jwt_token)
        print(json.dumps(result, indent=2))

        agent_id = result.get("agent_id") or result.get("id", "")
        api_key = result.get("api_key", "")

        if agent_id:
            config.agent_id = agent_id
        if api_key:
            config.server.api_key = api_key

        # Save updated config
        config_path = Path(args.config) if args.config else Path.home() / ".edge-agent" / "config.yaml"
        _save_config(config, config_path)

        if api_key:
            print(f"\n  Agent ID:  {agent_id}")
            print(f"  API Key:   {api_key}")
            print(f"\n  Save this API key — it won't be shown again!")
            print(f"  Config saved to: {config_path}")
    finally:
        sync.close()
        db.close()


def cmd_scan(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Scan a folder and process all files."""
    folder = args.folder
    if not folder:
        print("ERROR: Provide a folder path")
        sys.exit(1)

    db = LocalDB(config.db_path)
    scanner = FileScanner(
        ignore_patterns=config.scanner.ignore_patterns,
        max_file_size_mb=config.scanner.max_file_size_mb,
    )
    parser = ParserRouter()
    ocr = OCREngine(lang=config.ocr.lang, use_gpu=config.ocr.use_gpu)

    count = 0
    for file_info in scanner.scan_folder(folder, recursive=args.recursive):
        _process_file(file_info, db, parser, ocr,
                      agent_version=config.agent_version,
                      processing_version=PROCESSING_VERSION,
                      parser_version=config.parser.backend,
                      ocr_engine=config.ocr.engine if hasattr(config.ocr, "engine") else "paddleocr")
        count += 1
        if count % 100 == 0:
            print(f"  Processed {count} files...")

    print(f"Scanned and processed {count} files from {folder}")
    db.close()


def cmd_process(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Process a single file."""
    if not args.file:
        print("ERROR: Provide a file path")
        sys.exit(1)

    db = LocalDB(config.db_path)
    scanner = FileScanner()
    parser = ParserRouter()
    ocr = OCREngine(lang=config.ocr.lang, use_gpu=config.ocr.use_gpu)

    file_info = scanner.scan_single(args.file)
    if not file_info:
        print(f"ERROR: Could not scan {args.file}")
        sys.exit(1)

    _process_file(file_info, db, parser, ocr,
                  agent_version=config.agent_version,
                  processing_version=PROCESSING_VERSION,
                  parser_version=config.parser.backend,
                  ocr_engine=config.ocr.engine)
    record = db.get_file_by_hash(file_info["content_hash"])
    if record:
        print(json.dumps({
            "id": record["id"],
            "path": record["local_path"],
            "status": record["processing_status"],
            "text_length": len(record["extracted_text"]),
        }, indent=2))
    db.close()


def cmd_sync(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Push pending files to the platform."""
    if not config.server.api_key:
        print("ERROR: Set server.api_key in config or pass --api-key to register first")
        sys.exit(1)

    db = LocalDB(config.db_path)
    sync = SyncManager(config, db)
    try:
        result = sync.sync_with_retry()
        print(json.dumps(result, indent=2))
    finally:
        sync.close()
        db.close()


def cmd_watch(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Watch folders for changes and process new/modified files."""
    from edge_agent.watcher.monitor import FolderWatcher

    folders = args.folders or config.folders
    if not folders:
        print("ERROR: No folders to watch. Set folders in config or pass --folders")
        sys.exit(1)

    db = LocalDB(config.db_path)
    scanner = FileScanner(
        ignore_patterns=config.scanner.ignore_patterns,
        max_file_size_mb=config.scanner.max_file_size_mb,
    )
    parser = ParserRouter()
    ocr = OCREngine(lang=config.ocr.lang, use_gpu=config.ocr.use_gpu)
    watcher = FolderWatcher(debounce_seconds=config.watcher.debounce_seconds)

    def on_change(event_type: str, path: str) -> None:
        if event_type in ("created", "modified"):
            file_info = scanner.scan_single(path)
            if file_info:
                logger.info("File %s: %s", event_type, path)
                _process_file(file_info, db, parser, ocr,
                              agent_version=config.agent_version,
                              processing_version=PROCESSING_VERSION,
                              parser_version=config.parser.backend,
                              ocr_engine=config.ocr.engine)
        elif event_type == "deleted":
            record = db.get_file_by_path(path)
            if record:
                db.delete_file(record["id"])
                logger.info("Deleted record for %s", path)

    for folder in folders:
        watcher.watch(folder, recursive=config.watcher.recursive, callback=on_change)

    print(f"Watching {len(folders)} folders. Press Ctrl+C to stop.")
    running = True

    def _stop(sig, frame):
        nonlocal running
        running = False
        print("\nStopping...")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while running:
            time.sleep(1)
    finally:
        watcher.stop_all()
        db.close()


def cmd_status(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Show agent status."""
    db = LocalDB(config.db_path)
    stats = db.get_stats()
    print(f"Edge Agent v{__version__}")
    print(f"  Agent:    {config.agent_name}")
    print(f"  Agent ID: {config.agent_id or '(not registered)'}")
    print(f"  Server:   {config.server.url}")
    print(f"  DB:       {config.db_path}")
    print()
    print("  Files:")
    for key, val in stats.items():
        print(f"    {key}: {val}")
    db.close()


def cmd_run(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Full loop: process pending files, sync, then watch."""
    db = LocalDB(config.db_path)
    scanner = FileScanner(
        ignore_patterns=config.scanner.ignore_patterns,
        max_file_size_mb=config.scanner.max_file_size_mb,
    )
    parser = ParserRouter()
    ocr = OCREngine(lang=config.ocr.lang, use_gpu=config.ocr.use_gpu)

    # Initial scan of all configured folders
    for folder in config.folders:
        if Path(folder).exists():
            logger.info("Initial scan of %s", folder)
            for file_info in scanner.scan_folder(folder, recursive=True):
                _process_file(file_info, db, parser, ocr,
                              agent_version=config.agent_version,
                              processing_version=PROCESSING_VERSION,
                              parser_version=config.parser.backend,
                              ocr_engine=config.ocr.engine)

    # Sync
    if config.server.api_key:
        sync = SyncManager(config, db)
        try:
            sync.sync_with_retry()
        except Exception as e:
            logger.warning("Initial sync failed: %s", e)
        sync.close()

    db.close()

    # Start watching
    cmd_watch(args, config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edge-agent",
        description="Edge Agent — local document processing for AI Archive Platform",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", "-c", help="Path to config.yaml")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # register
    p_reg = sub.add_parser("register", help="Register with the SaaS platform")
    p_reg.add_argument("--jwt", help="JWT token for registration auth (from POST /api/v1/auth/login)")
    p_reg.add_argument("--name", help="Agent name")

    # scan
    p_scan = sub.add_parser("scan", help="Scan a folder and process files")
    p_scan.add_argument("folder", nargs="?", help="Folder path to scan")
    p_scan.add_argument("--no-recursive", dest="recursive", action="store_false", default=True)

    # process
    p_proc = sub.add_parser("process", help="Process a single file")
    p_proc.add_argument("file", nargs="?", help="File path to process")

    # sync
    sub.add_parser("sync", help="Push pending files to the platform")

    # watch
    p_watch = sub.add_parser("watch", help="Watch folders for changes")
    p_watch.add_argument("--folders", nargs="+", help="Folders to watch")

    # status
    sub.add_parser("status", help="Show agent status")

    # run
    p_run = sub.add_parser("run", help="Full loop: scan + process + sync + watch")
    p_run.add_argument("--folders", nargs="+", help="Folders to watch")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    config = load_config(getattr(args, "config", None))
    if args.verbose:
        config.log_level = "DEBUG"

    setup_logging(config)

    # Ensure data dir exists
    Path(config.data_dir).mkdir(parents=True, exist_ok=True)

    commands = {
        "register": cmd_register,
        "scan": cmd_scan,
        "process": cmd_process,
        "sync": cmd_sync,
        "watch": cmd_watch,
        "status": cmd_status,
        "run": cmd_run,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
