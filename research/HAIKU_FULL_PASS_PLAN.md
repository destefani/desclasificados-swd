# Haiku Full Pass Plan

## Overview

This document outlines a safe plan for running a full transcription pass of 21,512 declassified CIA documents using **Claude 3.5 Haiku**.

## Current State

| Metric | Value |
|--------|-------|
| Total source PDFs | 21,512 |
| Total pages (estimated) | ~76,152 |
| Average pages per PDF | 3.54 |
| Already transcribed (chatgpt-5-1) | 1,352 (6.3%) |
| Already transcribed (Haiku) | 100+ (test batches) |

## CRITICAL DECISION: PDFs vs Images (2024-12-04)

### Finding

The `data/images/` directory contains **only the first page** of each PDF document (21,512 images = 21,512 first pages). However, the original PDFs in `data/original_pdfs/` contain **all pages** (~76,000 total pages across 21,512 documents).

### Page Distribution (500 PDF sample)

| Pages | Frequency |
|-------|-----------|
| 1 page | ~18% |
| 2 pages | ~44% |
| 3+ pages | ~38% |
| **Average** | **3.54 pages** |

### Decision: USE PDFs (all pages)

**Rationale**: Full document coverage is required. Missing pages 2+ would lose significant content from 82% of documents.

### Cost Implications

| Source | Files | Pages | Est. Cost (Standard) | Est. Cost (Batch) |
|--------|-------|-------|----------------------|-------------------|
| Images (first page only) | 21,512 | 21,512 | ~$157 | ~$79 |
| **PDFs (all pages)** | 21,512 | ~76,152 | **~$550** | **~$275** |

**Cost multiplier**: ~3.5x (matching average pages per PDF)

### Command Change

```bash
# OLD (images only - INCOMPLETE)
uv run python -m app.transcribe_claude --model claude-3-5-haiku-20241022

# NEW (full PDFs - COMPLETE)
uv run python -m app.transcribe_claude --model claude-3-5-haiku-20241022 --use-pdf
```

### Output

Each PDF produces ONE JSON file containing transcription of ALL pages in that document.

## CRITICAL FINDING: Haiku vs Sonnet Text Transcription (2024-12-04)

### Discovery

Testing revealed that **Claude 3.5 Haiku does NOT produce actual text transcription** - it returns placeholder text while extracting metadata. Only **Claude Sonnet 4.5** produces full verbatim OCR text.

### Evidence

**Haiku 3.5 output (24738.pdf - 6 pages):**
```json
"original_text": "[Full OCR text from document]",
"reviewed_text": "[Corrected OCR text]"
```
- Text length: 29 characters (placeholder)
- Metadata: Fully extracted (names, dates, keywords, summary)
- Cost: $0.0153

**Sonnet 4.5 output (24736.jpg - 1 page):**
```json
"original_text": "Department of State\nUNCLASSIFIED\n\nEXCISE\n\nPAGE 21 STATE 214958\n53\nORIGIN INR0-08\n\nINFO OCT-01 ISO-00 /089 R\n\nDRAFTED BY:ARLIC:JGIBSIN:..."
```
- Text length: 1,800+ characters (actual OCR)
- Metadata: Fully extracted
- Full verbatim transcription with OCR corrections

### Comparison Table

| Aspect | Haiku 3.5 | Sonnet 4.5 |
|--------|-----------|------------|
| **original_text** | Placeholder only | Full OCR transcription |
| **reviewed_text** | Placeholder only | Corrected OCR text |
| **Metadata extraction** | YES | YES |
| **Summaries** | YES | YES |
| **Keywords** | YES | YES |
| **Searchable text** | NO | YES |
| **Structured outputs** | NO | YES |

### Cost Implications (Full Pass - 21,512 PDFs, ~76K pages)

| Model | Input Cost | Output Cost | **Total** |
|-------|------------|-------------|-----------|
| Haiku 3.5 | $97 | $172 | **~$270** |
| Sonnet 4.5 | $366 | $645 | **~$1,010** |

**Cost multiplier**: Sonnet is ~3.7x more expensive than Haiku

### Decision Matrix

| Use Case | Recommended Model | Cost |
|----------|-------------------|------|
| Metadata + summaries only | Haiku 3.5 | ~$270 |
| Full-text search capability | Sonnet 4.5 | ~$1,010 |
| RAG/semantic search | Either (summaries work) | - |
| Verbatim document quotes | Sonnet 4.5 | ~$1,010 |

### Command for Each Option

**Option A: Haiku (metadata only)**
```bash
uv run python -m app.transcribe_claude \
  --model claude-3-5-haiku-20241022 \
  --use-pdf \
  --max-workers 2
```

**Option B: Sonnet (full transcription)**
```bash
uv run python -m app.transcribe_claude \
  --model claude-sonnet-4-5-20250929 \
  --use-pdf \
  --max-workers 2
```

### OpenAI Model Testing Results (2024-12-04)

#### Models Tested for Full OCR Capability

| Model | Full OCR | Text Length | Notes |
|-------|----------|-------------|-------|
| **gpt-4.1-nano** | **YES** | 933 chars | Cheapest working option |
| **gpt-4.1-mini** | **YES** | 1,627 chars | Good balance |
| **gpt-4o** | **YES** | 1,679 chars | Expensive |
| **gpt-5.1-2025-11-13** | **YES** | 1,188 chars | Used for existing transcriptions |
| gpt-4o-mini | NO | 40 chars | **REFUSED to transcribe** |
| gpt-5-nano | N/A | - | No vision support (error) |
| gpt-5-mini | N/A | - | No vision support (error) |

#### Cost Comparison (Full Pass - 21,512 PDFs, ~76K pages)

Estimated tokens: ~122M input, ~43M output

| Model | Input $/M | Output $/M | **Est. Total** | Full OCR |
|-------|-----------|------------|----------------|----------|
| **gpt-4.1-nano** | $0.10 | $0.40 | **~$30** | **YES** |
| **gpt-4.1-mini** | $0.40 | $1.60 | **~$118** | **YES** |
| gpt-4o-mini | $0.15 | $0.60 | ~$44 | **NO (REFUSED)** |
| gpt-4o | $2.50 | $10.00 | ~$735 | YES |
| gpt-5.1 | $2.00 | $8.00 | ~$588 | YES |
| claude-3-5-haiku | $0.80 | $4.00 | ~$270 | **NO (placeholder)** |
| claude-sonnet-4.5 | $3.00 | $15.00 | ~$1,010 | YES |

#### RECOMMENDATION: gpt-4.1-nano (~$30)

**Winner**: `gpt-4.1-nano` at **~$30** for the full pass with complete OCR.

**Command:**
```bash
uv run python -m app.transcribe_openai \
  --model gpt-4.1-nano \
  --use-pdf \
  --max-workers 3
```

**Backup**: `gpt-4.1-mini` (~$118) if nano quality is insufficient.

Sources:
- [OpenAI Pricing](https://openai.com/api/pricing/)
- [GPT-4.1 Pricing Calculator](https://livechatai.com/gpt-4-1-pricing-calculator)

## Cost Analysis

### Haiku Pricing (per million tokens)

| Mode | Input | Output |
|------|-------|--------|
| Standard | $0.80 | $4.00 |
| Batch API (50% off) | $0.40 | $2.00 |

### Estimated Cost (Updated for PDFs)

Based on observed usage (~2,600 input tokens per page + ~1,300 output tokens per document):

| Mode | Cost per Page | Full Pass (76,152 pages) |
|------|---------------|--------------------------|
| **Standard** | ~$0.0073 | **~$550** |
| **Batch API** | ~$0.0037 | **~$275** |

**Note**: Cost is ~3.5x higher than image-only approach because we're processing ALL pages.

**Recommendation**: Use **Standard API** with 2-3 workers (Batch API had 94% failure rate in testing).

## Time Estimates

| Mode | Rate Limit | Estimated Time |
|------|------------|----------------|
| Standard (3 workers) | ~50 RPM | **~7 hours** |
| Standard (5 workers) | ~80 RPM | **~4.5 hours** |
| Batch API | Async | **24-48 hours** (but no monitoring needed) |

## Key Risks & Mitigations

### 1. Haiku Doesn't Support Structured Outputs

**Risk**: JSON parsing failures due to conversational preambles or malformed output.

**Mitigation**: Already implemented:
- `extract_json_from_response()` - extracts JSON from markdown blocks or raw text
- `auto_repair_response()` - fixes flat structures and missing fields
- JSON validation with detailed error logging

**Monitoring**: Watch for `JSON parse error` in logs.

### 2. Quality Degradation

**Risk**: Haiku may produce lower quality transcriptions than Sonnet.

**Mitigation**:
- Confidence scoring is built-in (tracked per document)
- Low-confidence documents are flagged for human review
- All metadata fields have validation

**Acceptance Criteria**:
- Average confidence > 0.7
- JSON validation pass rate > 95%

### 3. API Rate Limits

**Risk**: Getting rate-limited and wasting time.

**Current Limits** (configurable via env vars):
- `CLAUDE_MAX_RPM=50` (requests per minute)
- `CLAUDE_MAX_TPM=400000` (tokens per minute)

**Mitigation**: Built-in rate limiter with exponential backoff.

### 4. Unexpected Costs

**Risk**: API costs exceed budget.

**Mitigation**:
- Cost estimation displayed before processing
- Confirmation required before proceeding
- Real-time cost tracking in logs
- Can stop at any time with Ctrl+C (state is saved)

### 5. Process Interruption

**Risk**: Process dies mid-way, losing progress.

**Mitigation**:
- `--resume` flag skips already-processed files
- Output is saved immediately after each document
- State can be recovered from any point

## Execution Plan

### Phase 1: Dry Run (5 docs)

Test the pipeline end-to-end:

```bash
uv run python -m app.transcribe_claude \
  --model claude-3-5-haiku-20241022 \
  --max-files 5 \
  --max-workers 1
```

**Verify**:
- [ ] All 5 documents produce valid JSON
- [ ] Confidence scores are reasonable (> 0.5)
- [ ] No JSON parse errors
- [ ] Cost per document matches estimate (~$0.007)

### Phase 2: Small Batch (100 docs)

```bash
uv run python -m app.transcribe_claude \
  --model claude-3-5-haiku-20241022 \
  --max-files 100 \
  --max-workers 3 \
  --resume
```

**Expected**: ~$0.73, ~2 minutes

**Verify**:
- [ ] Success rate > 95%
- [ ] No rate limit errors
- [ ] Average confidence > 0.7

### Phase 3: Medium Batch (1000 docs)

```bash
uv run python -m app.transcribe_claude \
  --model claude-3-5-haiku-20241022 \
  --max-files 1000 \
  --max-workers 5 \
  --resume
```

**Expected**: ~$7.30, ~12-15 minutes

**Verify**:
- [ ] Consistent performance
- [ ] No memory issues
- [ ] Logs are manageable

### Phase 4: Full Pass (remaining ~20,411 docs)

**Option A: Standard API (Recommended for monitoring)**

```bash
uv run python -m app.transcribe_claude \
  --model claude-3-5-haiku-20241022 \
  --max-workers 5 \
  --resume \
  --yes
```

**Expected**: ~$147, ~4-5 hours

Run in a screen/tmux session for resilience:
```bash
tmux new -s haiku-full-pass
# Then run the command above
# Ctrl+b, d to detach
# tmux attach -t haiku-full-pass to reconnect
```

**Option B: Batch API (50% off, hands-free)**

```bash
uv run python -m app.transcribe_claude \
  --model claude-3-5-haiku-20241022 \
  --batch \
  --batch-size 5000 \
  --resume \
  --yes
```

**Expected**: ~$79, 24-48 hours (async)

### Phase 5: Quality Review

After completion:

```bash
# Check status
uv run python -m app.transcribe_claude --status

# Analyze quality
uv run python -m app.analyze_documents \
  data/generated_transcripts/claude-3-5-haiku-20241022 \
  --output reports/haiku_analysis.html
```

## Recommended Approach

### For Speed: Standard API

```bash
# In tmux/screen session
uv run python -m app.transcribe_claude \
  --model claude-3-5-haiku-20241022 \
  --max-workers 5 \
  --resume \
  --yes
```

- **Cost**: ~$157
- **Time**: ~4-5 hours
- **Pros**: Real-time monitoring, can stop/resume easily
- **Cons**: Requires active session

### For Cost: Batch API

```bash
uv run python -m app.transcribe_claude \
  --model claude-3-5-haiku-20241022 \
  --batch \
  --batch-size 5000 \
  --resume \
  --yes
```

- **Cost**: ~$79 (50% savings!)
- **Time**: 24-48 hours (async)
- **Pros**: Fire and forget, cheaper
- **Cons**: Can't monitor in real-time

## Safeguards Checklist

Before starting full pass:

- [ ] Backup any critical data
- [ ] Ensure sufficient disk space (~500MB for 21K JSON files)
- [ ] Verify ANTHROPIC_API_KEY is set and has sufficient credits
- [ ] Run Phase 1 dry run successfully
- [ ] Run Phase 2 small batch successfully
- [ ] Set up tmux/screen session for resilience

## Monitoring During Execution

### Progress

```bash
# Check file count
uv run python -m app.transcribe_claude --status

# Or directly
ls data/generated_transcripts/claude-3-5-haiku-20241022/*.json | wc -l
```

### Logs

Watch for:
- `JSON parse error` - indicates Haiku output issues
- `Rate limit` - indicates need to lower workers
- `API error` - transient issues (auto-retried)

### Cost

Displayed in real-time during processing and in final summary.

## Rollback Plan

If quality is unacceptable:

1. Stop processing (Ctrl+C)
2. Review problematic outputs in `data/generated_transcripts/claude-3-5-haiku-20241022/`
3. Delete problematic files if needed
4. Consider switching to Sonnet for better quality (higher cost)

```bash
# Remove all Haiku outputs if needed
rm -rf data/generated_transcripts/claude-3-5-haiku-20241022/
```

## Summary

| Parameter | Value |
|-----------|-------|
| Model | claude-3-5-haiku-20241022 |
| **Source** | **PDFs (--use-pdf)** |
| Documents | 21,512 |
| Total Pages | ~76,152 |
| **Estimated Cost (Standard)** | **~$550** |
| Estimated Cost (Batch) | ~$275 (not recommended) |
| Estimated Time (Standard) | ~12-15 hours |
| Recommended Workers | 2-3 |
| Confidence Target | > 0.7 |
| Success Rate Target | > 95% |
