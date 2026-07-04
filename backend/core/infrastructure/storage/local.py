from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

from core.application.interfaces.services import StorageBackend


class LocalStorage(StorageBackend):
    """Local filesystem implementation of StorageBackend ABC.

    Stores files under a configurable root directory, mirroring the
    logical path structure on disk. Suitable for single-server deployments
    and development; swap for S3/GCS in production clusters.
    """

    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        """Resolve a logical path to an absolute filesystem path, preventing escapes."""
        resolved = (self._root / path).resolve()
        if not str(resolved).startswith(str(self._root)):
            raise ValueError(f"Path escapes storage root: {path}")
        return resolved

    async def save(
        self,
        content: bytes,
        path: str,
        *,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

        if metadata:
            meta_path = target.with_suffix(target.suffix + ".meta")
            lines = []
            if content_type:
                lines.append(f"content-type={content_type}")
            for key, value in metadata.items():
                lines.append(f"{key}={value}")
            meta_path.write_text("\n".join(lines), encoding="utf-8")

        return path

    async def retrieve(self, path: str) -> bytes:
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found in storage: {path}")
        return target.read_bytes()

    async def delete(self, path: str) -> bool:
        target = self._resolve(path)
        if not target.exists():
            return False
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
            meta = target.with_suffix(target.suffix + ".meta")
            if meta.exists():
                meta.unlink()
        return True

    async def list(
        self,
        prefix: str = "",
        *,
        limit: int = 1000,
    ) -> Sequence[str]:
        base = self._resolve(prefix) if prefix else self._root
        if not base.exists():
            return []
        results: list[str] = []
        for entry in sorted(base.rglob("*")):
            if entry.is_file() and not entry.suffix == ".meta":
                rel = entry.relative_to(self._root)
                results.append(str(rel))
                if len(results) >= limit:
                    break
        return results

    async def get_url(self, path: str, *, expires_in: int = 3600) -> str:
        """Generate a pre-signed-style URL.

        For local storage this is a file:// URL with an expiry token
        embedded in the query string.  A real implementation would use
        signed tokens or reverse-proxy X-Accel-Redirect headers.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found in storage: {path}")

        expiry_ts = int(
            (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp()
        )
        payload = f"{path}:{expiry_ts}"
        token = hashlib.sha256(payload.encode()).hexdigest()[:32]
        encoded_path = quote(str(target))
        return f"file://{encoded_path}?expires={expiry_ts}&token={token}"

    async def exists(self, path: str) -> bool:
        return self._resolve(path).exists()
