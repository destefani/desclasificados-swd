"""
Document transcription using OpenAI API with native PDF support.

This module provides document transcription using OpenAI's vision capabilities,
with native PDF support (no conversion needed) for gpt-4.1 and gpt-4o models.

Usage:
    # Transcribe PDFs with gpt-4.1-nano
    uv run python -m app.transcribe_openai --model gpt-4.1-nano --max-files 10

    # Full pass with budget limit
    uv run python -m app.transcribe_openai --model gpt-4.1-nano --max-cost 35 --resume

    # Check status
    uv run python -m app.transcribe_openai --status
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
from openai import OpenAI
import openai
from jsonschema import Draft7Validator

from app.config import ROOT_DIR, DATA_DIR

# Batch API directories
BATCH_DIR = DATA_DIR / "batch_jobs"
BATCH_DIR.mkdir(parents=True, exist_ok=True)

# Max files per batch (to stay under 512MB upload limit)
# ~195KB per request average → ~2600 files per 512MB
# Using 2000 for safety margin
MAX_FILES_PER_BATCH = 2000

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables
load_dotenv(ROOT_DIR / '.env')

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Default model for transcription
DEFAULT_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4.1-nano")

# Models that support PDF input (vision-capable)
PDF_CAPABLE_MODELS = {
    "gpt-4.1-nano",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4o-2024-11-20",
}

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
    # GPT-4.1 family (April 2025)
    "gpt-4.1-nano": {
        "input": 0.10 / 1_000_000,
        "output": 0.40 / 1_000_000,
    },
    "gpt-4.1-mini": {
        "input": 0.40 / 1_000_000,
        "output": 1.60 / 1_000_000,
    },
    "gpt-4.1": {
        "input": 2.00 / 1_000_000,
        "output": 8.00 / 1_000_000,
    },
    # GPT-4o family
    "gpt-4o": {
        "input": 2.50 / 1_000_000,
        "output": 10.00 / 1_000_000,
    },
    "gpt-4o-mini": {
        "input": 0.15 / 1_000_000,
        "output": 0.60 / 1_000_000,
    },
}

# Rate limiting configuration
MAX_RPM = int(os.getenv("OPENAI_MAX_RPM", "500"))  # Requests per minute
MAX_TPM = int(os.getenv("OPENAI_MAX_TPM", "200000"))  # Tokens per minute
EST_TOKENS_PER_DOC = 6000  # Estimated tokens per API call (higher for PDFs)

# Global rate limiting state
request_times = deque()
token_usage = deque()
rate_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Cost Tracker
# ---------------------------------------------------------------------------
class CostTracker:
    """Thread-safe cost tracker for OpenAI API usage."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.lock = threading.Lock()

    def add_usage(self, input_tokens: int, output_tokens: int):
        """Track token usage."""
        with self.lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

    def get_cost(self, model: str = DEFAULT_MODEL) -> float:
        """Calculate cost based on model pricing."""
        rates = PRICING.get(model, PRICING["gpt-4.1-nano"])
        return (self.total_input_tokens * rates["input"] +
                self.total_output_tokens * rates["output"])

    def print_summary(self, model: str = DEFAULT_MODEL):
        """Print cost summary."""
        with self.lock:
            print("\n" + "-" * 70)
            print("TOKEN USAGE & COST")
            print("-" * 70)
            print(f"Model:          {model}")
            print(f"Input tokens:   {self.total_input_tokens:,}")
            print(f"Output tokens:  {self.total_output_tokens:,}")
            print(f"Total tokens:   {self.total_input_tokens + self.total_output_tokens:,}")
            print(f"Estimated cost: ${self.get_cost(model):.4f}")
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
    """
    if not isinstance(data, dict):
        return data

    # Handle flat structure (fields at root instead of under "metadata")
    METADATA_FIELDS = {
        "document_id", "case_number", "document_date", "classification_level",
        "declassification_date", "document_type", "author", "recipients",
        "people_mentioned", "country", "city", "other_place", "document_title",
        "document_description", "archive_location", "observations", "language",
        "keywords", "page_count", "document_summary", "financial_references",
        "violence_references", "torture_references"
    }

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
# PDF Content Preparation
# ---------------------------------------------------------------------------
def prepare_pdf_content(file_path: Path) -> dict:
    """
    Prepare PDF content for OpenAI API.

    OpenAI supports PDF input directly via file type specification.

    Args:
        file_path: Path to the PDF file

    Returns:
        Content block dict suitable for OpenAI messages API
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()

    encoded_data = base64.standard_b64encode(raw_data).decode("utf-8")
    file_size_kb = len(raw_data) / 1024

    logging.debug(f"Prepared PDF: {file_path.name} ({file_size_kb:.1f} KB)")

    # OpenAI PDF input format
    return {
        "type": "file",
        "file": {
            "filename": file_path.name,
            "file_data": f"data:application/pdf;base64,{encoded_data}",
        }
    }


def prepare_image_content(file_path: Path) -> dict:
    """
    Prepare image content for OpenAI API.

    Args:
        file_path: Path to the image file

    Returns:
        Content block dict suitable for OpenAI messages API
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()

    encoded_data = base64.standard_b64encode(raw_data).decode("utf-8")

    # Detect media type
    if raw_data[:8] == b'\x89PNG\r\n\x1a\n':
        media_type = 'image/png'
    elif raw_data[:2] == b'\xff\xd8':
        media_type = 'image/jpeg'
    else:
        media_type = 'image/jpeg'

    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{media_type};base64,{encoded_data}"
        }
    }


def get_source_files(use_images: bool = False, max_files: int = 0) -> list[Path]:
    """
    Get list of source files (PDFs or images).

    Args:
        use_images: If True, use images instead of PDFs
        max_files: Maximum number of files (0 = all)

    Returns:
        Sorted list of file paths
    """
    if use_images:
        source_dir = DATA_DIR / "images"
        patterns = ["*.jpg", "*.jpeg", "*.png"]
    else:
        source_dir = DATA_DIR / "original_pdfs"
        patterns = ["*.pdf"]

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
    use_images: bool = False,
) -> dict:
    """
    Transcribe a single document (PDF or image) using OpenAI vision.

    Args:
        file_path: Path to the file (PDF or image)
        output_dir: Directory for output JSON files
        model: OpenAI model to use
        skip_existing: If True, skip if output JSON already exists
        max_retries: Maximum retry attempts for API errors
        use_images: If True, treat file as image instead of PDF

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

    # Prepare content
    try:
        if use_images or file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            content_block = prepare_image_content(file_path)
            file_type = "image"
        else:
            content_block = prepare_pdf_content(file_path)
            file_type = "PDF"
        logging.debug(f"Prepared {file_type}: {filename}")
    except Exception as e:
        logging.error(f"✗ {filename} | Failed to read: {e}")
        return {"success": False, "cost": 0.0, "confidence": None, "error": str(e)}

    # Call OpenAI API with retry logic
    for attempt in range(1, max_retries + 1):
        try:
            wait_for_rate_limit()

            # Build messages
            messages = [{
                "role": "user",
                "content": [
                    content_block,
                    {
                        "type": "text",
                        "text": PROMPT
                    }
                ],
            }]

            # API call - use higher token limit to avoid truncation
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=8192,
                response_format={"type": "json_object"}
            )

            # Track usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost_tracker.add_usage(input_tokens, output_tokens)

            # Calculate per-document cost
            rates = PRICING.get(model, PRICING["gpt-4.1-nano"])
            doc_cost = input_tokens * rates["input"] + output_tokens * rates["output"]

            break  # Success, exit retry loop

        except openai.RateLimitError as e:
            if attempt == max_retries:
                logging.error(f"✗ {filename} | Rate limit after {max_retries} attempts")
                return {"success": False, "cost": 0.0, "confidence": None, "error": str(e)}
            delay = (2 ** attempt) + (time.time() % 1)
            logging.warning(f"Rate limit, retrying in {delay:.1f}s (attempt {attempt}/{max_retries})")
            time.sleep(delay)

        except openai.APIError as e:
            if attempt == max_retries:
                logging.error(f"✗ {filename} | API error after {max_retries} attempts: {e}")
                return {"success": False, "cost": 0.0, "confidence": None, "error": str(e)}
            delay = 2 ** attempt
            logging.warning(f"API error, retrying in {delay}s: {e}")
            time.sleep(delay)

    # Parse response
    response_text = response.choices[0].message.content

    # Parse JSON
    try:
        response_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logging.error(f"✗ {filename} | JSON parse error: {e}")
        logging.debug(f"Raw response (first 500 chars): {response_text[:500]}")
        return {"success": False, "cost": doc_cost, "confidence": None, "error": f"JSON parse error: {e}"}

    # Auto-repair and validate
    response_data = auto_repair_response(response_data)
    is_valid, errors = validate_response(response_data)

    if not is_valid:
        logging.warning(f"⚠ {filename} | Validation warnings: {'; '.join(errors[:3])}")

    # Extract confidence
    confidence_score = None
    if "confidence" in response_data:
        confidence_data = response_data["confidence"]
        if isinstance(confidence_data, dict) and "overall" in confidence_data:
            confidence_score = confidence_data["overall"]

    # Check for placeholder text (quality check)
    original_text = response_data.get("original_text", "")
    if len(original_text) < 100 or "Full OCR text" in original_text or "full text" in original_text.lower():
        logging.warning(f"⚠ {filename} | Possible placeholder text detected (len={len(original_text)})")

    # Save result
    try:
        output_path.write_text(
            json.dumps(response_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        elapsed = time.time() - start_time
        conf_str = f"{confidence_score:.2f}" if confidence_score else "N/A"
        text_len = len(original_text)
        logging.info(f"✓ {filename} | ${doc_cost:.4f} | {elapsed:.1f}s | conf: {conf_str} | text: {text_len}")

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
# Model Output Directory Management
# ---------------------------------------------------------------------------
def get_model_output_dir(model: str) -> Path:
    """
    Get model-specific output directory.
    """
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
    avg_pages: float = 3.54
) -> float:
    """Estimate cost for processing files."""
    rates = PRICING.get(model, PRICING["gpt-4.1-nano"])

    # Estimated tokens per document (based on avg pages)
    est_input = int(avg_pages * 1600)  # ~1600 tokens per page
    est_output = 2000

    per_doc = est_input * rates["input"] + est_output * rates["output"]
    return num_files * per_doc


def print_cost_estimate(
    num_files: int,
    model: str = DEFAULT_MODEL
):
    """Print cost estimate and ask for confirmation."""
    cost = estimate_cost(num_files, model)
    output_dir = get_model_output_dir(model)

    print("\n" + "=" * 70)
    print("COST ESTIMATE")
    print("=" * 70)
    print(f"Files to process:  {num_files:,}")
    print(f"Model:             {model}")
    print(f"Output directory:  {output_dir.relative_to(DATA_DIR.parent)}")
    print(f"Estimated cost:    ${cost:.2f}")
    print("=" * 70)

    return cost


# ---------------------------------------------------------------------------
# Main Processing Function
# ---------------------------------------------------------------------------
def process_documents(
    max_files: int = 0,
    resume: bool = True,
    max_workers: int = 5,
    model: str = DEFAULT_MODEL,
    skip_confirm: bool = False,
    use_images: bool = False,
    max_cost: float = None,
):
    """
    Process documents using OpenAI API.

    Args:
        max_files: Number of files to process (0 = all)
        resume: Skip already-processed files
        max_workers: Parallel workers
        model: OpenAI model to use
        skip_confirm: Skip cost confirmation
        use_images: Use images instead of PDFs
        max_cost: Maximum cost limit
    """
    output_dir = get_model_output_dir(model)
    source_type = "images" if use_images else "PDFs"
    logging.info(f"Source: {source_type} | Output: {output_dir}")

    # Get source files
    all_files = get_source_files(use_images=use_images, max_files=max_files)

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
    estimated_cost = print_cost_estimate(len(to_process), model)

    if max_cost and estimated_cost > max_cost:
        print(f"\n⚠️  Estimated cost (${estimated_cost:.2f}) exceeds max_cost (${max_cost:.2f})")
        print(f"   Will stop when max_cost is reached.")

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
                transcribe_single_document, f, output_dir, model, resume, 3, use_images
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

                    # Check cost limit
                    if max_cost and cost_tracker.get_cost(model) >= max_cost:
                        logging.warning(f"Max cost (${max_cost:.2f}) reached. Stopping.")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

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

    cost_tracker.print_summary(model)


# ---------------------------------------------------------------------------
# Batch API Functions (50% cost savings)
# ---------------------------------------------------------------------------
def create_batch_requests_file(
    files: list[Path],
    model: str,
    use_images: bool = False
) -> Path:
    """
    Create JSONL file with batch requests for OpenAI Batch API.

    Args:
        files: List of PDF/image files to process
        model: OpenAI model to use
        use_images: If True, treat files as images

    Returns:
        Path to the created JSONL file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = BATCH_DIR / f"batch_requests_{timestamp}.jsonl"

    logging.info(f"Creating batch requests file: {jsonl_path.name}")

    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for file_path in tqdm(files, desc="Preparing requests", unit="file"):
            try:
                # Prepare content block
                if use_images or file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    content_block = prepare_image_content(file_path)
                else:
                    content_block = prepare_pdf_content(file_path)

                # Create batch request object
                request = {
                    "custom_id": file_path.stem,  # Use filename as ID
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "messages": [{
                            "role": "user",
                            "content": [
                                content_block,
                                {"type": "text", "text": PROMPT}
                            ]
                        }],
                        "max_completion_tokens": 8192,
                        "response_format": {"type": "json_object"}
                    }
                }

                f.write(json.dumps(request) + '\n')

            except Exception as e:
                logging.error(f"Failed to prepare {file_path.name}: {e}")

    file_size_mb = jsonl_path.stat().st_size / (1024 * 1024)
    logging.info(f"Created batch file: {jsonl_path.name} ({file_size_mb:.1f} MB, {len(files)} requests)")

    return jsonl_path


def submit_batch(jsonl_path: Path) -> str:
    """
    Upload batch file and create batch job.

    Args:
        jsonl_path: Path to JSONL requests file

    Returns:
        Batch job ID
    """
    logging.info(f"Uploading batch file: {jsonl_path.name}")

    # Upload file
    with open(jsonl_path, 'rb') as f:
        batch_file = client.files.create(file=f, purpose="batch")

    logging.info(f"Uploaded file ID: {batch_file.id}")

    # Create batch job
    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    logging.info(f"Created batch job: {batch_job.id}")
    logging.info(f"Status: {batch_job.status}")

    # Save batch info
    batch_info = {
        "batch_id": batch_job.id,
        "input_file_id": batch_file.id,
        "jsonl_path": str(jsonl_path),
        "created_at": datetime.now().isoformat(),
        "status": batch_job.status
    }

    info_path = BATCH_DIR / f"batch_info_{batch_job.id}.json"
    info_path.write_text(json.dumps(batch_info, indent=2))

    return batch_job.id


def check_batch_status(batch_id: str) -> dict:
    """
    Check status of a batch job.

    Args:
        batch_id: Batch job ID

    Returns:
        Batch status dict
    """
    batch = client.batches.retrieve(batch_id)

    status = {
        "id": batch.id,
        "status": batch.status,
        "created_at": batch.created_at,
        "completed_at": getattr(batch, 'completed_at', None),
        "failed_at": getattr(batch, 'failed_at', None),
        "request_counts": {
            "total": batch.request_counts.total if batch.request_counts else 0,
            "completed": batch.request_counts.completed if batch.request_counts else 0,
            "failed": batch.request_counts.failed if batch.request_counts else 0,
        },
        "output_file_id": getattr(batch, 'output_file_id', None),
        "error_file_id": getattr(batch, 'error_file_id', None),
    }

    return status


def wait_for_batch(batch_id: str, poll_interval: int = 60) -> dict:
    """
    Wait for batch job to complete, polling periodically.

    Args:
        batch_id: Batch job ID
        poll_interval: Seconds between status checks

    Returns:
        Final batch status
    """
    logging.info(f"Waiting for batch {batch_id} to complete...")
    logging.info(f"(Polling every {poll_interval}s - you can safely Ctrl+C and resume later)")

    start_time = time.time()

    while True:
        status = check_batch_status(batch_id)

        elapsed = time.time() - start_time
        elapsed_str = f"{elapsed/60:.1f}min"

        completed = status['request_counts']['completed']
        total = status['request_counts']['total']
        failed = status['request_counts']['failed']
        pct = (completed / total * 100) if total > 0 else 0

        print(f"\r[{elapsed_str}] Status: {status['status']} | Progress: {completed}/{total} ({pct:.1f}%) | Failed: {failed}", end="", flush=True)

        if status['status'] in ['completed', 'failed', 'expired', 'cancelled']:
            print()  # New line
            logging.info(f"Batch {status['status']} after {elapsed_str}")
            return status

        time.sleep(poll_interval)


def download_batch_results(batch_id: str, output_dir: Path) -> dict:
    """
    Download and process batch results.

    Args:
        batch_id: Batch job ID
        output_dir: Directory to save individual JSON files

    Returns:
        Summary dict with success/failure counts
    """
    status = check_batch_status(batch_id)

    if status['status'] != 'completed':
        logging.error(f"Batch not completed. Status: {status['status']}")
        return {"success": 0, "failed": 0, "error": f"Batch status: {status['status']}"}

    if not status['output_file_id']:
        logging.error("No output file available")
        return {"success": 0, "failed": 0, "error": "No output file"}

    logging.info(f"Downloading results from batch {batch_id}")

    # Download output file
    result_content = client.files.content(status['output_file_id']).content

    # Save raw results
    raw_results_path = BATCH_DIR / f"batch_results_{batch_id}.jsonl"
    raw_results_path.write_bytes(result_content)
    logging.info(f"Saved raw results: {raw_results_path.name}")

    # Process each result
    results = {"success": 0, "failed": 0, "errors": []}

    for line in result_content.decode('utf-8').strip().split('\n'):
        try:
            result = json.loads(line)
            custom_id = result['custom_id']

            if result.get('error'):
                results['failed'] += 1
                results['errors'].append(f"{custom_id}: {result['error']}")
                logging.error(f"✗ {custom_id} | API error: {result['error']}")
                continue

            # Extract response content
            response_body = result.get('response', {}).get('body', {})
            choices = response_body.get('choices', [])

            if not choices:
                results['failed'] += 1
                logging.error(f"✗ {custom_id} | No choices in response")
                continue

            content = choices[0].get('message', {}).get('content', '')

            # Parse JSON response
            try:
                response_data = json.loads(content)
                response_data = auto_repair_response(response_data)
            except json.JSONDecodeError as e:
                results['failed'] += 1
                logging.error(f"✗ {custom_id} | JSON parse error: {e}")
                continue

            # Save to output file
            output_path = output_dir / f"{custom_id}.json"
            output_path.write_text(
                json.dumps(response_data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

            results['success'] += 1

            # Track usage for cost calculation
            usage = response_body.get('usage', {})
            if usage:
                cost_tracker.add_usage(
                    usage.get('prompt_tokens', 0),
                    usage.get('completion_tokens', 0)
                )

        except Exception as e:
            results['failed'] += 1
            logging.error(f"Error processing result: {e}")

    logging.info(f"Processed {results['success']} successful, {results['failed']} failed")

    # Download error file if exists
    if status.get('error_file_id'):
        error_content = client.files.content(status['error_file_id']).content
        error_path = BATCH_DIR / f"batch_errors_{batch_id}.jsonl"
        error_path.write_bytes(error_content)
        logging.info(f"Saved error file: {error_path.name}")

    return results


def run_batch_transcription(
    max_files: int = 0,
    model: str = DEFAULT_MODEL,
    use_images: bool = False,
    resume: bool = True,
    skip_confirm: bool = False,
):
    """
    Run batch transcription using OpenAI Batch API (50% cost savings).

    Automatically splits large file sets into chunks of MAX_FILES_PER_BATCH
    to stay under OpenAI's 512MB file upload limit.

    Args:
        max_files: Maximum files to process (0 = all)
        model: OpenAI model to use
        use_images: Use images instead of PDFs
        resume: Skip already-processed files
        skip_confirm: Skip confirmation prompt
    """
    output_dir = get_model_output_dir(model)

    # Get files to process
    all_files = get_source_files(use_images=use_images, max_files=max_files)

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

    # Calculate number of batches needed
    num_batches = (len(to_process) + MAX_FILES_PER_BATCH - 1) // MAX_FILES_PER_BATCH

    # Cost estimate (with 50% batch discount)
    regular_cost = estimate_cost(len(to_process), model)
    batch_cost = regular_cost * 0.5

    print("\n" + "=" * 70)
    print("BATCH API - 50% COST SAVINGS")
    print("=" * 70)
    print(f"Files to process:  {len(to_process):,}")
    print(f"Batches needed:    {num_batches} (max {MAX_FILES_PER_BATCH:,} files/batch)")
    print(f"Model:             {model}")
    print(f"Output directory:  {output_dir.relative_to(DATA_DIR.parent)}")
    print(f"Regular cost:      ${regular_cost:.2f}")
    print(f"Batch cost (50%):  ${batch_cost:.2f} ← YOU PAY THIS")
    print(f"You save:          ${regular_cost - batch_cost:.2f}")
    print("=" * 70)
    print("\nNote: Results typically ready in 2-4 hours per batch (max 24h)")

    if not skip_confirm:
        response = input("\nProceed with batch? [y/n]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled.")
            return

    # Split files into chunks
    chunks = [
        to_process[i:i + MAX_FILES_PER_BATCH]
        for i in range(0, len(to_process), MAX_FILES_PER_BATCH)
    ]

    batch_ids = []

    # Submit each chunk as a separate batch
    for i, chunk in enumerate(chunks, 1):
        print(f"\n--- Batch {i}/{num_batches} ({len(chunk):,} files) ---")

        # Create batch file for this chunk
        jsonl_path = create_batch_requests_file(chunk, model, use_images)

        # Submit batch
        try:
            batch_id = submit_batch(jsonl_path)
            batch_ids.append(batch_id)
            logging.info(f"Batch {i} submitted: {batch_id}")
        except Exception as e:
            logging.error(f"Failed to submit batch {i}: {e}")
            # Continue with remaining batches
            continue

    print("\n" + "=" * 70)
    print("BATCHES SUBMITTED")
    print("=" * 70)
    print(f"Total batches:   {len(batch_ids)}/{num_batches}")
    print(f"Total files:     {len(to_process):,}")
    print()
    print("Batch IDs:")
    for bid in batch_ids:
        print(f"  - {bid}")
    print()
    print("To check status:")
    print("  uv run python -m app.transcribe_openai --batch-list")
    print()
    print("To download results for each batch:")
    for bid in batch_ids:
        print(f"  uv run python -m app.transcribe_openai --batch-download {bid} --model {model}")
    print("=" * 70)

    # Save all batch IDs to a file for easy reference
    batch_session = {
        "batch_ids": batch_ids,
        "model": model,
        "total_files": len(to_process),
        "created_at": datetime.now().isoformat(),
    }
    session_path = BATCH_DIR / f"batch_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    session_path.write_text(json.dumps(batch_session, indent=2))
    print(f"\nSession saved: {session_path.name}")

    # Skip waiting in auto mode
    if skip_confirm:
        print("\nBatches submitted. Use --batch-status to check progress.")
        return

    # Ask if user wants to wait for all batches
    response = input(f"\nWait for all {len(batch_ids)} batches to complete? [y/n]: ").strip().lower()
    if response in ['y', 'yes']:
        total_success = 0
        total_failed = 0

        for i, batch_id in enumerate(batch_ids, 1):
            print(f"\n--- Waiting for batch {i}/{len(batch_ids)}: {batch_id} ---")
            status = wait_for_batch(batch_id)

            if status['status'] == 'completed':
                print(f"Downloading results for batch {i}...")
                results = download_batch_results(batch_id, output_dir)
                total_success += results['success']
                total_failed += results['failed']
            else:
                logging.error(f"Batch {i} failed with status: {status['status']}")

        print("\n" + "=" * 70)
        print("ALL BATCHES COMPLETE")
        print("=" * 70)
        print(f"Total successful: {total_success:,}")
        print(f"Total failed:     {total_failed:,}")
        print("=" * 70)

        cost_tracker.print_summary(model)
        print(f"\n50% batch discount: ${cost_tracker.get_cost(model) * 0.5:.2f}")


def list_batches():
    """List all batch jobs."""
    batches = client.batches.list(limit=20)

    print("\n" + "=" * 70)
    print("RECENT BATCH JOBS")
    print("=" * 70)
    print(f"{'ID':<30} {'Status':<12} {'Completed':<10} {'Failed':<8} {'Created'}")
    print("-" * 70)

    for batch in batches.data:
        completed = batch.request_counts.completed if batch.request_counts else 0
        failed = batch.request_counts.failed if batch.request_counts else 0
        created = datetime.fromtimestamp(batch.created_at).strftime("%Y-%m-%d %H:%M")
        print(f"{batch.id:<30} {batch.status:<12} {completed:<10} {failed:<8} {created}")

    print("=" * 70)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe documents using OpenAI API (gpt-4.1-nano)"
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
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Parallel workers (default: 5)"
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        help="Maximum cost limit in dollars"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--use-images",
        action="store_true",
        help="Use images instead of PDFs (first page only)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show status of all model output directories"
    )

    # Batch API arguments
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use Batch API for 50% cost savings (results in 2-24 hours)"
    )
    parser.add_argument(
        "--batch-status",
        type=str,
        metavar="BATCH_ID",
        help="Check status of a batch job"
    )
    parser.add_argument(
        "--batch-download",
        type=str,
        metavar="BATCH_ID",
        help="Download results from a completed batch job"
    )
    parser.add_argument(
        "--batch-list",
        action="store_true",
        help="List recent batch jobs"
    )

    args = parser.parse_args()

    # Handle status command
    if args.status:
        print("\n" + "=" * 70)
        print("MODEL OUTPUT STATUS")
        print("=" * 70)

        # Count total PDFs
        pdf_dir = DATA_DIR / "original_pdfs"
        total_pdfs = len(list(pdf_dir.glob("*.pdf")))
        print(f"Total source PDFs: {total_pdfs:,}")
        print()

        # List model outputs
        outputs = list_model_outputs()
        if outputs:
            print(f"{'Model':<45} {'Files':<10} {'Progress'}")
            print("-" * 70)
            for model_name, count in sorted(outputs.items()):
                pct = (count / total_pdfs * 100) if total_pdfs > 0 else 0
                bar_len = int(pct / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                print(f"{model_name:<45} {count:<10} {bar} {pct:.1f}%")
        else:
            print("No model outputs found yet.")

        print("=" * 70)
        exit(0)

    # Handle batch commands
    if args.batch_list:
        list_batches()
        exit(0)

    if args.batch_status:
        status = check_batch_status(args.batch_status)
        print("\n" + "=" * 70)
        print(f"BATCH STATUS: {args.batch_status}")
        print("=" * 70)
        print(f"Status:      {status['status']}")
        print(f"Total:       {status['request_counts']['total']}")
        print(f"Completed:   {status['request_counts']['completed']}")
        print(f"Failed:      {status['request_counts']['failed']}")
        if status['output_file_id']:
            print(f"Output file: {status['output_file_id']}")
        print("=" * 70)
        exit(0)

    if args.batch_download:
        output_dir = get_model_output_dir(args.model)
        results = download_batch_results(args.batch_download, output_dir)
        print("\n" + "=" * 70)
        print("DOWNLOAD COMPLETE")
        print("=" * 70)
        print(f"✓ Successful: {results['success']}")
        print(f"✗ Failed:     {results['failed']}")
        print(f"Output dir:   {output_dir}")
        print("=" * 70)
        cost_tracker.print_summary(args.model)
        print(f"\n💰 With 50% batch discount: ${cost_tracker.get_cost(args.model) * 0.5:.2f}")
        exit(0)

    resume = not args.no_resume

    # Use batch API or regular processing
    if args.batch:
        run_batch_transcription(
            max_files=args.max_files,
            model=args.model,
            use_images=args.use_images,
            resume=resume,
            skip_confirm=args.yes,
        )
    else:
        process_documents(
            max_files=args.max_files,
            resume=resume,
            max_workers=args.max_workers,
            model=args.model,
            skip_confirm=args.yes,
            use_images=args.use_images,
            max_cost=args.max_cost,
        )
