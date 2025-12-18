"""
HTML Research Report Generator for the Desclasificados project.

Generates standalone HTML reports for research questions that can be
deployed to GitHub Pages alongside the main analysis report.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from app.research_tracker import load_questions
from app.visualizations.pdf_viewer import (
    generate_external_link_interceptor,
    generate_external_viewer_modal,
)
from app.visualizations.research_questions import (
    CATEGORY_COLORS,
    STATUS_CONFIG,
)

# Output directories
DOCS_DIR = Path(__file__).parent.parent / "docs"
REPORTS_OUTPUT_DIR = DOCS_DIR / "reports"

# External viewer URL
DEFAULT_EXTERNAL_VIEWER = "https://declasseuucl.vercel.app"


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")[:50]


def get_report_filename(question: dict) -> str:
    """Generate a filename for a research question report."""
    q_id = question.get("id", "unknown").lower()
    category = slugify(question.get("category", "other"))
    return f"{q_id}-{category}.html"


def generate_report_css() -> str:
    """Generate CSS styles for standalone research reports."""
    return """
    :root {
        --primary: #2563EB;
        --primary-dark: #1E40AF;
        --gray-50: #F9FAFB;
        --gray-100: #F3F4F6;
        --gray-200: #E5E7EB;
        --gray-300: #D1D5DB;
        --gray-400: #9CA3AF;
        --gray-500: #6B7280;
        --gray-600: #4B5563;
        --gray-700: #374151;
        --gray-800: #1F2937;
        --gray-900: #111827;
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        line-height: 1.6;
        color: var(--gray-800);
        background: var(--gray-50);
    }

    .container {
        max-width: 900px;
        margin: 0 auto;
        padding: 40px 20px;
    }

    header {
        margin-bottom: 40px;
    }

    .breadcrumb {
        font-size: 14px;
        color: var(--gray-500);
        margin-bottom: 20px;
    }

    .breadcrumb a {
        color: var(--primary);
        text-decoration: none;
    }

    .breadcrumb a:hover {
        text-decoration: underline;
    }

    h1 {
        font-size: 28px;
        color: var(--gray-900);
        margin-bottom: 16px;
        line-height: 1.3;
    }

    .meta-badges {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 16px;
    }

    .badge {
        font-size: 12px;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 500;
    }

    .meta-info {
        font-size: 14px;
        color: var(--gray-500);
    }

    section {
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    section h2 {
        font-size: 18px;
        color: var(--gray-900);
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--gray-100);
    }

    .summary-box {
        background: var(--gray-50);
        border-left: 4px solid var(--primary);
        padding: 16px;
        border-radius: 0 8px 8px 0;
        font-size: 15px;
    }

    .evidence-list {
        list-style: none;
    }

    .evidence-item {
        padding: 16px;
        border: 1px solid var(--gray-200);
        border-radius: 8px;
        margin-bottom: 12px;
    }

    .evidence-item:last-child {
        margin-bottom: 0;
    }

    blockquote {
        font-style: italic;
        color: var(--gray-700);
        margin-bottom: 12px;
        padding-left: 16px;
        border-left: 3px solid var(--gray-300);
    }

    .evidence-source {
        font-size: 13px;
        color: var(--gray-500);
    }

    .evidence-source a {
        color: var(--primary);
        text-decoration: none;
    }

    .evidence-source a:hover {
        text-decoration: underline;
    }

    .doc-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    .doc-link::after {
        content: " ↗";
        font-size: 0.85em;
    }

    .documents-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 12px;
    }

    .doc-card {
        background: var(--gray-50);
        padding: 12px;
        border-radius: 8px;
        font-size: 13px;
    }

    .doc-card .doc-id {
        font-family: monospace;
        font-weight: 600;
        color: var(--gray-900);
    }

    .doc-card .doc-meta {
        color: var(--gray-500);
        margin-top: 4px;
    }

    .doc-card a {
        color: var(--primary);
        text-decoration: none;
    }

    .doc-card a:hover {
        text-decoration: underline;
    }

    .methodology {
        font-size: 14px;
        color: var(--gray-600);
    }

    .methodology dl {
        display: grid;
        grid-template-columns: 150px 1fr;
        gap: 8px 16px;
    }

    .methodology dt {
        font-weight: 500;
        color: var(--gray-700);
    }

    .methodology dd {
        color: var(--gray-600);
    }

    footer {
        text-align: center;
        padding: 40px 20px;
        color: var(--gray-500);
        font-size: 13px;
    }

    footer a {
        color: var(--primary);
        text-decoration: none;
    }

    footer a:hover {
        text-decoration: underline;
    }

    @media (max-width: 640px) {
        .container {
            padding: 20px 16px;
        }

        h1 {
            font-size: 22px;
        }

        section {
            padding: 16px;
        }

        .methodology dl {
            grid-template-columns: 1fr;
        }
    }
    """


def generate_research_report_html(
    question: dict,
    external_pdf_viewer: str | None = None,
) -> str:
    """
    Generate a standalone HTML report for a research question.

    Args:
        question: The research question dict from the tracker
        external_pdf_viewer: Base URL for the external document viewer

    Returns:
        Complete HTML string for the report
    """
    q_id = question.get("id", "")
    q_text = question.get("question", "")
    category = question.get("category", "OTHER")
    status = question.get("status", "unanswered")
    date_asked = question.get("date_asked", "")
    relevance = question.get("relevance_score")
    rag_results = question.get("rag_results", "")
    related_docs = question.get("related_docs", [])
    notes = question.get("notes", "")

    # Status badge
    status_info = STATUS_CONFIG.get(status, STATUS_CONFIG["unanswered"])
    status_style = f"background-color: {status_info['color']}20; color: {status_info['color']}; border: 1px solid {status_info['color']}40;"

    # Category badge
    cat_color = CATEGORY_COLORS.get(category, "#9CA3AF")
    cat_style = f"background-color: {cat_color}20; color: {cat_color}; border: 1px solid {cat_color}40;"

    # Build summary section
    summary_html = ""
    if rag_results:
        summary_html = f"""
        <section>
            <h2>Summary of Findings</h2>
            <div class="summary-box">
                {rag_results}
            </div>
        </section>
        """

    # Build documents section
    docs_html = ""
    if related_docs:
        doc_cards = ""
        for doc_id in related_docs:
            if external_pdf_viewer:
                link = f'<a href="{external_pdf_viewer}/?currentPage=1&documentId={doc_id}" class="pdf-link external">View Document</a>'
            else:
                link = ""
            doc_cards += f"""
            <div class="doc-card">
                <div class="doc-id">Document {doc_id}</div>
                <div class="doc-meta">{link}</div>
            </div>
            """

        docs_html = f"""
        <section>
            <h2>Source Documents</h2>
            <p style="margin-bottom: 16px; color: var(--gray-600);">
                {len(related_docs)} document(s) identified as relevant to this research question.
            </p>
            <div class="documents-grid">
                {doc_cards}
            </div>
        </section>
        """

    # Notes section
    notes_html = ""
    if notes:
        notes_html = f"""
        <section>
            <h2>Research Notes</h2>
            <p>{notes}</p>
        </section>
        """

    # Methodology section
    relevance_str = f"{relevance:.1%}" if relevance is not None else "N/A"
    methodology_html = f"""
    <section>
        <h2>Methodology</h2>
        <div class="methodology">
            <dl>
                <dt>Question ID</dt>
                <dd>{q_id}</dd>
                <dt>Date Asked</dt>
                <dd>{date_asked}</dd>
                <dt>Category</dt>
                <dd>{category}</dd>
                <dt>Status</dt>
                <dd>{status_info['label']}</dd>
                <dt>Top Relevance Score</dt>
                <dd>{relevance_str}</dd>
                <dt>Documents Analyzed</dt>
                <dd>{len(related_docs)}</dd>
            </dl>
        </div>
    </section>
    """

    # Build full HTML
    css = generate_report_css()
    generated_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{q_id}: {q_text[:60]}{'...' if len(q_text) > 60 else ''} | Desclasificados Research</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <nav class="breadcrumb">
                <a href="../index.html">Analysis Report</a> /
                <a href="../index.html#research-questions">Research Questions</a> /
                {q_id}
            </nav>
            <h1>{q_text}</h1>
            <div class="meta-badges">
                <span class="badge" style="{status_style}">{status_info['icon']} {status_info['label']}</span>
                <span class="badge" style="{cat_style}">{category}</span>
            </div>
            <div class="meta-info">
                Asked on {date_asked} | Relevance: {relevance_str}
            </div>
        </header>

        {summary_html}
        {docs_html}
        {notes_html}
        {methodology_html}

        <footer>
            <p>
                Part of the <a href="../index.html">Desclasificados</a> research project.<br>
                Generated on {generated_date}
            </p>
        </footer>
    </div>

    {generate_external_viewer_modal() if external_pdf_viewer else ""}
    {generate_external_link_interceptor() if external_pdf_viewer else ""}
</body>
</html>
"""


def generate_all_reports(
    external_pdf_viewer: str | None = None,
    output_dir: Path | None = None,
) -> list[dict]:
    """
    Generate HTML reports for all research questions.

    Args:
        external_pdf_viewer: Base URL for external document viewer
        output_dir: Output directory (defaults to docs/reports/)

    Returns:
        List of generated report info dicts
    """
    if output_dir is None:
        output_dir = REPORTS_OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    data = load_questions()
    questions = data.get("questions", [])

    if not questions:
        print("No research questions found.")
        return []

    generated = []
    for question in questions:
        filename = get_report_filename(question)
        filepath = output_dir / filename

        html = generate_research_report_html(question, external_pdf_viewer)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        # Update the question with the html_report path
        relative_path = f"reports/{filename}"
        generated.append({
            "id": question.get("id"),
            "filename": filename,
            "path": str(filepath),
            "relative_path": relative_path,
        })

        print(f"Generated: {filepath}")

    return generated


def update_questions_with_html_reports(generated: list[dict]) -> None:
    """Update research_questions.json with html_report paths."""
    from app.research_tracker import load_questions, save_questions

    data = load_questions()

    # Create lookup by ID
    report_lookup = {r["id"]: r["relative_path"] for r in generated}

    # Update questions
    for q in data.get("questions", []):
        q_id = q.get("id")
        if q_id in report_lookup:
            q["html_report"] = report_lookup[q_id]

    save_questions(data)
    print(f"\nUpdated {len(generated)} question(s) with html_report paths.")


# CLI Commands
def cmd_generate(args: argparse.Namespace) -> None:
    """Generate HTML reports for research questions."""
    external_viewer = args.external_viewer or DEFAULT_EXTERNAL_VIEWER

    if args.question_id:
        # Generate single report
        data = load_questions()
        question = None
        for q in data.get("questions", []):
            if q.get("id", "").upper() == args.question_id.upper():
                question = q
                break

        if not question:
            print(f"Question {args.question_id} not found.")
            sys.exit(1)

        output_dir = REPORTS_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = get_report_filename(question)
        filepath = output_dir / filename

        html = generate_research_report_html(question, external_viewer)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Generated: {filepath}")
    else:
        # Generate all reports
        generated = generate_all_reports(external_viewer)

        if generated and args.update_tracker:
            update_questions_with_html_reports(generated)


def cmd_list(args: argparse.Namespace) -> None:
    """List existing HTML reports."""
    if not REPORTS_OUTPUT_DIR.exists():
        print("No reports directory found.")
        return

    reports = list(REPORTS_OUTPUT_DIR.glob("rq-*.html"))
    if not reports:
        print("No HTML reports found.")
        return

    print(f"\nFound {len(reports)} HTML report(s):\n")
    for report in sorted(reports):
        print(f"  {report.name}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate HTML research reports for GitHub Pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate HTML reports")
    gen_parser.add_argument(
        "--question-id", "-q",
        type=str,
        help="Generate report for specific question ID (e.g., RQ-001)"
    )
    gen_parser.add_argument(
        "--external-viewer", "-e",
        type=str,
        help=f"External PDF viewer URL (default: {DEFAULT_EXTERNAL_VIEWER})"
    )
    gen_parser.add_argument(
        "--update-tracker",
        action="store_true",
        help="Update research_questions.json with html_report paths"
    )

    # List command
    subparsers.add_parser("list", help="List existing HTML reports")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
