from __future__ import annotations

import uuid
from typing import Any, Sequence

from core.application.interfaces.repositories import (
    AuditLogRepository,
    AITaskRepository,
    DocumentRepository,
    EmbeddingRepository,
    FileRepository,
)
from core.application.interfaces.services import (
    EmbeddingProvider,
    LLMProvider,
)
from core.domain.files.entities import FileRecord
from core.domain.files.value_objects import Hash


# ---------------------------------------------------------------------------
# Repository mocks
# ---------------------------------------------------------------------------


class MockFileRepository(FileRepository):
    def __init__(self) -> None:
        self._files: dict[uuid.UUID, FileRecord] = {}

    def get_by_id(self, file_id: uuid.UUID) -> FileRecord | None:
        return self._files.get(file_id)

    def save(self, file_record: FileRecord) -> FileRecord:
        self._files[file_record.id] = file_record
        return file_record

    def list_all(self, *, offset: int = 0, limit: int = 100) -> Sequence[FileRecord]:
        return list(self._files.values())[offset : offset + limit]

    def delete(self, file_id: uuid.UUID) -> bool:
        return self._files.pop(file_id, None) is not None

    def get_by_fingerprint(self, fingerprint_hash: Hash) -> Sequence[FileRecord]:
        return [f for f in self._files.values() if f.fingerprint.content_hash == fingerprint_hash]

    def find_duplicates(self) -> Sequence[dict[str, Any]]:
        return []


class MockDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._docs: dict[uuid.UUID, Any] = {}

    def get_by_id(self, document_id: uuid.UUID) -> Any | None:
        return self._docs.get(document_id)

    def get_by_file_id(self, file_id: uuid.UUID) -> Any | None:
        for doc in self._docs.values():
            if getattr(doc, "file_id", None) == file_id:
                return doc
        return None

    def save(self, document: Any) -> Any:
        self._docs[document.id] = document
        return document

    def list_all(self, *, offset: int = 0, limit: int = 100) -> Sequence[Any]:
        return list(self._docs.values())[offset : offset + limit]

    def delete(self, document_id: uuid.UUID) -> bool:
        return self._docs.pop(document_id, None) is not None

    def search_by_embedding(
        self,
        embedding_id: str,
        *,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> Sequence[tuple]:
        return []

    def get_chunks_by_document(self, document_id: uuid.UUID) -> Sequence:
        return []


class MockAITaskRepository(AITaskRepository):
    def __init__(self) -> None:
        self._tasks: dict[uuid.UUID, dict[str, Any]] = {}

    def get_by_id(self, task_id: uuid.UUID) -> dict[str, Any] | None:
        return self._tasks.get(task_id)

    def save(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = task.get("id", uuid.uuid4())
        task["id"] = str(task_id)
        self._tasks[uuid.UUID(task_id) if isinstance(task_id, str) else task_id] = task
        return task

    def list_pending(
        self,
        *,
        task_type: str | None = None,
        limit: int = 50,
    ) -> Sequence[dict[str, Any]]:
        return []


class MockEmbeddingRepository(EmbeddingRepository):
    def __init__(self) -> None:
        self._embeddings: dict[str, dict[str, Any]] = {}

    def save(
        self,
        vector_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        self._embeddings[vector_id] = {
            "embedding": embedding,
            "metadata": metadata or {},
        }
        return vector_id

    def search_similar(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 10,
        threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> Sequence[tuple[str, float, dict[str, Any]]]:
        return []

    def delete(self, vector_id: str) -> bool:
        return self._embeddings.pop(vector_id, None) is not None

    def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        return 0


class MockAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self._logs: list[dict[str, Any]] = []

    def save(self, log_entry: dict[str, Any]) -> None:
        self._logs.append(log_entry)

    def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[dict[str, Any]]:
        return [l for l in self._logs if l.get("user_id") == user_id][offset : offset + limit]

    def list_by_resource(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[dict[str, Any]]:
        return []


# ---------------------------------------------------------------------------
# Service / provider mocks
# ---------------------------------------------------------------------------


class MockLLMProvider(LLMProvider):
    def classify(
        self,
        text: str,
        *,
        categories: list[str],
        system_prompt: str | None = None,
    ) -> tuple[str, float]:
        return ("contract", 0.95)

    def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        return {field: f"extracted_{field}" for field in fields}

    def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        return "This is a summary of the document."

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        return "This is a chat response."


class MockEmbeddingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 384

    def embed_text(self, text: str) -> list[float]:
        return [0.1] * 384

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]



