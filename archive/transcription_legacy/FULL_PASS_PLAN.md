# Full Pass Processing Plan - Prompt v2

**Date:** 2025-11-30
**Scope:** Process all 21,512 documents with Prompt v2
**Estimated Cost:** ~$32 (at $0.0015/doc)
**Estimated Time:** 3-12 hours (depending on rate limiting)

---

## Executive Summary

This plan outlines a controlled, resumable, and cost-conscious approach to processing the entire corpus of 21,512 declassified CIA documents using the improved Prompt v2 system.

**Key Design Principles:**
1. **Cost Control First** - User approves spending at every step
2. **Graceful Resume** - Stop and continue without losing progress
3. **Quality Monitoring** - Track success rates in real-time
4. **Time Flexibility** - Control processing speed and duration
5. **Safety Nets** - Automatic rollback triggers and error handling

---

## Current State Analysis

### What We Have
- ✅ Prompt v2 with Structured Outputs (100% schema compliance)
- ✅ Basic cost estimation in `transcribe.py`
- ✅ Resume capability (skips existing JSONs)
- ✅ Rate limiting (2 RPS, 180k TPM)
- ✅ Retry logic with exponential backoff
- ✅ Small-scale testing (3 docs, 100% success)

### What We Need
- ❌ **Batch processing** - Process in controllable chunks
- ❌ **Progress tracking** - Real-time status dashboard
- ❌ **Budget controls** - Stop if cost exceeds limit
- ❌ **Time controls** - Stop after X hours
- ❌ **Checkpointing** - Save state at intervals
- ❌ **Quality monitoring** - Track metrics during run
- ❌ **Graceful shutdown** - Handle Ctrl+C cleanly
- ❌ **Interim reports** - Progress summaries at intervals

---

## Architecture Design

### 1. Batch Processing Controller

**Purpose:** Process documents in manageable batches with user approval between batches.

**Configuration:**
```python
# Batch sizes (user selectable)
BATCH_SIZES = {
    "tiny": 10,      # Testing
    "small": 100,    # Conservative
    "medium": 500,   # Balanced
    "large": 1000,   # Aggressive
    "all": None      # Process everything (with confirmation)
}

# Processing modes
MODES = {
    "interactive": "Prompt for confirmation after each batch",
    "auto": "Run all batches with single upfront confirmation",
    "scheduled": "Run during specified time window"
}
```

**Workflow:**
```
1. Calculate total remaining documents
2. Estimate cost and time for batch
3. Show summary:
   - Documents to process: N
   - Estimated cost: $X
   - Estimated time: Y minutes
   - Current rate: Z docs/minute
4. Request confirmation (y/n/adjust)
5. Process batch
6. Show results:
   - Success rate: X%
   - Cost so far: $Y
   - Low-confidence docs: Z
7. If more batches → repeat from step 2
```

### 2. Progress State Management

**State File:** `data/transcription_state.json`

```json
{
  "session_id": "20241130_153045",
  "prompt_version": "v2",
  "started_at": "2024-11-30T15:30:45Z",
  "last_updated": "2024-11-30T16:15:30Z",
  "total_documents": 21512,
  "processed": 1250,
  "successful": 1245,
  "failed": 5,
  "skipped": 0,
  "remaining": 20262,
  "cost_so_far": 1.875,
  "average_confidence": 0.89,
  "low_confidence_count": 87,
  "batches_completed": 12,
  "current_batch_size": 100,
  "estimated_time_remaining_minutes": 180,
  "processing_speed_docs_per_minute": 1.8,
  "last_checkpoint": "data/checkpoints/checkpoint_1200.json"
}
```

**Operations:**
- **Initialize** - Create new session on first run
- **Update** - Save after each document (or every N docs)
- **Resume** - Load state and continue from last position
- **Reset** - Clear state and start over

### 3. Cost Control System

**Budget Management:**
```python
class BudgetController:
    def __init__(self, max_budget: float = None):
        self.max_budget = max_budget  # None = unlimited
        self.spent = 0.0
        self.estimated_cost_per_doc = 0.0015

    def estimate_batch_cost(self, num_docs: int) -> float:
        return num_docs * self.estimated_cost_per_doc

    def can_process(self, num_docs: int) -> bool:
        if self.max_budget is None:
            return True
        estimated = self.estimate_batch_cost(num_docs)
        return (self.spent + estimated) <= self.max_budget

    def record_cost(self, actual_cost: float):
        self.spent += actual_cost

    def remaining_budget(self) -> float:
        if self.max_budget is None:
            return float('inf')
        return max(0, self.max_budget - self.spent)
```

**User Controls:**
- `--max-cost 50` - Stop if total cost exceeds $50
- `--cost-per-batch 5` - Process batches up to $5 each
- `--confirm-each` - Approve each batch individually

### 4. Time Control System

**Time Management:**
```python
class TimeController:
    def __init__(self, max_duration_hours: float = None):
        self.max_duration = max_duration_hours
        self.start_time = None
        self.pause_total = 0  # Track pause time

    def should_stop(self) -> bool:
        if self.max_duration is None:
            return False
        elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
        return elapsed >= self.max_duration

    def time_remaining(self) -> float:
        if self.max_duration is None:
            return float('inf')
        elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
        return max(0, self.max_duration - elapsed)
```

**User Controls:**
- `--max-hours 4` - Stop after 4 hours
- `--rate-limit 2` - Requests per second (adjust speed)
- `--pause-every 1000` - Pause for confirmation every N docs
- `--schedule "22:00-06:00"` - Run only during time window

### 5. Stop/Resume Mechanism

**Graceful Shutdown:**
```python
import signal
import sys

class GracefulShutdown:
    def __init__(self, state_manager):
        self.state = state_manager
        self.shutdown_requested = False

        # Register signal handlers
        signal.signal(signal.SIGINT, self.request_shutdown)
        signal.signal(signal.SIGTERM, self.request_shutdown)

    def request_shutdown(self, signum, frame):
        print("\n⚠️  Shutdown requested. Finishing current batch...")
        self.shutdown_requested = True

    def should_continue(self) -> bool:
        return not self.shutdown_requested

    def finalize(self):
        print("💾 Saving progress...")
        self.state.save()
        print("✅ State saved. Run 'make resume' to continue.")
```

**Resume Logic:**
```python
def resume_processing():
    # Load state
    state = StateManager.load()

    if state is None:
        print("No previous session found. Starting fresh.")
        return start_new_session()

    # Show resume info
    print(f"📋 Resuming session: {state.session_id}")
    print(f"   Processed: {state.processed}/{state.total_documents}")
    print(f"   Cost so far: ${state.cost_so_far:.2f}")
    print(f"   Remaining: {state.remaining} documents")
    print(f"   Estimated cost to complete: ${state.estimate_remaining_cost():.2f}")
    print(f"   Estimated time: {state.estimated_time_remaining_minutes} minutes")

    # Confirm resume
    confirm = input("\nContinue processing? (y/n): ")
    if confirm.lower() != 'y':
        return

    # Continue from last position
    continue_from(state)
```

**Checkpointing:**
- Save state every 100 documents
- Create checkpoint files: `data/checkpoints/checkpoint_N.json`
- Keep last 5 checkpoints (rotating buffer)
- Allow resume from specific checkpoint

### 6. Quality Monitoring Dashboard

**Real-Time Metrics:**
```python
class QualityMonitor:
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.confidence_scores = []
        self.low_confidence_docs = []  # overall < 0.75
        self.validation_errors = []

    def record_result(self, doc_name: str, success: bool,
                     confidence: float = None, errors: list = None):
        if success:
            self.success_count += 1
            if confidence:
                self.confidence_scores.append(confidence)
                if confidence < 0.75:
                    self.low_confidence_docs.append({
                        "document": doc_name,
                        "confidence": confidence
                    })
        else:
            self.failure_count += 1
            if errors:
                self.validation_errors.extend(errors)

    def get_dashboard(self) -> dict:
        return {
            "success_rate": self.success_count / (self.success_count + self.failure_count),
            "average_confidence": np.mean(self.confidence_scores),
            "low_confidence_count": len(self.low_confidence_docs),
            "failure_count": self.failure_count,
            "confidence_distribution": {
                "high (≥0.90)": sum(1 for c in self.confidence_scores if c >= 0.90),
                "medium (0.70-0.89)": sum(1 for c in self.confidence_scores if 0.70 <= c < 0.90),
                "low (<0.70)": sum(1 for c in self.confidence_scores if c < 0.70)
            }
        }
```

**Display Updates:**
```
┌─────────────────────────────────────────────────────────────┐
│ 🚀 Full Pass Progress - Session 20241130_153045            │
├─────────────────────────────────────────────────────────────┤
│ Documents:  1,250 / 21,512 (5.8%)  [████░░░░░░░░░░░░░░░░]  │
│ Success:    1,245 / 1,250 (99.6%)                          │
│ Cost:       $1.88 / $32.27 (est)                           │
│ Time:       45 min / 780 min (est)                         │
│ Speed:      27.8 docs/min                                  │
├─────────────────────────────────────────────────────────────┤
│ Quality Metrics:                                           │
│   Avg Confidence:    0.89                                  │
│   High (≥0.90):      723 (57.8%)                           │
│   Medium (0.70-0.89): 435 (34.8%)                          │
│   Low (<0.70):       87 (7.0%) ⚠️                          │
│   Failures:          5 (0.4%)                              │
├─────────────────────────────────────────────────────────────┤
│ Current Batch: 13/216 (100 docs/batch)                    │
│ ETA: 13h 15m (at current rate)                             │
│ [Ctrl+C to pause gracefully]                               │
└─────────────────────────────────────────────────────────────┘
```

### 7. Interim Reporting

**Report Triggers:**
- After each batch completion
- Every 500 documents
- Every hour
- On demand (send signal USR1)

**Report Contents:**
```markdown
# Interim Progress Report - Batch 13

**Session:** 20241130_153045
**Generated:** 2024-11-30 16:45:30
**Prompt Version:** v2

## Progress Summary
- Documents processed: 1,300 / 21,512 (6.0%)
- Success rate: 99.5% (1,294/1,300)
- Cost so far: $1.95
- Time elapsed: 48 minutes
- Processing speed: 27.1 docs/min

## Quality Metrics
- Average confidence: 0.88
- High confidence (≥0.90): 745 docs (57.3%)
- Medium confidence (0.70-0.89): 459 docs (35.3%)
- Low confidence (<0.70): 90 docs (6.9%)
- Validation failures: 6 docs (0.5%)

## Cost Analysis
- Actual cost per doc: $0.0015 (matches estimate)
- Estimated total cost: $32.27
- Estimated remaining cost: $30.32

## Time Projection
- ETA to completion: 13h 10m
- Expected finish: 2024-12-01 05:55:30

## Issues Detected
- 6 validation failures (see `logs/failures_20241130.log`)
- 90 low-confidence docs (see `reports/low_confidence_batch13.json`)

## Recommendations
- ✅ Continue processing (metrics within targets)
- 💡 Consider reviewing low-confidence docs after batch 20
- 💡 Speed is stable, no rate limit issues detected

## Next Batch
- Batch 14: 100 documents
- Estimated cost: $0.15
- Estimated time: 3.7 minutes
```

### 8. Error Handling & Rollback

**Automatic Rollback Triggers:**
```python
class RollbackController:
    def __init__(self):
        self.triggers = {
            "success_rate_below": 0.80,      # <80% success
            "cost_per_doc_above": 0.003,     # >$0.003/doc
            "validation_errors_above": 0.15, # >15% errors
            "avg_confidence_below": 0.70     # <0.70 avg
        }

    def should_rollback(self, metrics: dict) -> tuple[bool, str]:
        if metrics["success_rate"] < self.triggers["success_rate_below"]:
            return True, f"Success rate ({metrics['success_rate']:.1%}) below threshold"

        if metrics["cost_per_doc"] > self.triggers["cost_per_doc_above"]:
            return True, f"Cost per doc (${metrics['cost_per_doc']}) too high"

        if metrics["validation_error_rate"] > self.triggers["validation_errors_above"]:
            return True, f"Validation errors ({metrics['validation_error_rate']:.1%}) too high"

        if metrics["avg_confidence"] < self.triggers["avg_confidence_below"]:
            return True, f"Average confidence ({metrics['avg_confidence']}) too low"

        return False, ""
```

**Rollback Actions:**
1. **Stop processing immediately**
2. **Save current state**
3. **Generate incident report**
4. **Notify user with recommendations**
5. **Option to:**
   - Switch to v1 prompt
   - Adjust batch size
   - Change model
   - Manual review

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
**Goal:** Build batch processing and state management

**Tasks:**
- [ ] Create `BatchProcessor` class
- [ ] Implement `StateManager` with JSON persistence
- [ ] Add graceful shutdown handling (SIGINT/SIGTERM)
- [ ] Build basic progress tracking
- [ ] Test with 100-document batch

**Deliverables:**
- `app/batch_processor.py` - Core batch processing logic
- `app/state_manager.py` - State persistence
- `data/transcription_state.json` - State file schema
- Updated `transcribe.py` to use batch processor

### Phase 2: Control Systems (Week 1)
**Goal:** Add cost, time, and quality controls

**Tasks:**
- [ ] Implement `BudgetController`
- [ ] Implement `TimeController`
- [ ] Build `QualityMonitor` with real-time metrics
- [ ] Create checkpoint system
- [ ] Test stop/resume workflow

**Deliverables:**
- `app/controllers/budget.py`
- `app/controllers/time.py`
- `app/controllers/quality.py`
- `data/checkpoints/` directory
- CLI flags for budget/time limits

### Phase 3: Monitoring & Reporting (Week 1)
**Goal:** Add visibility and reporting

**Tasks:**
- [ ] Build real-time progress dashboard
- [ ] Create interim report generator
- [ ] Add automatic rollback triggers
- [ ] Implement alert system (email/Slack optional)
- [ ] Test full workflow end-to-end

**Deliverables:**
- `app/monitoring/dashboard.py`
- `app/monitoring/reports.py`
- `app/monitoring/rollback.py`
- `reports/` directory for interim reports
- Updated `CLAUDE.md` with full pass documentation

### Phase 4: Testing & Validation (Week 2)
**Goal:** Validate system with real-world batches

**Tasks:**
- [ ] Process 1,000 documents in test mode
- [ ] Validate quality metrics
- [ ] Test all control mechanisms (budget, time, quality)
- [ ] Test stop/resume multiple times
- [ ] Benchmark processing speed

**Success Criteria:**
- ✅ 100% resume capability (no lost progress)
- ✅ Budget controls accurate to within 5%
- ✅ Time estimates accurate to within 10%
- ✅ Quality metrics match small-batch results
- ✅ Graceful shutdown works reliably

### Phase 5: Production Run (Week 2-3)
**Goal:** Process all 21,512 documents

**Strategy:**
- Start with conservative batch size (100)
- Monitor first 1,000 docs closely
- Adjust batch size based on performance
- Run during off-hours if needed
- Review low-confidence docs at milestones

**Milestones:**
- 1,000 docs (5%) - Quality check
- 5,000 docs (25%) - Cost validation
- 10,000 docs (50%) - Midpoint review
- 21,512 docs (100%) - Final report

---

## CLI Interface Design

### New Commands

```bash
# Full pass with interactive confirmation
uv run python -m app.rag.full_pass \
  --batch-size medium \
  --mode interactive

# Full pass with budget limit
uv run python -m app.rag.full_pass \
  --batch-size 500 \
  --max-cost 50 \
  --mode auto

# Full pass with time limit
uv run python -m app.rag.full_pass \
  --batch-size large \
  --max-hours 8

# Resume from last session
uv run python -m app.rag.full_pass --resume

# Resume from specific checkpoint
uv run python -m app.rag.full_pass \
  --resume \
  --checkpoint data/checkpoints/checkpoint_5000.json

# Run during scheduled window
uv run python -m app.rag.full_pass \
  --batch-size large \
  --schedule "22:00-06:00" \
  --mode auto

# Status check (doesn't process, just shows state)
uv run python -m app.rag.full_pass --status

# Generate interim report
uv run python -m app.rag.full_pass --report

# Reset state (start over)
uv run python -m app.rag.full_pass --reset
```

### Make Targets

```makefile
# Full pass with default settings (interactive, medium batch)
full-pass:
	uv run python -m app.rag.full_pass

# Full pass with custom batch size
full-pass-batch:
	uv run python -m app.rag.full_pass --batch-size $(BATCH_SIZE)

# Resume from last session
full-pass-resume:
	uv run python -m app.rag.full_pass --resume

# Check status
full-pass-status:
	uv run python -m app.rag.full_pass --status

# Generate report
full-pass-report:
	uv run python -m app.rag.full_pass --report

# Reset state
full-pass-reset:
	uv run python -m app.rag.full_pass --reset
```

---

## Configuration File

**File:** `.fullpass.config.yaml`

```yaml
# Full Pass Configuration
version: 1.0

# Batch settings
batch:
  default_size: medium  # tiny, small, medium, large, all
  sizes:
    tiny: 10
    small: 100
    medium: 500
    large: 1000

# Budget controls
budget:
  max_total: null       # null = unlimited, or dollar amount
  max_per_batch: null   # null = unlimited
  cost_per_doc: 0.0015  # Estimated cost
  confirm_each: true    # Confirm each batch

# Time controls
time:
  max_hours: null       # null = unlimited
  rate_limit: 2         # Requests per second
  pause_every: null     # Pause after N docs (null = never)
  schedule: null        # "HH:MM-HH:MM" or null

# Quality thresholds
quality:
  min_success_rate: 0.80
  max_cost_per_doc: 0.003
  max_validation_errors: 0.15
  min_avg_confidence: 0.70

# Checkpointing
checkpoints:
  enabled: true
  every_n_docs: 100
  keep_last: 5

# Reporting
reports:
  interim_every_n_docs: 500
  interim_every_n_minutes: 60
  save_to: reports/

# Notifications (optional)
notifications:
  enabled: false
  email: null
  slack_webhook: null

# Rollback
rollback:
  auto_enabled: true
  fallback_to_v1: true

# Logging
logging:
  level: INFO
  save_to: logs/full_pass.log
```

---

## Risk Assessment

### High Risk

**1. API Rate Limits**
- **Risk:** OpenAI may throttle or block if we exceed tier limits
- **Mitigation:** Configurable rate limiting, monitor TPM usage, pause on 429 errors
- **Fallback:** Reduce batch size, increase sleep time

**2. Cost Overrun**
- **Risk:** Actual costs exceed estimates (~$32 → $50+)
- **Mitigation:** Budget controls, cost tracking per doc, abort on threshold
- **Fallback:** Process in smaller batches with manual approval

**3. Quality Degradation**
- **Risk:** v2 performs worse at scale than in small tests
- **Mitigation:** Quality monitoring, automatic rollback triggers
- **Fallback:** Switch to v1 mid-stream, process problematic docs separately

### Medium Risk

**4. Long Processing Time**
- **Risk:** Full pass takes >24 hours, user loses session
- **Mitigation:** Resume capability, checkpointing, time limits
- **Fallback:** Run in tmux/screen, scheduled batches

**5. Disk Space**
- **Risk:** 21,512 JSON files consume significant disk space
- **Mitigation:** Monitor disk usage, compress old checkpoints
- **Estimate:** ~500 MB for all JSONs (acceptable)

**6. Network Interruption**
- **Risk:** Connection loss during batch processing
- **Mitigation:** Retry logic (already exists), save state frequently
- **Fallback:** Resume from last checkpoint

### Low Risk

**7. State Corruption**
- **Risk:** `transcription_state.json` gets corrupted
- **Mitigation:** Validate JSON on load, keep backup checkpoints
- **Fallback:** Resume from last checkpoint

**8. Schema Changes**
- **Risk:** OpenAI modifies Structured Outputs behavior
- **Mitigation:** Pin model version, test before full run
- **Fallback:** Lock to specific model date

---

## Success Metrics

### Completion Criteria

**Must Have:**
- ✅ All 21,512 documents processed
- ✅ Success rate ≥95%
- ✅ Average confidence ≥0.85
- ✅ Total cost within 20% of estimate ($26-$39)
- ✅ No data loss or state corruption

**Should Have:**
- ✅ Processing time <24 hours
- ✅ <5% low-confidence documents (overall <0.70)
- ✅ Validation error rate <2%
- ✅ Successful resume after at least 1 interruption

**Nice to Have:**
- ✅ Processing time <12 hours
- ✅ No rollback events triggered
- ✅ All batches complete on first try
- ✅ Cost exactly matches estimate ($32)

### Quality Benchmarks

Compare to v1 performance (if available):
- Field completion rate (% non-empty fields)
- Keyword consistency (use of taxonomy)
- Date formatting compliance (ISO 8601)
- Name formatting compliance (LAST, FIRST)
- Classification accuracy

---

## Timeline Estimate

### Best Case (No Issues)
- **Setup:** 1 week (Phases 1-3)
- **Testing:** 3 days (Phase 4)
- **Production Run:** 2 days (at 2 RPS = ~3 docs/sec)
- **Total:** ~12 days

### Realistic Case
- **Setup:** 1.5 weeks (with debugging)
- **Testing:** 1 week (multiple test runs)
- **Production Run:** 3-4 days (with pauses, reviews)
- **Total:** ~3 weeks

### Worst Case
- **Setup:** 2 weeks (major issues)
- **Testing:** 1.5 weeks (quality problems)
- **Production Run:** 1 week (multiple rollbacks, manual review)
- **Total:** 4-5 weeks

---

## Cost Breakdown

### Development Costs (Time)
- Infrastructure: 20 hours
- Control systems: 15 hours
- Monitoring: 10 hours
- Testing: 15 hours
- Documentation: 5 hours
- **Total:** ~65 hours (1.5 weeks full-time)

### API Costs
- **Base estimate:** $32 (21,512 × $0.0015)
- **Test runs:** $5-10 (1,000-2,000 docs)
- **Retries/failures:** $2-3 (2% failure rate)
- **Total estimated:** $39-45

### Infrastructure
- Disk space: ~500 MB (negligible)
- Compute: Minimal (rate-limited processing)

---

## Post-Processing Plan

### After Full Pass Completion

**1. Quality Review (Day 1)**
- Generate comprehensive report
- Review all low-confidence documents (overall <0.70)
- Spot-check random sample (100 docs)
- Compare to v1 outputs (if available)

**2. Data Validation (Day 2)**
- Check for duplicates
- Validate all dates are ISO 8601
- Validate all names are "LAST, FIRST"
- Check keyword taxonomy compliance

**3. RAG Index Rebuild (Day 2-3)**
- Clear existing vector database
- Re-index all 21,512 documents
- Test query performance
- Compare answer quality to previous index

**4. Analysis & Visualization (Day 4)**
- Run `make analyze` for HTML report
- Run `make visualize` for charts
- Generate timeline visualization
- Create keyword frequency analysis

**5. Documentation (Day 5)**
- Update `STARTHERE.md` with new stats
- Update `CLAUDE.md` with lessons learned
- Create `FULL_PASS_RESULTS.md` with metrics
- Document any issues encountered

---

## Open Questions

1. **Should we process in random order or sequential?**
   - Random: Better sampling for quality monitoring
   - Sequential: Easier to track progress and debug

2. **How to handle documents that fail multiple times?**
   - Skip and log for manual review?
   - Fallback to v1 prompt?
   - Reduce quality expectations?

3. **Should we parallelize processing?**
   - Current: Sequential with rate limiting
   - Alternative: Multiple workers (more complex state management)

4. **How to handle prompt updates mid-stream?**
   - Lock prompt version for consistency?
   - Allow updates with version tracking?

5. **What to do with existing v1 transcripts?**
   - Keep as backup?
   - Archive and replace?
   - Run comparison analysis?

---

## Next Steps

**Before Implementation:**
1. Review and approve this plan
2. Decide on open questions
3. Set up test environment
4. Allocate budget ($45-50 total)

**To Start:**
1. Create feature branch: `feature/full-pass-processing`
2. Begin Phase 1 implementation
3. Set up monitoring infrastructure
4. Test with 100-document batch

**During Implementation:**
1. Daily progress updates
2. Test each phase independently
3. Document issues and solutions
4. Adjust plan as needed

---

## Appendix: Comparison to Current System

| Feature | Current (`make transcribe-all`) | Proposed Full Pass |
|---------|--------------------------------|-------------------|
| Batch control | ❌ All or nothing | ✅ Configurable batches |
| Cost control | ⚠️ Basic estimate | ✅ Budget limits + tracking |
| Time control | ❌ None | ✅ Time limits + scheduling |
| Stop/Resume | ⚠️ Basic (skip existing) | ✅ Graceful + checkpoints |
| Progress tracking | ❌ Console only | ✅ Real-time dashboard |
| Quality monitoring | ❌ None | ✅ Live metrics |
| Reporting | ❌ None | ✅ Interim + final reports |
| Rollback | ❌ Manual only | ✅ Automatic triggers |
| Error handling | ✅ Retry logic | ✅ Retry + skip + fallback |

---

**Status:** 📋 **PLAN READY FOR REVIEW**
**Next Action:** Approve plan and proceed with Phase 1 implementation
