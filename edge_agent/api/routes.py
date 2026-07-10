"""API routes for the Edge Agent local server."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .server import get_config, get_db, get_watcher, _start_time

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigUpdate(BaseModel):
    server_url: str | None = None
    api_key: str | None = None
    jwt_token: str | None = None
    agent_name: str | None = None
    folders: list[str] | None = None
    ocr_engine: str | None = None
    ocr_lang: str | None = None
    parser_backend: str | None = None
    sync_interval_minutes: int | None = None


class ScanRequest(BaseModel):
    folder: str
    recursive: bool = True


class ProcessRequest(BaseModel):
    file: str


class FolderAddRequest(BaseModel):
    path: str
    label: str = ""


class MarkSyncedRequest(BaseModel):
    file_hashes: list[str]


# --- Health & Status ---

@router.get("/health")
async def health():
    return {"status": "healthy", "service": "edge-agent-api"}


@router.get("/status")
async def status():
    config = get_config()
    db = get_db()
    stats = db.get_stats()
    watcher = get_watcher()
    return {
        "agent_name": config.agent_name,
        "agent_id": config.agent_id,
        "version": config.agent_version,
        "uptime_seconds": int(time.time() - _start_time),
        "watcher_active": len(watcher.watched_paths) > 0,
        "watched_folders": watcher.watched_paths,
        "db_path": config.db_path,
        "stats": stats,
    }


# --- Config ---

@router.get("/config")
async def get_agent_config():
    config = get_config()
    return {
        "server_url": config.server.url,
        "api_key": config.server.api_key,
        "jwt_token": config.server.jwt_token,
        "agent_name": config.agent_name,
        "agent_id": config.agent_id,
        "folders": config.folders,
        "ocr_engine": config.ocr.engine,
        "ocr_lang": config.ocr.lang,
        "parser_backend": config.parser.backend,
        "sync_interval_minutes": config.sync.interval_minutes,
    }


@router.put("/config")
async def update_config(update: ConfigUpdate):
    config = get_config()
    if update.server_url is not None:
        config.server.url = update.server_url
    if update.api_key is not None:
        config.server.api_key = update.api_key
    if update.jwt_token is not None:
        config.server.jwt_token = update.jwt_token
    if update.agent_name is not None:
        config.agent_name = update.agent_name
    if update.folders is not None:
        config.folders = update.folders
    if update.ocr_engine is not None:
        config.ocr.engine = update.ocr_engine
    if update.ocr_lang is not None:
        config.ocr.lang = update.ocr_lang
    if update.parser_backend is not None:
        config.parser.backend = update.parser_backend
    if update.sync_interval_minutes is not None:
        config.sync.interval_minutes = update.sync_interval_minutes

    _save_config_to_yaml(config)
    return {"status": "updated"}


def _save_config_to_yaml(config):
    try:
        from edge_agent.cli import _save_config
        config_path = Path(config.data_dir) / "config.yaml"
        _save_config(config, config_path)
    except Exception as e:
        logger.warning("Failed to save config: %s", e)


# --- Agent Operations ---

@router.get("/pending-sync")
async def pending_sync(batch_size: int = Query(50, ge=1, le=500)):
    """Build sync payload from pending local files (no SaaS call)."""
    from edge_agent.sync.manager import SyncManager
    config = get_config()
    db = get_db()
    sync = SyncManager(config, db)
    try:
        payload = sync.build_sync_payload(batch_size=batch_size)
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-synced")
async def mark_synced(req: MarkSyncedRequest):
    """Mark files as synced in local DB by content_hash."""
    from edge_agent.sync.manager import SyncManager
    config = get_config()
    db = get_db()
    sync = SyncManager(config, db)
    try:
        count = sync.mark_synced(req.file_hashes)
        return {"status": "ok", "marked": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan")
async def scan_folder(req: ScanRequest):
    """Scan a folder and process all files."""
    from edge_agent.core.scanner import FileScanner
    from edge_agent.parsers.router import ParserRouter
    from edge_agent.ocr.engine import OCREngine

    config = get_config()
    db = get_db()
    scanner = FileScanner(
        ignore_patterns=config.scanner.ignore_patterns,
        max_file_size_mb=config.scanner.max_file_size_mb,
    )
    parser = ParserRouter()
    ocr = OCREngine(lang=config.ocr.lang, use_gpu=config.ocr.use_gpu)

    folder = req.folder
    if not Path(folder).exists():
        raise HTTPException(status_code=400, detail=f"Folder not found: {folder}")

    files = list(scanner.scan_folder(folder, recursive=req.recursive))
    processed = 0
    errors = 0

    for file_meta in files:
        try:
            from edge_agent.cli import _process_file, PROCESSING_VERSION
            _process_file(
                file_meta, db, parser, ocr,
                agent_version=config.agent_version,
                processing_version=PROCESSING_VERSION,
                parser_version=config.parser.backend,
                ocr_engine=config.ocr.engine,
            )
            processed += 1
        except Exception as e:
            logger.error("Error processing %s: %s", file_meta.get("path"), e)
            errors += 1

    return {"scanned": len(files), "processed": processed, "errors": errors}


@router.post("/process")
async def process_file(req: ProcessRequest):
    """Process a single file."""
    from edge_agent.core.scanner import FileScanner
    from edge_agent.parsers.router import ParserRouter
    from edge_agent.ocr.engine import OCREngine
    from edge_agent.cli import _process_file, PROCESSING_VERSION

    config = get_config()
    db = get_db()
    scanner = FileScanner(
        ignore_patterns=config.scanner.ignore_patterns,
        max_file_size_mb=config.scanner.max_file_size_mb,
    )
    parser = ParserRouter()
    ocr = OCREngine(lang=config.ocr.lang, use_gpu=config.ocr.use_gpu)

    path = Path(req.file)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {req.file}")

    try:
        file_info = scanner.scan_single(req.file)
        if not file_info:
            raise HTTPException(status_code=400, detail=f"Could not scan {req.file}")

        _process_file(
            file_info, db, parser, ocr,
            agent_version=config.agent_version,
            processing_version=PROCESSING_VERSION,
            parser_version=config.parser.backend,
            ocr_engine=config.ocr.engine,
        )
        record = db.get_file_by_hash(file_info["content_hash"])
        return {
            "status": "processed",
            "file": str(path),
            "text_length": len(record["extracted_text"]) if record else 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Files ---

@router.get("/files")
async def list_files(status: str | None = None, limit: int = 50):
    """List files in the local database."""
    db = get_db()
    try:
        files = db.list_files(status=status, limit=limit)
        return {"files": files, "count": len(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Folders ---

@router.get("/folders")
async def list_folders():
    """List monitored folders."""
    config = get_config()
    watcher = get_watcher()
    folders = []
    for path_str in config.folders:
        folders.append({
            "path": path_str,
            "label": Path(path_str).name,
            "exists": Path(path_str).exists(),
            "watching": watcher.is_watching(path_str),
        })
    return {"folders": folders}


@router.post("/folders")
async def add_folder(req: FolderAddRequest):
    """Add a folder to monitor."""
    config = get_config()
    folder_path = req.path

    if not Path(folder_path).exists():
        raise HTTPException(status_code=400, detail=f"Folder not found: {folder_path}")

    if folder_path not in config.folders:
        config.folders.append(folder_path)
        _save_config_to_yaml(config)

    return {"status": "added", "path": folder_path}


@router.delete("/folders/{folder_path:path}")
async def remove_folder(folder_path: str):
    """Remove a folder from monitoring."""
    config = get_config()
    watcher = get_watcher()

    if folder_path in config.folders:
        config.folders.remove(folder_path)
        _save_config_to_yaml(config)

    if watcher.is_watching(folder_path):
        watcher.stop(folder_path)

    return {"status": "removed", "path": folder_path}


# --- Logs ---

@router.get("/logs")
async def get_logs(lines: int = 100):
    """Get recent log entries."""
    config = get_config()
    log_path = Path(config.log_file)
    if not log_path.exists():
        return {"logs": []}
    try:
        with open(log_path) as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:]
            return {"logs": [line.rstrip() for line in recent]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Watcher ---

@router.post("/watch/start")
async def start_watcher():
    """Start watching configured folders."""
    config = get_config()
    db = get_db()
    watcher = get_watcher()

    if not config.folders:
        return {"status": "no_folders", "message": "No folders configured"}

    from edge_agent.core.scanner import FileScanner
    from edge_agent.parsers.router import ParserRouter
    from edge_agent.ocr.engine import OCREngine
    from edge_agent.cli import _process_file, PROCESSING_VERSION

    scanner = FileScanner(
        ignore_patterns=config.scanner.ignore_patterns,
        max_file_size_mb=config.scanner.max_file_size_mb,
    )
    parser = ParserRouter()
    ocr = OCREngine(lang=config.ocr.lang, use_gpu=config.ocr.use_gpu)

    def on_change(event_type: str, path_str: str) -> None:
        if event_type in ("created", "modified"):
            file_info = scanner.scan_single(path_str)
            if file_info:
                logger.info("File %s: %s", event_type, path_str)
                _process_file(
                    file_info, db, parser, ocr,
                    agent_version=config.agent_version,
                    processing_version=PROCESSING_VERSION,
                    parser_version=config.parser.backend,
                    ocr_engine=config.ocr.engine,
                )
        elif event_type == "deleted":
            record = db.get_file_by_path(path_str)
            if record:
                db.delete_file(record["id"])
                logger.info("Deleted record for %s", path_str)

    for folder in config.folders:
        if Path(folder).exists() and not watcher.is_watching(folder):
            watcher.watch(
                folder,
                recursive=config.watcher.recursive,
                callback=on_change,
            )

    return {"status": "watcher_started", "folders": watcher.watched_paths}


@router.post("/watch/stop")
async def stop_watcher():
    """Stop watching folders."""
    watcher = get_watcher()
    watcher.stop_all()
    return {"status": "watcher_stopped"}
