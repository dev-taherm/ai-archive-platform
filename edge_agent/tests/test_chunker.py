"""Tests for edge_agent.core.chunker — text chunking."""
import pytest

from edge_agent.core.chunker import Chunk, chunk_text, chunk_size_min


class TestChunkText:
    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        chunks = chunk_text("Hello world")
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world"
        assert chunks[0].index == 0
        assert chunks[0].start_char == 0

    def test_long_text_multiple_chunks(self):
        text = "word " * 500  # 2500 chars
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        text = "a" * 2000
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        for i in range(1, len(chunks)):
            assert chunks[i].start_char < chunks[i - 1].end_char

    def test_chunk_indices_are_sequential(self):
        text = "word " * 500
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_split_at_paragraph_boundary(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph." * 20
        chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)
        assert len(chunks) > 1


class TestChunkSizeMin:
    def test_large_total(self):
        assert chunk_size_min(10000) == 3000  # 30% of 10000

    def test_small_total(self):
        assert chunk_size_min(100) == 100  # minimum floor

    def test_medium_total(self):
        assert chunk_size_min(1000) == 300
