#!/usr/bin/env python3
"""
Quality evaluation CLI for transcript validation.

Usage:
    # Show statistics for a model's transcripts
    uv run python -m app.evaluate stats gpt-5-mini

    # Generate stratified sample for manual review
    uv run python -m app.evaluate sample gpt-5-mini --output samples/

    # Run automated validation checks
    uv run python -m app.evaluate validate gpt-5-mini

    # Full quality report
    uv run python -m app.evaluate report gpt-5-mini --output quality_report.html
"""

import argparse
import json
import random
import shutil
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import DATA_DIR, TRANSCRIPTS_DIR


# Valid values per schema
VALID_CLASSIFICATION_LEVELS = {
    "TOP SECRET",
    "SECRET",
    "CONFIDENTIAL",
    "UNCLASSIFIED",
    "",  # Empty is allowed
}

VALID_DOCUMENT_TYPES = {
    "MEMORANDUM",
    "LETTER",
    "TELEGRAM",
    "INTELLIGENCE BRIEF",
    "REPORT",
    "MEETING MINUTES",
    "CABLE",
    "",  # Empty is allowed
}

VALID_LANGUAGES = {"ENGLISH", "SPANISH", ""}


@dataclass
class TranscriptStats:
    """Statistics for a set of transcripts."""

    total_documents: int
    confidence_scores: list[float]
    confidence_mean: float
    confidence_median: float
    confidence_std: float
    confidence_min: float
    confidence_max: float
    low_confidence_count: int  # < 0.70
    medium_confidence_count: int  # 0.70 - 0.85
    high_confidence_count: int  # > 0.85
    missing_date_count: int
    missing_author_count: int
    missing_doc_type_count: int
    empty_reviewed_text_count: int
    page_count_distribution: Counter
    concern_categories: Counter
    document_types: Counter
    classification_levels: Counter


@dataclass
class ValidationIssue:
    """A validation issue found in a transcript."""

    file_path: str
    document_id: str
    issue_type: str
    description: str
    severity: str  # "error", "warning", "info"


def load_transcripts(model_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Load all JSON transcripts from a model directory."""
    # Files to exclude (not transcripts)
    excluded_files = {"failed_documents.json", "incomplete_documents.json", "processing_state.json"}

    transcripts = []
    for json_file in sorted(model_dir.glob("*.json")):
        # Skip non-transcript files
        if json_file.name in excluded_files:
            continue
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                # Only include dict-type data (transcripts), skip lists
                if isinstance(data, dict):
                    transcripts.append((json_file, data))
                else:
                    print(f"Skipping non-transcript file: {json_file.name}")
        except json.JSONDecodeError as e:
            print(f"Error parsing {json_file}: {e}")
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    return transcripts


def compute_stats(transcripts: list[tuple[Path, dict[str, Any]]]) -> TranscriptStats:
    """Compute statistics from transcripts."""
    confidence_scores = []
    missing_date = 0
    missing_author = 0
    missing_doc_type = 0
    empty_reviewed_text = 0
    page_counts: Counter = Counter()
    concern_categories: Counter = Counter()
    document_types: Counter = Counter()
    classification_levels: Counter = Counter()

    for _, data in transcripts:
        # Confidence
        confidence = data.get("confidence", {})
        overall = confidence.get("overall", 0.0)
        confidence_scores.append(overall)

        # Categorize concerns
        for concern in confidence.get("concerns", []):
            # Simple categorization by keywords
            concern_lower = concern.lower()
            if "ocr" in concern_lower or "scan" in concern_lower:
                concern_categories["OCR/Scan Quality"] += 1
            elif "illegible" in concern_lower or "unclear" in concern_lower:
                concern_categories["Illegible Text"] += 1
            elif "redact" in concern_lower:
                concern_categories["Redactions"] += 1
            elif "date" in concern_lower:
                concern_categories["Date Issues"] += 1
            elif "name" in concern_lower or "author" in concern_lower:
                concern_categories["Name/Author Issues"] += 1
            elif "classification" in concern_lower:
                concern_categories["Classification Issues"] += 1
            else:
                concern_categories["Other"] += 1

        # Metadata completeness
        metadata = data.get("metadata", {})

        doc_date = metadata.get("document_date", "")
        if not doc_date or doc_date == "0000-00-00":
            missing_date += 1

        author = metadata.get("author", "")
        if not author:
            missing_author += 1

        doc_type = metadata.get("document_type", "")
        if not doc_type:
            missing_doc_type += 1
        document_types[doc_type or "UNKNOWN"] += 1

        classification = metadata.get("classification_level", "")
        classification_levels[classification or "UNKNOWN"] += 1

        # Page count
        page_count = metadata.get("page_count", 0)
        page_counts[page_count] += 1

        # Text content
        reviewed_text = data.get("reviewed_text", "")
        if not reviewed_text or len(reviewed_text.strip()) < 50:
            empty_reviewed_text += 1

    # Calculate statistics
    if confidence_scores:
        confidence_mean = statistics.mean(confidence_scores)
        confidence_median = statistics.median(confidence_scores)
        confidence_std = statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0.0
        confidence_min = min(confidence_scores)
        confidence_max = max(confidence_scores)
    else:
        confidence_mean = confidence_median = confidence_std = confidence_min = confidence_max = 0.0

    low_conf = sum(1 for s in confidence_scores if s < 0.70)
    med_conf = sum(1 for s in confidence_scores if 0.70 <= s <= 0.85)
    high_conf = sum(1 for s in confidence_scores if s > 0.85)

    return TranscriptStats(
        total_documents=len(transcripts),
        confidence_scores=confidence_scores,
        confidence_mean=confidence_mean,
        confidence_median=confidence_median,
        confidence_std=confidence_std,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        low_confidence_count=low_conf,
        medium_confidence_count=med_conf,
        high_confidence_count=high_conf,
        missing_date_count=missing_date,
        missing_author_count=missing_author,
        missing_doc_type_count=missing_doc_type,
        empty_reviewed_text_count=empty_reviewed_text,
        page_count_distribution=page_counts,
        concern_categories=concern_categories,
        document_types=document_types,
        classification_levels=classification_levels,
    )


def validate_transcripts(
    transcripts: list[tuple[Path, dict[str, Any]]]
) -> list[ValidationIssue]:
    """Run validation checks on transcripts."""
    issues: list[ValidationIssue] = []

    for file_path, data in transcripts:
        doc_id = file_path.stem
        metadata = data.get("metadata", {})
        confidence = data.get("confidence", {})

        # Check confidence threshold
        overall_conf = confidence.get("overall", 0.0)
        if overall_conf < 0.70:
            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    document_id=doc_id,
                    issue_type="low_confidence",
                    description=f"Low confidence score: {overall_conf:.2f}",
                    severity="warning",
                )
            )

        # Check date format
        doc_date = metadata.get("document_date", "")
        if doc_date and doc_date != "0000-00-00":
            if len(doc_date) != 10 or doc_date[4] != "-" or doc_date[7] != "-":
                issues.append(
                    ValidationIssue(
                        file_path=str(file_path),
                        document_id=doc_id,
                        issue_type="invalid_date_format",
                        description=f"Date not in YYYY-MM-DD format: {doc_date}",
                        severity="error",
                    )
                )

        # Check classification level
        classification = metadata.get("classification_level", "")
        if classification and classification not in VALID_CLASSIFICATION_LEVELS:
            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    document_id=doc_id,
                    issue_type="invalid_classification",
                    description=f"Invalid classification: {classification}",
                    severity="error",
                )
            )

        # Check document type
        doc_type = metadata.get("document_type", "")
        if doc_type and doc_type not in VALID_DOCUMENT_TYPES:
            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    document_id=doc_id,
                    issue_type="invalid_document_type",
                    description=f"Invalid document type: {doc_type}",
                    severity="warning",
                )
            )

        # Check language
        language = metadata.get("language", "")
        if language and language not in VALID_LANGUAGES:
            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    document_id=doc_id,
                    issue_type="invalid_language",
                    description=f"Invalid language: {language}",
                    severity="warning",
                )
            )

        # Check for empty reviewed text
        reviewed_text = data.get("reviewed_text", "")
        original_text = data.get("original_text", "")
        if not reviewed_text or len(reviewed_text.strip()) < 50:
            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    document_id=doc_id,
                    issue_type="empty_or_short_text",
                    description=f"Reviewed text is empty or very short ({len(reviewed_text.strip())} chars)",
                    severity="warning",
                )
            )

        # Check for incomplete transcription (original has content but reviewed is empty)
        if len(original_text) > 100 and len(reviewed_text) < 50:
            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    document_id=doc_id,
                    issue_type="incomplete_transcription",
                    description=f"Incomplete: original_text has {len(original_text)} chars but reviewed_text only has {len(reviewed_text)} chars",
                    severity="error",
                )
            )

        # Check page count consistency
        page_count = metadata.get("page_count", 0)
        text_length = len(reviewed_text) if reviewed_text else 0
        # Heuristic: expect at least 200 chars per page on average
        if page_count > 0 and text_length < page_count * 100:
            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    document_id=doc_id,
                    issue_type="text_page_mismatch",
                    description=f"Text length ({text_length}) seems short for {page_count} pages",
                    severity="info",
                )
            )

        # Check for missing critical fields
        if not metadata.get("document_date") or metadata.get("document_date") == "0000-00-00":
            issues.append(
                ValidationIssue(
                    file_path=str(file_path),
                    document_id=doc_id,
                    issue_type="missing_date",
                    description="Document date is missing or unknown",
                    severity="info",
                )
            )

    return issues


def generate_sample(
    transcripts: list[tuple[Path, dict[str, Any]]],
    output_dir: Path,
    sample_size: int = 30,
) -> dict[str, list[Path]]:
    """Generate a stratified sample of transcripts for manual review."""
    # Categorize by confidence
    high_conf = []  # > 0.90
    medium_conf = []  # 0.75 - 0.90
    low_conf = []  # < 0.75
    multi_page = []  # > 3 pages

    for file_path, data in transcripts:
        conf = data.get("confidence", {}).get("overall", 0.0)
        pages = data.get("metadata", {}).get("page_count", 1)

        if conf > 0.90:
            high_conf.append(file_path)
        elif conf >= 0.75:
            medium_conf.append(file_path)
        else:
            low_conf.append(file_path)

        if pages > 3:
            multi_page.append(file_path)

    # Sample from each category
    samples = {
        "high_confidence": random.sample(high_conf, min(5, len(high_conf))),
        "medium_confidence": random.sample(medium_conf, min(10, len(medium_conf))),
        "low_confidence": random.sample(low_conf, min(10, len(low_conf))),
        "multi_page": random.sample(multi_page, min(5, len(multi_page))),
    }

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy files to sample directory with category prefix
    pdf_dir = DATA_DIR / "original_pdfs"
    for category, files in samples.items():
        category_dir = output_dir / category
        category_dir.mkdir(exist_ok=True)

        for json_path in files:
            # Copy JSON
            shutil.copy(json_path, category_dir / json_path.name)

            # Copy corresponding PDF if exists
            pdf_name = json_path.stem + ".pdf"
            pdf_path = pdf_dir / pdf_name
            if pdf_path.exists():
                shutil.copy(pdf_path, category_dir / pdf_name)

    return samples


def print_stats(stats: TranscriptStats) -> None:
    """Print statistics to console."""
    print("=" * 80)
    print("TRANSCRIPT QUALITY STATISTICS")
    print("=" * 80)

    print(f"\nTotal Documents: {stats.total_documents}")

    print("\n--- Confidence Scores ---")
    print(f"  Mean:   {stats.confidence_mean:.3f}")
    print(f"  Median: {stats.confidence_median:.3f}")
    print(f"  Std:    {stats.confidence_std:.3f}")
    print(f"  Min:    {stats.confidence_min:.3f}")
    print(f"  Max:    {stats.confidence_max:.3f}")

    print("\n--- Confidence Distribution ---")
    print(f"  High (>0.85):    {stats.high_confidence_count:4d} ({100*stats.high_confidence_count/stats.total_documents:.1f}%)")
    print(f"  Medium (0.70-0.85): {stats.medium_confidence_count:4d} ({100*stats.medium_confidence_count/stats.total_documents:.1f}%)")
    print(f"  Low (<0.70):     {stats.low_confidence_count:4d} ({100*stats.low_confidence_count/stats.total_documents:.1f}%)")

    print("\n--- Metadata Completeness ---")
    print(f"  Missing date:     {stats.missing_date_count:4d} ({100*stats.missing_date_count/stats.total_documents:.1f}%)")
    print(f"  Missing author:   {stats.missing_author_count:4d} ({100*stats.missing_author_count/stats.total_documents:.1f}%)")
    print(f"  Missing doc type: {stats.missing_doc_type_count:4d} ({100*stats.missing_doc_type_count/stats.total_documents:.1f}%)")
    print(f"  Empty/short text: {stats.empty_reviewed_text_count:4d} ({100*stats.empty_reviewed_text_count/stats.total_documents:.1f}%)")

    print("\n--- Document Types ---")
    for doc_type, count in stats.document_types.most_common(10):
        print(f"  {doc_type:20s}: {count:4d}")

    print("\n--- Classification Levels ---")
    for level, count in stats.classification_levels.most_common():
        print(f"  {level or 'UNKNOWN':20s}: {count:4d}")

    print("\n--- Page Count Distribution ---")
    for pages in sorted(stats.page_count_distribution.keys()):
        count = stats.page_count_distribution[pages]
        print(f"  {pages:2d} pages: {count:4d}")

    print("\n--- Common Concerns ---")
    for concern, count in stats.concern_categories.most_common(10):
        print(f"  {concern:25s}: {count:4d}")

    print("\n" + "=" * 80)


def print_validation_results(issues: list[ValidationIssue]) -> None:
    """Print validation results to console."""
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)

    if not issues:
        print("\n✓ No validation issues found!")
        return

    # Group by severity
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    infos = [i for i in issues if i.severity == "info"]

    print(f"\nTotal Issues: {len(issues)}")
    print(f"  Errors:   {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    print(f"  Info:     {len(infos)}")

    # Group by issue type
    by_type: Counter = Counter(i.issue_type for i in issues)
    print("\n--- Issues by Type ---")
    for issue_type, count in by_type.most_common():
        print(f"  {issue_type:30s}: {count:4d}")

    # Show first 10 errors
    if errors:
        print("\n--- First 10 Errors ---")
        for issue in errors[:10]:
            print(f"  [{issue.document_id}] {issue.description}")

    # Show first 10 warnings
    if warnings:
        print("\n--- First 10 Warnings ---")
        for issue in warnings[:10]:
            print(f"  [{issue.document_id}] {issue.description}")

    print("\n" + "=" * 80)


def generate_html_report(
    stats: TranscriptStats,
    issues: list[ValidationIssue],
    model_name: str,
    output_file: Path,
) -> None:
    """Generate an HTML quality report."""
    # Issue summary
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    by_type: Counter = Counter(i.issue_type for i in issues)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Quality Report - {model_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        .error {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        .success {{ color: #28a745; }}
        .progress-bar {{ background: #e9ecef; border-radius: 4px; overflow: hidden; height: 20px; }}
        .progress-fill {{ height: 100%; transition: width 0.3s; }}
        .progress-high {{ background: #28a745; }}
        .progress-med {{ background: #ffc107; }}
        .progress-low {{ background: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Transcript Quality Report</h1>
        <p>Model: <strong>{model_name}</strong> | Documents: <strong>{stats.total_documents}</strong></p>

        <h2>Summary</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats.confidence_mean:.2f}</div>
                <div class="stat-label">Mean Confidence</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.high_confidence_count}</div>
                <div class="stat-label">High Confidence (>0.85)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(errors)}</div>
                <div class="stat-label">Validation Errors</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(warnings)}</div>
                <div class="stat-label">Validation Warnings</div>
            </div>
        </div>

        <h2>Confidence Distribution</h2>
        <div class="progress-bar" style="display: flex;">
            <div class="progress-fill progress-high" style="width: {100*stats.high_confidence_count/stats.total_documents}%"></div>
            <div class="progress-fill progress-med" style="width: {100*stats.medium_confidence_count/stats.total_documents}%"></div>
            <div class="progress-fill progress-low" style="width: {100*stats.low_confidence_count/stats.total_documents}%"></div>
        </div>
        <p>
            <span class="success">■</span> High ({stats.high_confidence_count}) |
            <span class="warning">■</span> Medium ({stats.medium_confidence_count}) |
            <span class="error">■</span> Low ({stats.low_confidence_count})
        </p>

        <h2>Metadata Completeness</h2>
        <table>
            <tr><th>Field</th><th>Missing</th><th>Percentage</th></tr>
            <tr><td>Document Date</td><td>{stats.missing_date_count}</td><td>{100*stats.missing_date_count/stats.total_documents:.1f}%</td></tr>
            <tr><td>Author</td><td>{stats.missing_author_count}</td><td>{100*stats.missing_author_count/stats.total_documents:.1f}%</td></tr>
            <tr><td>Document Type</td><td>{stats.missing_doc_type_count}</td><td>{100*stats.missing_doc_type_count/stats.total_documents:.1f}%</td></tr>
            <tr><td>Reviewed Text</td><td>{stats.empty_reviewed_text_count}</td><td>{100*stats.empty_reviewed_text_count/stats.total_documents:.1f}%</td></tr>
        </table>

        <h2>Document Types</h2>
        <table>
            <tr><th>Type</th><th>Count</th></tr>
            {"".join(f"<tr><td>{t}</td><td>{c}</td></tr>" for t, c in stats.document_types.most_common())}
        </table>

        <h2>Validation Issues by Type</h2>
        <table>
            <tr><th>Issue Type</th><th>Count</th></tr>
            {"".join(f"<tr><td>{t}</td><td>{c}</td></tr>" for t, c in by_type.most_common())}
        </table>

        <h2>Common Concerns</h2>
        <table>
            <tr><th>Concern Category</th><th>Count</th></tr>
            {"".join(f"<tr><td>{c}</td><td>{n}</td></tr>" for c, n in stats.concern_categories.most_common(10))}
        </table>

        <h2>Page Count Distribution</h2>
        <table>
            <tr><th>Pages</th><th>Documents</th></tr>
            {"".join(f"<tr><td>{p}</td><td>{c}</td></tr>" for p, c in sorted(stats.page_count_distribution.items()))}
        </table>
    </div>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report saved to {output_file}")


def stats_command(args: argparse.Namespace) -> None:
    """Show statistics for transcripts."""
    model_dir = TRANSCRIPTS_DIR / args.model
    if not model_dir.exists():
        print(f"Error: Model directory not found: {model_dir}")
        sys.exit(1)

    print(f"Loading transcripts from {model_dir}...")
    transcripts = load_transcripts(model_dir)

    if not transcripts:
        print("No transcripts found!")
        sys.exit(1)

    stats = compute_stats(transcripts)
    print_stats(stats)


def sample_command(args: argparse.Namespace) -> None:
    """Generate stratified sample for manual review."""
    model_dir = TRANSCRIPTS_DIR / args.model
    if not model_dir.exists():
        print(f"Error: Model directory not found: {model_dir}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else Path(f"samples_{args.model}")

    print(f"Loading transcripts from {model_dir}...")
    transcripts = load_transcripts(model_dir)

    if not transcripts:
        print("No transcripts found!")
        sys.exit(1)

    print(f"Generating stratified sample in {output_dir}...")
    samples = generate_sample(transcripts, output_dir, args.size)

    print("\nSample Summary:")
    for category, files in samples.items():
        print(f"  {category}: {len(files)} files")

    print(f"\nSample files saved to: {output_dir}")
    print("Each category folder contains JSON transcripts and corresponding PDFs for manual review.")


def validate_command(args: argparse.Namespace) -> None:
    """Run validation checks on transcripts."""
    model_dir = TRANSCRIPTS_DIR / args.model
    if not model_dir.exists():
        print(f"Error: Model directory not found: {model_dir}")
        sys.exit(1)

    print(f"Loading transcripts from {model_dir}...")
    transcripts = load_transcripts(model_dir)

    if not transcripts:
        print("No transcripts found!")
        sys.exit(1)

    print("Running validation checks...")
    issues = validate_transcripts(transcripts)
    print_validation_results(issues)

    # Optionally save issues to JSON
    if args.output:
        output_path = Path(args.output)
        issues_data = [
            {
                "file_path": i.file_path,
                "document_id": i.document_id,
                "issue_type": i.issue_type,
                "description": i.description,
                "severity": i.severity,
            }
            for i in issues
        ]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(issues_data, f, indent=2)
        print(f"\nIssues saved to {output_path}")


def report_command(args: argparse.Namespace) -> None:
    """Generate full quality report."""
    model_dir = TRANSCRIPTS_DIR / args.model
    if not model_dir.exists():
        print(f"Error: Model directory not found: {model_dir}")
        sys.exit(1)

    output_file = Path(args.output) if args.output else Path(f"quality_report_{args.model}.html")

    print(f"Loading transcripts from {model_dir}...")
    transcripts = load_transcripts(model_dir)

    if not transcripts:
        print("No transcripts found!")
        sys.exit(1)

    print("Computing statistics...")
    stats = compute_stats(transcripts)

    print("Running validation...")
    issues = validate_transcripts(transcripts)

    print("Generating HTML report...")
    generate_html_report(stats, issues, args.model, output_file)

    # Also print summary to console
    print_stats(stats)
    print_validation_results(issues)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Quality evaluation for transcript validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show statistics
  uv run python -m app.evaluate stats gpt-5-mini

  # Generate sample for manual review
  uv run python -m app.evaluate sample gpt-5-mini --output samples/

  # Run validation checks
  uv run python -m app.evaluate validate gpt-5-mini

  # Generate full HTML report
  uv run python -m app.evaluate report gpt-5-mini
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show transcript statistics")
    stats_parser.add_argument("model", type=str, help="Model directory name (e.g., gpt-5-mini)")

    # Sample command
    sample_parser = subparsers.add_parser("sample", help="Generate stratified sample for manual review")
    sample_parser.add_argument("model", type=str, help="Model directory name")
    sample_parser.add_argument("--output", "-o", type=str, help="Output directory for samples")
    sample_parser.add_argument("--size", "-s", type=int, default=30, help="Total sample size (default: 30)")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Run validation checks")
    validate_parser.add_argument("model", type=str, help="Model directory name")
    validate_parser.add_argument("--output", "-o", type=str, help="Output JSON file for issues")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate full HTML quality report")
    report_parser.add_argument("model", type=str, help="Model directory name")
    report_parser.add_argument("--output", "-o", type=str, help="Output HTML file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "stats":
        stats_command(args)
    elif args.command == "sample":
        sample_command(args)
    elif args.command == "validate":
        validate_command(args)
    elif args.command == "report":
        report_command(args)


if __name__ == "__main__":
    main()
