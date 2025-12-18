"""Research Questions Tracker for the Desclasificados project.

Tracks research questions asked during sessions, their status, RAG results,
and links to generated PDF reports.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

# Data file locations
DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
QUESTIONS_FILE = DATA_DIR / "research_questions.json"
MARKDOWN_FILE = DOCS_DIR / "research_questions.md"

# Status types
Status = Literal["unanswered", "partially_answered", "answered", "needs_more_data"]

# Category types (common themes in the archive)
CATEGORIES = [
    "OPERATION CONDOR",
    "HUMAN RIGHTS",
    "LETELIER ASSASSINATION",
    "COUP 1973",
    "ECONOMIC INTERVENTION",
    "ALLENDE GOVERNMENT",
    "PINOCHET REGIME",
    "DINA",
    "40 COMMITTEE",
    "TRACK II",
    "CIA OPERATIONS",
    "OTHER",
]


def load_questions() -> dict:
    """Load questions from the JSON file."""
    if not QUESTIONS_FILE.exists():
        return {"version": "1.0.0", "description": "Tracks research questions", "questions": []}
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_questions(data: dict) -> None:
    """Save questions to the JSON file."""
    QUESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_id(data: dict) -> str:
    """Generate the next question ID."""
    if not data["questions"]:
        return "RQ-001"
    max_num = max(int(q["id"].split("-")[1]) for q in data["questions"])
    return f"RQ-{max_num + 1:03d}"


def add_question(
    question: str,
    category: str = "OTHER",
    notes: str | None = None,
) -> dict:
    """Add a new research question to the tracker.

    Args:
        question: The research question text
        category: Topic category (from CATEGORIES list)
        notes: Optional notes about the question

    Returns:
        The newly created question record
    """
    data = load_questions()

    # Validate category
    if category.upper() not in CATEGORIES:
        category = "OTHER"
    else:
        category = category.upper()

    new_question: dict[str, str | float | list[str] | None] = {
        "id": generate_id(data),
        "question": question,
        "date_asked": datetime.now().strftime("%Y-%m-%d"),
        "category": category,
        "status": "unanswered",
        "rag_results": None,
        "relevance_score": None,
        "related_docs": [],
        "notes": notes,
        "pdf_report": None,
    }

    data["questions"].append(new_question)
    save_questions(data)
    generate_markdown()

    return new_question


def update_question(
    question_id: str,
    status: Status | None = None,
    rag_results: str | None = None,
    relevance_score: float | None = None,
    related_docs: list[str] | None = None,
    notes: str | None = None,
    pdf_report: str | None = None,
) -> dict | None:
    """Update an existing research question.

    Args:
        question_id: The question ID (e.g., "RQ-001")
        status: New status
        rag_results: Summary of RAG query results
        relevance_score: Top relevance score from RAG
        related_docs: List of relevant document IDs
        notes: Additional notes
        pdf_report: Path to generated PDF report

    Returns:
        The updated question record, or None if not found
    """
    data = load_questions()

    for q in data["questions"]:
        if q["id"] == question_id.upper():
            if status:
                q["status"] = status
            if rag_results:
                q["rag_results"] = rag_results
            if relevance_score is not None:
                q["relevance_score"] = relevance_score
            if related_docs:
                q["related_docs"] = related_docs
            if notes:
                q["notes"] = notes
            if pdf_report:
                q["pdf_report"] = pdf_report

            save_questions(data)
            generate_markdown()
            return q

    return None


def get_question(question_id: str) -> dict | None:
    """Get a question by ID."""
    data = load_questions()
    for q in data["questions"]:
        if q["id"] == question_id.upper():
            return q
    return None


def list_questions(
    status: Status | None = None,
    category: str | None = None,
) -> list[dict]:
    """List questions with optional filtering.

    Args:
        status: Filter by status
        category: Filter by category

    Returns:
        List of matching questions
    """
    data = load_questions()
    questions = data["questions"]

    if status:
        questions = [q for q in questions if q["status"] == status]
    if category:
        questions = [q for q in questions if q["category"] == category.upper()]

    return questions


def generate_markdown() -> None:
    """Generate the markdown documentation file from JSON data."""
    data = load_questions()
    questions = data["questions"]

    # Build markdown content
    lines = [
        "# Research Questions Tracker",
        "",
        "This document tracks research questions asked about the declassified CIA documents.",
        "Auto-generated from `data/research_questions.json`.",
        "",
        f"**Total Questions:** {len(questions)}",
        "",
    ]

    # Summary by status
    status_counts: dict[str, int] = {}
    for q in questions:
        status_counts[q["status"]] = status_counts.get(q["status"], 0) + 1

    if status_counts:
        lines.append("## Summary by Status")
        lines.append("")
        lines.append("| Status | Count |")
        lines.append("|--------|-------|")
        for status, count in sorted(status_counts.items()):
            lines.append(f"| {status} | {count} |")
        lines.append("")

    # Summary by category
    cat_counts: dict[str, int] = {}
    for q in questions:
        cat_counts[q["category"]] = cat_counts.get(q["category"], 0) + 1

    if cat_counts:
        lines.append("## Summary by Category")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        for cat, count in sorted(cat_counts.items()):
            lines.append(f"| {cat} | {count} |")
        lines.append("")

    # Question details
    if questions:
        lines.append("## Questions")
        lines.append("")

        for q in questions:
            lines.append(f"### {q['id']}: {q['question'][:80]}{'...' if len(q['question']) > 80 else ''}")
            lines.append("")
            lines.append(f"- **Full Question:** {q['question']}")
            lines.append(f"- **Date Asked:** {q['date_asked']}")
            lines.append(f"- **Category:** {q['category']}")
            lines.append(f"- **Status:** {q['status']}")

            if q.get("relevance_score") is not None:
                lines.append(f"- **Top Relevance Score:** {q['relevance_score']:.2%}")

            if q.get("related_docs"):
                docs_str = ", ".join(q["related_docs"][:5])
                if len(q["related_docs"]) > 5:
                    docs_str += f" (+{len(q['related_docs']) - 5} more)"
                lines.append(f"- **Related Documents:** {docs_str}")

            if q.get("pdf_report"):
                lines.append(f"- **PDF Report:** [{q['pdf_report']}](../{q['pdf_report']})")

            if q.get("rag_results"):
                lines.append("")
                lines.append("**RAG Results Summary:**")
                lines.append(f"> {q['rag_results']}")

            if q.get("notes"):
                lines.append("")
                lines.append(f"**Notes:** {q['notes']}")

            lines.append("")
            lines.append("---")
            lines.append("")

    # Write markdown file
    MARKDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MARKDOWN_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def print_question(q: dict) -> None:
    """Print a question to stdout."""
    print(f"\n{q['id']}: {q['question']}")
    print(f"  Category: {q['category']}")
    print(f"  Status: {q['status']}")
    print(f"  Date: {q['date_asked']}")
    if q.get("relevance_score") is not None:
        print(f"  Relevance: {q['relevance_score']:.2%}")
    if q.get("pdf_report"):
        print(f"  PDF Report: {q['pdf_report']}")
    if q.get("notes"):
        print(f"  Notes: {q['notes']}")


# CLI Commands
def cmd_add(args: argparse.Namespace) -> None:
    """Add a new question."""
    q = add_question(
        question=args.question,
        category=args.category or "OTHER",
        notes=args.notes,
    )
    print(f"Added question {q['id']}")
    print_question(q)


def cmd_update(args: argparse.Namespace) -> None:
    """Update an existing question."""
    related_docs = args.docs.split(",") if args.docs else None

    q = update_question(
        question_id=args.id,
        status=args.status,
        rag_results=args.rag_results,
        relevance_score=float(args.relevance) if args.relevance else None,
        related_docs=related_docs,
        notes=args.notes,
        pdf_report=args.pdf_report,
    )

    if q:
        print(f"Updated question {q['id']}")
        print_question(q)
    else:
        print(f"Question {args.id} not found")
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List questions."""
    questions = list_questions(status=args.status, category=args.category)

    if not questions:
        print("No questions found matching criteria")
        return

    print(f"\nFound {len(questions)} question(s):\n")
    print("-" * 80)

    for q in questions:
        print_question(q)

    print("-" * 80)


def cmd_show(args: argparse.Namespace) -> None:
    """Show a specific question."""
    q = get_question(args.id)
    if q:
        print_question(q)
        if q.get("rag_results"):
            print(f"\n  RAG Results:\n    {q['rag_results']}")
    else:
        print(f"Question {args.id} not found")
        sys.exit(1)


def cmd_generate_md(args: argparse.Namespace) -> None:
    """Regenerate the markdown file."""
    generate_markdown()
    print(f"Markdown generated: {MARKDOWN_FILE}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Research Questions Tracker for Desclasificados",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new research question")
    add_parser.add_argument("question", type=str, help="The research question")
    add_parser.add_argument("--category", "-c", type=str, help=f"Category: {', '.join(CATEGORIES)}")
    add_parser.add_argument("--notes", "-n", type=str, help="Initial notes")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update a research question")
    update_parser.add_argument("id", type=str, help="Question ID (e.g., RQ-001)")
    update_parser.add_argument("--status", "-s", type=str,
                               choices=["unanswered", "partially_answered", "answered", "needs_more_data"],
                               help="New status")
    update_parser.add_argument("--rag-results", "-r", type=str, help="RAG results summary")
    update_parser.add_argument("--relevance", type=str, help="Top relevance score (0.0-1.0)")
    update_parser.add_argument("--docs", "-d", type=str, help="Comma-separated document IDs")
    update_parser.add_argument("--notes", "-n", type=str, help="Additional notes")
    update_parser.add_argument("--pdf-report", "-p", type=str, help="Path to PDF report")

    # List command
    list_parser = subparsers.add_parser("list", help="List research questions")
    list_parser.add_argument("--status", "-s", type=str,
                             choices=["unanswered", "partially_answered", "answered", "needs_more_data"],
                             help="Filter by status")
    list_parser.add_argument("--category", "-c", type=str, help="Filter by category")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show a specific question")
    show_parser.add_argument("id", type=str, help="Question ID (e.g., RQ-001)")

    # Generate markdown command
    subparsers.add_parser("generate-md", help="Regenerate the markdown file")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "add":
        cmd_add(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "generate-md":
        cmd_generate_md(args)


if __name__ == "__main__":
    main()
