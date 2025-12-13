# Investigation 001: Empty reviewed_text in Document 24930

**Date**: 2025-12-07
**Status**: Resolved
**Severity**: Medium (1 document affected out of 1,125)

## Summary

Document 24930.json had an empty `reviewed_text` field while `original_text` contained partial content. This was flagged during quality evaluation of gpt-5-mini transcriptions.

## Findings

### Document Details
- **Document ID**: 24930 (00009517)
- **Title**: ANACONDA STRIKE; POLITICAL SITUATION IN CHILE
- **Date**: 1970-09-00
- **Pages**: 5 (per PDF metadata)
- **Model**: gpt-5-mini

### Issue Analysis
| Field | Length | Expected |
|-------|--------|----------|
| `original_text` | 2,503 chars | ~5,000+ (5 pages) |
| `reviewed_text` | 0 chars | ~5,000+ |
| `page_count` | 5 | 5 (correct) |

The `original_text` only contained transcription of pages 1-2 (partial), ending abruptly mid-sentence:
```
.;0 'II.TY I.
```

### Root Cause

The model returned an **incomplete structured output**. Possible causes:
1. **Token limit hit** - 5-page document may have exceeded output token budget
2. **Structured output truncation** - GPT-5-mini may prioritize metadata over text fields when approaching limits
3. **Model artifact** - Internal issue generating full output

The JSON schema allowed empty `reviewed_text` (no `minLength` constraint), so it passed validation.

### Scope

Checked all 1,125 gpt-5-mini transcripts:
- Only 1 document affected (0.09%)
- All other documents have both `original_text` and `reviewed_text` populated

## Resolution

### Code Fix (transcribe.py)

Added validation to reject incomplete outputs before saving:

```python
# Additional validation: check for empty/incomplete text fields
original_text = response_data.get("original_text", "")
reviewed_text = response_data.get("reviewed_text", "")

# If original_text has content but reviewed_text is empty, this is incomplete
if len(original_text) > 100 and len(reviewed_text) < 50:
    return record_failure(
        f"Incomplete output: original_text has {len(original_text)} chars but reviewed_text is empty/short",
        finish_reason,
        response_text,
    )

# If both text fields are suspiciously short for a multi-page document
page_count = response_data.get("metadata", {}).get("page_count", 1)
min_expected_chars = page_count * 200
if page_count > 1 and len(reviewed_text) < min_expected_chars:
    return record_failure(
        f"Incomplete output: {page_count} pages but only {len(reviewed_text)} chars",
        finish_reason,
        response_text,
    )
```

### Evaluation Enhancement (evaluate.py)

Added `incomplete_transcription` validation issue type with severity "error".

### Remediation for Document 24930

**Option 1**: Delete and re-process
```bash
rm data/generated_transcripts/gpt-5-mini/24930.json
OPENAI_MODEL=gpt-5-mini uv run python -m app.transcribe -n 1 --yes
```

**Option 2**: Keep for manual review (document may have inherent issues)

## Prevention

1. New validation in `transcribe.py` will fail and log documents with incomplete outputs
2. Failed documents go to `failed_documents.json` for retry
3. `app.evaluate validate` now flags `incomplete_transcription` as an error

## Related Files

- `/app/transcribe.py` - Validation fix at line 607-627
- `/app/evaluate.py` - New issue type at line 298-308
- `/data/generated_transcripts/gpt-5-mini/24930.json` - Affected document
