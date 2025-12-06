# Claude API Transcription Implementation Plan

**Created:** 2025-12-03
**Status:** Planning
**Goal:** Use Claude API with Batch processing for document transcription

## Executive Summary

Replace/augment current OpenAI transcription with Claude API, leveraging the **Batch API for 50% cost savings** on processing ~20,000 remaining documents.

## Why Claude?

| Factor | Claude 3.5 Haiku | GPT-4o-mini | Notes |
|--------|------------------|-------------|-------|
| OCR Quality | Excellent | Very Good | Claude handles degraded docs better |
| Structured Output | 99%+ compliance | 95%+ | More reliable JSON |
| Batch Discount | 50% off | None | Key cost advantage |
| Vision | Native | Native | Both support images |

## Cost Analysis

### Per-Document Estimates (Claude 3.5 Haiku)

**Token usage per document:**
- Input: ~2,600 tokens (image ~1,600 + prompt ~1,000)
- Output: ~1,300 tokens

**Pricing (Claude 3.5 Haiku):**
- Standard: $0.80/MTok input, $4.00/MTok output
- Batch (50% off): $0.40/MTok input, $2.00/MTok output

**Per document cost:**
- Standard: $(2,600 × 0.80 + 1,300 × 4.00) / 1,000,000 = $0.0073/doc
- Batch: $(2,600 × 0.40 + 1,300 × 2.00) / 1,000,000 = $0.0036/doc

### Full Pass Cost (20,160 remaining docs)

| Mode | Per Doc | Total Cost |
|------|---------|------------|
| Claude Standard API | $0.0073 | ~$147 |
| **Claude Batch API** | $0.0036 | **~$73** |
| GPT-4o (your actual) | $0.074 | ~$1,490 |

**Batch API saves ~50% vs Standard, and ~95% vs your previous GPT-4o run.**

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Document Processing Flow                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   data/images/           app/transcribe_claude.py               │
│   ┌─────────┐           ┌─────────────────────────┐             │
│   │ *.jpg   │──────────▶│  1. Prepare batch       │             │
│   │ (21,512)│           │  2. Submit to Claude    │             │
│   └─────────┘           │  3. Poll for completion │             │
│                         │  4. Process results     │             │
│                         └───────────┬─────────────┘             │
│                                     │                            │
│                                     ▼                            │
│                         ┌─────────────────────────┐             │
│                         │  data/generated_        │             │
│                         │  transcripts/*.json     │             │
│                         └─────────────────────────┘             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Core Module (app/transcribe_claude.py)

**New file:** `app/transcribe_claude.py`

```python
# Key components:
1. ClaudeTranscriber class
   - __init__(api_key, model, batch_mode)
   - transcribe_single(image_path) -> dict
   - prepare_batch(image_paths) -> list[dict]
   - submit_batch(requests) -> batch_id
   - poll_batch(batch_id) -> status
   - retrieve_results(batch_id) -> dict[str, dict]

2. Cost tracking
   - Track input/output tokens
   - Calculate costs per document
   - Report totals

3. Retry logic
   - Exponential backoff for rate limits
   - Error handling for API failures

4. Validation
   - Reuse existing JSON schema validation
   - Auto-repair functions
```

### Phase 2: Batch Processing Support

**Batch API workflow:**

1. **Prepare requests** - Create JSONL with all documents
2. **Submit batch** - Upload to Claude Batch API
3. **Poll status** - Check every 30-60 seconds
4. **Retrieve results** - Download when complete
5. **Process & save** - Validate and save JSON files

**Batch limits:**
- Max 10,000 requests per batch
- 24-hour processing window
- Results available for 29 days

**Strategy for 20,160 documents:**
- Split into 3 batches (~7,000 each)
- Submit sequentially or parallel
- ~$73 total cost

### Phase 3: CLI Integration

**New commands:**

```bash
# Single document (real-time)
make transcribe-claude FILES_TO_PROCESS=10

# Batch mode (50% discount, async)
make transcribe-claude-batch

# Check batch status
make transcribe-claude-status

# Resume/retry failed
make transcribe-claude-resume
```

### Phase 4: Testing & Validation

1. **Test single document** - Verify API connection
2. **Test small batch** - 10-50 documents
3. **Compare quality** - Claude vs existing OpenAI transcripts
4. **Full pass** - Process remaining 20,160 documents

## File Structure

```
app/
├── transcribe.py           # Existing OpenAI (keep as fallback)
├── transcribe_claude.py    # NEW: Claude implementation
├── transcribe_v2.py        # Legacy (can deprecate)
├── batch_processor.py      # Existing batch logic (reuse)
└── prompts/
    ├── metadata_prompt_v2.md    # Works with both OpenAI & Claude
    └── schemas/
        └── metadata_schema.json  # Shared schema
```

## Configuration

### Environment Variables (.env)

```bash
# Existing
ANTHROPIC_API_KEY=sk-ant-...

# New options
CLAUDE_TRANSCRIPTION_MODEL=claude-3-5-haiku-20241022
CLAUDE_BATCH_MODE=true
CLAUDE_MAX_BATCH_SIZE=7000
```

### Model Options

| Model | Speed | Cost | Quality | Recommended For |
|-------|-------|------|---------|-----------------|
| claude-3-5-haiku-20241022 | Fast | Low | Good | **Default - bulk processing** |
| claude-3-5-sonnet-20241022 | Medium | High | Excellent | Difficult documents |

## Implementation Steps

### Step 1: Create transcribe_claude.py (~2 hours)

- [ ] Basic structure with ClaudeTranscriber class
- [ ] Single document transcription
- [ ] Token/cost tracking
- [ ] Reuse existing validation logic

### Step 2: Add Batch API Support (~2 hours)

- [ ] Batch request preparation
- [ ] Batch submission
- [ ] Status polling
- [ ] Result retrieval and processing

### Step 3: CLI & Makefile (~1 hour)

- [ ] Add argparse options
- [ ] Create Makefile targets
- [ ] Update .env.example

### Step 4: Testing (~2 hours)

- [ ] Test single document
- [ ] Test batch of 50
- [ ] Quality comparison
- [ ] Cost verification

### Step 5: Documentation (~30 min)

- [ ] Update STARTHERE.md
- [ ] Update CLAUDE.md
- [ ] Document cost estimates

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Batch API fails | Implement single-doc fallback |
| Rate limits | Exponential backoff, respect limits |
| Quality issues | Compare 100 docs before full pass |
| Cost overrun | Set budget limits, confirm before batch |

## Success Criteria

1. ✅ Process 50 documents successfully
2. ✅ Quality >= existing OpenAI transcripts
3. ✅ Cost within $100 for full pass
4. ✅ Batch API working with 50% discount
5. ✅ Resume capability for interrupted batches

## Next Steps

1. **Approve this plan**
2. **Start Phase 1** - Create `transcribe_claude.py`
3. **Test with 10 documents** - Verify everything works
4. **Scale to full batch** - Process remaining ~20,000 docs

---

## Appendix: API Reference

### Claude Messages API (Vision)

```python
from anthropic import Anthropic

client = Anthropic(api_key="...")

message = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64_image_data,
                },
            },
            {
                "type": "text",
                "text": prompt
            }
        ],
    }],
)
```

### Claude Batch API

```python
# Submit batch
batch = client.batches.create(requests=[...])

# Check status
batch = client.batches.retrieve(batch_id)

# Get results
for result in client.batches.results(batch_id):
    if result.result.type == "succeeded":
        process(result)
```

### Token Calculation for Images

```python
# Estimate tokens for image
def estimate_image_tokens(width: int, height: int) -> int:
    return (width * height) // 750

# Standard document image (~1200x1600) = ~2,560 tokens
```
