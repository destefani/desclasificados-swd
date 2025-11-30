# Prompt v2 Implementation Guide

## Overview

Prompt v2 introduces significant improvements over v1:
- ✅ **Structured Outputs** with strict JSON schema enforcement (100% reliability)
- ✅ **Confidence scoring** for quality control
- ✅ **Enhanced field guidance** for more complete metadata extraction
- ✅ **Keyword taxonomy** for consistent categorization
- ✅ **Few-shot examples** for better edge case handling
- ✅ **Versioning** for tracking and rollback

## Quick Start

### Using v2 (Default)

```bash
# v2 is enabled by default
make transcribe-some FILES_TO_PROCESS=5
```

### Using v1 (Fallback)

```bash
# Set environment variable to use old prompt
export PROMPT_VERSION=v1
make transcribe-some FILES_TO_PROCESS=5
```

### Disabling Structured Outputs

```bash
# Use v2 prompt but without strict schema (not recommended)
export USE_STRUCTURED_OUTPUTS=false
make transcribe-some FILES_TO_PROCESS=5
```

## Configuration Options

### Environment Variables

Add to your `.env` file:

```bash
# Prompt version selection (v1 or v2)
PROMPT_VERSION=v2

# Enable/disable Structured Outputs (true or false)
USE_STRUCTURED_OUTPUTS=true

# Model selection (must support Structured Outputs for v2)
OPENAI_MODEL=gpt-4o-2024-08-06
# or
OPENAI_MODEL=gpt-4o-mini-2024-07-18
```

### Required Models for Structured Outputs

Structured Outputs requires these models:
- ✅ `gpt-4o-2024-08-06` (recommended)
- ✅ `gpt-4o-mini-2024-07-18` (cost-effective)
- ❌ `gpt-4o` (older versions - not compatible)
- ❌ `gpt-4-vision-preview` (not compatible)

## What's New in v2

### 1. Strict JSON Schema Validation

**Before (v1):**
```python
response_format={"type": "json_object"}
# Model tries to follow JSON, but may deviate
# Requires auto-repair for ~10-15% of outputs
```

**After (v2):**
```python
response_format={
    "type": "json_schema",
    "json_schema": {
        "schema": {...},
        "strict": True
    }
}
# Model MUST follow schema exactly
# Auto-repair needed <2% of time
```

### 2. Confidence Scoring

New `confidence` object in output:

```json
{
  "metadata": {...},
  "original_text": "...",
  "reviewed_text": "...",
  "confidence": {
    "overall": 0.85,
    "fields": {
      "document_date": 0.95,
      "author": 0.70
    },
    "concerns": [
      "Author name partially obscured by stamp"
    ]
  }
}
```

**Use cases:**
- Flag documents with overall < 0.75 for human review
- Track which fields are frequently low-confidence
- Prioritize high-confidence docs for immediate use

### 3. Enhanced Field Extraction

**Improved guidance for:**
- `document_id`: Where to look (corners, footers, stamps)
- `case_number`: Common formats (C5199900030)
- `archive_location`: How to extract from stamps
- `declassification_date`: Distinguish from document_date

**Expected improvement:** 30-50% reduction in empty fields

### 4. Keyword Taxonomy

**Before (v1):**
```markdown
Keywords: Always uppercase, short tags
Examples: "HUMAN RIGHTS", "OPERATION CONDOR"
```

**After (v2):**
```markdown
Extract 3-10 keywords from these categories:
- Political: ELECTIONS, POLITICAL PARTIES, COUP
- Intelligence: OPERATION CONDOR, CIA FUNDING
- Human Rights: REPRESSION, TORTURE
- US-Chile Relations: DIPLOMACY, FOREIGN POLICY
[... 9 categories total]
```

**Result:** More consistent, research-relevant keywords

### 5. Few-Shot Examples

Located in `app/prompts/examples/`:
- `example_01_clean_typed.md` - Standard case
- `example_02_heavily_redacted.md` - Redactions handling
- `example_03_handwritten.md` - Illegibility markers

**Note:** Examples not automatically included in prompt yet (Phase 3 feature). Currently serve as test cases and documentation.

## Performance Comparison

| Metric | v1 (Baseline) | v2 (Target) | Improvement |
|--------|---------------|-------------|-------------|
| Success rate | 85-90% | 95-98% | +8-10% |
| Auto-repair usage | 10-15% | <2% | -80-90% |
| Field completion | 50-65% | 70-85% | +30-50% |
| Cost per document | $0.00086 | $0.00070 | -19% |
| Confidence scoring | None | Full | ✅ New |

**Cost reduction** comes from:
- 50% cheaper input tokens (gpt-4o-2024-08-06 vs older)
- More efficient prompt (less redundancy)
- Fewer retries needed (schema enforcement)

## Testing & Validation

### Test v2 on Sample Documents

```bash
# Process 10 documents with v2
make transcribe-some FILES_TO_PROCESS=10

# Check output quality
ls -lh data/generated_transcripts/
```

### Compare v1 vs v2

```bash
# Backup existing transcripts
mv data/generated_transcripts data/generated_transcripts_v2

# Process same files with v1
export PROMPT_VERSION=v1
make transcribe-some FILES_TO_PROCESS=10

# Compare outputs
diff -u data/generated_transcripts_v1/24736.json \
        data/generated_transcripts_v2/24736.json
```

### Validation Checks

After processing, verify:
- ✅ All outputs have `confidence` object
- ✅ Dates in YYYY-MM-DD format (or 0000-00-00)
- ✅ Names in "LAST, FIRST" format
- ✅ Keywords are uppercase
- ✅ No JSON parsing errors
- ✅ Field completion improved

## Troubleshooting

### Error: "Model does not support Structured Outputs"

**Problem:** Using incompatible model

**Solution:**
```bash
# Update .env
OPENAI_MODEL=gpt-4o-2024-08-06
```

### Error: "Failed to load schema file"

**Problem:** Schema file missing or corrupt

**Solution:**
```bash
# Verify schema exists
ls app/prompts/schemas/metadata_schema.json

# Re-download or recreate if needed
git checkout app/prompts/schemas/metadata_schema.json
```

### High Failure Rate (>10%)

**Problem:** Model or prompt incompatibility

**Solution:**
```bash
# Fallback to v1
export PROMPT_VERSION=v1

# Or disable Structured Outputs
export USE_STRUCTURED_OUTPUTS=false
```

### Low Confidence Scores

**Problem:** Poor quality scans or complex documents

**Expected:** This is normal for difficult documents

**Action:**
- Review flagged documents manually
- Consider creating specialized prompt variant (Phase 3)
- Improve scan quality if possible

## Rollback Plan

If v2 causes issues:

**Option 1: Quick rollback to v1**
```bash
export PROMPT_VERSION=v1
# All new transcriptions use old prompt
```

**Option 2: Disable Structured Outputs only**
```bash
export USE_STRUCTURED_OUTPUTS=false
# Uses v2 prompt but without strict schema
```

**Option 3: Git revert**
```bash
git checkout feature/add-cost-estimation -- app/prompts/metadata_prompt.md
# Restore original v1 prompt
```

## Migration Notes

### Existing Transcripts

**v1 transcripts** (without confidence scoring):
- Still valid and usable
- Compatible with analysis tools
- No need to re-process

**Mixed v1/v2 corpus:**
- Analysis tools should handle both formats
- Check for `confidence` object existence before using
- Consider re-processing important documents with v2

### Schema Updates

If you modify `metadata_schema.json`:
1. Update schema file
2. Update prompt v2 to match
3. Test on 10-20 documents
4. Roll out gradually (25% → 75% → 100%)
5. Document changes in prompt header `changelog`

## Next Steps

### Phase 1 Complete ✅
- Structured Outputs implementation
- Confidence scoring
- Enhanced field guidance
- Keyword taxonomy

### Phase 2 (Optional)
- Integrate few-shot examples into prompt
- Create prompt variants (fast, standard, detailed)
- Build human-review queue for low-confidence docs

### Phase 3 (Future)
- Automated prompt testing framework
- A/B testing infrastructure
- Cross-reference extraction
- Multi-language improvements

## Support

**Questions?** Check:
- `PROMPT_IMPROVEMENT_PLAN.md` - Full improvement plan
- `PROMPT_MANAGEMENT_RESEARCH.md` - Research findings
- `app/prompts/examples/` - Example outputs

**Issues?** Report:
- Document error patterns
- Share problematic document IDs
- Include confidence scores and error messages

---

**Last Updated:** 2024-11-30
**Version:** 2.0.0
**Status:** Production Ready
