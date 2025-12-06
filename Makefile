# Makefile for automating setup and running the transcribe script with UV

# Variables
SCRIPT_MODULE = app.transcribe
MAX_FILES = 1
# By default, transcribe-some uses 5 files; you can override it below.
FILES_TO_PROCESS ?= 5
# Number of parallel workers for API calls
MAX_WORKERS ?= 32

# Target: install
# UV automatically creates and manages the virtual environment
install:
	uv sync

# Target: install-dev
# Install with development dependencies
install-dev:
	uv sync --dev

# Target: transcribe
# Basic transcribe with configurable max files
transcribe:
	uv run python -m $(SCRIPT_MODULE) --max-files $(MAX_FILES)

# Target: transcribe-all
# Runs the script for all files (max_files=0 means no limit)
transcribe-all:
	uv run python -m $(SCRIPT_MODULE) --max-files 0 --max-workers $(MAX_WORKERS)

# Target: transcribe-some
# By default, runs the script for 5 files. You can override it:
#    make transcribe-some FILES_TO_PROCESS=10
transcribe-some:
	uv run python -m $(SCRIPT_MODULE) --max-files $(FILES_TO_PROCESS)

# Target: resume
# Resumes where it left off (skips files that have existing .json)
resume:
	uv run python -m $(SCRIPT_MODULE) --resume --max-files 0

# Target: resume-some
# Resume with limited files
resume-some:
	uv run python -m $(SCRIPT_MODULE) --resume --max-files $(FILES_TO_PROCESS)

# Target: test
# Run tests with pytest
test:
	uv run pytest tests/

# Target: lint
# Run linting with ruff (if installed)
lint:
	uv run ruff check .

# Target: format
# Format code with ruff (if installed)
format:
	uv run ruff format .

# Target: analyze
# Run the analyze_documents script
analyze:
	uv run python -m app.analyze_documents

# Target: visualize
# Run the visualize_transcripts script
visualize:
	uv run python -m app.visualize_transcripts

# Target: rag-build
# Build the RAG vector database index
rag-build:
	uv run python -m app.rag.cli build

# Target: rag-rebuild
# Rebuild the RAG index (reset and build)
rag-rebuild:
	uv run python -m app.rag.cli build --reset

# Target: rag-stats
# Show RAG database statistics
rag-stats:
	uv run python -m app.rag.cli stats

# Target: rag-interactive
# Start RAG interactive query mode
rag-interactive:
	uv run python -m app.rag.cli interactive

# Target: rag-query
# Query the RAG system (usage: make rag-query QUERY="your question")
rag-query:
	uv run python -m app.rag.cli query "$(QUERY)"

# ---------------------------------------------------------------------------
# Claude Transcription (Anthropic API)
# ---------------------------------------------------------------------------

# Target: transcribe-claude
# Transcribe documents using Claude API (real-time mode)
transcribe-claude:
	uv run python -m app.transcribe_claude --max-files $(FILES_TO_PROCESS)

# Target: transcribe-claude-batch
# Transcribe all documents using Claude Batch API (50% discount)
transcribe-claude-batch:
	uv run python -m app.transcribe_claude --batch --max-files 0

# Target: transcribe-claude-batch-some
# Transcribe limited documents using Claude Batch API
transcribe-claude-batch-some:
	uv run python -m app.transcribe_claude --batch --max-files $(FILES_TO_PROCESS)

# Target: transcribe-claude-test
# Test Claude transcription with 5 documents
transcribe-claude-test:
	uv run python -m app.transcribe_claude --max-files 5

# ---------------------------------------------------------------------------
# Full Pass Processing (OpenAI - Legacy)
# ---------------------------------------------------------------------------

# Target: full-pass
# Run full pass processing with interactive confirmation (default: medium batch size)
full-pass:
	uv run python -m app.full_pass --batch-size medium --mode interactive

# Target: full-pass-auto
# Run full pass in auto mode (all batches without confirmation)
# Usage: make full-pass-auto BATCH_SIZE=large MAX_COST=50
BATCH_SIZE ?= medium
MAX_COST ?=
full-pass-auto:
	@if [ -n "$(MAX_COST)" ]; then \
		uv run python -m app.full_pass --batch-size $(BATCH_SIZE) --mode auto --max-cost $(MAX_COST); \
	else \
		uv run python -m app.full_pass --batch-size $(BATCH_SIZE) --mode auto; \
	fi

# Target: full-pass-resume
# Resume from previous full pass session
full-pass-resume:
	uv run python -m app.full_pass --resume

# Target: full-pass-status
# Show current full pass status
full-pass-status:
	uv run python -m app.full_pass --status

# Target: full-pass-reset
# Reset full pass state
full-pass-reset:
	uv run python -m app.full_pass --reset

# Target: clean
# Remove UV's cache and Python artifacts
clean:
	rm -rf .venv
	rm -rf $(shell find . -type d -name '__pycache__')
	rm -rf $(shell find . -type d -name '*.egg-info')
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	uv cache clean

# Target: clean-outputs
# Remove generated outputs but keep environment
clean-outputs:
	rm -rf data/generated_transcripts/*.json
	rm -rf output_images/*

# Target: update
# Update all dependencies to latest versions
update:
	uv sync --upgrade

# Target: lock
# Update the lock file
lock:
	uv lock

# Target: run
# Generic target to run any Python module with UV
# Usage: make run MODULE=app.main
run:
	uv run python -m $(MODULE)

# Target: shell
# Start a shell with the UV environment activated
shell:
	uv run bash

# Help target
help:
	@echo "Available targets:"
	@echo ""
	@echo "Setup:"
	@echo "  install              - Install dependencies with UV"
	@echo "  install-dev          - Install with dev dependencies"
	@echo ""
	@echo "Claude Transcription (recommended):"
	@echo "  transcribe-claude-test      - Test with 5 documents"
	@echo "  transcribe-claude           - Transcribe FILES_TO_PROCESS docs (real-time)"
	@echo "  transcribe-claude-batch     - Transcribe ALL docs (50%% off, async)"
	@echo "  transcribe-claude-batch-some - Batch process FILES_TO_PROCESS docs"
	@echo ""
	@echo "OpenAI Transcription (legacy):"
	@echo "  transcribe           - Run transcribe with MAX_FILES=$(MAX_FILES)"
	@echo "  transcribe-all       - Transcribe all files"
	@echo "  transcribe-some      - Transcribe FILES_TO_PROCESS=$(FILES_TO_PROCESS) files"
	@echo "  resume               - Resume transcription (skip existing)"
	@echo "  full-pass            - Run full pass processing (interactive)"
	@echo "  full-pass-auto       - Run full pass (auto mode)"
	@echo ""
	@echo "RAG (Question Answering):"
	@echo "  rag-build            - Build RAG vector database index"
	@echo "  rag-rebuild          - Rebuild RAG index (reset)"
	@echo "  rag-stats            - Show RAG database statistics"
	@echo "  rag-interactive      - Start RAG interactive mode"
	@echo "  rag-query            - Query RAG (usage: make rag-query QUERY='question')"
	@echo ""
	@echo "Analysis:"
	@echo "  analyze              - Run document analysis"
	@echo "  visualize            - Run transcript visualization"
	@echo ""
	@echo "Development:"
	@echo "  test                 - Run tests"
	@echo "  lint                 - Run linting"
	@echo "  format               - Format code"
	@echo "  clean                - Remove all generated files and caches"
	@echo "  clean-outputs        - Remove only output files"
	@echo "  update               - Update all dependencies"
	@echo "  shell                - Start shell with UV environment"
	@echo "  help                 - Show this help message"

# Default target
.DEFAULT_GOAL := help

# Phony targets (not files)
.PHONY: install install-dev transcribe transcribe-all transcribe-some resume resume-some \
        transcribe-claude transcribe-claude-batch transcribe-claude-batch-some transcribe-claude-test \
        test lint format analyze visualize rag-build rag-rebuild rag-stats rag-interactive \
        rag-query full-pass full-pass-auto full-pass-resume full-pass-status full-pass-reset \
        clean clean-outputs update lock run shell help