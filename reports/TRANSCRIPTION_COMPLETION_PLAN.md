# Transcription Completion Plan: GPT-4.1-Mini

**Date:** 2025-12-07
**Goal:** Complete transcription of all 21,512 documents using gpt-4.1-mini
**Status:** 22.9% complete (4,924 of 21,512 documents)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Documents** | 21,512 |
| **Already Transcribed** | 4,924 (22.9%) |
| **Remaining** | 16,588 (77.1%) |
| **Estimated Cost** | ~$60 |
| **Estimated Time** | ~2.5 hours |
| **Model** | gpt-4.1-mini |

---

## Current Status

### Transcription by Model

| Model | Documents | Notes |
|-------|-----------|-------|
| gpt-4.1-mini | 4,924 | **Primary model** |
| chatgpt-5-1 | 1,352 | Legacy |
| claude-3-5-haiku-20241022 | 122 | Testing |
| gpt-4.1-nano | 5 | Testing |
| claude-sonnet-4-5-20250929 | 2 | Testing |

**Target:** Complete all remaining documents with gpt-4.1-mini for consistency.

### Documents Requiring Transcription

The remaining 16,588 documents have not yet been processed with gpt-4.1-mini. The transcription script uses resume mode to skip already-transcribed files.

---

## Cost Analysis

### GPT-4.1-Mini Pricing

| Token Type | Price |
|-----------|-------|
| Input | $0.40 / 1M tokens |
| Output | $1.60 / 1M tokens |

### Cost Breakdown

| Item | Estimate |
|------|----------|
| Est. input tokens per doc | ~3,000 |
| Est. output tokens per doc | ~1,500 |
| Total input tokens (16,588 docs) | ~49.8M |
| Total output tokens (16,588 docs) | ~24.9M |
| **Input cost** | ~$19.91 |
| **Output cost** | ~$39.81 |
| **TOTAL COST** | **~$59.72** |
| Cost per document | ~$0.0036 |

### Budget Recommendation

Set a budget limit of **$75** to account for:
- Retries on failed documents
- Token variation between documents
- Safety margin

---

## Time Analysis

### Processing Rate

| Metric | Value |
|--------|-------|
| API rate limit | 2 requests/second |
| Effective throughput | ~120 docs/minute |
| Total estimated time | ~2.3 hours |

### Realistic Timeline

With pauses, monitoring, and potential retries:
- **Optimistic:** 2.5 hours
- **Realistic:** 3-4 hours
- **Conservative:** 5-6 hours (with batch confirmations)

---

## Execution Plan

### Prerequisites

1. **Set environment variable:**
   ```bash
   # In .env file
   OPENAI_MODEL=gpt-4.1-mini
   ```

2. **Verify API key has sufficient credits:**
   - Estimated cost: ~$60
   - Recommended buffer: $75-100

3. **Check disk space:**
   - ~500KB per transcript
   - Total: ~8GB for all 21,512 transcripts (already have ~2.5GB)

### Option A: Single Run (Fastest)

For uninterrupted processing of all remaining documents:

```bash
# Set the model
export OPENAI_MODEL=gpt-4.1-mini

# Run with resume (skips existing transcripts)
make resume
```

**Pros:** Simple, fastest completion
**Cons:** No batch confirmation, harder to monitor

### Option B: Batch Processing (Recommended)

Use the full-pass system for better control:

```bash
# Interactive mode - confirm each batch
make full-pass BATCH_SIZE=large

# Auto mode with budget limit
make full-pass-auto BATCH_SIZE=large MAX_COST=75
```

**Pros:** Cost control, progress monitoring, graceful shutdown
**Cons:** Slightly slower due to batch confirmations

### Option C: Incremental Batches (Conservative)

Process in smaller batches with confirmation:

```bash
# First batch: 1,000 documents (~$3.60)
make transcribe-some FILES_TO_PROCESS=1000

# After reviewing results, continue with larger batches
make resume-some FILES_TO_PROCESS=5000
```

**Pros:** Early quality validation, fine control
**Cons:** Requires multiple manual interventions

---

## Recommended Approach

### Phase 1: Validation (1,000 docs, ~$3.60)

Before committing to full processing:

```bash
export OPENAI_MODEL=gpt-4.1-mini
make transcribe-some FILES_TO_PROCESS=1000
```

After completion:
1. Verify output quality
2. Check cost matches estimate
3. Review any failures

### Phase 2: Full Processing (15,588 remaining, ~$56)

If Phase 1 is successful:

```bash
# Option A: Auto mode with budget
make full-pass-auto BATCH_SIZE=large MAX_COST=75

# Option B: Resume mode
make resume
```

### Phase 3: Post-Processing

After all documents are transcribed:

```bash
# 1. Verify completion
ls data/generated_transcripts/gpt-4.1-mini/ | wc -l
# Should be 21,512

# 2. Update RAG index
uv run python -m app.rag.cli build --reset

# 3. Generate analysis report
make analyze
```

---

## Monitoring

### During Processing

1. **Terminal output:** Shows progress bar and success rate
2. **Cost tracking:** Displayed after each batch/run
3. **Log file:** `logs/transcribe.log` (if enabled)

### Key Metrics to Watch

| Metric | Target | Action if Off |
|--------|--------|---------------|
| Success rate | >98% | Check API errors |
| Cost per doc | ~$0.0036 | Review if >$0.005 |
| Processing rate | ~120/min | Check rate limits |
| Confidence score | >0.80 avg | Flag low-confidence docs |

### Abort Conditions

Stop processing if:
- Success rate drops below 90%
- Cost per document exceeds $0.01
- API returns consistent errors

---

## Risk Mitigation

### API Rate Limits

**Risk:** OpenAI throttles requests
**Mitigation:** Built-in rate limiting (2 RPS, 150k TPM)
**Recovery:** Script automatically retries with backoff

### Network Interruption

**Risk:** Connection lost mid-processing
**Mitigation:** Resume mode skips completed files
**Recovery:** Simply re-run `make resume`

### Cost Overrun

**Risk:** Actual costs exceed estimate
**Mitigation:** Use `--max-cost` flag with full-pass
**Recovery:** Pause and reassess

### Quality Issues

**Risk:** Model produces poor transcriptions
**Mitigation:** Confidence scoring in Prompt v2
**Recovery:** Review low-confidence documents manually

---

## Quick Start Commands

```bash
# 1. Update .env to use gpt-4.1-mini
echo "OPENAI_MODEL=gpt-4.1-mini" >> .env

# 2. Test with small batch first (recommended)
make transcribe-some FILES_TO_PROCESS=100

# 3. If successful, run full completion
make resume

# 4. After completion, verify count
ls data/generated_transcripts/gpt-4.1-mini/ | wc -l

# 5. Update RAG index
uv run python -m app.rag.cli build --reset
```

---

## Checklist

- [ ] Verify OPENAI_API_KEY is valid
- [ ] Set OPENAI_MODEL=gpt-4.1-mini in .env
- [ ] Confirm ~$75 budget available
- [ ] Run validation batch (100-1000 docs)
- [ ] Review validation results
- [ ] Execute full transcription
- [ ] Verify all 21,512 documents transcribed
- [ ] Rebuild RAG index
- [ ] Update STARTHERE.md with new status

---

## Summary

To complete the transcription of all documents with gpt-4.1-mini:

1. **Cost:** ~$60 (budget $75 for safety)
2. **Time:** ~2.5-4 hours
3. **Command:** `OPENAI_MODEL=gpt-4.1-mini make resume`
4. **Post-processing:** Rebuild RAG index, update documentation

The existing infrastructure (rate limiting, resume capability, cost tracking) is production-ready. No code changes required.
