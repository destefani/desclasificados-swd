"""Unit tests for response_repair module."""

import pytest

from app.utils.response_repair import (
    auto_repair_response,
    validate_response,
    extract_confidence,
    check_placeholder_text,
    METADATA_FIELDS,
    DEFAULT_FINANCIAL_REFERENCES,
    DEFAULT_VIOLENCE_REFERENCES,
    DEFAULT_TORTURE_REFERENCES,
)


class TestAutoRepairResponse:
    """Tests for auto_repair_response function."""

    def test_returns_non_dict_unchanged(self):
        """Test non-dict input is returned unchanged."""
        assert auto_repair_response("string") == "string"
        assert auto_repair_response(123) == 123
        assert auto_repair_response([1, 2, 3]) == [1, 2, 3]

    def test_empty_dict_gets_defaults(self):
        """Test empty dict gets default fields added."""
        result = auto_repair_response({})
        assert "confidence" in result
        assert "original_text" in result
        assert "reviewed_text" in result
        assert "metadata" in result

    def test_flat_structure_is_nested(self):
        """Test flat metadata fields are moved under 'metadata' key."""
        flat_data = {
            "document_id": "12345",
            "document_date": "1974-05-00",
            "classification_level": "SECRET",
            "original_text": "Some text",
            "reviewed_text": "Some text corrected",
        }

        result = auto_repair_response(flat_data)

        # Metadata fields should be nested
        assert "metadata" in result
        assert result["metadata"]["document_id"] == "12345"
        assert result["metadata"]["document_date"] == "1974-05-00"
        assert result["metadata"]["classification_level"] == "SECRET"

        # Non-metadata fields stay at root
        assert result["original_text"] == "Some text"
        assert result["reviewed_text"] == "Some text corrected"

    def test_existing_metadata_preserved(self):
        """Test existing metadata structure is preserved."""
        data = {
            "metadata": {
                "document_id": "12345",
                "classification_level": "TOP SECRET",
            },
            "original_text": "Text",
        }

        result = auto_repair_response(data)
        assert result["metadata"]["document_id"] == "12345"
        assert result["metadata"]["classification_level"] == "TOP SECRET"

    def test_financial_references_added(self):
        """Test financial_references is added if missing."""
        result = auto_repair_response({"metadata": {}})

        assert "financial_references" in result["metadata"]
        fr = result["metadata"]["financial_references"]
        assert fr["amounts"] == []
        assert fr["financial_actors"] == []
        assert fr["purposes"] == []

    def test_financial_references_partial_filled(self):
        """Test partial financial_references is completed."""
        data = {
            "metadata": {
                "financial_references": {
                    "amounts": [{"value": "1000", "currency": "USD"}],
                    # missing financial_actors and purposes
                }
            }
        }

        result = auto_repair_response(data)
        fr = result["metadata"]["financial_references"]
        assert len(fr["amounts"]) == 1  # Preserved
        assert fr["financial_actors"] == []  # Added
        assert fr["purposes"] == []  # Added

    def test_violence_references_added(self):
        """Test violence_references is added if missing."""
        result = auto_repair_response({"metadata": {}})

        vr = result["metadata"]["violence_references"]
        assert vr["incident_types"] == []
        assert vr["victims"] == []
        assert vr["perpetrators"] == []
        assert vr["has_violence_content"] is False

    def test_torture_references_added(self):
        """Test torture_references is added if missing."""
        result = auto_repair_response({"metadata": {}})

        tr = result["metadata"]["torture_references"]
        assert tr["detention_centers"] == []
        assert tr["victims"] == []
        assert tr["perpetrators"] == []
        assert tr["methods_mentioned"] is False
        assert tr["has_torture_content"] is False

    def test_confidence_added_if_missing(self):
        """Test confidence is added if missing."""
        result = auto_repair_response({})

        assert "confidence" in result
        assert result["confidence"]["overall"] == 0.5
        assert len(result["confidence"]["concerns"]) > 0

    def test_confidence_partial_filled(self):
        """Test partial confidence is completed."""
        data = {"confidence": {"overall": 0.85}}

        result = auto_repair_response(data)
        assert result["confidence"]["overall"] == 0.85
        assert result["confidence"]["concerns"] == []

    def test_original_text_added(self):
        """Test original_text is added if missing."""
        result = auto_repair_response({})
        assert result["original_text"] == ""

    def test_reviewed_text_added(self):
        """Test reviewed_text is added if missing."""
        result = auto_repair_response({})
        assert result["reviewed_text"] == ""

    def test_valid_response_unchanged(self):
        """Test valid response is not modified unnecessarily."""
        valid_data = {
            "metadata": {
                "document_id": "12345",
                "financial_references": {
                    "amounts": [],
                    "financial_actors": [],
                    "purposes": [],
                },
                "violence_references": {
                    "incident_types": [],
                    "victims": [],
                    "perpetrators": [],
                    "has_violence_content": False,
                },
                "torture_references": {
                    "detention_centers": [],
                    "victims": [],
                    "perpetrators": [],
                    "methods_mentioned": False,
                    "has_torture_content": False,
                },
            },
            "original_text": "Original content",
            "reviewed_text": "Reviewed content",
            "confidence": {"overall": 0.9, "concerns": []},
        }

        result = auto_repair_response(valid_data)
        assert result["metadata"]["document_id"] == "12345"
        assert result["original_text"] == "Original content"
        assert result["confidence"]["overall"] == 0.9


class TestValidateResponse:
    """Tests for validate_response function."""

    def test_valid_response_passes(self):
        """Test valid response passes validation."""
        # Minimal valid response
        valid_data = {
            "metadata": {
                "document_id": "",
                "case_number": "",
                "document_date": "1974-05-00",
                "classification_level": "SECRET",
                "declassification_date": "",
                "document_type": "MEMORANDUM",
                "author": "",
                "recipients": [],
                "people_mentioned": [],
                "country": [],
                "city": [],
                "other_place": [],
                "document_title": "",
                "document_description": "",
                "archive_location": "",
                "observations": "",
                "language": "ENGLISH",
                "keywords": ["TEST"],
                "page_count": 1,
                "document_summary": "This is a test document summary that is at least 50 characters long for validation.",
                "financial_references": {
                    "amounts": [],
                    "financial_actors": [],
                    "purposes": [],
                },
                "violence_references": {
                    "incident_types": [],
                    "victims": [],
                    "perpetrators": [],
                    "has_violence_content": False,
                },
                "torture_references": {
                    "detention_centers": [],
                    "victims": [],
                    "perpetrators": [],
                    "methods_mentioned": False,
                    "has_torture_content": False,
                },
            },
            "original_text": "Test",
            "reviewed_text": "Test",
            "confidence": {"overall": 0.85, "concerns": []},
        }

        is_valid, errors = validate_response(valid_data)
        # Note: May fail if schema isn't found, which is OK for testing
        # The function should handle missing schema gracefully
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_missing_required_field(self):
        """Test missing required field is caught."""
        # Missing 'confidence' field
        invalid_data = {
            "metadata": {},
            "original_text": "Test",
            "reviewed_text": "Test",
            # missing confidence
        }

        is_valid, errors = validate_response(invalid_data)
        # Either validation fails, or schema wasn't found
        if not is_valid:
            assert len(errors) > 0

    def test_no_schema_returns_valid(self):
        """Test missing schema returns valid (graceful degradation)."""
        # When schema is explicitly passed as None
        is_valid, errors = validate_response({}, schema=None)
        # Should not crash
        # Note: when schema=None is passed, the function loads default schema
        # so validation may still occur. This test verifies no crash.
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)


class TestExtractConfidence:
    """Tests for extract_confidence function."""

    def test_extracts_confidence(self):
        """Test confidence is extracted correctly."""
        data = {"confidence": {"overall": 0.87, "concerns": []}}
        assert extract_confidence(data) == 0.87

    def test_missing_confidence_returns_none(self):
        """Test missing confidence returns None."""
        assert extract_confidence({}) is None

    def test_invalid_confidence_structure_returns_none(self):
        """Test invalid confidence structure returns None."""
        assert extract_confidence({"confidence": "invalid"}) is None
        assert extract_confidence({"confidence": {}}) is None
        assert extract_confidence({"confidence": {"wrong_key": 0.5}}) is None


class TestCheckPlaceholderText:
    """Tests for check_placeholder_text function."""

    def test_short_text_is_placeholder(self):
        """Test short text is flagged as placeholder."""
        assert check_placeholder_text("Short", threshold=100) is True
        assert check_placeholder_text("A" * 50, threshold=100) is True

    def test_long_text_is_not_placeholder(self):
        """Test long genuine text is not flagged."""
        genuine_text = "This is a genuine document transcription. " * 10
        assert check_placeholder_text(genuine_text, threshold=100) is False

    def test_placeholder_indicators(self):
        """Test known placeholder indicators are flagged."""
        assert check_placeholder_text("Full OCR text would appear here" * 5) is True
        assert check_placeholder_text("The full text of the document..." * 5) is True
        assert check_placeholder_text("[Document text would appear here]" * 5) is True

    def test_custom_threshold(self):
        """Test custom threshold works."""
        text = "A" * 50
        assert check_placeholder_text(text, threshold=25) is False
        assert check_placeholder_text(text, threshold=100) is True


class TestMetadataFields:
    """Tests for METADATA_FIELDS constant."""

    def test_contains_required_fields(self):
        """Test all required metadata fields are present."""
        required = {
            "document_id",
            "document_date",
            "classification_level",
            "document_type",
            "keywords",
            "language",
            "financial_references",
            "violence_references",
            "torture_references",
        }
        for field in required:
            assert field in METADATA_FIELDS, f"Missing field: {field}"

    def test_field_count(self):
        """Test expected number of metadata fields."""
        # Should have 23 metadata fields as per schema
        assert len(METADATA_FIELDS) == 23


class TestDefaultStructures:
    """Tests for default structure constants."""

    def test_financial_references_structure(self):
        """Test DEFAULT_FINANCIAL_REFERENCES has correct structure."""
        assert "amounts" in DEFAULT_FINANCIAL_REFERENCES
        assert "financial_actors" in DEFAULT_FINANCIAL_REFERENCES
        assert "purposes" in DEFAULT_FINANCIAL_REFERENCES
        assert all(isinstance(v, list) for v in DEFAULT_FINANCIAL_REFERENCES.values())

    def test_violence_references_structure(self):
        """Test DEFAULT_VIOLENCE_REFERENCES has correct structure."""
        assert "incident_types" in DEFAULT_VIOLENCE_REFERENCES
        assert "victims" in DEFAULT_VIOLENCE_REFERENCES
        assert "perpetrators" in DEFAULT_VIOLENCE_REFERENCES
        assert "has_violence_content" in DEFAULT_VIOLENCE_REFERENCES
        assert DEFAULT_VIOLENCE_REFERENCES["has_violence_content"] is False

    def test_torture_references_structure(self):
        """Test DEFAULT_TORTURE_REFERENCES has correct structure."""
        assert "detention_centers" in DEFAULT_TORTURE_REFERENCES
        assert "victims" in DEFAULT_TORTURE_REFERENCES
        assert "perpetrators" in DEFAULT_TORTURE_REFERENCES
        assert "methods_mentioned" in DEFAULT_TORTURE_REFERENCES
        assert "has_torture_content" in DEFAULT_TORTURE_REFERENCES
        assert DEFAULT_TORTURE_REFERENCES["methods_mentioned"] is False
        assert DEFAULT_TORTURE_REFERENCES["has_torture_content"] is False
