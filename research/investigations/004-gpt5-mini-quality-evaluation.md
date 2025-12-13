# Investigation 004: GPT-5-mini Transcription Quality Evaluation

**Date**: 2025-12-13
**Status**: Complete
**Severity**: Low (overall quality is good)

## Summary

Comprehensive quality evaluation of 5,666 documents transcribed with `gpt-5-mini` model. Overall quality is excellent with 82.7% high confidence scores and zero errors in validation.

## Overall Statistics

### Transcription Progress

| Metric | Value | Percentage |
|--------|-------|------------|
| Total Documents in Corpus | 21,512 | 100% |
| Transcribed (gpt-5-mini) | 5,666 | 26.3% |
| Remaining | 15,846 | 73.7% |

### Confidence Scores

| Metric | Value |
|--------|-------|
| **Mean** | 0.877 |
| **Median** | 0.880 |
| **Std Dev** | 0.045 |
| **Min** | 0.580 |
| **Max** | 0.960 |

### Confidence Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| **High (>0.85)** | 4,688 | 82.7% |
| **Medium (0.70-0.85)** | 965 | 17.0% |
| **Low (<0.70)** | 13 | 0.2% |

## Validation Results

### Issue Summary

| Severity | Count |
|----------|-------|
| **Errors** | 0 |
| **Warnings** | 13 |
| **Info** | 450 |

**Total Issues: 463**

### Issues by Type

| Issue Type | Count | Severity |
|------------|-------|----------|
| `missing_date` | 443 | Info |
| `low_confidence` | 13 | Warning |
| `text_page_mismatch` | 7 | Info |

### Low Confidence Documents (13)

| Document | Confidence |
|----------|------------|
| 25022 | 0.60 |
| 25027 | 0.65 |
| 25288 | 0.65 |
| 25289 | 0.68 |
| 25323 | 0.62 |
| 26873 | 0.58 |
| 27292 | 0.68 |
| 28834 | 0.68 |
| 29411 | 0.65 |
| 29565 | 0.65 |
| 29566 | - |
| 29750 | - |
| 29891 | - |

## Metadata Completeness

| Field | Missing | Percentage |
|-------|---------|------------|
| Document Date | 443 | 7.8% |
| Author | 1,187 | 20.9% |
| Document Type | 56 | 1.0% |
| Empty/Short Text | 0 | 0.0% |

## Document Distribution

### By Document Type

| Type | Count | Percentage |
|------|-------|------------|
| CABLE | 1,661 | 29.3% |
| MEMORANDUM | 1,470 | 25.9% |
| LETTER | 1,204 | 21.3% |
| TELEGRAM | 815 | 14.4% |
| REPORT | 352 | 6.2% |
| INTELLIGENCE BRIEF | 57 | 1.0% |
| UNKNOWN | 56 | 1.0% |
| MEETING MINUTES | 51 | 0.9% |

### By Classification Level

| Level | Count | Percentage |
|-------|-------|------------|
| UNCLASSIFIED | 2,741 | 48.4% |
| CONFIDENTIAL | 1,733 | 30.6% |
| UNKNOWN | 675 | 11.9% |
| SECRET | 511 | 9.0% |
| TOP SECRET | 6 | 0.1% |

### By Page Count

| Pages | Count | Notes |
|-------|-------|-------|
| 1 | 1,763 | 31.1% |
| 2 | 1,652 | 29.2% |
| 3 | 783 | 13.8% |
| 4-10 | 1,242 | 21.9% |
| 11-30 | 177 | 3.1% |
| 31-100 | 15 | 0.3% |
| 100+ | 7 | 0.1% (including 229p and 235p docs) |

## Common Concerns

| Category | Count | Description |
|----------|-------|-------------|
| OCR/Scan Quality | 11,053 | Poor scan quality, artifacts |
| Other | 5,288 | Various minor issues |
| Name/Author Issues | 4,453 | Unclear or incomplete names |
| Illegible Text | 2,976 | Portions unreadable |
| Date Issues | 2,138 | Missing or unclear dates |
| Classification Issues | 1,165 | Unclear classification markings |
| Redactions | 197 | Redacted content noted |

## Failed Documents

### Summary

| Status | Count |
|--------|-------|
| Previously Failed | 150 |
| Now Successfully Transcribed | 136 |
| **Still Missing** | **14** |

### Documents Still Missing (14)

| Document | Reason | Notes |
|----------|--------|-------|
| 25967 | Content filtered | OpenAI moderation |
| 26144 | Incomplete output | 12 pages, only 1369 chars |
| 26811 | Content filtered | OpenAI moderation |
| 27854 | Incomplete output | 2 pages, only 224 chars |
| 28107 | Content filtered | OpenAI moderation |
| 28561 | Content filtered | OpenAI moderation |
| 28722 | Incomplete output | 21 pages, only 2823 chars |
| 28926 | Incomplete output | 17 pages, only 2314 chars |
| 29375 | Incomplete output | 11 pages, only 1526 chars |
| 29761 | Incomplete output | 12 pages, only 1342 chars |
| 29919 | Response truncated | max_tokens reached |
| 29974 | Content filtered | OpenAI moderation |
| 30110 | Content filtered | OpenAI moderation |
| 30267 | Content filtered | OpenAI moderation |

**Content Filtered**: 7 documents (OpenAI's moderation flagged content)
**Incomplete Output**: 6 documents (insufficient text generated)
**Truncated**: 1 document (max tokens exceeded)

## Key Findings

### Strengths

1. **Excellent Confidence Scores**: 82.7% of documents have high confidence (>0.85)
2. **Zero Validation Errors**: No schema violations or critical issues
3. **Good Recovery Rate**: 136 of 150 previously failed documents now transcribed
4. **Complete Text**: 0% empty or short text (vs previous issues)
5. **Strong Document Type Coverage**: 99% have valid document types

### Areas for Improvement

1. **Missing Dates**: 7.8% of documents lack dates (expected for some historical docs)
2. **Missing Authors**: 20.9% lack author information (common in government cables)
3. **OCR Quality Concerns**: Most common concern category (11,053 mentions)
4. **14 Persistently Failing Documents**: Content moderation and output issues

## Recommendations

### Immediate Actions

1. **Manually review 13 low-confidence documents** for transcription quality
2. **Investigate 14 missing documents**:
   - Content-filtered (7): May require alternate model or manual transcription
   - Incomplete output (6): Retry with chunked processing
   - Truncated (1): Retry with larger max_tokens

### Long-term Improvements

1. **Continue processing remaining 15,846 documents** to reach full coverage
2. **Consider Claude for content-filtered documents** (different moderation policy)
3. **Implement quality-based re-transcription** for low-confidence documents

## Technical Notes

### Bug Fix Applied

Fixed `app/evaluate.py` to exclude non-transcript JSON files:
- `failed_documents.json` (list type, not transcript)
- `incomplete_documents.json`
- `processing_state.json`

### Commands Used

```bash
# Statistics
make eval-stats MODEL=gpt-5-mini

# Validation
make eval-validate MODEL=gpt-5-mini

# Full report
make eval-report MODEL=gpt-5-mini
```

## Related Files

- `data/generated_transcripts/gpt-5-mini/` - 5,666 transcripts
- `data/generated_transcripts/gpt-5-mini/failed_documents.json` - Failure log
- `app/evaluate.py` - Evaluation CLI (updated)
- `docs/QUALITY_TESTING_METHODS.md` - Testing documentation

---

*Evaluation performed: 2025-12-13*
