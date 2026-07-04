import pytest
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        username="testuser",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def second_user(db):
    return User.objects.create_user(
        email="second@example.com",
        password="secondpass123",
        username="seconduser",
        first_name="Second",
        last_name="User",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        username="adminuser",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def auth_client(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def auth_client_second(api_client, second_user):
    api_client.force_authenticate(user=second_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def sample_file_record():
    from apps.files.models import FileRecord
    return FileRecord.objects.create(
        path="/tmp/test_document.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        status="pending",
        content_hash="abc123def456",
        tags=["test", "sample"],
    )


@pytest.fixture
def completed_file_record():
    from apps.files.models import FileRecord
    return FileRecord.objects.create(
        path="/tmp/completed_document.pdf",
        mime_type="application/pdf",
        size_bytes=2048,
        status="pending",
        content_hash="completed_hash_123",
        tags=["completed"],
    )


@pytest.fixture
def sample_document(test_user, sample_file_record):
    from apps.documents.models import Document
    return Document.objects.create(
        file_id=sample_file_record.id,
        doc_type="pdf",
        processing_status="completed",
        title="Test Invoice Document",
        author="Test Author",
        subject="Test Subject",
        language="en",
        word_count=500,
        page_count=3,
        chunk_count=5,
        classification_confidence=0.92,
        tags=["invoice", "test"],
        extracted_text="This is a test invoice for services rendered...",
    )


@pytest.fixture
def sample_workflow(test_user):
    from apps.workflows.models import Workflow
    return Workflow.objects.create(
        name="Test Workflow",
        description="A test processing workflow",
        trigger_type="manual",
        steps=[
            {"name": "OCR Step", "step_type": "ocr", "order": 0},
            {"name": "Classify Step", "step_type": "classify", "order": 1},
        ],
        is_active=True,
        created_by=test_user,
    )


@pytest.fixture
def inactive_workflow(test_user):
    from apps.workflows.models import Workflow
    return Workflow.objects.create(
        name="Inactive Workflow",
        description="An inactive workflow",
        trigger_type="manual",
        steps=[],
        is_active=False,
        created_by=test_user,
    )


@pytest.fixture
def sample_provider():
    from apps.ai.models import ProviderConfig
    return ProviderConfig.objects.create(
        name="openai",
        display_name="OpenAI",
        provider_type="openai",
        capabilities=["llm", "embedding"],
        api_key="sk-test123",
        base_url="https://api.openai.com/v1",
        model_name="gpt-4o",
        is_active=True,
        is_default=True,
    )


@pytest.fixture
def mock_file_service():
    with patch("apps.files.apps.FilesConfig.file_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_document_service():
    with patch("apps.documents.apps.DocumentsConfig.document_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_ai_service():
    with patch("apps.ai.apps.AIConfig.ai_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_search_service():
    with patch("apps.search.apps.SearchConfig.search_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_chat_service():
    with patch("apps.chat.apps.ChatConfig.chat_service") as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


@pytest.fixture
def sample_upload_file():
    return SimpleUploadedFile(
        name="test_document.pdf",
        content=b"%PDF-1.4 fake pdf content for testing",
        content_type="application/pdf",
    )


@pytest.fixture
def sample_txt_upload_file():
    return SimpleUploadedFile(
        name="test_notes.txt",
        content=b"This is a test text file with some content for testing.",
        content_type="text/plain",
    )
