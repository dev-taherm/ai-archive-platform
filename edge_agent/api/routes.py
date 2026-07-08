"""API routes for the Edge Agent local server."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .server import get_config, get_db, _start_time, _watcher_active

router = APIRouter()


class ConfigUpdate(BaseModel):
    server_url: str | None = None
    api_key: str | None = None
    jwt_token: str | None = None
    agent_name: str | None = None
    folders: list[str] | None = None


class ScanRequest(BaseModel):
    folder: str
    recursive: bool = True


class ProcessRequest(BaseModel):
    file: str


class SyncRequest(BaseModel):
    batch_size: int = 50


# --- Health & Status ---

@router.get("/health")
async def health():
    return {"status": "healthy", "service": "edge-agent-api"}


@router.get("/status")
async def status():
    config = get_config()
    db = get_db()
    stats = db.get_stats() if hasattr(db, "get_stats") else {}
    return {
        "agent_name": config.agent_name,
        "agent_id": config.agent_id,
        "version": config.agent_version,
        "uptime_seconds": int(time.time() - _start_time),
        "watcher_active": _watcher_active,
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
    return {"status": "updated"}


# --- Agent Operations ---

@router.post("/register")
async def register_agent():
    """Register agent with the SaaS platform."""
    from edge_agent.sync.manager import SyncManager
    config = get_config()
    sync = SyncManager(config)
    try:
        result = sync.register()
        return {"status": "registered", "result": result}
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
    scanner = FileScanner(config)
    router_parser = ParserRouter(config)
    ocr = OCREngine(config)

    folder = req.folder
    if not Path(folder).exists():
        raise HTTPException(status_code=400, detail=f"Folder not found: {folder}")

    files = list(scanner.scan_folder(folder, recursive=req.recursive))
    processed = 0
    errors = 0

    for file_meta in files:
        try:
            path = Path(file_meta["path"])
            content = path.read_bytes()
            parsed = router_parser.parse(path, content)

            text = parsed.text if hasattr(parsed, "text") else ""
            markdown = parsed.markdown if hasattr(parsed, "markdown") else ""

            if not text and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".pdf"}:
                text = ocr.extract_text(content, config.ocr.lang)

            db.upsert_file(
                path=str(path),
                content_hash=file_meta.get("content_hash", ""),
                mime_type=file_meta.get("mime_type", ""),
                size_bytes=file_meta.get("size_bytes", 0),
                extracted_text=text,
                markdown=markdown,
                processing_status="processed",
            )
            processed += 1
        except Exception as e:
            logger.error("Error processing %s: %s", file_meta.get("path"), e)
            errors += 1

    return {"scanned": len(files), "processed": processed, "errors": errors}


@router.post("/process")
async def process_file(req: ProcessRequest):
    """Process a single file."""
    from edge_agent.parsers.router import ParserRouter
    from edge_agent.ocr.engine import OCREngine

    config = get_config()
    db = get_db()
    parser = ParserRouter(config)
    ocr = OCREngine(config)

    path = Path(req.file)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {req.file}")

    try:
        content = path.read_bytes()
        parsed = parser.parse(path, content)

        text = parsed.text if hasattr(parsed, "text") else ""
        markdown = parsed.markdown if hasattr(parsed, "markdown") else ""

        if not text and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".pdf"}:
            text = ocr.extract_text(content, config.ocr.lang)

        db.upsert_file(
            path=str(path),
            content_hash="",
            mime_type="",
            size_bytes=len(content),
            extracted_text=text,
            markdown=markdown,
            processing_status="processed",
        )
        return {"status": "processed", "file": str(path), "text_length": len(text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Sync ---

@router.post("/sync")
async def sync_files(req: SyncRequest | None = None):
    """Sync pending files to the SaaS platform."""
    from edge_agent.sync.manager import SyncManager
    config = get_config()
    sync = SyncManager(config)
    try:
        result = sync.sync_files()
        return {"status": "synced", "result": result}
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
            return {"logs": [l.rstrip() for l in recent]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Watcher ---

@router.post("/watch/start")
async def start_watcher():
    """Start watching configured folders."""
    global _watcher_active
    _watcher_active = True
    return {"status": "watcher_started"}


@router.post("/watch/stop")
async def stop_watcher():
    """Stop watching folders."""
    global _watcher_active
    _watcher_active = False
    return {"status": "watcher_stopped"}
