"""
Batch transcription CLI using OpenAI Batch API.

This module provides CLI commands for batch processing of PDF documents
with 50% cost reduction compared to synchronous processing.

Usage:
    # Prepare and submit a batch
    uv run python -m app.batch prepare -n 1000
    uv run python -m app.batch submit <file_id>

    # Monitor and retrieve
    uv run python -m app.batch status <batch_id>
    uv run python -m app.batch retrieve <batch_id>

    # All-in-one workflow
    uv run python -m app.batch run -n 1000 --poll

    # List jobs
    uv run python -m app.batch jobs
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.config import DATA_DIR, ROOT_DIR
from app.utils.batch_processor import BatchProcessor

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_prepare(args: argparse.Namespace) -> int:
    """Prepare a batch file from PDFs."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    # Get pending files
    pending = processor.get_pending_files()
    total_pending = len(pending)

    if total_pending == 0:
        print("No pending documents to process.")
        return 0

    # Limit if specified
    files_to_process = pending
    if args.limit:
        files_to_process = pending[: args.limit]

    print()
    print("=" * 50)
    print("Batch Preparation")
    print("=" * 50)
    print(f"Model:              {model}")
    print(f"Total pending:      {total_pending:,}")
    print(f"Files to process:   {len(files_to_process):,}")
    print()

    # Estimate cost (batch = 50% of standard)
    # Standard: $0.0275/doc, Batch: ~$0.0138/doc
    estimated_cost = len(files_to_process) * 0.0138
    print(f"Estimated cost:     ${estimated_cost:.2f} (50% batch discount)")
    print()

    if args.dry_run:
        print("[DRY RUN] Would create batch file with above documents")
        return 0

    # Confirm
    if not args.yes:
        try:
            response = input("Proceed with batch preparation? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("Cancelled.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0

    # Create batch file
    print()
    batch_file = processor.prepare_batch(files_to_process, batch_name=args.name)

    print()
    print("=" * 50)
    print("Next Steps")
    print("=" * 50)
    print(f"1. Upload and submit batch:")
    print(f"   uv run python -m app.batch submit-file {batch_file}")
    print()
    print(f"Or upload manually:")
    print(f"   file_id = processor.upload_batch_file('{batch_file}')")
    print(f"   uv run python -m app.batch submit <file_id>")
    print()

    return 0


def cmd_submit_file(args: argparse.Namespace) -> int:
    """Upload batch file and submit job."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    batch_file = Path(args.batch_file)
    if not batch_file.exists():
        print(f"Error: Batch file not found: {batch_file}")
        return 1

    print(f"Uploading batch file: {batch_file.name}")
    file_id = processor.upload_batch_file(batch_file)

    print(f"Submitting batch job...")
    batch_job = processor.submit_batch(file_id)

    print()
    print("=" * 50)
    print("Batch Job Created")
    print("=" * 50)
    print(f"Batch ID:       {batch_job.id}")
    print(f"Status:         {batch_job.status}")
    print(f"Input File:     {batch_job.input_file_id}")
    print()
    print("Monitor with:")
    print(f"   uv run python -m app.batch status {batch_job.id}")
    print()
    print("Or poll until complete:")
    print(f"   uv run python -m app.batch poll {batch_job.id}")
    print()

    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    """Submit a batch job from uploaded file ID."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    print(f"Submitting batch job for file: {args.file_id}")
    batch_job = processor.submit_batch(args.file_id)

    print()
    print("=" * 50)
    print("Batch Job Created")
    print("=" * 50)
    print(f"Batch ID:       {batch_job.id}")
    print(f"Status:         {batch_job.status}")
    print()

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Check status of a batch job."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    batch_job = processor.get_batch_status(args.batch_id)

    print()
    print("=" * 50)
    print("Batch Job Status")
    print("=" * 50)
    print(f"Batch ID:       {batch_job.id}")
    print(f"Status:         {batch_job.status}")
    print(f"Input File:     {batch_job.input_file_id}")
    print(f"Output File:    {batch_job.output_file_id or 'N/A'}")
    print(f"Created:        {batch_job.created_at}")
    print(f"Completed:      {batch_job.completed_at or 'N/A'}")

    if batch_job.request_counts:
        counts = batch_job.request_counts
        total = counts.get("total", 0)
        completed = counts.get("completed", 0)
        failed = counts.get("failed", 0)
        pct = (completed / total * 100) if total > 0 else 0
        print()
        print(f"Progress:       {completed}/{total} ({pct:.1f}%)")
        print(f"Failed:         {failed}")

    if batch_job.errors:
        print()
        print("Errors:")
        for err in batch_job.errors[:5]:
            print(f"  - {err.get('code')}: {err.get('message')}")

    print()
    return 0


def cmd_poll(args: argparse.Namespace) -> int:
    """Poll a batch job until completion."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    print(f"Polling batch {args.batch_id} (interval: {args.interval}s)...")
    print("Press Ctrl+C to stop polling (job will continue running)")
    print()

    try:
        batch_job = processor.poll_until_complete(
            args.batch_id,
            interval=args.interval,
        )

        print()
        print("=" * 50)
        print("Batch Complete")
        print("=" * 50)
        print(f"Status:         {batch_job.status}")

        if batch_job.request_counts:
            counts = batch_job.request_counts
            print(f"Total:          {counts.get('total', 0)}")
            print(f"Completed:      {counts.get('completed', 0)}")
            print(f"Failed:         {counts.get('failed', 0)}")

        if batch_job.status == "completed":
            print()
            print("Retrieve results with:")
            print(f"   uv run python -m app.batch retrieve {batch_job.id}")

        return 0

    except KeyboardInterrupt:
        print("\n\nPolling stopped. Job continues running.")
        print(f"Resume with: uv run python -m app.batch poll {args.batch_id}")
        return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    """Retrieve and process results from a completed batch."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    # Check status first
    batch_job = processor.get_batch_status(args.batch_id)
    if batch_job.status != "completed":
        print(f"Error: Batch is not completed (status: {batch_job.status})")
        if batch_job.status in ("validating", "in_progress", "finalizing"):
            print(f"Wait for completion with: uv run python -m app.batch poll {args.batch_id}")
        return 1

    print(f"Retrieving results for batch: {args.batch_id}")
    print()

    counts = processor.process_all_results(args.batch_id)

    print()
    print("=" * 50)
    print("Results Processed")
    print("=" * 50)
    print(f"Success:        {counts['success']}")
    print(f"Failed:         {counts['failed']}")
    print(f"Skipped:        {counts['skipped']}")
    print()

    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    """Cancel a batch job."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    if not args.yes:
        try:
            response = input(f"Cancel batch {args.batch_id}? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("Cancelled.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0

    batch_job = processor.cancel_batch(args.batch_id)
    print(f"Batch {batch_job.id} status: {batch_job.status}")

    return 0


def cmd_jobs(args: argparse.Namespace) -> int:
    """List all tracked batch jobs."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    jobs = processor.list_jobs()

    if not jobs:
        print("No batch jobs found.")
        return 0

    print()
    print("=" * 80)
    print("Batch Jobs")
    print("=" * 80)
    print(f"{'ID':<30} {'Status':<12} {'Progress':<15} {'Created':<20}")
    print("-" * 80)

    for job in jobs:
        job_id = job["id"][:28] + ".." if len(job["id"]) > 30 else job["id"]
        status = job["status"]
        created = job.get("created_at", "")[:16] if job.get("created_at") else "N/A"

        counts = job.get("request_counts", {})
        if counts:
            total = counts.get("total", 0)
            completed = counts.get("completed", 0)
            progress = f"{completed}/{total}"
        else:
            progress = "N/A"

        print(f"{job_id:<30} {status:<12} {progress:<15} {created:<20}")

    print()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """All-in-one: prepare, submit, poll, retrieve."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    # Get pending files
    pending = processor.get_pending_files()
    total_pending = len(pending)

    if total_pending == 0:
        print("No pending documents to process.")
        return 0

    # Limit if specified
    files_to_process = pending
    if args.limit:
        files_to_process = pending[: args.limit]

    print()
    print("=" * 50)
    print("Batch Transcription")
    print("=" * 50)
    print(f"Model:              {model}")
    print(f"Total pending:      {total_pending:,}")
    print(f"Files to process:   {len(files_to_process):,}")

    estimated_cost = len(files_to_process) * 0.0138
    print(f"Estimated cost:     ${estimated_cost:.2f} (50% batch discount)")
    print()

    if args.dry_run:
        print("[DRY RUN] Would process above documents")
        return 0

    # Confirm
    if not args.yes:
        try:
            response = input("Proceed? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("Cancelled.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0

    # Phase 1: Prepare
    print()
    print("-" * 50)
    print("Phase 1: Preparing batch file...")
    print("-" * 50)
    batch_file = processor.prepare_batch(files_to_process)

    # Phase 2: Upload and submit
    print()
    print("-" * 50)
    print("Phase 2: Uploading and submitting...")
    print("-" * 50)
    file_id = processor.upload_batch_file(batch_file)
    batch_job = processor.submit_batch(file_id)

    # Phase 3: Poll (if requested)
    if args.poll:
        print()
        print("-" * 50)
        print("Phase 3: Polling for completion...")
        print("-" * 50)
        print("Press Ctrl+C to stop polling (job will continue)")
        print()

        try:
            batch_job = processor.poll_until_complete(
                batch_job.id,
                interval=args.interval,
            )
        except KeyboardInterrupt:
            print("\n\nPolling stopped. Job continues running.")
            print(f"Resume with: uv run python -m app.batch poll {batch_job.id}")
            return 0

        # Phase 4: Retrieve
        if batch_job.status == "completed":
            print()
            print("-" * 50)
            print("Phase 4: Retrieving results...")
            print("-" * 50)
            counts = processor.process_all_results(batch_job.id)

            print()
            print("=" * 50)
            print("Complete")
            print("=" * 50)
            print(f"Success:        {counts['success']}")
            print(f"Failed:         {counts['failed']}")
            print(f"Skipped:        {counts['skipped']}")
        else:
            print(f"\nBatch finished with status: {batch_job.status}")

    else:
        print()
        print("=" * 50)
        print("Batch Submitted")
        print("=" * 50)
        print(f"Batch ID:       {batch_job.id}")
        print()
        print("Poll for completion:")
        print(f"   uv run python -m app.batch poll {batch_job.id}")
        print()
        print("Or retrieve when complete:")
        print(f"   uv run python -m app.batch retrieve {batch_job.id}")

    return 0


def cmd_pending(args: argparse.Namespace) -> int:
    """Show count of pending documents."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    processor = BatchProcessor(model=model)

    pending = processor.get_pending_files()

    print()
    print(f"Model:          {model}")
    print(f"Pending docs:   {len(pending):,}")
    print()

    if pending and args.sample:
        print(f"Sample (first {args.sample}):")
        for p in pending[: args.sample]:
            print(f"  - {p.name}")
        print()

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Batch transcription using OpenAI Batch API (50% cost savings)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  prepare       Create JSONL batch file from pending PDFs
  submit-file   Upload batch file and submit job
  submit        Submit job from already-uploaded file ID
  status        Check batch job status
  poll          Poll until batch completes
  retrieve      Download and process results
  cancel        Cancel a batch job
  jobs          List all tracked batch jobs
  run           All-in-one: prepare → submit → poll → retrieve
  pending       Show count of pending documents

Examples:
  # Quick start (all-in-one)
  %(prog)s run -n 100 --poll --yes

  # Step by step
  %(prog)s prepare -n 1000
  %(prog)s submit-file batches/batch_xxx.jsonl
  %(prog)s poll batch_abc123
  %(prog)s retrieve batch_abc123

Cost savings: Batch API is 50%% cheaper than synchronous processing.
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # prepare
    p_prepare = subparsers.add_parser("prepare", help="Create batch file from PDFs")
    p_prepare.add_argument("-n", "--limit", type=int, help="Max documents to include")
    p_prepare.add_argument("--name", help="Batch name (default: auto-generated)")
    p_prepare.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    p_prepare.add_argument("--dry-run", action="store_true", help="Show what would be done")

    # submit-file
    p_submit_file = subparsers.add_parser("submit-file", help="Upload and submit batch file")
    p_submit_file.add_argument("batch_file", help="Path to JSONL batch file")

    # submit
    p_submit = subparsers.add_parser("submit", help="Submit from uploaded file ID")
    p_submit.add_argument("file_id", help="OpenAI file ID")

    # status
    p_status = subparsers.add_parser("status", help="Check batch status")
    p_status.add_argument("batch_id", help="Batch job ID")

    # poll
    p_poll = subparsers.add_parser("poll", help="Poll until complete")
    p_poll.add_argument("batch_id", help="Batch job ID")
    p_poll.add_argument("--interval", type=int, default=60, help="Poll interval (seconds)")

    # retrieve
    p_retrieve = subparsers.add_parser("retrieve", help="Retrieve results")
    p_retrieve.add_argument("batch_id", help="Batch job ID")

    # cancel
    p_cancel = subparsers.add_parser("cancel", help="Cancel batch job")
    p_cancel.add_argument("batch_id", help="Batch job ID")
    p_cancel.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # jobs
    p_jobs = subparsers.add_parser("jobs", help="List batch jobs")

    # run (all-in-one)
    p_run = subparsers.add_parser("run", help="All-in-one workflow")
    p_run.add_argument("-n", "--limit", type=int, help="Max documents to process")
    p_run.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    p_run.add_argument("--poll", action="store_true", help="Poll for completion")
    p_run.add_argument("--interval", type=int, default=60, help="Poll interval (seconds)")
    p_run.add_argument("--dry-run", action="store_true", help="Show what would be done")

    # pending
    p_pending = subparsers.add_parser("pending", help="Show pending documents")
    p_pending.add_argument("--sample", type=int, default=5, help="Show N sample files")

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    if not args.command:
        print("Error: No command specified. Use --help for usage.")
        return 1

    commands = {
        "prepare": cmd_prepare,
        "submit-file": cmd_submit_file,
        "submit": cmd_submit,
        "status": cmd_status,
        "poll": cmd_poll,
        "retrieve": cmd_retrieve,
        "cancel": cmd_cancel,
        "jobs": cmd_jobs,
        "run": cmd_run,
        "pending": cmd_pending,
    }

    cmd_func = commands.get(args.command)
    if not cmd_func:
        print(f"Error: Unknown command: {args.command}")
        return 1

    return cmd_func(args)


if __name__ == "__main__":
    sys.exit(main())
