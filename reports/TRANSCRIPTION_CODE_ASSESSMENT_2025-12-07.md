# Transcription Code Assessment Report

**Date:** 2025-12-07
**Project:** Desclasificados - CIA Chilean Dictatorship Documents
**Branch:** feature/sensitive-content-tracking

---

## Executive Summary

The transcription codebase consists of **~5,000 lines** across 7 primary modules, supporting both OpenAI and Claude (Anthropic) APIs. The code is well-structured with proper separation of concerns, comprehensive error handling, and production-ready features including rate limiting, cost tracking, batch processing, and resume capability.

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Architecture** | Good | Clean module separation, consistent patterns |
| **Error Handling** | Excellent | Retry logic, graceful shutdown, validation |
| **Production Readiness** | Excellent | Rate limiting, cost tracking, resume support |
| **Maintainability** | Good | Well-documented, some duplication between modules |
| **Testing** | Needs Work | Minimal test coverage |

---

## 1. Module Overview

### 1.1 Line Counts

| Module | Lines | Purpose |
|--------|-------|---------|
| `transcribe_openai.py` | 1,326 | **Primary** - OpenAI transcription with PDF/batch support |
| `transcribe_claude.py` | 1,208 | Claude transcription with structured outputs |
| `transcribe.py` | 1,021 | Legacy OpenAI transcription |
| `full_pass.py` | 413 | CLI for batch orchestration |
| `state_manager.py` | 389 | Session persistence and checkpoints |
| `batch_processor.py` | 378 | Batch execution with graceful shutdown |
| `transcribe_v2.py` | 277 | Deprecated v2 implementation |
| **Total** | **5,012** | |

### 1.2 Module Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                          CLI Layer                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ full_pass.py │ │ transcribe_  │ │ transcribe_openai.py │ │
│  │              │ │ claude.py    │ │                      │ │
│  └──────┬───────┘ └──────────────┘ └──────────────────────┘ │
│         │                                                    │
├─────────┼────────────────────────────────────────────────────┤
│         ▼            Processing Layer                        │
│  ┌──────────────┐ ┌──────────────┐                          │
│  │ batch_       │ │ state_       │                          │
│  │ processor.py │ │ manager.py   │                          │
│  └──────────────┘ └──────────────┘                          │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                     Configuration Layer                       │
│  ┌──────────────┐ ┌──────────────────────────────────────┐  │
│  │ config.py    │ │ prompts/ (metadata_prompt_v2.md)     │  │
│  └──────────────┘ │ schemas/ (metadata_schema.json)      │  │
│                   └──────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Code Quality Analysis

### 2.1 Architecture Strengths

#### Model-Specific Output Directories
```python
# transcribe_openai.py:549-556
def get_model_output_dir(model: str) -> Path:
    safe_model_name = model.replace("/", "-").replace(":", "-")
    output_dir = DATA_DIR / "generated_transcripts" / safe_model_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
```
- Enables parallel testing of multiple models
- Clean separation of outputs
- Supports A/B comparison

#### Thread-Safe Cost Tracking
```python
# transcribe_openai.py:133-165
class CostTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.lock = threading.Lock()

    def add_usage(self, input_tokens: int, output_tokens: int):
        with self.lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
```
- Thread-safe for concurrent processing
- Real-time cost tracking per model
- Supports budget limits

#### Sliding Window Rate Limiting
```python
# transcribe_openai.py:174-209
def wait_for_rate_limit():
    while True:
        with rate_lock:
            now = time.time()
            # Remove entries older than 60 seconds
            while request_times and now - request_times[0] > 60:
                request_times.popleft()
            # Check RPM and TPM limits...
```
- Implements proper sliding window for RPM/TPM
- Prevents API throttling
- Configurable via environment variables

### 2.2 Design Patterns Used

| Pattern | Implementation | Location |
|---------|----------------|----------|
| **Strategy** | Multiple model backends | `transcribe_openai.py`, `transcribe_claude.py` |
| **State** | ProcessingState dataclass | `state_manager.py:17-56` |
| **Observer** | GracefulShutdown signals | `batch_processor.py:18-61` |
| **Template Method** | Common transcription flow | All transcribe modules |
| **Factory** | Content block preparation | `prepare_pdf_content()`, `prepare_image_content()` |

### 2.3 Code Duplication

There is significant duplication between modules that could be refactored:

| Duplicated Function | Modules | Lines |
|---------------------|---------|-------|
| `auto_repair_response()` | 3 modules | ~60 lines each |
| `validate_response()` | 3 modules | ~15 lines each |
| Rate limiting code | 3 modules | ~35 lines each |
| Cost estimation | 3 modules | ~30 lines each |

**Recommendation:** Extract common utilities to `app/utils/transcription_utils.py`

---

## 3. Feature Analysis

### 3.1 API Support Matrix

| Feature | OpenAI (`transcribe_openai.py`) | Claude (`transcribe_claude.py`) |
|---------|----------------------------------|--------------------------------|
| PDF Input | Native | Native |
| Image Input | Yes | Yes |
| Structured Outputs | JSON mode | Beta (claude-sonnet-4.5 only) |
| Batch API | Yes (50% savings) | Yes (50% savings) |
| Rate Limiting | Yes (RPM + TPM) | Yes (RPM + TPM) |
| Cost Tracking | Yes | Yes |
| Resume | Yes | Yes |

### 3.2 Error Handling

#### Retry Logic with Exponential Backoff
```python
# transcribe_openai.py:475-489
except openai.RateLimitError as e:
    if attempt == max_retries:
        logging.error(f"✗ {filename} | Rate limit after {max_retries} attempts")
        return {"success": False, ...}
    delay = (2 ** attempt) + (time.time() % 1)  # Jitter
    logging.warning(f"Rate limit, retrying in {delay:.1f}s")
    time.sleep(delay)
```
- 3 retries by default
- Exponential backoff with jitter
- Separate handling for rate limits vs API errors

#### Auto-Repair Response
```python
# transcribe_openai.py:233-288
def auto_repair_response(data: dict) -> dict:
    # Handle flat structure (move fields to metadata)
    if "metadata" not in data and any(k in data for k in METADATA_FIELDS):
        metadata = {}
        root_fields = {}
        for key, value in data.items():
            if key in METADATA_FIELDS:
                metadata[key] = value
        # ...

    # Ensure required nested structures exist
    if "financial_references" not in metadata:
        metadata["financial_references"] = {"amounts": [], ...}
```
- Handles schema variations from different models
- Ensures required fields exist
- Preserves data integrity

### 3.3 Graceful Shutdown

```python
# batch_processor.py:18-61
class GracefulShutdown:
    def __init__(self, state_manager: StateManager):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._request_shutdown)
        signal.signal(signal.SIGTERM, self._request_shutdown)

    def _request_shutdown(self, signum, frame):
        if not self.shutdown_requested:
            self.logger.info("Shutdown requested. Finishing current batch...")
            self.shutdown_requested = True
```
- Catches SIGINT and SIGTERM
- Completes current document before stopping
- Saves state for resume

### 3.4 State Management

```python
# state_manager.py:17-46
@dataclass
class ProcessingState:
    session_id: str
    prompt_version: str
    started_at: str
    last_updated: str
    total_documents: int
    processed: int
    successful: int
    failed: int
    # ... 15+ more fields
```

**Features:**
- Atomic file writes (temp file → rename)
- Checkpoint creation every N documents
- Automatic cleanup of old checkpoints (keeps last 5)
- Full session metrics (speed, ETA, confidence tracking)

---

## 4. Prompt Engineering

### 4.1 Prompt Structure (`metadata_prompt_v2.md`)

| Section | Lines | Purpose |
|---------|-------|---------|
| YAML Frontmatter | 1-20 | Version tracking, performance baselines |
| Core Tasks | 22-28 | High-level objectives |
| Field Extraction Guide | 30-220 | Detailed per-field instructions |
| Sensitive Content | 222-308 | Financial, violence, torture tracking |
| Text Transcription | 310-332 | OCR and correction guidelines |
| Confidence Assessment | 334-358 | Quality scoring rubric |
| Historical Context | 360-388 | Key figures, organizations, events |
| Output Format | 390-404 | JSON schema reference |

### 4.2 Prompt Versioning

```yaml
# metadata_prompt_v2.md:1-20
---
prompt_version: 2.1.0
prompt_name: "metadata_extraction_standard"
last_updated: 2024-12-01
model_compatibility: ["gpt-4o-2024-08-06", "gpt-4o-mini-2024-07-18"]
uses_structured_outputs: true
changelog:
  - v2.1.0: Added sensitive content tracking
  - v2.0.0: Structured Outputs, confidence scoring
  - v1.0.0: Initial prompt
performance_baseline:
  success_rate: 0.85
  avg_input_tokens: 2600
  avg_output_tokens: 1300
  cost_per_doc: 0.00086
---
```
- Semantic versioning
- Documented changelog
- Performance baselines for regression detection

### 4.3 JSON Schema (`metadata_schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["metadata", "original_text", "reviewed_text", "confidence"],
  "properties": {
    "metadata": {
      "required": [
        "document_id", "case_number", "document_date",
        "classification_level", "document_type", ...
        "financial_references", "violence_references", "torture_references"
      ]
    }
  }
}
```

**Key Schema Features:**
- 24 required metadata fields
- Date format validation (`YYYY-MM-DD`)
- Enum constraints for classification, document type, language
- Nested objects for sensitive content tracking
- Pattern validation for keywords, countries, cities

---

## 5. CLI & Configuration

### 5.1 CLI Options (`transcribe_openai.py`)

| Flag | Description | Default |
|------|-------------|---------|
| `--max-files N` | Limit files to process | 0 (all) |
| `--resume` | Skip existing transcripts | True |
| `--model MODEL` | Model to use | gpt-4.1-nano |
| `--max-workers N` | Parallel threads | 5 |
| `--max-cost N` | Budget limit | None |
| `--batch` | Use Batch API (50% off) | False |
| `--batch-status ID` | Check batch status | - |
| `--batch-download ID` | Download batch results | - |
| `--batch-list` | List recent batches | - |
| `--status` | Show progress by model | - |
| `-y, --yes` | Skip confirmation | False |
| `--use-images` | Use images not PDFs | False |

### 5.2 Environment Variables

| Variable | Default | Usage |
|----------|---------|-------|
| `OPENAI_API_KEY` | Required | OpenAI authentication |
| `ANTHROPIC_API_KEY` | Required | Claude authentication |
| `OPENAI_MAX_RPM` | 500 | Requests per minute limit |
| `OPENAI_MAX_TPM` | 200000 | Tokens per minute limit |
| `CLAUDE_MAX_RPM` | 50 | Claude requests per minute |
| `CLAUDE_MAX_TPM` | 400000 | Claude tokens per minute |
| `OPENAI_TRANSCRIPTION_MODEL` | gpt-4.1-nano | Default OpenAI model |
| `CLAUDE_TRANSCRIPTION_MODEL` | claude-sonnet-4.5-20250929 | Default Claude model |

### 5.3 Makefile Targets

```makefile
# Key targets
transcribe-claude       # Claude real-time transcription
transcribe-claude-batch # Claude batch API (50% off)
full-pass              # OpenAI interactive batch processing
full-pass-auto         # OpenAI auto mode with budget
full-pass-resume       # Resume previous session
full-pass-status       # Show progress
```

---

## 6. Performance Characteristics

### 6.1 Processing Speed

| Mode | Workers | Rate | Documents/Hour |
|------|---------|------|----------------|
| OpenAI Real-time | 5 | ~500 RPM | ~800-1000 |
| OpenAI Batch | N/A | Async | ~2000-4000 (2-4h delay) |
| Claude Real-time | 3 | ~50 RPM | ~150-200 |
| Claude Batch | N/A | Async | ~500-1000 (24h max) |

### 6.2 Cost Efficiency

| Model | Cost/Doc | Cost/21K Docs | Notes |
|-------|----------|---------------|-------|
| gpt-4.1-nano | ~$0.0015 | ~$32 | Best value |
| gpt-4.1-mini | ~$0.005 | ~$105 | Good quality |
| gpt-4o-mini | ~$0.002 | ~$42 | No full OCR |
| claude-3-5-haiku | ~$0.013 | ~$273 | No full OCR |
| claude-sonnet-4.5 | ~$0.047 | ~$1,000 | Best quality |

### 6.3 Batch API Savings

Both OpenAI and Claude support batch APIs with 50% cost reduction:

```python
# transcribe_openai.py:722-825
def run_batch_transcription(...):
    # Cost estimate (with 50% batch discount)
    regular_cost = estimate_cost(len(to_process), model)
    batch_cost = regular_cost * 0.5
```

---

## 7. Identified Issues

### 7.1 Code Issues

| Issue | Severity | Location | Description |
|-------|----------|----------|-------------|
| Code Duplication | Medium | Multiple modules | `auto_repair_response()`, rate limiting duplicated |
| Global State | Low | All transcribe modules | `cost_tracker`, `request_times` as globals |
| Missing Type Hints | Low | Some functions | Inconsistent use of type hints |
| Magic Numbers | Low | Rate limiting | Some constants not configurable |

### 7.2 Missing Features

| Feature | Priority | Description |
|---------|----------|-------------|
| Unit Tests | High | Limited test coverage |
| Dry Run Mode | Medium | Preview processing without API calls |
| Quality Sampling | Medium | Random sample validation during processing |
| Webhook Notifications | Low | Alert when batch completes |
| Multi-language Support | Low | Prompt only in English |

### 7.3 Potential Improvements

1. **Extract Common Utilities**
   ```python
   # Proposed: app/utils/transcription_utils.py
   class RateLimiter:
       """Shared rate limiting implementation"""

   class CostTracker:
       """Shared cost tracking"""

   def auto_repair_response(data: dict) -> dict:
       """Shared response repair logic"""
   ```

2. **Add Configuration Object**
   ```python
   # Proposed: app/config/transcription_config.py
   @dataclass
   class TranscriptionConfig:
       model: str
       max_workers: int
       max_cost: float | None
       rate_limits: RateLimits
       output_dir: Path
   ```

3. **Implement Strategy Pattern for Models**
   ```python
   # Proposed: app/transcription/base.py
   class TranscriptionProvider(ABC):
       @abstractmethod
       def transcribe(self, document: Path) -> TranscriptionResult:
           pass

   class OpenAIProvider(TranscriptionProvider):
       pass

   class ClaudeProvider(TranscriptionProvider):
       pass
   ```

---

## 8. Testing Recommendations

### 8.1 Unit Tests Needed

| Test File | Coverage Target |
|-----------|-----------------|
| `test_auto_repair.py` | `auto_repair_response()` edge cases |
| `test_rate_limiter.py` | Rate limiting logic |
| `test_cost_tracker.py` | Thread-safe cost tracking |
| `test_state_manager.py` | State persistence, checkpoints |
| `test_schema_validation.py` | JSON schema validation |

### 8.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_openai_single.py` | Single document transcription with mock |
| `test_claude_single.py` | Single document with Claude mock |
| `test_batch_processing.py` | Batch execution with graceful shutdown |
| `test_resume.py` | Resume from interrupted session |

### 8.3 Test Data

```python
# tests/fixtures/
# - sample_transcript_valid.json   # Valid schema
# - sample_transcript_flat.json    # Needs auto_repair
# - sample_transcript_missing.json # Missing required fields
# - sample_pdf_single.pdf          # 1-page test PDF
# - sample_pdf_multi.pdf           # Multi-page test PDF
```

---

## 9. Security Considerations

### 9.1 API Key Handling

```python
# transcribe_openai.py:54-58
load_dotenv(ROOT_DIR / '.env')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

- Keys loaded from `.env` file (gitignored)
- No keys hardcoded
- No key logging

### 9.2 File Handling

- All file paths validated via `Path` objects
- No shell injection vulnerabilities
- Output directories created with `mkdir(parents=True, exist_ok=True)`

### 9.3 Data Privacy

- Transcripts stored locally only
- No external data transmission beyond API calls
- Sensitive content tracking for audit purposes

---

## 10. Recommendations Summary

### Priority 1 (High)

1. **Add Unit Tests** - Critical for reliability
2. **Complete gpt-4.1-nano transcription** - 77% of documents remain
3. **Document API rate limits** - Avoid throttling during full pass

### Priority 2 (Medium)

1. **Extract common utilities** - Reduce duplication
2. **Add dry-run mode** - Preview before processing
3. **Implement quality sampling** - Validate during batch processing

### Priority 3 (Low)

1. **Refactor to provider pattern** - Cleaner architecture
2. **Add webhook notifications** - Batch completion alerts
3. **Improve type hints** - Better IDE support

---

## 11. Appendix: File Locations

| Component | Path |
|-----------|------|
| OpenAI Transcription | `app/transcribe_openai.py` |
| Claude Transcription | `app/transcribe_claude.py` |
| State Management | `app/state_manager.py` |
| Batch Processing | `app/batch_processor.py` |
| Full Pass CLI | `app/full_pass.py` |
| Prompt v2 | `app/prompts/metadata_prompt_v2.md` |
| JSON Schema | `app/prompts/schemas/metadata_schema.json` |
| Configuration | `app/config.py` |
| Makefile | `Makefile` |

---

*Report generated for Desclasificados project code assessment*
