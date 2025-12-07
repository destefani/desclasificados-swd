"""
Transcribe CIA documents using OpenAI vision models.

This module provides a unified CLI for transcribing PDF documents to structured JSON.
It automatically resumes from where it left off and supports graceful shutdown.

IMPORTANT: Always use PDFs from data/original_pdfs/, never JPEGs from data/images/.
JPEGs only contain the first page of multi-page documents (~70% have multiple pages).

Usage:
    uv run python -m app.transcribe              # Process all remaining PDFs
    uv run python -m app.transcribe -n 100       # Process 100 PDFs
    uv run python -m app.transcribe --status     # Show status only
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import random
import re
import signal
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Optional

import openai
from dotenv import load_dotenv
from jsonschema import Draft7Validator
from openai import OpenAI
from tqdm import tqdm

from app.config import DATA_DIR, ROOT_DIR
from app.utils.cost_tracker import PRICING, PricingTier

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Load environment variables
load_dotenv(ROOT_DIR / ".env")

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load the transcription prompt (v2 by default)
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v2")
USE_STRUCTURED_OUTPUTS = os.getenv("USE_STRUCTURED_OUTPUTS", "true").lower() == "true"

if PROMPT_VERSION == "v2":
    prompt_path = Path(__file__).parent / "prompts" / "metadata_prompt_v2.md"
else:
    prompt_path = Path(__file__).parent / "prompts" / "metadata_prompt.md"

try:
    PROMPT = prompt_path.read_text(encoding="utf-8")
    logging.info(f"Loaded prompt from: {prompt_path.name}")
except Exception as e:
    logging.error(f"Failed to read prompt file {prompt_path}: {e}")
    raise RuntimeError(f"Prompt file missing: {prompt_path}") from e

# Load JSON schema for Structured Outputs
SCHEMA: Optional[dict[str, Any]] = None
if USE_STRUCTURED_OUTPUTS:
    schema_path = Path(__file__).parent / "prompts" / "schemas" / "metadata_schema.json"
    try:
        SCHEMA = json.loads(schema_path.read_text(encoding="utf-8"))
        logging.info(f"Loaded JSON schema from: {schema_path.name}")
    except Exception as e:
        logging.warning(f"Failed to load schema: {e}. Falling back to basic JSON mode.")
        USE_STRUCTURED_OUTPUTS = False

# Rate limiting configuration
MAX_TPM = int(os.getenv("MAX_TOKENS_PER_MINUTE", "10000000"))  # 10M for gpt-4.1-mini
MAX_RPM = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "10000"))   # 10k RPM
EST_TOKENS_PER_DOC = 3000
EST_OUTPUT_TOKENS = 1500

# Global rate limiting state
token_usage: Deque[tuple[float, int]] = deque()
request_times: Deque[float] = deque()
rate_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class TranscriptionStatus:
    """Current transcription status."""

    model: str
    total: int
    done: int
    remaining: int
    remaining_files: list[str]

    @property
    def percent_done(self) -> float:
        return (self.done / self.total * 100) if self.total > 0 else 0.0


@dataclass
class ProcessingResult:
    """Result of processing a batch of files."""

    success: int
    failed: int
    skipped: int
    elapsed_seconds: float


@dataclass
class FailedDocument:
    """Record of a failed document for tracking and retry."""

    filename: str
    reason: str
    finish_reason: Optional[str]
    timestamp: str
    partial_content: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "reason": self.reason,
            "finish_reason": self.finish_reason,
            "timestamp": self.timestamp,
            "partial_content": self.partial_content,
        }


class FailedDocumentsTracker:
    """Thread-safe tracker for failed documents."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.failures: list[FailedDocument] = []
        self._lock = threading.Lock()
        self.log_file = output_dir / "failed_documents.json"

    def add_failure(
        self,
        filename: str,
        reason: str,
        finish_reason: Optional[str] = None,
        partial_content: Optional[str] = None,
    ) -> None:
        """Record a failed document."""
        from datetime import datetime

        failure = FailedDocument(
            filename=filename,
            reason=reason,
            finish_reason=finish_reason,
            timestamp=datetime.now().isoformat(),
            partial_content=partial_content[:1000] if partial_content else None,
        )

        with self._lock:
            self.failures.append(failure)
            self._save()

    def _save(self) -> None:
        """Save failures to disk (called within lock)."""
        existing: list[dict[str, Any]] = []

        # Load existing failures
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Append new failures
        for failure in self.failures:
            existing.append(failure.to_dict())

        # Write back
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        # Clear in-memory list after saving
        self.failures.clear()

    def get_count(self) -> int:
        """Get total count of failures from log file."""
        if not self.log_file.exists():
            return 0
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                return len(json.load(f))
        except (json.JSONDecodeError, IOError):
            return 0

    def get_summary(self) -> dict[str, int]:
        """Get count of failures by finish_reason."""
        if not self.log_file.exists():
            return {}
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                failures = json.load(f)
            summary: dict[str, int] = {}
            for f in failures:
                reason = f.get("finish_reason") or "unknown"
                summary[reason] = summary.get(reason, 0) + 1
            return summary
        except (json.JSONDecodeError, IOError):
            return {}


# ---------------------------------------------------------------------------
# Cost Tracking
# ---------------------------------------------------------------------------


class CostTracker:
    """Thread-safe cost tracker for API usage."""

    def __init__(self) -> None:
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._lock = threading.Lock()

    def add_usage(self, response: Any) -> None:
        """Track token usage from API response."""
        with self._lock:
            if hasattr(response, "usage"):
                usage = response.usage
                self.total_input_tokens += usage.prompt_tokens
                self.total_output_tokens += usage.completion_tokens

    def get_cost(self, model: str) -> float:
        """Calculate cost based on model pricing."""
        pricing = PRICING.get(model)
        if pricing is None:
            # Fallback pricing
            pricing = PricingTier(input_per_million=0.40, output_per_million=1.60)

        return (
            self.total_input_tokens * pricing.input_rate
            + self.total_output_tokens * pricing.output_rate
        )

    def print_summary(self, model: str) -> None:
        """Print cost summary."""
        with self._lock:
            print()
            print("-" * 50)
            print("Cost Summary")
            print("-" * 50)
            print(f"Model:          {model}")
            print(f"Input tokens:   {self.total_input_tokens:,}")
            print(f"Output tokens:  {self.total_output_tokens:,}")
            print(f"Estimated cost: ${self.get_cost(model):.4f}")
            print("-" * 50)


# Global cost tracker
cost_tracker = CostTracker()


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------


def wait_for_rate_limit(estimated_tokens: int) -> None:
    """Wait until both TPM and RPM budgets are available."""
    while True:
        with rate_lock:
            now = time.time()

            # Remove entries older than 60 seconds
            while token_usage and now - token_usage[0][0] > 60:
                token_usage.popleft()
            while request_times and now - request_times[0] > 60:
                request_times.popleft()

            # Calculate current usage
            tokens_used = sum(tokens for _, tokens in token_usage)
            requests_used = len(request_times)

            # Check if we can proceed (both TPM and RPM)
            if tokens_used + estimated_tokens < MAX_TPM and requests_used < MAX_RPM:
                token_usage.append((now, estimated_tokens))
                request_times.append(now)
                return

        time.sleep(0.1)  # Short sleep for faster throughput


def get_optimal_workers() -> int:
    """Determine optimal worker count based on rate limits."""
    # With 10k RPM and ~20s per request, we can sustain ~166 requests/min
    # Use workers to maximize throughput without overwhelming the API
    rpm_based = MAX_RPM // 60  # Requests we can start per second
    tpm_based = MAX_TPM // EST_TOKENS_PER_DOC // 60
    optimal = min(rpm_based, tpm_based, 100)  # Cap at 100 workers
    return max(optimal, 5)


# ---------------------------------------------------------------------------
# Schema Validation
# ---------------------------------------------------------------------------

FULL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["metadata", "original_text", "reviewed_text"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": [
                "document_id",
                "document_date",
                "classification_level",
                "document_type",
            ],
        },
        "original_text": {"type": "string"},
        "reviewed_text": {"type": "string"},
    },
}


def auto_repair_response(data: dict[str, Any]) -> dict[str, Any]:
    """Automatically fix common AI output issues."""
    if not isinstance(data, dict):
        return data

    metadata = data.get("metadata", {})

    # Fix reversed dates (DD-MM-YYYY -> YYYY-MM-DD)
    for date_field in ["document_date", "declassification_date"]:
        if date_field in metadata:
            date_str = str(metadata[date_field])
            if re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", date_str):
                parts = re.split(r"[-/]", date_str)
                metadata[date_field] = f"{parts[2]}-{parts[1]}-{parts[0]}"

    # Convert string arrays to actual arrays
    array_fields = [
        "recipients",
        "keywords",
        "people_mentioned",
        "country",
        "city",
        "other_place",
    ]
    for field in array_fields:
        value = metadata.get(field)
        if isinstance(value, str):
            metadata[field] = [value] if value else []
        elif value is None:
            metadata[field] = []

    # Ensure string fields are not null
    string_fields = [
        "document_id",
        "case_number",
        "document_date",
        "classification_level",
        "declassification_date",
        "document_type",
        "author",
        "document_title",
        "document_description",
        "archive_location",
        "observations",
        "language",
        "document_summary",
    ]
    for field in string_fields:
        if metadata.get(field) is None:
            metadata[field] = ""

    # Normalize classification levels
    if "classification_level" in metadata:
        classification = str(metadata["classification_level"]).upper()
        if "DECLASSIFIED" in classification or "UNCLASS" in classification:
            metadata["classification_level"] = "UNCLASSIFIED"

    # Ensure page_count is a number
    if "page_count" in metadata:
        try:
            metadata["page_count"] = (
                int(metadata["page_count"]) if metadata["page_count"] else 0
            )
        except (ValueError, TypeError):
            metadata["page_count"] = 0

    # Ensure top-level text fields are strings
    for field in ["original_text", "reviewed_text"]:
        if field not in data or data[field] is None:
            data[field] = ""

    return data


def validate_with_schema(
    data: dict[str, Any], enable_auto_repair: bool = True
) -> tuple[bool, list[str]]:
    """Validate response against schema."""
    if enable_auto_repair:
        data = auto_repair_response(data)

    validator = Draft7Validator(FULL_SCHEMA)
    errors = list(validator.iter_errors(data))

    if errors:
        error_msgs = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            error_msgs.append(f"{path}: {error.message}")
        return False, error_msgs

    return True, []


# ---------------------------------------------------------------------------
# API Interaction
# ---------------------------------------------------------------------------


def call_api_with_retry(
    messages: list[dict[str, Any]], model: str, max_retries: int = 3
) -> Any:
    """Call OpenAI API with exponential backoff retry."""
    for attempt in range(1, max_retries + 1):
        try:
            wait_for_rate_limit(EST_TOKENS_PER_DOC)

            if USE_STRUCTURED_OUTPUTS and SCHEMA:
                response_format: dict[str, Any] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "document_metadata_extraction",
                        "schema": SCHEMA,
                        "strict": True,
                    },
                }
            else:
                response_format = {"type": "json_object"}

            # GPT-5 and o-series models have different API requirements
            api_params: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "response_format": response_format,
            }
            if model.startswith(("gpt-5", "o1", "o3", "o4")):
                # GPT-5/o-series: use max_completion_tokens, no temperature param
                api_params["max_completion_tokens"] = 32000
            else:
                # Older models: use max_tokens and temperature=0
                api_params["max_tokens"] = 32000
                api_params["temperature"] = 0

            response = client.chat.completions.create(**api_params)  # type: ignore[call-overload]

            cost_tracker.add_usage(response)
            return response

        except openai.RateLimitError as e:
            if attempt == max_retries:
                raise
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logging.warning(f"Rate limit hit, retrying in {delay:.1f}s")
            time.sleep(delay)

        except (openai.APIError, openai.APIConnectionError) as e:
            if attempt == max_retries:
                raise
            delay = 2 ** (attempt - 1)
            logging.warning(f"API error, retrying in {delay}s: {e}")
            time.sleep(delay)

    raise RuntimeError("All retries exhausted")


# ---------------------------------------------------------------------------
# Document Transcription
# ---------------------------------------------------------------------------


def transcribe_single_document(
    filename: str,
    pdfs_dir: Path,
    output_dir: Path,
    model: str,
    dry_run: bool = False,
    failure_tracker: Optional[FailedDocumentsTracker] = None,
) -> str:
    """
    Transcribe a single PDF document (all pages).

    OpenAI vision API accepts PDFs directly via base64 encoding.
    The API processes all pages automatically.

    Args:
        filename: PDF filename to process
        pdfs_dir: Directory containing PDFs (data/original_pdfs/)
        output_dir: Directory for JSON outputs
        model: OpenAI model to use
        dry_run: If True, simulate without API calls
        failure_tracker: Optional tracker for recording failures

    Returns:
        "success", "skipped", or "failed"
    """
    file_path = pdfs_dir / filename
    output_filename = output_dir / (os.path.splitext(filename)[0] + ".json")

    def record_failure(reason: str, finish_reason: Optional[str] = None, partial: Optional[str] = None) -> str:
        """Helper to record failure and return 'failed'."""
        logging.error(f"✗ {filename} | {reason}")
        if failure_tracker:
            failure_tracker.add_failure(filename, reason, finish_reason, partial)
        return "failed"

    # Skip if already exists (always resume)
    if output_filename.exists():
        return "skipped"

    if dry_run:
        logging.info(f"[DRY RUN] Would process: {filename}")
        time.sleep(0.05)
        return "success"

    start_time = time.time()

    # Read and encode PDF directly (OpenAI accepts PDFs via base64)
    try:
        with open(file_path, "rb") as f:
            pdf_data = f.read()
        base64_pdf = base64.b64encode(pdf_data).decode("utf-8")
    except Exception as e:
        return record_failure(f"Failed to read PDF: {e}")

    # Build message content with PDF
    content: list[dict[str, Any]] = [
        {"type": "text", "text": PROMPT},
        {
            "type": "file",
            "file": {
                "filename": filename,
                "file_data": f"data:application/pdf;base64,{base64_pdf}",
            },
        },
    ]

    # Call API with PDF
    try:
        response = call_api_with_retry(
            messages=[{"role": "user", "content": content}],
            model=model,
        )
    except Exception as e:
        return record_failure(f"API call failed: {e}")

    # Parse response
    choice = response.choices[0]
    response_text = choice.message.content or ""
    finish_reason = choice.finish_reason

    # Check for truncation or content filter
    if finish_reason != "stop":
        reason_map = {
            "length": "Response truncated (max_tokens reached)",
            "content_filter": "Content filtered by OpenAI moderation",
        }
        reason = reason_map.get(finish_reason, f"Unexpected finish_reason: {finish_reason}")
        return record_failure(reason, finish_reason, response_text)

    cleaned_text = response_text.replace("```json", "").replace("```", "").strip()

    try:
        response_data = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        return record_failure(f"JSON parse error: {e}", finish_reason, response_text)

    # Validate
    enable_auto_repair = not USE_STRUCTURED_OUTPUTS
    is_valid, errors = validate_with_schema(response_data, enable_auto_repair)

    if not is_valid:
        return record_failure(f"Schema validation failed: {errors}", finish_reason)

    # Additional validation: check for empty/incomplete text fields
    original_text = response_data.get("original_text", "")
    reviewed_text = response_data.get("reviewed_text", "")

    # If original_text has content but reviewed_text is empty, this is incomplete
    if len(original_text) > 100 and len(reviewed_text) < 50:
        return record_failure(
            f"Incomplete output: original_text has {len(original_text)} chars but reviewed_text is empty/short ({len(reviewed_text)} chars)",
            finish_reason,
            response_text,
        )

    # If both text fields are suspiciously short for a multi-page document
    page_count = response_data.get("metadata", {}).get("page_count", 1)
    min_expected_chars = page_count * 200  # Expect at least 200 chars per page
    if page_count > 1 and len(reviewed_text) < min_expected_chars:
        return record_failure(
            f"Incomplete output: {page_count} pages but only {len(reviewed_text)} chars in reviewed_text (expected ~{min_expected_chars}+)",
            finish_reason,
            response_text,
        )

    # Write output
    try:
        with open(output_filename, "w", encoding="utf-8") as out_file:
            json.dump(response_data, out_file, ensure_ascii=False, indent=4)

        elapsed = time.time() - start_time
        size_kb = output_filename.stat().st_size / 1024
        # Get page count from metadata if available
        page_count = response_data.get("metadata", {}).get("page_count", "?")
        logging.info(f"✓ {filename} | {page_count} pages | {size_kb:.1f} KB | {elapsed:.2f}s")
        return "success"

    except Exception as e:
        return record_failure(f"Failed to write output: {e}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of validating transcription outputs."""

    total: int
    valid: int
    issues: list[dict[str, Any]]


def validate_outputs(model: str, min_text_length: int = 100) -> ValidationResult:
    """
    Validate all transcription outputs for completeness.

    Checks for:
    - Short original_text (< min_text_length chars)
    - Missing required fields
    - Placeholder text

    Args:
        model: Model name (determines output directory)
        min_text_length: Minimum expected text length

    Returns:
        ValidationResult with issues found
    """
    output_dir = DATA_DIR / "generated_transcripts" / model
    issues: list[dict[str, Any]] = []

    if not output_dir.exists():
        return ValidationResult(total=0, valid=0, issues=[])

    json_files = sorted(output_dir.glob("*.json"))
    total = len(json_files)

    placeholder_indicators = [
        "Full OCR text",
        "full text",
        "[Document text would appear here]",
        "[Transcription placeholder]",
        "Unable to transcribe",
    ]

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            file_issues: list[str] = []

            # Check original_text length
            original_text = data.get("original_text", "")
            if len(original_text) < min_text_length:
                file_issues.append(f"Short text: {len(original_text)} chars")

            # Check for placeholder text
            for indicator in placeholder_indicators:
                if indicator.lower() in original_text.lower():
                    file_issues.append(f"Placeholder text detected: '{indicator}'")
                    break

            # Check metadata exists
            metadata = data.get("metadata", {})
            if not metadata:
                file_issues.append("Missing metadata")

            # Check confidence
            confidence = data.get("confidence", {})
            overall = confidence.get("overall", 0) if isinstance(confidence, dict) else 0
            if overall < 0.5:
                file_issues.append(f"Low confidence: {overall}")

            if file_issues:
                issues.append({
                    "filename": json_file.name,
                    "issues": file_issues,
                    "text_length": len(original_text),
                    "confidence": overall,
                })

        except (json.JSONDecodeError, IOError) as e:
            issues.append({
                "filename": json_file.name,
                "issues": [f"Failed to read: {e}"],
                "text_length": 0,
                "confidence": 0,
            })

    return ValidationResult(
        total=total,
        valid=total - len(issues),
        issues=issues,
    )


def print_validation_report(result: ValidationResult) -> None:
    """Print validation results."""
    print()
    print("=" * 50)
    print("Validation Report")
    print("=" * 50)
    print(f"Total files:      {result.total}")
    print(f"Valid:            {result.valid}")
    print(f"Issues found:     {len(result.issues)}")

    if result.issues:
        print()
        print("Issues:")
        print("-" * 50)
        for item in result.issues[:20]:  # Show first 20
            print(f"  {item['filename']}:")
            for issue in item["issues"]:
                print(f"    - {issue}")

        if len(result.issues) > 20:
            print(f"  ... and {len(result.issues) - 20} more")

        # Save full report
        report_file = DATA_DIR / "validation_issues.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(result.issues, f, indent=2, ensure_ascii=False)
        print()
        print(f"Full report saved to: {report_file}")


# ---------------------------------------------------------------------------
# Status and Estimation
# ---------------------------------------------------------------------------


def get_status() -> TranscriptionStatus:
    """Get current transcription status using PDFs as source."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    pdfs_dir = DATA_DIR / "original_pdfs"
    output_dir = DATA_DIR / "generated_transcripts" / model

    # Get all PDFs (the authoritative source)
    all_pdfs = sorted(
        f for f in os.listdir(pdfs_dir) if f.lower().endswith(".pdf")
    )
    total = len(all_pdfs)

    # Get existing transcripts
    output_dir.mkdir(parents=True, exist_ok=True)
    done_ids = {
        os.path.splitext(f)[0] for f in os.listdir(output_dir) if f.endswith(".json")
    }
    done = len(done_ids)

    # Find remaining PDFs to process
    remaining_files = [
        f for f in all_pdfs if os.path.splitext(f)[0] not in done_ids
    ]

    return TranscriptionStatus(
        model=model,
        total=total,
        done=done,
        remaining=len(remaining_files),
        remaining_files=remaining_files,
    )


def estimate_cost(num_files: int, model: str) -> float:
    """Estimate cost for processing files."""
    pricing = PRICING.get(model)
    if pricing is None:
        pricing = PricingTier(input_per_million=0.40, output_per_million=1.60)

    input_tokens = num_files * EST_TOKENS_PER_DOC
    output_tokens = num_files * EST_OUTPUT_TOKENS

    return input_tokens * pricing.input_rate + output_tokens * pricing.output_rate


def format_time(seconds: float) -> str:
    """Format seconds as human-readable time."""
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        return f"{seconds / 60:.1f} minutes"
    else:
        return f"{seconds / 3600:.1f} hours"


def print_status(status: TranscriptionStatus) -> None:
    """Print transcription status."""
    print()
    print("Transcription Status")
    print("=" * 40)
    print(f"Model:           {status.model}")
    print(f"Total documents: {status.total:,}")
    print(f"Completed:       {status.done:,} ({status.percent_done:.1f}%)")
    print(f"Remaining:       {status.remaining:,}")
    print()


def print_estimate(num_files: int, model: str) -> float:
    """Print cost and time estimate. Returns estimated cost."""
    cost = estimate_cost(num_files, model)
    time_seconds = num_files / 2  # ~2 docs/second

    print("Estimate")
    print("-" * 40)
    print(f"Files to process: {num_files:,}")
    print(f"Estimated cost:   ${cost:.2f}")
    print(f"Estimated time:   {format_time(time_seconds)}")
    print()

    return cost


# ---------------------------------------------------------------------------
# Main Processing
# ---------------------------------------------------------------------------


def process_files(
    files: list[str],
    model: str,
    dry_run: bool = False,
    max_workers: Optional[int] = None,
    strict: bool = False,
) -> ProcessingResult:
    """Process PDF files with progress tracking and graceful shutdown.

    Args:
        files: List of PDF filenames to process
        model: OpenAI model to use
        dry_run: If True, simulate without API calls
        max_workers: Number of parallel workers (default: auto)
        strict: If True, stop on first failure
    """
    pdfs_dir = DATA_DIR / "original_pdfs"
    output_dir = DATA_DIR / "generated_transcripts" / model
    output_dir.mkdir(parents=True, exist_ok=True)

    workers = max_workers or get_optimal_workers()

    # Create failure tracker
    failure_tracker = FailedDocumentsTracker(output_dir)

    # Graceful shutdown handling
    shutdown_requested = False

    def handle_shutdown(signum: int, frame: Any) -> None:
        nonlocal shutdown_requested
        if not shutdown_requested:
            print("\n\nStopping gracefully... (waiting for current files)")
            shutdown_requested = True

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    results = {"success": 0, "skipped": 0, "failed": 0}
    start_time = time.time()

    print(f"Processing {len(files)} documents with {workers} workers...")
    print()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                transcribe_single_document, f, pdfs_dir, output_dir, model, dry_run, failure_tracker
            ): f
            for f in files
        }

        with tqdm(total=len(futures), desc="Progress", unit="doc") as pbar:
            for future in as_completed(futures):
                if shutdown_requested:
                    # Cancel pending futures
                    for f in futures:
                        f.cancel()
                    break

                try:
                    result = future.result()
                    results[result] += 1

                    # Strict mode: stop on first failure
                    if strict and result == "failed":
                        print("\n\nStrict mode: Stopping due to failure")
                        shutdown_requested = True
                        for f in futures:
                            f.cancel()
                except Exception as e:
                    results["failed"] += 1
                    logging.error(f"Error: {e}")
                    if strict:
                        print("\n\nStrict mode: Stopping due to error")
                        shutdown_requested = True
                        for f in futures:
                            f.cancel()

                pbar.update(1)

    elapsed = time.time() - start_time

    # Print summary
    print()
    print("=" * 40)
    print("Complete")
    print("=" * 40)
    processed = results["success"] + results["failed"]
    print(f"Processed: {processed}")
    print(f"Success:   {results['success']}")
    print(f"Skipped:   {results['skipped']}")
    print(f"Failed:    {results['failed']}")
    print(f"Time:      {format_time(elapsed)}")

    if not dry_run and results["success"] > 0:
        cost_tracker.print_summary(model)

    # Report on failures with breakdown by type
    total_failures = failure_tracker.get_count()
    if total_failures > 0:
        print()
        print(f"⚠️  {total_failures} failures logged to: {failure_tracker.log_file}")
        summary = failure_tracker.get_summary()
        if summary:
            print("   Breakdown:")
            for reason, count in sorted(summary.items(), key=lambda x: -x[1]):
                print(f"     - {reason}: {count}")
        print()
        print("   Review with: cat " + str(failure_tracker.log_file))

    if shutdown_requested:
        print()
        print("Stopped early. Run again to continue.")

    return ProcessingResult(
        success=results["success"],
        failed=results["failed"],
        skipped=results["skipped"],
        elapsed_seconds=elapsed,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Transcribe CIA PDF documents using GPT-4.1-mini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
IMPORTANT: This script processes PDFs from data/original_pdfs/ (all pages).
           DO NOT use JPEGs from data/images/ - they only contain first pages.

Examples:
  %(prog)s                    Process all remaining PDFs
  %(prog)s -n 100             Process 100 PDFs
  %(prog)s -n 100 --budget 5  Process up to 100 PDFs or $5
  %(prog)s --status           Show status without processing
  %(prog)s --yes              Skip confirmation prompt

Fast processing (higher OpenAI tiers):
  MAX_TOKENS_PER_MINUTE=2000000 %(prog)s --workers 50 --yes

Environment variables:
  OPENAI_MODEL             Model to use (default: gpt-4.1-mini)
  MAX_TOKENS_PER_MINUTE    Rate limit in tokens/min (default: 10000000)
        """,
    )

    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of files to process (default: all remaining)",
    )

    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    parser.add_argument(
        "--budget",
        type=float,
        default=None,
        metavar="$",
        help="Stop when estimated cost reaches this amount",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show transcription status and exit",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate processing without API calls",
    )

    # Advanced options
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help="Number of parallel workers (default: auto based on rate limits)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop on first failure (for ensuring complete transcription)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing outputs for completeness issues",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Get current status
    status = get_status()

    # Validate mode
    if args.validate:
        print(f"Validating outputs for model: {status.model}")
        result = validate_outputs(status.model)
        print_validation_report(result)
        return

    # Status-only mode
    if args.status:
        print_status(status)
        if status.remaining > 0:
            print_estimate(status.remaining, status.model)
        return

    # Nothing to do
    if status.remaining == 0:
        print_status(status)
        print("All documents have been transcribed!")
        return

    # Determine files to process
    files_to_process = status.remaining_files
    if args.limit:
        files_to_process = files_to_process[: args.limit]

    # Show status and estimate
    print_status(status)
    estimated_cost = print_estimate(len(files_to_process), status.model)

    # Budget check
    if args.budget and estimated_cost > args.budget:
        cost_per_doc = estimated_cost / len(files_to_process)
        max_docs = int(args.budget / cost_per_doc)
        files_to_process = files_to_process[:max_docs]
        print(f"Budget limit: Processing {max_docs} files (${args.budget:.2f} budget)")
        print()

    # Confirmation
    if not args.yes and not args.dry_run:
        try:
            response = input("Proceed? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("Cancelled.")
                return
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return

    # Process
    process_files(
        files=files_to_process,
        model=status.model,
        dry_run=args.dry_run,
        max_workers=args.workers,
        strict=args.strict,
    )


if __name__ == "__main__":
    main()
