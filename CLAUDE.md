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

- **`app/transcribe.py`** - Legacy transcription using OpenAI Responses API (currently uses non-standard API format)
- **`app/transcribe_v2.py`** - Production transcription with rate limiting, JSON schema validation, and robust error handling (uses standard Chat Completions API)
- **`app/analyze_documents.py`** - Aggregates metadata from JSON transcripts and generates HTML reports with timeline charts
- **`app/visualize_transcripts.py`** - Creates matplotlib visualizations (classification distribution, timeline, keywords)
- **`app/config.py`** - Centralized configuration for paths and logging
- **`app/data/pdf_extractor.py`** - Extracts text from PDFs using PyPDF2
- **`tests/test_app.py`** - Streamlit app for interactive document exploration

### Data Structure

```
data/
├── original_pdfs/      # Source PDF files
├── images/             # Extracted document images (JPEG)
├── generated_transcripts/  # JSON output (structured metadata)
├── generated_transcripts_v1/  # Legacy transcripts
└── session.json        # Session data
```

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

**Important**: The default transcription script (`app/transcribe.py`) currently uses `OPENAI_MODEL` env var but appears to use a non-standard API format. Use `app/transcribe_v2.py` for production work with proper rate limiting and validation.

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

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini  # or gpt-4o
OPENAI_TEST_KEY=your_test_key_here  # Used by transcribe_v2.py
```

**Note**: `transcribe.py` uses `OPENAI_API_KEY` and `OPENAI_MODEL`, while `transcribe_v2.py` uses `OPENAI_TEST_KEY`.

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