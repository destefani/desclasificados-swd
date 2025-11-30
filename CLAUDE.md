# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project processes declassified CIA documents related to the Chilean dictatorship (1973-1990). It extracts images from PDFs, transcribes them using OpenAI's vision models (GPT-4o/GPT-4o-mini), and generates structured JSON metadata with standardized historical information for research purposes.

**For detailed context, use cases, and ethical considerations, see [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md).**

### The Problem
The US government declassified ~20,000 CIA documents about the Chilean dictatorship, but the volume makes them practically inaccessible. This project creates a searchable, structured database to enable:
- Question answering from the CIA perspective
- Fact checking historical claims
- Research and analysis at scale
- Public access to primary sources

## Core Architecture

### Data Pipeline Flow

1. **PDF Processing** → Extract images from original PDFs (`data/original_pdfs/`)
2. **Image Transcription** → Process images (`data/images/`) with vision models to generate structured JSON transcripts
3. **Analysis & Visualization** → Aggregate metadata and create timelines, reports, and interactive dashboards

### Key Modules

- **`app/transcribe.py`** - Image transcription using OpenAI Chat Completions API with vision models (reads from `data/images/`)
- **`app/transcribe_v2.py`** - Production transcription with rate limiting, JSON schema validation, and robust error handling (uses standard Chat Completions API)
- **`app/analyze_documents.py`** - Aggregates metadata from JSON transcripts and generates HTML reports with timeline charts
- **`app/visualize_transcripts.py`** - Creates matplotlib visualizations (classification distribution, timeline, keywords)
- **`app/config.py`** - Centralized configuration for paths and logging
- **`app/data/pdf_extractor.py`** - Extracts text from PDFs using PyPDF2
- **`tests/test_app.py`** - Streamlit app for interactive document exploration

### Data Structure

```
data/
├── archive/                    # Historical transcription outputs (archived)
│   ├── generated_transcripts_v1/  # Legacy JSON (5,613 files)
│   ├── generated_transcripts_v2/  # Previous JSON (14 files)
│   ├── transcripts_pdf/           # PDF transcripts (21,512 files)
│   └── transcripts_txt/           # TXT transcripts (18,363 files)
├── original_pdfs/              # Source PDF files (21,512 files)
├── images/                     # Extracted document images - JPEG (21,512 files)
├── generated_transcripts/      # Current JSON transcriptions (active work)
├── vector_db/                  # ChromaDB vector database for RAG
└── session.json                # Session data
```

**Note:** The `data/archive/` directory contains all historical transcription outputs. Current transcription work goes to `data/generated_transcripts/`.

### Transcript JSON Schema

Each transcript follows a strict schema with:
- **metadata**: Document metadata (dates in ISO 8601: YYYY-MM-DD, names as "LAST, FIRST", standardized classification levels, etc.)
- **original_text**: Raw transcription with OCR artifacts
- **reviewed_text**: Cleaned/corrected version

See `app/transcribe_v2.py:103-137` for the complete JSONSchema definition.

## Development Commands

This project uses **UV** for dependency management and **Make** for task automation.

### Setup

```bash
# Install dependencies
make install

# Install with dev dependencies
make install-dev
```

### Transcription

```bash
# Transcribe 1 file (default)
make transcribe

# Transcribe specific number of files
make transcribe-some FILES_TO_PROCESS=10

# Transcribe all files (uses MAX_WORKERS=32 by default)
make transcribe-all

# Resume transcription (skip existing JSONs)
make resume

# Resume with limited files
make resume-some FILES_TO_PROCESS=10
```

**Cost Estimation**: Before processing, the script displays an estimated cost based on the number of files and model used, then asks for confirmation. This helps prevent unexpected API charges. The estimate accounts for resume mode (skips already-transcribed files).

**Important**: The default transcription script (`app/transcribe.py`) uses `OPENAI_MODEL` env var and includes cost estimation, rate limiting, and JSON schema validation. Use `app/transcribe_v2.py` for alternative implementation with different rate limiting configuration.

### Analysis & Visualization

```bash
# Generate HTML report with timeline
make analyze

# Create matplotlib visualizations
make visualize
```

### Testing & Code Quality

```bash
# Run tests
make test

# Lint code
make lint

# Format code
make format
```

### Cleanup

```bash
# Remove all caches and virtual environment
make clean

# Remove only generated transcripts and images
make clean-outputs
```

### Other Commands

```bash
# Update dependencies
make update

# Update lock file
make lock

# Run arbitrary Python module
make run MODULE=app.main

# Show all available commands
make help
```

## Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```bash
# OpenAI API Keys (required for embeddings and transcription)
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini  # or gpt-4o
OPENAI_TEST_KEY=your_test_key_here  # Used by transcribe_v2.py

# Anthropic API Key (required for Claude-powered RAG queries)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Notes**:
- `transcribe.py` uses `OPENAI_API_KEY` and `OPENAI_MODEL`, while `transcribe_v2.py` uses `OPENAI_TEST_KEY`
- RAG system uses `OPENAI_API_KEY` for embeddings and `ANTHROPIC_API_KEY` for Claude answer generation (default)
- Get Anthropic API key from: https://console.anthropic.com/settings/keys

## Rate Limiting & Concurrency

`transcribe_v2.py` implements comprehensive rate limiting:
- **RPS limit**: 2 requests/second (configurable at line 45)
- **Concurrency limit**: 3 simultaneous calls (line 46)
- **TPM limit**: 180k tokens/minute (line 47)
- **Exponential backoff**: 6 retries with jitter (line 86)

Adjust these constants based on your OpenAI tier limits. See lines 45-48 in `app/transcribe_v2.py`.

## Standardization Rules

The transcription prompt enforces strict formatting:
- **Dates**: ISO 8601 (YYYY-MM-DD), use "00" for unknown day/month
- **Names**: "LAST NAME, FIRST NAME" (uppercase)
- **Places**: Uppercase (e.g., "SANTIAGO", "VALPARAÍSO")
- **Classification**: Exactly one of: "TOP SECRET", "SECRET", "CONFIDENTIAL", "UNCLASSIFIED"
- **Document Types**: "MEMORANDUM", "LETTER", "TELEGRAM", "INTELLIGENCE BRIEF", "REPORT", "MEETING MINUTES", "CABLE"
- **Keywords**: Uppercase thematic tags (e.g., "HUMAN RIGHTS", "OPERATION CONDOR")
- **Language**: "ENGLISH" or "SPANISH"

See the full prompt in `app/transcribe.py:20-89` or `app/transcribe_v2.py:173-175`.

## Testing

The project uses pytest. Test files are in `tests/`. Currently contains a Streamlit app (`test_app.py`) for interactive testing.

Run all tests:
```bash
uv run pytest tests/
```

## Common Patterns

### Running Scripts Directly

All scripts can be run as modules with UV:
```bash
# Transcription
uv run python -m app.transcribe --max-files 5 --resume --max-workers 10

# Analysis
uv run python -m app.analyze_documents data/generated_transcripts --output report.html

# Visualization
uv run python -m app.visualize_transcripts
```

### Adding New Dependencies

```bash
# Add a dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update lock file
uv lock
```

## RAG System (Question Answering)

The project includes a Retrieval-Augmented Generation (RAG) system for querying the declassified documents using natural language. The system is located in `app/rag/`.

### RAG Architecture

**Components**:
- **Vector Database**: ChromaDB (local, persistent)
- **Embeddings**: OpenAI `text-embedding-3-small`
- **LLM**: Claude 3.5 Haiku (default) or OpenAI GPT-4o-mini
- **Chunking**: 512 tokens with 128-token overlap

### RAG CLI Commands

```bash
# Build the vector database index (one-time setup)
uv run python -m app.rag.cli build

# Reset and rebuild
uv run python -m app.rag.cli build --reset

# Query with Claude (default)
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?"

# Query with OpenAI
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?" --llm openai

# Query with specific Claude model
uv run python -m app.rag.cli query "Complex question..." --llm claude --model claude-3-5-sonnet-20241022

# Query with filters
uv run python -m app.rag.cli query "Human rights violations" \
  --start-date 1976-01-01 \
  --end-date 1976-12-31 \
  --keywords "OPERATION CONDOR,HUMAN RIGHTS" \
  --top-k 10

# Interactive mode
uv run python -m app.rag.cli interactive
uv run python -m app.rag.cli interactive --llm openai

# Database statistics
uv run python -m app.rag.cli stats
```

### Claude vs OpenAI for RAG

**Default: Claude 3.5 Haiku**
- ✅ Better citation accuracy
- ✅ Lower hallucination rates
- ✅ 200k token context window
- ✅ Superior at acknowledging gaps in knowledge
- ~$0.02-0.03 per query

**Alternative: OpenAI GPT-4o-mini**
- ✅ Similar cost (~$0.02-0.03 per query)
- ✅ Good performance
- ⚠️ 128k token context (less than Claude)
- Use with `--llm openai` flag

**For Complex Queries: Claude 3.5 Sonnet**
- ✅ Best for temporal analysis and multi-document synthesis
- ✅ Extended thinking capability
- 💰 Higher cost (~$0.06-0.10 per query)
- Use with `--model claude-3-5-sonnet-20241022`

See `docs/CLAUDE_MIGRATION_ANALYSIS.md` for detailed comparison and cost analysis.

### RAG Testing Results

The system has been tested with 6 research questions:
- **Success Rate**: 83% (5/6 excellent or passing)
- **Best Performance**: Letelier assassination (42.93% relevance)
- **Documents Indexed**: 5,611 (6,929 chunks)

See `tests/TEST_QUERIES_RESULTS.md` for full test results and analysis.

### RAG Module Structure

- `app/rag/embeddings.py` - Data loading, chunking, embedding generation
- `app/rag/vector_store.py` - ChromaDB operations
- `app/rag/retrieval.py` - Semantic search and filtering
- `app/rag/qa_pipeline.py` - Question answering with OpenAI
- `app/rag/qa_pipeline_claude.py` - Question answering with Claude (recommended)
- `app/rag/cli.py` - Command-line interface
- `app/rag/config.py` - Configuration settings

See `app/rag/README.md` for comprehensive RAG documentation.

## Documentation

Comprehensive project documentation is available in the `docs/` directory:
- **[docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)** - Historical context, use cases, ethical considerations, and project goals
- **[docs/README.md](docs/README.md)** - Documentation overview and organization

Refer to these documents when working on features related to research applications, data ethics, or user-facing functionality.

## Important Notes

- The `main.py` file in the root is a placeholder and not actively used
- Multiple virtual environments exist (`.venv/` and `app/.venv/`) - the root `.venv/` is the primary one
- The project contains both `generated_transcripts/` and `generated_transcripts_v1/` directories - v1 contains legacy outputs
- Image files are assumed to be JPEG format in `data/images/`
- The Streamlit app in `tests/test_app.py` uses a hardcoded path - update `TRANSCRIPTS_DIR` constant if needed
- always us uv to manage environments
- after every new feature implementation, make it easy for the reviewer to test it.
- always work on a new branch and create a PR when finished. PRs have to be manually accepted by a human in github