"""
State management for full pass document processing.

Provides persistence, resume capability, and progress tracking for batch processing
of large document collections.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class ProcessingState:
    """Represents the current state of a full pass processing session."""

    session_id: str
    prompt_version: str
    started_at: str
    last_updated: str
    total_documents: int
    processed: int
    successful: int
    failed: int
    skipped: int
    remaining: int
    cost_so_far: float
    average_confidence: float
    low_confidence_count: int
    batches_completed: int
    current_batch_size: int
    estimated_time_remaining_minutes: int
    processing_speed_docs_per_minute: float
    last_checkpoint: Optional[str] = None
    failed_documents: list = None
    low_confidence_documents: list = None

    def __post_init__(self):
        """Initialize mutable default values."""
        if self.failed_documents is None:
            self.failed_documents = []
        if self.low_confidence_documents is None:
            self.low_confidence_documents = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingState':
        """Create ProcessingState from dictionary."""
        return cls(**data)


class StateManager:
    """Manages processing state persistence and recovery."""

    def __init__(self, state_file: Path = None):
        """
        Initialize StateManager.

        Args:
            state_file: Path to state JSON file. Defaults to data/transcription_state.json
        """
        if state_file is None:
            state_file = Path(__file__).parent.parent / "data" / "transcription_state.json"

        self.state_file = Path(state_file)
        self.state: Optional[ProcessingState] = None
        self.logger = logging.getLogger(__name__)

        # Ensure data directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def create_new_session(
        self,
        total_documents: int,
        batch_size: int,
        prompt_version: str = "v2"
    ) -> ProcessingState:
        """
        Create a new processing session.

        Args:
            total_documents: Total number of documents to process
            batch_size: Size of each processing batch
            prompt_version: Prompt version to use (v1 or v2)

        Returns:
            New ProcessingState instance
        """
        now = datetime.now()
        session_id = now.strftime("%Y%m%d_%H%M%S")

        self.state = ProcessingState(
            session_id=session_id,
            prompt_version=prompt_version,
            started_at=now.isoformat(),
            last_updated=now.isoformat(),
            total_documents=total_documents,
            processed=0,
            successful=0,
            failed=0,
            skipped=0,
            remaining=total_documents,
            cost_so_far=0.0,
            average_confidence=0.0,
            low_confidence_count=0,
            batches_completed=0,
            current_batch_size=batch_size,
            estimated_time_remaining_minutes=0,
            processing_speed_docs_per_minute=0.0,
            failed_documents=[],
            low_confidence_documents=[]
        )

        self.save()
        self.logger.info(f"Created new session: {session_id}")
        return self.state

    def load(self) -> Optional[ProcessingState]:
        """
        Load processing state from file.

        Returns:
            ProcessingState if found, None otherwise
        """
        if not self.state_file.exists():
            self.logger.info("No existing state file found")
            return None

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.state = ProcessingState.from_dict(data)
            self.logger.info(f"Loaded session: {self.state.session_id}")
            return self.state

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse state file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load state file: {e}")
            return None

    def save(self) -> bool:
        """
        Save current state to file.

        Returns:
            True if successful, False otherwise
        """
        if self.state is None:
            self.logger.warning("No state to save")
            return False

        try:
            # Update last_updated timestamp
            self.state.last_updated = datetime.now().isoformat()

            # Write to temporary file first, then rename (atomic operation)
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.state_file)

            self.logger.debug("State saved successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False

    def update(
        self,
        processed: int = None,
        successful: int = None,
        failed: int = None,
        skipped: int = None,
        cost: float = None,
        confidence_scores: list = None,
        failed_doc: str = None,
        low_confidence_doc: dict = None
    ) -> bool:
        """
        Update processing state with new metrics.

        Args:
            processed: Number of documents processed (incremental)
            successful: Number of successful documents (incremental)
            failed: Number of failed documents (incremental)
            skipped: Number of skipped documents (incremental)
            cost: Cost to add to total
            confidence_scores: List of confidence scores to update average
            failed_doc: Document name to add to failed list
            low_confidence_doc: Dict with document info to add to low confidence list

        Returns:
            True if saved successfully
        """
        if self.state is None:
            self.logger.error("No active state to update")
            return False

        # Update counters (incremental)
        if processed is not None:
            self.state.processed += processed
        if successful is not None:
            self.state.successful += successful
        if failed is not None:
            self.state.failed += failed
        if skipped is not None:
            self.state.skipped += skipped

        # Update remaining
        self.state.remaining = self.state.total_documents - self.state.processed

        # Update cost
        if cost is not None:
            self.state.cost_so_far += cost

        # Update confidence metrics
        if confidence_scores is not None and len(confidence_scores) > 0:
            self.state.average_confidence = sum(confidence_scores) / len(confidence_scores)

        # Add failed document
        if failed_doc is not None:
            self.state.failed_documents.append(failed_doc)

        # Add low confidence document
        if low_confidence_doc is not None:
            self.state.low_confidence_documents.append(low_confidence_doc)
            self.state.low_confidence_count = len(self.state.low_confidence_documents)

        # Calculate processing speed
        if self.state.processed > 0:
            start_time = datetime.fromisoformat(self.state.started_at)
            elapsed_seconds = (datetime.now() - start_time).total_seconds()
            elapsed_minutes = elapsed_seconds / 60
            self.state.processing_speed_docs_per_minute = self.state.processed / elapsed_minutes if elapsed_minutes > 0 else 0

            # Estimate time remaining
            if self.state.processing_speed_docs_per_minute > 0:
                self.state.estimated_time_remaining_minutes = int(
                    self.state.remaining / self.state.processing_speed_docs_per_minute
                )

        return self.save()

    def complete_batch(self) -> bool:
        """
        Mark a batch as completed.

        Returns:
            True if saved successfully
        """
        if self.state is None:
            return False

        self.state.batches_completed += 1
        return self.save()

    def create_checkpoint(self) -> Optional[Path]:
        """
        Create a checkpoint file with current state.

        Returns:
            Path to checkpoint file if successful, None otherwise
        """
        if self.state is None:
            return None

        checkpoint_dir = self.state_file.parent / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / f"checkpoint_{self.state.processed}.json"

        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)

            self.state.last_checkpoint = str(checkpoint_file)
            self.logger.info(f"Created checkpoint: {checkpoint_file.name}")

            # Keep only last 5 checkpoints
            self._cleanup_old_checkpoints(checkpoint_dir, keep=5)

            return checkpoint_file

        except Exception as e:
            self.logger.error(f"Failed to create checkpoint: {e}")
            return None

    def _cleanup_old_checkpoints(self, checkpoint_dir: Path, keep: int = 5):
        """Remove old checkpoint files, keeping only the most recent N."""
        checkpoints = sorted(checkpoint_dir.glob("checkpoint_*.json"))

        if len(checkpoints) > keep:
            for old_checkpoint in checkpoints[:-keep]:
                try:
                    old_checkpoint.unlink()
                    self.logger.debug(f"Removed old checkpoint: {old_checkpoint.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove checkpoint {old_checkpoint}: {e}")

    def load_checkpoint(self, checkpoint_file: Path) -> Optional[ProcessingState]:
        """
        Load state from a specific checkpoint file.

        Args:
            checkpoint_file: Path to checkpoint JSON file

        Returns:
            ProcessingState if successful, None otherwise
        """
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.state = ProcessingState.from_dict(data)
            self.logger.info(f"Loaded checkpoint from: {checkpoint_file.name}")
            return self.state

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    def reset(self) -> bool:
        """
        Delete state file and reset to clean slate.

        Returns:
            True if successful
        """
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                self.logger.info("State file deleted")

            self.state = None
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset state: {e}")
            return False

    def get_summary(self) -> str:
        """
        Get a human-readable summary of current state.

        Returns:
            Formatted string with state summary
        """
        if self.state is None:
            return "No active session"

        s = self.state

        # Calculate percentages
        progress_pct = (s.processed / s.total_documents * 100) if s.total_documents > 0 else 0
        success_pct = (s.successful / s.processed * 100) if s.processed > 0 else 0

        summary = f"""
┌─────────────────────────────────────────────────────────────┐
│ Session: {s.session_id}
│ Prompt: v{s.prompt_version}
├─────────────────────────────────────────────────────────────┤
│ Documents:  {s.processed:,} / {s.total_documents:,} ({progress_pct:.1f}%)
│ Successful: {s.successful:,} ({success_pct:.1f}%)
│ Failed:     {s.failed:,}
│ Skipped:    {s.skipped:,}
│ Remaining:  {s.remaining:,}
├─────────────────────────────────────────────────────────────┤
│ Cost:       ${s.cost_so_far:.2f}
│ Avg Confidence: {s.average_confidence:.2f}
│ Low Confidence: {s.low_confidence_count} docs
├─────────────────────────────────────────────────────────────┤
│ Batches:    {s.batches_completed}
│ Speed:      {s.processing_speed_docs_per_minute:.1f} docs/min
│ ETA:        {s.estimated_time_remaining_minutes} minutes
└─────────────────────────────────────────────────────────────┘
"""
        return summary
