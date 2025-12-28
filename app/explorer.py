"""Document Explorer generator for the Desclasificados project.

Generates a standalone document explorer with search, filter, and pagination
for browsing all declassified documents.

Usage:
    uv run python -m app.explorer generate    # Generate explorer + data
    uv run python -m app.explorer data        # Generate only documents.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from app.analyze_documents import process_documents
from app.config import TRANSCRIPTS_DIR
from app.visualizations.document_explorer import generate_explorer_html

# Output directories
DOCS_DIR = Path(__file__).parent.parent / "docs"
DATA_DIR = DOCS_DIR / "data"
EXPLORER_DIR = DOCS_DIR / "explorer"

# Default external PDF viewer
DEFAULT_EXTERNAL_VIEWER = "https://declasseuucl.vercel.app"

# Default PDF directory
DEFAULT_PDF_DIR = Path(__file__).parent.parent / "data" / "original_pdfs"


def get_latest_transcript_dir() -> str:
    """Find the latest transcript directory based on schema version."""
    transcripts_base = Path(TRANSCRIPTS_DIR)
    if not transcripts_base.exists():
        raise FileNotFoundError(f"Transcripts directory not found: {transcripts_base}")

    # Find directories matching pattern model-vX.X.X
    dirs = [d for d in transcripts_base.iterdir() if d.is_dir() and "-v" in d.name]
    if not dirs:
        # Fallback to any directory
        dirs = [d for d in transcripts_base.iterdir() if d.is_dir()]

    if not dirs:
        raise FileNotFoundError(f"No transcript directories found in {transcripts_base}")

    # Sort by modification time, get latest
    return str(sorted(dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0])


def generate_documents_json(
    all_documents: list[dict[str, Any]],
    output_dir: str | Path = DATA_DIR,
    output_file: str = "documents.json",
) -> Path:
    """Extract and save document metadata for the explorer.

    Args:
        all_documents: List of document dictionaries from process_documents()
        output_dir: Directory to write the JSON file
        output_file: Name of the output file

    Returns:
        Path to the generated file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build simplified document records
    docs = []
    classifications_set: set[str] = set()
    types_set: set[str] = set()
    years: list[int] = []

    for doc in all_documents:
        # Extract year from date
        date_str = doc.get("date", "") or ""
        year = None
        if date_str and len(date_str) >= 4:
            try:
                year_str = date_str[:4]
                if year_str != "0000" and year_str.isdigit():
                    year = int(year_str)
                    years.append(year)
            except ValueError:
                pass

        # Get classification
        classification = doc.get("classification", "Unknown") or "Unknown"
        classifications_set.add(classification)

        # Get document type
        doc_type = doc.get("doc_type", "Unknown") or "Unknown"
        types_set.add(doc_type)

        # Get keywords (limit to 5 for size)
        keywords = doc.get("keywords", []) or []
        if isinstance(keywords, list):
            keywords = keywords[:5]
        else:
            keywords = []

        # Get people (limit to 5 for size)
        people = doc.get("people", []) or []
        if isinstance(people, list):
            people = people[:5]
        else:
            people = []

        # Truncate title and summary
        title = doc.get("title", "") or ""
        if len(title) > 100:
            title = title[:97] + "..."

        summary = doc.get("summary", "") or ""
        if len(summary) > 200:
            summary = summary[:197] + "..."

        docs.append({
            "id": doc.get("basename", ""),
            "doc_id": doc.get("doc_id", ""),
            "date": date_str,
            "year": year,
            "classification": classification,
            "type": doc_type,
            "title": title,
            "summary": summary,
            "pages": doc.get("page_count", 0) or 0,
            "keywords": keywords,
            "people": people,
        })

    # Sort by date (descending), then by id
    docs.sort(key=lambda d: (d["date"] or "0000-00-00", d["id"]), reverse=True)

    # Build facets
    facets = {
        "classifications": sorted(classifications_set),
        "types": sorted(types_set),
        "year_range": {
            "min": min(years) if years else 1963,
            "max": max(years) if years else 1993,
        },
    }

    output = {
        "generated": datetime.now().isoformat(),
        "total_count": len(docs),
        "schema_version": "1.0.0",
        "documents": docs,
        "facets": facets,
    }

    output_path = output_dir / output_file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    return output_path


def generate_explorer_page(
    output_dir: str | Path = EXPLORER_DIR,
    output_file: str = "index.html",
    external_pdf_viewer: str = DEFAULT_EXTERNAL_VIEWER,
) -> Path:
    """Generate the standalone document explorer HTML page.

    Args:
        output_dir: Directory to write the HTML file
        output_file: Name of the output file
        external_pdf_viewer: Base URL for external PDF viewer

    Returns:
        Path to the generated file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    html_content = generate_explorer_html(external_pdf_viewer=external_pdf_viewer)

    output_path = output_dir / output_file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path


def generate_all(
    transcript_dir: str | None = None,
    pdf_dir: str | None = None,
    external_pdf_viewer: str = DEFAULT_EXTERNAL_VIEWER,
) -> dict[str, Path]:
    """Generate both documents.json and explorer page.

    Args:
        transcript_dir: Directory containing JSON transcripts
        pdf_dir: Directory containing source PDFs
        external_pdf_viewer: Base URL for external PDF viewer

    Returns:
        Dictionary with paths to generated files
    """
    if transcript_dir is None:
        transcript_dir = get_latest_transcript_dir()

    if pdf_dir is None:
        pdf_dir = str(DEFAULT_PDF_DIR)

    print(f"Processing transcripts from: {transcript_dir}")

    # Process documents to get all_documents list
    results = process_documents(transcript_dir, full_mode=True, pdf_dir=pdf_dir)
    all_documents = results.get("all_documents", [])

    if not all_documents:
        print("Warning: No documents found!", file=sys.stderr)
        return {}

    print(f"Found {len(all_documents)} documents")

    # Generate documents.json
    json_path = generate_documents_json(all_documents)
    json_size = json_path.stat().st_size / 1024 / 1024
    print(f"Generated: {json_path} ({json_size:.2f} MB)")

    # Generate explorer page
    html_path = generate_explorer_page(external_pdf_viewer=external_pdf_viewer)
    html_size = html_path.stat().st_size / 1024
    print(f"Generated: {html_path} ({html_size:.1f} KB)")

    return {
        "documents_json": json_path,
        "explorer_html": html_path,
    }


def generate_data_only(
    transcript_dir: str | None = None,
    pdf_dir: str | None = None,
) -> Path | None:
    """Generate only documents.json without the explorer page.

    Args:
        transcript_dir: Directory containing JSON transcripts
        pdf_dir: Directory containing source PDFs

    Returns:
        Path to generated file, or None if no documents found
    """
    if transcript_dir is None:
        transcript_dir = get_latest_transcript_dir()

    if pdf_dir is None:
        pdf_dir = str(DEFAULT_PDF_DIR)

    print(f"Processing transcripts from: {transcript_dir}")

    # Process documents
    results = process_documents(transcript_dir, full_mode=True, pdf_dir=pdf_dir)
    all_documents = results.get("all_documents", [])

    if not all_documents:
        print("Warning: No documents found!", file=sys.stderr)
        return None

    print(f"Found {len(all_documents)} documents")

    # Generate documents.json
    json_path = generate_documents_json(all_documents)
    json_size = json_path.stat().st_size / 1024 / 1024
    print(f"Generated: {json_path} ({json_size:.2f} MB)")

    return json_path


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate document explorer for declassified documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    uv run python -m app.explorer generate
    uv run python -m app.explorer data
    uv run python -m app.explorer generate --transcript-dir data/generated_transcripts/gpt-5-mini-v2.2.0
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command (both data and page)
    gen_parser = subparsers.add_parser("generate", help="Generate explorer data and page")
    gen_parser.add_argument(
        "--transcript-dir",
        help="Directory containing JSON transcripts (default: latest in data/generated_transcripts/)",
    )
    gen_parser.add_argument(
        "--pdf-dir",
        default=str(DEFAULT_PDF_DIR),
        help="Directory containing source PDFs",
    )
    gen_parser.add_argument(
        "--external-viewer",
        default=DEFAULT_EXTERNAL_VIEWER,
        help="Base URL for external PDF viewer",
    )

    # Data-only command
    data_parser = subparsers.add_parser("data", help="Generate only documents.json")
    data_parser.add_argument(
        "--transcript-dir",
        help="Directory containing JSON transcripts",
    )
    data_parser.add_argument(
        "--pdf-dir",
        default=str(DEFAULT_PDF_DIR),
        help="Directory containing source PDFs",
    )

    args = parser.parse_args()

    if args.command == "generate":
        generate_all(
            transcript_dir=args.transcript_dir,
            pdf_dir=args.pdf_dir,
            external_pdf_viewer=args.external_viewer,
        )
    elif args.command == "data":
        generate_data_only(
            transcript_dir=args.transcript_dir,
            pdf_dir=args.pdf_dir,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
