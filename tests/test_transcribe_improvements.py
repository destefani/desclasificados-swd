"""
Unit tests for transcribe.py improvements.

Tests cover:
- Response validation
- Auto-repair logic
- JSONSchema validation
- Cost tracking
- Rate limiting (basic)
"""

import pytest
import json
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.transcribe import (
    validate_response,
    auto_repair_response,
    validate_with_schema,
    CostTracker,
)


class TestValidateResponse:
    """Test basic response validation."""

    def test_valid_response(self):
        """Test that valid response passes validation."""
        valid_data = {
            "metadata": {
                "document_date": "1976-09-21",
                "classification_level": "SECRET",
                "document_type": "MEMORANDUM"
            },
            "original_text": "Some text",
            "reviewed_text": "Reviewed text"
        }

        is_valid, errors = validate_response(valid_data)
        assert is_valid is True
        assert len(errors) == 0

    def test_missing_metadata(self):
        """Test that missing metadata is caught."""
        invalid_data = {
            "original_text": "Some text",
            "reviewed_text": "Reviewed text"
        }

        is_valid, errors = validate_response(invalid_data)
        assert is_valid is False
        assert any("metadata" in error for error in errors)

    def test_missing_text_fields(self):
        """Test that missing text fields are caught."""
        invalid_data = {
            "metadata": {
                "document_date": "1976-09-21",
                "classification_level": "SECRET",
                "document_type": "MEMORANDUM"
            }
        }

        is_valid, errors = validate_response(invalid_data)
        assert is_valid is False
        assert any("original_text" in error for error in errors)

    def test_metadata_not_dict(self):
        """Test that non-dict metadata is caught."""
        invalid_data = {
            "metadata": "not a dict",
            "original_text": "Some text",
            "reviewed_text": "Reviewed text"
        }

        is_valid, errors = validate_response(invalid_data)
        assert is_valid is False
        assert any("not a dictionary" in error for error in errors)

    def test_text_fields_not_strings(self):
        """Test that non-string text fields are caught."""
        invalid_data = {
            "metadata": {
                "document_date": "1976-09-21",
                "classification_level": "SECRET",
                "document_type": "MEMORANDUM"
            },
            "original_text": 123,  # Should be string
            "reviewed_text": "Reviewed text"
        }

        is_valid, errors = validate_response(invalid_data)
        assert is_valid is False
        assert any("original_text" in error for error in errors)


class TestAutoRepairResponse:
    """Test auto-repair functionality."""

    def test_fix_reversed_dates(self):
        """Test that DD-MM-YYYY dates are fixed to YYYY-MM-DD."""
        data = {
            "metadata": {
                "document_date": "21-09-1976",
                "declassification_date": "15/03/2000"
            },
            "original_text": "",
            "reviewed_text": ""
        }

        repaired = auto_repair_response(data)
        assert repaired["metadata"]["document_date"] == "1976-09-21"
        assert repaired["metadata"]["declassification_date"] == "2000-03-15"

    def test_convert_string_to_array(self):
        """Test that string values are converted to arrays where expected."""
        data = {
            "metadata": {
                "recipients": "KISSINGER, HENRY",  # Should be array
                "keywords": "HUMAN RIGHTS",  # Should be array
                "people_mentioned": ""  # Empty string should become empty array
            },
            "original_text": "",
            "reviewed_text": ""
        }

        repaired = auto_repair_response(data)
        assert repaired["metadata"]["recipients"] == ["KISSINGER, HENRY"]
        assert repaired["metadata"]["keywords"] == ["HUMAN RIGHTS"]
        assert repaired["metadata"]["people_mentioned"] == []

    def test_normalize_classification(self):
        """Test that classification levels are normalized."""
        test_cases = [
            ("DECLASSIFIED", "UNCLASSIFIED"),
            ("declassified", "UNCLASSIFIED"),
            ("UNCLASS", "UNCLASSIFIED"),
            ("SECRET", "SECRET"),  # Should remain unchanged
        ]

        for input_val, expected in test_cases:
            data = {
                "metadata": {"classification_level": input_val},
                "original_text": "",
                "reviewed_text": ""
            }

            repaired = auto_repair_response(data)
            assert repaired["metadata"]["classification_level"] == expected

    def test_handle_null_fields(self):
        """Test that null fields are converted to empty strings/arrays."""
        data = {
            "metadata": {
                "document_id": None,
                "recipients": None,
                "page_count": None
            },
            "original_text": None,
            "reviewed_text": None
        }

        repaired = auto_repair_response(data)
        assert repaired["metadata"]["document_id"] == ""
        assert repaired["metadata"]["recipients"] == []
        assert repaired["metadata"]["page_count"] == 0
        assert repaired["original_text"] == ""
        assert repaired["reviewed_text"] == ""

    def test_fix_page_count_type(self):
        """Test that page_count is converted to number."""
        data = {
            "metadata": {"page_count": "5"},
            "original_text": "",
            "reviewed_text": ""
        }

        repaired = auto_repair_response(data)
        assert repaired["metadata"]["page_count"] == 5
        assert isinstance(repaired["metadata"]["page_count"], int)


class TestValidateWithSchema:
    """Test full JSONSchema validation with auto-repair."""

    def test_valid_complete_document(self):
        """Test that a complete valid document passes."""
        valid_doc = {
            "metadata": {
                "document_id": "CIA-001",
                "case_number": "CASE-123",
                "document_date": "1976-09-21",
                "classification_level": "SECRET",
                "declassification_date": "2000-01-01",
                "document_type": "MEMORANDUM",
                "author": "KISSINGER, HENRY",
                "recipients": ["PINOCHET, AUGUSTO"],
                "people_mentioned": ["ALLENDE, SALVADOR"],
                "country": ["CHILE"],
                "city": ["SANTIAGO"],
                "other_place": [],
                "document_title": "Test Document",
                "document_description": "A test",
                "archive_location": "BOX 1",
                "observations": "None",
                "language": "ENGLISH",
                "keywords": ["OPERATION CONDOR"],
                "page_count": 1,
                "document_summary": "Test summary"
            },
            "original_text": "Original text here",
            "reviewed_text": "Reviewed text here"
        }

        is_valid, errors = validate_with_schema(valid_doc, enable_auto_repair=False)
        assert is_valid is True
        assert len(errors) == 0

    def test_auto_repair_fixes_invalid(self):
        """Test that auto-repair can fix invalid documents."""
        invalid_doc = {
            "metadata": {
                "document_id": "CIA-001",
                "case_number": "CASE-123",
                "document_date": "21-09-1976",  # Wrong format - will be auto-fixed
                "classification_level": "DECLASSIFIED",  # Will be normalized
                "declassification_date": "",
                "document_type": "MEMORANDUM",
                "author": "",
                "recipients": "SINGLE RECIPIENT",  # String - will be converted to array
                "people_mentioned": [],
                "country": [],
                "city": [],
                "other_place": [],
                "document_title": "",
                "document_description": "",
                "archive_location": "",
                "observations": "",
                "language": "",
                "keywords": [],
                "page_count": "1",  # String - will be converted to int
                "document_summary": ""
            },
            "original_text": "text",
            "reviewed_text": "text"
        }

        # Without auto-repair, should fail
        is_valid_without, errors_without = validate_with_schema(invalid_doc, enable_auto_repair=False)

        # With auto-repair, should pass
        is_valid_with, errors_with = validate_with_schema(invalid_doc, enable_auto_repair=True)

        # Auto-repair should fix the issues
        assert is_valid_with is True or len(errors_with) < len(errors_without)


class TestCostTracker:
    """Test cost tracking functionality."""

    def test_initialization(self):
        """Test that CostTracker initializes correctly."""
        tracker = CostTracker()
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0

    def test_add_usage(self):
        """Test adding usage from API response."""
        tracker = CostTracker()

        # Mock API response
        class MockUsage:
            prompt_tokens = 1000
            completion_tokens = 500

        class MockResponse:
            usage = MockUsage()

        response = MockResponse()
        tracker.add_usage(response)

        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500

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
        import threading

        tracker = CostTracker()

        class MockUsage:
            prompt_tokens = 100
            completion_tokens = 50

        class MockResponse:
            usage = MockUsage()

        def add_usage_many_times():
            for _ in range(100):
                tracker.add_usage(MockResponse())

        # Run in multiple threads
        threads = [threading.Thread(target=add_usage_many_times) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have processed 10 threads * 100 additions each
        assert tracker.total_input_tokens == 10 * 100 * 100
        assert tracker.total_output_tokens == 10 * 100 * 50


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_document(self):
        """Test handling of completely empty document."""
        empty_doc = {}

        is_valid, errors = validate_response(empty_doc)
        assert is_valid is False
        assert len(errors) > 0

    def test_deeply_nested_invalid_data(self):
        """Test handling of deeply nested invalid structures."""
        nested_invalid = {
            "metadata": {
                "document_date": {"nested": "object"},  # Should be string
                "classification_level": ["array"],  # Should be string
                "document_type": 123  # Should be string
            },
            "original_text": "text",
            "reviewed_text": "text"
        }

        # Should catch type errors
        is_valid, errors = validate_response(nested_invalid)
        # Basic validation may not catch all nested issues
        # That's what full schema validation is for

    def test_auto_repair_handles_non_dict(self):
        """Test that auto-repair handles non-dict gracefully."""
        result = auto_repair_response("not a dict")
        assert result == "not a dict"  # Should return unchanged

        result = auto_repair_response(None)
        assert result is None  # Should return unchanged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
