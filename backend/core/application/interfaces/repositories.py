from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Sequence

from core.domain.documents.entities import Document, DocumentChunk
from core.domain.files.entities import FileRecord
from core.domain.files.value_objects import Hash


class FileRepository(ABC):
    """Abstract interface for file persistence operations."""

    @abstractmethod
    def get_by_id(self, file_id: uuid.UUID) -> FileRecord | None:
        """Retrieve a file record by its unique identifier."""

    @abstractmethod
    def save(self, file_record: FileRecord) -> FileRecord:
        """Persist a file record, returning the saved version."""

    @abstractmethod
    def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[FileRecord]:
        """Return all file records with pagination."""

    @abstractmethod
    def delete(self, file_id: uuid.UUID) -> bool:
        """Delete a file record by ID. Returns True if deleted."""

    @abstractmethod
    def get_by_fingerprint(self, fingerprint_hash: Hash) -> Sequence[FileRecord]:
        """Find all files sharing the same content hash."""

    @abstractmethod
    def find_duplicates(self) -> Sequence[dict[str, Any]]:
        """Return groups of duplicate files grouped by fingerprint hash."""


class DocumentRepository(ABC):
    """Abstract interface for document persistence operations."""

    @abstractmethod
    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        """Retrieve a document by its unique identifier."""

    @abstractmethod
    def save(self, document: Document) -> Document:
        """Persist a document, returning the saved version."""

    @abstractmethod
    def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        """Return all documents with pagination."""

    @abstractmethod
    def delete(self, document_id: uuid.UUID) -> bool:
        """Delete a document by ID. Returns True if deleted."""

    @abstractmethod
    def search_by_embedding(
        self,
        embedding_id: str,
        *,
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        """Search document chunks by embedding similarity."""

    @abstractmethod
    def get_chunks_by_document(
        self,
        document_id: uuid.UUID,
    ) -> Sequence[DocumentChunk]:
        """Retrieve all chunks belonging to a document."""


class AITaskRepository(ABC):
    """Abstract interface for AI task queue persistence."""

    @abstractmethod
    def get_by_id(self, task_id: uuid.UUID) -> dict[str, Any] | None:
        """Retrieve an AI task by its unique identifier."""

    @abstractmethod
    def save(self, task: dict[str, Any]) -> dict[str, Any]:
        """Persist an AI task, returning the saved version."""

    @abstractmethod
    def list_pending(
        self,
        *,
        task_type: str | None = None,
        limit: int = 50,
    ) -> Sequence[dict[str, Any]]:
        """Return pending AI tasks, optionally filtered by type."""


class EmbeddingRepository(ABC):
    """Abstract interface for embedding vector persistence."""

    @abstractmethod
    def save(
        self,
        vector_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store an embedding vector with optional metadata. Returns the vector ID."""

    @abstractmethod
    def search_similar(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 10,
        threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> Sequence[tuple[str, float, dict[str, Any]]]:
        """Find the most similar embeddings to a query vector."""

    @abstractmethod
    def delete(self, vector_id: str) -> bool:
        """Delete an embedding vector by ID. Returns True if deleted."""

    @abstractmethod
    def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        """Delete embeddings matching metadata filter. Returns count deleted."""


class AuditLogRepository(ABC):
    """Abstract interface for audit log persistence."""

    @abstractmethod
    def save(self, log_entry: dict[str, Any]) -> None:
        """Persist an audit log entry."""

    @abstractmethod
    def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[dict[str, Any]]:
        """Return audit log entries for a specific user."""

    @abstractmethod
    def list_by_resource(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[dict[str, Any]]:
        """Return audit log entries for a specific resource."""


class UserRepository(ABC):
    """Abstract interface for user persistence operations."""

    @abstractmethod
    def get_by_id(self, user_id: uuid.UUID) -> dict[str, Any] | None:
        """Retrieve a user by their unique identifier."""

    @abstractmethod
    def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Retrieve a user by their email address."""

    @abstractmethod
    def save(self, user: dict[str, Any]) -> dict[str, Any]:
        """Persist a user, returning the saved version."""

    @abstractmethod
    def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[dict[str, Any]]:
        """Return all users with pagination."""
