# GPT-4.1-mini Full Pass Plan

## Overview

This document outlines the plan for running a full transcription pass of 21,512 declassified CIA documents using **OpenAI gpt-4.1-mini** with native PDF support.

## CRITICAL UPDATE (2024-12-04)

**gpt-4.1-nano does NOT produce full OCR text** - it returns placeholders like Claude Haiku.
**gpt-4.1-mini WORKS** and produces actual verbatim transcription.

## Why gpt-4.1-mini?

| Metric | gpt-4.1-mini | gpt-4.1-nano | Claude Sonnet 4.5 |
|--------|--------------|--------------|-------------------|
| Full OCR | **YES** | NO (placeholder) | YES |
| Est. Cost | **~$118** | ~$30 (unusable) | ~$1,010 |
| Input $/M | $0.40 | $0.10 | $3.00 |
| Output $/M | $1.60 | $0.40 | $15.00 |
| **Savings vs Sonnet** | **88%** | - | - |

## Current State

| Metric | Value |
|--------|-------|
| Total source PDFs | 21,512 |
| Total pages (estimated) | ~76,152 |
| Average pages per PDF | 3.54 |
| Estimated input tokens | ~122 million |
| Estimated output tokens | ~43 million |
| Already transcribed (gpt-5.1) | 1,352 |
| Remaining | ~20,160 |

## Technical Requirements

### 1. OpenAI API Differences from Claude

| Feature | Claude | OpenAI gpt-4.1 |
|---------|--------|----------------|
| Max tokens param | `max_tokens` | `max_completion_tokens` |
| PDF support | Native `document` type | Convert to images or use vision |
| Structured outputs | Beta feature | Native with `response_format` |
| Image format | base64 in content | base64 URL in `image_url` |

### 2. PDF Handling Strategy

**Option A: Convert PDFs to images first (Recommended)**
- Use pdf2image/poppler to convert each PDF page to image
- Send images to gpt-4.1-nano vision
- Pros: More reliable, proven approach
- Cons: Extra conversion step

**Option B: Use existing images**
- Use pre-extracted images from `data/images/`
- Only first page of each document
- **NOT RECOMMENDED** - loses 82% of content

**Option C: Multi-page as multiple images**
- Convert each PDF to multiple images
- Send all pages in single API call
- Pros: Complete coverage
- Cons: Higher token usage per call

### 3. Rate Limits (OpenAI Tier)

Check your tier at: https://platform.openai.com/settings/organization/limits

| Tier | RPM | TPM |
|------|-----|-----|
| Tier 1 | 500 | 200,000 |
| Tier 2 | 5,000 | 2,000,000 |
| Tier 3 | 5,000 | 4,000,000 |

**Recommended workers based on tier:**
- Tier 1: 3-5 workers
- Tier 2+: 10-20 workers

## Implementation Plan

### Phase 0: Setup (Pre-requisites)

```bash
# Install dependencies
uv add pdf2image pillow

# Verify poppler is installed (required for pdf2image)
which pdftoppm || brew install poppler

# Verify OpenAI API key
echo $OPENAI_API_KEY
```

### Phase 1: Create transcribe_openai.py

New module based on `transcribe_claude.py` with:

1. **PDF to image conversion**
   ```python
   from pdf2image import convert_from_path

   def pdf_to_images(pdf_path: Path) -> list[bytes]:
       """Convert PDF pages to images."""
       images = convert_from_path(pdf_path, dpi=150)
       result = []
       for img in images:
           buffer = io.BytesIO()
           img.save(buffer, format='JPEG', quality=85)
           result.append(buffer.getvalue())
       return result
   ```

2. **OpenAI vision API call**
   ```python
   def transcribe_document(images: list[bytes], model: str) -> dict:
       content = []
       for img_bytes in images:
           b64 = base64.b64encode(img_bytes).decode()
           content.append({
               "type": "image_url",
               "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
           })
       content.append({"type": "text", "text": PROMPT})

       response = client.chat.completions.create(
           model=model,
           messages=[{"role": "user", "content": content}],
           max_completion_tokens=4000,
           response_format={"type": "json_object"}
       )
       return json.loads(response.choices[0].message.content)
   ```

3. **Cost tracking**
   ```python
   PRICING = {
       "gpt-4.1-nano": {"input": 0.10 / 1_000_000, "output": 0.40 / 1_000_000},
       "gpt-4.1-mini": {"input": 0.40 / 1_000_000, "output": 1.60 / 1_000_000},
   }
   ```

4. **Resume capability**
   - Check for existing JSON before processing
   - `--resume` flag to skip existing files

5. **Rate limiting**
   - Sliding window for RPM/TPM
   - Exponential backoff on 429 errors

### Phase 2: Dry Run (5 PDFs)

```bash
uv run python -m app.transcribe_openai \
  --model gpt-4.1-nano \
  --max-files 5 \
  --max-workers 1
```

**Verify:**
- [ ] PDFs converted to images correctly
- [ ] All pages sent to API
- [ ] JSON output is valid
- [ ] Full OCR text (not placeholder)
- [ ] Cost per document matches estimate (~$0.0015)

**Expected cost:** ~$0.01

### Phase 3: Small Batch (100 PDFs)

```bash
uv run python -m app.transcribe_openai \
  --model gpt-4.1-nano \
  --max-files 100 \
  --max-workers 3 \
  --resume
```

**Verify:**
- [ ] Success rate > 95%
- [ ] No rate limit errors
- [ ] Output quality acceptable
- [ ] Cost tracking accurate

**Expected cost:** ~$0.15

### Phase 4: Medium Batch (1,000 PDFs)

```bash
uv run python -m app.transcribe_openai \
  --model gpt-4.1-nano \
  --max-files 1000 \
  --max-workers 5 \
  --resume
```

**Verify:**
- [ ] Consistent performance
- [ ] No memory issues (PDF conversion)
- [ ] Resume works correctly

**Expected cost:** ~$1.50

### Phase 5: Full Pass (~20,160 remaining)

```bash
# In tmux/screen session for resilience
tmux new -s openai-full-pass

uv run python -m app.transcribe_openai \
  --model gpt-4.1-nano \
  --max-workers 10 \
  --resume \
  --yes
```

**Expected:**
- Cost: ~$30
- Time: 4-8 hours (depending on rate limits)

**Monitor:**
```bash
# Check progress
ls data/generated_transcripts/gpt-4.1-nano/*.json | wc -l

# Check for errors
grep -i "error" logs/openai_transcribe.log | tail -20
```

## Output Structure

```
data/generated_transcripts/
├── gpt-4.1-nano/           # NEW - this pass
│   ├── 24736.json
│   ├── 24737.json
│   └── ...
├── chatgpt-5-1/            # Previous pass (1,352 files)
├── claude-3-5-haiku-20241022/
└── claude-sonnet-4-5-20250929/
```

## Cost Controls

### Budget Limits

```bash
# Set maximum spend
uv run python -m app.transcribe_openai \
  --model gpt-4.1-nano \
  --max-cost 35.00 \
  --resume
```

### Real-time Tracking

```python
# Display after each batch
print(f"Progress: {processed}/{total} ({pct:.1f}%)")
print(f"Cost so far: ${cost:.2f} / ${max_cost:.2f}")
print(f"Estimated total: ${estimated_total:.2f}")
```

### Stop Conditions

1. **Budget exceeded**: Stop if cost > max_cost
2. **Error rate**: Stop if >10% failures in last 100
3. **Manual**: Ctrl+C saves state for resume

## Risk Mitigation

### 1. PDF Conversion Failures

**Risk:** Some PDFs may fail to convert (corrupted, encrypted)

**Mitigation:**
- Log failures separately
- Continue with other files
- Manual review of failed files

```python
try:
    images = pdf_to_images(pdf_path)
except Exception as e:
    log_error(pdf_path, str(e))
    failed_pdfs.append(pdf_path)
    continue
```

### 2. Rate Limiting

**Risk:** Hit rate limits, slow down processing

**Mitigation:**
- Implement exponential backoff
- Track RPM/TPM in sliding window
- Reduce workers if frequent 429s

### 3. Cost Overrun

**Risk:** Actual cost exceeds estimate

**Mitigation:**
- Real-time cost tracking
- Configurable max_cost limit
- Alert at 80% of budget

### 4. Quality Issues

**Risk:** gpt-4.1-nano output quality insufficient

**Mitigation:**
- Phase 2/3 quality review before full pass
- Fallback to gpt-4.1-mini if needed
- Sample-based quality checks during run

## Quality Assurance

### During Processing

```python
# Track quality metrics
quality_metrics = {
    "total": 0,
    "successful": 0,
    "failed": 0,
    "avg_text_length": 0,
    "min_text_length": float('inf'),
    "json_valid": 0,
}
```

### Post-Processing

```bash
# Validate all outputs
uv run python -m app.validate_transcripts \
  data/generated_transcripts/gpt-4.1-nano/

# Check for placeholder text
grep -l "Full OCR text" data/generated_transcripts/gpt-4.1-nano/*.json

# Compare with previous transcriptions
uv run python -m app.compare_transcripts \
  --old data/generated_transcripts/chatgpt-5-1/ \
  --new data/generated_transcripts/gpt-4.1-nano/
```

## Rollback Plan

If quality is unacceptable:

1. **Stop processing** (Ctrl+C)
2. **Review samples** from output directory
3. **Options:**
   - Switch to gpt-4.1-mini (~$118)
   - Switch to gpt-5.1 (~$588)
   - Use Claude Sonnet 4.5 (~$1,010)

```bash
# Remove gpt-4.1-nano outputs if needed
rm -rf data/generated_transcripts/gpt-4.1-nano/
```

## Timeline

| Phase | Documents | Est. Time | Est. Cost |
|-------|-----------|-----------|-----------|
| Phase 0: Setup | - | 30 min | $0 |
| Phase 1: Implement | - | 2-3 hours | $0 |
| Phase 2: Dry Run | 5 | 5 min | $0.01 |
| Phase 3: Small Batch | 100 | 15 min | $0.15 |
| Phase 4: Medium Batch | 1,000 | 1 hour | $1.50 |
| Phase 5: Full Pass | ~20,160 | 4-8 hours | ~$28 |
| **Total** | **21,512** | **~10 hours** | **~$30** |

## Commands Reference

```bash
# Dry run (5 files)
uv run python -m app.transcribe_openai --model gpt-4.1-nano --max-files 5

# Small batch with resume
uv run python -m app.transcribe_openai --model gpt-4.1-nano --max-files 100 --resume

# Full pass with budget limit
uv run python -m app.transcribe_openai --model gpt-4.1-nano --max-cost 35 --resume --yes

# Check status
uv run python -m app.transcribe_openai --status

# Use gpt-4.1-mini as backup
uv run python -m app.transcribe_openai --model gpt-4.1-mini --resume
```

## Checklist Before Full Pass

- [ ] OpenAI API key has sufficient credits
- [ ] Poppler installed for PDF conversion
- [ ] Phase 2 dry run successful
- [ ] Phase 3 small batch successful
- [ ] Quality review passed
- [ ] tmux/screen session ready
- [ ] Disk space available (~500MB for JSONs)
- [ ] Monitoring plan in place

## Summary

| Parameter | Value |
|-----------|-------|
| Model | gpt-4.1-nano |
| Source | PDFs (all pages) |
| Documents | 21,512 |
| Total Pages | ~76,152 |
| **Estimated Cost** | **~$30** |
| Estimated Time | 4-8 hours |
| Recommended Workers | 5-10 |
| Output Directory | data/generated_transcripts/gpt-4.1-nano/ |
