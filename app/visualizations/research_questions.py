"""
Research questions visualization for GitHub Pages.

Generates the research questions index page and integrates with the main report.
"""

import json
from pathlib import Path

# Status display configuration
STATUS_CONFIG = {
    "answered": {"icon": "✅", "color": "#16A34A", "label": "Answered"},
    "partially_answered": {"icon": "🔄", "color": "#CA8A04", "label": "Partial"},
    "unanswered": {"icon": "❓", "color": "#6B7280", "label": "Unanswered"},
    "needs_more_data": {"icon": "📊", "color": "#DC2626", "label": "Needs Data"},
}

# Category colors (matching existing theme)
CATEGORY_COLORS = {
    "OPERATION CONDOR": "#DC2626",
    "HUMAN RIGHTS": "#7C3AED",
    "LETELIER ASSASSINATION": "#0891B2",
    "COUP 1973": "#EA580C",
    "ECONOMIC INTERVENTION": "#16A34A",
    "ALLENDE GOVERNMENT": "#2563EB",
    "PINOCHET REGIME": "#4B5563",
    "DINA": "#BE185D",
    "40 COMMITTEE": "#7C2D12",
    "TRACK II": "#1E40AF",
    "CIA OPERATIONS": "#374151",
    "OTHER": "#9CA3AF",
}


def load_research_questions() -> list[dict]:
    """Load research questions from the JSON file."""
    questions_file = Path(__file__).parent.parent.parent / "data" / "research_questions.json"
    if not questions_file.exists():
        return []
    with open(questions_file, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("questions", [])


def generate_summary_cards(questions: list[dict]) -> str:
    """Generate summary cards HTML for research questions overview."""
    total = len(questions)
    if total == 0:
        return """
        <div class="summary-grid">
            <div class="summary-card">
                <h3>No Questions Yet</h3>
                <div class="value">0</div>
                <div class="subtext">Start asking research questions</div>
            </div>
        </div>
        """

    # Count by status
    status_counts: dict[str, int] = {}
    for q in questions:
        status = q.get("status", "unanswered")
        status_counts[status] = status_counts.get(status, 0) + 1

    answered = status_counts.get("answered", 0)
    in_progress = status_counts.get("partially_answered", 0) + status_counts.get("unanswered", 0)

    # Calculate average relevance for answered questions
    relevance_scores = [q.get("relevance_score", 0) for q in questions if q.get("relevance_score")]
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

    return f"""
    <div class="summary-grid">
        <div class="summary-card">
            <h3>Total Questions</h3>
            <div class="value">{total}</div>
            <div class="subtext">Research inquiries tracked</div>
        </div>
        <div class="summary-card">
            <h3>Answered</h3>
            <div class="value" style="color: #16A34A;">{answered}</div>
            <div class="subtext">{answered/total*100:.0f}% complete</div>
        </div>
        <div class="summary-card">
            <h3>In Progress</h3>
            <div class="value" style="color: #CA8A04;">{in_progress}</div>
            <div class="subtext">Awaiting analysis</div>
        </div>
        <div class="summary-card">
            <h3>Avg Relevance</h3>
            <div class="value">{avg_relevance:.1%}</div>
            <div class="subtext">RAG match score</div>
        </div>
    </div>
    """


def generate_category_chart(questions: list[dict]) -> str:
    """Generate a category distribution chart."""
    if not questions:
        return ""

    # Count by category
    cat_counts: dict[str, int] = {}
    for q in questions:
        cat = q.get("category", "OTHER")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    if not cat_counts:
        return ""

    # Sort by count descending
    sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)

    # Build bar chart HTML
    max_count = max(cat_counts.values())
    bars_html = ""
    for cat, count in sorted_cats:
        color = CATEGORY_COLORS.get(cat, "#9CA3AF")
        width_pct = (count / max_count) * 100
        bars_html += f"""
        <div class="category-bar-row">
            <div class="category-label">{cat}</div>
            <div class="category-bar-container">
                <div class="category-bar" style="width: {width_pct}%; background-color: {color};"></div>
                <span class="category-count">{count}</span>
            </div>
        </div>
        """

    return f"""
    <div class="category-chart">
        <h3>Questions by Category</h3>
        {bars_html}
    </div>
    """


def generate_question_card(
    question: dict,
    external_pdf_viewer: str | None = None,
) -> str:
    """Generate HTML card for a single research question."""
    q_id = question.get("id", "")
    q_text = question.get("question", "")
    category = question.get("category", "OTHER")
    status = question.get("status", "unanswered")
    date_asked = question.get("date_asked", "")
    relevance = question.get("relevance_score")
    rag_results = question.get("rag_results", "")
    related_docs = question.get("related_docs", [])
    html_report = question.get("html_report", "")
    pdf_report = question.get("pdf_report", "")

    # Status styling
    status_info = STATUS_CONFIG.get(status, STATUS_CONFIG["unanswered"])
    status_html = f"""
    <span class="status-badge" style="background-color: {status_info['color']}20; color: {status_info['color']}; border: 1px solid {status_info['color']}40;">
        {status_info['icon']} {status_info['label']}
    </span>
    """

    # Category badge
    cat_color = CATEGORY_COLORS.get(category, "#9CA3AF")
    category_html = f"""
    <span class="category-badge" style="background-color: {cat_color}20; color: {cat_color}; border: 1px solid {cat_color}40;">
        {category}
    </span>
    """

    # Relevance display
    relevance_html = ""
    if relevance is not None:
        relevance_pct = relevance * 100
        relevance_color = "#16A34A" if relevance_pct >= 40 else "#CA8A04" if relevance_pct >= 25 else "#DC2626"
        relevance_html = f"""
        <div class="relevance-score">
            <span class="relevance-label">Relevance:</span>
            <span class="relevance-value" style="color: {relevance_color};">{relevance_pct:.1f}%</span>
        </div>
        """

    # RAG results summary
    rag_html = ""
    if rag_results:
        rag_html = f"""
        <div class="rag-summary">
            <strong>Findings:</strong> {rag_results}
        </div>
        """

    # Related documents with links
    docs_html = ""
    if related_docs:
        doc_links = []
        for doc_id in related_docs[:5]:
            if external_pdf_viewer:
                link = f'<a href="{external_pdf_viewer}/?currentPage=1&documentId={doc_id}" target="_blank" class="pdf-link external">{doc_id}</a>'
            else:
                link = f'<span class="doc-id">{doc_id}</span>'
            doc_links.append(link)

        more = f" (+{len(related_docs) - 5} more)" if len(related_docs) > 5 else ""
        docs_html = f"""
        <div class="related-docs">
            <strong>Source Documents:</strong> {", ".join(doc_links)}{more}
        </div>
        """

    # Report link
    report_html = ""
    if html_report:
        report_html = f"""
        <a href="{html_report}" class="report-link">
            View Full Report →
        </a>
        """
    elif pdf_report and external_pdf_viewer:
        # Fall back to PDF if no HTML report
        report_html = f"""
        <a href="{pdf_report}" target="_blank" class="report-link external">
            View PDF Report ↗
        </a>
        """

    return f"""
    <div class="question-card" id="{q_id.lower()}">
        <div class="question-header">
            <span class="question-id">{q_id}</span>
            {status_html}
            {category_html}
        </div>
        <h3 class="question-text">{q_text}</h3>
        <div class="question-meta">
            <span class="date-asked">Asked: {date_asked}</span>
            {relevance_html}
        </div>
        {rag_html}
        {docs_html}
        {report_html}
    </div>
    """


def generate_questions_list(
    questions: list[dict],
    external_pdf_viewer: str | None = None,
) -> str:
    """Generate the full questions list HTML."""
    if not questions:
        return """
        <div class="empty-state">
            <p>No research questions have been tracked yet.</p>
            <p>Use <code>make rq-add Q="your question"</code> to add questions.</p>
        </div>
        """

    # Sort by date (newest first), then by ID
    sorted_questions = sorted(
        questions,
        key=lambda x: (x.get("date_asked", ""), x.get("id", "")),
        reverse=True,
    )

    cards_html = ""
    for q in sorted_questions:
        cards_html += generate_question_card(q, external_pdf_viewer)

    return f"""
    <div class="questions-list">
        {cards_html}
    </div>
    """


def generate_research_questions_css() -> str:
    """Generate CSS styles for research questions components."""
    return """
    /* Research Questions Styles */
    .category-chart {
        margin: 20px 0;
        padding: 15px;
        background: var(--gray-50);
        border-radius: 8px;
    }

    .category-chart h3 {
        margin: 0 0 15px 0;
        font-size: 14px;
        color: var(--gray-600);
    }

    .category-bar-row {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        gap: 10px;
    }

    .category-label {
        width: 180px;
        font-size: 12px;
        color: var(--gray-700);
        text-align: right;
        flex-shrink: 0;
    }

    .category-bar-container {
        flex-grow: 1;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .category-bar {
        height: 20px;
        border-radius: 4px;
        transition: width 0.3s ease;
    }

    .category-count {
        font-size: 12px;
        color: var(--gray-600);
        font-weight: 500;
    }

    .questions-list {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .question-card {
        background: white;
        border: 1px solid var(--gray-200);
        border-radius: 8px;
        padding: 20px;
        transition: box-shadow 0.2s ease;
    }

    .question-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    .question-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
        flex-wrap: wrap;
    }

    .question-id {
        font-family: monospace;
        font-size: 12px;
        color: var(--gray-500);
        background: var(--gray-100);
        padding: 2px 8px;
        border-radius: 4px;
    }

    .status-badge, .category-badge {
        font-size: 11px;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 500;
    }

    .question-text {
        font-size: 16px;
        color: var(--gray-900);
        margin: 0 0 12px 0;
        line-height: 1.4;
    }

    .question-meta {
        display: flex;
        align-items: center;
        gap: 20px;
        font-size: 13px;
        color: var(--gray-500);
        margin-bottom: 12px;
    }

    .relevance-score {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .relevance-value {
        font-weight: 600;
    }

    .rag-summary {
        background: var(--gray-50);
        padding: 12px;
        border-radius: 6px;
        font-size: 14px;
        color: var(--gray-700);
        margin-bottom: 12px;
        border-left: 3px solid var(--primary);
    }

    .related-docs {
        font-size: 13px;
        color: var(--gray-600);
        margin-bottom: 12px;
    }

    .doc-link {
        color: var(--primary);
        text-decoration: none;
        font-family: monospace;
    }

    .doc-link:hover {
        text-decoration: underline;
    }

    .doc-id {
        font-family: monospace;
        color: var(--gray-600);
    }

    .report-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        color: var(--primary);
        text-decoration: none;
        font-weight: 500;
        font-size: 14px;
    }

    .report-link:hover {
        text-decoration: underline;
    }

    .report-link.external::after {
        content: " ↗";
        font-size: 0.9em;
    }

    .empty-state {
        text-align: center;
        padding: 40px;
        color: var(--gray-500);
    }

    .empty-state code {
        background: var(--gray-100);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 13px;
    }
    """


def generate_research_questions_section(
    external_pdf_viewer: str | None = None,
) -> str:
    """
    Generate the complete research questions section for the main report.

    Args:
        external_pdf_viewer: Base URL for external document viewer

    Returns:
        HTML string for the research questions section
    """
    questions = load_research_questions()

    summary_html = generate_summary_cards(questions)
    category_html = generate_category_chart(questions)
    questions_html = generate_questions_list(questions, external_pdf_viewer)

    return f"""
    <section id="research-questions">
        <h2>Research Questions</h2>
        <p class="section-intro">
            Tracked research questions about the declassified documents, their analysis status,
            and links to evidence from the archive.
        </p>
        {summary_html}
        {category_html}
        <h3 style="margin-top: 30px;">All Questions</h3>
        {questions_html}
    </section>
    """


def generate_research_questions_nav_item() -> str:
    """Generate the navigation item for research questions."""
    return '<li><a href="#research-questions">Research Questions</a></li>'
