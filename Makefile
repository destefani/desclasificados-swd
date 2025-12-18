# Makefile for CIA Declassified Documents Project
#
# Usage:
#   make install        Install dependencies
#   make transcribe     Transcribe documents (main command)
#   make test           Run tests
#   make help           Show all commands

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default model and schema version for transcripts
# Override with: make analyze MODEL=gpt-4.1-mini SCHEMA=v2.0.0
MODEL ?= gpt-5-mini
SCHEMA ?= v2.2.0
TRANSCRIPTS_DIR = data/generated_transcripts/$(MODEL)-$(SCHEMA)

# =============================================================================
# SETUP
# =============================================================================

install:
	uv sync

install-dev:
	uv sync --dev

# =============================================================================
# TRANSCRIPTION
# =============================================================================
#
# Primary command for transcribing documents. Automatically resumes from
# where it left off and supports graceful shutdown (Ctrl+C).
#
# Usage:
#   make transcribe              Process all remaining documents
#   make transcribe N=100        Process 100 documents
#   make transcribe BUDGET=50    Stop at $50 budget
#   make transcribe YES=1        Skip confirmation prompt
#
transcribe:
	@CMD="uv run python -m app.transcribe"; \
	if [ -n "$(N)" ]; then CMD="$$CMD --limit $(N)"; fi; \
	if [ -n "$(BUDGET)" ]; then CMD="$$CMD --budget $(BUDGET)"; fi; \
	if [ "$(YES)" = "1" ]; then CMD="$$CMD --yes"; fi; \
	$$CMD

# Show transcription status without processing
transcribe-status:
	uv run python -m app.transcribe --status

# =============================================================================
# BATCH PROCESSING (50% cost savings)
# =============================================================================
#
# Use the OpenAI Batch API for large jobs at 50% reduced cost.
# Trade-off: Results within 24 hours (often faster) vs real-time.
#
# Usage:
#   make batch-run N=1000         All-in-one workflow
#   make batch-pending            Show pending documents
#   make batch-jobs               List batch jobs
#

# All-in-one: prepare, submit, poll, retrieve
batch-run:
	@CMD="uv run python -m app.batch run --poll"; \
	if [ -n "$(N)" ]; then CMD="$$CMD --limit $(N)"; fi; \
	if [ "$(YES)" = "1" ]; then CMD="$$CMD --yes"; fi; \
	$$CMD

# Prepare batch file only (for manual submission)
batch-prepare:
	@CMD="uv run python -m app.batch prepare"; \
	if [ -n "$(N)" ]; then CMD="$$CMD --limit $(N)"; fi; \
	if [ "$(YES)" = "1" ]; then CMD="$$CMD --yes"; fi; \
	$$CMD

# Show pending documents count
batch-pending:
	uv run python -m app.batch pending

# List all batch jobs
batch-jobs:
	uv run python -m app.batch jobs

# =============================================================================
# RAG (Question Answering)
# =============================================================================

rag-build:
	uv run python -m app.rag.cli build

rag-rebuild:
	uv run python -m app.rag.cli build --reset

rag-stats:
	uv run python -m app.rag.cli stats

rag-interactive:
	uv run python -m app.rag.cli interactive

# Usage: make rag-query QUERY="your question"
rag-query:
	uv run python -m app.rag.cli query "$(QUERY)"

# =============================================================================
# QUALITY EVALUATION
# =============================================================================
#
# Commands for evaluating transcript quality before full corpus processing.
#
# Usage:
#   make eval-stats MODEL=gpt-5-mini      Show statistics
#   make eval-validate MODEL=gpt-5-mini   Run validation checks
#   make eval-sample MODEL=gpt-5-mini     Generate sample for manual review
#   make eval-report MODEL=gpt-5-mini     Generate full HTML report
#
eval-stats:
	uv run python -m app.evaluate stats $(MODEL)

eval-validate:
	uv run python -m app.evaluate validate $(MODEL)

eval-sample:
	uv run python -m app.evaluate sample $(MODEL) --output samples_$(MODEL)

eval-report:
	uv run python -m app.evaluate report $(MODEL)

# Show dataset progress summary
progress:
	@echo "=== $(MODEL) Dataset Progress ==="
	@echo ""
	@echo "Total PDFs: $$(find data/original_pdfs -name '*.pdf' 2>/dev/null | wc -l | tr -d ' ')"
	@echo "Transcribed: $$(find $(TRANSCRIPTS_DIR) -name '*.json' ! -name 'failed_*' ! -name 'incomplete_*' ! -name 'processing_*' 2>/dev/null | wc -l | tr -d ' ')"
	@echo ""
	@echo "See $(TRANSCRIPTS_DIR)/PROGRESS_LOG.md for full history"

# =============================================================================
# ANALYSIS
# =============================================================================

analyze:
	uv run python -m app.analyze_documents $(TRANSCRIPTS_DIR)

analyze-full:
	uv run python -m app.analyze_documents $(TRANSCRIPTS_DIR) --full --pdf-dir data/original_pdfs

# Generate GitHub Pages compatible report (outputs to docs/index.html)
github-pages:
	uv run python -m app.analyze_documents $(TRANSCRIPTS_DIR) --github-pages --pdf-dir data/original_pdfs

# Generate GitHub Pages report with external PDF viewer links
github-pages-external:
	uv run python -m app.analyze_documents $(TRANSCRIPTS_DIR) --github-pages \
		--external-pdf-viewer "https://declasseuucl.vercel.app" --pdf-dir data/original_pdfs

# Update analysis and deploy to GitHub Pages (one command)
deploy:
	@echo "Generating research question HTML reports..."
	@uv run python -m app.research_reports generate --update-tracker
	@echo ""
	@echo "Generating GitHub Pages report..."
	@uv run python -m app.analyze_documents $(TRANSCRIPTS_DIR) --github-pages \
		--external-pdf-viewer "https://declasseuucl.vercel.app" --pdf-dir data/original_pdfs
	@echo ""
	@echo "Committing and pushing to GitHub..."
	@git add docs/
	@git commit -m "Update analysis report" || echo "No changes to commit"
	@git push
	@echo ""
	@echo "Done! GitHub Pages will update automatically."

# Serve the report with embedded PDF viewer
serve:
	@echo "Generating server-compatible report..."
	uv run python -m app.analyze_documents $(TRANSCRIPTS_DIR) --serve --pdf-dir data/original_pdfs
	@echo ""
	uv run python -m app.serve_report --report reports/report_full.html --pdf-dir data/original_pdfs

visualize:
	uv run python -m app.visualize_transcripts

# =============================================================================
# TESTING & CODE QUALITY
# =============================================================================

test:
	uv run pytest tests/

test-unit:
	uv run pytest tests/unit/ -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy app/ --ignore-missing-imports

# =============================================================================
# RESEARCH QUESTIONS TRACKER
# =============================================================================
#
# Track research questions asked about the declassified documents.
#
# Usage:
#   make rq-list                    List all research questions
#   make rq-add Q="your question"   Add a new question
#   make rq-update ID=RQ-001 ...    Update a question
#

rq-list:
	uv run python -m app.research_tracker list

rq-add:
	@if [ -z "$(Q)" ]; then echo "Usage: make rq-add Q='your question' [CAT=CATEGORY]"; exit 1; fi
	@CMD="uv run python -m app.research_tracker add '$(Q)'"; \
	if [ -n "$(CAT)" ]; then CMD="$$CMD --category $(CAT)"; fi; \
	if [ -n "$(NOTES)" ]; then CMD="$$CMD --notes '$(NOTES)'"; fi; \
	$$CMD

rq-show:
	@if [ -z "$(ID)" ]; then echo "Usage: make rq-show ID=RQ-001"; exit 1; fi
	uv run python -m app.research_tracker show $(ID)

rq-update:
	@if [ -z "$(ID)" ]; then echo "Usage: make rq-update ID=RQ-001 [STATUS=answered] [PDF=path/to/report.pdf]"; exit 1; fi
	@CMD="uv run python -m app.research_tracker update $(ID)"; \
	if [ -n "$(STATUS)" ]; then CMD="$$CMD --status $(STATUS)"; fi; \
	if [ -n "$(RAG)" ]; then CMD="$$CMD --rag-results '$(RAG)'"; fi; \
	if [ -n "$(REL)" ]; then CMD="$$CMD --relevance $(REL)"; fi; \
	if [ -n "$(DOCS)" ]; then CMD="$$CMD --docs $(DOCS)"; fi; \
	if [ -n "$(NOTES)" ]; then CMD="$$CMD --notes '$(NOTES)'"; fi; \
	if [ -n "$(PDF)" ]; then CMD="$$CMD --pdf-report $(PDF)"; fi; \
	$$CMD

rq-generate-md:
	uv run python -m app.research_tracker generate-md

# Generate HTML reports for research questions
rq-reports:
	uv run python -m app.research_reports generate --update-tracker

# Generate HTML report for a specific question
# Usage: make rq-report ID=RQ-001
rq-report:
	@if [ -z "$(ID)" ]; then echo "Usage: make rq-report ID=RQ-001"; exit 1; fi
	uv run python -m app.research_reports generate --question-id $(ID)

# List existing HTML reports
rq-reports-list:
	uv run python -m app.research_reports list

# =============================================================================
# UTILITIES
# =============================================================================

clean:
	rm -rf .venv
	rm -rf $(shell find . -type d -name '__pycache__')
	rm -rf $(shell find . -type d -name '*.egg-info')
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	uv cache clean

update:
	uv sync --upgrade

lock:
	uv lock

# Generic target to run any Python module
# Usage: make run MODULE=app.main
run:
	uv run python -m $(MODULE)

shell:
	uv run bash

# =============================================================================
# HELP
# =============================================================================

help:
	@echo ""
	@echo "CIA Declassified Documents Project"
	@echo "==================================="
	@echo ""
	@echo "Setup:"
	@echo "  install          Install dependencies"
	@echo "  install-dev      Install with dev dependencies"
	@echo ""
	@echo "Transcription:"
	@echo "  transcribe       Process documents (main command)"
	@echo "                   Options: N=100 BUDGET=50 YES=1"
	@echo "  transcribe-status  Show current status"
	@echo ""
	@echo "Batch Processing (50% savings):"
	@echo "  batch-run        All-in-one batch workflow"
	@echo "                   Options: N=1000 YES=1"
	@echo "  batch-prepare    Create batch file only"
	@echo "  batch-pending    Show pending documents"
	@echo "  batch-jobs       List batch jobs"
	@echo ""
	@echo "RAG (Question Answering):"
	@echo "  rag-build        Build vector database index"
	@echo "  rag-rebuild      Rebuild index from scratch"
	@echo "  rag-stats        Show database statistics"
	@echo "  rag-interactive  Start interactive query mode"
	@echo "  rag-query        Query (usage: make rag-query QUERY='...')"
	@echo ""
	@echo "Quality Evaluation:"
	@echo "  eval-stats       Show transcript statistics"
	@echo "  eval-validate    Run validation checks"
	@echo "  eval-sample      Generate sample for review"
	@echo "  eval-report      Generate full HTML report"
	@echo "                   (use MODEL=gpt-5-mini)"
	@echo "  progress         Show dataset creation progress"
	@echo ""
	@echo "Analysis:"
	@echo "  analyze          Generate HTML report"
	@echo "  analyze-full     Generate full report with PDF links"
	@echo "  github-pages     Generate GitHub Pages report (no PDF links)"
	@echo "  github-pages-external  GitHub Pages with external PDF viewer"
	@echo "  deploy           Update analysis and push to GitHub Pages"
	@echo "  serve            Start report server with PDF viewer"
	@echo "  visualize        Create visualizations"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  lint             Run linting"
	@echo "  format           Format code"
	@echo "  typecheck        Run mypy type checking"
	@echo ""
	@echo "Research Questions Tracker:"
	@echo "  rq-list          List all research questions"
	@echo "  rq-add           Add question (Q='...' [CAT=CATEGORY])"
	@echo "  rq-show          Show question (ID=RQ-001)"
	@echo "  rq-update        Update question (ID=RQ-001 [STATUS=...] [PDF=...])"
	@echo "  rq-generate-md   Regenerate markdown documentation"
	@echo "  rq-reports       Generate HTML reports for all questions"
	@echo "  rq-report        Generate HTML report (ID=RQ-001)"
	@echo "  rq-reports-list  List existing HTML reports"
	@echo ""
	@echo "Utilities:"
	@echo "  clean            Remove caches and venv"
	@echo "  update           Update dependencies"
	@echo "  help             Show this message"
	@echo ""

.DEFAULT_GOAL := help

.PHONY: install install-dev transcribe transcribe-status \
        batch-run batch-prepare batch-pending batch-jobs \
        rag-build rag-rebuild rag-stats rag-interactive rag-query \
        eval-stats eval-validate eval-sample eval-report progress \
        analyze analyze-full github-pages github-pages-external deploy serve visualize \
        test test-unit lint format typecheck \
        rq-list rq-add rq-show rq-update rq-generate-md rq-reports rq-report rq-reports-list \
        clean update lock run shell help
