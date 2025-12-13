"""
Batch processor for full pass document transcription.

Handles batch processing with graceful shutdown, progress tracking, and resume capability.
"""

import logging
import signal
import sys
import time
from pathlib import Path
from typing import List, Callable, Optional, Dict, Any
from datetime import datetime

from app.state_manager import StateManager, ProcessingState


class GracefulShutdown:
    """Handles graceful shutdown on interrupt signals."""

    def __init__(self, state_manager: StateManager):
        """
        Initialize graceful shutdown handler.

        Args:
            state_manager: StateManager instance for saving state on shutdown
        """
        self.state_manager = state_manager
        self.shutdown_requested = False
        self.logger = logging.getLogger(__name__)

        # Register signal handlers
        signal.signal(signal.SIGINT, self._request_shutdown)
        signal.signal(signal.SIGTERM, self._request_shutdown)

    def _request_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        if not self.shutdown_requested:
            self.logger.info("\n⚠️  Shutdown requested. Finishing current batch...")
            print("\n⚠️  Shutdown requested. Finishing current batch...")
            self.shutdown_requested = True
        else:
            self.logger.warning("Shutdown already requested. Please wait...")
            print("Shutdown already requested. Please wait...")

    def should_continue(self) -> bool:
        """
        Check if processing should continue.

        Returns:
            False if shutdown was requested, True otherwise
        """
        return not self.shutdown_requested

    def finalize(self):
        """Finalize shutdown by saving state."""
        self.logger.info("💾 Saving progress...")
        print("💾 Saving progress...")
        self.state_manager.save()
        print("✅ State saved. Run with --resume to continue.")
        self.logger.info("State saved successfully")


class BatchProcessor:
    """Processes documents in batches with resume capability."""

    def __init__(
        self,
        state_manager: StateManager,
        process_func: Callable[[Path], Dict[str, Any]],
        checkpoint_interval: int = 100
    ):
        """
        Initialize BatchProcessor.

        Args:
            state_manager: StateManager instance for state persistence
            process_func: Function to process a single document.
                         Should return dict with keys: success, cost, confidence, error
            checkpoint_interval: Create checkpoint every N documents
        """
        self.state_manager = state_manager
        self.process_func = process_func
        self.checkpoint_interval = checkpoint_interval
        self.logger = logging.getLogger(__name__)
        self.shutdown_handler = GracefulShutdown(state_manager)

        # Metrics tracking
        self.confidence_scores = []

    def process_batch(
        self,
        documents: List[Path],
        batch_num: int,
        total_batches: int,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Process a batch of documents.

        Args:
            documents: List of document paths to process
            batch_num: Current batch number (1-indexed)
            total_batches: Total number of batches
            show_progress: Whether to show progress output

        Returns:
            Dict with batch results: {
                "processed": int,
                "successful": int,
                "failed": int,
                "skipped": int,
                "total_cost": float,
                "completed": bool  # True if batch finished, False if interrupted
            }
        """
        batch_results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_cost": 0.0,
            "completed": False
        }

        batch_start_time = time.time()

        if show_progress:
            print(f"\n{'='*60}")
            print(f"Batch {batch_num}/{total_batches} - Processing {len(documents)} documents")
            print(f"{'='*60}\n")

        for idx, doc_path in enumerate(documents, 1):
            # Check for shutdown request
            if not self.shutdown_handler.should_continue():
                self.logger.info(f"Shutdown requested at document {idx}/{len(documents)}")
                break

            # Show progress
            if show_progress:
                print(f"[{idx}/{len(documents)}] Processing: {doc_path.name}...", end=" ")

            try:
                # Process document
                result = self.process_func(doc_path)

                # Update batch results
                batch_results["processed"] += 1

                if result.get("success", False):
                    batch_results["successful"] += 1

                    # Track confidence
                    if "confidence" in result and result["confidence"] is not None:
                        self.confidence_scores.append(result["confidence"])

                        # Check for low confidence
                        if result["confidence"] < 0.75:
                            self.state_manager.update(
                                low_confidence_doc={
                                    "document": doc_path.name,
                                    "confidence": result["confidence"]
                                }
                            )

                    if show_progress:
                        conf_str = f"(conf: {result.get('confidence', 0):.2f})" if result.get('confidence') else ""
                        print(f"✅ {conf_str}")

                else:
                    batch_results["failed"] += 1
                    error = result.get("error", "Unknown error")
                    self.logger.warning(f"Failed to process {doc_path.name}: {error}")
                    self.state_manager.update(failed_doc=doc_path.name)

                    if show_progress:
                        print(f"❌ {error}")

                # Track cost
                if "cost" in result:
                    batch_results["total_cost"] += result["cost"]

                # Update state
                self.state_manager.update(
                    processed=1,
                    successful=1 if result.get("success") else 0,
                    failed=1 if not result.get("success") else 0,
                    cost=result.get("cost", 0),
                    confidence_scores=self.confidence_scores
                )

                # Create checkpoint at intervals
                if batch_results["processed"] % self.checkpoint_interval == 0:
                    self.state_manager.create_checkpoint()
                    if show_progress:
                        print(f"\n💾 Checkpoint created at {batch_results['processed']} documents\n")

            except Exception as e:
                batch_results["failed"] += 1
                self.logger.error(f"Exception processing {doc_path.name}: {e}", exc_info=True)
                self.state_manager.update(
                    processed=1,
                    failed=1,
                    failed_doc=doc_path.name
                )

                if show_progress:
                    print(f"❌ Exception: {str(e)}")

        # Calculate batch stats
        batch_elapsed = time.time() - batch_start_time
        batch_results["completed"] = self.shutdown_handler.should_continue()

        if show_progress:
            self._print_batch_summary(batch_results, batch_elapsed, batch_num)

        return batch_results

    def _print_batch_summary(
        self,
        batch_results: Dict[str, Any],
        elapsed_seconds: float,
        batch_num: int
    ):
        """Print summary of batch processing results."""
        processed = batch_results["processed"]
        successful = batch_results["successful"]
        failed = batch_results["failed"]
        cost = batch_results["total_cost"]

        success_rate = (successful / processed * 100) if processed > 0 else 0
        docs_per_min = (processed / elapsed_seconds * 60) if elapsed_seconds > 0 else 0

        print(f"\n{'='*60}")
        print(f"Batch {batch_num} Complete")
        print(f"{'='*60}")
        print(f"Processed:    {processed}")
        print(f"Successful:   {successful} ({success_rate:.1f}%)")
        print(f"Failed:       {failed}")
        print(f"Cost:         ${cost:.4f}")
        print(f"Time:         {elapsed_seconds:.1f}s ({docs_per_min:.1f} docs/min)")
        print(f"{'='*60}\n")

    def get_documents_to_process(
        self,
        images_dir: Path,
        output_dir: Path,
        skip_existing: bool = True
    ) -> List[Path]:
        """
        Get list of documents to process, optionally skipping existing outputs.

        Args:
            images_dir: Directory containing source images
            output_dir: Directory containing output JSON files
            skip_existing: If True, skip documents with existing JSON outputs

        Returns:
            List of document paths to process
        """
        # Get all image files
        all_images = sorted(images_dir.glob("*.jpg"))

        if not skip_existing:
            return all_images

        # Filter out already processed documents
        to_process = []
        for img_path in all_images:
            json_path = output_dir / f"{img_path.stem}.json"
            if not json_path.exists():
                to_process.append(img_path)

        self.logger.info(f"Found {len(all_images)} total images, {len(to_process)} to process")
        return to_process

    def estimate_batch_cost(
        self,
        num_documents: int,
        cost_per_doc: float = 0.0015
    ) -> float:
        """
        Estimate cost for processing a batch.

        Args:
            num_documents: Number of documents in batch
            cost_per_doc: Estimated cost per document

        Returns:
            Estimated total cost
        """
        return num_documents * cost_per_doc

    def estimate_batch_time(
        self,
        num_documents: int,
        rate_limit: float = 2.0
    ) -> int:
        """
        Estimate time to process a batch in minutes.

        Args:
            num_documents: Number of documents in batch
            rate_limit: Requests per second

        Returns:
            Estimated time in minutes
        """
        # Account for rate limiting and overhead
        docs_per_minute = rate_limit * 60 * 0.8  # 80% efficiency
        minutes = num_documents / docs_per_minute
        return int(minutes) + 1

    def create_batches(
        self,
        documents: List[Path],
        batch_size: int
    ) -> List[List[Path]]:
        """
        Split documents into batches.

        Args:
            documents: List of document paths
            batch_size: Size of each batch

        Returns:
            List of batches (each batch is a list of paths)
        """
        batches = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batches.append(batch)

        self.logger.info(f"Created {len(batches)} batches of size {batch_size}")
        return batches

    def show_batch_estimate(
        self,
        batch_num: int,
        total_batches: int,
        batch_size: int,
        cost_per_doc: float = 0.0015,
        rate_limit: float = 2.0
    ):
        """
        Show estimate for upcoming batch.

        Args:
            batch_num: Current batch number (1-indexed)
            total_batches: Total number of batches
            batch_size: Number of documents in batch
            cost_per_doc: Estimated cost per document
            rate_limit: Requests per second
        """
        estimated_cost = self.estimate_batch_cost(batch_size, cost_per_doc)
        estimated_time = self.estimate_batch_time(batch_size, rate_limit)

        print(f"\n{'─'*60}")
        print(f"Batch {batch_num}/{total_batches} Estimate")
        print(f"{'─'*60}")
        print(f"Documents:      {batch_size}")
        print(f"Estimated cost: ${estimated_cost:.4f}")
        print(f"Estimated time: ~{estimated_time} minutes")
        print(f"{'─'*60}\n")

    def confirm_batch(self) -> bool:
        """
        Ask user to confirm batch processing.

        Returns:
            True if user confirms, False otherwise
        """
        response = input("Continue with this batch? (y/n): ").strip().lower()
        return response == 'y'

    def finalize(self):
        """Finalize processing and save state."""
        self.shutdown_handler.finalize()
