from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DomainEventBus:
    """Simple in-process event bus for domain events."""

    _handlers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)

    @classmethod
    def subscribe(cls, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        cls._handlers[event_type].append(handler)

    @classmethod
    def unsubscribe(cls, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        if event_type in cls._handlers:
            try:
                cls._handlers[event_type].remove(handler)
            except ValueError:
                logger.warning(
                    "Handler %s not found for event %s", handler.__qualname__, event_type
                )

    @classmethod
    def publish(cls, event_type: str, payload: dict[str, Any]) -> None:
        for handler in cls._handlers.get(event_type, []):
            try:
                handler(payload)
            except Exception:
                logger.exception("Event handler failed for %s", event_type)

    @classmethod
    def clear(cls) -> None:
        cls._handlers.clear()


def _on_file_created(payload: dict[str, Any]) -> None:
    logger.info("Event: file_created file_id=%s path=%s", payload.get("file_id"), payload.get("path"))


def _on_file_deleted(payload: dict[str, Any]) -> None:
    logger.info("Event: file_deleted file_id=%s", payload.get("file_id"))


def _on_document_classified(payload: dict[str, Any]) -> None:
    logger.info("Event: document_classified doc_id=%s type=%s", payload.get("document_id"), payload.get("doc_type"))


def _on_document_indexed(payload: dict[str, Any]) -> None:
    logger.info("Event: document_indexed doc_id=%s chunks=%s", payload.get("document_id"), payload.get("chunk_count"))


# Register default handlers
DomainEventBus.subscribe("file_created", _on_file_created)
DomainEventBus.subscribe("file_deleted", _on_file_deleted)
DomainEventBus.subscribe("document_classified", _on_document_classified)
DomainEventBus.subscribe("document_indexed", _on_document_indexed)


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    Events represent something meaningful that happened in the domain.
    They are immutable records carrying event_type, timestamp, and payload.
    """

    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, event_type: str, **payload: Any) -> DomainEvent:
        """Factory method to create a domain event with a payload."""
        return cls(event_type=event_type, payload=payload)

    def __post_init__(self) -> None:
        if isinstance(self.event_id, str):
            object.__setattr__(self, "event_id", uuid.UUID(self.event_id))
        if isinstance(self.timestamp, str):
            object.__setattr__(
                self, "timestamp", datetime.fromisoformat(self.timestamp)
            )
