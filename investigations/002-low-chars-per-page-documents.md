# Investigation 002: Documents with Low Characters Per Page Ratio

**Date**: 2025-12-07
**Status**: Resolved
**Severity**: Low (false positive - documents are not truncated)

## Summary

After fixing the empty `reviewed_text` issue in document 24930 (Investigation 001), we analyzed all transcripts to identify potentially truncated documents using a chars/page ratio metric. 17 documents were flagged with <200 chars/page, but investigation revealed these are **not truncated** - they are genuinely massive legal documents with sparse readable content.

## Findings

### Flagged Documents (17 total)

| doc_id | pages | reviewed_chars | chars/page | document_type |
|--------|-------|----------------|------------|---------------|
| 25816 | 229 | 18,052 | 79 | Extradition case file |
| 25573 | 76 | 6,041 | 79 | Visa/court documents |
| 25788 | 101 | 9,191 | 91 | Rotated scans, low contrast |
| 25044 | 235 | 22,161 | 94 | Extradition file, passport copies |
| 25798 | 65 | 6,549 | 101 | Spanish memo, poor scan |
| 25680 | 77 | 8,207 | 107 | Multi-page legal file |
| 25674 | 52 | 5,652 | 109 | Court documents |
| 25747 | 89 | 10,099 | 113 | Legal proceedings |
| 25709 | 59 | 7,043 | 119 | Mixed documents |
| 25730 | 113 | 13,679 | 121 | Large compilation |
| 25666 | 70 | 8,744 | 125 | Court records |
| 25731 | 51 | 6,580 | 129 | Legal bundle |
| 25045 | 69 | 9,056 | 131 | Case file |
| 25760 | 84 | 11,431 | 136 | Extradition documents |
| 25715 | 51 | 7,066 | 139 | Court proceedings |
| 25755 | 54 | 8,018 | 148 | Legal file |
| 25725 | 59 | 9,387 | 159 | Mixed documents |

### Root Cause Analysis

These documents are **NOT truncated**. The low chars/page ratio is explained by:

1. **Document Type**: Large court files and extradition cases (50-235 pages)
2. **Content Nature**:
   - Many pages are forms with mostly blank space
   - Passport photocopies with minimal text
   - Hospital records and certificates
   - Signature pages and stamps
   - Cover sheets and filing labels
3. **Scan Quality Issues**:
   - Rotated pages (noted in observations)
   - Low contrast and faded text
   - Handwritten annotations illegible to OCR
   - Mixed language (Spanish/English) with varying quality

### Evidence from Transcript Analysis

Example from document 25044 (235 pages, 94 chars/page):
- `document_type`: "EXTRADITION FILE"
- `document_description`: "Compilation of Chilean Justice Ministry extradition-related materials including Chilean passports, hospital records, cables, requests..."
- `observations`: "Includes Chilean passport photocopies...hospital records... Many sections have poor scan quality..."
- `confidence`: 0.6 (model correctly noted difficulty)

Example from document 25816 (229 pages, 79 chars/page):
- `document_type`: "EXTRADITION CASE FILE"
- `language`: "SPANISH"
- `observations`: "Document is a large case file with many pages of poor scan quality..."
- The model correctly identified it as a Spanish-language court document

### Comparison with True Truncation (Investigation 001)

| Issue | 001 (Truncated) | 002 (Not Truncated) |
|-------|-----------------|---------------------|
| `reviewed_text` | **Empty (0 chars)** | Has content (6k-22k chars) |
| `original_text` | Partial, cut mid-sentence | Complete with page markers |
| Confidence | 0.82 (reasonable) | 0.4-0.7 (low - model noted issues) |
| Page markers | Missing pages 3-5 | All pages present ("Page X / Y") |

## Resolution

### No Code Fix Needed

The transcription system is working correctly. These documents:
- Have all pages identified in `original_text`
- Have appropriate `reviewed_text` given content quality
- Have lower confidence scores (model correctly flagged difficulty)
- Have detailed `observations` noting scan quality issues

### Recommendation

1. **Accept as-is**: The model extracted what was readable
2. **Optional manual review**: For historically critical documents, flag these 17 for human review
3. **No re-processing needed**: Re-running would produce same results

## Prevention

The validation added in Investigation 001 correctly handles actual truncation:
- Catches empty `reviewed_text` when `original_text` has content
- The chars/page metric is **not a reliable truncation indicator** for legal/court documents

## Metrics for Future Reference

For typical CIA documents (memos, cables, reports):
- Average: 400-800 chars/page
- Minimum safe threshold: 200 chars/page

For court files and legal compilations:
- Can be as low as 50-100 chars/page (legitimately)
- Low confidence score is expected

## Related Files

- All 17 documents in `/data/generated_transcripts/gpt-5-mini/`
- Investigation 001: `/investigations/001-empty-reviewed-text.md`
