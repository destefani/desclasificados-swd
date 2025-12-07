# STARTHERE - CIA Declassified Documents Project

**Start every development session by reading this file.**

---

## ⚠️ CRITICAL: PDF vs JPEG Issue

**ALWAYS use PDFs for transcription, NEVER use JPEGs.**

| Issue | Impact |
|-------|--------|
| ~70% of PDFs have multiple pages | JPEGs only contain the first page |
| 21,512 PDFs → 21,512 JPEGs | **~65,000+ pages were being missed** |
| Existing JPEG-based transcripts | **Incomplete - missing most content** |

**The `data/images/` directory contains ONLY first pages. DO NOT USE for transcription.**

**Correct source:** `data/original_pdfs/` - Complete multi-page documents

---

## What This Is

A system for processing, searching, and analyzing ~20,000 declassified CIA documents about the Chilean dictatorship (1973-1990). The project:

1. **Transcribes** PDFs directly using OpenAI vision models (all pages)
2. **Indexes** them in a vector database
3. **Answers questions** using RAG (Retrieval-Augmented Generation) with Claude or OpenAI

## Current Status

### Transcription Progress

| Metric | Value |
|--------|-------|
| **Total Documents** | 21,512 |
| **Transcribed (gpt-5-mini)** | 1,125 |
| **Remaining** | ~20,387 |
| **Primary Model** | gpt-5-mini |

### Quality Evaluation (gpt-5-mini batch)

| Metric | Value |
|--------|-------|
| **Documents Evaluated** | 1,125 |
| **Mean Confidence** | 0.861 |
| **High Confidence (>0.8)** | 71.7% |
| **Low Confidence (<0.6)** | 0.4% |
| **Validation Errors** | 0 |
| **Issues Fixed** | 1 (empty reviewed_text) |

See `investigations/` for documented quality issues and resolutions.

✅ **Production Ready:**
- RAG system with 5,611 documents indexed (6,929 chunks)
- Dual LLM support: **Claude 3.5 Haiku (default)** and OpenAI GPT-4o-mini
- 83% test success rate on research queries
- Interactive and CLI query modes
- Automated testing infrastructure
- **NEW:** Shared utilities module (`app/utils/`) for code reuse
- **NEW:** Comprehensive unit tests (65 tests passing)
- **NEW:** Prompt v2.1 with sensitive content tracking (financial, violence, torture)
- Prompt decoupling - prompts now in external files for easy maintenance
- PDF and image processing support

⚠️ **Known Limitations:**
- 77% of documents still need transcription
- Coverage gaps in late-period documents (1988-1990)
- Some thematic areas underrepresented (economics, culture)
- Claude API requires valid credit balance (can use OpenAI as fallback)

## Quick Setup (First Time)

```bash
# 1. Install dependencies
make install

# 2. Set up environment variables (create .env file)
cp .env.example .env
# Then edit .env and add your API keys:
#   OPENAI_API_KEY=sk-...        # Required for embeddings
#   ANTHROPIC_API_KEY=sk-ant-... # Required for Claude (default LLM)

# 3. Build the RAG index (one-time, ~10-15 min, ~$0.60)
uv run python -m app.rag.cli build
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys

## Most Common Commands

### RAG Queries (Primary Use Case)

```bash
# Query with Claude (default, recommended)
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?"

# Interactive mode for exploratory research
uv run python -m app.rag.cli interactive

# Query with filters
uv run python -m app.rag.cli query "Human rights violations" \
  --start-date 1976-01-01 --end-date 1976-12-31 \
  --keywords "OPERATION CONDOR" --top-k 10

# Use OpenAI instead of Claude
uv run python -m app.rag.cli query "Your question" --llm openai

# Database stats
uv run python -m app.rag.cli stats
```

### Document Transcription

```bash
# Process all remaining documents (shows estimate, asks confirmation)
make transcribe

# Process specific number of files
make transcribe N=100

# With budget limit (stops when cost reaches limit)
make transcribe N=1000 BUDGET=50

# Skip confirmation prompt
make transcribe YES=1

# Check status without processing
make transcribe-status
```

**Features:**
- Automatically resumes from where it left off
- Shows cost estimate before processing
- Graceful shutdown with Ctrl+C (just run again to continue)
- Budget limiting to control costs

**Estimated cost:** ~$0.0038/document with gpt-4.1-mini

**Fast processing (for higher OpenAI tiers):**

```bash
# Tier 4+ (~30-45 min for full corpus)
MAX_TOKENS_PER_MINUTE=2000000 uv run python -m app.transcribe --workers 50 --yes

# Tier 3 (~1 hour)
MAX_TOKENS_PER_MINUTE=800000 uv run python -m app.transcribe --workers 30 --yes

# Tier 2 (~1.5 hours)
MAX_TOKENS_PER_MINUTE=450000 uv run python -m app.transcribe --workers 20 --yes
```

Check your tier at: https://platform.openai.com/settings/organization/limits

### Quality Evaluation

```bash
# Statistics for transcripts
make eval-stats MODEL=gpt-5-mini

# Validate all transcripts for issues
make eval-validate MODEL=gpt-5-mini

# Generate stratified sample for manual review
make eval-sample MODEL=gpt-5-mini

# Full evaluation report
make eval-report MODEL=gpt-5-mini
```

### Analysis & Visualization

```bash
# Generate HTML report with timeline
make analyze

# Create matplotlib visualizations
make visualize
```

### Testing

```bash
# Run unit tests (65 tests for utilities)
uv run pytest tests/unit/ -v

# Run all tests
make test

# Test Claude integration
uv run python test_claude_integration.py
```

## Project Structure

```
.
├── app/
│   ├── rag/                    # RAG system (main feature)
│   │   ├── cli.py              # CLI interface
│   │   ├── qa_pipeline_claude.py   # Claude integration
│   │   ├── qa_pipeline.py      # OpenAI integration
│   │   ├── vector_store.py     # ChromaDB operations
│   │   └── README.md           # RAG documentation
│   ├── prompts/                # External prompt files
│   │   ├── metadata_prompt_v2.md   # Document transcription prompt (v2)
│   │   ├── schemas/            # JSON schemas for validation
│   │   └── README.md           # Prompt documentation
│   ├── utils/                  # Shared utilities (NEW)
│   │   ├── cost_tracker.py     # Thread-safe API cost tracking
│   │   ├── rate_limiter.py     # Sliding window rate limiting
│   │   └── response_repair.py  # Auto-repair and validation
│   ├── transcribe.py           # Document transcription (main)
│   ├── analyze_documents.py    # Metadata aggregation
│   └── visualize_transcripts.py  # Matplotlib charts
├── data/
│   ├── original_pdfs/          # Source PDFs (21,512)
│   ├── images/                 # Extracted images (21,512)
│   ├── generated_transcripts/  # Model-specific output dirs
│   │   ├── gpt-4.1-mini/       # 4,924 transcripts
│   │   ├── chatgpt-5-1/        # 1,352 transcripts
│   │   └── ...
│   └── vector_db/              # ChromaDB index
├── docs/                       # Comprehensive documentation
├── investigations/             # Documented quality issues (NEW)
├── reports/                    # Assessment reports
├── tests/
│   └── unit/                   # Unit tests (65 tests)
└── Makefile                    # Task automation
```

## Key Files to Know

| File | Purpose |
|------|---------|
| **STARTHERE.md** | This file - read first every session |
| **CLAUDE.md** | Instructions for Claude Code about the project |
| **reports/*.md** | Assessment reports and analysis |
| **docs/PROJECT_CONTEXT.md** | Historical context, use cases, ethics |
| **app/rag/README.md** | Complete RAG system documentation |
| **app/prompts/PROMPT_V2_GUIDE.md** | Prompt engineering guide |
| **Makefile** | All available commands (`make help`) |

## Common Workflows

### Research a Historical Question

```bash
# Start interactive mode
uv run python -m app.rag.cli interactive

# Ask questions like:
# - "What did the CIA know about the Letelier assassination?"
# - "How did the CIA's assessment of Pinochet change over time?"
# - "What was Operation Condor?"
```

### Process New Documents

```bash
# 1. Add PDFs to data/original_pdfs/
# 2. Extract images (if not already done)
# 3. Transcribe new images
make transcribe N=100

# 4. Update RAG index
uv run python -m app.rag.cli build
```

### Compare LLM Responses

```bash
# Same query with different LLMs
uv run python -m app.rag.cli query "Your question" --llm claude
uv run python -m app.rag.cli query "Your question" --llm openai
```

## Cost Estimates

### One-Time Setup
- Build RAG index: ~$0.60 (5,611 docs)

### Document Transcription (with gpt-4o-mini)
- Per document: ~$0.0008-0.0010
- 100 documents: ~$0.08-0.10
- 1,000 documents: ~$0.80-1.00
- All 21,502 images: ~$17-21

**Note:** Transcription script shows cost estimate before processing and requires confirmation.

### Per-Query
- Claude 3.5 Haiku (default): ~$0.02-0.03
- OpenAI GPT-4o-mini: ~$0.02-0.03
- Claude 3.5 Sonnet (complex): ~$0.06-0.10

### Monthly (with Claude Haiku)
- 100 queries: ~$2-3
- 1,000 queries: ~$20-30

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ANTHROPIC_API_KEY not found` | Add to `.env` file |
| `Vector database is empty` | Run `uv run python -m app.rag.cli build` |
| Rate limit errors | Adjust `EMBEDDING_RPS` in `app/rag/config.py` |
| No transcripts found | Check `data/generated_transcripts_v1/` has JSON files |

## Next Steps Based on Testing

**Priority Improvements:**
1. Expand document coverage (1988-1990 period)
2. Add hybrid search (BM25 + vector)
3. Implement query rewriting
4. Build Streamlit web interface

See `docs/PROJECT_CONTEXT.md` for detailed roadmap.

## Getting Help

```bash
# Show all make commands
make help

# RAG CLI help
uv run python -m app.rag.cli --help

# Test Claude integration
uv run python test_claude_integration.py
```

## Integration with Official Repository

This project has been integrated with the official repository at `github.com/destefani/desclasificados-swd`:

**Adopted from official repo:**
- ✅ Prompt decoupling: Prompts moved to `app/prompts/metadata_prompt.md`
- ✅ Prompt documentation: `app/prompts/README.md`
- ✅ PDF direct processing in `transcribe.py`

**Our contributions ready for upstream:**
- Complete RAG system with 5,611 indexed documents
- Claude integration for better answer quality
- Comprehensive documentation suite
- Testing infrastructure
- Analysis and visualization tools

**Key differences:**
- Official repo: PDF processing only
- Our repo: Both PDF and image processing
- Official repo: OpenAI only
- Our repo: Claude (recommended) + OpenAI fallback

## Important Notes

- **Default LLM is Claude** (better citations, lower hallucination) but requires valid credit balance
- **OpenAI fallback available** - use `--llm openai` flag if Claude credits are low
- **Embeddings always use OpenAI** (Claude has no embedding API)
- **Use UV for all Python commands** (not pip or virtualenv)
- **Don't commit `.env`** (contains API keys)
- **Always test after implementing features** (see TESTING_CLAUDE.md)
- **Prompts are now external** - edit `app/prompts/metadata_prompt.md` to modify transcription behavior

## Quick Reference

```bash
# The 5 commands you'll use most:
make transcribe                    # Process documents
make transcribe-status             # Check progress
make rag-interactive               # Research questions
make rag-query QUERY="..."         # Single query
make test                          # Run tests
```

---

**Read this file at the start of every session. For deeper context, see:**
- `CLAUDE.md` - Project instructions for AI assistant
- `docs/PROJECT_CONTEXT.md` - Historical context and goals
- `app/rag/README.md` - RAG system details
- `TESTING_CLAUDE.md` - Testing procedures
