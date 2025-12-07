# Transcription System Simplification Plan

**Date:** 2025-12-07
**Problem:** The transcription system has become confusing with multiple overlapping approaches, too many parameters, and unclear entry points.

---

## Current State: The Problem

### Multiple Overlapping Systems

| System | File | Purpose |
|--------|------|---------|
| `transcribe.py` | Main transcription | Single/batch with threading |
| `transcribe_v2.py` | Legacy | Old version, unclear if used |
| `full_pass.py` | Batch orchestration | Wraps transcribe.py with state |
| `batch_processor.py` | Batch logic | Used by full_pass.py |
| `state_manager.py` | State persistence | Used by full_pass.py |

### Too Many Make Targets (9 for transcription alone!)

```
transcribe          - 1 file
transcribe-all      - All files
transcribe-some     - N files
resume              - All remaining
resume-some         - N remaining
full-pass           - Interactive batches
full-pass-auto      - Auto batches
full-pass-resume    - Resume full-pass
full-pass-status    - Show status
full-pass-reset     - Reset state
```

### Confusing Parameters

- `--max-files` (0 means all? unintuitive)
- `--resume` (flag) vs `full-pass --resume` (different behavior)
- `--max-workers` (threading)
- `--batch-size` (tiny/small/medium/large or number)
- `--mode` (interactive/auto)
- `--max-cost` (budget)
- `--max-hours` (time limit)

### User Confusion Points

1. **"Which command do I use?"** - 9 options is too many
2. **"What's the difference between resume and full-pass-resume?"** - Different systems
3. **"What do all these parameters mean?"** - Information overload
4. **"How do I just transcribe everything?"** - Should be simple

---

## Proposed Solution: Progressive Disclosure

### Principle: One Command, Options When Needed

**The 80% case:** User wants to transcribe documents. Make that dead simple.

**The 20% case:** User needs fine control. Offer it, but don't require it.

---

## New Design

### Single Entry Point

```bash
# THE ONE COMMAND
make transcribe
```

That's it. This should:
1. Auto-detect what needs to be done
2. Show status
3. Ask for confirmation
4. Process with sensible defaults
5. Be resumable (Ctrl+C safe)

### Progressive Complexity

```
Level 0 (Default):     make transcribe
Level 1 (Limit):       make transcribe N=100
Level 2 (Options):     make transcribe N=100 BUDGET=50
Level 3 (Advanced):    uv run python -m app.transcribe --help
```

### New Make Targets (Reduced from 9 to 3)

```makefile
# Primary command - does everything
transcribe:
	uv run python -m app.transcribe

# With file limit
transcribe N=100:
	uv run python -m app.transcribe --limit 100

# Status check (no processing)
transcribe-status:
	uv run python -m app.transcribe --status
```

### New CLI Design

```bash
# Default: Process all remaining, auto-resume, show estimate, ask confirm
uv run python -m app.transcribe

# Limit number of files
uv run python -m app.transcribe --limit 100
uv run python -m app.transcribe -n 100

# Skip confirmation
uv run python -m app.transcribe --yes

# Set budget limit (stops when reached)
uv run python -m app.transcribe --budget 50

# Just show status, don't process
uv run python -m app.transcribe --status

# Dry run (no API calls)
uv run python -m app.transcribe --dry-run
```

### Removed/Deprecated Options

| Old | New | Reason |
|-----|-----|--------|
| `--max-files 0` | `--limit` (no value = all) | Clearer |
| `--resume` | Always on | Why wouldn't you resume? |
| `--max-workers` | Auto-calculated | Users shouldn't need to tune this |
| `--batch-size` | Internal detail | Not user-facing |
| `--mode` | Removed | Just use `--yes` for non-interactive |
| `full-pass` commands | Merged into transcribe | One system |

---

## New User Experience

### Scenario 1: First Time User

```bash
$ make transcribe

Transcription Status
====================
Total documents:     21,512
Already done:         4,924 (22.9%)
Remaining:           16,588 (77.1%)

Estimate
--------
Model:        gpt-4.1-mini
Cost:         ~$60
Time:         ~2.5 hours

Proceed? [y/N]: y

Processing... ████████████░░░░░░░░ 45% (7,465/16,588)
              Cost: $27.12 | Speed: 115 docs/min | ETA: 1h 20m

^C
Stopping gracefully... saving progress.
Run 'make transcribe' to continue.
```

### Scenario 2: Continue Where Left Off

```bash
$ make transcribe

Transcription Status
====================
Total documents:     21,512
Already done:        12,389 (57.6%)
Remaining:            9,123 (42.4%)

Estimate
--------
Model:        gpt-4.1-mini
Cost:         ~$33
Time:         ~1.3 hours

Proceed? [y/N]: y
```

### Scenario 3: Just Process 100 Files

```bash
$ make transcribe N=100

Transcription Status
====================
Processing:    100 documents (of 9,123 remaining)

Estimate
--------
Cost:         ~$0.36
Time:         ~50 seconds

Proceed? [y/N]: y
```

### Scenario 4: Check Status Without Processing

```bash
$ make transcribe-status

Transcription Status
====================
Total documents:     21,512
Already done:        12,389 (57.6%)
Remaining:            9,123 (42.4%)

Model breakdown:
  gpt-4.1-mini:     12,389
  (others):              0

Estimated to complete:
  Cost:  ~$33
  Time:  ~1.3 hours
```

---

## Implementation Plan

### Phase 1: Consolidate (Remove Duplication)

1. **Archive `transcribe_v2.py`** - Move to `archive/` if not used
2. **Merge full_pass into transcribe.py** - One system
3. **Simplify state management** - Use file existence as state (already works)

### Phase 2: Simplify CLI

1. **New argument parser:**
   ```python
   parser.add_argument('-n', '--limit', type=int, help='Max files to process')
   parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation')
   parser.add_argument('--budget', type=float, help='Stop at budget ($)')
   parser.add_argument('--status', action='store_true', help='Show status only')
   parser.add_argument('--dry-run', action='store_true', help='No API calls')
   ```

2. **Remove confusing options:**
   - `--max-files 0` → just omit `--limit`
   - `--resume` → always on (default behavior)
   - `--max-workers` → auto-calculated internally
   - `--batch-size` → internal detail

### Phase 3: Simplify Makefile

**Before (9 targets):**
```makefile
transcribe:
transcribe-all:
transcribe-some:
resume:
resume-some:
full-pass:
full-pass-auto:
full-pass-resume:
full-pass-status:
full-pass-reset:
```

**After (3 targets):**
```makefile
# Primary transcription command
# Usage: make transcribe [N=100] [BUDGET=50] [YES=1]
transcribe:
	@if [ -n "$(N)" ]; then \
		ARGS="--limit $(N)"; \
	fi; \
	if [ -n "$(BUDGET)" ]; then \
		ARGS="$$ARGS --budget $(BUDGET)"; \
	fi; \
	if [ "$(YES)" = "1" ]; then \
		ARGS="$$ARGS --yes"; \
	fi; \
	uv run python -m app.transcribe $$ARGS

# Check status without processing
transcribe-status:
	uv run python -m app.transcribe --status

# Reset (remove all transcripts for current model)
transcribe-reset:
	@echo "This will delete all transcripts for the current model."
	@read -p "Are you sure? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ]; then \
		rm -rf data/generated_transcripts/$$(grep OPENAI_MODEL .env | cut -d= -f2)/; \
	fi
```

### Phase 4: Update Documentation

1. **STARTHERE.md** - Single transcription section
2. **CLAUDE.md** - Remove full-pass documentation
3. **Remove** `research/FULL_PASS_PLAN.md` - Outdated

---

## Files to Modify/Remove

### Remove or Archive
- [ ] `app/transcribe_v2.py` → `archive/`
- [ ] `app/full_pass.py` → `archive/`
- [ ] `app/batch_processor.py` → `archive/` (merge useful bits)
- [ ] `app/state_manager.py` → `archive/` (use simpler approach)
- [ ] `research/FULL_PASS_PLAN.md` → `archive/`

### Modify
- [ ] `app/transcribe.py` - Simplify CLI, add --status, --budget
- [ ] `Makefile` - Reduce to 3 targets
- [ ] `STARTHERE.md` - Simplify transcription section
- [ ] `CLAUDE.md` - Remove full-pass documentation

### Keep As-Is
- `app/utils/cost_tracker.py` - Good utility
- `app/utils/rate_limiter.py` - Good utility
- `app/utils/response_repair.py` - Good utility

---

## Migration Path

For existing users:

```bash
# Old way (still works during transition)
make resume

# New way
make transcribe
```

Add deprecation warnings to old commands for 1-2 releases.

---

## Summary

| Before | After |
|--------|-------|
| 9 Make targets | 3 Make targets |
| 5 Python files | 1 Python file |
| ~15 CLI options | ~5 CLI options |
| 2 parallel systems | 1 unified system |
| Complex batch orchestration | Simple loop with graceful shutdown |

### The New Mental Model

```
make transcribe              # Do the thing
make transcribe N=100        # Do some of the thing
make transcribe-status       # Check progress
```

That's it. Everything else is internal implementation detail.

---

## Decision Points

Before implementing, please confirm:

1. **Archive or delete old files?** (Recommend: archive)
2. **Keep `--max-workers` as hidden option?** (Recommend: yes, for debugging)
3. **Transition period with deprecation warnings?** (Recommend: yes)
4. **Batch size - fixed or configurable?** (Recommend: fixed at 500 internal)

---

## Next Steps

1. Review and approve this plan
2. Create feature branch: `feature/simplify-transcription`
3. Implement Phase 1-4
4. Test with small batch
5. Update documentation
6. Create PR
