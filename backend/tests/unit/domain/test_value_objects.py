import pytest

from core.domain.files.value_objects import Hash, FileSize, MimeType, FilePath, FileStatus
from core.domain.ai.value_objects import AIProvider, ModelConfig, TaskStatus


# --- Hash ---


def test_hash_creation():
    h = Hash(algorithm="sha256", digest="abc123def456")
    assert h.algorithm == "sha256"
    assert h.digest == "abc123def456"


def test_hash_canonical():
    h = Hash(algorithm="sha256", digest="abc123def456")
    assert h.canonical == "sha256:abc123def456"


def test_hash_equality():
    h1 = Hash(algorithm="sha256", digest="abc123")
    h2 = Hash(algorithm="sha256", digest="abc123")
    h3 = Hash(algorithm="sha256", digest="def456")
    h4 = Hash(algorithm="md5", digest="abc123")
    assert h1 == h2
    assert h1 != h3
    assert h1 != h4


def test_hash_in_set():
    h1 = Hash(algorithm="sha256", digest="abc123")
    h2 = Hash(algorithm="sha256", digest="abc123")
    assert len({h1, h2}) == 1


def test_hash_empty_raises():
    with pytest.raises(ValueError):
        Hash(algorithm="", digest="abc123")
    with pytest.raises(ValueError):
        Hash(algorithm="sha256", digest="")


# --- FilePath ---


def test_file_path_creation():
    fp = FilePath(raw="/documents/test.pdf")
    assert fp.raw == "/documents/test.pdf"


def test_file_path_normalized():
    fp = FilePath(raw="/test/file.pdf")
    assert fp.normalized == "/test/file.pdf"


def test_file_path_filename():
    fp = FilePath(raw="/documents/test.pdf")
    assert fp.filename == "test.pdf"


def test_file_path_extension():
    fp = FilePath(raw="/documents/test.pdf")
    assert fp.extension == ".pdf"


def test_file_path_parent():
    fp = FilePath(raw="/documents/test.pdf")
    assert fp.parent == "/documents"


def test_file_path_empty_raises():
    with pytest.raises(ValueError):
        FilePath(raw="")
    with pytest.raises(ValueError):
        FilePath(raw="   ")


# --- FileSize ---


def test_file_size_bytes():
    s = FileSize(bytes=1048576)
    assert s.bytes == 1048576


def test_file_size_kilobytes():
    s = FileSize(bytes=2048)
    assert s.kilobytes == 2.0


def test_file_size_megabytes():
    s = FileSize(bytes=2097152)
    assert s.megabytes == 2.0


def test_file_size_human_readable_bytes():
    assert FileSize(bytes=500).human_readable == "500 B"


def test_file_size_human_readable_kb():
    assert FileSize(bytes=1536).human_readable == "1.5 KB"


def test_file_size_human_readable_mb():
    assert FileSize(bytes=2097152).human_readable == "2.0 MB"


def test_file_size_negative_raises():
    with pytest.raises(ValueError):
        FileSize(bytes=-1)


# --- MimeType ---


def test_mime_type_creation():
    m = MimeType(value="application/pdf")
    assert m.value == "application/pdf"


def test_mime_type_type_and_subtype():
    m = MimeType(value="text/plain")
    assert m.type == "text"
    assert m.subtype == "plain"


def test_mime_type_is_text():
    assert MimeType(value="text/plain").is_text
    assert MimeType(value="application/json").is_text
    assert not MimeType(value="application/pdf").is_text


def test_mime_type_is_image():
    assert MimeType(value="image/png").is_image
    assert not MimeType(value="application/pdf").is_image


def test_mime_type_is_pdf():
    assert MimeType(value="application/pdf").is_pdf
    assert not MimeType(value="text/plain").is_pdf


def test_mime_type_invalid_raises():
    with pytest.raises(ValueError):
        MimeType(value="")
    with pytest.raises(ValueError):
        MimeType(value="invalid-no-slash")


# --- FileStatus ---


def test_file_status_values():
    assert FileStatus.PENDING.value == "pending"
    assert FileStatus.INDEXING.value == "indexing"
    assert FileStatus.INDEXED.value == "indexed"
    assert FileStatus.DUPLICATE.value == "duplicate"
    assert FileStatus.FAILED.value == "failed"
    assert FileStatus.DELETED.value == "deleted"


# --- AIProvider ---


def test_ai_provider_values():
    assert AIProvider.OPENAI.value == "openai"
    assert AIProvider.GOOGLE.value == "google"
    assert AIProvider.OLLAMA.value == "ollama"
    assert AIProvider.ANTHROPIC.value == "anthropic"
    assert AIProvider.LOCAL.value == "local"


# --- ModelConfig ---


def test_model_config_creation():
    config = ModelConfig(
        model_name="gpt-4o",
        provider=AIProvider.OPENAI,
    )
    assert config.model_name == "gpt-4o"
    assert config.provider == AIProvider.OPENAI
    assert config.temperature == 0.0
    assert config.max_tokens == 4096


def test_model_config_custom():
    config = ModelConfig(
        model_name="claude-3",
        provider=AIProvider.ANTHROPIC,
        temperature=0.7,
        max_tokens=8192,
    )
    assert config.temperature == 0.7
    assert config.max_tokens == 8192


def test_model_config_is_local():
    local_config = ModelConfig(provider=AIProvider.LOCAL, model_name="llama")
    remote_config = ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o")
    assert local_config.is_local
    assert not remote_config.is_local


def test_model_config_supports_streaming():
    assert ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o").supports_streaming
    assert ModelConfig(provider=AIProvider.ANTHROPIC, model_name="claude").supports_streaming
    assert ModelConfig(provider=AIProvider.LOCAL, model_name="llama").supports_streaming is False


def test_model_config_invalid_temperature():
    with pytest.raises(ValueError):
        ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", temperature=-0.1)
    with pytest.raises(ValueError):
        ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", temperature=2.1)


def test_model_config_invalid_max_tokens():
    with pytest.raises(ValueError):
        ModelConfig(provider=AIProvider.OPENAI, model_name="gpt-4o", max_tokens=0)


# --- TaskStatus ---


def test_task_status_values():
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"
    assert TaskStatus.TIMEOUT.value == "timeout"


def test_task_status_is_terminal():
    assert TaskStatus.COMPLETED.is_terminal
    assert TaskStatus.FAILED.is_terminal
    assert TaskStatus.CANCELLED.is_terminal
    assert TaskStatus.TIMEOUT.is_terminal
    assert not TaskStatus.PENDING.is_terminal
    assert not TaskStatus.RUNNING.is_terminal


def test_task_status_is_success():
    assert TaskStatus.COMPLETED.is_success
    assert not TaskStatus.FAILED.is_success
    assert not TaskStatus.PENDING.is_success
