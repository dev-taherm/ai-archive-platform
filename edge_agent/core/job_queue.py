from __future__ import annotations

import json
from typing import Any

from edge_agent.db.local_db import LocalDB


class JobQueue:
    """Lightweight SQLite-backed job queue.

    Phase 1: jobs are executed synchronously after creation.
    Phase 2: a background worker picks up pending jobs asynchronously.
    """

    def __init__(self, db: LocalDB) -> None:
        self.db = db

    def create_job(self, job_type: str, payload: dict[str, Any] | None = None) -> str:
        return self.db.create_job(job_type, payload)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self.db.get_job(job_id)

    def list_jobs(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        return self.db.list_jobs(status, limit)

    def start_job(self, job_id: str) -> None:
        from datetime import datetime, timezone
        self.db.update_job(
            job_id, status="running", started_at=datetime.now(timezone.utc).isoformat()
        )

    def complete_job(self, job_id: str, result: Any = None) -> None:
        from datetime import datetime, timezone
        self.db.update_job(
            job_id,
            status="completed",
            result=json.dumps(result) if result is not None else None,
            progress=1.0,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    def fail_job(self, job_id: str, error: str) -> None:
        from datetime import datetime, timezone
        self.db.update_job(
            job_id,
            status="failed",
            error=error,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
