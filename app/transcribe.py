import os
import base64
import argparse
import json
import logging
import time
import random
import re
import threading
from collections import deque
from dotenv import load_dotenv
from tqdm import tqdm
from openai import OpenAI
import openai
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from jsonschema import Draft7Validator, ValidationError

from app.config import ROOT_DIR, DATA_DIR

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

# Load the transcription prompt from the markdown file in `app/prompts`.
prompt_path = Path(__file__).parent / "prompts" / "metadata_prompt.md"
try:
    prompt = prompt_path.read_text(encoding="utf-8")
except Exception as e:
    logging.error(f"Failed to read prompt file {prompt_path}: {e}")
    raise RuntimeError(f"Prompt file missing or unreadable: {prompt_path}: {e}")

# ---------------------------------------------------------------------------
# Rate Limiting Configuration
# ---------------------------------------------------------------------------
# Adjust these based on your OpenAI API tier limits
MAX_TPM = int(os.getenv("MAX_TOKENS_PER_MINUTE", "150000"))  # Tokens per minute
EST_TOKENS_PER_DOC = 3000  # Estimated tokens per API call

# Global rate limiting state
token_usage = deque()  # (timestamp, tokens) for last 60 seconds
token_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Cost Tracking
# ---------------------------------------------------------------------------
class CostTracker:
    """Thread-safe cost tracker for API usage."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.lock = threading.Lock()

    def add_usage(self, response):
        """Track token usage from API response."""
        with self.lock:
            if hasattr(response, 'usage'):
                usage = response.usage
                self.total_input_tokens += usage.prompt_tokens
                self.total_output_tokens += usage.completion_tokens

    def get_cost(self, model="gpt-4o-mini"):
        """Calculate cost based on model pricing."""
        pricing = {
            "gpt-4o-mini": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
            "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
        }

        rates = pricing.get(model, pricing["gpt-4o-mini"])
        cost = (self.total_input_tokens * rates["input"] +
                self.total_output_tokens * rates["output"])

        return cost

    def print_summary(self, model="gpt-4o-mini"):
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


def wait_for_token_budget(estimated_tokens: int):
    """
    Wait until we have token budget available within the rate limit window.

    This implements a sliding window rate limiter that tracks token usage
    over the last 60 seconds and blocks if we would exceed the limit.
    """
    while True:
        with token_lock:
            now = time.time()

            # Remove entries older than 60 seconds
            while token_usage and now - token_usage[0][0] > 60:
                token_usage.popleft()

            # Calculate current usage in the last 60 seconds
            used = sum(tokens for _, tokens in token_usage)

            # Check if we can proceed without exceeding the limit
            if used + estimated_tokens < MAX_TPM:
                token_usage.append((now, estimated_tokens))
                return

        # Wait and retry
        time.sleep(0.5)


def get_optimal_workers() -> int:
    """
    Determine optimal worker count based on rate limits.

    Returns a conservative default based on MAX_TPM to avoid overwhelming the API.
    Users can override with --max-workers flag.
    """
    # Calculate based on TPM and estimated tokens per document
    # With 150k TPM and 3k tokens/doc, theoretical max is 50 docs/min = ~0.8 docs/sec
    # With some safety margin for parallel processing
    optimal = min(int(MAX_TPM / EST_TOKENS_PER_DOC / 10), 32)

    # Never go below 2 workers
    return max(optimal, 2)


def validate_response(data: dict) -> tuple[bool, list[str]]:
    """
    Validate that the API response has the required structure.

    Returns:
        (is_valid, error_messages)
    """
    errors = []

    # Check top-level structure
    if not isinstance(data, dict):
        return False, ["Response is not a dictionary"]

    # Check required top-level fields
    required_fields = ["metadata", "original_text", "reviewed_text"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    # Check metadata is a dict
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append("metadata is not a dictionary")
        return False, errors

    # Check critical metadata fields exist
    critical_fields = ["document_date", "classification_level", "document_type"]
    for field in critical_fields:
        if field not in metadata:
            errors.append(f"Missing critical metadata field: {field}")

    # Validate text fields are strings
    if not isinstance(data.get("original_text"), str):
        errors.append("original_text is not a string")
    if not isinstance(data.get("reviewed_text"), str):
        errors.append("reviewed_text is not a string")

    if errors:
        return False, errors

    return True, []


# ---------------------------------------------------------------------------
# JSONSchema Validation & Auto-Repair
# ---------------------------------------------------------------------------
FULL_SCHEMA = {
    "type": "object",
    "required": ["metadata", "original_text", "reviewed_text"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": [
                "document_id", "case_number", "document_date",
                "classification_level", "declassification_date",
                "document_type", "author", "recipients",
                "people_mentioned", "country", "city",
                "other_place", "document_title", "document_description",
                "archive_location", "observations", "language",
                "keywords", "page_count", "document_summary"
            ],
            "properties": {
                "document_id": {"type": "string"},
                "case_number": {"type": "string"},
                "document_date": {"type": "string"},
                "classification_level": {"type": "string"},
                "declassification_date": {"type": "string"},
                "document_type": {"type": "string"},
                "author": {"type": "string"},
                "document_title": {"type": "string"},
                "document_description": {"type": "string"},
                "archive_location": {"type": "string"},
                "observations": {"type": "string"},
                "language": {"type": "string"},
                "document_summary": {"type": "string"},
                "recipients": {"type": "array"},
                "people_mentioned": {"type": "array"},
                "country": {"type": "array"},
                "city": {"type": "array"},
                "other_place": {"type": "array"},
                "keywords": {"type": "array"},
                "page_count": {"type": "number"}
            }
        },
        "original_text": {"type": "string"},
        "reviewed_text": {"type": "string"}
    }
}


def auto_repair_response(data: dict) -> dict:
    """
    Automatically fix common AI output issues.

    This function attempts to repair known formatting problems:
    - Reversed dates (DD-MM-YYYY → YYYY-MM-DD)
    - String values where arrays are expected
    - Common classification level variations
    - Missing or null fields

    Returns:
        The repaired data dictionary
    """
    if not isinstance(data, dict):
        return data

    metadata = data.get("metadata", {})

    # Fix reversed dates (DD-MM-YYYY → YYYY-MM-DD)
    for date_field in ["document_date", "declassification_date"]:
        if date_field in metadata:
            date_str = str(metadata[date_field])

            # Pattern: DD-MM-YYYY or DD/MM/YYYY
            if re.match(r"^\d{2}[-/]\d{2}[-/]\d{4}$", date_str):
                parts = re.split(r"[-/]", date_str)
                metadata[date_field] = f"{parts[2]}-{parts[1]}-{parts[0]}"
                logging.debug(f"Auto-fixed date format: {date_str} → {metadata[date_field]}")

    # Convert string arrays to actual arrays
    array_fields = ["recipients", "keywords", "people_mentioned", "country", "city", "other_place"]
    for field in array_fields:
        value = metadata.get(field)
        if isinstance(value, str):
            metadata[field] = [value] if value else []
            logging.debug(f"Auto-converted {field} from string to array")
        elif value is None:
            metadata[field] = []

    # Ensure string fields are strings (not null)
    string_fields = [
        "document_id", "case_number", "document_date",
        "classification_level", "declassification_date",
        "document_type", "author", "document_title",
        "document_description", "archive_location",
        "observations", "language", "document_summary"
    ]
    for field in string_fields:
        if metadata.get(field) is None:
            metadata[field] = ""

    # Normalize classification levels
    if "classification_level" in metadata:
        classification = str(metadata["classification_level"]).upper()

        if "DECLASSIFIED" in classification or "UNCLASS" in classification:
            metadata["classification_level"] = "UNCLASSIFIED"
            logging.debug(f"Normalized classification: {classification} → UNCLASSIFIED")

    # Ensure page_count is a number
    if "page_count" in metadata:
        try:
            metadata["page_count"] = int(metadata["page_count"]) if metadata["page_count"] else 0
        except (ValueError, TypeError):
            metadata["page_count"] = 0

    # Ensure top-level text fields are strings
    for field in ["original_text", "reviewed_text"]:
        if field not in data or data[field] is None:
            data[field] = ""

    return data


def validate_with_schema(data: dict, enable_auto_repair: bool = True) -> tuple[bool, list[str]]:
    """
    Validate response against full JSONSchema.

    Args:
        data: The response data to validate
        enable_auto_repair: If True, attempt to auto-repair before validating

    Returns:
        (is_valid, error_messages)
    """
    # Attempt auto-repair first
    if enable_auto_repair:
        data = auto_repair_response(data)

    # Validate against schema
    validator = Draft7Validator(FULL_SCHEMA)
    errors = list(validator.iter_errors(data))

    if errors:
        error_msgs = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            error_msgs.append(f"{path}: {error.message}")
        return False, error_msgs

    return True, []


def call_api_with_retry(messages, model, max_retries=3):
    """
    Call OpenAI API with exponential backoff retry for transient failures.
    Includes rate limiting to prevent exceeding token quotas.

    Args:
        messages: The messages to send to the API
        model: The model to use
        max_retries: Maximum number of retry attempts

    Returns:
        API response object

    Raises:
        Exception if all retries are exhausted
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Wait for token budget before making the API call
            wait_for_token_budget(EST_TOKENS_PER_DOC)

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )

            # Track token usage for cost calculation
            cost_tracker.add_usage(response)

            return response
        except openai.RateLimitError as e:
            if attempt == max_retries:
                logging.error(f"Rate limit error after {max_retries} attempts: {e}")
                raise

            # Exponential backoff with jitter
            delay = (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logging.warning(f"Rate limit hit, retrying in {delay:.1f}s (attempt {attempt}/{max_retries})")
            time.sleep(delay)

        except openai.APIError as e:
            if attempt == max_retries:
                logging.error(f"API error after {max_retries} attempts: {e}")
                raise

            delay = 2 ** (attempt - 1)
            logging.warning(f"API error, retrying in {delay}s (attempt {attempt}/{max_retries}): {e}")
            time.sleep(delay)

        except openai.APIConnectionError as e:
            if attempt == max_retries:
                logging.error(f"Connection error after {max_retries} attempts: {e}")
                raise

            delay = 2 ** (attempt - 1)
            logging.warning(f"Connection error, retrying in {delay}s (attempt {attempt}/{max_retries})")
            time.sleep(delay)


def transcribe_single_document(
    filename: str,
    document_dir: Path,
    output_dir: Path,
    resume: bool,
    dry_run: bool = False
) -> str:
    """
    Transcribe a single document.

    Returns:
        "success" if successful
        "skipped" if skipped due to resume mode
        "failed" if failed
    """
    file_path = document_dir / filename
    output_filename = output_dir / (os.path.splitext(filename)[0] + ".json")

    # Dry-run mode: simulate processing without API calls
    if dry_run:
        logging.info(f"[DRY RUN] Would process: {filename}")
        time.sleep(0.1)  # Simulate processing time
        return "success"

    # If resume mode is ON, skip if the JSON file already exists
    if resume and output_filename.exists():
        logging.info(f"⊘ {filename} | Skipped (already exists)")
        return "skipped"

    start_time = time.time()

    # Read the PDF file and encode it in base64
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        base64_string = base64.b64encode(data).decode("utf-8")
        file_size_kb = len(data) / 1024
        logging.debug(f"Encoded {filename} ({file_size_kb:.1f} KB) to base64")
    except Exception as e:
        logging.error(f"✗ {filename} | Failed to read file: {e}")
        return "failed"

    # Send the request to the model using retry logic
    try:
        response = call_api_with_retry(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/pdf;base64,{base64_string}"
                            }
                        },
                    ],
                }
            ],
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        )

        api_time = time.time() - start_time
        logging.debug(f"{filename} | API call completed in {api_time:.2f}s")

    except Exception as e:
        logging.error(f"✗ {filename} | API request failed: {e}")
        return "failed"

    # Extract the response content
    response_text = response.choices[0].message.content

    # Clean the response to remove ```json ...``` blocks (if any)
    cleaned_text = (
        response_text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    # Attempt to parse the cleaned text as JSON
    try:
        response_data = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logging.error(f"✗ {filename} | JSON parse error: {e}")
        return "failed"

    # Validate with full schema and auto-repair
    is_valid, errors = validate_with_schema(response_data, enable_auto_repair=True)
    if not is_valid:
        logging.error(f"✗ {filename} | Schema validation failed:")
        for error in errors:
            logging.error(f"    - {error}")
        return "failed"

    # Write the JSON to file
    try:
        with open(output_filename, "w", encoding="utf-8") as out_file:
            json.dump(response_data, out_file, ensure_ascii=False, indent=4)

        output_size_kb = output_filename.stat().st_size / 1024
        total_time = time.time() - start_time

        logging.info(f"✓ {filename} | {output_size_kb:.1f} KB | {total_time:.2f}s")
        return "success"

    except Exception as e:
        logging.error(f"✗ {filename} | Failed to write output: {e}")
        return "failed"


def process_documents_in_directory(max_files=0, resume=False, max_workers=2, dry_run=False):
    """
    Processes PDF documents from DATA_DIR / 'original_pdfs' in parallel threads.

    Args:
        max_files: Number of files to process; 0 means process all.
        resume: If True, skip already transcribed (existing .json).
        max_workers: How many parallel threads to run.
        dry_run: If True, simulate processing without calling API.
    """
    document_dir = DATA_DIR / "original_pdfs"
    output_dir = DATA_DIR / "generated_transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Gather all PDF files, sorted for consistent ordering
    all_documents = sorted(
        f for f in os.listdir(document_dir) if f.lower().endswith(".pdf")
    )

    # If max_files != 0, truncate the list
    if max_files > 0:
        all_documents = all_documents[:max_files]

    if not all_documents:
        logging.warning("No PDF files found to process")
        return

    logging.info(f"Starting batch transcription: {len(all_documents)} files, {max_workers} workers")

    # Track statistics
    results = {
        "success": 0,
        "skipped": 0,
        "failed": 0
    }

    start_time = time.time()

    # Create a ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all jobs
        futures = {
            executor.submit(transcribe_single_document, filename, document_dir, output_dir, resume, dry_run): filename
            for filename in all_documents
        }

        # Process results as they complete
        with tqdm(total=len(futures), desc="Processing documents", unit="doc") as pbar:
            for future in as_completed(futures):
                filename = futures[future]
                try:
                    result = future.result()
                    results[result] += 1
                except Exception as e:
                    logging.error(f"✗ {filename} | Unexpected error: {e}")
                    results["failed"] += 1
                finally:
                    pbar.update(1)

    # Calculate summary statistics
    total_time = time.time() - start_time
    total_files = len(all_documents)

    # Print summary
    print("\n" + "=" * 70)
    print("BATCH TRANSCRIPTION COMPLETE")
    print("=" * 70)
    print(f"Total files:       {total_files}")
    print(f"✓ Successful:      {results['success']:4d} ({results['success']/total_files*100:5.1f}%)")
    print(f"⊘ Skipped:         {results['skipped']:4d} ({results['skipped']/total_files*100:5.1f}%)")
    print(f"✗ Failed:          {results['failed']:4d} ({results['failed']/total_files*100:5.1f}%)")
    print("-" * 70)
    print(f"Total time:        {total_time:.1f}s ({total_time/60:.1f} minutes)")

    if results['success'] > 0:
        avg_time = total_time / results['success']
        print(f"Avg time/doc:      {avg_time:.2f}s")
        print(f"Throughput:        {results['success']/(total_time/3600):.1f} docs/hour")

    print("=" * 70)

    # Print cost summary (if not dry-run)
    if not dry_run and results['success'] > 0:
        cost_tracker.print_summary(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    if results['failed'] > 0:
        print(f"\n⚠️  {results['failed']} files failed. Check logs for details.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process PDF documents and generate structured JSON transcripts."
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Number of files to process; 0 means process all files."
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip any documents that already have a .json transcript."
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=get_optimal_workers(),
        help=f"Number of parallel threads for API calls (default: {get_optimal_workers()} based on rate limits)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate processing without calling the API (for testing)."
    )

    args = parser.parse_args()

    process_documents_in_directory(
        max_files=args.max_files,
        resume=args.resume,
        max_workers=args.max_workers,
        dry_run=args.dry_run
    )
