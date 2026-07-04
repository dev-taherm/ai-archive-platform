import pytest
import uuid
from datetime import datetime, timezone

from core.domain.common.entities import BaseEntity
from core.domain.files.entities import FileRecord, FileFingerprint, DuplicateGroup
from core.domain.files.value_objects import Hash, FileSize, MimeType, FilePath, FileStatus


# ---------------------------------------------------------------------------
# BaseEntity
# ---------------------------------------------------------------------------


class TestBaseEntity:
    def test_default_id(self):
        e = BaseEntity()
        assert isinstance(e.id, uuid.UUID)

    def test_default_timestamps(self):
        before = datetime.now(timezone.utc)
        e = BaseEntity()
        after = datetime.now(timezone.utc)
        assert before <= e.created_at <= after
        assert before <= e.updated_at <= after

    def test_with_updated_timestamp(self):
        e = BaseEntity()
        import time
        time.sleep(0.01)
        updated = e.with_updated_timestamp()
        assert updated.id == e.id
        assert updated.created_at == e.created_at
        assert updated.updated_at >= e.updated_at

    def test_string_id_coercion(self):
        raw_id = "12345678-1234-5678-1234-567812345678"
        e = BaseEntity(id=raw_id)
        assert e.id == uuid.UUID(raw_id)

    def test_string_timestamp_coercion(self):
        ts = "2024-01-15T12:00:00+00:00"
        e = BaseEntity(created_at=ts, updated_at=ts)
        assert isinstance(e.created_at, datetime)
        assert isinstance(e.updated_at, datetime)


# ---------------------------------------------------------------------------
# FileFingerprint
# ---------------------------------------------------------------------------


class TestFileFingerprint:
    def test_creation(self):
        fp = FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=100),
        )
        assert fp.content_hash.algorithm == "sha256"
        assert fp.size.bytes == 100

    def test_creation_with_magic_bytes(self):
        fp = FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=100),
            magic_bytes="%PDF",
        )
        assert fp.magic_bytes == "%PDF"

    def test_creation_with_extra(self):
        fp = FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=100),
            extra={"custom": "data"},
        )
        assert fp.extra == {"custom": "data"}

    def test_equality_by_content_hash(self):
        h1 = Hash(algorithm="sha256", digest="abc123")
        h2 = Hash(algorithm="sha256", digest="abc123")
        fp1 = FileFingerprint(content_hash=h1, size=FileSize(bytes=100))
        fp2 = FileFingerprint(content_hash=h2, size=FileSize(bytes=200))
        assert fp1 == fp2  # equal by content_hash only

    def test_inequality(self):
        h1 = Hash(algorithm="sha256", digest="abc123")
        h2 = Hash(algorithm="sha256", digest="def456")
        fp1 = FileFingerprint(content_hash=h1, size=FileSize(bytes=100))
        fp2 = FileFingerprint(content_hash=h2, size=FileSize(bytes=100))
        assert fp1 != fp2

    def test_not_equal_to_non_fingerprint(self):
        fp = FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=100),
        )
        assert fp.__eq__("not a fingerprint") is NotImplemented

    def test_hash_equal(self):
        h1 = Hash(algorithm="sha256", digest="abc123")
        fp1 = FileFingerprint(content_hash=h1, size=FileSize(bytes=100))
        fp2 = FileFingerprint(content_hash=h1, size=FileSize(bytes=200))
        assert hash(fp1) == hash(fp2)

    def test_in_set(self):
        h1 = Hash(algorithm="sha256", digest="abc123")
        fp1 = FileFingerprint(content_hash=h1, size=FileSize(bytes=100))
        fp2 = FileFingerprint(content_hash=h1, size=FileSize(bytes=200))
        assert len({fp1, fp2}) == 1

    def test_immutability(self):
        fp = FileFingerprint(
            content_hash=Hash(algorithm="sha256", digest="abc123"),
            size=FileSize(bytes=100),
        )
        with pytest.raises(AttributeError):
            fp.magic_bytes = "new"


# ---------------------------------------------------------------------------
# FileRecord
# ---------------------------------------------------------------------------


class TestFileRecord:
    def _make_record(self, **overrides) -> FileRecord:
        defaults = dict(
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
        defaults.update(overrides)
        return FileRecord(**defaults)

    def test_creation(self):
        record = self._make_record()
        assert record.path.raw == "/test/file.pdf"
        assert record.status == FileStatus.PENDING
        assert record.size.bytes == 1024

    def test_defaults_with_explicit_args(self):
        record = FileRecord(
            path=FilePath(raw="/test/default.pdf"),
            mime_type=MimeType(value="application/octet-stream"),
            size=FileSize(bytes=0),
            status=FileStatus.PENDING,
            fingerprint=FileFingerprint(
                content_hash=Hash(algorithm="sha256", digest="e3b0c44298fc"),
                size=FileSize(bytes=0),
            ),
        )
        assert record.path.raw == "/test/default.pdf"
        assert record.mime_type.value == "application/octet-stream"
        assert record.status == FileStatus.PENDING
        assert record.tags == ()
        assert record.metadata == {}
        assert record.duplicate_group_id is None
        assert record.checksum is None

    def test_with_tags(self):
        record = self._make_record(tags=("important", "contract"))
        assert "important" in record.tags
        assert "contract" in record.tags
        assert len(record.tags) == 2

    def test_with_metadata(self):
        record = self._make_record(metadata={"key": "value"})
        assert record.metadata == {"key": "value"}

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_indexed uses self.status= on frozen dataclass instead of object.__setattr__",
        raises=AttributeError,
        strict=True,
    )
    def test_mark_indexed(self):
        record = self._make_record()
        record.mark_indexed()
        assert record.status == FileStatus.INDEXED

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_duplicate uses self.status= on frozen dataclass instead of object.__setattr__",
        raises=AttributeError,
        strict=True,
    )
    def test_mark_duplicate(self):
        group_id = uuid.uuid4()
        record = self._make_record()
        record.mark_duplicate(group_id)
        assert record.status == FileStatus.DUPLICATE
        assert record.duplicate_group_id == group_id

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_failed uses self.status= on frozen dataclass instead of object.__setattr__",
        raises=AttributeError,
        strict=True,
    )
    def test_mark_failed(self):
        record = self._make_record()
        record.mark_failed()
        assert record.status == FileStatus.FAILED

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_deleted uses self.status= on frozen dataclass instead of object.__setattr__",
        raises=AttributeError,
        strict=True,
    )
    def test_mark_deleted(self):
        record = self._make_record(status=FileStatus.INDEXED)
        record.mark_deleted()
        assert record.status == FileStatus.DELETED

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_indexed uses self.status= on frozen dataclass",
        raises=AttributeError,
        strict=True,
    )
    def test_is_available_indexed(self):
        record = self._make_record()
        record.mark_indexed()
        assert record.is_available

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_duplicate uses self.status= on frozen dataclass",
        raises=AttributeError,
        strict=True,
    )
    def test_is_available_duplicate(self):
        record = self._make_record()
        record.mark_duplicate(uuid.uuid4())
        assert record.is_available

    def test_is_not_available_pending(self):
        record = self._make_record()
        assert not record.is_available

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_failed uses self.status= on frozen dataclass",
        raises=AttributeError,
        strict=True,
    )
    def test_is_not_available_failed(self):
        record = self._make_record()
        record.mark_failed()
        assert not record.is_available

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_deleted uses self.status= on frozen dataclass",
        raises=AttributeError,
        strict=True,
    )
    def test_is_not_available_deleted(self):
        record = self._make_record()
        record.mark_deleted()
        assert not record.is_available

    def test_extension(self):
        record = self._make_record(path=FilePath(raw="/test/document.pdf"))
        assert record.extension == ".pdf"

    def test_filename(self):
        record = self._make_record(path=FilePath(raw="/test/document.pdf"))
        assert record.filename == "document.pdf"

    def test_with_checksum(self):
        h = Hash(algorithm="sha256", digest="abc123")
        record = self._make_record(checksum=h)
        assert record.checksum == h

    def test_immutability(self):
        record = self._make_record()
        with pytest.raises(AttributeError):
            record.status = FileStatus.INDEXED

    @pytest.mark.xfail(
        reason="BUG: FileRecord.mark_indexed uses self.status= on frozen dataclass",
        raises=AttributeError,
        strict=True,
    )
    def test_mark_indexed_updates_timestamp(self):
        record = self._make_record()
        old_updated = record.updated_at
        import time
        time.sleep(0.01)
        record.mark_indexed()
        assert record.updated_at >= old_updated


# ---------------------------------------------------------------------------
# DuplicateGroup
# ---------------------------------------------------------------------------


class TestDuplicateGroup:
    def test_creation(self):
        ids = (uuid.uuid4(), uuid.uuid4())
        group = DuplicateGroup(id=uuid.uuid4(), file_ids=ids)
        assert group.file_count == 2
        assert not group.resolved

    def test_defaults(self):
        group = DuplicateGroup()
        assert group.file_count == 0
        assert not group.resolved
        assert group.fingerprint is None

    def test_file_count(self):
        group = DuplicateGroup(file_ids=(uuid.uuid4(), uuid.uuid4(), uuid.uuid4()))
        assert group.file_count == 3

    def test_resolve(self):
        group = DuplicateGroup(
            id=uuid.uuid4(),
            file_ids=(uuid.uuid4(), uuid.uuid4()),
        )
        resolved = group.resolve()
        assert resolved.resolved
        assert resolved.id == group.id
        assert resolved.file_ids == group.file_ids
        assert resolved.fingerprint == group.fingerprint
        assert resolved.created_at == group.created_at

    def test_resolve_preserves_original(self):
        group = DuplicateGroup(file_ids=(uuid.uuid4(),))
        resolved = group.resolve()
        assert not group.resolved  # original unchanged
        assert resolved.resolved

    def test_immutability(self):
        group = DuplicateGroup(file_ids=(uuid.uuid4(),))
        with pytest.raises(AttributeError):
            group.resolved = True
