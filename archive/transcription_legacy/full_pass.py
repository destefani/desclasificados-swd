"""
Full pass document processing CLI.

Provides batch processing with cost control, time management, and resume capability.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.state_manager import StateManager
from app.batch_processor import BatchProcessor
from app.transcribe import transcribe_single_image


# Batch size presets
BATCH_SIZES = {
    "tiny": 10,
    "small": 100,
    "medium": 500,
    "large": 1000,
}


def setup_logging(level: str = "INFO"):
    """Configure logging for full pass processing."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/full_pass.log'),
            logging.StreamHandler()
        ]
    )


def process_document_wrapper(doc_path: Path) -> Dict[str, Any]:
    """
    Wrapper around transcribe_single_image to match BatchProcessor interface.

    Args:
        doc_path: Path to document image

    Returns:
        Dict with keys: success, cost, confidence, error
    """
    images_dir = Path(__file__).parent.parent / "data" / "images"
    output_dir = Path(__file__).parent.parent / "data" / "generated_transcripts"

    try:
        # Call transcription function
        result = transcribe_single_image(
            image_path=doc_path,
            output_dir=output_dir
        )

        # Extract metrics from result
        return {
            "success": result.get("success", False),
            "cost": result.get("cost", 0.0),
            "confidence": result.get("confidence"),
            "error": result.get("error")
        }

    except Exception as e:
        return {
            "success": False,
            "cost": 0.0,
            "confidence": None,
            "error": str(e)
        }


def show_status(state_manager: StateManager):
    """Display current processing status."""
    state = state_manager.load()

    if state is None:
        print("\n❌ No active processing session found.\n")
        return

    print(state_manager.get_summary())


def show_resume_info(state_manager: StateManager) -> bool:
    """
    Show resume information and ask for confirmation.

    Returns:
        True if user wants to resume, False otherwise
    """
    state = state_manager.load()

    if state is None:
        print("\n❌ No previous session found. Starting fresh.\n")
        return False

    print("\n" + "="*60)
    print("Resume Previous Session")
    print("="*60)
    print(f"Session ID:        {state.session_id}")
    print(f"Prompt Version:    v{state.prompt_version}")
    print(f"Started:           {state.started_at}")
    print(f"Progress:          {state.processed:,} / {state.total_documents:,} ({state.processed/state.total_documents*100:.1f}%)")
    print(f"Success Rate:      {state.successful/state.processed*100 if state.processed > 0 else 0:.1f}%")
    print(f"Cost So Far:       ${state.cost_so_far:.2f}")
    print(f"Remaining:         {state.remaining:,} documents")

    # Estimate remaining
    cost_per_doc = state.cost_so_far / state.processed if state.processed > 0 else 0.0015
    estimated_remaining_cost = state.remaining * cost_per_doc

    print(f"Estimated to complete: ${estimated_remaining_cost:.2f}")
    print(f"Estimated time:        ~{state.estimated_time_remaining_minutes} minutes")
    print("="*60 + "\n")

    response = input("Continue from where you left off? (y/n): ").strip().lower()
    return response == 'y'


def run_full_pass(
    batch_size: int = 100,
    mode: str = "interactive",
    resume: bool = False,
    max_cost: Optional[float] = None,
    max_hours: Optional[float] = None,
    checkpoint_interval: int = 100
):
    """
    Run full pass processing.

    Args:
        batch_size: Number of documents per batch
        mode: Processing mode (interactive or auto)
        resume: Whether to resume from previous session
        max_cost: Maximum total cost (None = unlimited)
        max_hours: Maximum hours to run (None = unlimited)
        checkpoint_interval: Create checkpoint every N documents
    """
    # Setup paths
    images_dir = Path(__file__).parent.parent / "data" / "images"
    output_dir = Path(__file__).parent.parent / "data" / "generated_transcripts"
    output_dir.mkdir(exist_ok=True)

    # Initialize state manager
    state_manager = StateManager()

    # Handle resume
    if resume:
        if not show_resume_info(state_manager):
            print("Exiting.")
            return
        state = state_manager.load()
    else:
        # Check for existing session
        existing_state = state_manager.load()
        if existing_state is not None and existing_state.remaining > 0:
            print(f"\n⚠️  Found existing session with {existing_state.remaining:,} documents remaining.")

            # In auto mode, automatically reset and start fresh
            if mode == "auto":
                print("Auto mode: Resetting state and starting fresh.")
                state_manager.reset()
                state = None
            else:
                # Interactive mode: ask user
                response = input("Resume existing session? (y/n): ").strip().lower()
                if response == 'y':
                    state = existing_state
                    resume = True
                else:
                    # Reset and start fresh
                    state_manager.reset()
                    state = None
        else:
            state = None

    # Initialize batch processor
    processor = BatchProcessor(
        state_manager=state_manager,
        process_func=process_document_wrapper,
        checkpoint_interval=checkpoint_interval
    )

    # Get documents to process
    documents = processor.get_documents_to_process(
        images_dir=images_dir,
        output_dir=output_dir,
        skip_existing=True
    )

    if len(documents) == 0:
        print("\n✅ No documents to process. All done!\n")
        return

    # Create new session if not resuming
    if state is None:
        prompt_version = os.getenv("PROMPT_VERSION", "v2")
        state = state_manager.create_new_session(
            total_documents=len(documents),
            batch_size=batch_size,
            prompt_version=prompt_version
        )

    # Create batches
    batches = processor.create_batches(documents, batch_size)
    total_batches = len(batches)

    print(f"\n{'='*60}")
    print(f"Full Pass Processing - {len(documents):,} documents")
    print(f"{'='*60}")
    print(f"Batch size:        {batch_size}")
    print(f"Total batches:     {total_batches}")
    print(f"Mode:              {mode}")
    print(f"Prompt version:    v{state.prompt_version}")
    if max_cost:
        print(f"Max cost:          ${max_cost:.2f}")
    if max_hours:
        print(f"Max hours:         {max_hours}")
    print(f"{'='*60}\n")

    # Process batches
    for batch_num, batch_docs in enumerate(batches, 1):
        # Show batch estimate
        processor.show_batch_estimate(
            batch_num=batch_num,
            total_batches=total_batches,
            batch_size=len(batch_docs)
        )

        # Check budget constraint
        if max_cost is not None:
            estimated_batch_cost = processor.estimate_batch_cost(len(batch_docs))
            if state.cost_so_far + estimated_batch_cost > max_cost:
                print(f"⚠️  Budget limit reached. Spent: ${state.cost_so_far:.2f}, Limit: ${max_cost:.2f}")
                print("Stopping processing.")
                break

        # Ask for confirmation in interactive mode
        if mode == "interactive":
            if not processor.confirm_batch():
                print("Batch skipped. Exiting.")
                break

        # Process batch
        batch_results = processor.process_batch(
            documents=batch_docs,
            batch_num=batch_num,
            total_batches=total_batches,
            show_progress=True
        )

        # Mark batch as completed
        state_manager.complete_batch()

        # Show current state
        print(state_manager.get_summary())

        # Check if batch was interrupted
        if not batch_results["completed"]:
            print("\n⚠️  Processing interrupted.")
            processor.finalize()
            return

        # Check time constraint
        if max_hours is not None:
            # TODO: Implement time tracking
            pass

    # Final summary
    final_state = state_manager.state
    print(f"\n{'='*60}")
    print("Full Pass Complete!")
    print(f"{'='*60}")
    print(f"Total processed:   {final_state.processed:,}")
    print(f"Successful:        {final_state.successful:,} ({final_state.successful/final_state.processed*100:.1f}%)")
    print(f"Failed:            {final_state.failed:,}")
    print(f"Total cost:        ${final_state.cost_so_far:.2f}")
    print(f"Avg confidence:    {final_state.average_confidence:.2f}")
    print(f"Low confidence:    {final_state.low_confidence_count}")
    print(f"{'='*60}\n")


def main():
    """Main entry point for full pass CLI."""
    parser = argparse.ArgumentParser(
        description="Full pass document processing with batch control and resume capability"
    )

    parser.add_argument(
        "--batch-size",
        type=str,
        default="medium",
        help="Batch size: tiny (10), small (100), medium (500), large (1000), or custom number"
    )

    parser.add_argument(
        "--mode",
        choices=["interactive", "auto"],
        default="interactive",
        help="Processing mode: interactive (confirm each batch) or auto (run all)"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous session"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status and exit"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset state and start fresh"
    )

    parser.add_argument(
        "--max-cost",
        type=float,
        help="Maximum total cost in dollars"
    )

    parser.add_argument(
        "--max-hours",
        type=float,
        help="Maximum hours to run"
    )

    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=100,
        help="Create checkpoint every N documents (default: 100)"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Initialize state manager
    state_manager = StateManager()

    # Handle status command
    if args.status:
        show_status(state_manager)
        return

    # Handle reset command
    if args.reset:
        response = input("⚠️  This will delete all progress. Are you sure? (y/n): ").strip().lower()
        if response == 'y':
            state_manager.reset()
            print("✅ State reset complete.")
        else:
            print("Reset cancelled.")
        return

    # Parse batch size
    if args.batch_size in BATCH_SIZES:
        batch_size = BATCH_SIZES[args.batch_size]
    else:
        try:
            batch_size = int(args.batch_size)
        except ValueError:
            print(f"❌ Invalid batch size: {args.batch_size}")
            print(f"   Use: tiny, small, medium, large, or a number")
            return

    # Run full pass
    try:
        run_full_pass(
            batch_size=batch_size,
            mode=args.mode,
            resume=args.resume,
            max_cost=args.max_cost,
            max_hours=args.max_hours,
            checkpoint_interval=args.checkpoint_interval
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        state_manager.save()
        print("✅ State saved.")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        state_manager.save()
        print("State saved.")


if __name__ == "__main__":
    main()
