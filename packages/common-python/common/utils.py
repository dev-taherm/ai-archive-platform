"""Shared utilities for fingerprint computation and MIME detection."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path


def compute_file_hash(filepath: str | Path, algorithm: str = "sha256") -> str:
    """Compute a content hash for a file.

    Returns a string in the format ``algorithm:hexdigest``
    (e.g. ``sha256:abc123...``).
    """
    path = Path(filepath)
    h = hashlib.new(algorithm)
    h.update(path.read_bytes())
    return f"{algorithm}:{h.hexdigest()}"


def guess_mime_type(filepath: str | Path) -> str:
    """Guess the MIME type of a file from its extension."""
    mime, _ = mimetypes.guess_type(str(filepath))
    return mime or "application/octet-stream"


def read_magic_bytes(filepath: str | Path, n: int = 8) -> str:
    """Read the first *n* bytes of a file as a hex string (magic bytes)."""
    path = Path(filepath)
    return path.read_bytes()[:n].hex()
