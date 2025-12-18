# STARTHERE - CIA Declassified Documents Project

**Start every development session by reading this file.**

---

## 🆕 RAG Versioning Implemented (2025-12-18)

**Branch:** `research/disambiguation`

The RAG system now supports versioned indexes with transcript source tracking.

**New commands:**
```bash
# List available RAG indexes with source metadata
uv run python -m app.rag.cli list

# Build a versioned RAG index (creates rag-v1.0.0/)
uv run python -m app.rag.cli build --rag-version 1.0.0

# Query/stats with specific version
uv run python -m app.rag.cli query "Pinochet" --rag-version 1.0.0
uv run python -m app.rag.cli stats --rag-version 1.0.0
```

**What it tracks:**
- Schema version of source transcripts (v2.0.0, v2.2.0, etc.)
- Model used for transcription (gpt-5-mini, etc.)
- Document counts per source
- Embedding model and chunk settings

**Directory structure:**
- `data/rag-v{version}/` - Versioned RAG indexes with `manifest.json`
- `data/vector_db/` - Legacy unversioned index (still supported)

**Files changed:** `app/rag/config.py`, `app/rag/vector_store.py`, `app/rag/embeddings.py`, `app/rag/cli.py`, `app/rag/README.md`

---

## 🆕 Entity Disambiguation Research Started (2025-12-16)

**Branch:** `research/disambiguation`

**Problem:** The analysis report shows 1,055 people entries with significant disambiguation issues:
- **28% (298 entries)** marked as `[FIRST NAME UNKNOWN]`
- Duplicate entries for same person (e.g., LETELIER, ORLANDO + LETELIER, [FIRST NAME UNKNOWN])
- OCR errors creating spelling variants (MOFFITT/MOFFIT, RONNI/RONNIE)
- Non-person entities extracted as people (EMBASSY, AMEMBASSY, SECSTATE)

**Key examples:**
| Entity | Issue |
|--------|-------|
| LETELIER, ORLANDO (1,048 docs) + LETELIER, [FIRST NAME UNKNOWN] (257 docs) | Same person, split |
| GILLESPIE, [FIRST NAME UNKNOWN] (366 docs) | Likely Charles A. Gillespie, US Ambassador |
| BARNES, [FIRST NAME UNKNOWN] (319 docs) | Likely Harry G. Barnes Jr., US Ambassador |
| AMEMBASSY (45 entries), EMBASSY (19 entries) | Not people |

**Research document:** `docs/DISAMBIGUATION_RESEARCH.md`

**Recommended approaches:**
1. Rule-based filtering (remove EMBASSY, AMEMBASSY, etc.)
2. OCR correction mappings (MOFFIT→MOFFITT)
3. Knowledge base linking (key historical figures)
4. LLM-assisted disambiguation for context-dependent cases

**Next steps:** Implement Phase 1 quick wins (filtering, OCR corrections, top 50 canonical names)

---

## 🆕 Full Report Sections Complete (2025-12-14)

**PR #27: GitHub Pages report now includes all sections.**

The full report generator (`generate_full_html_report`) was missing several sections from the basic report. These have been added:

- Financial: Purposes and Financial Actors tables
- Confidence: Common Concerns table
- Document Types section with Languages subsection
- Locations: Countries, Cities, Other Places tables
- People: Recipients table

**Deploy the updated report:**
```bash
make deploy  # Generates report and pushes to GitHub Pages
```

---

## 🆕 Historical Research Plan Ready (2025-12-13)

**Phase 1 corpus analysis complete.** Ready to begin historical research.

**Quick Start:**
```bash
# Re-run corpus analysis after more transcription
uv run python -c "..." # See research/historical/findings/CORPUS_ANALYSIS_PHASE1.md

# Query the RAG system for research
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?"
uv run python -m app.rag.cli interactive
```

**Key Findings from 450 documents:**
- Letelier Assassination: 132 mentions (best documented case)
- CIA Funding/Covert Action: 90 mentions each
- 40 Committee: 86 mentions
- Peak year: 1970 (Allende election)

**Next Steps:**
1. Continue transcription to increase corpus
2. Re-run corpus analysis
3. Begin Case Study 1: Letelier Assassination
4. Begin Track A: Operation Condor

**See:** `research/historical/RESEARCH_PLAN.md` for full 6-phase plan

---

## 🆕 NEW: Chunked Processing for Large PDFs (2025-12-13)

**Large documents (>30 pages) are now automatically split into chunks.**

This fixes the "incomplete output" issue where large PDFs (89-139 pages) were truncated.

```bash
# Retry incomplete documents (with chunked processing)
uv run python -m app.transcribe --retry-incomplete --yes

# Retry all failed documents
uv run python -m app.transcribe --retry-failed --yes
```

**How it works:**
- Documents >30 pages are split into 20-page chunks
- Chunks are processed **in parallel** (up to 4 concurrent) for faster processing
- Results are merged with deduplicated metadata

**Performance:** A 139-page document (7 chunks) now processes ~4x faster with parallel chunk processing.

**Files added:**
- `app/utils/chunked_pdf.py` - PDF splitting and result merging
- `tests/unit/test_chunked_pdf.py` - 15 unit tests

---

## 🆕 Batch API Implementation (2025-12-07)

**Batch processing is available for 50% cost savings.**

```bash
# Quick start - process 1000 docs with batch API
make batch-run N=1000 YES=1

# Or use CLI directly
uv run python -m app.batch run -n 1000 --poll --yes
```

| Method | Cost | Time | Savings |
|--------|------|------|---------|
| Synchronous | ~$498 | ~2.5 hours | - |
| **Batch API** | ~$249 | ≤24 hours | **$249 (50%)** |

See [Batch Processing section](#batch-processing-50-cost-savings) below for full documentation.

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
| **Transcribed (gpt-5-mini)** | 5,666 |
| **Remaining** | ~15,846 |
| **Primary Model** | gpt-5-mini |

### Quality Evaluation (gpt-5-mini) - Updated 2025-12-13

| Metric | Value |
|--------|-------|
| **Documents Evaluated** | 5,666 |
| **Mean Confidence** | 0.877 |
| **High Confidence (>0.85)** | 82.7% |
| **Medium Confidence (0.70-0.85)** | 17.0% |
| **Low Confidence (<0.70)** | 0.2% (13 docs) |
| **Validation Errors** | 0 |
| **Missing Documents** | 14 (content filtered or incomplete) |

See `research/investigations/004-gpt5-mini-quality-evaluation.md` for full evaluation details.

**Dataset Progress Log:** `data/generated_transcripts/gpt-5-mini/PROGRESS_LOG.md`

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

### Batch Processing (50% Cost Savings)

For large transcription jobs, use the Batch API for 50% cost reduction:

```bash
# All-in-one: prepare, submit, poll, retrieve
uv run python -m app.batch run -n 1000 --poll --yes

# Step-by-step workflow
uv run python -m app.batch prepare -n 1000     # Create batch file
uv run python -m app.batch submit-file <file>   # Upload and submit
uv run python -m app.batch poll <batch_id>      # Wait for completion
uv run python -m app.batch retrieve <batch_id>  # Download results

# Check pending documents
uv run python -m app.batch pending

# List batch jobs
uv run python -m app.batch jobs
```

**Cost comparison:**
| Method | Cost per doc | 18k docs | Time |
|--------|-------------|----------|------|
| Synchronous | ~$0.0275 | ~$498 | ~2.5 hours |
| Batch API | ~$0.0138 | ~$249 | ≤24 hours |

See `docs/BATCH_API_IMPLEMENTATION_PLAN.md` for technical details.

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

See `docs/QUALITY_TESTING_METHODS.md` for comprehensive quality testing documentation.

### Analysis & Visualization

```bash
# Generate HTML report with timeline
make analyze

# Generate GitHub Pages report with external PDF viewer
make github-pages-external

# Create matplotlib visualizations
make visualize
```

**GitHub Pages report** outputs to `docs/index.html` with clickable PDF links to the external viewer at `declasseuucl.vercel.app`. After generation, push to GitHub and enable Pages from the `docs/` folder.

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
├── research/                   # Research directory
│   ├── technical/             # Technical research (prompts, RAG, etc.)
│   ├── investigations/        # Documented quality issues
│   └── historical/            # Historical research (NEW)
│       ├── RESEARCH_PLAN.md   # 6-phase research methodology
│       ├── findings/          # Analysis results
│       ├── themes/            # Operation Condor, Human Rights, etc.
│       └── cases/             # Letelier, Caravan of Death, etc.
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
| **research/historical/RESEARCH_PLAN.md** | Historical research plan (6 phases) |
| **research/historical/findings/** | Corpus analysis and research findings |
| **reports/*.md** | Assessment reports and analysis |
| **docs/PROJECT_CONTEXT.md** | Historical context, use cases, ethics |
| **docs/QUALITY_TESTING_METHODS.md** | Quality testing documentation |
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

### Historical Research Workflow (NEW)

```bash
# 1. Re-run corpus analysis after transcription progress
# See the Python code in research/historical/findings/CORPUS_ANALYSIS_PHASE1.md

# 2. Use RAG for specific research questions
uv run python -m app.rag.cli query "Documents about Letelier" --start-date 1976-01-01 --end-date 1976-12-31
uv run python -m app.rag.cli query "Operation Condor intelligence sharing"

# 3. Document findings in research/historical/
# - themes/operation-condor/
# - cases/letelier-assassination/
# - findings/
```

**Research Priority Order:**
1. Letelier Assassination (132 keyword mentions - best documented)
2. Political Interference / Covert Action (90+ documents)
3. Operation Condor (38 DINA mentions - needs more transcription)

See `research/historical/RESEARCH_PLAN.md` for full methodology.

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
