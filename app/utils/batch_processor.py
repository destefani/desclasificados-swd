"""
Batch processing utilities for OpenAI Batch API.

This module provides functions to prepare, submit, and process batch jobs
for document transcription using OpenAI's Batch API (50% cost reduction).

Usage:
    from app.utils.batch_processor import BatchProcessor

    processor = BatchProcessor(model="gpt-4.1-mini")
    batch_file = processor.prepare_batch(pdf_files[:1000])
    batch_job = processor.submit_batch(batch_file)
    processor.poll_until_complete(batch_job.id)
    results = processor.retrieve_results(batch_job.id)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from openai import OpenAI

from app.config import DATA_DIR, ROOT_DIR

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Load prompt and schema
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "metadata_prompt_v2.md"
SCHEMA_PATH = Path(__file__).parent.parent / "prompts" / "schemas" / "metadata_schema.json"

try:
    PROMPT = PROMPT_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    raise RuntimeError(f"Prompt file not found: {PROMPT_PATH}")

try:
    SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
except FileNotFoundError:
    raise RuntimeError(f"Schema file not found: {SCHEMA_PATH}")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BatchRequest:
    """A single request in a batch job."""

    custom_id: str
    pdf_path: Path
    model: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSONL-ready dictionary."""
        # Read and encode PDF
        with open(self.pdf_path, "rb") as f:
            pdf_data = f.read()
        base64_pdf = base64.b64encode(pdf_data).decode("utf-8")

        # Build message content
        content: list[dict[str, Any]] = [
            {"type": "text", "text": PROMPT},
            {
                "type": "file",
                "file": {
                    "filename": self.pdf_path.name,
                    "file_data": f"data:application/pdf;base64,{base64_pdf}",
                },
            },
        ]

        # Build request body (same format as synchronous API)
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "document_metadata_extraction",
                    "schema": SCHEMA,
                    "strict": True,
                },
            },
        }

        # GPT-5 and o-series models use max_completion_tokens
        if self.model.startswith(("gpt-5", "o1", "o3", "o4")):
            body["max_completion_tokens"] = 32000
        else:
            body["max_tokens"] = 32000
            body["temperature"] = 0

        return {
            "custom_id": self.custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body,
        }


@dataclass
class BatchJob:
    """Represents a batch job."""

    id: str
    status: str
    input_file_id: str
    output_file_id: Optional[str] = None
    error_file_id: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    request_counts: dict[str, int] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, response: Any) -> "BatchJob":
        """Create from OpenAI API response."""
        created_at = None
        if hasattr(response, "created_at") and response.created_at:
            created_at = datetime.fromtimestamp(response.created_at)

        completed_at = None
        if hasattr(response, "completed_at") and response.completed_at:
            completed_at = datetime.fromtimestamp(response.completed_at)

        request_counts = {}
        if hasattr(response, "request_counts") and response.request_counts:
            rc = response.request_counts
            request_counts = {
                "total": getattr(rc, "total", 0),
                "completed": getattr(rc, "completed", 0),
                "failed": getattr(rc, "failed", 0),
            }

        errors = []
        if hasattr(response, "errors") and response.errors:
            errors = [{"code": e.code, "message": e.message} for e in response.errors.data]

        return cls(
            id=response.id,
            status=response.status,
            input_file_id=response.input_file_id,
            output_file_id=getattr(response, "output_file_id", None),
            error_file_id=getattr(response, "error_file_id", None),
            created_at=created_at,
            completed_at=completed_at,
            request_counts=request_counts,
            errors=errors,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "status": self.status,
            "input_file_id": self.input_file_id,
            "output_file_id": self.output_file_id,
            "error_file_id": self.error_file_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "request_counts": self.request_counts,
            "errors": self.errors,
        }


@dataclass
class BatchResult:
    """A single result from a batch job."""

    custom_id: str
    status_code: int
    response_body: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None

    @property
    def is_success(self) -> bool:
        return self.status_code == 200 and self.error is None

    @property
    def content(self) -> Optional[str]:
        """Extract the response content."""
        if not self.response_body:
            return None
        choices = self.response_body.get("choices", [])
        if not choices:
            return None
        return choices[0].get("message", {}).get("content")

    @property
    def finish_reason(self) -> Optional[str]:
        """Extract finish reason."""
        if not self.response_body:
            return None
        choices = self.response_body.get("choices", [])
        if not choices:
            return None
        return choices[0].get("finish_reason")

    @property
    def usage(self) -> dict[str, int]:
        """Extract token usage."""
        if not self.response_body:
            return {}
        return self.response_body.get("usage", {})


# ---------------------------------------------------------------------------
# Batch Processor
# ---------------------------------------------------------------------------


class BatchProcessor:
    """
    Manages batch transcription jobs using OpenAI's Batch API.

    Example:
        processor = BatchProcessor(model="gpt-4.1-mini")

        # Prepare batch file
        batch_file = processor.prepare_batch(pdf_files)

        # Submit and wait
        batch_job = processor.submit_batch(batch_file)
        processor.poll_until_complete(batch_job.id)

        # Process results
        for result in processor.retrieve_results(batch_job.id):
            if result.is_success:
                processor.save_result(result, output_dir)
    """

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        api_key: Optional[str] = None,
    ) -> None:
        self.model = model
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.output_dir = DATA_DIR / "generated_transcripts" / model
        self.batch_dir = self.output_dir / "batches"
        self.batch_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Phase 1: Prepare Batch
    # -------------------------------------------------------------------------

    def prepare_batch(
        self,
        pdf_files: list[Path],
        batch_name: Optional[str] = None,
    ) -> Path:
        """
        Create a JSONL batch file from PDF files.

        Args:
            pdf_files: List of PDF file paths to process
            batch_name: Optional name for the batch file

        Returns:
            Path to the created JSONL file
        """
        if not pdf_files:
            raise ValueError("No PDF files provided")

        # Generate batch name
        if not batch_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_name = f"batch_{timestamp}_{len(pdf_files)}docs"

        batch_file = self.batch_dir / f"{batch_name}.jsonl"

        logging.info(f"Preparing batch with {len(pdf_files)} documents...")

        with open(batch_file, "w", encoding="utf-8") as f:
            for pdf_path in pdf_files:
                # custom_id is the PDF filename without extension
                custom_id = pdf_path.stem

                request = BatchRequest(
                    custom_id=custom_id,
                    pdf_path=pdf_path,
                    model=self.model,
                )

                f.write(json.dumps(request.to_dict(), ensure_ascii=False) + "\n")

        file_size = batch_file.stat().st_size / (1024 * 1024)  # MB
        logging.info(f"Batch file created: {batch_file} ({file_size:.1f} MB)")

        return batch_file

    def upload_batch_file(self, batch_file: Path) -> str:
        """
        Upload batch file to OpenAI Files API.

        Args:
            batch_file: Path to JSONL batch file

        Returns:
            File ID from OpenAI
        """
        logging.info(f"Uploading batch file: {batch_file.name}...")

        with open(batch_file, "rb") as f:
            file_obj = self.client.files.create(file=f, purpose="batch")

        logging.info(f"Uploaded file ID: {file_obj.id}")
        return file_obj.id

    # -------------------------------------------------------------------------
    # Phase 2: Submit and Monitor
    # -------------------------------------------------------------------------

    def submit_batch(self, file_id: str) -> BatchJob:
        """
        Submit a batch job to OpenAI.

        Args:
            file_id: ID of uploaded batch file

        Returns:
            BatchJob object

        Raises:
            openai.BadRequestError: If billing limit reached or other API error
        """
        logging.info(f"Submitting batch job for file: {file_id}...")

        try:
            response = self.client.batches.create(
                input_file_id=file_id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
            )
        except Exception as e:
            error_msg = str(e)
            if "billing_hard_limit_reached" in error_msg:
                logging.error("OpenAI billing limit reached. Add credits at: https://platform.openai.com/settings/organization/billing")
            raise

        batch_job = BatchJob.from_api_response(response)
        logging.info(f"Batch job created: {batch_job.id} (status: {batch_job.status})")

        # Save job info
        self._save_job_info(batch_job)

        return batch_job

    def get_batch_status(self, batch_id: str) -> BatchJob:
        """Get current status of a batch job."""
        response = self.client.batches.retrieve(batch_id)
        return BatchJob.from_api_response(response)

    def poll_until_complete(
        self,
        batch_id: str,
        interval: int = 60,
        timeout: int = 86400,  # 24 hours
    ) -> BatchJob:
        """
        Poll batch job until completion.

        Args:
            batch_id: Batch job ID
            interval: Seconds between polls
            timeout: Maximum seconds to wait

        Returns:
            Final BatchJob state
        """
        start_time = time.time()
        terminal_states = {"completed", "failed", "expired", "cancelled"}

        logging.info(f"Polling batch {batch_id} (interval: {interval}s)...")

        while True:
            batch_job = self.get_batch_status(batch_id)

            # Log progress
            counts = batch_job.request_counts
            if counts:
                total = counts.get("total", 0)
                completed = counts.get("completed", 0)
                failed = counts.get("failed", 0)
                pct = (completed / total * 100) if total > 0 else 0
                logging.info(
                    f"Status: {batch_job.status} | Progress: {completed}/{total} ({pct:.1f}%) | Failed: {failed}"
                )
            else:
                logging.info(f"Status: {batch_job.status}")

            # Check if done
            if batch_job.status in terminal_states:
                logging.info(f"Batch {batch_id} finished with status: {batch_job.status}")
                self._save_job_info(batch_job)
                return batch_job

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Batch {batch_id} timed out after {timeout}s")

            time.sleep(interval)

    def cancel_batch(self, batch_id: str) -> BatchJob:
        """Cancel a batch job."""
        logging.info(f"Cancelling batch: {batch_id}")
        response = self.client.batches.cancel(batch_id)
        return BatchJob.from_api_response(response)

    # -------------------------------------------------------------------------
    # Phase 3: Retrieve Results
    # -------------------------------------------------------------------------

    def retrieve_results(self, batch_id: str) -> Iterator[BatchResult]:
        """
        Download and parse results from a completed batch.

        Args:
            batch_id: Batch job ID

        Yields:
            BatchResult objects
        """
        batch_job = self.get_batch_status(batch_id)

        if batch_job.status != "completed":
            raise ValueError(f"Batch {batch_id} is not completed (status: {batch_job.status})")

        if not batch_job.output_file_id:
            raise ValueError(f"Batch {batch_id} has no output file")

        # Download results
        logging.info(f"Downloading results from: {batch_job.output_file_id}")
        content = self.client.files.content(batch_job.output_file_id)

        # Save raw results
        results_file = self.batch_dir / f"{batch_id}_results.jsonl"
        with open(results_file, "wb") as f:
            f.write(content.content)

        logging.info(f"Results saved to: {results_file}")

        # Parse and yield results
        with open(results_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                yield BatchResult(
                    custom_id=data["custom_id"],
                    status_code=data["response"]["status_code"],
                    response_body=data["response"].get("body"),
                    error=data.get("error"),
                )

    def process_result(self, result: BatchResult) -> str:
        """
        Process a single batch result and save to JSON.

        Args:
            result: BatchResult to process

        Returns:
            "success", "failed", or "skipped"
        """
        output_file = self.output_dir / f"{result.custom_id}.json"

        # Skip if already exists
        if output_file.exists():
            return "skipped"

        # Check for errors
        if not result.is_success:
            logging.error(f"Failed: {result.custom_id} - {result.error}")
            return "failed"

        # Check finish reason
        if result.finish_reason != "stop":
            logging.error(f"Failed: {result.custom_id} - finish_reason: {result.finish_reason}")
            return "failed"

        # Parse content
        content = result.content
        if not content:
            logging.error(f"Failed: {result.custom_id} - empty content")
            return "failed"

        try:
            # Clean markdown code blocks if present
            cleaned = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logging.error(f"Failed: {result.custom_id} - JSON parse error: {e}")
            return "failed"

        # Validate required fields
        if "metadata" not in data or "original_text" not in data:
            logging.error(f"Failed: {result.custom_id} - missing required fields")
            return "failed"

        # Save result
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        logging.info(f"Saved: {result.custom_id}.json")
        return "success"

    def process_all_results(self, batch_id: str) -> dict[str, int]:
        """
        Process all results from a batch job.

        Returns:
            Dictionary with counts: {"success": N, "failed": M, "skipped": K}
        """
        counts = {"success": 0, "failed": 0, "skipped": 0}

        for result in self.retrieve_results(batch_id):
            status = self.process_result(result)
            counts[status] += 1

        logging.info(
            f"Processed batch {batch_id}: "
            f"{counts['success']} success, {counts['failed']} failed, {counts['skipped']} skipped"
        )

        return counts

    # -------------------------------------------------------------------------
    # Job Management
    # -------------------------------------------------------------------------

    def _save_job_info(self, batch_job: BatchJob) -> None:
        """Save batch job info to tracking file."""
        jobs_file = self.batch_dir / "batch_jobs.json"

        # Load existing jobs
        jobs: list[dict[str, Any]] = []
        if jobs_file.exists():
            with open(jobs_file, "r", encoding="utf-8") as f:
                jobs = json.load(f)

        # Update or add job
        job_dict = batch_job.to_dict()
        existing_idx = next((i for i, j in enumerate(jobs) if j["id"] == batch_job.id), None)

        if existing_idx is not None:
            jobs[existing_idx] = job_dict
        else:
            jobs.append(job_dict)

        # Save
        with open(jobs_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all tracked batch jobs."""
        jobs_file = self.batch_dir / "batch_jobs.json"
        if not jobs_file.exists():
            return []

        with open(jobs_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_pending_files(self, pdfs_dir: Optional[Path] = None) -> list[Path]:
        """
        Get list of PDF files that haven't been processed yet.

        Args:
            pdfs_dir: Directory containing PDFs (default: data/original_pdfs)

        Returns:
            List of PDF paths that need processing
        """
        if pdfs_dir is None:
            pdfs_dir = DATA_DIR / "original_pdfs"

        # Get all PDFs
        all_pdfs = sorted(pdfs_dir.glob("*.pdf"))

        # Get existing outputs
        existing = {f.stem for f in self.output_dir.glob("*.json")}

        # Return pending
        return [p for p in all_pdfs if p.stem not in existing]

    # -------------------------------------------------------------------------
    # Cost Tracking
    # -------------------------------------------------------------------------

    def calculate_batch_cost(self, results: list[BatchResult]) -> dict[str, Any]:
        """
        Calculate cost from batch results.

        Returns:
            Cost summary with tokens and estimated cost
        """
        total_input = 0
        total_output = 0

        for result in results:
            usage = result.usage
            total_input += usage.get("prompt_tokens", 0)
            total_output += usage.get("completion_tokens", 0)

        # Batch API pricing is 50% of standard
        # gpt-4.1-mini: $0.40/1M input, $1.60/1M output (standard)
        # Batch: $0.20/1M input, $0.80/1M output
        input_cost = total_input * 0.20 / 1_000_000
        output_cost = total_output * 0.80 / 1_000_000

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
        }
