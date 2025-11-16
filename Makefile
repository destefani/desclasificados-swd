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
	@echo "  install          - Install dependencies with UV"
	@echo "  install-dev      - Install with dev dependencies"
	@echo "  transcribe       - Run transcribe with MAX_FILES=$(MAX_FILES)"
	@echo "  transcribe-all   - Transcribe all files"
	@echo "  transcribe-some  - Transcribe FILES_TO_PROCESS=$(FILES_TO_PROCESS) files"
	@echo "  resume           - Resume transcription (skip existing)"
	@echo "  resume-some      - Resume with limited files"
	@echo "  analyze          - Run document analysis"
	@echo "  visualize        - Run transcript visualization"
	@echo "  test             - Run tests"
	@echo "  lint             - Run linting"
	@echo "  format           - Format code"
	@echo "  clean            - Remove all generated files and caches"
	@echo "  clean-outputs    - Remove only output files"
	@echo "  update           - Update all dependencies"
	@echo "  lock             - Update lock file"
	@echo "  shell            - Start shell with UV environment"
	@echo "  help             - Show this help message"

# Default target
.DEFAULT_GOAL := help

# Phony targets (not files)
.PHONY: install install-dev transcribe transcribe-all transcribe-some resume resume-some \
        test lint format analyze visualize clean clean-outputs update lock run shell help