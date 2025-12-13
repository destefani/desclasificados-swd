"""Unit tests for chunked PDF processing."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from app.utils.chunked_pdf import (
    ChunkResult,
    needs_chunking,
    merge_chunk_results,
    DEFAULT_CHUNK_THRESHOLD,
    DEFAULT_CHUNK_SIZE,
)


class TestNeedsChunking:
    """Tests for needs_chunking function."""

    def test_small_document_no_chunking(self):
        """Small documents don't need chunking."""
        with patch("app.utils.chunked_pdf.get_pdf_page_count") as mock_count:
            mock_count.return_value = 10
            result = needs_chunking(Path("test.pdf"))
            assert result is False

    def test_large_document_needs_chunking(self):
        """Large documents need chunking."""
        with patch("app.utils.chunked_pdf.get_pdf_page_count") as mock_count:
            mock_count.return_value = 50
            result = needs_chunking(Path("test.pdf"))
            assert result is True

    def test_threshold_boundary(self):
        """Document at threshold doesn't need chunking."""
        with patch("app.utils.chunked_pdf.get_pdf_page_count") as mock_count:
            mock_count.return_value = DEFAULT_CHUNK_THRESHOLD
            result = needs_chunking(Path("test.pdf"))
            assert result is False

    def test_custom_threshold(self):
        """Custom threshold is respected."""
        with patch("app.utils.chunked_pdf.get_pdf_page_count") as mock_count:
            mock_count.return_value = 15
            # With threshold=10, 15 pages should need chunking
            assert needs_chunking(Path("test.pdf"), threshold=10) is True
            # With threshold=20, 15 pages should not need chunking
            assert needs_chunking(Path("test.pdf"), threshold=20) is False


class TestMergeChunkResults:
    """Tests for merge_chunk_results function."""

    def test_merge_single_chunk(self):
        """Single chunk merge returns chunk data."""
        chunk = ChunkResult(
            chunk_index=0,
            start_page=1,
            end_page=10,
            success=True,
            data={
                "original_text": "Page 1 content",
                "reviewed_text": "Page 1 reviewed",
                "metadata": {
                    "document_title": "Test Document",
                    "people_mentioned": ["PERSON, ONE"],
                    "keywords": ["TEST"],
                },
                "confidence": {"overall": 0.9, "concerns": ["Minor issue"]},
            },
        )

        result = merge_chunk_results([chunk], "test.pdf", 10)

        assert "Test Document" in str(result["metadata"]["document_title"])
        assert "Page 1 reviewed" in result["reviewed_text"]
        assert result["confidence"]["overall"] == 0.9

    def test_merge_multiple_chunks(self):
        """Multiple chunks are merged correctly."""
        chunks = [
            ChunkResult(
                chunk_index=0,
                start_page=1,
                end_page=20,
                success=True,
                data={
                    "original_text": "Chunk 1 text",
                    "reviewed_text": "Chunk 1 reviewed",
                    "metadata": {
                        "document_title": "Test Document",
                        "people_mentioned": ["PERSON, ONE"],
                        "keywords": ["KEYWORD1"],
                        "country": ["CHILE"],
                    },
                    "confidence": {"overall": 0.9, "concerns": ["Issue 1"]},
                },
            ),
            ChunkResult(
                chunk_index=1,
                start_page=21,
                end_page=40,
                success=True,
                data={
                    "original_text": "Chunk 2 text",
                    "reviewed_text": "Chunk 2 reviewed",
                    "metadata": {
                        "document_title": "Test Document",
                        "people_mentioned": ["PERSON, TWO"],
                        "keywords": ["KEYWORD2"],
                        "country": ["USA"],
                    },
                    "confidence": {"overall": 0.8, "concerns": ["Issue 2"]},
                },
            ),
        ]

        result = merge_chunk_results(chunks, "test.pdf", 40)

        # Text should be concatenated with markers
        assert "Chunk 1 reviewed" in result["reviewed_text"]
        assert "Chunk 2 reviewed" in result["reviewed_text"]
        assert "Pages 1-20" in result["reviewed_text"]
        assert "Pages 21-40" in result["reviewed_text"]

        # Arrays should be merged
        assert "PERSON, ONE" in result["metadata"]["people_mentioned"]
        assert "PERSON, TWO" in result["metadata"]["people_mentioned"]
        assert "KEYWORD1" in result["metadata"]["keywords"]
        assert "KEYWORD2" in result["metadata"]["keywords"]
        assert "CHILE" in result["metadata"]["country"]
        assert "USA" in result["metadata"]["country"]

        # Confidence should be averaged
        assert result["confidence"]["overall"] == 0.85

        # Concerns should be merged
        assert "Issue 1" in result["confidence"]["concerns"]
        assert "Issue 2" in result["confidence"]["concerns"]

        # Page count should be set
        assert result["metadata"]["page_count"] == 40

    def test_merge_with_failed_chunks(self):
        """Failed chunks are excluded from merge."""
        chunks = [
            ChunkResult(
                chunk_index=0,
                start_page=1,
                end_page=20,
                success=True,
                data={
                    "original_text": "Good content",
                    "reviewed_text": "Good reviewed",
                    "metadata": {"document_title": "Test"},
                    "confidence": {"overall": 0.9, "concerns": []},
                },
            ),
            ChunkResult(
                chunk_index=1,
                start_page=21,
                end_page=40,
                success=False,
                error="API error",
            ),
        ]

        result = merge_chunk_results(chunks, "test.pdf", 40)

        assert "Good reviewed" in result["reviewed_text"]
        assert result["confidence"]["overall"] == 0.9

    def test_merge_all_failed(self):
        """All failed chunks returns error result."""
        chunks = [
            ChunkResult(
                chunk_index=0,
                start_page=1,
                end_page=20,
                success=False,
                error="Error 1",
            ),
            ChunkResult(
                chunk_index=1,
                start_page=21,
                end_page=40,
                success=False,
                error="Error 2",
            ),
        ]

        result = merge_chunk_results(chunks, "test.pdf", 40)

        assert result["confidence"]["overall"] == 0.0
        assert "All chunks failed" in result["confidence"]["concerns"][0]

    def test_merge_deduplicates_arrays(self):
        """Duplicate values in arrays are removed."""
        chunks = [
            ChunkResult(
                chunk_index=0,
                start_page=1,
                end_page=20,
                success=True,
                data={
                    "metadata": {
                        "people_mentioned": ["PINOCHET, AUGUSTO", "ALLENDE, SALVADOR"],
                        "keywords": ["HUMAN RIGHTS", "COUP"],
                    },
                    "original_text": "text",
                    "reviewed_text": "text",
                    "confidence": {"overall": 0.9, "concerns": []},
                },
            ),
            ChunkResult(
                chunk_index=1,
                start_page=21,
                end_page=40,
                success=True,
                data={
                    "metadata": {
                        "people_mentioned": ["PINOCHET, AUGUSTO", "LETELIER, ORLANDO"],
                        "keywords": ["HUMAN RIGHTS", "ASSASSINATION"],
                    },
                    "original_text": "text",
                    "reviewed_text": "text",
                    "confidence": {"overall": 0.8, "concerns": []},
                },
            ),
        ]

        result = merge_chunk_results(chunks, "test.pdf", 40)

        # Should have 3 unique people (PINOCHET only once)
        assert len(result["metadata"]["people_mentioned"]) == 3
        assert result["metadata"]["people_mentioned"].count("PINOCHET, AUGUSTO") == 1

        # Should have 3 unique keywords (HUMAN RIGHTS only once)
        assert len(result["metadata"]["keywords"]) == 3

    def test_merge_financial_references(self):
        """Financial references are merged correctly."""
        chunks = [
            ChunkResult(
                chunk_index=0,
                start_page=1,
                end_page=20,
                success=True,
                data={
                    "metadata": {
                        "financial_references": {
                            "amounts": [{"value": "1000000", "currency": "USD", "context": "aid"}],
                            "financial_actors": ["CIA"],
                            "purposes": ["COVERT OPERATION"],
                        }
                    },
                    "original_text": "text",
                    "reviewed_text": "text",
                    "confidence": {"overall": 0.9, "concerns": []},
                },
            ),
            ChunkResult(
                chunk_index=1,
                start_page=21,
                end_page=40,
                success=True,
                data={
                    "metadata": {
                        "financial_references": {
                            "amounts": [{"value": "500000", "currency": "USD", "context": "funding"}],
                            "financial_actors": ["NED"],
                            "purposes": ["OTHER"],
                        }
                    },
                    "original_text": "text",
                    "reviewed_text": "text",
                    "confidence": {"overall": 0.8, "concerns": []},
                },
            ),
        ]

        result = merge_chunk_results(chunks, "test.pdf", 40)

        fin_refs = result["metadata"]["financial_references"]
        assert len(fin_refs["amounts"]) == 2
        assert "CIA" in fin_refs["financial_actors"]
        assert "NED" in fin_refs["financial_actors"]

    def test_merge_violence_references(self):
        """Violence references are merged correctly."""
        chunks = [
            ChunkResult(
                chunk_index=0,
                start_page=1,
                end_page=20,
                success=True,
                data={
                    "metadata": {
                        "violence_references": {
                            "incident_types": ["ASSASSINATION"],
                            "victims": ["LETELIER, ORLANDO"],
                            "perpetrators": ["DINA"],
                            "has_violence_content": True,
                        }
                    },
                    "original_text": "text",
                    "reviewed_text": "text",
                    "confidence": {"overall": 0.9, "concerns": []},
                },
            ),
            ChunkResult(
                chunk_index=1,
                start_page=21,
                end_page=40,
                success=True,
                data={
                    "metadata": {
                        "violence_references": {
                            "incident_types": ["BOMBING"],
                            "victims": [],
                            "perpetrators": ["MILITARY"],
                            "has_violence_content": True,
                        }
                    },
                    "original_text": "text",
                    "reviewed_text": "text",
                    "confidence": {"overall": 0.8, "concerns": []},
                },
            ),
        ]

        result = merge_chunk_results(chunks, "test.pdf", 40)

        vio_refs = result["metadata"]["violence_references"]
        assert "ASSASSINATION" in vio_refs["incident_types"]
        assert "BOMBING" in vio_refs["incident_types"]
        assert vio_refs["has_violence_content"] is True


class TestChunkResult:
    """Tests for ChunkResult dataclass."""

    def test_successful_chunk(self):
        """Successful chunk has data."""
        chunk = ChunkResult(
            chunk_index=0,
            start_page=1,
            end_page=20,
            success=True,
            data={"test": "data"},
        )
        assert chunk.success is True
        assert chunk.data is not None
        assert chunk.error is None

    def test_failed_chunk(self):
        """Failed chunk has error."""
        chunk = ChunkResult(
            chunk_index=0,
            start_page=1,
            end_page=20,
            success=False,
            error="API error",
        )
        assert chunk.success is False
        assert chunk.data is None
        assert chunk.error == "API error"


class TestConstants:
    """Tests for module constants."""

    def test_default_threshold(self):
        """Default threshold is reasonable."""
        assert DEFAULT_CHUNK_THRESHOLD == 30

    def test_default_chunk_size(self):
        """Default chunk size is reasonable."""
        assert DEFAULT_CHUNK_SIZE == 20
        assert DEFAULT_CHUNK_SIZE < DEFAULT_CHUNK_THRESHOLD
