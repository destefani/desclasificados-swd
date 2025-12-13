"""
Response repair and validation utilities.

Provides auto-repair for common schema issues and validation against
the metadata JSON schema.
"""

import json
import logging
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


logger = logging.getLogger(__name__)

# Metadata fields that should be nested under "metadata" key
METADATA_FIELDS = {
    "document_id",
    "case_number",
    "document_date",
    "classification_level",
    "declassification_date",
    "document_type",
    "author",
    "recipients",
    "people_mentioned",
    "country",
    "city",
    "other_place",
    "document_title",
    "document_description",
    "archive_location",
    "observations",
    "language",
    "keywords",
    "page_count",
    "document_summary",
    "financial_references",
    "violence_references",
    "torture_references",
}

# Default empty structures for sensitive content fields
DEFAULT_FINANCIAL_REFERENCES: dict[str, Any] = {
    "amounts": [],
    "financial_actors": [],
    "purposes": [],
}

DEFAULT_VIOLENCE_REFERENCES: dict[str, Any] = {
    "incident_types": [],
    "victims": [],
    "perpetrators": [],
    "has_violence_content": False,
}

DEFAULT_TORTURE_REFERENCES: dict[str, Any] = {
    "detention_centers": [],
    "victims": [],
    "perpetrators": [],
    "methods_mentioned": [],
    "has_torture_content": False,
}

DEFAULT_CONFIDENCE: dict[str, Any] = {
    "overall": 0.5,
    "concerns": ["Auto-generated confidence due to missing field"],
}


def auto_repair_response(data: dict) -> dict:
    """
    Automatically fix common output issues in API responses.

    Handles:
    - Flat structure (metadata fields at root level)
    - Missing required nested structures
    - Missing confidence field
    - Missing text fields

    Args:
        data: Raw response data from API

    Returns:
        Repaired data conforming to expected schema structure
    """
    if not isinstance(data, dict):
        return data

    # Handle flat structure (fields at root instead of under "metadata")
    if "metadata" not in data and any(k in data for k in METADATA_FIELDS):
        metadata = {}
        root_fields = {}
        for key, value in data.items():
            if key in METADATA_FIELDS:
                metadata[key] = value
            else:
                root_fields[key] = value
        data = root_fields
        data["metadata"] = metadata

    metadata = data.get("metadata", {})

    # Ensure financial_references exists and has correct structure
    if "financial_references" not in metadata or not isinstance(
        metadata.get("financial_references"), dict
    ):
        metadata["financial_references"] = DEFAULT_FINANCIAL_REFERENCES.copy()
    else:
        # Ensure all sub-fields exist
        for key, default in DEFAULT_FINANCIAL_REFERENCES.items():
            if key not in metadata["financial_references"]:
                metadata["financial_references"][key] = default

    # Ensure violence_references exists and has correct structure
    if "violence_references" not in metadata or not isinstance(
        metadata.get("violence_references"), dict
    ):
        metadata["violence_references"] = DEFAULT_VIOLENCE_REFERENCES.copy()
    else:
        for key, default_val in DEFAULT_VIOLENCE_REFERENCES.items():
            if key not in metadata["violence_references"]:
                metadata["violence_references"][key] = default_val

    # Ensure torture_references exists and has correct structure
    if "torture_references" not in metadata or not isinstance(
        metadata.get("torture_references"), dict
    ):
        metadata["torture_references"] = DEFAULT_TORTURE_REFERENCES.copy()
    else:
        for key, default_val in DEFAULT_TORTURE_REFERENCES.items():
            if key not in metadata["torture_references"]:
                metadata["torture_references"][key] = default_val

    # Ensure confidence structure exists
    if "confidence" not in data or not isinstance(data.get("confidence"), dict):
        data["confidence"] = DEFAULT_CONFIDENCE.copy()
    else:
        if "overall" not in data["confidence"]:
            data["confidence"]["overall"] = 0.5
        if "concerns" not in data["confidence"]:
            data["confidence"]["concerns"] = []

    # Ensure text fields exist
    if "original_text" not in data:
        data["original_text"] = ""
    if "reviewed_text" not in data:
        data["reviewed_text"] = ""

    # Ensure metadata is in the data
    if "metadata" not in data:
        data["metadata"] = metadata

    return data


def validate_response(
    data: dict,
    schema: dict | None = None,
) -> tuple[bool, list[str]]:
    """
    Validate response data against JSON schema.

    Args:
        data: Response data to validate
        schema: JSON schema to validate against. If None, loads from default path.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    if schema is None:
        schema = _load_default_schema()

    if schema is None:
        # No schema available, skip validation
        return True, []

    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(data))

    if errors:
        error_msgs = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            error_msgs.append(f"{path}: {error.message}")
        return False, error_msgs

    return True, []


def _load_default_schema() -> dict | None:
    """Load the default metadata schema from the prompts directory."""
    schema_path = (
        Path(__file__).parent.parent / "prompts" / "schemas" / "metadata_schema.json"
    )

    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Failed to load schema from {schema_path}: {e}")
        return None


def extract_confidence(data: dict) -> float | None:
    """
    Extract confidence score from response data.

    Args:
        data: Response data containing confidence field

    Returns:
        Confidence score (0.0-1.0) or None if not found
    """
    if "confidence" not in data:
        return None

    confidence_data = data["confidence"]
    if isinstance(confidence_data, dict) and "overall" in confidence_data:
        return confidence_data["overall"]

    return None


def check_placeholder_text(original_text: str, threshold: int = 100) -> bool:
    """
    Check if the original_text appears to be placeholder content.

    Args:
        original_text: The transcribed text to check
        threshold: Minimum expected length for real content

    Returns:
        True if placeholder text is detected, False otherwise
    """
    if len(original_text) < threshold:
        return True

    placeholder_indicators = [
        "Full OCR text",
        "full text",
        "[Document text would appear here]",
        "[Transcription placeholder]",
        "Unable to transcribe",
    ]

    for indicator in placeholder_indicators:
        if indicator.lower() in original_text.lower():
            return True

    return False
