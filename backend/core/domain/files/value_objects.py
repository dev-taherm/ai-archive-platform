from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import PurePosixPath


class FileStatus(enum.Enum):
    """Lifecycle status of a file in the archive."""

    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    COMPLETED = "completed"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass(frozen=True)
class FilePath:
    """Immutable value object representing a normalized file path."""

    raw: str

    def __post_init__(self) -> None:
        if not self.raw or not self.raw.strip():
            raise ValueError("FilePath cannot be empty")

    @property
    def normalized(self) -> str:
        return str(PurePosixPath(self.raw).as_posix())

    @property
    def filename(self) -> str:
        return PurePosixPath(self.raw).name

    @property
    def extension(self) -> str:
        return PurePosixPath(self.raw).suffix.lower()

    @property
    def parent(self) -> str:
        return str(PurePosixPath(self.raw).parent)


@dataclass(frozen=True)
class FileSize:
    """Immutable value object representing file size in bytes."""

    bytes: int

    def __post_init__(self) -> None:
        if self.bytes < 0:
            raise ValueError("FileSize cannot be negative")

    @property
    def kilobytes(self) -> float:
        return round(self.bytes / 1024, 2)

    @property
    def megabytes(self) -> float:
        return round(self.bytes / (1024 * 1024), 2)

    @property
    def human_readable(self) -> str:
        if self.bytes < 1024:
            return f"{self.bytes} B"
        if self.bytes < 1024 * 1024:
            return f"{self.kilobytes} KB"
        if self.bytes < 1024 * 1024 * 1024:
            return f"{self.megabytes} MB"
        return f"{round(self.bytes / (1024 * 1024 * 1024), 2)} GB"


@dataclass(frozen=True)
class MimeType:
    """Immutable value object representing a MIME type."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or "/" not in self.value:
            raise ValueError(f"Invalid MIME type: {self.value}")

    @property
    def type(self) -> str:
        return self.value.split("/")[0]

    @property
    def subtype(self) -> str:
        return self.value.split("/")[1]

    @property
    def is_text(self) -> bool:
        return self.type == "text" or self.subtype in {
            "json",
            "xml",
            "javascript",
            "yaml",
            "csv",
        }

    @property
    def is_image(self) -> bool:
        return self.type == "image"

    @property
    def is_pdf(self) -> bool:
        return self.value == "application/pdf"


@dataclass(frozen=True)
class Hash:
    """Immutable value object representing a file hash."""

    algorithm: str
    digest: str

    def __post_init__(self) -> None:
        if not self.algorithm or not self.digest:
            raise ValueError("Hash algorithm and digest cannot be empty")

    @property
    def canonical(self) -> str:
        return f"{self.algorithm}:{self.digest}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Hash):
            return NotImplemented
        return self.digest == other.digest and self.algorithm == other.algorithm

    def __hash__(self) -> int:
        return hash((self.algorithm, self.digest))
