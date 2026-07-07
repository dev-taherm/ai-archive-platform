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
from edge_agent.llm.client import LLMClient
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
        "llm": {
            "provider": config.llm.provider,
            "model": config.llm.model,
            "api_key": config.llm.api_key,
            "base_url": config.llm.base_url,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens,
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
    entity_stats = db.get_entity_stats()
    print(f"Edge Agent v{__version__}")
    print(f"  Agent:    {config.agent_name}")
    print(f"  Agent ID: {config.agent_id or '(not registered)'}")
    print(f"  Server:   {config.server.url}")
    print(f"  DB:       {config.db_path}")
    print()
    print("  Files:")
    for key, val in stats.items():
        print(f"    {key}: {val}")
    if entity_stats:
        print()
        print("  Entities:")
        for etype, count in sorted(entity_stats.items()):
            print(f"    {etype}: {count}")
    db.close()


def _extract_entities_batch(
    db: LocalDB,
    llm: LLMClient,
    batch_size: int = 10,
    force: bool = False,
) -> dict:
    """Batch-extract entities from all completed files that lack entities.

    Args:
        db: Local database.
        llm: LLM client for extraction.
        batch_size: Number of files to process per batch.
        force: If True, re-extract even files that already have entities.

    Returns:
        Stats dict with extracted counts.
    """
    files = db.list_files(status="completed", synced=0, limit=10000)
    if not files:
        # Also get synced files if force=True
        if force:
            files = db.list_files(status="completed", limit=10000)
        else:
            return {"processed": 0, "entities_found": 0}

    processed = 0
    total_entities = 0

    for f in files:
        file_id = f["id"]
        text = f.get("extracted_text", "")
        if not text or len(text.strip()) < 50:
            continue

        # Skip files that already have entities (unless force)
        if not force:
            existing = db.get_entities(file_id)
            if existing:
                continue

        logger.info("Extracting entities from: %s", f.get("local_path", file_id))
        try:
            entities = llm.extract_entities(text)
            if entities:
                ent_dicts = [
                    {
                        "entity_type": e.entity_type,
                        "name": e.name,
                        "context": e.context,
                        "confidence": e.confidence,
                        "source": "agent",
                    }
                    for e in entities
                ]
                db.save_entities(file_id, ent_dicts)
                total_entities += len(ent_dicts)
                logger.info("  Found %d entities", len(ent_dicts))
            processed += 1
        except Exception:
            logger.exception("  Entity extraction failed for %s", f.get("local_path"))

        if processed >= batch_size:
            break

    return {"processed": processed, "entities_found": total_entities}


def cmd_extract(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Batch-extract entities from processed files using LLM."""
    if not config.llm.api_key and config.llm.provider != "ollama":
        print(f"ERROR: LLM API key not configured for {config.llm.provider}")
        print("  Set llm.api_key in config or EDGE_LLM_API_KEY env var")
        sys.exit(1)

    db = LocalDB(config.db_path)
    llm = LLMClient(config.llm)
    force = getattr(args, "force", False)
    batch_size = getattr(args, "batch", 10)

    print(f"Extracting entities (provider={config.llm.provider}, model={config.llm.model})...")
    result = _extract_entities_batch(db, llm, batch_size=batch_size, force=force)
    print(f"  Files processed: {result['processed']}")
    print(f"  Entities found:  {result['entities_found']}")

    entity_stats = db.get_entity_stats()
    if entity_stats:
        print()
        print("  By type:")
        for etype, count in sorted(entity_stats.items()):
            print(f"    {etype}: {count}")

    db.close()


# ---------------------------------------------------------------------------
# Command dispatch — executes commands received from the SaaS platform
# ---------------------------------------------------------------------------

def _execute_scan(
    db: LocalDB,
    scanner: FileScanner,
    parser: ParserRouter,
    ocr: OCREngine,
    config: EdgeAgentConfig,
    payload: dict,
) -> dict:
    """Execute a scan command: scan one or all folders."""
    folder = payload.get("folder_path")
    folders = [folder] if folder else config.folders
    scanned = 0
    processed = 0

    for f in folders:
        if not Path(f).exists():
            logger.warning("Folder does not exist: %s", f)
            continue
        for file_info in scanner.scan_folder(f, recursive=True):
            _process_file(
                file_info, db, parser, ocr,
                agent_version=config.agent_version,
                processing_version=PROCESSING_VERSION,
                parser_version=config.parser.backend,
                ocr_engine=config.ocr.engine,
            )
            scanned += 1
            processed += 1

    return {"scanned": scanned, "processed": processed}


def _execute_sync(
    db: LocalDB,
    config: EdgeAgentConfig,
) -> dict:
    """Execute a sync command: push pending files to the platform."""
    sync = SyncManager(config, db)
    try:
        result = sync.sync_with_retry()
        return result
    finally:
        sync.close()


def _execute_process(
    db: LocalDB,
    scanner: FileScanner,
    parser: ParserRouter,
    ocr: OCREngine,
    config: EdgeAgentConfig,
    payload: dict,
) -> dict:
    """Execute a process command: process a single file by path."""
    file_path = payload.get("file_path", "")
    if not file_path:
        return {"error": "No file_path in payload"}

    file_info = scanner.scan_single(file_path)
    if not file_info:
        return {"error": f"Could not scan {file_path}"}

    _process_file(
        file_info, db, parser, ocr,
        agent_version=config.agent_version,
        processing_version=PROCESSING_VERSION,
        parser_version=config.parser.backend,
        ocr_engine=config.ocr.engine,
    )
    return {"processed": file_path, "status": "completed"}


def _execute_config_update(
    config: EdgeAgentConfig,
    payload: dict,
) -> dict:
    """Execute a config_update command: update local configuration."""
    updated_fields = []
    if "sync_interval_minutes" in payload:
        config.sync.interval_minutes = payload["sync_interval_minutes"]
        updated_fields.append("sync_interval_minutes")
    if "max_file_size_mb" in payload:
        config.scanner.max_file_size_mb = payload["max_file_size_mb"]
        updated_fields.append("max_file_size_mb")
    if "folders" in payload:
        config.folders = payload["folders"]
        updated_fields.append("folders")
    return {"updated": updated_fields}


def _execute_shutdown() -> dict:
    """Execute a shutdown command: signal the agent to stop."""
    logger.info("Shutdown command received")
    return {"status": "shutting_down"}


def _execute_update(config: EdgeAgentConfig, payload: dict) -> dict:
    """Execute an update command: pull latest and restart."""
    import subprocess
    import sys

    repo_path = payload.get("repo_path", str(Path(__file__).parent.parent))
    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("Update pulled successfully: %s", result.stdout.strip())
            # Restart the current process
            os.execv(sys.executable, [sys.executable] + sys.argv)
        return {"status": "update_failed", "error": result.stderr}
    except Exception as e:
        return {"status": "update_failed", "error": str(e)}


def _execute_restart() -> dict:
    """Execute a restart command: restart the current process."""
    import os
    import sys

    logger.info("Restart command received")
    os.execv(sys.executable, [sys.executable] + sys.argv)
    # Unreachable, but just in case
    return {"status": "restarting"}


def _execute_start_scan(config: EdgeAgentConfig, payload: dict) -> dict:
    """Execute a start_scan command: mark folders for continuous scanning."""
    folders = payload.get("folders", config.folders)
    logger.info("Continuous scan started for: %s", folders)
    return {"status": "scan_started", "folders": folders}


def _execute_stop_scan() -> dict:
    """Execute a stop_scan command: stop continuous scanning."""
    logger.info("Continuous scan stopped")
    return {"status": "scan_stopped"}


def dispatch_commands(
    commands: list[dict],
    db: LocalDB,
    scanner: FileScanner,
    parser: ParserRouter,
    ocr: OCREngine,
    config: EdgeAgentConfig,
    sync: SyncManager | None = None,
) -> list[dict]:
    """Process a list of commands from the server.

    Returns list of results for reporting back to the platform.
    """
    results = []
    for cmd in commands:
        cmd_id = cmd.get("id", "")
        cmd_type = cmd.get("command_type", "")
        payload = cmd.get("payload", {})

        logger.info("Dispatching command: %s (id=%s)", cmd_type, cmd_id)

        try:
            if cmd_type == "scan":
                result = _execute_scan(db, scanner, parser, ocr, config, payload)
            elif cmd_type == "sync":
                result = _execute_sync(db, config)
            elif cmd_type == "process":
                result = _execute_process(db, scanner, parser, ocr, config, payload)
            elif cmd_type == "config_update":
                result = _execute_config_update(config, payload)
            elif cmd_type == "shutdown":
                result = _execute_shutdown()
            elif cmd_type == "update":
                result = _execute_update(config, payload)
            elif cmd_type == "restart":
                result = _execute_restart()
            elif cmd_type == "start_scan":
                result = _execute_start_scan(config, payload)
            elif cmd_type == "stop_scan":
                result = _execute_stop_scan()
            else:
                result = {"error": f"Unknown command type: {cmd_type}"}

            results.append({"command_id": cmd_id, "status": "completed", "result": result})

            # Report back to server
            if sync:
                try:
                    sync.report_command_result(cmd_id, status="completed", result=result)
                except Exception as e:
                    logger.warning("Failed to report command result: %s", e)

        except Exception as e:
            logger.exception("Command %s failed", cmd_type)
            error_result = {"error": str(e)}
            results.append({"command_id": cmd_id, "status": "failed", "result": error_result})
            if sync:
                try:
                    sync.report_command_result(cmd_id, status="failed", result=error_result)
                except Exception:
                    logger.warning("Failed to report command failure")

    return results


def _heartbeat_loop(
    sync: SyncManager,
    db: LocalDB,
    scanner: FileScanner,
    parser: ParserRouter,
    ocr: OCREngine,
    config: EdgeAgentConfig,
    stop_event: Any,
) -> None:
    """Periodic heartbeat loop: sends heartbeat, receives and dispatches commands."""
    interval_seconds = config.sync.interval_minutes * 60
    logger.info(
        "Heartbeat loop started (interval=%d minutes)",
        config.sync.interval_minutes,
    )

    while not stop_event.is_set():
        try:
            response = sync.heartbeat()
            pending_commands = response.get("pending_commands", [])

            if pending_commands:
                logger.info("Received %d command(s)", len(pending_commands))
                dispatch_commands(
                    pending_commands, db, scanner, parser, ocr, config, sync=sync,
                )
        except Exception as e:
            logger.warning("Heartbeat failed: %s", e)

        stop_event.wait(interval_seconds)


def cmd_run(args: argparse.Namespace, config: EdgeAgentConfig) -> None:
    """Full loop: process pending files, sync, then watch + heartbeat."""
    import threading

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

    # Initial sync + start heartbeat thread
    sync = None
    stop_event = threading.Event()
    heartbeat_thread = None

    if config.server.api_key:
        sync = SyncManager(config, db)
        try:
            sync.sync_with_retry()
        except Exception as e:
            logger.warning("Initial sync failed: %s", e)

        heartbeat_thread = threading.Thread(
            target=_heartbeat_loop,
            args=(sync, db, scanner, parser, ocr, config, stop_event),
            daemon=True,
            name="heartbeat",
        )
        heartbeat_thread.start()
        logger.info("Heartbeat thread started")

    # cmd_watch creates its own db/scanner/parser/ocr and blocks
    cmd_watch(args, config)

    # Cleanup after watch exits (SIGINT/SIGTERM)
    stop_event.set()
    if heartbeat_thread:
        heartbeat_thread.join(timeout=5)
    if sync:
        sync.close()
    db.close()


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

    # extract
    p_extract = sub.add_parser("extract", help="Batch-extract entities from processed files")
    p_extract.add_argument("--batch", type=int, default=10, help="Max files to process (default: 10)")
    p_extract.add_argument("--force", action="store_true", help="Re-extract even files with existing entities")

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
        "extract": cmd_extract,
        "run": cmd_run,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
