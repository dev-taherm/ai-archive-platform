import pytest
import uuid
from datetime import datetime, timezone, timedelta

from core.domain.common.value_objects import Timestamp, EntityId
from core.domain.files.value_objects import Hash, FileSize, MimeType, FilePath, FileStatus
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)
from core.domain.ai.value_objects import AIProvider, ModelConfig, TaskStatus


# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------


class TestTimestamp:
    def test_creation_with_utc(self):
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        ts = Timestamp(value=dt)
        assert ts.value == dt

    def test_creation_adds_utc_if_naive(self):
        dt = datetime(2024, 1, 15, 12, 0, 0)
        ts = Timestamp(value=dt)
        assert ts.value.tzinfo is not None
        assert ts.value.tzinfo == timezone.utc

    def test_now(self):
        before = datetime.now(timezone.utc)
        ts = Timestamp.now()
        after = datetime.now(timezone.utc)
        assert before <= ts.value <= after

    def test_fromisoformat(self):
        ts = Timestamp.fromisoformat("2024-06-15T10:30:00+00:00")
        assert ts.value.hour == 10
        assert ts.value.minute == 30

    def test_isoformat(self):
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        ts = Timestamp(value=dt)
        assert "2024-01-15" in ts.isoformat

    def test_epoch_seconds(self):
        dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ts = Timestamp(value=dt)
        assert ts.epoch_seconds == 1704067200.0

    def test_comparison_gt(self):
        t1 = Timestamp(value=datetime(2024, 1, 1, tzinfo=timezone.utc))
        t2 = Timestamp(value=datetime(2024, 6, 1, tzinfo=timezone.utc))
        assert t2 > t1
        assert not t1 > t2

    def test_comparison_ge(self):
        t1 = Timestamp(value=datetime(2024, 1, 1, tzinfo=timezone.utc))
        t2 = Timestamp(value=datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert t1 >= t2
        assert t2 >= t1

    def test_comparison_lt(self):
        t1 = Timestamp(value=datetime(2024, 1, 1, tzinfo=timezone.utc))
        t2 = Timestamp(value=datetime(2024, 6, 1, tzinfo=timezone.utc))
        assert t1 < t2
        assert not t2 < t1

    def test_comparison_le(self):
        t1 = Timestamp(value=datetime(2024, 1, 1, tzinfo=timezone.utc))
        t2 = Timestamp(value=datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert t1 <= t2
        assert t2 <= t1

    def test_immutability(self):
        ts = Timestamp(value=datetime(2024, 1, 1, tzinfo=timezone.utc))
        with pytest.raises(AttributeError):
            ts.value = datetime(2025, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# EntityId
# ---------------------------------------------------------------------------


class TestEntityId:
    def test_generate(self):
        eid = EntityId.generate()
        assert isinstance(eid.value, uuid.UUID)

    def test_from_string(self):
        raw = "12345678-1234-5678-1234-567812345678"
        eid = EntityId.from_string(raw)
        assert eid.value == uuid.UUID(raw)

    def test_from_string_invalid(self):
        with pytest.raises(ValueError):
            EntityId.from_string("not-a-uuid")

    def test_hex(self):
        raw = "12345678-1234-5678-1234-567812345678"
        eid = EntityId.from_string(raw)
        assert len(eid.hex) == 32

    def test_short(self):
        raw = "12345678-1234-5678-1234-567812345678"
        eid = EntityId.from_string(raw)
        assert len(eid.short) == 8

    def test_immutable(self):
        eid = EntityId.generate()
        with pytest.raises(AttributeError):
            eid.value = uuid.uuid4()

    def test_equality(self):
        raw = "12345678-1234-5678-1234-567812345678"
        eid1 = EntityId.from_string(raw)
        eid2 = EntityId.from_string(raw)
        assert eid1 == eid2

    def test_string_coercion(self):
        """EntityId accepts a string UUID in __post_init__."""
        raw = "12345678-1234-5678-1234-567812345678"
        eid = EntityId(value=raw)
        assert eid.value == uuid.UUID(raw)


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------


class TestHash:
    def test_creation(self):
        h = Hash(algorithm="sha256", digest="abc123def456")
        assert h.algorithm == "sha256"
        assert h.digest == "abc123def456"

    def test_canonical(self):
        h = Hash(algorithm="sha256", digest="abc123def456")
        assert h.canonical == "sha256:abc123def456"

    def test_equality(self):
        h1 = Hash(algorithm="sha256", digest="abc123")
        h2 = Hash(algorithm="sha256", digest="abc123")
        h3 = Hash(algorithm="sha256", digest="def456")
        h4 = Hash(algorithm="md5", digest="abc123")
        assert h1 == h2
        assert h1 != h3
        assert h1 != h4

    def test_not_equal_to_non_hash(self):
        h = Hash(algorithm="sha256", digest="abc123")
        assert h.__eq__("not a hash") is NotImplemented

    def test_in_set(self):
        h1 = Hash(algorithm="sha256", digest="abc123")
        h2 = Hash(algorithm="sha256", digest="abc123")
        assert len({h1, h2}) == 1

    def test_different_hashes_in_set(self):
        h1 = Hash(algorithm="sha256", digest="abc123")
        h2 = Hash(algorithm="sha256", digest="def456")
        assert len({h1, h2}) == 2

    def test_empty_algorithm_raises(self):
        with pytest.raises(ValueError):
            Hash(algorithm="", digest="abc123")

    def test_empty_digest_raises(self):
        with pytest.raises(ValueError):
            Hash(algorithm="sha256", digest="")

    def test_immutability(self):
        h = Hash(algorithm="sha256", digest="abc123")
        with pytest.raises(AttributeError):
            h.algorithm = "md5"


# ---------------------------------------------------------------------------
# FilePath
# ---------------------------------------------------------------------------


class TestFilePath:
    def test_creation(self):
        fp = FilePath(raw="/documents/test.pdf")
        assert fp.raw == "/documents/test.pdf"

    def test_normalized(self):
        fp = FilePath(raw="/test/file.pdf")
        assert fp.normalized == "/test/file.pdf"

    def test_filename(self):
        fp = FilePath(raw="/documents/test.pdf")
        assert fp.filename == "test.pdf"

    def test_extension(self):
        fp = FilePath(raw="/documents/test.pdf")
        assert fp.extension == ".pdf"

    def test_extension_lowercase(self):
        fp = FilePath(raw="/documents/test.PDF")
        assert fp.extension == ".pdf"

    def test_extension_none(self):
        fp = FilePath(raw="/documents/noext")
        assert fp.extension == ""

    def test_parent(self):
        fp = FilePath(raw="/documents/sub/test.pdf")
        assert fp.parent == "/documents/sub"

    def test_parent_root(self):
        fp = FilePath(raw="/test.pdf")
        assert fp.parent == "/"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            FilePath(raw="")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            FilePath(raw="   ")

    def test_tab_only_raises(self):
        with pytest.raises(ValueError):
            FilePath(raw="\t")

    def test_immutability(self):
        fp = FilePath(raw="/test.pdf")
        with pytest.raises(AttributeError):
            fp.raw = "/other.pdf"


# ---------------------------------------------------------------------------
# FileSize
# ---------------------------------------------------------------------------


class TestFileSize:
    def test_bytes(self):
        s = FileSize(bytes=1048576)
        assert s.bytes == 1048576

    def test_kilobytes(self):
        s = FileSize(bytes=2048)
        assert s.kilobytes == 2.0

    def test_kilobytes_rounding(self):
        s = FileSize(bytes=1536)
        assert s.kilobytes == 1.5

    def test_megabytes(self):
        s = FileSize(bytes=2097152)
        assert s.megabytes == 2.0

    def test_human_readable_bytes(self):
        assert FileSize(bytes=0).human_readable == "0 B"
        assert FileSize(bytes=500).human_readable == "500 B"
        assert FileSize(bytes=1023).human_readable == "1023 B"

    def test_human_readable_kb(self):
        assert FileSize(bytes=1024).human_readable == "1.0 KB"
        assert FileSize(bytes=1536).human_readable == "1.5 KB"
        assert FileSize(bytes=1048575).human_readable == "1024.0 KB"

    def test_human_readable_mb(self):
        assert FileSize(bytes=1048576).human_readable == "1.0 MB"
        assert FileSize(bytes=2097152).human_readable == "2.0 MB"

    def test_human_readable_gb(self):
        assert FileSize(bytes=1073741824).human_readable == "1.0 GB"
        assert FileSize(bytes=2147483648).human_readable == "2.0 GB"

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            FileSize(bytes=-1)

    def test_zero_allowed(self):
        s = FileSize(bytes=0)
        assert s.bytes == 0

    def test_immutability(self):
        s = FileSize(bytes=1024)
        with pytest.raises(AttributeError):
            s.bytes = 2048


# ---------------------------------------------------------------------------
# MimeType
# ---------------------------------------------------------------------------


class TestMimeType:
    def test_creation(self):
        m = MimeType(value="application/pdf")
        assert m.value == "application/pdf"

    def test_type_and_subtype(self):
        m = MimeType(value="text/plain")
        assert m.type == "text"
        assert m.subtype == "plain"

    def test_is_text(self):
        assert MimeType(value="text/plain").is_text
        assert MimeType(value="text/html").is_text
        assert MimeType(value="application/json").is_text
        assert MimeType(value="application/xml").is_text
        assert MimeType(value="application/javascript").is_text
        assert MimeType(value="application/yaml").is_text
        assert MimeType(value="application/csv").is_text

    def test_is_not_text(self):
        assert not MimeType(value="application/pdf").is_text
        assert not MimeType(value="image/png").is_text

    def test_is_image(self):
        assert MimeType(value="image/png").is_image
        assert MimeType(value="image/jpeg").is_image
        assert MimeType(value="image/gif").is_image

    def test_is_not_image(self):
        assert not MimeType(value="application/pdf").is_image
        assert not MimeType(value="text/plain").is_image

    def test_is_pdf(self):
        assert MimeType(value="application/pdf").is_pdf

    def test_is_not_pdf(self):
        assert not MimeType(value="text/plain").is_pdf
        assert not MimeType(value="image/png").is_pdf

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            MimeType(value="")

    def test_no_slash_raises(self):
        with pytest.raises(ValueError):
            MimeType(value="invalid-no-slash")

    def test_immutability(self):
        m = MimeType(value="application/pdf")
        with pytest.raises(AttributeError):
            m.value = "text/plain"


# ---------------------------------------------------------------------------
# FileStatus
# ---------------------------------------------------------------------------


class TestFileStatus:
    def test_values(self):
        assert FileStatus.PENDING.value == "pending"
        assert FileStatus.INDEXING.value == "indexing"
        assert FileStatus.INDEXED.value == "indexed"
        assert FileStatus.DUPLICATE.value == "duplicate"
        assert FileStatus.FAILED.value == "failed"
        assert FileStatus.DELETED.value == "deleted"

    def test_all_members(self):
        assert len(FileStatus) == 6


# ---------------------------------------------------------------------------
# DocumentType
# ---------------------------------------------------------------------------


class TestDocumentType:
    def test_from_extension_pdf(self):
        assert DocumentType.from_extension(".pdf") == DocumentType.PDF

    def test_from_extension_text(self):
        assert DocumentType.from_extension(".txt") == DocumentType.TEXT

    def test_from_extension_markdown(self):
        assert DocumentType.from_extension(".md") == DocumentType.MARKDOWN

    def test_from_extension_html(self):
        assert DocumentType.from_extension(".html") == DocumentType.HTML
        assert DocumentType.from_extension(".htm") == DocumentType.HTML
        assert DocumentType.from_extension(".xml") == DocumentType.HTML

    def test_from_extension_code(self):
        for ext in [".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h",
                     ".sql", ".yaml", ".yml", ".toml"]:
            assert DocumentType.from_extension(ext) == DocumentType.CODE

    def test_from_extension_email(self):
        assert DocumentType.from_extension(".eml") == DocumentType.EMAIL

    def test_from_extension_spreadsheet(self):
        assert DocumentType.from_extension(".xlsx") == DocumentType.SPREADSHEET
        assert DocumentType.from_extension(".xls") == DocumentType.SPREADSHEET

    def test_from_extension_presentation(self):
        assert DocumentType.from_extension(".pptx") == DocumentType.PRESENTATION
        assert DocumentType.from_extension(".ppt") == DocumentType.PRESENTATION

    def test_from_extension_csv(self):
        assert DocumentType.from_extension(".csv") == DocumentType.CSV

    def test_from_extension_json(self):
        assert DocumentType.from_extension(".json") == DocumentType.JSON

    def test_from_extension_unknown(self):
        assert DocumentType.from_extension(".xyz") == DocumentType.UNKNOWN
        assert DocumentType.from_extension(".unknown") == DocumentType.UNKNOWN

    def test_from_extension_case_insensitive(self):
        assert DocumentType.from_extension(".PDF") == DocumentType.PDF
        assert DocumentType.from_extension(".TXT") == DocumentType.TEXT


# ---------------------------------------------------------------------------
# Language
# ---------------------------------------------------------------------------


class TestLanguage:
    def test_values(self):
        assert Language.EN.value == "en"
        assert Language.FR.value == "fr"
        assert Language.DE.value == "de"
        assert Language.ES.value == "es"
        assert Language.JA.value == "ja"
        assert Language.ZH.value == "zh"
        assert Language.UNKNOWN.value == "unknown"

    def test_all_members(self):
        assert len(Language) == 19


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


class TestConfidence:
    def test_creation(self):
        c = Confidence(value=0.85)
        assert c.value == 0.85

    def test_is_high(self):
        assert Confidence(value=0.8).is_high
        assert Confidence(value=0.95).is_high
        assert Confidence(value=1.0).is_high

    def test_is_not_high(self):
        assert not Confidence(value=0.79).is_high
        assert not Confidence(value=0.5).is_high

    def test_is_medium(self):
        assert Confidence(value=0.5).is_medium
        assert Confidence(value=0.65).is_medium
        assert Confidence(value=0.79).is_medium

    def test_is_not_medium(self):
        assert not Confidence(value=0.49).is_medium
        assert not Confidence(value=0.8).is_medium

    def test_is_low(self):
        assert Confidence(value=0.0).is_low
        assert Confidence(value=0.3).is_low
        assert Confidence(value=0.49).is_low

    def test_is_not_low(self):
        assert not Confidence(value=0.5).is_low
        assert not Confidence(value=1.0).is_low

    def test_percentage(self):
        assert Confidence(value=0.856).percentage == "85.6%"
        assert Confidence(value=0.0).percentage == "0.0%"
        assert Confidence(value=1.0).percentage == "100.0%"
        assert Confidence(value=0.5).percentage == "50.0%"

    def test_boundary_zero(self):
        c = Confidence(value=0.0)
        assert c.value == 0.0
        assert c.is_low

    def test_boundary_one(self):
        c = Confidence(value=1.0)
        assert c.value == 1.0
        assert c.is_high

    def test_below_zero_raises(self):
        with pytest.raises(ValueError):
            Confidence(value=-0.1)

    def test_above_one_raises(self):
        with pytest.raises(ValueError):
            Confidence(value=1.1)

    def test_immutability(self):
        c = Confidence(value=0.85)
        with pytest.raises(AttributeError):
            c.value = 0.9


# ---------------------------------------------------------------------------
# ProcessingStatus
# ---------------------------------------------------------------------------


class TestProcessingStatus:
    def test_values(self):
        assert ProcessingStatus.QUEUED.value == "queued"
        assert ProcessingStatus.EXTRACTING.value == "extracting"
        assert ProcessingStatus.CLASSIFYING.value == "classifying"
        assert ProcessingStatus.INDEXING.value == "indexing"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.RETRYING.value == "retrying"

    def test_is_terminal(self):
        assert ProcessingStatus.COMPLETED.is_terminal
        assert ProcessingStatus.FAILED.is_terminal

    def test_is_not_terminal(self):
        assert not ProcessingStatus.QUEUED.is_terminal
        assert not ProcessingStatus.EXTRACTING.is_terminal
        assert not ProcessingStatus.CLASSIFYING.is_terminal
        assert not ProcessingStatus.INDEXING.is_terminal
        assert not ProcessingStatus.RETRYING.is_terminal

    def test_can_retry(self):
        assert ProcessingStatus.FAILED.can_retry
        assert ProcessingStatus.RETRYING.can_retry

    def test_cannot_retry(self):
        assert not ProcessingStatus.COMPLETED.can_retry
        assert not ProcessingStatus.QUEUED.can_retry
        assert not ProcessingStatus.EXTRACTING.can_retry
        assert not ProcessingStatus.INDEXING.can_retry


# ---------------------------------------------------------------------------
# AIProvider
# ---------------------------------------------------------------------------


class TestAIProvider:
    def test_values(self):
        assert AIProvider.OPENAI.value == "openai"
        assert AIProvider.GOOGLE.value == "google"
        assert AIProvider.OLLAMA.value == "ollama"
        assert AIProvider.ANTHROPIC.value == "anthropic"
        assert AIProvider.LOCAL.value == "local"
        assert AIProvider.AZURE.value == "azure"
        assert AIProvider.AWS_BEDROCK.value == "aws_bedrock"
        assert AIProvider.HUGGINGFACE.value == "huggingface"
        assert AIProvider.COHERE.value == "cohere"

    def test_all_members(self):
        assert len(AIProvider) == 9


# ---------------------------------------------------------------------------
# ModelConfig
# ---------------------------------------------------------------------------


class TestModelConfig:
    def test_creation(self):
        config = ModelConfig(model_name="gpt-4o", provider=AIProvider.OPENAI)
        assert config.model_name == "gpt-4o"
        assert config.provider == AIProvider.OPENAI
        assert config.temperature == 0.0
        assert config.max_tokens == 4096

    def test_custom(self):
        config = ModelConfig(
            model_name="claude-3",
            provider=AIProvider.ANTHROPIC,
            temperature=0.7,
            max_tokens=8192,
            top_p=0.9,
        )
        assert config.temperature == 0.7
        assert config.max_tokens == 8192
        assert config.top_p == 0.9

    def test_extra_params(self):
        config = ModelConfig(
            model_name="gpt-4o",
            provider=AIProvider.OPENAI,
            extra_params={"seed": 42},
        )
        assert config.extra_params == {"seed": 42}

    def test_is_local(self):
        assert ModelConfig(provider=AIProvider.LOCAL, model_name="llama").is_local
        assert not ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o").is_local

    def test_supports_streaming(self):
        assert ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o").supports_streaming
        assert ModelConfig(provider=AIProvider.ANTHROPIC, model_name="claude").supports_streaming
        assert ModelConfig(provider=AIProvider.AZURE, model_name="gpt-4o").supports_streaming
        assert not ModelConfig(provider=AIProvider.LOCAL, model_name="llama").supports_streaming
        assert not ModelConfig(provider=AIProvider.OLLAMA, model_name="llama").supports_streaming

    def test_temperature_too_low(self):
        with pytest.raises(ValueError):
            ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", temperature=-0.1)

    def test_temperature_too_high(self):
        with pytest.raises(ValueError):
            ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", temperature=2.1)

    def test_temperature_boundaries(self):
        c1 = ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", temperature=0.0)
        c2 = ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", temperature=2.0)
        assert c1.temperature == 0.0
        assert c2.temperature == 2.0

    def test_max_tokens_zero(self):
        with pytest.raises(ValueError):
            ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", max_tokens=0)

    def test_max_tokens_negative(self):
        with pytest.raises(ValueError):
            ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", max_tokens=-1)

    def test_immutability(self):
        config = ModelConfig(model_name="gpt-4o", provider=AIProvider.OPENAI)
        with pytest.raises(AttributeError):
            config.temperature = 1.0


# ---------------------------------------------------------------------------
# TaskStatus
# ---------------------------------------------------------------------------


class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.TIMEOUT.value == "timeout"

    def test_is_terminal(self):
        assert TaskStatus.COMPLETED.is_terminal
        assert TaskStatus.FAILED.is_terminal
        assert TaskStatus.CANCELLED.is_terminal
        assert TaskStatus.TIMEOUT.is_terminal

    def test_is_not_terminal(self):
        assert not TaskStatus.PENDING.is_terminal
        assert not TaskStatus.RUNNING.is_terminal

    def test_is_success(self):
        assert TaskStatus.COMPLETED.is_success

    def test_is_not_success(self):
        assert not TaskStatus.FAILED.is_success
        assert not TaskStatus.PENDING.is_success
        assert not TaskStatus.RUNNING.is_success
        assert not TaskStatus.CANCELLED.is_success
        assert not TaskStatus.TIMEOUT.is_success
