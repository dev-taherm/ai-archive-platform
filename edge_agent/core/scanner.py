from __future__ import annotations

import hashlib
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _generate_id() -> str:
    return str(uuid.uuid4())


def compute_fingerprint(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _detect_mime(filepath: str) -> str:
    mime, _ = mimetypes.guess_type(filepath)
    return mime or "application/octet-stream"


def scan_single(filepath: str) -> dict | None:
    try:
        st = os.stat(filepath)
        if not os.path.isfile(filepath):
            return None
        name = os.path.basename(filepath)
        return {
            "id": _generate_id(),
            "local_path": filepath,
            "filename": name,
            "extension": os.path.splitext(name)[1].lower(),
            "file_hash": compute_fingerprint(filepath),
            "size_bytes": st.st_size,
            "mime_type": _detect_mime(filepath),
            "modified_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        }
    except (PermissionError, OSError):
        return None


def scan_folder(path: str) -> list[dict]:
    entries: list[dict] = []
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if fname.startswith("."):
                continue
            fpath = os.path.join(root, fname)
            meta = scan_single(fpath)
            if meta:
                entries.append(meta)
    return entries
