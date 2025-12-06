"""
Document transcription using Claude API (Anthropic).

This module provides document transcription using Claude's vision capabilities,
with support for both real-time (single document) and batch processing modes.
Supports both image files and PDF documents as input.

Usage:
    # Single document mode with images (real-time)
    uv run python -m app.transcribe_claude --max-files 10

    # Use PDF files instead of images
    uv run python -m app.transcribe_claude --use-pdf --max-files 10

    # Batch mode (50% discount, async processing)
    uv run python -m app.transcribe_claude --batch --max-files 1000

    # Resume from previous batch
    uv run python -m app.transcribe_claude --batch --resume
"""

import os
import base64
import argparse
import json
import logging
import time
import threading
from pathlib import Path
from datetime import datetime
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from tqdm import tqdm
from anthropic import Anthropic
import anthropic
from jsonschema import Draft7Validator

from app.config import ROOT_DIR, DATA_DIR

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables
load_dotenv(ROOT_DIR / '.env')

# Initialize the Anthropic client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Default model for transcription
DEFAULT_MODEL = os.getenv("CLAUDE_TRANSCRIPTION_MODEL", "claude-sonnet-4-5-20250929")

# Models that support structured outputs (beta feature)
STRUCTURED_OUTPUT_MODELS = {
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-5",  # Alias
    # Add new models here as they get support
}

# Beta header required for structured outputs
STRUCTURED_OUTPUTS_BETA = "structured-outputs-2025-11-13"

# Load the transcription prompt
prompt_path = Path(__file__).parent / "prompts" / "metadata_prompt_v2.md"
try:
    PROMPT = prompt_path.read_text(encoding="utf-8")
    logging.info(f"Loaded prompt from: {prompt_path.name}")
except Exception as e:
    logging.error(f"Failed to read prompt file {prompt_path}: {e}")
    raise RuntimeError(f"Prompt file missing or unreadable: {prompt_path}: {e}")

# Load JSON schema for validation
schema_path = Path(__file__).parent / "prompts" / "schemas" / "metadata_schema.json"
try:
    SCHEMA = json.loads(schema_path.read_text(encoding="utf-8"))
    logging.info(f"Loaded JSON schema from: {schema_path.name}")
except Exception as e:
    logging.warning(f"Failed to load schema file {schema_path}: {e}")
    SCHEMA = None

# ---------------------------------------------------------------------------
# Pricing Configuration (per million tokens)
# ---------------------------------------------------------------------------
PRICING = {
    # Claude 4 models (with structured outputs)
    "claude-sonnet-4-5-20250929": {
        "input": 3.00 / 1_000_000,
        "output": 15.00 / 1_000_000,
        "batch_input": 1.50 / 1_000_000,
        "batch_output": 7.50 / 1_000_000,
    },
    "claude-sonnet-4-5": {
        "input": 3.00 / 1_000_000,
        "output": 15.00 / 1_000_000,
        "batch_input": 1.50 / 1_000_000,
        "batch_output": 7.50 / 1_000_000,
    },
    # Claude 3.5 models
    "claude-3-5-haiku-20241022": {
        "input": 0.80 / 1_000_000,
        "output": 4.00 / 1_000_000,
        "batch_input": 0.40 / 1_000_000,  # 50% discount
        "batch_output": 2.00 / 1_000_000,  # 50% discount
    },
    "claude-3-5-sonnet-20241022": {
        "input": 3.00 / 1_000_000,
        "output": 15.00 / 1_000_000,
        "batch_input": 1.50 / 1_000_000,
        "batch_output": 7.50 / 1_000_000,
    },
    # Claude 3 models (legacy)
    "claude-3-haiku-20240307": {
        "input": 0.25 / 1_000_000,
        "output": 1.25 / 1_000_000,
        "batch_input": 0.125 / 1_000_000,
        "batch_output": 0.625 / 1_000_000,
    },
}

# Rate limiting configuration
MAX_RPM = int(os.getenv("CLAUDE_MAX_RPM", "50"))  # Requests per minute
MAX_TPM = int(os.getenv("CLAUDE_MAX_TPM", "400000"))  # Tokens per minute
EST_TOKENS_PER_DOC = 4000  # Estimated tokens per API call (input + output)

# Global rate limiting state
request_times = deque()
token_usage = deque()
rate_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Cost Tracker
# ---------------------------------------------------------------------------
class CostTracker:
    """Thread-safe cost tracker for Claude API usage."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.lock = threading.Lock()

    def add_usage(self, input_tokens: int, output_tokens: int):
        """Track token usage."""
        with self.lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

    def get_cost(self, model: str = DEFAULT_MODEL, batch_mode: bool = False) -> float:
        """Calculate cost based on model pricing."""
        rates = PRICING.get(model, PRICING["claude-3-5-haiku-20241022"])

        if batch_mode:
            input_rate = rates.get("batch_input", rates["input"] * 0.5)
            output_rate = rates.get("batch_output", rates["output"] * 0.5)
        else:
            input_rate = rates["input"]
            output_rate = rates["output"]

        return (self.total_input_tokens * input_rate +
                self.total_output_tokens * output_rate)

    def print_summary(self, model: str = DEFAULT_MODEL, batch_mode: bool = False):
        """Print cost summary."""
        with self.lock:
            mode_str = "BATCH (50% off)" if batch_mode else "STANDARD"
            print("\n" + "-" * 70)
            print("TOKEN USAGE & COST")
            print("-" * 70)
            print(f"Model:          {model}")
            print(f"Mode:           {mode_str}")
            print(f"Input tokens:   {self.total_input_tokens:,}")
            print(f"Output tokens:  {self.total_output_tokens:,}")
            print(f"Total tokens:   {self.total_input_tokens + self.total_output_tokens:,}")
            print(f"Estimated cost: ${self.get_cost(model, batch_mode):.4f}")
            print("-" * 70)


# Global cost tracker
cost_tracker = CostTracker()


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
def wait_for_rate_limit():
    """
    Wait until we have capacity within rate limits.
    Implements sliding window for both RPM and TPM.
    """
    while True:
        with rate_lock:
            now = time.time()

            # Remove entries older than 60 seconds
            while request_times and now - request_times[0] > 60:
                request_times.popleft()
            while token_usage and now - token_usage[0][0] > 60:
                token_usage.popleft()

            # Check RPM
            if len(request_times) >= MAX_RPM:
                sleep_time = 60 - (now - request_times[0]) + 0.1
                if sleep_time > 0:
                    logging.debug(f"Rate limit (RPM): waiting {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    continue

            # Check TPM
            used_tokens = sum(tokens for _, tokens in token_usage)
            if used_tokens + EST_TOKENS_PER_DOC > MAX_TPM:
                sleep_time = 60 - (now - token_usage[0][0]) + 0.1
                if sleep_time > 0:
                    logging.debug(f"Rate limit (TPM): waiting {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    continue

            # Record this request
            request_times.append(now)
            token_usage.append((now, EST_TOKENS_PER_DOC))
            return


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_response(data: dict) -> tuple[bool, list[str]]:
    """Validate response against JSON schema."""
    if SCHEMA is None:
        return True, []

    validator = Draft7Validator(SCHEMA)
    errors = list(validator.iter_errors(data))

    if errors:
        error_msgs = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            error_msgs.append(f"{path}: {error.message}")
        return False, error_msgs

    return True, []


def auto_repair_response(data: dict) -> dict:
    """
    Automatically fix common output issues.
    Reuses logic from transcribe.py for consistency.
    """
    if not isinstance(data, dict):
        return data

    # Handle flat structure (fields at root instead of under "metadata")
    # This happens when models don't follow the nested schema exactly
    METADATA_FIELDS = {
        "document_id", "case_number", "document_date", "classification_level",
        "declassification_date", "document_type", "author", "recipients",
        "people_mentioned", "country", "city", "other_place", "document_title",
        "document_description", "archive_location", "observations", "language",
        "keywords", "page_count", "document_summary", "financial_references",
        "violence_references", "torture_references"
    }

    if "metadata" not in data and any(k in data for k in METADATA_FIELDS):
        # Restructure: move metadata fields into nested structure
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

    # Ensure all required nested structures exist
    if "financial_references" not in metadata or not isinstance(metadata.get("financial_references"), dict):
        metadata["financial_references"] = {"amounts": [], "financial_actors": [], "purposes": []}

    if "violence_references" not in metadata or not isinstance(metadata.get("violence_references"), dict):
        metadata["violence_references"] = {
            "incident_types": [], "victims": [], "perpetrators": [], "has_violence_content": False
        }

    if "torture_references" not in metadata or not isinstance(metadata.get("torture_references"), dict):
        metadata["torture_references"] = {
            "detention_centers": [], "victims": [], "perpetrators": [],
            "methods_mentioned": False, "has_torture_content": False
        }

    # Ensure confidence structure exists
    if "confidence" not in data or not isinstance(data.get("confidence"), dict):
        data["confidence"] = {"overall": 0.5, "concerns": ["Auto-generated confidence due to missing field"]}

    # Ensure text fields exist
    if "original_text" not in data:
        data["original_text"] = ""
    if "reviewed_text" not in data:
        data["reviewed_text"] = ""

    return data


# ---------------------------------------------------------------------------
# JSON Extraction (fallback for models without structured outputs)
# ---------------------------------------------------------------------------
def extract_json_from_response(text: str) -> str:
    """
    Extract JSON from Claude's response, handling markdown code blocks
    and conversational preamble.
    """
    import re

    text = text.strip()

    # Try to find JSON in markdown code block
    json_block = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if json_block:
        return json_block.group(1).strip()

    # Try to find raw JSON object (starts with {)
    json_start = text.find('{')
    if json_start != -1:
        # Find matching closing brace
        depth = 0
        for i, char in enumerate(text[json_start:], json_start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[json_start:i+1]

    # Return as-is if no JSON structure found
    return text


def supports_structured_outputs(model: str) -> bool:
    """Check if model supports structured outputs."""
    return model in STRUCTURED_OUTPUT_MODELS


def sanitize_schema_for_claude(schema: dict) -> dict:
    """
    Remove unsupported JSON Schema properties for Claude structured outputs.
    Claude doesn't support: maxItems, minItems, minLength, maxLength, pattern, etc.
    """
    import copy

    UNSUPPORTED_PROPS = {
        "$schema", "minItems", "maxItems", "minLength", "maxLength",
        "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"
    }

    def clean(obj):
        if isinstance(obj, dict):
            cleaned = {}
            for key, value in obj.items():
                if key in UNSUPPORTED_PROPS:
                    continue
                cleaned[key] = clean(value)
            return cleaned
        elif isinstance(obj, list):
            return [clean(item) for item in obj]
        else:
            return obj

    return clean(copy.deepcopy(schema))


# ---------------------------------------------------------------------------
# File Format Detection & Content Preparation
# ---------------------------------------------------------------------------
def detect_image_format(data: bytes) -> str:
    """
    Detect actual image format from file content (magic bytes).
    Returns media type string suitable for Claude API.
    """
    # Check magic bytes
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    elif data[:2] == b'\xff\xd8':
        return 'image/jpeg'
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    else:
        # Default to JPEG if unknown
        return 'image/jpeg'


def prepare_document_content(file_path: Path, use_pdf: bool = False) -> dict:
    """
    Prepare document content for Claude API.

    Args:
        file_path: Path to the file (image or PDF)
        use_pdf: If True, treat as PDF document

    Returns:
        Content block dict suitable for Claude messages API
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()

    encoded_data = base64.standard_b64encode(raw_data).decode("utf-8")
    file_size_kb = len(raw_data) / 1024

    if use_pdf or file_path.suffix.lower() == '.pdf':
        # PDF document
        logging.debug(f"Prepared PDF: {file_path.name} ({file_size_kb:.1f} KB)")
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": encoded_data,
            }
        }
    else:
        # Image file
        media_type = detect_image_format(raw_data)
        logging.debug(f"Prepared image: {file_path.name} ({file_size_kb:.1f} KB, {media_type})")
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded_data,
            }
        }


def get_source_files(use_pdf: bool = False, max_files: int = 0) -> list[Path]:
    """
    Get list of source files (images or PDFs).

    Args:
        use_pdf: If True, use PDF files from original_pdfs/
        max_files: Maximum number of files (0 = all)

    Returns:
        Sorted list of file paths
    """
    if use_pdf:
        source_dir = DATA_DIR / "original_pdfs"
        patterns = ["*.pdf"]
    else:
        source_dir = DATA_DIR / "images"
        patterns = ["*.jpg", "*.jpeg", "*.png"]

    all_files = []
    for pattern in patterns:
        all_files.extend(source_dir.glob(pattern))

    all_files = sorted(all_files)

    if max_files > 0:
        all_files = all_files[:max_files]

    return all_files


# ---------------------------------------------------------------------------
# Single Document Transcription
# ---------------------------------------------------------------------------
def transcribe_single_document(
    file_path: Path,
    output_dir: Path,
    model: str = DEFAULT_MODEL,
    skip_existing: bool = True,
    max_retries: int = 3,
    use_pdf: bool = False,
) -> dict:
    """
    Transcribe a single document (image or PDF) using Claude vision.

    Args:
        file_path: Path to the file (image or PDF)
        output_dir: Directory for output JSON files
        model: Claude model to use
        skip_existing: If True, skip if output JSON already exists
        max_retries: Maximum retry attempts for API errors
        use_pdf: If True, treat file as PDF document

    Returns:
        Dict with keys: success, cost, confidence, error, skipped
    """
    filename = file_path.name
    output_path = output_dir / f"{file_path.stem}.json"

    # Skip if already exists
    if skip_existing and output_path.exists():
        logging.debug(f"⊘ {filename} | Skipped (already exists)")
        return {
            "success": True,
            "cost": 0.0,
            "confidence": None,
            "error": None,
            "skipped": True
        }

    start_time = time.time()

    # Prepare document content (image or PDF)
    try:
        content_block = prepare_document_content(file_path, use_pdf=use_pdf)
        file_type = "PDF" if use_pdf or file_path.suffix.lower() == '.pdf' else "image"
        logging.debug(f"Prepared {file_type}: {filename}")
    except Exception as e:
        logging.error(f"✗ {filename} | Failed to read: {e}")
        return {"success": False, "cost": 0.0, "confidence": None, "error": str(e)}

    # Determine if we can use structured outputs
    use_structured = supports_structured_outputs(model)
    if use_structured:
        logging.debug(f"Using structured outputs for {model}")

    # Call Claude API with retry logic
    for attempt in range(1, max_retries + 1):
        try:
            wait_for_rate_limit()

            # Build API call parameters
            api_params = {
                "model": model,
                "max_tokens": 4096,
                "messages": [{
                    "role": "user",
                    "content": [
                        content_block,
                        {
                            "type": "text",
                            "text": PROMPT
                        }
                    ],
                }],
            }

            # Add structured outputs if supported
            if use_structured and SCHEMA:
                api_params["betas"] = [STRUCTURED_OUTPUTS_BETA]
                api_params["output_format"] = {
                    "type": "json_schema",
                    "schema": sanitize_schema_for_claude(SCHEMA)
                }
                message = client.beta.messages.create(**api_params)
            else:
                message = client.messages.create(**api_params)

            # Track usage
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens
            cost_tracker.add_usage(input_tokens, output_tokens)

            # Calculate per-document cost
            rates = PRICING.get(model, PRICING["claude-3-5-haiku-20241022"])
            doc_cost = input_tokens * rates["input"] + output_tokens * rates["output"]

            break  # Success, exit retry loop

        except anthropic.RateLimitError as e:
            if attempt == max_retries:
                logging.error(f"✗ {filename} | Rate limit after {max_retries} attempts")
                return {"success": False, "cost": 0.0, "confidence": None, "error": str(e)}
            delay = (2 ** attempt) + (time.time() % 1)
            logging.warning(f"Rate limit, retrying in {delay:.1f}s (attempt {attempt}/{max_retries})")
            time.sleep(delay)

        except anthropic.APIError as e:
            if attempt == max_retries:
                logging.error(f"✗ {filename} | API error after {max_retries} attempts: {e}")
                return {"success": False, "cost": 0.0, "confidence": None, "error": str(e)}
            delay = 2 ** attempt
            logging.warning(f"API error, retrying in {delay}s: {e}")
            time.sleep(delay)

    # Parse response
    response_text = message.content[0].text

    # For structured outputs, response should be valid JSON
    # For other models, extract JSON from potentially conversational response
    if use_structured:
        cleaned_text = response_text.strip()
    else:
        cleaned_text = extract_json_from_response(response_text)

    # Parse JSON
    try:
        response_data = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logging.error(f"✗ {filename} | JSON parse error: {e}")
        logging.debug(f"Raw response (first 500 chars): {response_text[:500]}")
        return {"success": False, "cost": doc_cost, "confidence": None, "error": f"JSON parse error: {e}"}

    # Auto-repair and validate
    response_data = auto_repair_response(response_data)
    is_valid, errors = validate_response(response_data)

    if not is_valid:
        logging.warning(f"⚠ {filename} | Validation warnings: {'; '.join(errors[:3])}")
        # Continue anyway - auto-repair should have fixed critical issues

    # Extract confidence
    confidence_score = None
    if "confidence" in response_data:
        confidence_data = response_data["confidence"]
        if isinstance(confidence_data, dict) and "overall" in confidence_data:
            confidence_score = confidence_data["overall"]

    # Save result
    try:
        output_path.write_text(
            json.dumps(response_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        elapsed = time.time() - start_time
        conf_str = f"{confidence_score:.2f}" if confidence_score else "N/A"
        logging.info(f"✓ {filename} | ${doc_cost:.4f} | {elapsed:.1f}s | conf: {conf_str}")

        return {
            "success": True,
            "cost": doc_cost,
            "confidence": confidence_score,
            "error": None,
            "skipped": False
        }

    except Exception as e:
        logging.error(f"✗ {filename} | Failed to save: {e}")
        return {"success": False, "cost": doc_cost, "confidence": confidence_score, "error": str(e)}


# ---------------------------------------------------------------------------
# Batch Processing (Batch API)
# ---------------------------------------------------------------------------
def prepare_batch_requests(
    file_paths: list[Path],
    model: str = DEFAULT_MODEL,
    use_pdf: bool = False,
) -> list[dict]:
    """
    Prepare batch API requests for multiple documents.

    Args:
        file_paths: List of file paths (images or PDFs)
        model: Claude model to use
        use_pdf: Treat files as PDFs

    Returns:
        List of batch request objects
    """
    requests = []

    for file_path in tqdm(file_paths, desc="Preparing batch requests"):
        try:
            content_block = prepare_document_content(file_path, use_pdf=use_pdf)

            requests.append({
                "custom_id": file_path.stem,
                "params": {
                    "model": model,
                    "max_tokens": 4096,
                    "messages": [{
                        "role": "user",
                        "content": [
                            content_block,
                            {
                                "type": "text",
                                "text": PROMPT
                            }
                        ],
                    }]
                }
            })

        except Exception as e:
            logging.error(f"Failed to prepare {file_path.name}: {e}")
            continue

    return requests


def submit_batch(requests: list[dict]) -> str:
    """
    Submit batch job to Claude API.

    Args:
        requests: List of batch request objects

    Returns:
        Batch ID
    """
    logging.info(f"Submitting batch with {len(requests)} requests...")

    batch = client.messages.batches.create(requests=requests)

    logging.info(f"Batch submitted: {batch.id}")
    logging.info(f"Status: {batch.processing_status}")

    return batch.id


def poll_batch_status(batch_id: str, poll_interval: int = 60) -> dict:
    """
    Poll batch status until completion.

    Args:
        batch_id: The batch ID to poll
        poll_interval: Seconds between polls

    Returns:
        Completed batch object
    """
    logging.info(f"Polling batch {batch_id} (interval: {poll_interval}s)...")

    while True:
        batch = client.messages.batches.retrieve(batch_id)

        processed = batch.request_counts.processing if hasattr(batch.request_counts, 'processing') else 0
        succeeded = batch.request_counts.succeeded if hasattr(batch.request_counts, 'succeeded') else 0
        errored = batch.request_counts.errored if hasattr(batch.request_counts, 'errored') else 0

        logging.info(
            f"Batch {batch_id}: {batch.processing_status} | "
            f"processed: {processed}, succeeded: {succeeded}, errored: {errored}"
        )

        if batch.processing_status == "ended":
            return batch

        time.sleep(poll_interval)


def retrieve_batch_results(batch_id: str, output_dir: Path) -> dict:
    """
    Retrieve and save results from completed batch.

    Args:
        batch_id: The batch ID
        output_dir: Directory to save JSON results

    Returns:
        Summary dict with success/error counts
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {"success": 0, "failed": 0, "total_cost": 0.0}

    logging.info(f"Retrieving results for batch {batch_id}...")

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id

        if result.result.type == "succeeded":
            try:
                # Extract response - handle different content structures
                message = result.result.message
                if hasattr(message, 'content') and len(message.content) > 0:
                    content_block = message.content[0]
                    if hasattr(content_block, 'text'):
                        response_text = content_block.text
                    else:
                        response_text = str(content_block)
                else:
                    logging.error(f"✗ {custom_id} | No content in response")
                    results["failed"] += 1
                    continue

                if not response_text or not response_text.strip():
                    logging.error(f"✗ {custom_id} | Empty response text")
                    results["failed"] += 1
                    continue

                # Use the same JSON extraction as real-time mode
                cleaned_text = extract_json_from_response(response_text)

                response_data = json.loads(cleaned_text)
                response_data = auto_repair_response(response_data)

                # Save
                output_path = output_dir / f"{custom_id}.json"
                output_path.write_text(
                    json.dumps(response_data, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )

                # Track cost
                usage = result.result.message.usage
                input_tokens = usage.input_tokens
                output_tokens = usage.output_tokens
                cost_tracker.add_usage(input_tokens, output_tokens)

                results["success"] += 1
                logging.info(f"✓ {custom_id}")

            except json.JSONDecodeError as e:
                logging.error(f"✗ {custom_id} | JSON parse error: {e}")
                logging.debug(f"Response text (first 200 chars): {response_text[:200] if response_text else 'EMPTY'}")
                results["failed"] += 1
            except Exception as e:
                logging.error(f"✗ {custom_id} | Processing error: {e}")
                results["failed"] += 1
        else:
            error_msg = getattr(result.result, 'error', 'Unknown error')
            logging.error(f"✗ {custom_id} | API error: {error_msg}")
            results["failed"] += 1

    return results


# ---------------------------------------------------------------------------
# Model Output Directory Management
# ---------------------------------------------------------------------------
def get_model_output_dir(model: str) -> Path:
    """
    Get model-specific output directory.
    Each model has its own directory to track outputs separately.

    Example: data/generated_transcripts/claude-sonnet-4-5-20250929/
    """
    # Sanitize model name for directory (replace special chars)
    safe_model_name = model.replace("/", "-").replace(":", "-")
    output_dir = DATA_DIR / "generated_transcripts" / safe_model_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def list_model_outputs() -> dict[str, int]:
    """List all model output directories and their file counts."""
    base_dir = DATA_DIR / "generated_transcripts"
    if not base_dir.exists():
        return {}

    results = {}
    for subdir in base_dir.iterdir():
        if subdir.is_dir():
            count = len(list(subdir.glob("*.json")))
            results[subdir.name] = count
    return results


# ---------------------------------------------------------------------------
# Cost Estimation
# ---------------------------------------------------------------------------
def estimate_cost(
    num_files: int,
    model: str = DEFAULT_MODEL,
    batch_mode: bool = False
) -> float:
    """Estimate cost for processing files."""
    rates = PRICING.get(model, PRICING["claude-3-5-haiku-20241022"])

    # Estimated tokens per document
    est_input = 2600  # ~1600 image + ~1000 prompt
    est_output = 1300

    if batch_mode:
        input_rate = rates.get("batch_input", rates["input"] * 0.5)
        output_rate = rates.get("batch_output", rates["output"] * 0.5)
    else:
        input_rate = rates["input"]
        output_rate = rates["output"]

    per_doc = est_input * input_rate + est_output * output_rate
    return num_files * per_doc


def print_cost_estimate(
    num_files: int,
    model: str = DEFAULT_MODEL,
    batch_mode: bool = False
):
    """Print cost estimate and ask for confirmation."""
    cost = estimate_cost(num_files, model, batch_mode)
    mode_str = "BATCH (50% off)" if batch_mode else "STANDARD"
    output_dir = get_model_output_dir(model)

    print("\n" + "=" * 70)
    print("COST ESTIMATE")
    print("=" * 70)
    print(f"Files to process:  {num_files:,}")
    print(f"Model:             {model}")
    print(f"Mode:              {mode_str}")
    print(f"Output directory:  {output_dir.relative_to(DATA_DIR.parent)}")
    print(f"Estimated cost:    ${cost:.2f}")
    print("=" * 70)

    return cost


# ---------------------------------------------------------------------------
# Main Processing Functions
# ---------------------------------------------------------------------------
def process_documents_realtime(
    max_files: int = 0,
    resume: bool = True,
    max_workers: int = 3,
    model: str = DEFAULT_MODEL,
    skip_confirm: bool = False,
    use_pdf: bool = False,
):
    """
    Process documents in real-time mode (standard API).

    Args:
        max_files: Number of files to process (0 = all)
        resume: Skip already-processed files
        max_workers: Parallel workers
        model: Claude model to use
        skip_confirm: Skip cost confirmation
        use_pdf: Use PDF files instead of images
    """
    output_dir = get_model_output_dir(model)
    source_type = "PDFs" if use_pdf else "images"
    logging.info(f"Source: {source_type} | Output: {output_dir}")

    # Get source files (images or PDFs)
    all_files = get_source_files(use_pdf=use_pdf, max_files=max_files)

    # Filter already processed
    if resume:
        to_process = [
            f for f in all_files
            if not (output_dir / f"{f.stem}.json").exists()
        ]
    else:
        to_process = all_files

    if not to_process:
        logging.info("No files to process")
        return

    # Cost estimate
    cost = print_cost_estimate(len(to_process), model, batch_mode=False)

    if not skip_confirm:
        response = input("\nProceed? [y/n]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled.")
            return

    print()
    logging.info(f"Processing {len(to_process)} {source_type} with {max_workers} workers")

    # Process
    results = {"success": 0, "skipped": 0, "failed": 0}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                transcribe_single_document, f, output_dir, model, resume, 3, use_pdf
            ): f for f in to_process
        }

        with tqdm(total=len(futures), desc="Processing", unit="doc") as pbar:
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.get("skipped"):
                        results["skipped"] += 1
                    elif result.get("success"):
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    logging.error(f"Unexpected error: {e}")
                    results["failed"] += 1
                finally:
                    pbar.update(1)

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"Total files:    {len(to_process)}")
    print(f"✓ Successful:   {results['success']}")
    print(f"⊘ Skipped:      {results['skipped']}")
    print(f"✗ Failed:       {results['failed']}")
    print(f"Time:           {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print("=" * 70)

    cost_tracker.print_summary(model, batch_mode=False)


def process_documents_batch(
    max_files: int = 0,
    resume: bool = True,
    model: str = DEFAULT_MODEL,
    skip_confirm: bool = False,
    batch_size: int = 5000,
    use_pdf: bool = False,
):
    """
    Process documents using Batch API (50% discount).

    Args:
        max_files: Number of files to process (0 = all)
        resume: Skip already-processed files
        model: Claude model to use
        skip_confirm: Skip cost confirmation
        batch_size: Max requests per batch (API limit is 10,000)
        use_pdf: Use PDF files instead of images
    """
    output_dir = get_model_output_dir(model)
    source_type = "PDFs" if use_pdf else "images"
    logging.info(f"Source: {source_type} | Output: {output_dir}")

    # Get source files (images or PDFs)
    all_files = get_source_files(use_pdf=use_pdf, max_files=max_files)

    # Filter already processed
    if resume:
        to_process = [
            f for f in all_files
            if not (output_dir / f"{f.stem}.json").exists()
        ]
    else:
        to_process = all_files

    if not to_process:
        logging.info("No files to process")
        return

    # Cost estimate
    cost = print_cost_estimate(len(to_process), model, batch_mode=True)

    if not skip_confirm:
        response = input("\nProceed with batch processing? [y/n]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled.")
            return

    print()

    # Split into batches
    batches = [to_process[i:i + batch_size] for i in range(0, len(to_process), batch_size)]
    logging.info(f"Processing {len(to_process)} {source_type} in {len(batches)} batch(es)")

    total_results = {"success": 0, "failed": 0}

    for i, batch_files in enumerate(batches, 1):
        logging.info(f"\n--- Batch {i}/{len(batches)} ({len(batch_files)} documents) ---")

        # Prepare requests
        requests = prepare_batch_requests(batch_files, model, use_pdf=use_pdf)

        if not requests:
            logging.error("No valid requests prepared")
            continue

        # Submit batch
        batch_id = submit_batch(requests)

        # Save batch ID for resume capability
        batch_state_file = DATA_DIR / "batch_state.json"
        batch_state = {
            "batch_id": batch_id,
            "submitted_at": datetime.now().isoformat(),
            "num_requests": len(requests),
            "model": model,
        }
        batch_state_file.write_text(json.dumps(batch_state, indent=2))
        logging.info(f"Batch state saved to {batch_state_file}")

        # Poll until complete
        batch = poll_batch_status(batch_id)

        # Retrieve results
        results = retrieve_batch_results(batch_id, output_dir)
        total_results["success"] += results["success"]
        total_results["failed"] += results["failed"]

    # Summary
    print("\n" + "=" * 70)
    print("BATCH PROCESSING COMPLETE")
    print("=" * 70)
    print(f"Total batches:  {len(batches)}")
    print(f"✓ Successful:   {total_results['success']}")
    print(f"✗ Failed:       {total_results['failed']}")
    print("=" * 70)

    cost_tracker.print_summary(model, batch_mode=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe documents using Claude API (Anthropic)"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Number of files to process (0 = all)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Skip already-processed files (default: True)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Process all files, even if already done"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use Batch API (50%% discount, async processing)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Claude model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Parallel workers for real-time mode (default: 3)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Max requests per batch (default: 5000, max: 10000)"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--use-pdf",
        action="store_true",
        help="Use PDF files from original_pdfs/ instead of images"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show status of all model output directories"
    )

    args = parser.parse_args()

    # Handle status command
    if args.status:
        print("\n" + "=" * 70)
        print("MODEL OUTPUT STATUS")
        print("=" * 70)

        # Count total images
        image_dir = DATA_DIR / "images"
        total_images = len(list(image_dir.glob("*.jpg"))) + len(list(image_dir.glob("*.jpeg")))
        print(f"Total source images: {total_images:,}")
        print()

        # List model outputs
        outputs = list_model_outputs()
        if outputs:
            print(f"{'Model':<45} {'Files':<10} {'Progress'}")
            print("-" * 70)
            for model_name, count in sorted(outputs.items()):
                pct = (count / total_images * 100) if total_images > 0 else 0
                bar_len = int(pct / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                print(f"{model_name:<45} {count:<10} {bar} {pct:.1f}%")
        else:
            print("No model outputs found yet.")

        print("=" * 70)
        exit(0)

    resume = not args.no_resume

    if args.batch:
        process_documents_batch(
            max_files=args.max_files,
            resume=resume,
            model=args.model,
            skip_confirm=args.yes,
            batch_size=min(args.batch_size, 10000),
            use_pdf=args.use_pdf,
        )
    else:
        process_documents_realtime(
            max_files=args.max_files,
            resume=resume,
            max_workers=args.max_workers,
            model=args.model,
            skip_confirm=args.yes,
            use_pdf=args.use_pdf,
        )
