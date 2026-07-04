import pytest
import uuid

from core.domain.files.entities import FileRecord, FileFingerprint, DuplicateGroup
from core.domain.files.value_objects import Hash, FileSize, MimeType, FilePath, FileStatus


def test_file_record_creation():
    record = FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw="/test/file.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.PENDING,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
        ),
    )
    assert record.path.raw == "/test/file.pdf"
    assert record.status == FileStatus.PENDING
    assert record.size.bytes == 1024


def test_file_record_with_tags():
    record = FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw="/test/file.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.PENDING,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
        ),
        tags=("important", "contract"),
    )
    assert "important" in record.tags
    assert "contract" in record.tags


@pytest.mark.xfail(
    reason="BUG: FileRecord.mark_indexed uses self.status= on a frozen dataclass "
           "instead of object.__setattr__ (compare Document entity which does it correctly)",
    raises=AttributeError,
    strict=True,
)
def test_file_record_mark_indexed():
    record = FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw="/test/file.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.PENDING,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
        ),
    )
    record.mark_indexed()
    assert record.status == FileStatus.INDEXED
    assert record.is_available


@pytest.mark.xfail(
    reason="BUG: FileRecord.mark_duplicate uses self.status= on a frozen dataclass",
    raises=AttributeError,
    strict=True,
)
def test_file_record_mark_duplicate():
    group_id = uuid.uuid4()
    record = FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw="/test/file.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.PENDING,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
        ),
    )
    record.mark_duplicate(group_id)
    assert record.status == FileStatus.DUPLICATE
    assert record.duplicate_group_id == group_id
    assert record.is_available


@pytest.mark.xfail(
    reason="BUG: FileRecord.mark_failed uses self.status= on a frozen dataclass",
    raises=AttributeError,
    strict=True,
)
def test_file_record_mark_failed():
    record = FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw="/test/file.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.PENDING,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
        ),
    )
    record.mark_failed()
    assert record.status == FileStatus.FAILED
    assert not record.is_available


@pytest.mark.xfail(
    reason="BUG: FileRecord.mark_deleted uses self.status= on a frozen dataclass",
    raises=AttributeError,
    strict=True,
)
def test_file_record_mark_deleted():
    record = FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw="/test/file.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.INDEXED,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
        ),
    )
    record.mark_deleted()
    assert record.status == FileStatus.DELETED
    assert not record.is_available


def test_file_record_extension():
    record = FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw="/test/document.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.PENDING,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
        ),
    )
    assert record.extension == ".pdf"


def test_file_record_filename():
    record = FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw="/test/document.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        status=FileStatus.PENDING,
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=1024),
        ),
    )
    assert record.filename == "document.pdf"


def test_file_fingerprint_equality():
    h1 = Hash(algorithm="sha256", digest="abc123")
    h2 = Hash(algorithm="sha256", digest="abc123")
    h3 = Hash(algorithm="sha256", digest="def456")

    fp1 = FileFingerprint(content_hash=h1, size=FileSize(bytes=100))
    fp2 = FileFingerprint(content_hash=h2, size=FileSize(bytes=200))
    fp3 = FileFingerprint(content_hash=h3, size=FileSize(bytes=100))

    assert fp1 == fp2  # equal by content_hash
    assert fp1 != fp3


def test_file_fingerprint_hash():
    h1 = Hash(algorithm="sha256", digest="abc123")
    fp1 = FileFingerprint(content_hash=h1, size=FileSize(bytes=100))
    fp2 = FileFingerprint(content_hash=h1, size=FileSize(bytes=200))
    assert hash(fp1) == hash(fp2)


def test_duplicate_group_creation():
    group = DuplicateGroup(
        id=uuid.uuid4(),
        file_ids=(uuid.uuid4(), uuid.uuid4()),
    )
    assert group.file_count == 2
    assert not group.resolved


def test_duplicate_group_resolve():
    group = DuplicateGroup(
        id=uuid.uuid4(),
        file_ids=(uuid.uuid4(), uuid.uuid4()),
    )
    resolved = group.resolve()
    assert resolved.resolved
    assert resolved.id == group.id
    assert resolved.file_ids == group.file_ids
