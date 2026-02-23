import pytest
from pathlib import Path
from tests.unit.test_document_service import sample_transcripts


class TestStatsService:
    def test_compute_stats(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.stats_service import StatsService
        doc_svc = DocumentService(sample_transcripts)
        stats = StatsService(doc_svc)
        result = stats.get_stats(total_pdfs=21512)
        assert result["total_documents"] == 3
        assert result["transcription_progress"]["completed"] == 3
        assert result["transcription_progress"]["total"] == 21512

    def test_classification_distribution(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.stats_service import StatsService
        doc_svc = DocumentService(sample_transcripts)
        stats = StatsService(doc_svc)
        result = stats.get_stats(total_pdfs=3)
        dist = result["classification_distribution"]
        assert dist["TOP SECRET"] == 1
        assert dist["SECRET"] == 1
        assert dist["CONFIDENTIAL"] == 1

    def test_timeline(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.stats_service import StatsService
        doc_svc = DocumentService(sample_transcripts)
        stats = StatsService(doc_svc)
        result = stats.get_stats(total_pdfs=3)
        assert "1973" in result["timeline"]
        assert result["timeline"]["1973"] == 1

    def test_avg_confidence(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.stats_service import StatsService
        doc_svc = DocumentService(sample_transcripts)
        stats = StatsService(doc_svc)
        result = stats.get_stats(total_pdfs=3)
        assert result["avg_confidence"] == 0.9
