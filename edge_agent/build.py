#!/usr/bin/env python3
"""Build edge-agent binary using PyInstaller for the current platform.

Usage:
    python edge_agent/build.py

Output:
    backend/media/agents/binaries/edge-agent-{platform}-{arch}
    backend/media/agents/binaries/manifest.json
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EDGE_AGENT_DIR = REPO_ROOT / "edge_agent"
SPEC_FILE = REPO_ROOT / "edge-agent.spec"
DIST_DIR = REPO_ROOT / "edge_agent" / "dist"
BINARIES_DIR = REPO_ROOT / "backend" / "media" / "agents" / "binaries"


def get_platform_key() -> str:
    """Return a platform key like 'linux-x86_64', 'darwin-arm64', etc."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize machine names
    if machine in ("x86_64", "amd64"):
        machine = "x86_64"
    elif machine in ("arm64", "aarch64"):
        machine = "arm64"
    elif machine in ("i386", "i686", "x86"):
        machine = "x86_64"  # treat 32-bit as 64-bit for simplicity

    return f"{system}-{machine}"


def get_binary_name() -> str:
    """Return the binary filename for the current platform."""
    platform_key = get_platform_key()
    suffix = ".exe" if platform_key.startswith("win") else ""
    return f"edge-agent-{platform_key}{suffix}"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_binary() -> Path:
    """Build the edge-agent binary using PyInstaller."""
    print(f"Building edge-agent for {get_platform_key()}...")

    # Clean previous build artifacts
    for d in [REPO_ROOT / "build", DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath", str(DIST_DIR),
        "--workpath", str(REPO_ROOT / "build"),
        str(SPEC_FILE),
    ]

    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        sys.exit(1)

    # Find the built binary
    binary_name = "edge-agent.exe" if platform.system() == "Windows" else "edge-agent"
    binary_path = DIST_DIR / binary_name
    if not binary_path.exists():
        # Try nested directory (PyInstaller sometimes puts it in a subfolder)
        for p in DIST_DIR.rglob(binary_name):
            binary_path = p
            break
        else:
            print(f"ERROR: Binary not found at {binary_path}")
            sys.exit(1)

    print(f"Built: {binary_path} ({binary_path.stat().st_size:,} bytes)")
    return binary_path


def copy_binary(binary_path: Path) -> Path:
    """Copy the binary to the media directory with a platform-specific name."""
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)

    dest_name = get_binary_name()
    dest = BINARIES_DIR / dest_name
    shutil.copy2(binary_path, dest)
    dest.chmod(0o755)

    print(f"Copied to: {dest}")
    return dest


def update_manifest(binary_path: Path) -> None:
    """Update or create the manifest.json file."""
    manifest_path = BINARIES_DIR / "manifest.json"

    # Load existing manifest or create new
    manifest = {"version": "0.1.0", "builds": {}}
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)

    platform_key = get_platform_key()
    stat = binary_path.stat()

    manifest["builds"][platform_key] = {
        "filename": binary_path.name,
        "size_bytes": stat.st_size,
        "sha256": sha256_file(binary_path),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest updated: {manifest_path}")


def main() -> None:
    if not SPEC_FILE.exists():
        print(f"ERROR: PyInstaller spec file not found at {SPEC_FILE}")
        sys.exit(1)

    binary_path = build_binary()
    dest = copy_binary(binary_path)
    update_manifest(dest)

    print(f"\nDone! Binary available at: {dest}")
    print(f"Platform: {get_platform_key()}")


if __name__ == "__main__":
    main()
