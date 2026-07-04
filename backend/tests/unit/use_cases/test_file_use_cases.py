from __future__ import annotations

import pytest
import uuid

from core.application.dtos.file_dto import FileRecordDTO, ScanResultDTO, FileOperationDTO
from core.application.use_cases.file_use_cases import FileUseCases
from core.domain.common.exceptions import EntityNotFound, ValidationException
from core.domain.files.entities import FileFingerprint, FileRecord
from core.domain.files.value_objects import FileSize, FilePath, FileStatus, Hash, MimeType
from tests.mocks import MockFileRepository, MockFileScanner, MockStorageBackend


@pytest.fixture
def file_repository() -> MockFileRepository:
    return MockFileRepository()


@pytest.fixture
def storage_backend() -> MockStorageBackend:
    return MockStorageBackend()


@pytest.fixture
def file_scanner() -> MockFileScanner:
    return MockFileScanner()


@pytest.fixture
def file_use_cases(
    file_repository: MockFileRepository,
    storage_backend: MockStorageBackend,
    file_scanner: MockFileScanner,
) -> FileUseCases:
    return FileUseCases(
        file_repository=file_repository,
        storage_backend=storage_backend,
        file_scanner=file_scanner,
    )


def _make_file_record(file_id: uuid.UUID | None = None, **overrides) -> FileRecord:
    defaults = dict(
        id=file_id or uuid.uuid4(),
        path=FilePath(raw="/test/file.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.PENDING,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
            magic_bytes="%PDF",
        ),
    )
    defaults.update(overrides)
    return FileRecord(**defaults)


# ---------------------------------------------------------------------------
# get_file
# ---------------------------------------------------------------------------


class TestGetFile:
    def test_success(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        record = _make_file_record(file_id)
        file_use_cases._file_repository.save(record)

        result = file_use_cases.get_file(file_id)
        assert result.id == file_id
        assert result.path == "/test/file.pdf"
        assert result.size_bytes == 1024
        assert result.mime_type == "application/pdf"
        assert result.status == "pending"

    def test_not_found_raises(self, file_use_cases: FileUseCases) -> None:
        with pytest.raises(EntityNotFound) as exc_info:
            file_use_cases.get_file(uuid.uuid4())
        assert "FileRecord" in str(exc_info.value.message)

    def test_returns_dto(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))

        result = file_use_cases.get_file(file_id)
        assert isinstance(result, FileRecordDTO)


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------


class TestListFiles:
    def test_empty(self, file_use_cases: FileUseCases) -> None:
        result = file_use_cases.list_files()
        assert result == []

    def test_returns_records(self, file_use_cases: FileUseCases) -> None:
        record = _make_file_record()
        file_use_cases._file_repository.save(record)

        result = file_use_cases.list_files()
        assert len(result) == 1
        assert result[0].id == record.id

    def test_pagination_offset(self, file_use_cases: FileUseCases) -> None:
        ids = []
        for _ in range(5):
            r = _make_file_record()
            file_use_cases._file_repository.save(r)
            ids.append(r.id)

        page = file_use_cases.list_files(offset=0, limit=2)
        assert len(page) == 2

        page2 = file_use_cases.list_files(offset=2, limit=2)
        assert len(page2) == 2

        page3 = file_use_cases.list_files(offset=4, limit=2)
        assert len(page3) == 1

    def test_pagination_limit(self, file_use_cases: FileUseCases) -> None:
        for _ in range(10):
            file_use_cases._file_repository.save(_make_file_record())

        result = file_use_cases.list_files(limit=3)
        assert len(result) == 3

    def test_returns_dtos(self, file_use_cases: FileUseCases) -> None:
        file_use_cases._file_repository.save(_make_file_record())
        result = file_use_cases.list_files()
        assert all(isinstance(r, FileRecordDTO) for r in result)

    def test_offset_beyond_data(self, file_use_cases: FileUseCases) -> None:
        file_use_cases._file_repository.save(_make_file_record())
        result = file_use_cases.list_files(offset=10)
        assert result == []


# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------


class TestDeleteFile:
    def test_success(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))

        result = file_use_cases.delete_file(file_id)
        assert result.success is True
        assert result.operation == "delete"
        assert result.file_id == file_id

    def test_file_removed(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))

        file_use_cases.delete_file(file_id)
        assert file_use_cases._file_repository.get_by_id(file_id) is None

    def test_not_found_raises(self, file_use_cases: FileUseCases) -> None:
        with pytest.raises(EntityNotFound):
            file_use_cases.delete_file(uuid.uuid4())

    def test_returns_operation_dto(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))

        result = file_use_cases.delete_file(file_id)
        assert isinstance(result, FileOperationDTO)

    def test_storage_delete_called(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        record = _make_file_record(file_id)
        file_use_cases._file_repository.save(record)

        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"
        file_use_cases.delete_file(file_id)
        assert not file_use_cases._storage_backend.exists("/test/file.pdf")

    def test_delete_failure_returns_failure_result(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        record = _make_file_record(file_id)
        file_use_cases._file_repository.save(record)

        original_delete = file_use_cases._file_repository.delete

        def fail_delete(fid: uuid.UUID) -> bool:
            return False

        file_use_cases._file_repository.delete = fail_delete
        result = file_use_cases.delete_file(file_id)
        assert result.success is False
        assert result.error_message is not None

        file_use_cases._file_repository.delete = original_delete


# ---------------------------------------------------------------------------
# rename_file
# ---------------------------------------------------------------------------


class TestRenameFile:
    def test_success(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))
        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"

        result = file_use_cases.rename_file(file_id, "renamed.pdf")
        assert result.success is True
        assert result.operation == "rename"
        assert result.file_id == file_id

    def test_not_found_raises(self, file_use_cases: FileUseCases) -> None:
        with pytest.raises(EntityNotFound):
            file_use_cases.rename_file(uuid.uuid4(), "new.pdf")

    def test_empty_name_raises(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))

        with pytest.raises(ValidationException):
            file_use_cases.rename_file(file_id, "")

    def test_whitespace_name_raises(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))

        with pytest.raises(ValidationException):
            file_use_cases.rename_file(file_id, "   ")

    def test_updates_path(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))
        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"

        file_use_cases.rename_file(file_id, "new_name.pdf")
        saved = file_use_cases._file_repository.get_by_id(file_id)
        assert saved is not None
        assert "new_name.pdf" in saved.path.normalized

    def test_storage_failure_returns_failure(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))
        # No content in storage — retrieve will return empty bytes
        # but let's make retrieve raise
        original = file_use_cases._storage_backend.retrieve

        def fail_retrieve(path: str) -> bytes:
            raise OSError("Storage unavailable")

        file_use_cases._storage_backend.retrieve = fail_retrieve
        result = file_use_cases.rename_file(file_id, "new.pdf")
        assert result.success is False
        assert "Storage rename failed" in result.error_message

        file_use_cases._storage_backend.retrieve = original


# ---------------------------------------------------------------------------
# move_file
# ---------------------------------------------------------------------------


class TestMoveFile:
    def test_success(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))
        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"

        result = file_use_cases.move_file(file_id, "/new_folder")
        assert result.success is True
        assert result.operation == "move"
        assert result.file_id == file_id
        assert result.destination_path is not None

    def test_not_found_raises(self, file_use_cases: FileUseCases) -> None:
        with pytest.raises(EntityNotFound):
            file_use_cases.move_file(uuid.uuid4(), "/dest")

    def test_updates_path(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))
        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"

        file_use_cases.move_file(file_id, "/new_folder")
        saved = file_use_cases._file_repository.get_by_id(file_id)
        assert saved is not None
        assert saved.path.normalized.startswith("/new_folder")
        assert saved.path.filename == "file.pdf"

    def test_storage_failure_returns_failure(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))

        original = file_use_cases._storage_backend.retrieve

        def fail_retrieve(path: str) -> bytes:
            raise OSError("Storage unavailable")

        file_use_cases._storage_backend.retrieve = fail_retrieve
        result = file_use_cases.move_file(file_id, "/dest")
        assert result.success is False
        assert "Storage move failed" in result.error_message

        file_use_cases._storage_backend.retrieve = original


# ---------------------------------------------------------------------------
# copy_file
# ---------------------------------------------------------------------------


class TestCopyFile:
    def test_success(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        original_record = _make_file_record(file_id)
        file_use_cases._file_repository.save(original_record)
        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"

        result = file_use_cases.copy_file(file_id, "/copy_folder")
        assert result.success is True
        assert result.operation == "copy"
        assert result.source_path == "/test/file.pdf"
        assert result.destination_path is not None

    def test_creates_new_record(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))
        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"

        result = file_use_cases.copy_file(file_id, "/copy_folder")
        # The new copy should have a different ID
        assert result.file_id != file_id

    def test_copy_has_pending_status(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))
        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"

        result = file_use_cases.copy_file(file_id, "/copy_folder")
        copy_record = file_use_cases._file_repository.get_by_id(result.file_id)
        assert copy_record is not None
        assert copy_record.status == FileStatus.PENDING

    def test_not_found_raises(self, file_use_cases: FileUseCases) -> None:
        with pytest.raises(EntityNotFound):
            file_use_cases.copy_file(uuid.uuid4(), "/dest")

    def test_storage_failure_returns_failure(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))

        original = file_use_cases._storage_backend.retrieve

        def fail_retrieve(path: str) -> bytes:
            raise OSError("Storage unavailable")

        file_use_cases._storage_backend.retrieve = fail_retrieve
        result = file_use_cases.copy_file(file_id, "/dest")
        assert result.success is False
        assert "Storage copy failed" in result.error_message

        file_use_cases._storage_backend.retrieve = original

    def test_original_preserved(self, file_use_cases: FileUseCases) -> None:
        file_id = uuid.uuid4()
        file_use_cases._file_repository.save(_make_file_record(file_id))
        file_use_cases._storage_backend._store["/test/file.pdf"] = b"content"

        file_use_cases.copy_file(file_id, "/copy_folder")
        original = file_use_cases._file_repository.get_by_id(file_id)
        assert original is not None
        assert original.path.raw == "/test/file.pdf"


# ---------------------------------------------------------------------------
# scan_folder
# ---------------------------------------------------------------------------


class TestScanFolder:
    def test_creates_records(self, file_use_cases: FileUseCases) -> None:
        scanner = MockFileScanner(
            files=[
                {
                    "path": "/data/doc.pdf",
                    "size_bytes": 2048,
                    "mime_type": "application/pdf",
                    "content_hash": "sha256:deadbeef",
                    "magic_bytes": "%PDF",
                },
            ]
        )
        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=scanner,
        )

        result = use_cases.scan_folder("/data")
        assert result.new_files == 1
        assert result.total_files_found == 1
        assert len(result.file_ids) == 1

    def test_skips_duplicates(self, file_use_cases: FileUseCases) -> None:
        existing = _make_file_record()
        file_use_cases._file_repository.save(existing)

        scanner = MockFileScanner(
            files=[
                {
                    "path": "/data/dup.pdf",
                    "size_bytes": 1024,
                    "mime_type": "application/pdf",
                    "content_hash": "sha256:abc123",
                    "magic_bytes": "%PDF",
                },
            ]
        )
        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=scanner,
        )

        result = use_cases.scan_folder("/data")
        assert result.skipped_files == 1
        assert result.new_files == 0

    def test_empty_folder(self, file_use_cases: FileUseCases) -> None:
        scanner = MockFileScanner(files=[])
        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=scanner,
        )

        result = use_cases.scan_folder("/empty")
        assert result.total_files_found == 0
        assert result.files_scanned == 0
        assert result.new_files == 0

    def test_multiple_files(self, file_use_cases: FileUseCases) -> None:
        files = [
            {
                "path": f"/data/file_{i}.pdf",
                "size_bytes": 1024 * (i + 1),
                "mime_type": "application/pdf",
                "content_hash": f"sha256:hash_{i}",
                "magic_bytes": "%PDF",
            }
            for i in range(5)
        ]
        scanner = MockFileScanner(files=files)
        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=scanner,
        )

        result = use_cases.scan_folder("/data")
        assert result.new_files == 5
        assert result.total_files_found == 5

    def test_returns_scan_result_dto(self, file_use_cases: FileUseCases) -> None:
        scanner = MockFileScanner(files=[])
        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=scanner,
        )

        result = use_cases.scan_folder("/data")
        assert isinstance(result, ScanResultDTO)

    def test_hash_with_colon_prefix(self, file_use_cases: FileUseCases) -> None:
        scanner = MockFileScanner(
            files=[
                {
                    "path": "/data/doc.pdf",
                    "size_bytes": 1024,
                    "mime_type": "application/pdf",
                    "content_hash": "sha256:abcdef123456",
                    "magic_bytes": "",
                },
            ]
        )
        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=scanner,
        )

        result = use_cases.scan_folder("/data")
        assert result.new_files == 1

    def test_hash_without_colon_defaults_sha256(self, file_use_cases: FileUseCases) -> None:
        scanner = MockFileScanner(
            files=[
                {
                    "path": "/data/doc.pdf",
                    "size_bytes": 1024,
                    "mime_type": "application/pdf",
                    "content_hash": "abcdef123456",
                    "magic_bytes": "",
                },
            ]
        )
        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=scanner,
        )

        result = use_cases.scan_folder("/data")
        assert result.new_files == 1

    def test_scan_duration_recorded(self, file_use_cases: FileUseCases) -> None:
        scanner = MockFileScanner(files=[])
        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=scanner,
        )

        result = use_cases.scan_folder("/data")
        assert result.scan_duration_seconds >= 0

    def test_failed_file_counted(self, file_use_cases: FileUseCases) -> None:
        scanner = MockFileScanner(
            files=[
                {
                    "path": "/data/bad.pdf",
                    "size_bytes": 1024,
                    "mime_type": "application/pdf",
                    "content_hash": "sha256:good",
                },
                # Missing required fields will cause an error
            ]
        )

        # Add a file that will cause ValueError in FilePath (empty path)
        bad_files = [
            {
                "path": "/data/good.pdf",
                "size_bytes": 1024,
                "mime_type": "application/pdf",
                "content_hash": "sha256:hash1",
            },
        ]

        class FailingScanner:
            def scan_folder(self, path, *, recursive=True, patterns=None, ignore_patterns=None):
                yield bad_files[0]
                yield {"size_bytes": 100}  # Missing path — will cause KeyError

            def watch_folder(self, path, *, recursive=True, callback=None):
                pass

            def stop_watching(self, path):
                pass

            def is_watching(self, path):
                return False

        use_cases = FileUseCases(
            file_repository=file_use_cases._file_repository,
            storage_backend=file_use_cases._storage_backend,
            file_scanner=FailingScanner(),
        )

        result = use_cases.scan_folder("/data")
        assert result.failed_files == 1
        assert len(result.errors) == 1
