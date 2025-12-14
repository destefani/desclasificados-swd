"""
Unit tests for transcription utilities.

Tests cover:
- Response validation (JSON schema)
- Auto-repair logic
- Cost tracking
"""

import pytest
import threading
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.response_repair import (
    validate_response,
    auto_repair_response,
)
from app.utils.cost_tracker import CostTracker


class TestValidateResponse:
    """Test JSON schema validation."""

    def test_valid_complete_document(self):
        """Test that a complete valid document passes schema validation."""
        valid_doc = {
            "metadata": {
                "document_id": "CIA-001",
                "case_number": "CASE123",
                "document_date": "1976-09-21",
                "date_range": {
                    "start_date": "",
                    "end_date": "",
                    "is_approximate": False
                },
                "classification_level": "SECRET",
                "declassification_date": "2000-01-01",
                "document_type": "MEMORANDUM",
                "author": "KISSINGER, HENRY",
                "recipients": ["PINOCHET, AUGUSTO"],
                "people_mentioned": ["ALLENDE, SALVADOR"],
                "organizations_mentioned": [
                    {"name": "CIA", "type": "INTELLIGENCE_AGENCY", "country": "UNITED STATES"}
                ],
                "country": ["CHILE"],
                "city": ["SANTIAGO"],
                "other_place": [],
                "document_title": "Test Document",
                "document_description": "A test document about Chile",
                "archive_location": "BOX 1",
                "observations": "None",
                "language": "ENGLISH",
                "keywords": ["OPERATION CONDOR"],
                "page_count": 1,
                "document_summary": "This is a test document about historical events in Chile during the 1970s.",
                "financial_references": {
                    "amounts": [],
                    "financial_actors": [],
                    "purposes": [],
                    "has_financial_content": False
                },
                "violence_references": {
                    "incident_types": [],
                    "victims": [],
                    "perpetrators": [],
                    "has_violence_content": False
                },
                "torture_references": {
                    "detention_centers": [],
                    "victims": [],
                    "perpetrators": [],
                    "methods_mentioned": [],
                    "has_torture_content": False
                },
                "disappearance_references": {
                    "victims": [],
                    "perpetrators": [],
                    "locations": [],
                    "dates_mentioned": [],
                    "has_disappearance_content": False
                }
            },
            "original_text": "Original text here",
            "reviewed_text": "Reviewed text here",
            "confidence": {
                "overall": 0.9,
                "concerns": [],
            },
        }

        is_valid, errors = validate_response(valid_doc)
        assert is_valid is True, f"Validation failed with errors: {errors}"
        assert len(errors) == 0


class TestAutoRepairResponse:
    """Test auto-repair functionality."""

    def test_returns_non_dict_unchanged(self):
        """Test that non-dict input is returned unchanged."""
        result = auto_repair_response("not a dict")  # type: ignore
        assert result == "not a dict"

    def test_adds_missing_sensitive_content_fields(self):
        """Test that missing sensitive content fields are added."""
        data = {
            "metadata": {
                "document_date": "1976-09-21",
            },
            "original_text": "text",
            "reviewed_text": "text",
        }

        repaired = auto_repair_response(data)

        # Should add financial_references
        assert "financial_references" in repaired["metadata"]
        assert repaired["metadata"]["financial_references"]["amounts"] == []

        # Should add violence_references
        assert "violence_references" in repaired["metadata"]
        assert repaired["metadata"]["violence_references"]["has_violence_content"] is False

        # Should add torture_references
        assert "torture_references" in repaired["metadata"]
        assert repaired["metadata"]["torture_references"]["has_torture_content"] is False

    def test_adds_missing_confidence(self):
        """Test that missing confidence field is added."""
        data = {
            "metadata": {},
            "original_text": "text",
            "reviewed_text": "text",
        }

        repaired = auto_repair_response(data)

        assert "confidence" in repaired
        assert repaired["confidence"]["overall"] == 0.5
        assert len(repaired["confidence"]["concerns"]) > 0

    def test_adds_missing_text_fields(self):
        """Test that missing text fields are added."""
        data = {"metadata": {}}

        repaired = auto_repair_response(data)

        assert repaired["original_text"] == ""
        assert repaired["reviewed_text"] == ""

    def test_handles_flat_structure(self):
        """Test that flat structure is nested under metadata."""
        data = {
            "document_date": "1976-09-21",
            "classification_level": "SECRET",
            "original_text": "text",
            "reviewed_text": "text",
        }

        repaired = auto_repair_response(data)

        # Fields should be moved under metadata
        assert "metadata" in repaired
        assert repaired["metadata"]["document_date"] == "1976-09-21"
        assert repaired["metadata"]["classification_level"] == "SECRET"

    def test_preserves_existing_values(self):
        """Test that existing valid values are preserved."""
        data = {
            "metadata": {
                "document_date": "1976-09-21",
                "financial_references": {
                    "amounts": ["$1,000,000"],
                    "financial_actors": ["CIA"],
                    "purposes": ["covert operations"],
                },
            },
            "original_text": "existing text",
            "reviewed_text": "existing reviewed",
            "confidence": {
                "overall": 0.95,
                "concerns": [],
            },
        }

        repaired = auto_repair_response(data)

        # Existing values should be preserved
        assert repaired["metadata"]["document_date"] == "1976-09-21"
        assert repaired["metadata"]["financial_references"]["amounts"] == ["$1,000,000"]
        assert repaired["original_text"] == "existing text"
        assert repaired["confidence"]["overall"] == 0.95


class TestCostTracker:
    """Test cost tracking functionality."""

    def test_initialization(self):
        """Test that CostTracker initializes correctly."""
        tracker = CostTracker()
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0

    def test_add_usage(self):
        """Test adding usage with input/output tokens."""
        tracker = CostTracker()

        tracker.add_usage(input_tokens=1000, output_tokens=500)

        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500

    def test_add_usage_cumulative(self):
        """Test that add_usage accumulates."""
        tracker = CostTracker()

        tracker.add_usage(input_tokens=1000, output_tokens=500)
        tracker.add_usage(input_tokens=500, output_tokens=250)

        assert tracker.total_input_tokens == 1500
        assert tracker.total_output_tokens == 750

    def test_cost_calculation_gpt4o_mini(self):
        """Test cost calculation for gpt-4o-mini."""
        tracker = CostTracker()
        tracker.total_input_tokens = 1_000_000
        tracker.total_output_tokens = 1_000_000

        cost = tracker.get_cost("gpt-4o-mini")

        # gpt-4o-mini: $0.150/1M input, $0.600/1M output
        expected_cost = (1_000_000 * 0.150 / 1_000_000) + (1_000_000 * 0.600 / 1_000_000)
        assert abs(cost - expected_cost) < 0.0001  # Allow for floating point errors

    def test_cost_calculation_gpt4o(self):
        """Test cost calculation for gpt-4o."""
        tracker = CostTracker()
        tracker.total_input_tokens = 100_000
        tracker.total_output_tokens = 50_000

        cost = tracker.get_cost("gpt-4o")

        # gpt-4o: $2.50/1M input, $10.00/1M output
        expected_cost = (100_000 * 2.50 / 1_000_000) + (50_000 * 10.00 / 1_000_000)
        assert abs(cost - expected_cost) < 0.0001

    def test_thread_safety(self):
        """Test that cost tracker is thread-safe."""
        tracker = CostTracker()

        def add_usage_many_times():
            for _ in range(100):
                tracker.add_usage(input_tokens=100, output_tokens=50)

        # Run in multiple threads
        threads = [threading.Thread(target=add_usage_many_times) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have processed 10 threads * 100 additions each
        assert tracker.total_input_tokens == 10 * 100 * 100
        assert tracker.total_output_tokens == 10 * 100 * 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
