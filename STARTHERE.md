# STARTHERE - CIA Declassified Documents Project

**Start every development session by reading this file.**

## What This Is

A system for processing, searching, and analyzing ~20,000 declassified CIA documents about the Chilean dictatorship (1973-1990). The project:

1. **Extracts** images from PDF documents
2. **Transcribes** them using OpenAI vision models (GPT-4o)
3. **Indexes** them in a vector database
4. **Answers questions** using RAG (Retrieval-Augmented Generation) with Claude or OpenAI

## Current Status

✅ **Production Ready:**
- RAG system with 5,611 documents indexed (6,929 chunks)
- Dual LLM support: **Claude 3.5 Haiku (default)** and OpenAI GPT-4o-mini
- 83% test success rate on research queries
- Interactive and CLI query modes
- Automated testing infrastructure
- **NEW:** Prompt decoupling - prompts now in external files for easy maintenance
- **NEW:** PDF and image processing support
- **NEW:** Integrated with official repository (desclasificados-swd)

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

**Note:** The transcription script shows a cost estimate before processing and asks for confirmation. This prevents unexpected API charges.

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
