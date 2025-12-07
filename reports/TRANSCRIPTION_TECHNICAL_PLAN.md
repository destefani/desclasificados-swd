# Technical Implementation Plan: Transcription Simplification

**Date:** 2025-12-07
**Branch:** `feature/simplify-transcription`
**Estimated Effort:** 4-6 hours

---

## Overview

Consolidate 5 Python files (2,400 lines) into 1 simplified file (~600 lines) with a clean CLI.

### Current State

| File | Lines | Purpose | Action |
|------|-------|---------|--------|
| `app/transcribe.py` | 943 | Main transcription | **KEEP & MODIFY** |
| `app/transcribe_v2.py` | 277 | Legacy version | **ARCHIVE** |
| `app/full_pass.py` | 413 | Batch orchestration | **ARCHIVE** |
| `app/batch_processor.py` | 378 | Batch logic | **ARCHIVE** |
| `app/state_manager.py` | 389 | State persistence | **ARCHIVE** |

### Target State

| File | Lines | Purpose |
|------|-------|---------|
| `app/transcribe.py` | ~600 | Unified transcription with simple CLI |

---

## Step-by-Step Implementation

### Step 1: Create Archive Directory

```bash
mkdir -p archive/transcription_legacy
```

Move files that will be replaced:
- `app/transcribe_v2.py` → `archive/transcription_legacy/`
- `app/full_pass.py` → `archive/transcription_legacy/`
- `app/batch_processor.py` → `archive/transcription_legacy/`
- `app/state_manager.py` → `archive/transcription_legacy/`

### Step 2: Simplify `app/transcribe.py`

#### 2.1 Remove Duplicate Code

The file has duplicate implementations. Remove:

- **Lines 75-116**: `CostTracker` class (use `app/utils/cost_tracker.py` instead)
- **Lines 165-256**: `validate_response()` (use `app/utils/response_repair.py` instead)
- **Lines 258-330**: `auto_repair_response()` (use `app/utils/response_repair.py` instead)

Replace with imports:
```python
from app.utils.cost_tracker import CostTracker, estimate_cost, PRICING
from app.utils.response_repair import auto_repair_response, validate_response
```

#### 2.2 New CLI Interface

Replace the argument parser (lines 903-943) with:

```python
def parse_args():
    parser = argparse.ArgumentParser(
        description="Transcribe CIA documents using GPT-4.1-mini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Process all remaining documents
  %(prog)s -n 100             # Process 100 documents
  %(prog)s -n 100 --budget 5  # Process up to 100 docs or $5
  %(prog)s --status           # Show status without processing
  %(prog)s --yes              # Skip confirmation prompt
        """
    )

    parser.add_argument(
        '-n', '--limit',
        type=int,
        default=None,
        metavar='N',
        help='Maximum number of files to process (default: all remaining)'
    )

    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompt'
    )

    parser.add_argument(
        '--budget',
        type=float,
        default=None,
        metavar='$',
        help='Stop when estimated cost reaches this amount'
    )

    parser.add_argument(
        '--status',
        action='store_true',
        help='Show transcription status and exit'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate processing without API calls'
    )

    # Hidden advanced options (for debugging)
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help=argparse.SUPPRESS  # Hidden from help
    )

    return parser.parse_args()
```

#### 2.3 New Main Function

Replace `process_documents_in_directory()` with cleaner logic:

```python
def get_transcription_status() -> dict:
    """Get current transcription status."""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    images_dir = DATA_DIR / "images"
    output_dir = DATA_DIR / "generated_transcripts" / model

    # Count all images
    all_images = sorted(
        f for f in os.listdir(images_dir)
        if f.lower().endswith((".jpg", ".jpeg"))
    )
    total = len(all_images)

    # Count existing transcripts
    output_dir.mkdir(parents=True, exist_ok=True)
    done_ids = {
        os.path.splitext(f)[0]
        for f in os.listdir(output_dir)
        if f.endswith(".json")
    }
    done = len(done_ids)

    # Find remaining
    remaining_files = [
        f for f in all_images
        if os.path.splitext(f)[0] not in done_ids
    ]
    remaining = len(remaining_files)

    return {
        "model": model,
        "total": total,
        "done": done,
        "remaining": remaining,
        "percent_done": (done / total * 100) if total > 0 else 0,
        "remaining_files": remaining_files,
    }


def print_status(status: dict):
    """Print transcription status."""
    print()
    print("Transcription Status")
    print("=" * 40)
    print(f"Model:           {status['model']}")
    print(f"Total documents: {status['total']:,}")
    print(f"Completed:       {status['done']:,} ({status['percent_done']:.1f}%)")
    print(f"Remaining:       {status['remaining']:,}")
    print()


def print_estimate(files_to_process: int, model: str):
    """Print cost and time estimate."""
    # Use pricing from utils
    pricing = PRICING.get(model, PRICING.get("gpt-4.1-mini"))

    # Token estimates
    input_tokens = files_to_process * 3000
    output_tokens = files_to_process * 1500

    cost = (input_tokens * pricing.input_rate +
            output_tokens * pricing.output_rate)

    # Time estimate (at ~2 docs/second with overhead)
    time_seconds = files_to_process / 2
    time_minutes = time_seconds / 60

    print("Estimate")
    print("-" * 40)
    print(f"Files to process: {files_to_process:,}")
    print(f"Estimated cost:   ${cost:.2f}")
    print(f"Estimated time:   {format_time(time_seconds)}")
    print()

    return cost


def format_time(seconds: float) -> str:
    """Format seconds as human-readable time."""
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.1f} minutes"
    else:
        return f"{seconds/3600:.1f} hours"


def main():
    args = parse_args()

    # Get current status
    status = get_transcription_status()

    # Status-only mode
    if args.status:
        print_status(status)
        if status['remaining'] > 0:
            print_estimate(status['remaining'], status['model'])
        return

    # Nothing to do
    if status['remaining'] == 0:
        print_status(status)
        print("All documents have been transcribed!")
        return

    # Determine files to process
    files_to_process = status['remaining_files']
    if args.limit:
        files_to_process = files_to_process[:args.limit]

    # Show status and estimate
    print_status(status)
    estimated_cost = print_estimate(len(files_to_process), status['model'])

    # Budget check
    if args.budget and estimated_cost > args.budget:
        # Reduce to fit budget
        cost_per_doc = estimated_cost / len(files_to_process)
        max_docs = int(args.budget / cost_per_doc)
        files_to_process = files_to_process[:max_docs]
        print(f"Budget limit: Processing {max_docs} files (${args.budget:.2f} budget)")
        print()

    # Confirmation
    if not args.yes and not args.dry_run:
        response = input("Proceed? [y/N]: ").strip().lower()
        if response not in ('y', 'yes'):
            print("Cancelled.")
            return

    # Process documents
    process_files(
        files=files_to_process,
        model=status['model'],
        dry_run=args.dry_run,
        max_workers=args.workers or get_optimal_workers()
    )


if __name__ == "__main__":
    main()
```

#### 2.4 Simplified Processing Function

Replace `process_documents_in_directory()` with:

```python
def process_files(files: list, model: str, dry_run: bool = False, max_workers: int = 2):
    """
    Process a list of files with progress tracking and graceful shutdown.

    Args:
        files: List of filenames to process
        model: Model name for output directory
        dry_run: If True, simulate without API calls
        max_workers: Number of parallel workers
    """
    images_dir = DATA_DIR / "images"
    output_dir = DATA_DIR / "generated_transcripts" / model
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup graceful shutdown
    shutdown_requested = False
    def handle_shutdown(signum, frame):
        nonlocal shutdown_requested
        if not shutdown_requested:
            print("\n\nStopping gracefully... (wait for current files)")
            shutdown_requested = True

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Track results
    results = {"success": 0, "failed": 0}
    start_time = time.time()

    print(f"\nProcessing {len(files)} documents...")
    print()

    # Process with thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                transcribe_single_document,
                f, images_dir, output_dir,
                resume=True, dry_run=dry_run
            ): f
            for f in files
        }

        with tqdm(total=len(futures), desc="Progress", unit="doc") as pbar:
            for future in as_completed(futures):
                if shutdown_requested:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    result = future.result()
                    if result == "success":
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    results["failed"] += 1
                    logging.error(f"Error: {e}")

                pbar.update(1)

    # Print summary
    elapsed = time.time() - start_time
    print()
    print("=" * 40)
    print("Complete")
    print("=" * 40)
    print(f"Processed: {results['success'] + results['failed']}")
    print(f"Success:   {results['success']}")
    print(f"Failed:    {results['failed']}")
    print(f"Time:      {format_time(elapsed)}")

    if not dry_run and results['success'] > 0:
        cost_tracker.print_summary(model=model)

    if shutdown_requested:
        print()
        print("Stopped early. Run again to continue.")
```

### Step 3: Update Makefile

Replace transcription targets with:

```makefile
# =============================================================================
# TRANSCRIPTION
# =============================================================================

# Primary transcription command
# Usage:
#   make transcribe              - Process all remaining
#   make transcribe N=100        - Process 100 files
#   make transcribe BUDGET=50    - Stop at $50
#   make transcribe YES=1        - Skip confirmation
transcribe:
	@CMD="uv run python -m app.transcribe"; \
	if [ -n "$(N)" ]; then CMD="$$CMD --limit $(N)"; fi; \
	if [ -n "$(BUDGET)" ]; then CMD="$$CMD --budget $(BUDGET)"; fi; \
	if [ "$(YES)" = "1" ]; then CMD="$$CMD --yes"; fi; \
	$$CMD

# Show transcription status
transcribe-status:
	uv run python -m app.transcribe --status

# =============================================================================
```

Remove these targets:
- `transcribe-all`
- `transcribe-some`
- `resume`
- `resume-some`
- `full-pass`
- `full-pass-auto`
- `full-pass-resume`
- `full-pass-status`
- `full-pass-reset`

### Step 4: Update Cost Tracker Pricing

Add gpt-4.1-mini pricing to `app/utils/cost_tracker.py` if not present:

```python
PRICING = {
    # ... existing ...
    "gpt-4.1-mini": PricingTier(0.40, 1.60),
}
```

### Step 5: Update Documentation

#### STARTHERE.md - Transcription Section

Replace the complex transcription documentation with:

```markdown
### Document Transcription

```bash
# Process all remaining documents
make transcribe

# Process specific number of files
make transcribe N=100

# With budget limit
make transcribe N=1000 BUDGET=50

# Check status
make transcribe-status
```

The script automatically:
- Detects remaining work
- Shows cost estimate
- Asks for confirmation
- Resumes from where it left off (Ctrl+C safe)
```

#### CLAUDE.md - Remove Full-Pass Section

Remove the entire "Full Pass Processing" section and replace with a reference to the simplified transcription commands.

### Step 6: Update .env.example

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini  # Recommended for transcription
```

---

## File Changes Summary

### Files to Archive (move to `archive/transcription_legacy/`)

| File | Reason |
|------|--------|
| `app/transcribe_v2.py` | Unused legacy version |
| `app/full_pass.py` | Functionality merged into transcribe.py |
| `app/batch_processor.py` | Functionality merged into transcribe.py |
| `app/state_manager.py` | Using simpler file-based state |
| `research/FULL_PASS_PLAN.md` | Outdated documentation |

### Files to Modify

| File | Changes |
|------|---------|
| `app/transcribe.py` | New CLI, remove duplicates, simplify |
| `Makefile` | Remove 9 targets, add 2 simple ones |
| `STARTHERE.md` | Simplify transcription docs |
| `CLAUDE.md` | Remove full-pass section |
| `.env.example` | Set gpt-4.1-mini as default |
| `app/utils/cost_tracker.py` | Ensure gpt-4.1-mini pricing exists |

### Files to Delete (if exists)

| File | Reason |
|------|--------|
| `data/transcription_state.json` | No longer needed |
| `data/checkpoints/` | No longer needed |

---

## Testing Plan

### Test 1: Status Check
```bash
make transcribe-status
# Expected: Shows current status without processing
```

### Test 2: Dry Run
```bash
uv run python -m app.transcribe --dry-run -n 5
# Expected: Simulates processing 5 files
```

### Test 3: Small Batch
```bash
make transcribe N=10
# Expected: Processes 10 files with confirmation
```

### Test 4: With Budget
```bash
make transcribe N=100 BUDGET=1
# Expected: Stops when cost reaches ~$1
```

### Test 5: Graceful Shutdown
```bash
make transcribe N=100
# Press Ctrl+C after a few files
# Expected: Stops gracefully, shows summary
# Run again: Should continue from where it stopped
```

### Test 6: Skip Confirmation
```bash
make transcribe N=5 YES=1
# Expected: Processes without asking
```

---

## Rollback Plan

If issues arise:

1. Restore archived files from `archive/transcription_legacy/`
2. Revert Makefile changes
3. The old commands will work again

---

## Definition of Done

- [ ] All legacy files archived
- [ ] `app/transcribe.py` simplified with new CLI
- [ ] Makefile has only 2 transcription targets
- [ ] `make transcribe` works end-to-end
- [ ] `make transcribe-status` shows correct status
- [ ] Graceful shutdown works (Ctrl+C)
- [ ] Budget limiting works
- [ ] Documentation updated
- [ ] All tests pass
- [ ] PR created and ready for review

---

## Estimated Line Changes

| File | Before | After | Delta |
|------|--------|-------|-------|
| `app/transcribe.py` | 943 | ~600 | -343 |
| `app/transcribe_v2.py` | 277 | 0 | -277 |
| `app/full_pass.py` | 413 | 0 | -413 |
| `app/batch_processor.py` | 378 | 0 | -378 |
| `app/state_manager.py` | 389 | 0 | -389 |
| `Makefile` | 205 | ~160 | -45 |
| **Total** | **2,605** | **~760** | **-1,845** |

Net reduction: **~1,800 lines** (70% reduction)
