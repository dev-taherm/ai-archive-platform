"""SaaS sync engine — registration, heartbeat, file sync with retry."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _to_epoch(value: Any) -> float:
    """Convert a value to Unix epoch float. Backend expects FloatField."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value)
            return dt.timestamp()
        except (ValueError, TypeError):
            pass
    return 0.0


_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _sanitize_text(value: Any) -> str:
    """Strip control characters that PostgreSQL rejects in text/jsonb columns."""
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="replace")
        except Exception:
            return ""
    if not isinstance(value, str):
        return str(value) if value else ""
    return _CONTROL_CHARS_RE.sub('', value)


def _sanitize_json_recursive(obj: Any) -> Any:
    """Recursively sanitize control chars in all strings within a JSON-like structure."""
    if isinstance(obj, bytes):
        try:
            obj = obj.decode("utf-8", errors="replace")
        except Exception:
            return ""
    if isinstance(obj, str):
        return _CONTROL_CHARS_RE.sub('', obj)
    if isinstance(obj, dict):
        return {k: _sanitize_json_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json_recursive(item) for item in obj]
    return obj


def build_files_payload(pending_rows: list[dict]) -> list[dict]:
    """Build the files payload array from pending database rows."""
    files_payload = []
    for f in pending_rows:
        raw_text = _sanitize_text(f.get("extracted_text") or "")
        raw_md = _sanitize_text(f.get("markdown") or "")
        if not (raw_text.strip() or raw_md.strip()):
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
            "modified_at": _to_epoch(f["modified_at"]),
            "extracted_text": raw_text,
            "markdown": raw_md,
            "language": f["language"],
            "word_count": f["word_count"],
            "char_count": f["char_count"],
            "page_count": f["page_count"],
        }
        for key in ("content_blocks", "tables", "images"):
            val = f.get(key, "[]")
            if isinstance(val, str):
                try:
                    entry[key] = _sanitize_json_recursive(json.loads(val))
                except json.JSONDecodeError:
                    entry[key] = []
            else:
                entry[key] = _sanitize_json_recursive(val)
        files_payload.append(entry)
    return files_payload


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

    # ── File Sync ────────────────────────────────────────────────────────────

    def sync_files(self, limit: int = 50) -> dict[str, Any]:
        creds = self.get_credentials()
        if not all(creds.values()):
            return {"status": "skipped", "reason": "not registered"}

        pending = self.db.get_pending_sync(limit=limit)
        if not pending:
            return {"status": "ok", "synced": 0, "message": "Nothing to sync"}

        files_payload = build_files_payload(pending)

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
            self._metrics.increment_sync_events()
            self._metrics.increment_sync_files(len(synced_hashes))

        logger.info("Synced %d files to %s", len(synced_hashes), creds["server_url"])
        return {
            "status": "ok",
            "synced": len(synced_hashes),
            "saas_result": sync_result,
        }
