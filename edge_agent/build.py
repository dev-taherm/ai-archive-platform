#!/usr/bin/env python3
"""Build edge-agent binary using PyInstaller for the current platform.

Usage:
    python edge_agent/build.py

Output:
    backend/media/agents/binaries/edge-agent-{platform}-{arch}
    desktop/src-tauri/binaries/edge-agent-{triple}
    Both directories get manifest.json
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
TAURI_BINARIES_DIR = REPO_ROOT / "desktop" / "src-tauri" / "binaries"
TAURI_BUNDLE_DIR = REPO_ROOT / "desktop" / "src-tauri" / "target" / "release" / "bundle"
DESKTOP_DIR = REPO_ROOT / "backend" / "media" / "desktop"


def get_platform_key() -> str:
    """Return a platform key like 'linux-x86_64', 'darwin-arm64', etc."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if machine in ("x86_64", "amd64"):
        machine = "x86_64"
    elif machine in ("arm64", "aarch64"):
        machine = "arm64"
    elif machine in ("i386", "i686", "x86"):
        machine = "x86_64"

    return f"{system}-{machine}"


def get_target_triple() -> str:
    """Map platform to Rust target triple for Tauri sidecar naming."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    arch_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
    }
    arch = arch_map.get(machine, machine)

    os_map = {
        "linux": "unknown-linux-gnu",
        "darwin": "apple-darwin",
        "windows": "pc-windows-msvc",
    }
    os_part = os_map.get(system, "unknown-linux-gnu")

    return f"{arch}-{os_part}"


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

    binary_name = "edge-agent.exe" if platform.system() == "Windows" else "edge-agent"
    binary_path = DIST_DIR / binary_name
    if not binary_path.exists():
        for p in DIST_DIR.rglob(binary_name):
            binary_path = p
            break
        else:
            print(f"ERROR: Binary not found at {binary_path}")
            sys.exit(1)

    print(f"Built: {binary_path} ({binary_path.stat().st_size:,} bytes)")
    return binary_path


def copy_to_legacy(binary_path: Path) -> Path:
    """Copy binary to backend/media/agents/binaries/ with platform naming."""
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)

    dest_name = get_binary_name()
    dest = BINARIES_DIR / dest_name
    shutil.copy2(binary_path, dest)
    dest.chmod(0o755)

    print(f"Copied to legacy: {dest}")
    return dest


def copy_to_tauri(binary_path: Path) -> Path:
    """Copy binary to desktop/src-tauri/binaries/ with Tauri triple naming."""
    TAURI_BINARIES_DIR.mkdir(parents=True, exist_ok=True)

    triple = get_target_triple()
    suffix = ".exe" if platform.system() == "Windows" else ""
    dest_name = f"edge-agent-{triple}{suffix}"
    dest = TAURI_BINARIES_DIR / dest_name
    shutil.copy2(binary_path, dest)
    dest.chmod(0o755)

    print(f"Copied to Tauri: {dest}")
    return dest


def update_manifest(binary_path: Path, dest_dir: Path) -> None:
    """Update or create manifest.json in the given directory."""
    manifest_path = dest_dir / "manifest.json"

    manifest = {"version": "0.1.0", "builds": {}}
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)

    platform_key = get_platform_key()
    triple = get_target_triple()
    stat = binary_path.stat()

    manifest["builds"][platform_key] = {
        "filename": binary_path.name,
        "triple": triple,
        "size_bytes": stat.st_size,
        "sha256": sha256_file(binary_path),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest updated: {manifest_path}")


def copy_desktop_artifacts() -> list[Path]:
    """Copy Tauri build artifacts (.deb, .rpm, .AppImage, .dmg, .msi) to backend/media/desktop/."""
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

    copied = []
    extensions = {
        "deb": TAURI_BUNDLE_DIR / "deb",
        "rpm": TAURI_BUNDLE_DIR / "rpm",
        "appimage": TAURI_BUNDLE_DIR / "appimage",
        "dmg": TAURI_BUNDLE_DIR / "dmg",
        "msi": TAURI_BUNDLE_DIR / "nsis",
    }

    for ext, bundle_dir in extensions.items():
        if not bundle_dir.exists():
            continue
        for artifact in bundle_dir.iterdir():
            if artifact.is_file() and artifact.suffix == f".{ext}":
                dest = DESKTOP_DIR / artifact.name
                shutil.copy2(artifact, dest)
                print(f"Copied desktop: {dest}")
                copied.append(dest)

    return copied


def update_desktop_manifest(artifacts: list[Path]) -> None:
    """Update or create desktop-manifest.json in backend/media/desktop/."""
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = DESKTOP_DIR / "desktop-manifest.json"

    manifest = {"version": "0.1.0", "builds": {}}
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)

    platform_key = get_platform_key()

    for artifact in artifacts:
        suffix = artifact.suffix
        if suffix == ".deb":
            build_key = platform_key
        elif suffix == ".rpm":
            build_key = f"{platform_key}-rpm"
        elif suffix == ".AppImage":
            build_key = f"{platform_key}-appimage"
        elif suffix == ".dmg":
            build_key = f"{platform_key}-dmg"
        elif suffix == ".msi":
            build_key = f"{platform_key}-msi"
        else:
            continue

        stat = artifact.stat()
        manifest["builds"][build_key] = {
            "filename": artifact.name,
            "size_bytes": stat.st_size,
            "sha256": sha256_file(artifact),
            "built_at": datetime.now(timezone.utc).isoformat(),
        }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Desktop manifest updated: {manifest_path}")


def main() -> None:
    if not SPEC_FILE.exists():
        print(f"ERROR: PyInstaller spec file not found at {SPEC_FILE}")
        sys.exit(1)

    binary_path = build_binary()
    copy_to_legacy(binary_path)
    tauri_dest = copy_to_tauri(binary_path)

    # Update manifests in both locations
    update_manifest(binary_path, BINARIES_DIR)
    update_manifest(binary_path, TAURI_BINARIES_DIR)

    # Copy desktop app artifacts
    desktop_artifacts = copy_desktop_artifacts()
    if desktop_artifacts:
        update_desktop_manifest(desktop_artifacts)

    triple = get_target_triple()
    print(f"\nDone! Built for {get_platform_key()} ({triple})")
    print(f"  Legacy: {BINARIES_DIR / get_binary_name()}")
    print(f"  Tauri:  {tauri_dest}")
    if desktop_artifacts:
        print(f"  Desktop: {DESKTOP_DIR}")


if __name__ == "__main__":
    main()
