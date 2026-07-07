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


# ---------------------------------------------------------------------------
# Agent fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_agent(test_user):
    from apps.agents.models import Agent
    return Agent.objects.create(
        user=test_user,
        agent_id="test-agent-01",
        name="Test Agent",
        status="offline",
        platform="linux",
        hostname="test-host",
        agent_version="0.1.0",
        capabilities=["scan", "ocr", "parse"],
        sync_interval_minutes=30,
        max_file_size_mb=100,
    )


@pytest.fixture
def sample_agent_folder(sample_agent):
    from apps.agents.models import AgentFolder
    return AgentFolder.objects.create(
        agent=sample_agent,
        local_path="/home/user/documents",
        label="Documents",
        is_active=True,
        file_count=10,
    )


@pytest.fixture
def sample_agent_command(sample_agent):
    from apps.agents.models import AgentCommand
    return AgentCommand.objects.create(
        agent=sample_agent,
        command_type="sync",
        payload={},
        status="pending",
    )


# ---------------------------------------------------------------------------
# Report fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_report(test_user):
    from apps.reports.models import Report
    return Report.objects.create(
        report_type="archive_summary",
        title="Test Report",
        status="completed",
        generated_by=test_user,
        data={"total_files": 42, "total_documents": 10},
    )


# ---------------------------------------------------------------------------
# API Key fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_api_key(test_user):
    from apps.apikeys.models import ApiKey
    key_instance, raw_key = ApiKey.create_key(test_user, name="test-key")
    return key_instance


# ---------------------------------------------------------------------------
# Search fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_saved_search(test_user):
    from apps.search.models import SavedSearch
    return SavedSearch.objects.create(
        user=test_user,
        name="My Search",
        query="invoice 2024",
        search_type="hybrid",
        filters={"doc_type": "invoice"},
    )


@pytest.fixture
def sample_search_log(test_user):
    from apps.search.models import SearchLog
    return SearchLog.objects.create(
        user_id=test_user.pk,
        query="test query",
        search_type="hybrid",
        result_count=5,
        search_time_ms=12.5,
    )
