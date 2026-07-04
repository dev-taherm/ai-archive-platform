from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# On-disk vector store: chunks + embeddings in a JSON file
# Production: replace with pgvector
DEFAULT_STORE_PATH = Path("/home/taher/Documents/ai-archive-platform/backend/data/vector_store.json")


class VectorStore:
    """In-memory + on-disk vector store using numpy for cosine similarity.

    Stores document chunks with their embeddings and provides
    approximate nearest neighbor search via brute-force cosine similarity.

    Production upgrade: swap with pgvector for PostgreSQL-native vector search.
    """

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._path = Path(store_path) if store_path else DEFAULT_STORE_PATH
        self._entries: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        """Load entries from disk if available."""
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = json.load(f)
                self._entries = data.get("entries", [])
                if self._entries:
                    self._rebuild_index()
                logger.info("Loaded %d entries from vector store", len(self._entries))
            except Exception as e:
                logger.warning("Failed to load vector store: %s", e)
                self._entries = []

    def _save(self) -> None:
        """Persist entries to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {"entries": self._entries}
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)

    def _rebuild_index(self) -> None:
        """Rebuild the numpy embedding matrix."""
        if not self._entries:
            self._embeddings = None
            return
        vectors = [e["embedding"] for e in self._entries]
        self._embeddings = np.array(vectors, dtype=np.float32)

    @property
    def count(self) -> int:
        return len(self._entries)

    @property
    def dimension(self) -> int:
        if self._embeddings is not None and len(self._embeddings) > 0:
            return self._embeddings.shape[1]
        return 0

    def add(
        self,
        entry_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add an entry to the store."""
        self._entries.append({
            "id": entry_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
        })
        self._rebuild_index()

    def add_batch(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
    ) -> int:
        """Add multiple entries. Returns count added."""
        if not ids:
            return 0

        meta_list = metadata or [{} for _ in ids]
        for entry_id, text, emb, meta in zip(ids, texts, embeddings, meta_list):
            self._entries.append({
                "id": entry_id,
                "text": text,
                "embedding": emb,
                "metadata": meta,
            })
        self._rebuild_index()
        return len(ids)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar entries using cosine similarity.

        Args:
            query_embedding: Query vector.
            top_k: Number of results to return.
            threshold: Minimum similarity score (0.0-1.0).
            filter_metadata: Optional metadata filter (exact match).

        Returns:
            List of dicts with keys: id, text, score, metadata.
        """
        if not self._entries or self._embeddings is None:
            return []

        query = np.array(query_embedding, dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != self._embeddings.shape[1]:
            logger.warning("Query embedding dimension mismatch: %d vs %d", query.shape[0], self._embeddings.shape[1])
            return []

        # Cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []

        # Avoid division by zero
        norms = np.where(norms == 0, 1.0, norms)
        similarities = (self._embeddings @ query) / (norms * query_norm)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < threshold:
                continue

            entry = self._entries[idx]

            # Apply metadata filter
            if filter_metadata:
                entry_meta = entry.get("metadata", {})
                if not all(entry_meta.get(k) == v for k, v in filter_metadata.items()):
                    continue

            results.append({
                "id": entry["id"],
                "text": entry["text"],
                "score": score,
                "metadata": entry.get("metadata", {}),
            })

        return results

    def delete(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        before = len(self._entries)
        self._entries = [e for e in self._entries if e["id"] != entry_id]
        if len(self._entries) < before:
            self._rebuild_index()
            return True
        return False

    def delete_by_document(self, document_id: str) -> int:
        """Delete all entries for a document. Returns count deleted."""
        before = len(self._entries)
        self._entries = [
            e for e in self._entries
            if e.get("metadata", {}).get("document_id") != document_id
        ]
        deleted = before - len(self._entries)
        if deleted > 0:
            self._rebuild_index()
        return deleted

    def clear(self) -> int:
        """Clear all entries. Returns count cleared."""
        count = len(self._entries)
        self._entries = []
        self._embeddings = None
        return count

    def get_entry(self, entry_id: str) -> dict[str, Any] | None:
        """Get an entry by ID."""
        for e in self._entries:
            if e["id"] == entry_id:
                return {"id": e["id"], "text": e["text"], "metadata": e.get("metadata", {})}
        return None
