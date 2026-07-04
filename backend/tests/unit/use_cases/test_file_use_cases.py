from __future__ import annotations

import pytest
import uuid

from core.application.use_cases.file_use_cases import FileUseCases
from core.domain.common.exceptions import EntityNotFound
from core.domain.files.entities import FileFingerprint, FileRecord
from core.domain.files.value_objects import FileSize, FilePath, FileStatus, Hash, MimeType
from tests.mocks import MockFileRepository, MockFileScanner, MockStorageBackend


@pytest.fixture
def file_use_cases() -> FileUseCases:
    return FileUseCases(
        file_repository=MockFileRepository(),
        storage_backend=MockStorageBackend(),
        file_scanner=MockFileScanner(),
    )


def _make_file_record(file_id: uuid.UUID | None = None) -> FileRecord:
    return FileRecord(
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


# ---------------------------------------------------------------------------
# get_file
# ---------------------------------------------------------------------------


def test_get_file_success(file_use_cases: FileUseCases) -> None:
    file_id = uuid.uuid4()
    record = _make_file_record(file_id)
    file_use_cases._file_repository.save(record)

    result = file_use_cases.get_file(file_id)
    assert result.id == file_id
    assert result.path == "/test/file.pdf"
    assert result.size_bytes == 1024


def test_get_file_not_found_raises(file_use_cases: FileUseCases) -> None:
    with pytest.raises(EntityNotFound):
        file_use_cases.get_file(uuid.uuid4())


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------


def test_list_files_empty(file_use_cases: FileUseCases) -> None:
    result = file_use_cases.list_files()
    assert result == []


def test_list_files_returns_records(file_use_cases: FileUseCases) -> None:
    record = _make_file_record()
    file_use_cases._file_repository.save(record)

    result = file_use_cases.list_files()
    assert len(result) == 1
    assert result[0].id == record.id


def test_list_files_pagination(file_use_cases: FileUseCases) -> None:
    for _ in range(5):
        file_use_cases._file_repository.save(_make_file_record())

    page = file_use_cases.list_files(offset=0, limit=2)
    assert len(page) == 2


# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------


def test_delete_file_success(file_use_cases: FileUseCases) -> None:
    file_id = uuid.uuid4()
    record = _make_file_record(file_id)
    file_use_cases._file_repository.save(record)

    result = file_use_cases.delete_file(file_id)
    assert result.success is True
    assert result.operation == "delete"

    # Verify the file is actually deleted
    assert file_use_cases._file_repository.get_by_id(file_id) is None


def test_delete_file_not_found_raises(file_use_cases: FileUseCases) -> None:
    with pytest.raises(EntityNotFound):
        file_use_cases.delete_file(uuid.uuid4())


# ---------------------------------------------------------------------------
# scan_folder
# ---------------------------------------------------------------------------


def test_scan_folder_creates_records(file_use_cases: FileUseCases) -> None:
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


def test_scan_folder_skips_duplicates(file_use_cases: FileUseCases) -> None:
    # Pre-save a file with the same fingerprint
    existing = _make_file_record()
    file_use_cases._file_repository.save(existing)

    scanner = MockFileScanner(
        files=[
            {
                "path": "/data/dup.pdf",
                "size_bytes": 1024,
                "mime_type": "application/pdf",
                "content_hash": "sha256:abc123",  # same digest as existing
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
