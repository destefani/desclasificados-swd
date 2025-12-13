# OpenAI Batch API Implementation Plan

## Overview

Add Batch API support to the transcription pipeline to reduce costs by 50% (~$249 savings for remaining ~18k documents).

**Trade-off:**
- Synchronous: ~$498, ~2.5 hours
- Batch API: ~$249, ≤24 hours (often faster)

## Architecture

### Current Flow (Synchronous)
```
PDF → Base64 encode → API call → Parse response → Save JSON
     (parallel workers, real-time)
```

### New Flow (Batch)
```
Phase 1: Prepare
  PDFs → Base64 encode → JSONL batch file → Upload to Files API

Phase 2: Submit
  Create batch job → Poll for completion (background)

Phase 3: Retrieve
  Download results → Match by custom_id → Validate → Save JSONs
```

## Implementation Plan

### Phase 1: Core Batch Module (`app/batch_transcribe.py`)

#### 1.1 Batch Request Builder

```python
@dataclass
class BatchRequest:
    custom_id: str      # PDF filename (without extension)
    method: str = "POST"
    url: str = "/v1/chat/completions"
    body: dict          # Same format as current API calls
```

**Functions:**
- `create_batch_request(pdf_path: Path, model: str) -> BatchRequest`
- `write_batch_file(requests: list[BatchRequest], output_path: Path) -> Path`

#### 1.2 Batch Job Manager

```python
@dataclass
class BatchJob:
    id: str
    status: str         # validating, in_progress, completed, failed, etc.
    input_file_id: str
    output_file_id: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    request_counts: dict  # total, completed, failed
```

**Functions:**
- `upload_batch_file(file_path: Path) -> str`  # Returns file_id
- `create_batch(file_id: str, model: str) -> BatchJob`
- `poll_batch(batch_id: str, interval: int = 60) -> BatchJob`
- `cancel_batch(batch_id: str) -> bool`

#### 1.3 Result Processor

**Functions:**
- `download_results(output_file_id: str) -> Path`
- `parse_results(results_path: Path) -> Iterator[BatchResult]`
- `process_result(result: BatchResult, output_dir: Path) -> str`  # success/failed

### Phase 2: CLI Integration

Add to `app/transcribe.py` or create new `app/batch.py`:

```bash
# Prepare batch (creates JSONL, uploads)
uv run python -m app.batch prepare -n 1000

# Submit batch job
uv run python -m app.batch submit <batch_file_id>

# Check status
uv run python -m app.batch status <batch_id>

# Process results when complete
uv run python -m app.batch retrieve <batch_id>

# One-command workflow
uv run python -m app.batch run -n 1000 --poll
```

### Phase 3: State Management

Track batch jobs in `data/generated_transcripts/<model>/batch_jobs.json`:

```json
{
  "jobs": [
    {
      "batch_id": "batch_abc123",
      "input_file_id": "file_xyz",
      "output_file_id": "file_uvw",
      "status": "completed",
      "created_at": "2025-12-07T10:00:00",
      "completed_at": "2025-12-07T12:30:00",
      "documents": ["doc1.pdf", "doc2.pdf", ...],
      "request_counts": {"total": 1000, "completed": 998, "failed": 2}
    }
  ]
}
```

## File Structure

```
app/
├── transcribe.py          # Existing synchronous (unchanged)
├── batch.py               # NEW: Batch CLI entry point
└── utils/
    └── batch_processor.py # NEW: Core batch logic
```

## API Reference

### Batch Request Format (JSONL)
```json
{
  "custom_id": "DOC_0000024930",
  "method": "POST",
  "url": "/v1/chat/completions",
  "body": {
    "model": "gpt-4.1-mini",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "<PROMPT>"},
          {"type": "file", "file": {"filename": "...", "file_data": "data:application/pdf;base64,..."}}
        ]
      }
    ],
    "response_format": {"type": "json_schema", "json_schema": {...}},
    "max_completion_tokens": 32000
  }
}
```

### Batch Response Format (JSONL)
```json
{
  "id": "batch_req_abc123",
  "custom_id": "DOC_0000024930",
  "response": {
    "status_code": 200,
    "body": {
      "choices": [{"message": {"content": "..."}, "finish_reason": "stop"}],
      "usage": {"prompt_tokens": 1000, "completion_tokens": 500}
    }
  },
  "error": null
}
```

## Testing Plan

### Test 1: Unit Tests
- [ ] `test_create_batch_request()` - Verify JSONL format
- [ ] `test_parse_results()` - Parse mock response
- [ ] `test_match_custom_ids()` - Match results to inputs

### Test 2: Small Batch (5 docs)
```bash
# Prepare batch
uv run python -m app.batch prepare -n 5 --dry-run
uv run python -m app.batch prepare -n 5

# Submit and wait
uv run python -m app.batch run -n 5 --poll

# Verify outputs
ls -la data/generated_transcripts/gpt-4.1-mini/*.json | tail -5
```

**Verify:**
- [ ] JSONL file created correctly
- [ ] File uploaded to OpenAI
- [ ] Batch job created
- [ ] Polling works
- [ ] Results downloaded
- [ ] JSONs match synchronous output format

### Test 3: Medium Batch (100 docs)
```bash
uv run python -m app.batch run -n 100 --poll
```

**Verify:**
- [ ] All 100 documents processed
- [ ] Failures tracked correctly
- [ ] Cost tracking works
- [ ] Resume works if interrupted

### Test 4: Cost Validation
```bash
# Compare costs
uv run python -m app.transcribe --cost-history  # Synchronous
uv run python -m app.batch --cost-history       # Batch
```

**Verify:**
- [ ] Batch costs are ~50% of synchronous

## Error Handling

| Error | Handling |
|-------|----------|
| Upload fails | Retry 3x with backoff |
| Batch creation fails | Log error, cleanup file |
| Batch times out (>24h) | Alert user, option to cancel |
| Partial failure | Process successful, log failures |
| Rate limit on file upload | Respect limits, retry |

## Rollback Plan

If batch processing has issues:
1. Cancel any pending batches: `uv run python -m app.batch cancel --all`
2. Clean up uploaded files
3. Fall back to synchronous: `uv run python -m app.transcribe --yes`

## Cost Estimate

| Docs | Synchronous | Batch | Savings |
|------|-------------|-------|---------|
| 100 | $2.75 | $1.38 | $1.37 |
| 1,000 | $27.50 | $13.75 | $13.75 |
| 18,093 | $498 | $249 | $249 |

## Timeline

1. **Core Implementation** - `batch_processor.py` with prepare/submit/retrieve
2. **CLI Integration** - `batch.py` with commands
3. **Testing** - 5 doc → 100 doc → full run
4. **Documentation** - Update STARTHERE.md, add examples

## Dependencies

Already installed:
- `openai` (latest version supports batch API)
- `tqdm` (progress bars)

No new dependencies required.

## Open Questions

1. **File size limits?** - OpenAI Batch API supports up to 100MB input files
2. **Vision with batch?** - Supported, using base64 inline (same as current)
3. **gpt-5-mini support?** - Need to verify model availability in Batch API
4. **Concurrent batches?** - Multiple batches can run in parallel

## References

- [OpenAI Batch Processing Cookbook](https://cookbook.openai.com/examples/batch_processing)
- [OpenAI Batch API Reference](https://platform.openai.com/docs/api-reference/batch)
- [openbatch Python Library](https://www.daniel-gomm.com/blog/2025/openbatch/)
