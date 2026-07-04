import pytest
import uuid

from core.domain.files.value_objects import Hash, FileSize, MimeType, FilePath, FileStatus
from core.domain.files.entities import FileFingerprint, FileRecord
from core.domain.documents.value_objects import DocumentType, Language, Confidence, ProcessingStatus
from core.domain.ai.value_objects import AIProvider, ModelConfig


@pytest.fixture
def sample_hash():
    return Hash(algorithm="sha256", digest="abc123def456")


@pytest.fixture
def sample_file_size():
    return FileSize(bytes=1024)


@pytest.fixture
def sample_mime_type():
    return MimeType(value="application/pdf")


@pytest.fixture
def sample_file_path():
    return FilePath(raw="/documents/test.pdf")


@pytest.fixture
def sample_document_type():
    return DocumentType.PDF


@pytest.fixture
def sample_language():
    return Language.EN


@pytest.fixture
def sample_confidence():
    return Confidence(value=0.95)


@pytest.fixture
def sample_model_config():
    return ModelConfig(
        model_name="gpt-4o",
        provider=AIProvider.OPENAI,
    )


@pytest.fixture
def sample_file_record():
    return FileRecord(
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
