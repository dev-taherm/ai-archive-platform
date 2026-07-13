"""Tests for edge_agent.core.worker — background job worker."""
import time
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.core.job_queue import JobQueue
from edge_agent.core.worker import Worker
from edge_agent.db.local_db import LocalDB


@pytest.fixture
def db(tmp_path):
    return LocalDB(str(tmp_path / "test.db"))


@pytest.fixture
def queue(db):
    return JobQueue(db)


class TestWorker:
    def test_start_stop(self, db):
        w = Worker(db)
        assert not w.is_running
        w.start()
        assert w.is_running
        w.stop()
        assert not w.is_running

    def test_double_start(self, db):
        w = Worker(db)
        w.start()
        w.start()
        w.stop()

    @patch("edge_agent.core.worker.ParserRouter")
    @patch("edge_agent.core.worker.OCREngine")
    def test_wait_for_job_completed(self, mock_ocr, mock_parser, db, tmp_path):
        from edge_agent.core.models import ParsedDocument

        mock_parser.return_value.parse.return_value = ParsedDocument(
            markdown="parsed content"
        )

        f = tmp_path / "test.txt"
        f.write_text("hello world")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "test.txt"}])

        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "file1"})
            result = w.wait_for_job(jid, timeout=10.0)
            assert result is not None
            assert result["status"] == "completed"
        finally:
            w.stop()

    def test_wait_for_job_timeout(self, db):
        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "nonexistent"})
            result = w.wait_for_job(jid, timeout=2.0)
            assert result is not None
            assert result["status"] == "failed"
        finally:
            w.stop()

    def test_unknown_job_type(self, db):
        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("unknown_type", {})
            result = w.wait_for_job(jid, timeout=5.0)
            assert result is not None
            assert result["status"] == "failed"
        finally:
            w.stop()

    def test_pause_resume(self, db):
        w = Worker(db)
        w.start()
        try:
            assert not w._paused
            w.pause()
            assert w._paused
            w.resume()
            assert not w._paused
        finally:
            w.stop()

    def test_paused_does_not_process(self, db):
        w = Worker(db)
        w.start()
        w.pause()
        try:
            jid = db.create_job("scan_file", {"file_id": "nonexistent"})
            time.sleep(2)
            job = db.get_job(jid)
            assert job["status"] == "pending"
        finally:
            w.stop()

    def test_processing_count(self, db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "test.txt"}])

        w = Worker(db)
        assert w.processing_count == 0
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "file1"})
            w.wait_for_job(jid, timeout=10.0)
        finally:
            w.stop()

    def test_restart(self, db):
        w = Worker(db)
        w.start()
        time.sleep(0.2)
        w.restart()
        assert w.is_running
        w.stop()


class TestWorkerLanguageDetection:
    @patch("edge_agent.api.server.get_config")
    @patch("edge_agent.ocr.engine.OCREngine")
    @patch("edge_agent.parsers.router.ParserRouter")
    def test_arabic_document_detected(self, mock_parser_cls, mock_ocr_cls, mock_get_config, db, tmp_path):
        from edge_agent.core.models import ParsedDocument, Language
        from edge_agent.config import EdgeAgentConfig

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ParsedDocument(
            markdown="هذه وثيقة عربية تحتوي على نص كامل يمكن كشفه"
        )
        mock_parser_cls.return_value = mock_parser

        mock_ocr = MagicMock()
        mock_ocr.detect_language.return_value = Language.AR
        mock_ocr_cls.return_value = mock_ocr

        mock_get_config.return_value = EdgeAgentConfig()

        f = tmp_path / "arabic.txt"
        f.write_text("هذه وثيقة عربية")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "arabic.txt"}])

        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "file1"})
            for _ in range(50):
                time.sleep(0.2)
                job = db.get_job(jid)
                if job and job["status"] in ("completed", "failed"):
                    break
            assert job is not None
            assert job["status"] == "completed"
            file_record = db.get_file_by_id("file1")
            assert file_record["language"] == "ar"
        finally:
            w.stop()

    @patch("edge_agent.api.server.get_config")
    @patch("edge_agent.ocr.engine.OCREngine")
    @patch("edge_agent.parsers.router.ParserRouter")
    def test_english_document_detected(self, mock_parser_cls, mock_ocr_cls, mock_get_config, db, tmp_path):
        from edge_agent.core.models import ParsedDocument, Language
        from edge_agent.config import EdgeAgentConfig

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ParsedDocument(
            markdown="This is an English document with enough text to detect the language"
        )
        mock_parser_cls.return_value = mock_parser

        mock_ocr = MagicMock()
        mock_ocr.detect_language.return_value = Language.EN
        mock_ocr_cls.return_value = mock_ocr

        mock_get_config.return_value = EdgeAgentConfig()

        f = tmp_path / "english.txt"
        f.write_text("This is an English document")
        db.upsert_files([{"id": "file2", "local_path": str(f), "filename": "english.txt"}])

        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "file2"})
            for _ in range(50):
                time.sleep(0.2)
                job = db.get_job(jid)
                if job and job["status"] in ("completed", "failed"):
                    break
            assert job is not None
            assert job["status"] == "completed"
            file_record = db.get_file_by_id("file2")
            assert file_record["language"] == "en"
        finally:
            w.stop()


class TestWorkerLanguagePassthrough:
    @patch("edge_agent.api.server.get_config")
    @patch("edge_agent.ocr.engine.OCREngine")
    @patch("edge_agent.parsers.router.ParserRouter")
    def test_parser_parse_called_during_scan(self, mock_parser_cls, mock_ocr_cls, mock_get_config, db, tmp_path):
        from edge_agent.core.models import ParsedDocument
        from edge_agent.config import EdgeAgentConfig

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ParsedDocument(markdown="hello world")
        mock_parser_cls.return_value = mock_parser

        mock_ocr = MagicMock()
        mock_ocr.detect_language.return_value = None
        mock_ocr_cls.return_value = mock_ocr

        mock_get_config.return_value = EdgeAgentConfig()

        f = tmp_path / "doc.txt"
        f.write_text("hello world")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "doc.txt"}])

        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "file1"})
            for _ in range(50):
                time.sleep(0.2)
                job = db.get_job(jid)
                if job and job["status"] in ("completed", "failed"):
                    break
            assert job is not None
            assert job["status"] == "completed"
            mock_parser.parse.assert_called_once_with(str(f))
        finally:
            w.stop()


class TestWorkerOCRLanguageHint:
    @patch("edge_agent.api.server.get_config")
    @patch("edge_agent.ocr.engine.OCREngine")
    @patch("edge_agent.parsers.router.ParserRouter")
    def test_arabic_ocr_fallback_uses_detected_lang(self, mock_parser_cls, mock_ocr_cls, mock_get_config, db, tmp_path):
        from edge_agent.core.models import ParsedDocument, Language
        from edge_agent.config import EdgeAgentConfig

        # Parser returns short text (triggers OCR fallback)
        mock_parser = MagicMock()
        mock_parser.parse.return_value = ParsedDocument(markdown="نا")
        mock_parser_cls.return_value = mock_parser

        mock_ocr = MagicMock()
        mock_ocr.detect_language.return_value = Language.AR
        mock_ocr_cls.return_value = mock_ocr

        mock_get_config.return_value = EdgeAgentConfig()

        f = tmp_path / "scanned_arabic.png"
        f.write_bytes(b"\x89PNG fake image")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "scanned_arabic.png"}])

        with patch("edge_agent.core.worker.ocr_fallback") as mock_fallback:
            mock_fallback.return_value = ("نص عربي كامل من OCR", True)
            w = Worker(db)
            w.start()
            try:
                jid = db.create_job("scan_file", {"file_id": "file1"})
                for _ in range(50):
                    time.sleep(0.2)
                    job = db.get_job(jid)
                    if job and job["status"] in ("completed", "failed"):
                        break
                # ocr_fallback should have been called with language_hint="ar"
                mock_fallback.assert_called_once()
                call_args = mock_fallback.call_args
                assert call_args.kwargs.get("language_hint") == "ar" or call_args[1].get("language_hint") == "ar"
            finally:
                w.stop()
