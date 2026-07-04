from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SearchFiltersDTO:
    """Data transfer object for search filtering criteria."""

    doc_types: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    date_from: datetime | None = None
    date_to: datetime | None = None
    min_score: float = 0.0
    file_extensions: tuple[str, ...] = ()
    exclude_duplicates: bool = True


@dataclass(frozen=True)
class SearchQueryDTO:
    """Data transfer object for search query parameters."""

    query: str
    user_id: uuid.UUID | None = None
    search_type: str = "hybrid"
    max_results: int = 20
    offset: int = 0
    filters: SearchFiltersDTO = field(default_factory=SearchFiltersDTO)
    include_chunks: bool = False


@dataclass(frozen=True)
class SearchResultDTO:
    """Data transfer object for a single search result."""

    document_id: uuid.UUID
    file_id: uuid.UUID
    title: str
    snippet: str
    score: float
    rank: int
    doc_type: str = "unknown"
    language: str = "unknown"
    match_source: str = ""
    highlights: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResponseDTO:
    """Data transfer object for search response with metadata."""

    query: str
    results: tuple[SearchResultDTO, ...]
    total_count: int
    search_time_ms: float
    search_type: str = "hybrid"
    applied_filters: SearchFiltersDTO = field(default_factory=SearchFiltersDTO)

    @property
    def has_results(self) -> bool:
        """Whether the search returned any results."""
        return len(self.results) > 0

    @property
    def page_count(self) -> int:
        """Estimated number of pages based on max_results (default 20)."""
        if not self.results:
            return 0
        return max(1, -(-self.total_count // 20))
