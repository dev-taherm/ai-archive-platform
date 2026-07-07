"""Tests for edge_agent.core.scanner — FileScanner."""
import os
import tempfile
from pathlib import Path

import pytest

from edge_agent.core.scanner import DEFAULT_IGNORE_PATTERNS, FileScanner


@pytest.fixture
def scanner():
    return FileScanner(max_file_size_mb=10)


@pytest.fixture
def scan_dir(tmp_path):
    """Create a temp directory with sample files."""
    (tmp_path / "doc.txt").write_text("hello world")
    (tmp_path / "data.csv").write_text("a,b,c\n1,2,3")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.md").write_text("# Nested")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("git stuff")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cache.pyc").write_bytes(b"\x00")
    (tmp_path / "large.bin").write_bytes(b"x" * (11 * 1024 * 1024))  # 11MB
    (tmp_path / "empty.txt").write_text("")
    return tmp_path


class TestFileScannerFingerprint:
    def test_compute_fingerprint(self, scanner, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        fp = scanner.compute_fingerprint(str(f))
        assert fp["content_hash"].startswith("sha256:")
        assert fp["mime_type"] == "text/plain"
        assert fp["magic_bytes"]

    def test_deterministic_fingerprint(self, scanner, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        fp1 = scanner.compute_fingerprint(str(f))
        fp2 = scanner.compute_fingerprint(str(f))
        assert fp1["content_hash"] == fp2["content_hash"]


class TestFileScannerScanFolder:
    def test_scan_folder_finds_files(self, scanner, scan_dir):
        results = list(scanner.scan_folder(str(scan_dir)))
        filenames = [r["filename"] for r in results]
        assert "doc.txt" in filenames
        assert "data.csv" in filenames
        assert "nested.md" in filenames

    def test_scan_ignores_git(self, scanner, scan_dir):
        results = list(scanner.scan_folder(str(scan_dir)))
        filenames = [r["filename"] for r in results]
        assert "config" not in filenames  # .git/config ignored

    def test_scan_ignores_pycache(self, scanner, scan_dir):
        results = list(scanner.scan_folder(str(scan_dir)))
        filenames = [r["filename"] for r in results]
        assert "cache.pyc" not in filenames

    def test_scan_ignores_large_files(self, scanner, scan_dir):
        results = list(scanner.scan_folder(str(scan_dir)))
        filenames = [r["filename"] for r in results]
        assert "large.bin" not in filenames

    def test_scan_ignores_empty_files(self, scanner, scan_dir):
        results = list(scanner.scan_folder(str(scan_dir)))
        filenames = [r["filename"] for r in results]
        assert "empty.txt" not in filenames

    def test_scan_nonexistent_dir(self, scanner):
        results = list(scanner.scan_folder("/nonexistent/path/12345"))
        assert results == []

    def test_scan_not_a_dir(self, scanner, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        results = list(scanner.scan_folder(str(f)))
        assert results == []

    def test_scan_non_recursive(self, scanner, scan_dir):
        results = list(scanner.scan_folder(str(scan_dir), recursive=False))
        filenames = [r["filename"] for r in results]
        assert "nested.md" not in filenames

    def test_scan_with_patterns(self, scanner, scan_dir):
        results = list(scanner.scan_folder(str(scan_dir), patterns=["*.txt"]))
        filenames = [r["filename"] for r in results]
        assert "doc.txt" in filenames
        assert "data.csv" not in filenames

    def test_result_fields(self, scanner, scan_dir):
        results = list(scanner.scan_folder(str(scan_dir)))
        r = results[0]
        assert "path" in r
        assert "content_hash" in r
        assert "mime_type" in r
        assert "size_bytes" in r
        assert r["is_file"] is True


class TestFileScannerScanSingle:
    def test_scan_single(self, scanner, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = scanner.scan_single(str(f))
        assert result is not None
        assert result["filename"] == "test.txt"

    def test_scan_single_nonexistent(self, scanner):
        result = scanner.scan_single("/nonexistent/file.txt")
        assert result is None

    def test_scan_single_empty(self, scanner, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = scanner.scan_single(str(f))
        assert result is None

    def test_scan_single_too_large(self, scanner, tmp_path):
        f = tmp_path / "big.bin"
        f.write_bytes(b"x" * (11 * 1024 * 1024))
        result = scanner.scan_single(str(f))
        assert result is None
