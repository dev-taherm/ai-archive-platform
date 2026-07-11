"""Tests for edge_agent.core.scanner — file scanning and fingerprinting."""
import os
import tempfile
from pathlib import Path

import pytest

from edge_agent.core.scanner import compute_fingerprint, scan_folder, scan_single


class TestScanSingle:
    def test_text_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        meta = scan_single(str(f))
        assert meta is not None
        assert meta["filename"] == "test.txt"
        assert meta["extension"] == ".txt"
        assert meta["size_bytes"] == 11
        assert meta["mime_type"] == "text/plain"
        assert meta["file_hash"] == compute_fingerprint(str(f))
        assert "local_path" in meta

    def test_nonexistent_file(self):
        meta = scan_single("/nonexistent/file.txt")
        assert meta is None

    def test_permission_error(self, tmp_path):
        f = tmp_path / "restricted.bin"
        f.write_text("data")
        os.chmod(str(f), 0o000)
        try:
            meta = scan_single(str(f))
            assert meta is None
        finally:
            os.chmod(str(f), 0o644)

    def test_binary_file(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")
        meta = scan_single(str(f))
        assert meta is not None
        assert meta["extension"] == ".bin"

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        meta = scan_single(str(f))
        assert meta is not None
        assert meta["size_bytes"] == 0
        assert meta["file_hash"] == compute_fingerprint(str(f))


class TestComputeFingerprint:
    def test_same_content_same_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("same content")
        b.write_text("same content")
        assert compute_fingerprint(str(a)) == compute_fingerprint(str(b))

    def test_different_content_different_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("content a")
        b.write_text("content b")
        assert compute_fingerprint(str(a)) != compute_fingerprint(str(b))

    def test_empty_file_hash(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        h = compute_fingerprint(str(f))
        assert isinstance(h, str) and len(h) == 64

    def test_large_file_hash(self, tmp_path):
        f = tmp_path / "large.bin"
        f.write_bytes(b"x" * 1024 * 1024)
        h = compute_fingerprint(str(f))
        assert isinstance(h, str) and len(h) == 64


class TestScanFolder:
    def test_empty_folder(self, tmp_path):
        files = scan_folder(str(tmp_path))
        assert files == []

    def test_single_file(self, tmp_path):
        (tmp_path / "doc.txt").write_text("hello")
        files = scan_folder(str(tmp_path))
        assert len(files) == 1
        assert files[0]["filename"] == "doc.txt"

    def test_multiple_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("aaa")
        (tmp_path / "b.md").write_text("bbb")
        (tmp_path / "c.py").write_text("ccc")
        files = scan_folder(str(tmp_path))
        assert len(files) == 3

    def test_nested_directories(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.txt").write_text("nested")
        (tmp_path / "root.txt").write_text("root")
        files = scan_folder(str(tmp_path))
        assert len(files) == 2

    def test_hidden_files_skipped(self, tmp_path):
        (tmp_path / "visible.txt").write_text("visible")
        (tmp_path / ".hidden").write_text("hidden")
        files = scan_folder(str(tmp_path))
        assert len(files) == 1

    def test_nonexistent_directory(self):
        files = scan_folder("/nonexistent/path")
        assert files == []

    def test_file_instead_of_directory(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("data")
        files = scan_folder(str(f))
        assert files == []
