from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from core.domain.common.events import DomainEvent


@dataclass(frozen=True)
class DocumentClassified(DomainEvent):
    """Emitted when a document has been classified."""

    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    doc_type: str = ""
    confidence: float = 0.0

    def __init__(self, document_id: uuid.UUID, doc_type: str, confidence: float) -> None:
        super().__init__(
            event_type="document.classified",
            payload={
                "document_id": str(document_id),
                "doc_type": doc_type,
                "confidence": confidence,
            },
        )
        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "doc_type", doc_type)
        object.__setattr__(self, "confidence", confidence)


@dataclass(frozen=True)
class DocumentIndexed(DomainEvent):
    """Emitted when a document has been fully indexed."""

    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    chunk_count: int = 0

    def __init__(self, document_id: uuid.UUID, chunk_count: int) -> None:
        super().__init__(
            event_type="document.indexed",
            payload={
                "document_id": str(document_id),
                "chunk_count": chunk_count,
            },
        )
        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "chunk_count", chunk_count)
