"""Document and Entity Explorer generator for the Desclasificados project.

Generates standalone explorers with search, filter, and pagination
for browsing declassified documents and entities (people, orgs, keywords, places).

Usage:
    uv run python -m app.explorer generate    # Generate all explorers + data
    uv run python -m app.explorer data        # Generate only JSON data files
    uv run python -m app.explorer entities    # Generate only entities explorer
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
ENTITIES_DIR = DOCS_DIR / "entities"

# Default external PDF viewer
DEFAULT_EXTERNAL_VIEWER = "https://declasseuucl.vercel.app"

# Default PDF directory
DEFAULT_PDF_DIR = Path(__file__).parent.parent / "data" / "original_pdfs"

# Entity type icons for display
ENTITY_ICONS = {
    "person": "👤",
    "organization": "🏛️",
    "keyword": "🏷️",
    "place": "📍",
}


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


def generate_entities_json(
    results: dict[str, Any],
    output_dir: str | Path = DATA_DIR,
    output_file: str = "entities.json",
) -> Path:
    """Extract and save entity metadata for the entity explorer.

    Aggregates people, organizations, keywords, and places from processed documents.

    Args:
        results: Results dictionary from process_documents(full_mode=True)
        output_dir: Directory to write the JSON file
        output_file: Name of the output file

    Returns:
        Path to the generated file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    entities: list[dict[str, Any]] = []
    letters_set: set[str] = set()

    # Helper to create entity ID
    def make_id(entity_type: str, name: str) -> str:
        slug = name.lower().replace(" ", "-").replace(",", "").replace(".", "")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")[:50]
        return f"{entity_type}-{slug}"

    # Helper to get first letter
    def get_first_letter(name: str) -> str:
        if name:
            first = name[0].upper()
            if first.isalpha():
                return first
        return "#"

    # Helper to extract sample doc IDs from docs list
    def get_sample_docs(
        docs_list: list[tuple[str, str, str]] | list[tuple[str, str]],
        limit: int = 3
    ) -> list[str]:
        samples = []
        for doc in docs_list[:limit]:
            # docs_list items are (doc_id, pdf_path, basename) or (doc_id, pdf_path)
            if len(doc) >= 3:
                samples.append(doc[2])  # basename
            elif len(doc) >= 1:
                samples.append(doc[0])  # doc_id
        return samples

    # Process People
    people_count = results.get("people_count", {})
    people_docs = results.get("people_docs", {})
    for name, count in people_count.items():
        if not name or count < 1:
            continue
        first_letter = get_first_letter(name)
        letters_set.add(first_letter)
        docs_list = people_docs.get(name, [])
        entities.append({
            "id": make_id("person", name),
            "name": name,
            "type": "person",
            "doc_count": count,
            "first_letter": first_letter,
            "sample_docs": get_sample_docs(docs_list),
        })

    # Process Organizations
    org_count = results.get("org_count", {})
    org_docs = results.get("org_docs", {})
    for name, count in org_count.items():
        if not name or count < 1:
            continue
        first_letter = get_first_letter(name)
        letters_set.add(first_letter)
        docs_list = org_docs.get(name, [])
        entities.append({
            "id": make_id("organization", name),
            "name": name,
            "type": "organization",
            "doc_count": count,
            "first_letter": first_letter,
            "sample_docs": get_sample_docs(docs_list),
        })

    # Process Keywords
    keywords_count = results.get("keywords_count", {})
    keyword_docs = results.get("keyword_docs", {})
    for name, count in keywords_count.items():
        if not name or count < 1:
            continue
        first_letter = get_first_letter(name)
        letters_set.add(first_letter)
        docs_list = keyword_docs.get(name, [])
        entities.append({
            "id": make_id("keyword", name),
            "name": name,
            "type": "keyword",
            "doc_count": count,
            "first_letter": first_letter,
            "sample_docs": get_sample_docs(docs_list),
        })

    # Process Places (countries, cities, other)
    for place_type, count_key in [
        ("country", "country_count"),
        ("city", "city_count"),
        ("other", "other_place_count"),
    ]:
        place_count = results.get(count_key, {})
        for name, count in place_count.items():
            if not name or count < 1:
                continue
            first_letter = get_first_letter(name)
            letters_set.add(first_letter)
            entities.append({
                "id": make_id("place", f"{place_type}-{name}"),
                "name": name,
                "type": "place",
                "subtype": place_type,
                "doc_count": count,
                "first_letter": first_letter,
                "sample_docs": [],  # Places don't have doc refs in current data
            })

    # Sort by doc_count descending by default
    entities.sort(key=lambda e: (-e["doc_count"], e["name"]))

    # Calculate type counts for facets
    type_counts = {"person": 0, "organization": 0, "keyword": 0, "place": 0}
    subtype_counts: dict[str, int] = {}
    doc_counts = [e["doc_count"] for e in entities]

    for entity in entities:
        type_counts[entity["type"]] += 1
        if entity["type"] == "place":
            subtype = entity.get("subtype", "other")
            subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1

    # Build facets
    facets = {
        "types": type_counts,
        "subtypes": {"place": subtype_counts},
        "letters": sorted(letters_set),
        "doc_count_range": {
            "min": min(doc_counts) if doc_counts else 0,
            "max": max(doc_counts) if doc_counts else 0,
        },
    }

    output = {
        "generated": datetime.now().isoformat(),
        "total_count": len(entities),
        "schema_version": "1.0.0",
        "entities": entities,
        "facets": facets,
    }

    output_path = output_dir / output_file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    return output_path


def generate_entity_explorer_page(
    output_dir: str | Path = ENTITIES_DIR,
    output_file: str = "index.html",
    external_pdf_viewer: str = DEFAULT_EXTERNAL_VIEWER,
) -> Path:
    """Generate the standalone entity explorer HTML page.

    Args:
        output_dir: Directory to write the HTML file
        output_file: Name of the output file
        external_pdf_viewer: Base URL for external PDF viewer

    Returns:
        Path to the generated file
    """
    # Import here to avoid circular imports
    from app.visualizations.entity_explorer import generate_entity_explorer_html

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    html_content = generate_entity_explorer_html(external_pdf_viewer=external_pdf_viewer)

    output_path = output_dir / output_file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

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
    """Generate all explorer data and pages (documents + entities).

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

    # Generate document explorer page
    html_path = generate_explorer_page(external_pdf_viewer=external_pdf_viewer)
    html_size = html_path.stat().st_size / 1024
    print(f"Generated: {html_path} ({html_size:.1f} KB)")

    # Generate entities.json
    entities_json_path = generate_entities_json(results)
    entities_json_size = entities_json_path.stat().st_size / 1024
    print(f"Generated: {entities_json_path} ({entities_json_size:.1f} KB)")

    # Generate entity explorer page
    entities_html_path = generate_entity_explorer_page(
        external_pdf_viewer=external_pdf_viewer
    )
    entities_html_size = entities_html_path.stat().st_size / 1024
    print(f"Generated: {entities_html_path} ({entities_html_size:.1f} KB)")

    return {
        "documents_json": json_path,
        "explorer_html": html_path,
        "entities_json": entities_json_path,
        "entities_html": entities_html_path,
    }


def generate_data_only(
    transcript_dir: str | None = None,
    pdf_dir: str | None = None,
) -> dict[str, Path]:
    """Generate only data files (documents.json + entities.json) without HTML pages.

    Args:
        transcript_dir: Directory containing JSON transcripts
        pdf_dir: Directory containing source PDFs

    Returns:
        Dictionary with paths to generated files
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
        return {}

    print(f"Found {len(all_documents)} documents")

    # Generate documents.json
    json_path = generate_documents_json(all_documents)
    json_size = json_path.stat().st_size / 1024 / 1024
    print(f"Generated: {json_path} ({json_size:.2f} MB)")

    # Generate entities.json
    entities_json_path = generate_entities_json(results)
    entities_json_size = entities_json_path.stat().st_size / 1024
    print(f"Generated: {entities_json_path} ({entities_json_size:.1f} KB)")

    return {
        "documents_json": json_path,
        "entities_json": entities_json_path,
    }


def generate_entities_only(
    transcript_dir: str | None = None,
    pdf_dir: str | None = None,
    external_pdf_viewer: str = DEFAULT_EXTERNAL_VIEWER,
) -> dict[str, Path]:
    """Generate only entity explorer (entities.json + page).

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

    # Process documents
    results = process_documents(transcript_dir, full_mode=True, pdf_dir=pdf_dir)
    all_documents = results.get("all_documents", [])

    if not all_documents:
        print("Warning: No documents found!", file=sys.stderr)
        return {}

    print(f"Found {len(all_documents)} documents")

    # Generate entities.json
    entities_json_path = generate_entities_json(results)
    entities_json_size = entities_json_path.stat().st_size / 1024
    print(f"Generated: {entities_json_path} ({entities_json_size:.1f} KB)")

    # Generate entity explorer page
    entities_html_path = generate_entity_explorer_page(
        external_pdf_viewer=external_pdf_viewer
    )
    entities_html_size = entities_html_path.stat().st_size / 1024
    print(f"Generated: {entities_html_path} ({entities_html_size:.1f} KB)")

    return {
        "entities_json": entities_json_path,
        "entities_html": entities_html_path,
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate document and entity explorers for declassified documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    uv run python -m app.explorer generate     # Generate all (docs + entities)
    uv run python -m app.explorer data         # Generate only JSON data files
    uv run python -m app.explorer entities     # Generate only entity explorer
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command (all data and pages)
    gen_parser = subparsers.add_parser(
        "generate", help="Generate all explorer data and pages"
    )
    gen_parser.add_argument(
        "--transcript-dir",
        help="Directory containing JSON transcripts (default: latest)",
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
    data_parser = subparsers.add_parser(
        "data", help="Generate only JSON data files (no HTML)"
    )
    data_parser.add_argument(
        "--transcript-dir",
        help="Directory containing JSON transcripts",
    )
    data_parser.add_argument(
        "--pdf-dir",
        default=str(DEFAULT_PDF_DIR),
        help="Directory containing source PDFs",
    )

    # Entities-only command
    entities_parser = subparsers.add_parser(
        "entities", help="Generate only entity explorer"
    )
    entities_parser.add_argument(
        "--transcript-dir",
        help="Directory containing JSON transcripts",
    )
    entities_parser.add_argument(
        "--pdf-dir",
        default=str(DEFAULT_PDF_DIR),
        help="Directory containing source PDFs",
    )
    entities_parser.add_argument(
        "--external-viewer",
        default=DEFAULT_EXTERNAL_VIEWER,
        help="Base URL for external PDF viewer",
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
    elif args.command == "entities":
        generate_entities_only(
            transcript_dir=args.transcript_dir,
            pdf_dir=args.pdf_dir,
            external_pdf_viewer=args.external_viewer,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
