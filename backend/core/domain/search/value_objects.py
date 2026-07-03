from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class SearchMode(enum.Enum):
    """Search strategy to use."""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    EXACT = "exact"


class SortOrder(enum.Enum):
    """Sort direction for results."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class SearchFilters:
    """Immutable filters applied to search queries."""

    document_types: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    language: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    min_size: int | None = None
    max_size: int | None = None
    file_statuses: tuple[str, ...] = ()
    authors: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def has_filters(self) -> bool:
        return any([
            self.document_types,
            self.tags,
            self.language,
            self.date_from,
            self.date_to,
            self.min_size is not None,
            self.max_size is not None,
            self.file_statuses,
            self.authors,
            self.extra,
        ])

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.document_types:
            result["document_types"] = list(self.document_types)
        if self.tags:
            result["tags"] = list(self.tags)
        if self.language:
            result["language"] = self.language
        if self.date_from:
            result["date_from"] = self.date_from
        if self.date_to:
            result["date_to"] = self.date_to
        if self.min_size is not None:
            result["min_size"] = self.min_size
        if self.max_size is not None:
            result["max_size"] = self.max_size
        if self.file_statuses:
            result["file_statuses"] = list(self.file_statuses)
        if self.authors:
            result["authors"] = list(self.authors)
        if self.extra:
            result["extra"] = self.extra
        return result
