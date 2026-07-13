from __future__ import annotations

import hmac
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .server import (
    get_config,
    get_db,
    get_worker,
    get_watcher,
    get_sync_engine,
    get_metrics,
    get_log_handler,
    get_event_bus,
    get_start_time,
)
from edge_agent.core.capabilities import detect_capabilities
from edge_agent.core.job_queue import JobQueue


def _validate_path_safe(path: str) -> str:
    resolved = str(Path(path).resolve())
    # Validate resolved path components, not raw input
    if ".." in resolved.split(os.sep) or ".." in resolved.split("/") or ".." in resolved.split("\\"):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    return resolved

logger = logging.getLogger(__name__)

router = APIRouter()


class ParseFileRequest(BaseModel):
    file_path: str


class ScanRequest(BaseModel):
    file_id: str


class FolderCreate(BaseModel):
    path: str


class ConfigUpdate(BaseModel):
    config: dict[str, str]


class JobCreate(BaseModel):
    type: str
    payload: dict | None = None


class MarkSyncedRequest(BaseModel):
    file_hashes: list[str]


class RescanRequest(BaseModel):
    path: str


class RegisterRequest(BaseModel):
    server_url: str
    access_token: str


class MoveFileRequest(BaseModel):
    file_id: str
    dest_path: str


class RenameFileRequest(BaseModel):
    file_id: str
    new_name: str


class DeleteFileRequest(BaseModel):
    file_id: str


class CopyFileRequest(BaseModel):
    file_id: str
    dest_path: str


class ArchiveRequest(BaseModel):
    file_ids: list[str]
    dest_path: str
    format: str = "zip"


class RestoreFileRequest(BaseModel):
    trash_id: str


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "edge-agent"}


@router.get("/status")
async def status():
    cfg = get_config()
    db = get_db()
    worker = get_worker()
    watcher = get_watcher()
    metrics = get_metrics()

    files = db.get_stats()
    job_stats = db.get_job_stats()

    return {
        "agent_name": cfg.agent_name,
        "agent_id": cfg.agent_id,
        "version": cfg.agent_version,
        "uptime_seconds": int(time.time() - get_start_time()),
        "worker": {
            "running": worker.is_running,
            "paused": worker.is_paused,
            "active_jobs": worker.processing_count,
        },
        "watcher": {
            "running": watcher.is_running,
            "folder_count": watcher.folder_count,
        },
        "files": files,
        "queue": job_stats,
        "memory_mb": metrics.snapshot().get("memory_mb", 0.0),
    }


@router.get("/capabilities")
async def capabilities():
    return detect_capabilities()


@router.get("/config")
async def get_config_endpoint():
    db = get_db()
    return db.get_config()


# ── SaaS Communication (proxy to SaaS backend) ─────────────────────────────


@router.post("/register")
async def register_agent(body: RegisterRequest):
    engine = get_sync_engine()
    result = engine.register(body.server_url, body.access_token)
    return result


@router.post("/heartbeat")
async def send_heartbeat():
    engine = get_sync_engine()
    return engine.heartbeat()


@router.post("/sync")
async def run_sync():
    engine = get_sync_engine()
    return engine.sync_files()


@router.put("/config")
async def update_config_endpoint(body: ConfigUpdate):
    db = get_db()
    db.set_config_batch(body.config)
    return {"status": "ok"}


@router.get("/folders")
async def get_folders():
    db = get_db()
    return db.get_folders()


@router.post("/folders")
async def add_folder(body: FolderCreate):
    from edge_agent.core.scanner import scan_folder

    db = get_db()
    db.add_folder(body.path)
    files = scan_folder(body.path)
    count = db.upsert_files(files)
    return {"status": "ok", "path": body.path, "discovered": count}


@router.delete("/folders")
async def remove_folder(path: str = Query(...)):
    db = get_db()
    db.remove_folder(path)
    return {"status": "removed", "path": path}


@router.post("/folders/rescan")
async def rescan_folder(body: RescanRequest):
    from edge_agent.core.scanner import scan_folder, scan_single

    db = get_db()
    fpath = body.path
    if not Path(fpath).is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {fpath}")

    existing_files = db.get_files(limit=10000)
    existing_by_path: dict[str, dict] = {f["local_path"]: f for f in existing_files}

    discovered = 0
    updated = 0

    for root, dirs, files in os.walk(fpath, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if fname.startswith("."):
                continue
            full = os.path.join(root, fname)
            meta = scan_single(full)
            if not meta:
                continue
            if full in existing_by_path:
                old = existing_by_path[full]
                if meta["file_hash"] != old.get("file_hash"):
                    db.upsert_files([meta])
                    updated += 1
            else:
                db.upsert_files([meta])
                discovered += 1

    removed_paths = [p for p in existing_by_path if not Path(p).exists()]
    for p in removed_paths:
        db.delete_files_by_path(p)

    return {
        "status": "ok",
        "path": fpath,
        "discovered": discovered,
        "updated": updated,
        "removed": len(removed_paths),
    }


@router.get("/files")
async def get_files(
    status: str | None = Query(None),
    limit: int = Query(1000),
    folder: str | None = Query(None),
):
    db = get_db()
    return db.get_files(status=status, limit=limit, folder=folder)


@router.get("/files/{file_id}")
async def get_file(file_id: str):
    db = get_db()
    record = db.get_file_by_id(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    return record


@router.post("/files/mark-synced")
async def mark_files_synced(body: MarkSyncedRequest):
    db = get_db()
    db.mark_synced(body.file_hashes)
    return {"status": "ok", "count": len(body.file_hashes)}


@router.post("/scan")
async def scan_file(body: ScanRequest):
    db = get_db()
    worker = get_worker()
    queue = JobQueue(db)

    record = db.get_file_by_id(body.file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = record["local_path"]
    if not Path(file_path).exists():
        db.mark_file_failed(body.file_id)
        raise HTTPException(status_code=400, detail=f"File not found: {file_path}")

    existing = queue.list_jobs(status="pending", limit=50)
    existing += queue.list_jobs(status="running", limit=50)
    for j in existing:
        payload = j.get("payload", {})
        if isinstance(payload, dict) and payload.get("file_id") == body.file_id:
            return {"status": "processing", "job_id": j["id"], "note": "Already queued"}

    job_id = queue.create_job("scan_file", {"file_id": body.file_id})

    return {"status": "processing", "job_id": job_id}


@router.get("/logs")
async def get_logs(
    level: str | None = Query(None),
    limit: int = Query(50),
    since: str | None = Query(None),
):
    handler = get_log_handler()
    if handler is None:
        return []
    return handler.get_records(level=level, limit=limit, since=since)


@router.get("/metrics")
async def get_agent_metrics():
    metrics = get_metrics()
    return metrics.snapshot()


@router.post("/agent/pause")
async def pause_agent():
    worker = get_worker()
    worker.pause()
    return {"status": "paused"}


@router.post("/agent/resume")
async def resume_agent():
    worker = get_worker()
    worker.resume()
    return {"status": "resumed"}


@router.post("/agent/restart")
async def restart_agent():
    from edge_agent.api.server import get_config as get_cfg

    worker = get_worker()
    watcher = get_watcher()
    cfg = get_cfg()

    worker.stop()
    logger.info("Worker stopped for restart")

    if watcher.is_running:
        watcher.stop()
        logger.info("Watcher stopped for restart")

    worker.start()
    logger.info("Worker restarted")

    if cfg.watcher.enabled:
        watcher.start(cfg.folders)
        logger.info("Watcher restarted for %d folders", len(cfg.folders))

    return {"status": "restarted"}


@router.post("/parse-file")
async def parse_file(req: ParseFileRequest):
    from edge_agent.parsers.router import ParserRouter
    from edge_agent.ocr.engine import OCREngine
    from edge_agent.ocr.fallback import ocr_fallback

    path = Path(req.file_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {req.file_path}")
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {req.file_path}")

    cfg = get_config()
    parser = ParserRouter()
    ocr = OCREngine(lang=cfg.ocr.lang, use_gpu=cfg.ocr.use_gpu)

    try:
        parsed = parser.parse(req.file_path)
        text = (parsed.markdown or "").replace("\0", "")
        text, ocr_used = ocr_fallback(text, path, ocr)

        return {
            "status": "ok",
            "file_path": req.file_path,
            "filename": path.name,
            "extension": path.suffix.lower(),
            "markdown": text,
            "content_blocks": [b.to_dict() if hasattr(b, "to_dict") else vars(b) for b in parsed.content_blocks],
            "tables": [t.to_dict() if hasattr(t, "to_dict") else vars(t) for t in parsed.tables],
            "images": [i.to_dict() if hasattr(i, "to_dict") else vars(i) for i in parsed.images],
            "language": getattr(parsed, "language", "unknown"),
            "word_count": parsed.word_count,
            "char_count": parsed.char_count,
            "page_count": parsed.page_count,
            "ocr_used": ocr_used,
            "parse_method": getattr(parsed, "parse_method", ""),
            "parse_time_ms": getattr(parsed, "parse_time_ms", 0.0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to parse %s", req.file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs")
async def create_job(body: JobCreate):
    db = get_db()
    queue = JobQueue(db)
    job_id = queue.create_job(body.type, body.payload)
    return {"job_id": job_id}


@router.get("/jobs")
async def list_jobs(
    status: str | None = Query(None),
    limit: int = Query(50),
):
    db = get_db()
    queue = JobQueue(db)
    return queue.list_jobs(status=status, limit=limit)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    db = get_db()
    queue = JobQueue(db)
    job = queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── File Operations ─────────────────────────────────────────────────────────


@router.post("/files/move")
async def move_file(body: MoveFileRequest):
    db = get_db()
    record = db.get_file_by_id(body.file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    src = record["local_path"]
    dest = _validate_path_safe(body.dest_path)
    if not Path(src).exists():
        raise HTTPException(status_code=400, detail=f"Source not found: {src}")
    if Path(dest).exists():
        raise HTTPException(status_code=409, detail=f"Destination already exists: {dest}")

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    os.rename(src, str(dest_path))

    db.update_file_path(
        body.file_id,
        local_path=str(dest_path),
        filename=dest_path.name,
        extension=dest_path.suffix.lower(),
    )
    return {"status": "ok", "file_id": body.file_id, "new_path": str(dest_path)}


@router.post("/files/rename")
async def rename_file(body: RenameFileRequest):
    db = get_db()
    record = db.get_file_by_id(body.file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    src = Path(record["local_path"])
    if not src.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {src}")

    new_name = body.new_name
    if "/" in new_name or "\\" in new_name:
        raise HTTPException(status_code=400, detail="Rename cannot contain path separators")
    dest = src.parent / new_name
    if dest.exists():
        raise HTTPException(status_code=409, detail=f"Destination already exists: {dest}")
    os.rename(str(src), str(dest))

    db.update_file_path(
        body.file_id,
        local_path=str(dest),
        filename=dest.name,
        extension=dest.suffix.lower(),
    )
    return {"status": "ok", "file_id": body.file_id, "new_path": str(dest)}


@router.post("/files/delete")
async def delete_file(body: DeleteFileRequest):
    db = get_db()
    record = db.get_file_by_id(body.file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    src = Path(record["local_path"])
    if not src.exists():
        db.delete_file_record(body.file_id)
        return {"status": "ok", "note": "File already missing, record removed"}

    config = get_config()
    trash_dir = Path(config.data_dir) / "trash"
    trash_dir.mkdir(parents=True, exist_ok=True)

    size = src.stat().st_size
    trash_id = db.add_to_trash(str(src), body.file_id, size)
    trash_subdir = trash_dir / trash_id
    trash_subdir.mkdir(parents=True, exist_ok=True)
    dest = trash_subdir / src.name
    os.rename(str(src), str(dest))

    db.delete_file_record(body.file_id)
    return {"status": "ok", "trash_id": trash_id}


@router.post("/files/copy")
async def copy_file(body: CopyFileRequest):
    db = get_db()
    record = db.get_file_by_id(body.file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    src = Path(record["local_path"])
    if not src.exists():
        raise HTTPException(status_code=400, detail=f"Source not found: {src}")

    dest_path_str = _validate_path_safe(body.dest_path)
    dest = Path(dest_path_str)
    if dest.exists():
        raise HTTPException(status_code=409, detail=f"Destination already exists: {dest_path_str}")
    dest.parent.mkdir(parents=True, exist_ok=True)

    import shutil
    shutil.copy2(str(src), str(dest))

    from edge_agent.core.scanner import scan_single
    meta = scan_single(str(dest))
    if meta:
        db.upsert_files([meta])
        return {"status": "ok", "file": meta}

    return {"status": "ok", "note": "Copied but could not index"}


@router.post("/files/restore")
async def restore_file(body: RestoreFileRequest):
    db = get_db()
    entry = db.get_trash_entry(body.trash_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Trash entry not found")

    original = Path(entry["original_path"])
    trash_dir = Path(get_config().data_dir) / "trash" / body.trash_id
    trash_file = trash_dir / original.name

    if trash_file.exists():
        original.parent.mkdir(parents=True, exist_ok=True)
        os.rename(str(trash_file), str(original))

    from edge_agent.core.scanner import scan_single
    meta = scan_single(str(original))
    file_id = entry["original_file_id"] if entry["original_file_id"] else None
    if meta:
        if file_id:
            meta["id"] = file_id
            db.upsert_files([meta])
        else:
            db.upsert_files([meta])

    db.remove_from_trash(body.trash_id)

    if trash_dir.exists():
        import shutil
        shutil.rmtree(str(trash_dir))

    return {"status": "ok", "original_path": str(original)}


@router.post("/files/archive")
async def archive_files(body: ArchiveRequest):
    if not body.file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")

    db = get_db()
    dest = Path(body.dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    files_to_archive: list[Path] = []
    for fid in body.file_ids:
        rec = db.get_file_by_id(fid)
        if rec:
            p = Path(rec["local_path"])
            if p.exists():
                files_to_archive.append(p)

    if not files_to_archive:
        raise HTTPException(status_code=400, detail="No valid files to archive")

    import shutil
    if body.format == "zip":
        import zipfile
        with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in files_to_archive:
                zf.write(str(fp), arcname=fp.name)
    else:
        import tarfile
        with tarfile.open(str(dest), "w:gz") as tf:
            for fp in files_to_archive:
                tf.add(str(fp), arcname=fp.name)

    return {"status": "ok", "archive_path": str(dest), "file_count": len(files_to_archive)}


@router.get("/trash")
async def list_trash():
    db = get_db()
    entries = db.list_trash()
    config = get_config()
    trash_dir = Path(config.data_dir) / "trash"
    result = []
    for e in entries:
        orig = Path(e["original_path"])
        trash_path = trash_dir / e["id"] / orig.name
        result.append({
            **e,
            "filename": orig.name,
            "trash_file_exists": trash_path.exists(),
        })
    return result


# ── WebSocket (true push model) ──────────────────────────────────────────────


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    """Push-based WebSocket — events auto-push to all connected clients.

    Protocol:
      Server → Client: {"type":"event","event":{...}}   (real-time event)
      Server → Client: {"type":"events","events":[...]}  (buffered batch on connect)
      Server → Client: {"type":"ping"}                   (keepalive, 30s)
      Client → Server: {"type":"pong"}                   (keepalive response)
    """
    import asyncio

    await ws.accept()
    bus = get_event_bus()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _on_event(event: dict[str, Any]) -> None:
        """Observer callback — called from worker/watcher threads."""
        try:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except RuntimeError:
            pass  # event loop closed

    bus.subscribe(_on_event)

    try:
        # Send buffered events immediately on connect
        buffered = bus.snapshot(max_events=100)
        if buffered:
            try:
                await ws.send_json({"type": "events", "events": buffered})
            except WebSocketDisconnect:
                return

        async def _sender() -> None:
            """Push events from EventBus observer to the WS client."""
            while True:
                event = await queue.get()
                try:
                    await ws.send_json({"type": "event", "event": event})
                except Exception:
                    break

        async def _keepalive() -> None:
            """Server-side ping every 30s to detect stale connections."""
            while True:
                await asyncio.sleep(30)
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    break

        sender_task = asyncio.create_task(_sender())
        keepalive_task = asyncio.create_task(_keepalive())

        try:
            # Read client messages (pong responses, manual pings)
            while True:
                data = await ws.receive_text()
                if data == "pong":
                    continue
                if data == "ping":
                    await ws.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        finally:
            sender_task.cancel()
            keepalive_task.cancel()
    finally:
        bus.unsubscribe(_on_event)


# ── API Key Auth (optional) ──────────────────────────────────────────────────


def verify_api_key(auth: str | None = None) -> None:
    cfg = get_config()
    key = cfg.server.api_key
    if not key:
        return
    if not hmac.compare_digest(auth or "", key):
        raise HTTPException(status_code=403, detail="Invalid API key")
