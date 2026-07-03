from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.domain.search.value_objects import SearchFilters, SearchMode, SortOrder


@dataclass(frozen=True)
class SearchQuery:
    """Represents a user's search request."""

    text: str
    mode: SearchMode = SearchMode.HYBRID
    filters: SearchFilters = field(default_factory=SearchFilters)
    sort_by: str = "relevance"
    sort_order: SortOrder = SortOrder.DESC
    limit: int = 20
    offset: int = 0
    user_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 100:
            raise ValueError(f"Limit must be 1-100, got {self.limit}")
        if self.offset < 0:
            raise ValueError(f"Offset must be >= 0, got {self.offset}")

    @property
    def page(self) -> int:
        if self.limit == 0:
            return 1
        return (self.offset // self.limit) + 1

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


@dataclass(frozen=True)
class SearchResult:
    """A single search result hit."""

    document_id: uuid.UUID
    score: float
    content_snippet: str
    title: str = ""
    path: str = ""
    highlight: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_relevant(self) -> bool:
        return self.score >= 0.5


@dataclass(frozen=True)
class SearchResponse:
    """Aggregated search response with results and metadata."""

    query: SearchQuery
    results: tuple[SearchResult, ...] = ()
    total_count: int = 0
    processing_time_ms: float = 0.0
    suggestions: tuple[str, ...] = ()

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0

    @property
    def page_count(self) -> int:
        if self.query.limit == 0:
            return 0
        return -(-self.total_count // self.query.limit)

    @property
    def current_page(self) -> int:
        return self.query.page
