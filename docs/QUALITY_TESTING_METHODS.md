# Quality Testing Methods for Document Transcription

This document provides a comprehensive guide to all quality testing methods available for evaluating document transcription quality in the desclasificados project.

---

## Quick Reference

| Method | Command | Purpose |
|--------|---------|---------|
| Statistics | `make eval-stats MODEL=gpt-5-mini` | View confidence scores, metadata completeness |
| Validation | `make eval-validate MODEL=gpt-5-mini` | Find errors and warnings |
| Sampling | `make eval-sample MODEL=gpt-5-mini` | Generate sample for manual review |
| HTML Report | `make eval-report MODEL=gpt-5-mini` | Full visual quality report |
| Unit Tests | `uv run pytest tests/unit/ -v` | Test code correctness |

---

## 1. Evaluation CLI (`app/evaluate.py`)

The primary quality evaluation tool with four commands:

### 1.1 Statistics Command

Shows comprehensive statistics for transcription quality.

```bash
# Via Makefile
make eval-stats MODEL=gpt-5-mini

# Direct CLI
uv run python -m app.evaluate stats gpt-5-mini
```

**Metrics Provided:**

| Category | Metrics |
|----------|---------|
| **Confidence Scores** | Mean, Median, Std, Min, Max |
| **Confidence Distribution** | High (>0.85), Medium (0.70-0.85), Low (<0.70) |
| **Metadata Completeness** | Missing date, author, doc type, empty text |
| **Document Types** | Distribution (MEMORANDUM, CABLE, REPORT, etc.) |
| **Classification Levels** | TOP SECRET, SECRET, CONFIDENTIAL, UNCLASSIFIED |
| **Page Count Distribution** | Documents per page count |
| **Common Concerns** | OCR quality, illegibility, redactions, etc. |

**Example Output:**
```
================================================================================
TRANSCRIPT QUALITY STATISTICS
================================================================================

Total Documents: 1,125

--- Confidence Scores ---
  Mean:   0.861
  Median: 0.880
  Std:    0.072
  Min:    0.500
  Max:    0.950

--- Confidence Distribution ---
  High (>0.85):       807 (71.7%)
  Medium (0.70-0.85): 314 (27.9%)
  Low (<0.70):          4 ( 0.4%)
```

### 1.2 Validation Command

Runs automated validation checks against schema and business rules.

```bash
# Via Makefile
make eval-validate MODEL=gpt-5-mini

# Direct CLI
uv run python -m app.evaluate validate gpt-5-mini

# Save issues to JSON
uv run python -m app.evaluate validate gpt-5-mini --output issues.json
```

**Validation Checks:**

| Check | Severity | Description |
|-------|----------|-------------|
| `low_confidence` | Warning | Confidence score < 0.70 |
| `invalid_date_format` | Error | Date not in YYYY-MM-DD format |
| `invalid_classification` | Error | Invalid classification level |
| `invalid_document_type` | Warning | Document type not in allowed list |
| `invalid_language` | Warning | Language not ENGLISH or SPANISH |
| `empty_or_short_text` | Warning | reviewed_text < 50 chars |
| `incomplete_transcription` | Error | original_text > 100 chars but reviewed_text < 50 |
| `text_page_mismatch` | Info | Text length inconsistent with page count |
| `missing_date` | Info | Document date is missing or 0000-00-00 |

**Valid Values:**

- **Classification Levels:** `TOP SECRET`, `SECRET`, `CONFIDENTIAL`, `UNCLASSIFIED`, (empty)
- **Document Types:** `MEMORANDUM`, `LETTER`, `TELEGRAM`, `INTELLIGENCE BRIEF`, `REPORT`, `MEETING MINUTES`, `CABLE`, (empty)
- **Languages:** `ENGLISH`, `SPANISH`, (empty)

### 1.3 Sample Command

Generates stratified samples for manual review.

```bash
# Via Makefile
make eval-sample MODEL=gpt-5-mini

# Direct CLI
uv run python -m app.evaluate sample gpt-5-mini --output samples/ --size 30
```

**Sample Categories:**

| Category | Criteria | Default Count |
|----------|----------|---------------|
| `high_confidence/` | Confidence > 0.90 | 5 files |
| `medium_confidence/` | Confidence 0.75-0.90 | 10 files |
| `low_confidence/` | Confidence < 0.75 | 10 files |
| `multi_page/` | Page count > 3 | 5 files |

Each category folder contains:
- JSON transcript files
- Corresponding PDF files (for side-by-side comparison)

### 1.4 Report Command

Generates a visual HTML quality report.

```bash
# Via Makefile
make eval-report MODEL=gpt-5-mini

# Direct CLI
uv run python -m app.evaluate report gpt-5-mini --output quality_report.html
```

**Report Contents:**
- Summary cards (mean confidence, high confidence count, errors, warnings)
- Confidence distribution bar chart
- Metadata completeness table
- Document types table
- Validation issues by type
- Common concerns table
- Page count distribution

---

## 2. Response Repair & Validation (`app/utils/response_repair.py`)

Runtime validation and auto-repair utilities used during transcription.

### 2.1 Auto-Repair Function

```python
from app.utils.response_repair import auto_repair_response

repaired_data = auto_repair_response(raw_api_response)
```

**Handles:**
- Flat structure → nested metadata structure
- Missing `financial_references`, `violence_references`, `torture_references`
- Missing `confidence` field (defaults to 0.5)
- Missing `original_text` and `reviewed_text` fields

### 2.2 Schema Validation

```python
from app.utils.response_repair import validate_response

is_valid, errors = validate_response(data)
if not is_valid:
    for error in errors:
        print(f"Validation error: {error}")
```

Validates against: `app/prompts/schemas/metadata_schema.json`

### 2.3 Confidence Extraction

```python
from app.utils.response_repair import extract_confidence

confidence = extract_confidence(data)  # Returns float or None
```

### 2.4 Placeholder Detection

```python
from app.utils.response_repair import check_placeholder_text

is_placeholder = check_placeholder_text(text, threshold=100)
```

**Detects:**
- Text shorter than threshold
- Known placeholder phrases ("Full OCR text", "[Document text would appear here]", etc.)

---

## 3. Transcription Validation (`app/transcribe.py`)

Built-in validation during and after transcription.

### 3.1 Schema Validation with Auto-Repair

```python
from app.transcribe import validate_with_schema

is_valid, errors = validate_with_schema(data, enable_auto_repair=True)
```

Used during transcription to validate each API response.

### 3.2 Batch Output Validation

```bash
# Validate all outputs for a model
uv run python -c "from app.transcribe import validate_outputs, print_validation_report; r = validate_outputs('gpt-5-mini'); print_validation_report(r)"
```

**Checks:**
- Short `original_text` (< 100 chars)
- Placeholder text detection
- Empty `reviewed_text` when `original_text` has content
- Missing required fields

---

## 4. JSON Schema (`app/prompts/schemas/metadata_schema.json`)

The authoritative schema definition for transcript validation.

**Required Top-Level Fields:**
- `metadata` (object)
- `original_text` (string)
- `reviewed_text` (string)
- `confidence` (object with `overall` and `concerns`)

**Required Metadata Fields:**
| Field | Type | Validation |
|-------|------|------------|
| `document_id` | string | - |
| `case_number` | string | Pattern: `^[A-Z0-9]*$` |
| `document_date` | string | Pattern: ISO 8601 (YYYY-MM-DD) |
| `classification_level` | enum | TOP SECRET, SECRET, CONFIDENTIAL, UNCLASSIFIED, "" |
| `document_type` | enum | MEMORANDUM, LETTER, TELEGRAM, etc. |
| `author` | string | - |
| `recipients` | array[string] | - |
| `people_mentioned` | array[string] | - |
| `country` | array[string] | Pattern: `^[A-Z\s]+$` |
| `city` | array[string] | Pattern: `^[A-Z\s]+$` |
| `keywords` | array[string] | 1-15 items, pattern: `^[A-Z0-9\s\-]+$` |
| `page_count` | integer | minimum: 0 |
| `document_summary` | string | 50-1500 chars |

**Confidence Object:**
```json
{
  "overall": 0.85,  // 0.0-1.0
  "concerns": ["Concern 1", "Concern 2"]
}
```

---

## 5. Unit Tests (`tests/unit/`)

### 5.1 Response Repair Tests

```bash
uv run pytest tests/unit/test_response_repair.py -v
```

**Test Classes:**
- `TestAutoRepairResponse` - Tests auto-repair functionality
- `TestValidateResponse` - Tests schema validation
- `TestExtractConfidence` - Tests confidence extraction
- `TestCheckPlaceholderText` - Tests placeholder detection
- `TestMetadataFields` - Tests field constants
- `TestDefaultStructures` - Tests default value structures

### 5.2 Chunked PDF Tests

```bash
uv run pytest tests/unit/test_chunked_pdf.py -v
```

**Test Classes:**
- `TestNeedsChunking` - Tests chunking threshold logic
- `TestMergeChunkResults` - Tests result merging
- `TestChunkResult` - Tests dataclass behavior
- `TestConstants` - Tests configuration constants

### 5.3 Run All Unit Tests

```bash
# All unit tests
uv run pytest tests/unit/ -v

# With coverage
uv run pytest tests/unit/ --cov=app/utils

# Run specific test
uv run pytest tests/unit/test_response_repair.py::TestAutoRepairResponse -v
```

---

## 6. Investigation Tracking (`investigations/`)

Documented quality issues and their resolutions.

### Current Investigations

| ID | Title | Status |
|----|-------|--------|
| 001 | Empty reviewed_text in Document 24930 | Resolved |
| 002 | Documents with Low Characters Per Page Ratio | Resolved |
| 003 | Batch API Implementation | Complete |

### Creating New Investigations

```bash
# Create new investigation file
cp investigations/README.md investigations/004-new-issue.md
# Edit with issue details
```

**Template Structure:**
1. Summary - Brief description
2. Findings - Details, root cause, scope
3. Resolution - Code fix, remediation steps
4. Prevention - Future prevention measures

---

## 7. Quality Workflow

### Pre-Transcription

1. Verify source files exist in `data/original_pdfs/`
2. Check API credentials are configured
3. Review cost estimates

### During Transcription

- Real-time validation with auto-repair
- Progress tracking with confidence scores
- Automatic retry for API failures

### Post-Transcription

```bash
# 1. Check overall statistics
make eval-stats MODEL=gpt-5-mini

# 2. Run validation to find issues
make eval-validate MODEL=gpt-5-mini

# 3. Generate sample for manual review (optional)
make eval-sample MODEL=gpt-5-mini

# 4. Create full report for documentation
make eval-report MODEL=gpt-5-mini

# 5. Run unit tests to verify code
uv run pytest tests/unit/ -v
```

### Remediation

For documents with issues:

```bash
# Retry failed documents
uv run python -m app.transcribe --retry-failed --yes

# Retry incomplete documents (chunked processing)
uv run python -m app.transcribe --retry-incomplete --yes

# Process specific documents
uv run python -m app.transcribe --files 24930.pdf,24931.pdf --yes
```

---

## 8. Quality Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Confidence < 0.70 | Low | Manual review required |
| Confidence 0.70-0.85 | Medium | Spot check recommended |
| Confidence > 0.85 | High | Acceptable |
| Empty reviewed_text | Error | Re-transcribe |
| Invalid date format | Error | Manual correction |
| Text < 100 chars/page | Warning | Investigate |

---

## 9. Files Reference

| File | Purpose |
|------|---------|
| `app/evaluate.py` | Main evaluation CLI |
| `app/utils/response_repair.py` | Auto-repair and validation utilities |
| `app/utils/cost_tracker.py` | Cost tracking for API usage |
| `app/prompts/schemas/metadata_schema.json` | JSON schema definition |
| `app/transcribe.py` | Transcription with validation |
| `tests/unit/test_response_repair.py` | Unit tests for repair utilities |
| `tests/unit/test_chunked_pdf.py` | Unit tests for PDF chunking |
| `investigations/` | Documented quality issues |
| `Makefile` | Quality command shortcuts |

---

## 10. Example Commands

```bash
# Quick quality check for gpt-5-mini transcripts
make eval-stats MODEL=gpt-5-mini
make eval-validate MODEL=gpt-5-mini

# Full quality evaluation
make eval-report MODEL=gpt-5-mini

# Run all tests
make test

# Validate specific output directory
uv run python -m app.evaluate stats gpt-4.1-mini

# Generate sample for specific model
uv run python -m app.evaluate sample gpt-5-mini --output manual_review/ --size 50
```

---

*Last updated: 2025-12-13*
