from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

from edge_agent.core.event_bus import (
    EVENT_SCAN_COMPLETED,
    EVENT_SCAN_FAILED,
    EVENT_SCAN_STARTED,
    EVENT_STATUS_CHANGED,
)
from edge_agent.core.job_queue import JobQueue
from edge_agent.db.local_db import LocalDB
from edge_agent.ocr.fallback import ocr_fallback, _MIN_TEXT_LENGTH

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 300  # how often to run recurring sync tasks


class Worker:
    def __init__(
        self,
        db: LocalDB,
        sync_engine: Any | None = None,
        metrics: Any | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self.db = db
        self.sync_engine = sync_engine
        self._metrics = metrics
        self._event_bus = event_bus
        self.queue = JobQueue(db)
        self._running = False
        self._paused = False
        self._thread: threading.Thread | None = None
        self._last_sync: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def processing_count(self) -> int:
        return len([j for j in self.queue.list_jobs(status="running", limit=100)])

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._paused = False
        self._recover_stale_jobs()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="worker")
        self._thread.start()
        logger.info("Worker started")

    def stop(self) -> None:
        self._running = False
        self._paused = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Worker stopped")

    def pause(self) -> None:
        self._paused = True
        self._publish_event({"type": EVENT_STATUS_CHANGED, "paused": True})
        logger.info("Worker paused")

    def resume(self) -> None:
        self._paused = False
        self._publish_event({"type": EVENT_STATUS_CHANGED, "paused": False})
        logger.info("Worker resumed")

    def restart(self) -> None:
        logger.info("Worker restarting")
        self.stop()
        self.start()

    # ── Command handler (called by WS client) ────────────────────────────────

    def handle_command(self, command_type: str, payload: dict[str, Any]) -> None:
        """Handle a command received from the SaaS backend via WebSocket."""
        logger.info("Handling command: %s", command_type)
        try:
            if command_type == "restart":
                self.restart()
            elif command_type == "shutdown":
                self._running = False
                self._paused = False
                logger.info("Shutdown command received")
            elif command_type == "start_scan":
                self.resume()
            elif command_type == "stop_scan":
                self.pause()
            else:
                logger.warning("Unknown command type: %s", command_type)
        except Exception:
            logger.exception("Failed to handle command: %s", command_type)

    # ── Event publishing helper ───────────────────────────────────────────────

    def _publish_event(self, event: dict[str, Any]) -> None:
        """Publish an event to the EventBus (safe to call from any thread)."""
        if self._event_bus:
            try:
                self._event_bus.publish(event)
            except Exception:
                logger.exception("Failed to publish event")

    # ── Stale job recovery ────────────────────────────────────────────────────

    def _recover_stale_jobs(self) -> None:
        try:
            stale = self.queue.list_jobs(status="running", limit=50)
            for job in stale:
                self.queue.fail_job(job["id"], "Worker restarted — job interrupted")
                logger.warning("Recovered stale job %s (%s)", job["id"], job.get("type"))
            if stale:
                logger.info("Recovered %d stale jobs", len(stale))
        except Exception:
            logger.exception("Failed to recover stale jobs")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                if self._paused:
                    time.sleep(1)
                    continue
                pending = self.queue.list_jobs(status="pending", limit=10)
                for job in pending:
                    if not self._running:
                        break
                    self._process_job(job)
            except Exception:
                logger.exception("Worker loop error")

            if self.sync_engine:
                self._run_recurring_tasks()

            time.sleep(1)

    def _run_recurring_tasks(self) -> None:
        now = time.time()
        if now - self._last_sync >= SYNC_INTERVAL_SECONDS:
            try:
                self.sync_engine.sync_files()
            except Exception:
                logger.exception("Sync failed")
            self._last_sync = now

    # ── Job processing ────────────────────────────────────────────────────────

    def _process_job(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        job_type = job["type"]
        payload = job.get("payload", {})
        try:
            self.queue.start_job(job_id)
            logger.info("Processing job %s (%s)", job_id, job_type)

            self._publish_event({
                "type": EVENT_SCAN_STARTED,
                "job_id": job_id,
                "file_id": payload.get("file_id"),
            })

            if job_type == "scan_file":
                self._execute_scan(job_id, payload)
                self._publish_event({
                    "type": EVENT_SCAN_COMPLETED,
                    "job_id": job_id,
                    "file_id": payload.get("file_id"),
                })
            else:
                self.queue.fail_job(job_id, f"Unknown job type: {job_type}")
        except Exception as e:
            logger.exception("Job %s failed", job_id)
            try:
                self.db.mark_file_failed(payload.get("file_id", ""))
                self.queue.fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job %s as failed", job_id)
            if self._metrics:
                self._metrics.increment_errors()
            self._publish_event({
                "type": EVENT_SCAN_FAILED,
                "job_id": job_id,
                "file_id": payload.get("file_id"),
                "error": str(e),
            })

    def _execute_scan(self, job_id: str, payload: dict[str, Any]) -> None:
        from edge_agent.parsers.router import ParserRouter
        from edge_agent.ocr.engine import OCREngine
        from edge_agent.api.server import get_config

        file_id = payload["file_id"]
        record = self.db.get_file_by_id(file_id)
        if record is None:
            raise ValueError(f"File not found: {file_id}")

        file_path = record["local_path"]
        path_obj = Path(file_path)

        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        cfg = get_config()
        parser = ParserRouter()
        ocr = OCREngine(lang=cfg.ocr.lang, use_gpu=cfg.ocr.use_gpu)

        t0 = time.time()
        parsed = parser.parse(file_path)
        parse_time_ms = (time.time() - t0) * 1000
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', parsed.markdown or "")

        if self._metrics:
            self._metrics.increment_scanned()
            self._metrics.add_parse_time(parse_time_ms)
        text, ocr_used = ocr_fallback(text, path_obj, ocr)

        content_blocks = json.dumps(
            [b.to_dict() for b in parsed.content_blocks]
        )
        tables = json.dumps(
            [t.to_dict() for t in parsed.tables]
        )
        images = json.dumps(
            [i.to_dict() for i in parsed.images]
        )
        language = getattr(parsed, "language", "unknown")
        word_count = parsed.word_count
        char_count = parsed.char_count
        page_count = parsed.page_count

        self.db.update_file_after_scan(
            file_id,
            markdown=text,
            content_blocks=content_blocks,
            tables=tables,
            images=images,
            language=language,
            word_count=word_count,
            char_count=char_count,
            page_count=page_count,
            ocr_used=ocr_used,
            parse_method=getattr(parsed, "parse_method", ""),
            parse_time_ms=getattr(parsed, "parse_time_ms", 0.0),
        )

        self.queue.complete_job(job_id, {
            "file_id": file_id,
            "ocr_used": ocr_used,
            "word_count": word_count,
        })
        logger.info("Job %s completed: %s", job_id, file_id)
