from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

from edge_agent.core.job_queue import JobQueue
from edge_agent.db.local_db import LocalDB

logger = logging.getLogger(__name__)


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
        self._events: dict[str, threading.Event] = {}
        self._last_heartbeat: float = 0.0
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
        logger.info("Worker paused")

    def resume(self) -> None:
        self._paused = False
        logger.info("Worker resumed")

    def restart(self) -> None:
        logger.info("Worker restarting")
        self.stop()
        self.start()

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

    def wait_for_job(self, job_id: str, timeout: float = 300.0) -> dict[str, Any] | None:
        ev = threading.Event()
        self._events[job_id] = ev
        ev.wait(timeout=timeout)
        self._events.pop(job_id, None)
        return self.queue.get_job(job_id)

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
        if now - self._last_heartbeat >= 60:
            try:
                self.sync_engine.heartbeat()
            except Exception:
                logger.exception("Heartbeat failed")
            self._last_heartbeat = now

        if now - self._last_sync >= 300:
            try:
                self.sync_engine.sync_files()
            except Exception:
                logger.exception("Sync failed")
            self._last_sync = now

    def _process_job(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        job_type = job["type"]
        payload = job.get("payload", {})
        try:
            self.queue.start_job(job_id)
            logger.info("Processing job %s (%s)", job_id, job_type)

            if self._event_bus:
                self._event_bus.publish({
                    "type": "scan_started",
                    "job_id": job_id,
                    "file_id": payload.get("file_id"),
                })

            if job_type == "scan_file":
                self._execute_scan(job_id, payload)
                if self._event_bus:
                    self._event_bus.publish({
                        "type": "scan_completed",
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
                self._metrics.parse_errors += 1
            if self._event_bus:
                try:
                    self._event_bus.publish({
                        "type": "scan_failed",
                        "job_id": job_id,
                        "file_id": payload.get("file_id"),
                        "error": str(e),
                    })
                except Exception:
                    logger.exception("Failed to publish scan_failed event")
        finally:
            ev = self._events.pop(job_id, None)
            if ev:
                ev.set()

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
            self._metrics.files_scanned += 1
            self._metrics.parse_time_total_ms += parse_time_ms
        ocr_used = False

        if not text or len(text.strip()) < 50:
            suffix = path_obj.suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp", ".pdf"):
                content = path_obj.read_bytes()
                ocr_text = ocr.extract_text(content, content_type="application/octet-stream")
                if ocr_text and len(ocr_text) > len(text):
                    text = ocr_text
                    ocr_used = True

        content_blocks = json.dumps(
            [b.to_dict() if hasattr(b, "to_dict") else vars(b) for b in parsed.content_blocks]
        )
        tables = json.dumps(
            [t.to_dict() if hasattr(t, "to_dict") else vars(t) for t in parsed.tables]
        )
        images = json.dumps(
            [i.to_dict() if hasattr(i, "to_dict") else vars(i) for i in parsed.images]
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
