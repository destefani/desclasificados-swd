# STARTHERE - CIA Declassified Documents Project

**Start every development session by reading this file.**

---

## ACTIVE: GPT-4.1-mini Full Pass (December 2024)

**Status**: Ready to run full pass via Batch API
**Model**: `gpt-4.1-mini` (produces full OCR text with native PDF support)
**Cost**: ~$59 with Batch API (50% discount)

### Progress
- **Processed:** 6,405 / 21,512 files (29.8%)
- **Primary model:** gpt-4.1-mini (4,924 files)
- **Success rate:** 100%
- **Avg confidence:** 0.922

```bash
# Check how many done
ls data/generated_transcripts/gpt-4.1-mini/*.json 2>/dev/null | wc -l
```

### RECOMMENDED: Batch API (50% OFF) ~$59

The batch command automatically splits 21,402 files into 11 batches of 2,000 files each (to stay under OpenAI's 512MB upload limit).

**Run in tmux (recommended):**
```bash
# Start tmux session
tmux new -s batch-upload

# Submit all 11 batches
uv run python -m app.transcribe_openai \
  --batch \
  --model gpt-4.1-mini \
  --resume \
  --yes

# Detach: Ctrl+B then D
# Reattach: tmux attach -t batch-upload
```

**Check status:**
```bash
uv run python -m app.transcribe_openai --batch-list
```

**Download results for each batch:**
```bash
uv run python -m app.transcribe_openai \
  --batch-download <BATCH_ID> \
  --model gpt-4.1-mini
```

**Important notes:**
- Each batch takes 2-4 hours to process (max 24h)
- Results are stored for ~30 days
- Download results as soon as batches complete
- Batch session info saved in `data/batch_jobs/`

### Alternative: Sync API (~$118)
```bash
tmux new -s openai-full-pass
uv run python -m app.transcribe_openai \
  --model gpt-4.1-mini \
  --max-workers 10 \
  --resume \
  --yes
```

### Monitor
```bash
watch -n 10 'ls data/generated_transcripts/gpt-4.1-mini/*.json 2>/dev/null | wc -l'
```

### Key Files
- `app/transcribe_openai.py` - OpenAI transcription module (native PDF)
- `research/GPT41_NANO_FULL_PASS_PLAN.md` - Detailed plan
- `reports/Model_OCR_Comparison_Report.pdf` - Model comparison

### Quality Notes
- Phase 2 tested: 89% success, full OCR text confirmed
- Multi-page PDFs work (2-6 pages tested)
- Financial amounts extracted correctly ($1,240,000 example)
- Confidence scores: 0.85-0.90

---

## What This Is

A system for processing, searching, and analyzing ~20,000 declassified CIA documents about the Chilean dictatorship (1973-1990). The project:

1. **Extracts** images from PDF documents
2. **Transcribes** them using OpenAI vision models (GPT-5-nano recommended)
3. **Indexes** them in a vector database
4. **Answers questions** using RAG (Retrieval-Augmented Generation) with Claude or OpenAI

## Current Status

✅ **Production Ready:**
- RAG system with 5,611 documents indexed (6,929 chunks)
- Dual LLM support: **Claude 3.5 Haiku (default)** and OpenAI GPT-4o-mini
- 83% test success rate on research queries
- Interactive and CLI query modes
- Automated testing infrastructure
- Prompt decoupling - prompts now in external files for easy maintenance
- PDF and image processing support
- Integrated with official repository (desclasificados-swd)
- **NEW:** Sensitive content tracking (financial, violence, torture) - structured extraction of money flows, violent incidents, and human rights abuses

⚠️ **Known Limitations:**
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
# Transcribe 1 file (default - uses Prompt v2)
make transcribe

# Transcribe 10 files (shows cost estimate & asks for confirmation)
make transcribe-some FILES_TO_PROCESS=10

# Resume transcription (skip existing, shows estimate for remaining files only)
make resume
```

**Prompt v2 (Default):** Uses OpenAI Structured Outputs with 100% schema compliance, confidence scoring, and enhanced metadata extraction. See `app/prompts/PROMPT_V2_GUIDE.md`.

**Sensitive Content Tracking (NEW):** Documents are now analyzed for:
- `financial_references` - Money amounts, actors (CIA, ITT, etc.), purposes (campaign funding, bribes, covert ops)
- `violence_references` - Incident types (assassination, bombing, kidnapping), victims, perpetrators
- `torture_references` - Detention centers (Villa Grimaldi, Londres 38), victims, perpetrators

**Note:** The transcription script shows a cost estimate before processing and asks for confirmation. This prevents unexpected API charges.

### Full Pass Processing (NEW)

For processing all 21,512 documents with batch control, cost limits, and resume capability:

```bash
# Interactive mode - confirm each batch (recommended for first use)
make full-pass

# Auto mode with budget limit
make full-pass-auto BATCH_SIZE=medium MAX_COST=50

# Resume from previous session
make full-pass-resume

# Check current status
make full-pass-status

# Reset state and start fresh
make full-pass-reset
```

**Features:**
- ✅ **Batch control** - Process in chunks (tiny=10, small=100, medium=500, large=1000)
- ✅ **Cost control** - Set budget limits and track spending in real-time
- ✅ **Time control** - Set max hours, schedule processing windows
- ✅ **Stop/Resume** - Graceful shutdown (Ctrl+C) and resume from exact position
- ✅ **Quality monitoring** - Real-time success rates, confidence tracking
- ✅ **Checkpoints** - Auto-save every 100 documents
- ✅ **Interim reports** - Progress summaries at intervals

**Estimated cost for full pass:** See [Cost Estimates](#cost-estimates) section - depends heavily on model choice.

See `research/FULL_PASS_PLAN.md` for complete documentation.

### Analysis & Visualization

```bash
# Generate HTML report with timeline
make analyze

# Create matplotlib visualizations
make visualize
```

### Testing

```bash
# Test Claude integration
uv run python test_claude_integration.py

# Run all tests
make test
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
│   ├── prompts/                # External prompt files (NEW)
│   │   ├── metadata_prompt.md  # Document transcription prompt
│   │   └── README.md           # Prompt documentation
│   ├── transcribe.py           # PDF transcription (updated)
│   ├── transcribe_v2.py        # Production image transcription
│   ├── analyze_documents.py    # Metadata aggregation
│   └── visualize_transcripts.py  # Matplotlib charts
├── data/
│   ├── original_pdfs/          # Source PDFs
│   ├── images/                 # Extracted images
│   ├── generated_transcripts/  # Structured JSON output
│   └── vector_db/              # ChromaDB index
├── docs/                       # Comprehensive documentation
├── tests/                      # Test suite
└── Makefile                    # Task automation
```

## Key Files to Know

| File | Purpose |
|------|---------|
| **STARTHERE.md** | This file - read first every session |
| **CLAUDE.md** | Instructions for me (Claude Code) about the project |
| **TESTING_CLAUDE.md** | How to test Claude integration |
| **docs/PROJECT_CONTEXT.md** | Historical context, use cases, ethics |
| **app/rag/README.md** | Complete RAG system documentation |
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
make transcribe-some FILES_TO_PROCESS=<N>

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

### Document Transcription - IMPORTANT COST WARNING

**Real-world experience (December 2024):** Processing 1,352 documents with GPT-4o cost ~$100 USD (~$0.074/doc). The original estimates below were wrong for vision tasks.

#### Why Vision Costs More Than Expected
GPT-4o-mini uses ~33x more tokens per image while being 33x cheaper per token, resulting in **similar or higher costs** than GPT-4o for vision tasks. This is a known pricing quirk.

#### Model Comparison for Vision/PDF Tasks (December 2024)

| Model | Input/1M | Output/1M | Full OCR? | Full pass (21,512) |
|-------|----------|-----------|-----------|-------------------|
| **gpt-4.1-mini** | $0.40 | $1.60 | **YES** | **~$118** |
| gpt-4.1-nano | $0.10 | $0.40 | NO (placeholder) | N/A |
| Claude Haiku | $0.25 | $1.25 | NO (placeholder) | N/A |
| Claude Sonnet | $3.00 | $15.00 | YES | ~$1,010 |
| GPT-4o | $2.50 | $10.00 | YES | ~$1,590 |

#### Recommendation: gpt-4.1-mini for Full Pass

**Why gpt-4.1-mini:**
- Native PDF support (no image conversion needed)
- Produces actual OCR text (not placeholders)
- 88% cheaper than Claude Sonnet
- All pages of multi-page PDFs processed
- Quality validated: 0.85-0.90 confidence scores

**Before running full pass:**
1. Test on 50-100 documents first
2. Validate transcription quality
3. Calculate actual per-document cost
4. Then scale up

#### Current Progress (Dec 2024)
- **Processed:** 6,405 documents (29.8%)
- **Remaining:** 15,107 documents
- **Archive (v1):** 5,611 docs (older format, in RAG index)
- **Open PR:** [#11](https://github.com/destefani/desclasificados-swd/pull/11) - Sensitive content tracking + multi-model support

### Per-Query (RAG)
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
uv run python -m app.rag.cli interactive          # Research questions
uv run python -m app.rag.cli query "..."          # Single query
make transcribe-some FILES_TO_PROCESS=10          # Process documents
make analyze                                      # Generate reports
uv run python test_claude_integration.py          # Test system
```

---

**Read this file at the start of every session. For deeper context, see:**
- `CLAUDE.md` - Project instructions for AI assistant
- `docs/PROJECT_CONTEXT.md` - Historical context and goals
- `app/rag/README.md` - RAG system details
- `TESTING_CLAUDE.md` - Testing procedures
