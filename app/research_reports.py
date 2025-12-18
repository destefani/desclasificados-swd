"""
HTML Research Report Generator for the Desclasificados project.

Generates standalone HTML reports for research questions that can be
deployed to GitHub Pages alongside the main analysis report.

Supports two modes:
1. Rich reports: Uses structured JSON data from data/research_reports/{id}.json
2. Basic reports: Falls back to data from research_questions.json
"""

import argparse
import json
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

# Directories
DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs"
REPORTS_DATA_DIR = DATA_DIR / "research_reports"
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


def load_rich_report_data(question_id: str) -> dict | None:
    """Load rich report data from JSON file if it exists."""
    filename = f"{question_id.lower()}.json"
    filepath = REPORTS_DATA_DIR / filename
    if filepath.exists():
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    return None


def doc_link(doc_id: str, external_viewer: str, text: str | None = None) -> str:
    """Generate HTML link to a document."""
    url = f"{external_viewer}/?currentPage=1&documentId={doc_id}"
    display_text = text or f"Document {doc_id}"
    return f'<a href="{url}" class="pdf-link external">{display_text}</a>'


def generate_rich_report_css() -> str:
    """Generate CSS styles for rich research reports."""
    return """
    :root {
        --primary: #2563EB;
        --primary-dark: #1a365d;
        --heading-color: #1a365d;
        --subheading-color: #2c5282;
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
        --quote-bg: #f7fafc;
        --quote-text: #4a5568;
        --table-header-bg: #2c5282;
        --table-row-bg: #f7fafc;
        --table-border: #cbd5e0;
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
        background: white;
    }

    /* Site Navigation */
    .site-nav {
        background: var(--gray-800);
        padding: 12px 20px;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    .site-nav a {
        color: var(--gray-200);
        text-decoration: none;
        font-size: 14px;
        padding: 6px 12px;
        border-radius: 4px;
        transition: background 0.2s;
    }

    .site-nav a:hover {
        background: rgba(255,255,255,0.1);
    }

    .site-nav .nav-brand {
        font-weight: 600;
        color: white;
        margin-right: 20px;
    }

    .site-nav .nav-divider {
        color: var(--gray-500);
        margin: 0 4px;
    }

    .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 40px 20px;
    }

    /* Header styles */
    header {
        text-align: center;
        margin-bottom: 40px;
        padding-bottom: 20px;
        border-bottom: 1px solid var(--gray-200);
    }

    header h1 {
        font-size: 24px;
        color: var(--gray-900);
        margin-bottom: 8px;
        line-height: 1.3;
    }

    header .subtitle {
        font-size: 14px;
        color: var(--gray-500);
        margin-bottom: 16px;
    }

    header .meta {
        font-size: 12px;
        color: var(--gray-400);
    }

    /* Section styles */
    .section-heading {
        font-size: 18px;
        color: var(--heading-color);
        margin: 30px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--gray-100);
    }

    .subheading {
        font-size: 14px;
        font-style: italic;
        color: var(--subheading-color);
        margin: 20px 0 12px 0;
    }

    /* Content styles */
    p {
        margin-bottom: 12px;
        font-size: 14px;
        line-height: 1.7;
    }

    .intro-text {
        font-size: 14px;
        margin-bottom: 20px;
    }

    /* Quote styles */
    blockquote {
        background: var(--quote-bg);
        color: var(--quote-text);
        padding: 16px 20px;
        margin: 16px 0;
        border-radius: 4px;
        font-size: 14px;
        line-height: 1.6;
        border-left: 4px solid var(--primary);
    }

    /* Source citation */
    .source {
        font-size: 12px;
        color: var(--gray-500);
        margin-top: 8px;
    }

    .source a {
        color: var(--primary);
        text-decoration: none;
    }

    .source a:hover {
        text-decoration: underline;
    }

    /* Document reference */
    .doc-ref {
        color: var(--primary);
        text-decoration: none;
    }

    .doc-ref:hover {
        text-decoration: underline;
    }

    /* Lists */
    ul {
        margin: 12px 0 12px 24px;
    }

    li {
        margin-bottom: 6px;
        font-size: 14px;
    }

    /* Tables */
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        font-size: 13px;
    }

    th {
        background: var(--table-header-bg);
        color: white;
        padding: 12px;
        text-align: left;
        font-weight: 500;
    }

    td {
        background: var(--table-row-bg);
        padding: 10px 12px;
        border: 1px solid var(--table-border);
    }

    td a {
        color: var(--primary);
        text-decoration: none;
    }

    td a:hover {
        text-decoration: underline;
    }

    /* Conclusion items */
    .conclusion-item {
        margin-bottom: 8px;
        font-size: 14px;
    }

    .conclusion-item strong {
        color: var(--gray-900);
    }

    /* Summary box */
    .summary-box {
        background: var(--gray-50);
        padding: 16px;
        border-radius: 4px;
        margin: 16px 0;
        font-size: 14px;
    }

    /* Methodology */
    .methodology-list {
        list-style: none;
        margin-left: 0;
    }

    .methodology-list li {
        margin-bottom: 4px;
    }

    /* Footer */
    footer {
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid var(--gray-200);
        text-align: center;
        font-size: 12px;
        color: var(--gray-500);
    }

    footer a {
        color: var(--primary);
        text-decoration: none;
    }

    footer a:hover {
        text-decoration: underline;
    }

    /* Breadcrumb */
    .breadcrumb {
        font-size: 13px;
        color: var(--gray-500);
        margin-bottom: 30px;
        text-align: left;
    }

    .breadcrumb a {
        color: var(--primary);
        text-decoration: none;
    }

    .breadcrumb a:hover {
        text-decoration: underline;
    }

    @media (max-width: 640px) {
        .container {
            padding: 20px 16px;
        }

        header h1 {
            font-size: 20px;
        }

        table {
            font-size: 12px;
        }

        th, td {
            padding: 8px;
        }
    }
    """


def render_content_item(
    item: dict,
    external_viewer: str,
) -> str:
    """Render a single content item to HTML."""
    item_type = item.get("type", "")

    if item_type == "paragraph":
        return f'<p>{item.get("text", "")}</p>'

    elif item_type == "quote":
        return f'<blockquote>"{item.get("text", "")}"</blockquote>'

    elif item_type == "document_reference":
        doc_id = item.get("doc_id", "")
        classification = item.get("classification", "")
        date = item.get("date", "")
        intro = item.get("intro", "")
        link = doc_link(doc_id, external_viewer)
        meta = f" ({classification}, {date})" if classification and date else ""
        return f'<p>{link}{meta} {intro}</p>'

    elif item_type == "source":
        doc_id = item.get("doc_id", "")
        description = item.get("description", "")
        link = doc_link(doc_id, external_viewer, f"Doc {doc_id}")
        return f'<p class="source">Source: {link}, {description}</p>'

    elif item_type == "subheading":
        return f'<h4 class="subheading">{item.get("text", "")}</h4>'

    elif item_type == "list":
        items_html = "".join(f"<li>{i}</li>" for i in item.get("items", []))
        return f"<ul>{items_html}</ul>"

    return ""


def render_section(section: dict, external_viewer: str) -> str:
    """Render a report section to HTML."""
    number = section.get("number", "")
    title = section.get("title", "")
    content = section.get("content", [])

    heading = f"{number}. {title}" if number else title
    content_html = "".join(
        render_content_item(item, external_viewer) for item in content
    )

    return f'<h2 class="section-heading">{heading}</h2>\n{content_html}'


def render_table(table: dict, external_viewer: str) -> str:
    """Render a table to HTML."""
    title = table.get("title", "")
    description = table.get("description", "")
    headers = table.get("headers", [])
    rows = table.get("rows", [])

    header_html = "".join(f"<th>{h}</th>" for h in headers)

    rows_html = ""
    for row in rows:
        cells = ""
        for i, cell in enumerate(row):
            # First column might be a document ID that should be linked
            if i == 0 and cell.isdigit() and title == "Key Source Documents":
                cell_content = doc_link(cell, external_viewer, cell)
            else:
                cell_content = cell
            cells += f"<td>{cell_content}</td>"
        rows_html += f"<tr>{cells}</tr>"

    desc_html = f'<p>{description}</p>' if description else ""

    return f'''
    <h2 class="section-heading">{title}</h2>
    {desc_html}
    <table>
        <thead><tr>{header_html}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    '''


def render_conclusions(conclusions: dict, external_viewer: str) -> str:
    """Render conclusions section to HTML."""
    html = '<h2 class="section-heading">Conclusions</h2>'

    # What the Documents Prove
    proven = conclusions.get("proven", {})
    if proven:
        html += f'<h4 class="subheading">{proven.get("title", "What the Documents Prove")}</h4>'
        html += "<ul>"
        for item in proven.get("items", []):
            bold = item.get("bold", "")
            text = item.get("text", "")
            html += f'<li class="conclusion-item"><strong>{bold}</strong> - {text}</li>'
        html += "</ul>"

    # Balanced Assessment
    balanced = conclusions.get("balanced", {})
    if balanced:
        html += f'<h4 class="subheading">{balanced.get("title", "Balanced Assessment")}</h4>'
        html += f'<p>{balanced.get("intro", "")}</p>'
        html += "<ul>"
        for caveat in balanced.get("caveats", []):
            html += f"<li>{caveat}</li>"
        html += "</ul>"
        summary = balanced.get("summary", "")
        if summary:
            html += f'<p><strong>The evidence suggests both factors contributed:</strong> {summary}</p>'

    return html


def render_methodology(methodology: dict, external_viewer: str) -> str:
    """Render methodology section to HTML."""
    description = methodology.get("description", "")

    items = [
        ("Index", f'{methodology.get("index_version", "")} (created {methodology.get("index_date", "")})'),
        ("Documents", f'{methodology.get("total_documents", "")} transcribed documents ({methodology.get("total_chunks", "")} text chunks)'),
        ("Sources", methodology.get("sources", "")),
        ("Embedding Model", methodology.get("embedding_model", "")),
        ("LLM", methodology.get("llm", "")),
        ("Queries", methodology.get("queries", "")),
    ]

    items_html = "".join(
        f"<li><strong>{label}:</strong> {value}</li>"
        for label, value in items if value
    )

    return f'''
    <h2 class="section-heading">Methodology</h2>
    <p>{description}</p>
    <ul class="methodology-list">{items_html}</ul>
    <p style="margin-top: 16px;">
        <strong>Document Viewer:</strong>
        <a href="{external_viewer}" target="_blank">{external_viewer}</a>
    </p>
    <p class="source">
        All document links open in the Desclasificados document viewer where you can browse the original declassified PDFs.
    </p>
    '''


def generate_rich_report_html(
    report_data: dict,
    question: dict,
    external_pdf_viewer: str,
) -> str:
    """Generate a rich HTML report from structured JSON data."""
    title = report_data.get("title", "")
    subtitle = report_data.get("subtitle", "")
    research_question = report_data.get("question", "")
    introduction = report_data.get("introduction", "")
    sections = report_data.get("sections", [])
    tables = report_data.get("tables", [])
    conclusions = report_data.get("conclusions", {})
    methodology = report_data.get("methodology", {})

    q_id = question.get("id", "")
    generated_date = datetime.now().strftime("%B %d, %Y")

    # Build methodology metadata line
    method = report_data.get("methodology", {})
    meta_line = f"Generated: {generated_date}"
    if method.get("index_version"):
        meta_line += f" | Source: {method['index_version']} ({method.get('total_documents', '')} documents, {method.get('total_chunks', '')} chunks)"

    # Render sections
    sections_html = "".join(render_section(s, external_pdf_viewer) for s in sections)

    # Render tables
    tables_html = "".join(render_table(t, external_pdf_viewer) for t in tables)

    # Render conclusions
    conclusions_html = render_conclusions(conclusions, external_pdf_viewer) if conclusions else ""

    # Render methodology
    methodology_html = render_methodology(methodology, external_pdf_viewer) if methodology else ""

    css = generate_rich_report_css()

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Desclasificados Research</title>
    <style>
{css}
    </style>
</head>
<body>
    <nav class="site-nav">
        <a href="../index.html" class="nav-brand">Desclasificados</a>
        <a href="../index.html">Dashboard</a>
        <a href="../about.html">About</a>
        <span class="nav-divider">|</span>
        <a href="../index.html#research-questions">Research Questions</a>
    </nav>

    <div class="container">
        <nav class="breadcrumb">
            <a href="../index.html#research-questions">Research Questions</a> /
            {q_id}
        </nav>

        <header>
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
            <p class="meta">{meta_line}</p>
        </header>

        <h2 class="section-heading">Research Question</h2>
        <p class="intro-text">{research_question}</p>
        <p>{introduction}</p>

        {sections_html}
        {tables_html}
        {conclusions_html}
        {methodology_html}

        <footer>
            <p>
                This report was generated from the <a href="../index.html">Desclasificados</a> project archive.<br>
                All cited documents are from declassified US government records.
            </p>
        </footer>
    </div>

    {generate_external_viewer_modal()}
    {generate_external_link_interceptor()}
</body>
</html>
'''


def generate_basic_report_css() -> str:
    """Generate CSS styles for basic research reports."""
    return """
    :root {
        --primary: #2563EB;
        --primary-dark: #1E40AF;
        --gray-50: #F9FAFB;
        --gray-100: #F3F4F6;
        --gray-200: #E5E7EB;
        --gray-500: #6B7280;
        --gray-600: #4B5563;
        --gray-700: #374151;
        --gray-800: #1F2937;
        --gray-900: #111827;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
        line-height: 1.6;
        color: var(--gray-800);
        background: var(--gray-50);
    }

    /* Site Navigation */
    .site-nav {
        background: var(--gray-800);
        padding: 12px 20px;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    .site-nav a {
        color: #E5E7EB;
        text-decoration: none;
        font-size: 14px;
        padding: 6px 12px;
        border-radius: 4px;
        transition: background 0.2s;
    }

    .site-nav a:hover {
        background: rgba(255,255,255,0.1);
    }

    .site-nav .nav-brand {
        font-weight: 600;
        color: white;
        margin-right: 20px;
    }

    .site-nav .nav-divider {
        color: #6B7280;
        margin: 0 4px;
    }

    .container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }

    header { margin-bottom: 40px; }

    .breadcrumb { font-size: 14px; color: var(--gray-500); margin-bottom: 20px; }
    .breadcrumb a { color: var(--primary); text-decoration: none; }
    .breadcrumb a:hover { text-decoration: underline; }

    h1 { font-size: 28px; color: var(--gray-900); margin-bottom: 16px; }

    .meta-badges { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
    .badge { font-size: 12px; padding: 4px 12px; border-radius: 16px; font-weight: 500; }
    .meta-info { font-size: 14px; color: var(--gray-500); }

    section { background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    section h2 { font-size: 18px; color: var(--gray-900); margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid var(--gray-100); }

    .summary-box { background: var(--gray-50); border-left: 4px solid var(--primary); padding: 16px; border-radius: 0 8px 8px 0; }

    .documents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
    .doc-card { background: var(--gray-50); padding: 12px; border-radius: 8px; font-size: 13px; }
    .doc-card .doc-id { font-family: monospace; font-weight: 600; }
    .doc-card a { color: var(--primary); text-decoration: none; }

    .methodology dl { display: grid; grid-template-columns: 150px 1fr; gap: 8px 16px; font-size: 14px; }
    .methodology dt { font-weight: 500; color: var(--gray-700); }
    .methodology dd { color: var(--gray-600); }

    footer { text-align: center; padding: 40px 20px; color: var(--gray-500); font-size: 13px; }
    footer a { color: var(--primary); text-decoration: none; }
    """


def generate_basic_report_html(
    question: dict,
    external_pdf_viewer: str | None = None,
) -> str:
    """Generate a basic HTML report from research_questions.json data."""
    q_id = question.get("id", "")
    q_text = question.get("question", "")
    category = question.get("category", "OTHER")
    status = question.get("status", "unanswered")
    date_asked = question.get("date_asked", "")
    relevance = question.get("relevance_score")
    rag_results = question.get("rag_results", "")
    related_docs = question.get("related_docs", [])
    notes = question.get("notes", "")

    status_info = STATUS_CONFIG.get(status, STATUS_CONFIG["unanswered"])
    status_style = f"background-color: {status_info['color']}20; color: {status_info['color']}; border: 1px solid {status_info['color']}40;"
    cat_color = CATEGORY_COLORS.get(category, "#9CA3AF")
    cat_style = f"background-color: {cat_color}20; color: {cat_color}; border: 1px solid {cat_color}40;"

    summary_html = f'<section><h2>Summary of Findings</h2><div class="summary-box">{rag_results}</div></section>' if rag_results else ""

    docs_html = ""
    if related_docs and external_pdf_viewer:
        doc_cards = "".join(
            f'<div class="doc-card"><div class="doc-id">Document {doc_id}</div><div><a href="{external_pdf_viewer}/?currentPage=1&documentId={doc_id}" class="pdf-link external">View Document</a></div></div>'
            for doc_id in related_docs
        )
        docs_html = f'<section><h2>Source Documents</h2><p style="margin-bottom:16px;color:var(--gray-600);">{len(related_docs)} document(s) identified as relevant.</p><div class="documents-grid">{doc_cards}</div></section>'

    notes_html = f'<section><h2>Research Notes</h2><p>{notes}</p></section>' if notes else ""

    relevance_str = f"{relevance:.1%}" if relevance is not None else "N/A"
    methodology_html = f'''<section><h2>Methodology</h2><div class="methodology"><dl>
        <dt>Question ID</dt><dd>{q_id}</dd>
        <dt>Date Asked</dt><dd>{date_asked}</dd>
        <dt>Category</dt><dd>{category}</dd>
        <dt>Status</dt><dd>{status_info['label']}</dd>
        <dt>Relevance Score</dt><dd>{relevance_str}</dd>
        <dt>Documents</dt><dd>{len(related_docs)}</dd>
    </dl></div></section>'''

    css = generate_basic_report_css()
    generated_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{q_id}: {q_text[:60]}{'...' if len(q_text) > 60 else ''} | Desclasificados Research</title>
    <style>{css}</style>
</head>
<body>
    <nav class="site-nav">
        <a href="../index.html" class="nav-brand">Desclasificados</a>
        <a href="../index.html">Dashboard</a>
        <a href="../about.html">About</a>
        <span class="nav-divider">|</span>
        <a href="../index.html#research-questions">Research Questions</a>
    </nav>
    <div class="container">
        <header>
            <nav class="breadcrumb"><a href="../index.html#research-questions">Research Questions</a> / {q_id}</nav>
            <h1>{q_text}</h1>
            <div class="meta-badges">
                <span class="badge" style="{status_style}">{status_info['icon']} {status_info['label']}</span>
                <span class="badge" style="{cat_style}">{category}</span>
            </div>
            <div class="meta-info">Asked on {date_asked} | Relevance: {relevance_str}</div>
        </header>
        {summary_html}
        {docs_html}
        {notes_html}
        {methodology_html}
        <footer><p>Part of the <a href="../index.html">Desclasificados</a> research project.<br>Generated on {generated_date}</p></footer>
    </div>
    {generate_external_viewer_modal() if external_pdf_viewer else ""}
    {generate_external_link_interceptor() if external_pdf_viewer else ""}
</body>
</html>'''


def generate_research_report_html(
    question: dict,
    external_pdf_viewer: str | None = None,
) -> str:
    """
    Generate an HTML report for a research question.

    Attempts to load rich report data first, falls back to basic format.
    """
    q_id = question.get("id", "")
    external_viewer = external_pdf_viewer or DEFAULT_EXTERNAL_VIEWER

    # Try to load rich report data
    rich_data = load_rich_report_data(q_id)

    if rich_data:
        return generate_rich_report_html(rich_data, question, external_viewer)
    else:
        return generate_basic_report_html(question, external_viewer)


def generate_all_reports(
    external_pdf_viewer: str | None = None,
    output_dir: Path | None = None,
) -> list[dict]:
    """Generate HTML reports for all research questions."""
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
    report_lookup = {r["id"]: r["relative_path"] for r in generated}

    for q in data.get("questions", []):
        q_id = q.get("id")
        if q_id in report_lookup:
            q["html_report"] = report_lookup[q_id]

    save_questions(data)
    print(f"\nUpdated {len(generated)} question(s) with html_report paths.")


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate HTML reports for research questions."""
    external_viewer = args.external_viewer or DEFAULT_EXTERNAL_VIEWER

    if args.question_id:
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

    gen_parser = subparsers.add_parser("generate", help="Generate HTML reports")
    gen_parser.add_argument("--question-id", "-q", type=str, help="Generate report for specific question ID")
    gen_parser.add_argument("--external-viewer", "-e", type=str, help=f"External PDF viewer URL (default: {DEFAULT_EXTERNAL_VIEWER})")
    gen_parser.add_argument("--update-tracker", action="store_true", help="Update research_questions.json with html_report paths")

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
