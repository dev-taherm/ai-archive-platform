"""SaaS sync engine — registration, heartbeat, file sync with retry."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class SyncEngine:
    def __init__(self, db: Any, config: Any, metrics: Any | None = None) -> None:
        self.db = db
        self._config = config
        self._metrics = metrics
        self._http_timeout = 30

    # ── Credentials ──────────────────────────────────────────────────────────

    def get_credentials(self) -> dict[str, str]:
        cfg = self.db.get_config()
        return {
            "server_url": cfg.get("server_url", ""),
            "agent_id": cfg.get("agent_id", ""),
            "api_key": cfg.get("api_key", ""),
        }

    # ── Registration ─────────────────────────────────────────────────────────

    def register(self, server_url: str, access_token: str) -> dict[str, Any]:
        hostname = os.uname().nodename if hasattr(os, "uname") else "unknown"
        url = f"{server_url.rstrip('/')}/api/v1/agents/auto-register"
        body = json.dumps({
            "hostname": hostname,
            "platform": sys.platform,
            "agent_version": self._config.agent_version,
        }).encode()

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._http_timeout) as resp:
                result = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            logger.error("Registration failed (%s): %s", e.code, body)
            raise RuntimeError(f"Registration returned {e.code}: {body}") from e
        except urllib.error.URLError as e:
            logger.error("Registration connection failed: %s", e)
            raise RuntimeError(f"Registration failed: {e}") from e

        self.db.set_config("server_url", server_url)
        self.db.set_config("agent_id", result["agent_id"])
        self.db.set_config("api_key", result["api_key"])
        if result.get("frontend_url"):
            self.db.set_config("frontend_url", result["frontend_url"])
        logger.info("Registered agent %s at %s", result["agent_id"], server_url)
        return result

    # ── Heartbeat ────────────────────────────────────────────────────────────

    def heartbeat(self) -> dict[str, Any]:
        creds = self.get_credentials()
        if not all(creds.values()):
            return {"status": "skipped", "reason": "not registered"}

        url = f"{creds['server_url'].rstrip('/')}/api/v1/agents/{creds['agent_id']}/heartbeat"

        # Count completed files
        completed = self.db.conn.execute(
            "SELECT COUNT(*) FROM files WHERE processing_status='completed'"
        ).fetchone()[0]

        body = json.dumps({"status": "online", "files_count": completed}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": creds["api_key"],
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._http_timeout) as resp:
                result = json.loads(resp.read().decode())
                if self._metrics:
                    self._metrics.heartbeat_count += 1
                return result
        except urllib.error.HTTPError as e:
            logger.warning("Heartbeat failed (%s): %s", e.code, e.read().decode()[:200])
            return {"status": "error", "code": e.code}
        except urllib.error.URLError as e:
            logger.warning("Heartbeat connection failed: %s", e)
            return {"status": "error", "reason": str(e)}

    # ── File Sync ────────────────────────────────────────────────────────────

    def sync_files(self, limit: int = 50) -> dict[str, Any]:
        creds = self.get_credentials()
        if not all(creds.values()):
            return {"status": "skipped", "reason": "not registered"}

        pending = self.db.get_pending_sync(limit=limit)
        if not pending:
            return {"status": "ok", "synced": 0, "message": "Nothing to sync"}

        files_payload = []
        for f in pending:
            if not (f.get("extracted_text") or f.get("markdown")):
                logger.warning(
                    "Skipping sync for %s: extracted_text and markdown are both empty",
                    f.get("local_path"),
                )
                continue
            entry = {
                "local_path": f["local_path"],
                "file_hash": f["file_hash"],
                "file_size": f["size_bytes"],
                "mime_type": f["mime_type"],
                "modified_at": f["modified_at"],
                "extracted_text": f["extracted_text"],
                "markdown": f["markdown"],
                "language": f["language"],
                "word_count": f["word_count"],
                "char_count": f["char_count"],
                "page_count": f["page_count"],
            }
            for key in ("content_blocks", "tables", "images"):
                val = f.get(key, "[]")
                if isinstance(val, str):
                    try:
                        entry[key] = json.loads(val)
                    except json.JSONDecodeError:
                        entry[key] = []
                else:
                    entry[key] = val
            files_payload.append(entry)

        if not files_payload:
            return {"status": "ok", "synced": 0, "message": "All files skipped (empty text)"}

        url = f"{creds['server_url'].rstrip('/')}/api/v1/agents/{creds['agent_id']}/sync"
        body = json.dumps({"files": files_payload}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": creds["api_key"],
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                sync_result = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            logger.error("Sync failed (%s): %s", e.code, body[:500])
            raise RuntimeError(f"Sync returned {e.code}: {body}") from e
        except urllib.error.URLError as e:
            logger.error("Sync connection failed: %s", e)
            raise RuntimeError(f"Sync failed: {e}") from e

        synced_hashes = [e["file_hash"] for e in files_payload if e.get("file_hash")]
        if synced_hashes:
            self.db.mark_synced(synced_hashes)

        if self._metrics:
            self._metrics.sync_events += 1
            self._metrics.sync_files += len(synced_hashes)

        logger.info("Synced %d files to %s", len(synced_hashes), creds["server_url"])
        return {
            "status": "ok",
            "synced": len(synced_hashes),
            "saas_result": sync_result,
        }
