#!/usr/bin/env python3
"""
Analyze declassified CIA documents and generate an HTML report.

This module processes JSON transcript files and generates a comprehensive
HTML report with statistics, visualizations, and sensitive content analysis.
"""
import base64
import io
import os
import json
import glob
import argparse
import collections
from datetime import datetime
from typing import Any

from collections import Counter

from dateutil import parser as date_parser
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

from app.visualizations.interactive_timeline import (
    generate_interactive_timeline,
    generate_timeline_with_monthly_detail,
)
from app.visualizations.network_graph import (
    generate_people_network,
    generate_organization_network,
)
from app.visualizations.geographic_map import generate_geographic_map
from app.visualizations.sensitive_content import (
    generate_sensitive_timeline,
    generate_perpetrator_victim_network,
    generate_incident_types_chart,
    generate_sensitive_summary_cards,
)
from app.visualizations.keyword_cloud import generate_keyword_cloud
from app.visualizations.financial_dashboard import (
    generate_financial_summary_cards,
    generate_financial_timeline,
    generate_financial_flow_network,
    generate_financial_purposes_chart,
    generate_financial_actors_chart,
    generate_financial_category_cards,
)
from app.visualizations.pdf_viewer import (
    generate_pdf_viewer_modal,
    generate_pdf_link_interceptor,
    generate_external_viewer_modal,
    generate_external_link_interceptor,
)
from app.visualizations.research_questions import (
    generate_research_questions_section,
    generate_research_questions_css,
)
from app.visualizations.document_explorer import generate_explorer_html


# Financial categorization constants for separating covert ops from macro-economic data
COVERT_OPS_PURPOSES = {
    "ELECTION SUPPORT", "OPPOSITION SUPPORT", "PROPAGANDA",
    "MEDIA FUNDING", "INTELLIGENCE OPERATIONS", "POLITICAL ACTION"
}
COVERT_OPS_ACTORS = {"CIA", "40 COMMITTEE", "NSC", "STATE DEPARTMENT"}
MACRO_THRESHOLD = 100_000_000  # $100M - amounts above this without covert markers are macro


def image_to_base64(image_path: str) -> str:
    """Convert an image file to a base64 data URI."""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"


def process_documents(
    directory: str,
    full_mode: bool = False,
    pdf_dir: str | None = None
) -> dict[str, Any]:
    """
    Process all JSON transcript files in the given directory.

    Skips non-transcript files (failed_*, incomplete_*, processing_*).

    Args:
        directory: Directory containing JSON transcript files
        full_mode: If True, collect document-level data for detailed linking
        pdf_dir: Directory containing source PDFs (used in full_mode)

    Returns a dictionary with aggregated statistics.
    """
    all_files = glob.glob(os.path.join(directory, "*.json"))
    # Skip non-transcript files
    skip_prefixes = ('failed_', 'incomplete_', 'processing_')
    files = [f for f in all_files if not os.path.basename(f).startswith(skip_prefixes)]

    # Counters for basic metadata
    timeline_daily = collections.Counter()
    timeline_monthly = collections.Counter()
    timeline_yearly = collections.Counter()
    people_count = collections.Counter()
    keywords_count = collections.Counter()
    recipients_count = collections.Counter()
    doc_type_count = collections.Counter()
    classification_count = collections.Counter()
    language_count = collections.Counter()

    # Location counters (new granular fields)
    country_count = collections.Counter()
    city_count = collections.Counter()
    other_place_count = collections.Counter()

    # Organization counters
    org_count = collections.Counter()
    org_type_count = collections.Counter()
    org_country_count = collections.Counter()

    # Financial references
    financial_purposes_count = collections.Counter()
    financial_actors_count = collections.Counter()
    financial_amounts: list[dict] = []
    docs_with_financial = 0

    # Categorized financial data for separating covert ops from macro-economic
    financial_amounts_by_year: dict[str, list[dict]] = collections.defaultdict(list)
    covert_ops_amounts: list[dict] = []
    macro_economic_amounts: list[dict] = []

    # Sensitive content counters
    violence_incident_types = collections.Counter()
    violence_victims = collections.Counter()
    violence_perpetrators = collections.Counter()
    docs_with_violence = 0

    torture_detention_centers = collections.Counter()
    torture_methods = collections.Counter()
    torture_victims = collections.Counter()
    torture_perpetrators = collections.Counter()
    docs_with_torture = 0

    disappearance_victims = collections.Counter()
    disappearance_perpetrators = collections.Counter()
    disappearance_locations = collections.Counter()
    docs_with_disappearance = 0

    # Confidence tracking
    confidence_scores: list[float] = []
    confidence_concerns = collections.Counter()

    # Classification by year for stacked timeline chart
    classification_by_year: dict[str, Counter] = collections.defaultdict(collections.Counter)

    # Sensitive content by year for timeline visualization
    sensitive_content_by_year: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"violence": 0, "torture": 0, "disappearance": 0}
    )

    total_docs = 0
    total_pages = 0

    # Full mode: track which documents contain each entity
    # Maps entity -> list of (doc_id, pdf_path)
    if full_mode:
        people_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        keyword_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        org_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        violence_victim_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        violence_perp_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        torture_victim_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        torture_perp_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        torture_center_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        disappearance_victim_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        disappearance_perp_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        financial_purpose_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        financial_actor_docs: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
        all_documents: list[dict[str, Any]] = []

    for file in files:
        try:
            with open(file, 'r', encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue

        # Skip if not a dict (some tracking files might be arrays)
        if not isinstance(data, dict):
            continue

        total_docs += 1
        metadata = data.get("metadata", {})

        # Full mode: compute document ID and PDF path
        if full_mode:
            doc_basename = os.path.splitext(os.path.basename(file))[0]
            doc_id = metadata.get("document_id", doc_basename) or doc_basename
            if pdf_dir:
                pdf_path = os.path.join(pdf_dir, f"{doc_basename}.pdf")
            else:
                pdf_path = ""
            doc_ref = (doc_id, pdf_path, doc_basename)

        # Page count
        page_count = metadata.get("page_count", 0)
        if isinstance(page_count, int):
            total_pages += page_count

        # Process document date
        doc_date_str = metadata.get("document_date", "")
        doc_year = "Unknown"  # Track year for classification_by_year
        if doc_date_str:
            timeline_daily[doc_date_str] += 1
            # Extract year and month for aggregated views
            try:
                if doc_date_str.startswith("0000"):
                    year = "Unknown"
                    month = "Unknown"
                else:
                    parts = doc_date_str.split("-")
                    year = parts[0] if parts[0] != "0000" else "Unknown"
                    month = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 and parts[1] != "00" else "Unknown"
                doc_year = year
                timeline_yearly[year] += 1
                if month != "Unknown":
                    timeline_monthly[month] += 1
            except Exception:
                timeline_yearly["Unknown"] += 1
        else:
            timeline_yearly["Unknown"] += 1

        # Classification level
        classification = metadata.get("classification_level", "Unknown") or "Unknown"
        classification_count[classification] += 1
        classification_by_year[doc_year][classification] += 1

        # Language
        language = metadata.get("language", "Unknown") or "Unknown"
        language_count[language] += 1

        # Document type
        doc_type = metadata.get("document_type", "Unknown") or "Unknown"
        doc_type_count[doc_type] += 1

        # People mentioned
        for person in metadata.get("people_mentioned", []):
            if person:
                people_count[person] += 1
                if full_mode:
                    people_docs[person].append(doc_ref)

        # Recipients
        for recipient in metadata.get("recipients", []):
            if recipient:
                recipients_count[recipient] += 1

        # Keywords
        for keyword in metadata.get("keywords", []):
            if keyword:
                keywords_count[keyword] += 1
                if full_mode:
                    keyword_docs[keyword].append(doc_ref)

        # Locations (new granular fields)
        for country in metadata.get("country", []):
            if country:
                country_count[country] += 1
        for city in metadata.get("city", []):
            if city:
                city_count[city] += 1
        for place in metadata.get("other_place", []):
            if place:
                other_place_count[place] += 1

        # Organizations
        for org in metadata.get("organizations_mentioned", []):
            if isinstance(org, dict):
                name = org.get("name", "")
                org_type = org.get("type", "")
                org_country = org.get("country", "")
                if name:
                    org_count[name] += 1
                    if full_mode:
                        org_docs[name].append(doc_ref)
                if org_type:
                    org_type_count[org_type] += 1
                if org_country:
                    org_country_count[org_country] += 1

        # Financial references with categorization
        fin_refs = metadata.get("financial_references", {})
        if isinstance(fin_refs, dict) and fin_refs.get("has_financial_content"):
            docs_with_financial += 1
            doc_purposes = set(fin_refs.get("purposes", []))
            doc_actors = set(fin_refs.get("financial_actors", []))

            for purpose in doc_purposes:
                if purpose:
                    financial_purposes_count[purpose] += 1
                    if full_mode:
                        financial_purpose_docs[purpose].append(doc_ref)
            for actor in doc_actors:
                if actor:
                    financial_actors_count[actor] += 1
                    if full_mode:
                        financial_actor_docs[actor].append(doc_ref)

            # Get document ID for enrichment
            file_doc_id = os.path.splitext(os.path.basename(file))[0]

            for amount in fin_refs.get("amounts", []):
                if isinstance(amount, dict):
                    # Enrich amount with document context
                    enriched = {
                        **amount,
                        "doc_id": file_doc_id,
                        "doc_year": doc_year,
                    }
                    financial_amounts.append(enriched)

                    # Add to timeline by year
                    if doc_year != "Unknown":
                        financial_amounts_by_year[doc_year].append(enriched)

                    # Categorize: Covert Ops vs Macro-Economic
                    is_covert = (
                        bool(doc_purposes & COVERT_OPS_PURPOSES) or
                        bool(doc_actors & COVERT_OPS_ACTORS)
                    )
                    normalized = amount.get("normalized_usd")

                    if normalized and normalized > MACRO_THRESHOLD and not is_covert:
                        macro_economic_amounts.append(enriched)
                    elif is_covert or (normalized and normalized < MACRO_THRESHOLD):
                        covert_ops_amounts.append(enriched)
                    else:
                        macro_economic_amounts.append(enriched)

        # Violence references
        vio_refs = metadata.get("violence_references", {})
        if isinstance(vio_refs, dict) and vio_refs.get("has_violence_content"):
            docs_with_violence += 1
            sensitive_content_by_year[doc_year]["violence"] += 1
            for incident in vio_refs.get("incident_types", []):
                if incident:
                    violence_incident_types[incident] += 1
            for victim in vio_refs.get("victims", []):
                if victim:
                    violence_victims[victim] += 1
                    if full_mode:
                        violence_victim_docs[victim].append(doc_ref)
            for perp in vio_refs.get("perpetrators", []):
                if perp:
                    violence_perpetrators[perp] += 1
                    if full_mode:
                        violence_perp_docs[perp].append(doc_ref)

        # Torture references
        tor_refs = metadata.get("torture_references", {})
        if isinstance(tor_refs, dict) and tor_refs.get("has_torture_content"):
            docs_with_torture += 1
            sensitive_content_by_year[doc_year]["torture"] += 1
            for center in tor_refs.get("detention_centers", []):
                if center:
                    torture_detention_centers[center] += 1
                    if full_mode:
                        torture_center_docs[center].append(doc_ref)
            for method in tor_refs.get("methods_mentioned", []):
                if method:
                    torture_methods[method] += 1
            for victim in tor_refs.get("victims", []):
                if victim:
                    torture_victims[victim] += 1
                    if full_mode:
                        torture_victim_docs[victim].append(doc_ref)
            for perp in tor_refs.get("perpetrators", []):
                if perp:
                    torture_perpetrators[perp] += 1
                    if full_mode:
                        torture_perp_docs[perp].append(doc_ref)

        # Disappearance references
        dis_refs = metadata.get("disappearance_references", {})
        if isinstance(dis_refs, dict) and dis_refs.get("has_disappearance_content"):
            docs_with_disappearance += 1
            sensitive_content_by_year[doc_year]["disappearance"] += 1
            for victim in dis_refs.get("victims", []):
                if victim:
                    disappearance_victims[victim] += 1
                    if full_mode:
                        disappearance_victim_docs[victim].append(doc_ref)
            for perp in dis_refs.get("perpetrators", []):
                if perp:
                    disappearance_perpetrators[perp] += 1
                    if full_mode:
                        disappearance_perp_docs[perp].append(doc_ref)
            for loc in dis_refs.get("locations", []):
                if loc:
                    disappearance_locations[loc] += 1

        # Confidence
        confidence = data.get("confidence", {})
        if isinstance(confidence, dict):
            overall = confidence.get("overall")
            if isinstance(overall, (int, float)):
                confidence_scores.append(float(overall))
            for concern in confidence.get("concerns", []):
                if concern:
                    confidence_concerns[concern] += 1

        # Full mode: collect document info for the document index
        if full_mode:
            all_documents.append({
                "basename": doc_basename,
                "doc_id": doc_id,
                "pdf_path": pdf_path,
                "date": metadata.get("document_date", ""),
                "classification": classification,
                "doc_type": doc_type,
                "title": metadata.get("document_title", ""),
                "summary": metadata.get("document_summary", ""),
                "page_count": page_count if isinstance(page_count, int) else 0,
                # Include entity data for network visualization
                "people": metadata.get("people_mentioned", []),
                "organizations": metadata.get("organizations_mentioned", []),
            })

    return {
        "total_docs": total_docs,
        "total_pages": total_pages,
        "files_skipped": len(all_files) - len(files),
        "timeline_daily": timeline_daily,
        "timeline_monthly": timeline_monthly,
        "timeline_yearly": timeline_yearly,
        "people_count": people_count,
        "keywords_count": keywords_count,
        "recipients_count": recipients_count,
        "doc_type_count": doc_type_count,
        "classification_count": classification_count,
        "classification_by_year": dict(classification_by_year),
        "sensitive_content_by_year": dict(sensitive_content_by_year),
        "language_count": language_count,
        "country_count": country_count,
        "city_count": city_count,
        "other_place_count": other_place_count,
        "org_count": org_count,
        "org_type_count": org_type_count,
        "org_country_count": org_country_count,
        "financial_purposes_count": financial_purposes_count,
        "financial_actors_count": financial_actors_count,
        "financial_amounts": financial_amounts,
        "docs_with_financial": docs_with_financial,
        "financial_amounts_by_year": dict(financial_amounts_by_year),
        "covert_ops_amounts": covert_ops_amounts,
        "macro_economic_amounts": macro_economic_amounts,
        "violence_incident_types": violence_incident_types,
        "violence_victims": violence_victims,
        "violence_perpetrators": violence_perpetrators,
        "docs_with_violence": docs_with_violence,
        "torture_detention_centers": torture_detention_centers,
        "torture_methods": torture_methods,
        "torture_victims": torture_victims,
        "torture_perpetrators": torture_perpetrators,
        "docs_with_torture": docs_with_torture,
        "disappearance_victims": disappearance_victims,
        "disappearance_perpetrators": disappearance_perpetrators,
        "disappearance_locations": disappearance_locations,
        "docs_with_disappearance": docs_with_disappearance,
        "confidence_scores": confidence_scores,
        "confidence_concerns": confidence_concerns,
        # Full mode data (empty if not in full mode)
        "full_mode": full_mode,
        "all_documents": all_documents if full_mode else [],
        "people_docs": dict(people_docs) if full_mode else {},
        "keyword_docs": dict(keyword_docs) if full_mode else {},
        "org_docs": dict(org_docs) if full_mode else {},
        "violence_victim_docs": dict(violence_victim_docs) if full_mode else {},
        "violence_perp_docs": dict(violence_perp_docs) if full_mode else {},
        "torture_victim_docs": dict(torture_victim_docs) if full_mode else {},
        "torture_perp_docs": dict(torture_perp_docs) if full_mode else {},
        "torture_center_docs": dict(torture_center_docs) if full_mode else {},
        "disappearance_victim_docs": dict(disappearance_victim_docs) if full_mode else {},
        "disappearance_perp_docs": dict(disappearance_perp_docs) if full_mode else {},
        "financial_purpose_docs": dict(financial_purpose_docs) if full_mode else {},
        "financial_actor_docs": dict(financial_actor_docs) if full_mode else {},
    }


def plot_timeline(timeline: dict, output_image: str = 'timeline.png', title: str = "Documents per Year") -> bool:
    """Create and save a bar chart for the timeline. Returns True if plot was created."""
    if not timeline:
        return False

    # Sort by key (year/month)
    sorted_items = sorted(
        [(k, v) for k, v in timeline.items() if k != "Unknown"],
        key=lambda x: x[0]
    )

    if not sorted_items:
        return False

    labels, counts = zip(*sorted_items)

    plt.figure(figsize=(12, 6))
    plt.bar(labels, counts, color='#2563eb')
    plt.xlabel("Date")
    plt.ylabel("Number of Documents")
    plt.title(title)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_image, dpi=100)
    plt.close()
    return True


def plot_pie_chart(counter: dict, output_image: str, title: str, max_items: int = 8) -> bool:
    """Create and save a pie chart. Returns True if plot was created."""
    if not counter:
        return False

    # Get top items, group rest as "Other"
    sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)

    if len(sorted_items) > max_items:
        top_items = sorted_items[:max_items-1]
        other_count = sum(v for _, v in sorted_items[max_items-1:])
        top_items.append(("Other", other_count))
    else:
        top_items = sorted_items

    labels, sizes = zip(*top_items)

    plt.figure(figsize=(10, 8))
    colors = plt.cm.Set3(range(len(labels)))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_image, dpi=100)
    plt.close()
    return True


def plot_confidence_histogram(scores: list[float], output_image: str) -> bool:
    """Create a histogram of confidence scores."""
    if not scores:
        return False

    plt.figure(figsize=(10, 6))
    plt.hist(scores, bins=20, range=(0, 1), color='#2563eb', edgecolor='white')
    plt.xlabel("Confidence Score")
    plt.ylabel("Number of Documents")
    plt.title("Distribution of Confidence Scores")
    plt.axvline(x=sum(scores)/len(scores), color='red', linestyle='--', label=f'Mean: {sum(scores)/len(scores):.2f}')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_image, dpi=100)
    plt.close()
    return True


def generate_html_report(
    results: dict,
    output_dir: str,
    output_file: str = "report.html",
    standalone: bool = True
):
    """Generate a comprehensive HTML report with all statistics and visualizations.

    Args:
        results: Dictionary with aggregated statistics from process_documents()
        output_dir: Directory to save the report
        output_file: Name of the HTML file
        standalone: If True (default), embed images as base64 for a self-contained file.
                   If False, save images as separate PNG files.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Generate plots
    timeline_path = os.path.join(output_dir, "timeline_yearly.png")
    classification_path = os.path.join(output_dir, "classification.png")
    doc_types_path = os.path.join(output_dir, "doc_types.png")
    confidence_path = os.path.join(output_dir, "confidence.png")

    timeline_exists = plot_timeline(
        results["timeline_yearly"],
        timeline_path,
        "Documents per Year"
    )
    classification_exists = plot_pie_chart(
        results["classification_count"],
        classification_path,
        "Classification Levels"
    )
    doc_type_exists = plot_pie_chart(
        results["doc_type_count"],
        doc_types_path,
        "Document Types"
    )
    confidence_exists = plot_confidence_histogram(
        results["confidence_scores"],
        confidence_path
    )

    # Convert images to base64 if standalone mode
    if standalone:
        timeline_src = image_to_base64(timeline_path) if timeline_exists else ""
        classification_src = image_to_base64(classification_path) if classification_exists else ""
        doc_types_src = image_to_base64(doc_types_path) if doc_type_exists else ""
        confidence_src = image_to_base64(confidence_path) if confidence_exists else ""
        # Clean up PNG files after embedding
        for path in [timeline_path, classification_path, doc_types_path, confidence_path]:
            if os.path.exists(path):
                os.remove(path)
    else:
        timeline_src = "timeline_yearly.png"
        classification_src = "classification.png"
        doc_types_src = "doc_types.png"
        confidence_src = "confidence.png"

    def create_table(counter: dict, limit: int = 50, id_prefix: str = "", show_all: bool = True) -> str:
        """Create an HTML table from a Counter, with optional collapsible rows.

        Args:
            counter: Dict of item -> count
            limit: Number of items to show initially
            id_prefix: Unique prefix for table IDs
            show_all: If False, never show "Show all X items" button (prevents DOM bloat)
        """
        if not counter:
            return "<p><em>No data available</em></p>"

        sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        total_items = len(sorted_items)

        # When show_all is False, only include visible rows (no hidden section)
        if not show_all:
            sorted_items = sorted_items[:limit]

        rows_visible = []
        rows_hidden = []

        for i, (k, v) in enumerate(sorted_items):
            row = f"<tr><td>{k}</td><td>{v:,}</td></tr>"
            if i < limit:
                rows_visible.append(row)
            else:
                rows_hidden.append(row)

        table_id = id_prefix or f"table_{hash(str(counter))}"

        html = f"""
        <table class="data-table">
            <thead><tr><th>Item</th><th>Count</th></tr></thead>
            <tbody id="{table_id}_visible">{''.join(rows_visible)}</tbody>
        """

        if rows_hidden and show_all:
            html += f"""
            <tbody id="{table_id}_hidden" class="hidden">{''.join(rows_hidden)}</tbody>
            </table>
            <button class="show-more-btn" onclick="toggleRows('{table_id}')">
                Show all {total_items:,} items ({total_items - limit:,} more)
            </button>
            """
        else:
            html += "</table>"
            # Show count of hidden items when show_all is False
            if total_items > limit and not show_all:
                html += f"<p class='table-note'><em>Showing top {limit} of {total_items:,} items</em></p>"

        return html

    def create_financial_summary_section(results: dict) -> str:
        """Create a compact financial summary section with two cards."""

        def get_top_items(counter: dict, n: int = 5) -> list:
            """Get top N items from a counter."""
            if not counter:
                return []
            return sorted(counter.items(), key=lambda x: x[1], reverse=True)[:n]

        def format_item_list(items: list) -> str:
            """Format items as a compact list."""
            if not items:
                return "<p class='no-data'>No data</p>"
            html = "<ul class='entity-top-list'>"
            for name, count in items:
                # Truncate long names
                display_name = name[:35] + "..." if len(name) > 35 else name
                html += f"<li><span class='entity-name' title='{name}'>{display_name}</span> <span class='entity-count'>({count:,})</span></li>"
            html += "</ul>"
            return html

        # Get counts
        purposes = results.get('financial_purposes_count', {})
        actors = results.get('financial_actors_count', {})
        purposes_total = len(purposes)
        purposes_mentions = sum(purposes.values())
        actors_total = len(actors)
        actors_mentions = sum(actors.values())

        # Get top items
        top_purposes = get_top_items(purposes, 5)
        top_actors = get_top_items(actors, 5)

        return f"""
        <div class="financial-cards">
            <div class="financial-card">
                <div class="entity-card-header">
                    <span class="entity-icon">💰</span>
                    <h3>Funding Purposes</h3>
                </div>
                <div class="entity-stats">
                    <span class="stat-number">{purposes_total:,}</span>
                    <span class="stat-label">purpose categories</span>
                </div>
                <div class="entity-mentions">{purposes_mentions:,} total references</div>
                <h4>Most Common</h4>
                {format_item_list(top_purposes)}
            </div>

            <div class="financial-card">
                <div class="entity-card-header">
                    <span class="entity-icon">🏛️</span>
                    <h3>Financial Actors</h3>
                </div>
                <div class="entity-stats">
                    <span class="stat-number">{actors_total:,}</span>
                    <span class="stat-label">entities mentioned</span>
                </div>
                <div class="entity-mentions">{actors_mentions:,} total mentions</div>
                <h4>Top Actors</h4>
                {format_item_list(top_actors)}
                <a href="entities/?type=organization" class="entity-card-link">View in Entity Explorer →</a>
            </div>
        </div>
        """

    def format_number(n: int) -> str:
        return f"{n:,}"

    def pct(part: int, total: int) -> str:
        if total == 0:
            return "0%"
        return f"{part/total*100:.1f}%"

    # Calculate summary stats
    total = results["total_docs"]
    avg_confidence = sum(results["confidence_scores"]) / len(results["confidence_scores"]) if results["confidence_scores"] else 0

    # Build HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Declassified Documents Analysis Report</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --danger: #dc2626;
            --warning: #f59e0b;
            --success: #10b981;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-600: #4b5563;
            --gray-800: #1f2937;
        }}

        * {{ box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: var(--gray-100);
            color: var(--gray-800);
            line-height: 1.6;
        }}

        .container {{
            display: flex;
            min-height: 100vh;
        }}

        nav {{
            width: 250px;
            background: var(--gray-800);
            color: white;
            padding: 20px;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
        }}

        nav h2 {{
            margin-top: 0;
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--gray-200);
        }}

        nav ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}

        nav li {{
            margin: 8px 0;
        }}

        nav a {{
            color: var(--gray-200);
            text-decoration: none;
            font-size: 0.9rem;
            display: block;
            padding: 6px 10px;
            border-radius: 4px;
            transition: background 0.2s;
        }}

        nav a:hover {{
            background: rgba(255,255,255,0.1);
        }}

        nav .nav-section {{
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}

        nav .nav-section-title {{
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--gray-600);
            margin-bottom: 8px;
        }}

        main {{
            flex: 1;
            margin-left: 250px;
            padding: 30px 40px;
            max-width: 1200px;
        }}

        h1 {{
            color: var(--gray-800);
            border-bottom: 3px solid var(--primary);
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}

        h2 {{
            color: var(--gray-800);
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--gray-200);
        }}

        h3 {{
            color: var(--gray-600);
            margin-top: 25px;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .summary-card.danger {{
            border-left: 4px solid var(--danger);
        }}

        .summary-card.warning {{
            border-left: 4px solid var(--warning);
        }}

        .summary-card h3 {{
            margin: 0 0 5px 0;
            font-size: 0.85rem;
            text-transform: uppercase;
            color: var(--gray-600);
        }}

        .summary-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--gray-800);
        }}

        .summary-card .subtext {{
            font-size: 0.85rem;
            color: var(--gray-600);
        }}

        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}

        .chart-container img {{
            max-width: 100%;
            height: auto;
        }}

        .data-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin: 15px 0;
        }}

        .data-table th {{
            background: var(--gray-800);
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
        }}

        .data-table td {{
            padding: 10px 15px;
            border-bottom: 1px solid var(--gray-200);
        }}

        .data-table tr:hover {{
            background: var(--gray-100);
        }}

        .hidden {{
            display: none;
        }}

        .show-more-btn {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            margin-top: 10px;
        }}

        .show-more-btn:hover {{
            background: var(--primary-dark);
        }}

        .table-note {{
            color: var(--gray-600);
            font-size: 0.85rem;
            margin-top: 8px;
        }}

        /* Financial summary cards */
        .financial-cards {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}

        .financial-card {{
            background: white;
            border: 1px solid var(--gray-200);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .entity-card-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }}

        .entity-icon {{
            font-size: 1.5rem;
        }}

        .entity-card-header h3 {{
            margin: 0;
            font-size: 1.1rem;
            color: var(--gray-800);
        }}

        .entity-stats {{
            text-align: center;
            padding: 15px 0;
            background: var(--gray-100);
            border-radius: 8px;
            margin-bottom: 10px;
        }}

        .entity-stats .stat-number {{
            display: block;
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary);
        }}

        .entity-stats .stat-label {{
            font-size: 0.85rem;
            color: var(--gray-600);
        }}

        .entity-mentions {{
            text-align: center;
            font-size: 0.85rem;
            color: var(--gray-600);
            margin-bottom: 15px;
        }}

        .financial-card h4 {{
            font-size: 0.9rem;
            color: var(--gray-600);
            margin: 15px 0 10px 0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .entity-top-list {{
            list-style: none;
            padding: 0;
            margin: 0 0 15px 0;
        }}

        .entity-top-list li {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid var(--gray-100);
            font-size: 0.9rem;
        }}

        .entity-top-list li:last-child {{
            border-bottom: none;
        }}

        .entity-count {{
            color: var(--gray-600);
            font-weight: 500;
        }}

        .entity-card-link {{
            display: block;
            text-align: center;
            padding: 10px;
            background: var(--gray-100);
            border-radius: 6px;
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
            transition: background 0.2s;
        }}

        .entity-card-link:hover {{
            background: var(--gray-200);
        }}

        @media (max-width: 768px) {{
            .financial-cards {{
                grid-template-columns: 1fr;
            }}
        }}

        .sensitive-warning {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 15px 20px;
            margin: 20px 0;
        }}

        .sensitive-warning h4 {{
            color: var(--danger);
            margin: 0 0 10px 0;
        }}

        .two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        @media (max-width: 900px) {{
            nav {{
                display: none;
            }}
            main {{
                margin-left: 0;
            }}
            .two-col {{
                grid-template-columns: 1fr;
            }}
        }}

        .meta-info {{
            background: var(--gray-200);
            padding: 10px 15px;
            border-radius: 4px;
            font-size: 0.85rem;
            color: var(--gray-600);
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <h2>Navigation</h2>
            <ul>
                <li><a href="#overview">Overview</a></li>
                <li><a href="#timeline">Timeline</a></li>
                <li><a href="#classification">Classification</a></li>
                <li><a href="#document-types">Document Types</a></li>
            </ul>

            <div class="nav-section">
                <div class="nav-section-title">Entities</div>
                <ul>
                    <li><a href="#entity-summary">Entity Summary</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Sensitive Content</div>
                <ul>
                    <li><a href="#violence">Violence References</a></li>
                    <li><a href="#torture">Torture References</a></li>
                    <li><a href="#disappearances">Disappearances</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Other</div>
                <ul>
                    <li><a href="#financial">Financial References</a></li>
                    <li><a href="#confidence">Confidence Scores</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Project</div>
                <ul>
                    <li><a href="about.html">About</a></li>
                </ul>
            </div>
        </nav>

        <main>
            <h1>Declassified CIA Documents Analysis Report</h1>

            <div class="meta-info">
                Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} |
                Source: {output_dir}
            </div>

            <section id="overview">
                <h2>Overview</h2>
                <div class="summary-grid">
                    <div class="summary-card">
                        <h3>Total Documents</h3>
                        <div class="value">{format_number(total)}</div>
                        <div class="subtext">{format_number(results['total_pages'])} total pages</div>
                    </div>
                    <div class="summary-card">
                        <h3>Avg Confidence</h3>
                        <div class="value">{avg_confidence:.1%}</div>
                        <div class="subtext">{format_number(len(results['confidence_scores']))} scored</div>
                    </div>
                    <div class="summary-card danger">
                        <h3>Violence Content</h3>
                        <div class="value">{format_number(results['docs_with_violence'])}</div>
                        <div class="subtext">{pct(results['docs_with_violence'], total)} of documents</div>
                    </div>
                    <div class="summary-card danger">
                        <h3>Torture Content</h3>
                        <div class="value">{format_number(results['docs_with_torture'])}</div>
                        <div class="subtext">{pct(results['docs_with_torture'], total)} of documents</div>
                    </div>
                    <div class="summary-card danger">
                        <h3>Disappearances</h3>
                        <div class="value">{format_number(results['docs_with_disappearance'])}</div>
                        <div class="subtext">{pct(results['docs_with_disappearance'], total)} of documents</div>
                    </div>
                    <div class="summary-card warning">
                        <h3>Financial Content</h3>
                        <div class="value">{format_number(results['docs_with_financial'])}</div>
                        <div class="subtext">{pct(results['docs_with_financial'], total)} of documents</div>
                    </div>
                </div>
            </section>

            <section id="timeline">
                <h2>Timeline</h2>
                {f"<div class='chart-container'><img src='{timeline_src}' alt='Timeline'></div>" if timeline_exists else "<p><em>No valid dates for timeline</em></p>"}

                <h3>Documents by Year</h3>
                {create_table(results['timeline_yearly'], limit=50, id_prefix='timeline_yearly')}
            </section>

            <section id="classification">
                <h2>Classification Levels</h2>
                <div class="two-col">
                    {f"<div class='chart-container'><img src='{classification_src}' alt='Classification'></div>" if classification_exists else ""}
                    <div>
                        {create_table(results['classification_count'], limit=10, id_prefix='classification')}
                    </div>
                </div>
            </section>

            <section id="document-types">
                <h2>Document Types</h2>
                <div class="two-col">
                    {f"<div class='chart-container'><img src='{doc_types_src}' alt='Document Types'></div>" if doc_type_exists else ""}
                    <div>
                        {create_table(results['doc_type_count'], limit=10, id_prefix='doc_types')}
                    </div>
                </div>

                <h3>Languages</h3>
                {create_table(results['language_count'], limit=10, id_prefix='languages')}
            </section>

            <section id="entity-summary">
                <h2>Entity Summary</h2>
                <p>Top entities extracted from documents. For full entity browsing, use the GitHub Pages version with the Entity Explorer.</p>

                <div class="two-col">
                    <div>
                        <h3>Top People ({len(results['people_count']):,} total)</h3>
                        {create_table(results['people_count'], limit=15, id_prefix='people')}
                    </div>
                    <div>
                        <h3>Top Organizations ({len(results['org_count']):,} total)</h3>
                        {create_table(results['org_count'], limit=15, id_prefix='orgs')}
                    </div>
                </div>

                <div class="two-col">
                    <div>
                        <h3>Top Keywords ({len(results['keywords_count']):,} total)</h3>
                        {create_table(results['keywords_count'], limit=15, id_prefix='keywords')}
                    </div>
                    <div>
                        <h3>Top Countries ({len(results['country_count']):,} total)</h3>
                        {create_table(results['country_count'], limit=15, id_prefix='countries')}
                    </div>
                </div>
            </section>

            <section id="violence">
                <h2>Violence References</h2>

                <div class="sensitive-warning">
                    <h4>Content Warning</h4>
                    <p>This section contains references to violence, executions, and other sensitive historical events documented in declassified materials.</p>
                </div>

                <p><strong>{format_number(results['docs_with_violence'])} documents</strong> ({pct(results['docs_with_violence'], total)}) contain violence-related content.</p>

                <h3>Incident Types</h3>
                {create_table(results['violence_incident_types'], limit=20, id_prefix='violence_types')}

                <div class="two-col">
                    <div>
                        <h3>Victims</h3>
                        {create_table(results['violence_victims'], limit=30, id_prefix='violence_victims')}
                    </div>
                    <div>
                        <h3>Perpetrators</h3>
                        {create_table(results['violence_perpetrators'], limit=30, id_prefix='violence_perps')}
                    </div>
                </div>
            </section>

            <section id="torture">
                <h2>Torture References</h2>

                <div class="sensitive-warning">
                    <h4>Content Warning</h4>
                    <p>This section contains references to torture, detention centers, and interrogation practices documented in declassified materials.</p>
                </div>

                <p><strong>{format_number(results['docs_with_torture'])} documents</strong> ({pct(results['docs_with_torture'], total)}) contain torture-related content.</p>

                <h3>Detention Centers</h3>
                {create_table(results['torture_detention_centers'], limit=20, id_prefix='detention_centers')}

                <h3>Methods Mentioned</h3>
                {create_table(results['torture_methods'], limit=20, id_prefix='torture_methods')}

                <div class="two-col">
                    <div>
                        <h3>Victims</h3>
                        {create_table(results['torture_victims'], limit=30, id_prefix='torture_victims')}
                    </div>
                    <div>
                        <h3>Perpetrators</h3>
                        {create_table(results['torture_perpetrators'], limit=30, id_prefix='torture_perps')}
                    </div>
                </div>
            </section>

            <section id="disappearances">
                <h2>Disappearance References</h2>

                <div class="sensitive-warning">
                    <h4>Content Warning</h4>
                    <p>This section contains references to forced disappearances (desaparecidos) documented in declassified materials.</p>
                </div>

                <p><strong>{format_number(results['docs_with_disappearance'])} documents</strong> ({pct(results['docs_with_disappearance'], total)}) contain disappearance-related content.</p>

                <div class="two-col">
                    <div>
                        <h3>Victims</h3>
                        {create_table(results['disappearance_victims'], limit=30, id_prefix='disapp_victims')}
                    </div>
                    <div>
                        <h3>Perpetrators</h3>
                        {create_table(results['disappearance_perpetrators'], limit=30, id_prefix='disapp_perps')}
                    </div>
                </div>

                <h3>Locations</h3>
                {create_table(results['disappearance_locations'], limit=30, id_prefix='disapp_locations')}
            </section>

            <section id="financial">
                <h2>Financial References</h2>

                <p><strong>{format_number(results['docs_with_financial'])} documents</strong> ({pct(results['docs_with_financial'], total)}) contain financial references.</p>

                {create_financial_summary_section(results)}
            </section>

            <section id="confidence">
                <h2>Confidence Scores</h2>

                {f"<div class='chart-container'><img src='{confidence_src}' alt='Confidence Distribution'></div>" if confidence_exists else "<p><em>No confidence data available</em></p>"}

                <h3>Common Concerns</h3>
                <p>Issues flagged during transcription that may require human review.</p>
                {create_table(results['confidence_concerns'], limit=10, id_prefix='concerns', show_all=False)}
            </section>

            <footer style="margin-top: 50px; padding: 20px 0; border-top: 1px solid var(--gray-200); color: var(--gray-600); font-size: 0.85rem;">
                <p>This report analyzes declassified CIA documents related to the Chilean dictatorship (1973-1990).</p>
                <p>Data extracted from structured JSON transcripts using vision-based transcription.</p>
            </footer>
        </main>
    </div>

    <script>
        function toggleRows(tableId) {{
            const hidden = document.getElementById(tableId + '_hidden');
            const btn = event.target;
            if (hidden.classList.contains('hidden')) {{
                hidden.classList.remove('hidden');
                btn.textContent = 'Show less';
            }} else {{
                hidden.classList.add('hidden');
                btn.textContent = btn.getAttribute('data-original') || 'Show more';
            }}
        }}

        // Store original button text
        document.querySelectorAll('.show-more-btn').forEach(btn => {{
            btn.setAttribute('data-original', btn.textContent);
        }});
    </script>
</body>
</html>
"""

    output_path = os.path.join(output_dir, output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Report saved to {output_path}")


def generate_full_html_report(
    results: dict,
    output_dir: str,
    output_file: str = "report_full.html",
    standalone: bool = True,
    serve_mode: bool = False,
    github_pages_mode: bool = False,
    external_pdf_viewer: str | None = None,
):
    """Generate a full HTML report with PDF links for local investigation.

    This report includes all the standard statistics plus:
    - Document index with links to source PDFs
    - Entity tables with expandable document lists
    - Direct links to PDFs from sensitive content sections

    Args:
        results: Dictionary with aggregated statistics from process_documents(full_mode=True)
        output_dir: Directory to save the report
        output_file: Name of the HTML file
        standalone: If True (default), embed images as base64 for a self-contained file.
        serve_mode: If True, generate server-compatible URLs (/pdf/) and include PDF viewer.
        github_pages_mode: If True, disable PDF links for GitHub Pages deployment.
        external_pdf_viewer: Base URL for external PDF viewer (e.g., https://declasseuucl.vercel.app)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Generate interactive timeline (full report uses JavaScript-based visualization)
    interactive_timeline_html = generate_timeline_with_monthly_detail(
        timeline_yearly=results["timeline_yearly"],
        timeline_monthly=results["timeline_monthly"],
        classification_by_year=results.get("classification_by_year"),
        container_id="timeline-chart-full",
        height="550px",
    )

    # Generate network graphs (requires all_documents from full_mode)
    all_documents = results.get("all_documents", [])
    if all_documents:
        # Convert all_documents to the format expected by network functions
        docs_for_network = []
        for doc in all_documents:
            docs_for_network.append({
                "metadata": {
                    "document_id": doc.get("doc_id", ""),
                    "people_mentioned": doc.get("people", []),
                    "organizations_mentioned": doc.get("organizations", []),
                }
            })

        people_network_html = generate_people_network(
            docs_for_network,
            container_id="people-network-full",
            height="600px",
            max_nodes=75,
            min_occurrences=3,
            min_edge_weight=2,
        )

        org_network_html = generate_organization_network(
            docs_for_network,
            container_id="org-network-full",
            height="500px",
            max_nodes=50,
            min_occurrences=3,
            min_edge_weight=2,
        )
    else:
        people_network_html = "<p><em>Network visualization requires full mode data</em></p>"
        org_network_html = "<p><em>Network visualization requires full mode data</em></p>"

    # Generate geographic map
    geographic_map_html = generate_geographic_map(
        city_count=results.get("city_count", Counter()),
        country_count=results.get("country_count", Counter()),
        other_place_count=results.get("other_place_count", Counter()),
        torture_detention_centers=results.get("torture_detention_centers", Counter()),
        container_id="geographic-map-full",
        height="600px",
        show_detention_centers=True,
        show_condor_countries=True,
    )

    # Generate sensitive content dashboard
    sensitive_summary_html = generate_sensitive_summary_cards(
        docs_with_violence=results.get("docs_with_violence", 0),
        docs_with_torture=results.get("docs_with_torture", 0),
        docs_with_disappearance=results.get("docs_with_disappearance", 0),
        total_docs=results.get("total_docs", 0),
        violence_victims=results.get("violence_victims", Counter()),
        torture_victims=results.get("torture_victims", Counter()),
        disappearance_victims=results.get("disappearance_victims", Counter()),
        violence_perpetrators=results.get("violence_perpetrators", Counter()),
        torture_perpetrators=results.get("torture_perpetrators", Counter()),
        disappearance_perpetrators=results.get("disappearance_perpetrators", Counter()),
    )

    sensitive_timeline_html = generate_sensitive_timeline(
        sensitive_content_by_year=results.get("sensitive_content_by_year", {}),
        container_id="sensitive-timeline-full",
        height="400px",
        include_events=True,
    )

    # Generate perpetrator-victim network (only in full mode with doc mappings)
    if results.get("full_mode"):
        perp_victim_network_html = generate_perpetrator_victim_network(
            violence_victims=results.get("violence_victims", Counter()),
            violence_perpetrators=results.get("violence_perpetrators", Counter()),
            torture_victims=results.get("torture_victims", Counter()),
            torture_perpetrators=results.get("torture_perpetrators", Counter()),
            disappearance_victims=results.get("disappearance_victims", Counter()),
            disappearance_perpetrators=results.get("disappearance_perpetrators", Counter()),
            violence_victim_docs=results.get("violence_victim_docs"),
            violence_perp_docs=results.get("violence_perp_docs"),
            torture_victim_docs=results.get("torture_victim_docs"),
            torture_perp_docs=results.get("torture_perp_docs"),
            disappearance_victim_docs=results.get("disappearance_victim_docs"),
            disappearance_perp_docs=results.get("disappearance_perp_docs"),
            container_id="perp-victim-network-full",
            height="600px",
            max_nodes=75,
            min_mentions=2,
        )
    else:
        perp_victim_network_html = "<p><em>Perpetrator-victim network requires full mode</em></p>"

    incident_types_html = generate_incident_types_chart(
        violence_incident_types=results.get("violence_incident_types", Counter()),
        torture_methods=results.get("torture_methods", Counter()),
        container_id="incident-types-full",
        height="350px",
        max_items=12,
    )

    # Generate keyword word cloud
    keyword_cloud_html = generate_keyword_cloud(
        keyword_count=results.get("keywords_count", Counter()),
        container_id="keyword-cloud-full",
        width=800,
        height=400,
        max_words=80,
        min_count=2,
    )

    # Generate financial dashboard visualizations
    financial_summary_html = generate_financial_summary_cards(
        docs_with_financial=results.get("docs_with_financial", 0),
        total_docs=results.get("total_docs", 0),
        financial_amounts=results.get("financial_amounts", []),
        financial_actors_count=results.get("financial_actors_count", Counter()),
        financial_purposes_count=results.get("financial_purposes_count", Counter()),
    )

    # financial_purposes_chart_html is generated after create_pdf_link is defined

    financial_actors_chart_html = generate_financial_actors_chart(
        financial_actors_count=results.get("financial_actors_count", Counter()),
        container_id="financial-actors-chart",
        height="400px",
        max_items=15,
    )

    # NEW: Category cards showing covert ops vs macro-economic
    financial_category_html = generate_financial_category_cards(
        covert_ops_amounts=results.get("covert_ops_amounts", []),
        macro_economic_amounts=results.get("macro_economic_amounts", []),
    )

    # NEW: Timeline chart
    financial_timeline_html = generate_financial_timeline(
        financial_amounts_by_year=results.get("financial_amounts_by_year", {}),
        container_id="financial-timeline",
        height="350px",
    )

    # Generate static plots for other charts
    classification_path = os.path.join(output_dir, "classification.png")
    doc_types_path = os.path.join(output_dir, "doc_types.png")
    confidence_path = os.path.join(output_dir, "confidence.png")

    classification_exists = plot_pie_chart(
        results["classification_count"],
        classification_path,
        "Classification Levels"
    )
    doc_type_exists = plot_pie_chart(
        results["doc_type_count"],
        doc_types_path,
        "Document Types"
    )
    confidence_exists = plot_confidence_histogram(
        results["confidence_scores"],
        confidence_path
    )

    # Generate research questions section
    research_questions_html = generate_research_questions_section(
        external_pdf_viewer=external_pdf_viewer,
    )
    research_questions_css = generate_research_questions_css()

    # Convert images to base64 if standalone mode
    if standalone:
        classification_src = image_to_base64(classification_path) if classification_exists else ""
        doc_types_src = image_to_base64(doc_types_path) if doc_type_exists else ""
        confidence_src = image_to_base64(confidence_path) if confidence_exists else ""
        for path in [classification_path, doc_types_path, confidence_path]:
            if os.path.exists(path):
                os.remove(path)
    else:
        # Non-standalone mode: use file paths for images
        classification_src = "classification.png"
        doc_types_src = "doc_types.png"
        confidence_src = "confidence.png"

    def create_pdf_link(
        pdf_path: str,
        label: str,
        doc_id: str | None = None,
        basename: str | None = None
    ) -> str:
        """Create an HTML link to a PDF file."""
        if external_pdf_viewer and (basename or doc_id):
            # Use external PDF viewer URL - prefer basename (numeric) over doc_id
            external_id = basename or doc_id
            url = f"{external_pdf_viewer}/?currentPage=1&documentId={external_id}"
            return f'<a href="{url}" target="_blank" class="pdf-link external">{label}</a>'
        if github_pages_mode and not external_pdf_viewer:
            # No PDF links in GitHub Pages mode without external viewer
            return f'<span class="pdf-unavailable" title="PDFs not available online">{label}</span>'
        if pdf_path:
            if serve_mode:
                # Use server URL for PDF viewer modal
                filename = os.path.basename(pdf_path)
                return f'<a href="/pdf/{filename}" class="pdf-link">{label}</a>'
            else:
                # Use file:// URL for direct opening
                return f'<a href="file://{os.path.abspath(pdf_path)}" target="_blank">{label}</a>'
        return label

    # Generate financial purposes chart with document links (now that create_pdf_link is available)
    financial_purposes_chart_html = generate_financial_purposes_chart(
        financial_purposes_count=results.get("financial_purposes_count", Counter()),
        container_id="financial-purposes-chart",
        height="350px",
        purpose_docs=results.get("financial_purpose_docs"),
        create_pdf_link_fn=create_pdf_link,
        max_docs_display=20,
    )

    def create_table(counter: dict, limit: int = 50, id_prefix: str = "", show_all: bool = True) -> str:
        """Create an HTML table from a Counter, with optional collapsible rows.

        Args:
            counter: Dict of item -> count
            limit: Number of items to show initially
            id_prefix: Unique prefix for table IDs
            show_all: If False, never show "Show all X items" button (prevents DOM bloat)
        """
        if not counter:
            return "<p><em>No data available</em></p>"

        sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        total_items = len(sorted_items)

        # When show_all is False, only include visible rows (no hidden section)
        if not show_all:
            sorted_items = sorted_items[:limit]

        rows_visible = []
        rows_hidden = []

        for i, (k, v) in enumerate(sorted_items):
            row = f"<tr><td>{k}</td><td>{v:,}</td></tr>"
            if i < limit:
                rows_visible.append(row)
            else:
                rows_hidden.append(row)

        table_id = id_prefix or f"table_{hash(str(counter))}"

        html = f"""
        <table class="data-table">
            <thead><tr><th>Item</th><th>Count</th></tr></thead>
            <tbody id="{table_id}_visible">{''.join(rows_visible)}</tbody>
        """

        if rows_hidden and show_all:
            html += f"""
            <tbody id="{table_id}_hidden" class="hidden">{''.join(rows_hidden)}</tbody>
            </table>
            <button class="show-more-btn" onclick="toggleRows('{table_id}')">
                Show all {total_items:,} items ({total_items - limit:,} more)
            </button>
            """
        else:
            html += "</table>"
            # Show count of hidden items when show_all is False
            if total_items > limit and not show_all:
                html += f"<p class='table-note'><em>Showing top {limit} of {total_items:,} items</em></p>"

        return html

    def create_table_with_docs(
        counter: dict,
        docs_map: dict,
        limit: int = 50,
        id_prefix: str = ""
    ) -> str:
        """Create an HTML table with expandable document links using <details>."""
        if not counter:
            return "<p><em>No data available</em></p>"

        sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        rows = []

        for i, (name, count) in enumerate(sorted_items[:limit]):
            doc_refs = docs_map.get(name, [])
            if doc_refs:
                # Create expandable document list
                doc_links = []
                for doc_id, pdf_path, doc_basename in doc_refs[:20]:  # Limit to 20 docs
                    link = create_pdf_link(pdf_path, f"{doc_basename}", doc_id=doc_id, basename=doc_basename)
                    doc_links.append(f"<li>{link} <small>({doc_id})</small></li>")

                more_text = ""
                if len(doc_refs) > 20:
                    more_text = f"<li><em>... and {len(doc_refs) - 20} more</em></li>"

                details_html = f'''
                <details>
                    <summary>{count:,} documents</summary>
                    <ul class="doc-list">{"".join(doc_links)}{more_text}</ul>
                </details>
                '''
                rows.append(f"<tr><td>{name}</td><td>{details_html}</td></tr>")
            else:
                rows.append(f"<tr><td>{name}</td><td>{count:,}</td></tr>")

        more_rows = ""
        if len(sorted_items) > limit:
            more_rows = f"<tr><td colspan='2'><em>... and {len(sorted_items) - limit} more items</em></td></tr>"

        return f"""
        <table class="data-table">
            <thead><tr><th>Item</th><th>Documents</th></tr></thead>
            <tbody>{"".join(rows)}{more_rows}</tbody>
        </table>
        """

    def create_entity_summary_section(results: dict) -> str:
        """Create a compact entity summary section with cards linking to Entity Explorer."""

        def get_top_items(counter: dict, n: int = 5) -> list:
            """Get top N items from a counter."""
            if not counter:
                return []
            return sorted(counter.items(), key=lambda x: x[1], reverse=True)[:n]

        def format_item_list(items: list) -> str:
            """Format items as a compact list."""
            if not items:
                return "<p class='no-data'>No data</p>"
            html = "<ul class='entity-top-list'>"
            for name, count in items:
                # Truncate long names
                display_name = name[:30] + "..." if len(name) > 30 else name
                html += f"<li><span class='entity-name' title='{name}'>{display_name}</span> <span class='entity-count'>({count:,})</span></li>"
            html += "</ul>"
            return html

        # Get counts
        people_total = len(results.get('people_count', {}))
        people_mentions = sum(results.get('people_count', {}).values())
        orgs_total = len(results.get('org_count', {}))
        orgs_mentions = sum(results.get('org_count', {}).values())
        keywords_total = len(results.get('keywords_count', {}))
        keywords_mentions = sum(results.get('keywords_count', {}).values())
        places_total = (
            len(results.get('country_count', {})) +
            len(results.get('city_count', {})) +
            len(results.get('other_place_count', {}))
        )
        places_mentions = (
            sum(results.get('country_count', {}).values()) +
            sum(results.get('city_count', {}).values()) +
            sum(results.get('other_place_count', {}).values())
        )

        # Get top items
        top_people = get_top_items(results.get('people_count', {}), 5)
        top_orgs = get_top_items(results.get('org_count', {}), 5)
        top_keywords = get_top_items(results.get('keywords_count', {}), 5)
        top_countries = get_top_items(results.get('country_count', {}), 5)

        return f"""
        <div class="entity-summary-header">
            <p>Explore all entities extracted from {results.get('total_docs', 0):,} declassified documents.</p>
            <a href="entities/" class="btn btn-primary">Open Entity Explorer →</a>
        </div>

        <div class="entity-cards">
            <div class="entity-card">
                <div class="entity-card-header">
                    <span class="entity-icon">👤</span>
                    <h3>People</h3>
                </div>
                <div class="entity-stats">
                    <span class="stat-number">{people_total:,}</span>
                    <span class="stat-label">unique individuals</span>
                </div>
                <div class="entity-mentions">{people_mentions:,} total mentions</div>
                <h4>Most Mentioned</h4>
                {format_item_list(top_people)}
                <a href="entities/?type=person" class="entity-card-link">View all people →</a>
            </div>

            <div class="entity-card">
                <div class="entity-card-header">
                    <span class="entity-icon">🏢</span>
                    <h3>Organizations</h3>
                </div>
                <div class="entity-stats">
                    <span class="stat-number">{orgs_total:,}</span>
                    <span class="stat-label">unique organizations</span>
                </div>
                <div class="entity-mentions">{orgs_mentions:,} total mentions</div>
                <h4>Most Mentioned</h4>
                {format_item_list(top_orgs)}
                <a href="entities/?type=organization" class="entity-card-link">View all organizations →</a>
            </div>

            <div class="entity-card">
                <div class="entity-card-header">
                    <span class="entity-icon">🏷️</span>
                    <h3>Keywords</h3>
                </div>
                <div class="entity-stats">
                    <span class="stat-number">{keywords_total:,}</span>
                    <span class="stat-label">unique keywords</span>
                </div>
                <div class="entity-mentions">{keywords_mentions:,} total mentions</div>
                <h4>Most Used</h4>
                {format_item_list(top_keywords)}
                <a href="entities/?type=keyword" class="entity-card-link">View all keywords →</a>
            </div>

            <div class="entity-card">
                <div class="entity-card-header">
                    <span class="entity-icon">📍</span>
                    <h3>Places</h3>
                </div>
                <div class="entity-stats">
                    <span class="stat-number">{places_total:,}</span>
                    <span class="stat-label">unique locations</span>
                </div>
                <div class="entity-mentions">{places_mentions:,} total mentions</div>
                <h4>Top Countries</h4>
                {format_item_list(top_countries)}
                <a href="entities/?type=place" class="entity-card-link">View all places →</a>
            </div>
        </div>
        """

    def create_financial_summary_section(results: dict) -> str:
        """Create a compact financial summary section with two cards."""

        def get_top_items(counter: dict, n: int = 5) -> list:
            """Get top N items from a counter."""
            if not counter:
                return []
            return sorted(counter.items(), key=lambda x: x[1], reverse=True)[:n]

        def format_item_list(items: list) -> str:
            """Format items as a compact list."""
            if not items:
                return "<p class='no-data'>No data</p>"
            html = "<ul class='entity-top-list'>"
            for name, count in items:
                # Truncate long names
                display_name = name[:35] + "..." if len(name) > 35 else name
                html += f"<li><span class='entity-name' title='{name}'>{display_name}</span> <span class='entity-count'>({count:,})</span></li>"
            html += "</ul>"
            return html

        # Get counts
        purposes = results.get('financial_purposes_count', {})
        actors = results.get('financial_actors_count', {})
        purposes_total = len(purposes)
        purposes_mentions = sum(purposes.values())
        actors_total = len(actors)
        actors_mentions = sum(actors.values())

        # Get top items
        top_purposes = get_top_items(purposes, 5)
        top_actors = get_top_items(actors, 5)

        return f"""
        <div class="financial-cards">
            <div class="financial-card">
                <div class="entity-card-header">
                    <span class="entity-icon">💰</span>
                    <h3>Funding Purposes</h3>
                </div>
                <div class="entity-stats">
                    <span class="stat-number">{purposes_total:,}</span>
                    <span class="stat-label">purpose categories</span>
                </div>
                <div class="entity-mentions">{purposes_mentions:,} total references</div>
                <h4>Most Common</h4>
                {format_item_list(top_purposes)}
            </div>

            <div class="financial-card">
                <div class="entity-card-header">
                    <span class="entity-icon">🏛️</span>
                    <h3>Financial Actors</h3>
                </div>
                <div class="entity-stats">
                    <span class="stat-number">{actors_total:,}</span>
                    <span class="stat-label">entities mentioned</span>
                </div>
                <div class="entity-mentions">{actors_mentions:,} total mentions</div>
                <h4>Top Actors</h4>
                {format_item_list(top_actors)}
                <a href="entities/?type=organization" class="entity-card-link">View in Entity Explorer →</a>
            </div>
        </div>
        """

    def create_document_index(documents: list, limit: int = 500) -> str:
        """Create a searchable document index table."""
        if not documents:
            return "<p><em>No documents available</em></p>"

        # Sort by date (most recent first), then by basename
        sorted_docs = sorted(
            documents,
            key=lambda d: (d.get("date", "") or "0000-00-00", d.get("basename", "")),
            reverse=True
        )

        rows = []
        for doc in sorted_docs[:limit]:
            pdf_link = create_pdf_link(
                doc["pdf_path"], "View PDF",
                doc_id=doc.get("doc_id"),
                basename=doc.get("basename")
            )
            title = doc.get("title", "") or doc.get("doc_id", doc["basename"])
            if len(title) > 60:
                title = title[:57] + "..."

            rows.append(f"""
            <tr>
                <td>{doc.get('date', 'Unknown')}</td>
                <td class="classification-{doc.get('classification', 'Unknown').lower().replace(' ', '-')}">{doc.get('classification', 'Unknown')}</td>
                <td>{doc.get('doc_type', 'Unknown')}</td>
                <td title="{doc.get('title', '')}">{title}</td>
                <td>{doc.get('page_count', 0)}</td>
                <td>{pdf_link}</td>
            </tr>
            """)

        more_text = ""
        if len(sorted_docs) > limit:
            more_text = f"<p><em>Showing {limit} of {len(sorted_docs)} documents</em></p>"

        return f"""
        {more_text}
        <table class="data-table doc-index">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Classification</th>
                    <th>Type</th>
                    <th>Title</th>
                    <th>Pages</th>
                    <th>PDF</th>
                </tr>
            </thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
        """

    def format_number(n: int) -> str:
        return f"{n:,}"

    def pct(part: int, total: int) -> str:
        if total == 0:
            return "0%"
        return f"{part/total*100:.1f}%"

    # Calculate summary stats
    total = results["total_docs"]
    avg_confidence = sum(results["confidence_scores"]) / len(results["confidence_scores"]) if results["confidence_scores"] else 0

    # Build HTML with full mode enhancements
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Declassified Documents Analysis - Full Report</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --danger: #dc2626;
            --warning: #f59e0b;
            --success: #10b981;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-600: #4b5563;
            --gray-800: #1f2937;
        }}

        * {{ box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: var(--gray-100);
            color: var(--gray-800);
            line-height: 1.6;
        }}

        .container {{
            display: flex;
            min-height: 100vh;
        }}

        nav {{
            width: 250px;
            background: var(--gray-800);
            color: white;
            padding: 20px;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
        }}

        nav h2 {{
            margin-top: 0;
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--gray-200);
        }}

        nav ul {{ list-style: none; padding: 0; margin: 0; }}
        nav li {{ margin: 8px 0; }}
        nav a {{
            color: var(--gray-200);
            text-decoration: none;
            font-size: 0.9rem;
            display: block;
            padding: 6px 10px;
            border-radius: 4px;
            transition: background 0.2s;
        }}
        nav a:hover {{ background: rgba(255,255,255,0.1); }}
        nav .nav-section {{
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        nav .nav-section-title {{
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--gray-600);
            margin-bottom: 8px;
        }}

        main {{
            flex: 1;
            margin-left: 250px;
            padding: 30px 40px;
            max-width: 1400px;
        }}

        h1 {{
            color: var(--gray-800);
            border-bottom: 3px solid var(--primary);
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}

        h2 {{
            color: var(--gray-800);
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--gray-200);
        }}

        h3 {{ color: var(--gray-600); margin-top: 25px; }}

        .full-mode-badge {{
            background: var(--primary);
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-left: 10px;
            vertical-align: middle;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .summary-card.danger {{ border-left: 4px solid var(--danger); }}
        .summary-card.warning {{ border-left: 4px solid var(--warning); }}

        .summary-card h3 {{
            margin: 0 0 5px 0;
            font-size: 0.85rem;
            text-transform: uppercase;
            color: var(--gray-600);
        }}

        .summary-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--gray-800);
        }}

        .summary-card .subtext {{
            font-size: 0.85rem;
            color: var(--gray-600);
        }}

        /* Entity Summary Cards */
        .entity-summary-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px 20px;
            background: linear-gradient(135deg, var(--gray-100), white);
            border-radius: 8px;
            border: 1px solid var(--gray-200);
        }}

        .entity-summary-header p {{
            margin: 0;
            color: var(--gray-600);
        }}

        .entity-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .entity-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid var(--gray-200);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .entity-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }}

        .entity-card-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }}

        .entity-card-header .entity-icon {{
            font-size: 1.5rem;
        }}

        .entity-card-header h3 {{
            margin: 0;
            font-size: 1.1rem;
            color: var(--gray-800);
        }}

        .entity-stats {{
            text-align: center;
            padding: 15px 0;
            background: var(--gray-100);
            border-radius: 8px;
            margin-bottom: 10px;
        }}

        .entity-stats .stat-number {{
            display: block;
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary);
        }}

        .entity-stats .stat-label {{
            font-size: 0.85rem;
            color: var(--gray-600);
        }}

        .entity-mentions {{
            text-align: center;
            font-size: 0.85rem;
            color: var(--gray-600);
            margin-bottom: 15px;
        }}

        .entity-card h4 {{
            font-size: 0.9rem;
            color: var(--gray-600);
            margin: 15px 0 10px 0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .entity-top-list {{
            list-style: none;
            padding: 0;
            margin: 0 0 15px 0;
        }}

        .entity-top-list li {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid var(--gray-100);
            font-size: 0.9rem;
        }}

        .entity-top-list li:last-child {{
            border-bottom: none;
        }}

        .entity-top-list .entity-name {{
            color: var(--gray-800);
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .entity-top-list .entity-count {{
            color: var(--gray-600);
            font-size: 0.85rem;
            margin-left: 10px;
        }}

        .entity-card-link {{
            display: block;
            text-align: center;
            padding: 10px;
            background: var(--gray-100);
            border-radius: 6px;
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
            transition: background 0.2s;
        }}

        .entity-card-link:hover {{
            background: var(--gray-200);
        }}

        /* Financial summary cards (2-column) */
        .financial-cards {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}

        .financial-card {{
            background: white;
            border: 1px solid var(--gray-200);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        @media (max-width: 768px) {{
            .financial-cards {{
                grid-template-columns: 1fr;
            }}
        }}

        .btn {{
            display: inline-block;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s;
        }}

        .btn-primary {{
            background: var(--primary);
            color: white;
        }}

        .btn-primary:hover {{
            background: var(--primary-dark);
        }}

        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}

        .chart-container img {{ max-width: 100%; height: auto; }}

        .data-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin: 15px 0;
        }}

        .data-table th {{
            background: var(--gray-800);
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
        }}

        .data-table td {{
            padding: 10px 15px;
            border-bottom: 1px solid var(--gray-200);
            vertical-align: top;
        }}

        .data-table tr:hover {{ background: var(--gray-100); }}

        .doc-index td {{ font-size: 0.9rem; }}

        /* Classification colors */
        .classification-top-secret {{ color: #dc2626; font-weight: bold; }}
        .classification-secret {{ color: #ea580c; font-weight: bold; }}
        .classification-confidential {{ color: #ca8a04; }}
        .classification-unclassified {{ color: #16a34a; }}

        details {{
            cursor: pointer;
        }}

        details summary {{
            color: var(--primary);
            font-weight: 500;
        }}

        details summary:hover {{
            text-decoration: underline;
        }}

        .doc-list {{
            margin: 10px 0;
            padding-left: 20px;
            font-size: 0.9rem;
        }}

        .doc-list li {{
            margin: 4px 0;
        }}

        .doc-list a {{
            color: var(--primary);
            text-decoration: none;
        }}

        .doc-list a:hover {{
            text-decoration: underline;
        }}

        .pdf-unavailable {{
            color: var(--gray-600);
            font-style: italic;
            cursor: not-allowed;
        }}

        .pdf-link.external::after {{
            content: " ↗";
            font-size: 0.8em;
        }}

        .show-more-btn {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            margin-top: 10px;
        }}

        .show-more-btn:hover {{
            background: var(--primary-dark);
        }}

        .table-note {{
            color: var(--gray-600);
            font-size: 0.85rem;
            margin-top: 8px;
        }}

        .sensitive-warning {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 15px 20px;
            margin: 20px 0;
        }}

        .sensitive-warning h4 {{
            color: var(--danger);
            margin: 0 0 10px 0;
        }}

        .two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        .meta-info {{
            background: var(--gray-200);
            padding: 10px 15px;
            border-radius: 4px;
            font-size: 0.85rem;
            color: var(--gray-600);
            margin-bottom: 30px;
        }}

        @media (max-width: 900px) {{
            nav {{ display: none; }}
            main {{ margin-left: 0; }}
            .two-col {{ grid-template-columns: 1fr; }}
        }}

        /* Research Questions Styles */
        {research_questions_css}
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <h2>Navigation</h2>
            <ul>
                <li><a href="#overview">Overview</a></li>
                <li><a href="#documents">Document Explorer</a></li>
                <li><a href="#research-questions">Research Questions</a></li>
                <li><a href="#timeline">Timeline</a></li>
                <li><a href="#classification">Classification</a></li>
                <li><a href="#document-types">Document Types</a></li>
            </ul>

            <div class="nav-section">
                <div class="nav-section-title">Network Analysis</div>
                <ul>
                    <li><a href="#people-network">People Network</a></li>
                    <li><a href="#org-network">Organization Network</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Geographic</div>
                <ul>
                    <li><a href="#geographic-map">Geographic Map</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Entities</div>
                <ul>
                    <li><a href="#entity-summary">Entity Summary</a></li>
                    <li><a href="entities/">Entity Explorer</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Sensitive Content</div>
                <ul>
                    <li><a href="#sensitive-dashboard">Dashboard</a></li>
                    <li><a href="#violence">Violence</a></li>
                    <li><a href="#torture">Torture</a></li>
                    <li><a href="#disappearances">Disappearances</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Other</div>
                <ul>
                    <li><a href="#financial">Financial</a></li>
                    <li><a href="#confidence">Confidence</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Explorers</div>
                <ul>
                    <li><a href="explorer/">Document Explorer</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Project</div>
                <ul>
                    <li><a href="about.html">About</a></li>
                </ul>
            </div>
        </nav>

        <main>
            <h1>Declassified CIA Documents Analysis <span class="full-mode-badge">{"Online Report" if github_pages_mode else "Full Report"}</span></h1>

            <div class="meta-info">
                Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} |
                {"<strong>Online version - PDFs not available</strong>" if github_pages_mode else f"Source: {output_dir} | <strong>Full mode with PDF links (for local use only)</strong>"}
            </div>

            <section id="overview">
                <h2>Overview</h2>
                <div class="summary-grid">
                    <div class="summary-card">
                        <h3>Total Documents</h3>
                        <div class="value">{format_number(total)}</div>
                        <div class="subtext">{format_number(results['total_pages'])} total pages</div>
                    </div>
                    <div class="summary-card">
                        <h3>Avg Confidence</h3>
                        <div class="value">{avg_confidence:.1%}</div>
                        <div class="subtext">{format_number(len(results['confidence_scores']))} scored</div>
                    </div>
                    <div class="summary-card danger">
                        <h3>Violence Content</h3>
                        <div class="value">{format_number(results['docs_with_violence'])}</div>
                        <div class="subtext">{pct(results['docs_with_violence'], total)} of documents</div>
                    </div>
                    <div class="summary-card danger">
                        <h3>Torture Content</h3>
                        <div class="value">{format_number(results['docs_with_torture'])}</div>
                        <div class="subtext">{pct(results['docs_with_torture'], total)} of documents</div>
                    </div>
                    <div class="summary-card danger">
                        <h3>Disappearances</h3>
                        <div class="value">{format_number(results['docs_with_disappearance'])}</div>
                        <div class="subtext">{pct(results['docs_with_disappearance'], total)} of documents</div>
                    </div>
                    <div class="summary-card warning">
                        <h3>Financial Content</h3>
                        <div class="value">{format_number(results['docs_with_financial'])}</div>
                        <div class="subtext">{pct(results['docs_with_financial'], total)} of documents</div>
                    </div>
                </div>
            </section>

            <section id="documents">
                <h2>Document Explorer</h2>
                {f'''
                <div class="explorer-teaser" style="background: white; padding: 24px; border-radius: 8px; margin-bottom: 24px; text-align: center;">
                    <p style="font-size: 18px; margin-bottom: 16px;">
                        Browse, search, and filter all <strong>{format_number(total)}</strong> declassified documents.
                    </p>
                    <a href="explorer/" class="btn" style="display: inline-block; background: var(--primary); color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600;">
                        Open Document Explorer &rarr;
                    </a>
                </div>
                <h3>Recent Documents</h3>
                <p>Showing the 10 most recent documents:</p>
                {create_document_index(results.get('all_documents', []), limit=10)}
                ''' if github_pages_mode else f'''
                <p>Browse all processed documents. Click "View PDF" to open the source document.</p>
                {create_document_index(results.get('all_documents', []))}
                '''}
            </section>

            {research_questions_html}

            <section id="timeline">
                <h2>Timeline</h2>
                <p>Interactive timeline showing document distribution over time with historical event annotations.
                Use the controls to zoom, pan, and switch between yearly/monthly views.</p>
                <div class="chart-container">
                    {interactive_timeline_html}
                </div>
            </section>

            <section id="classification">
                <h2>Classification Levels</h2>
                <div class="two-col">
                    {f"<div class='chart-container'><img src='{classification_src}' alt='Classification'></div>" if classification_exists else ""}
                    {f"<div class='chart-container'><img src='{doc_types_src}' alt='Document Types'></div>" if doc_type_exists else ""}
                </div>
            </section>

            <section id="document-types">
                <h2>Document Types</h2>
                {create_table(results['doc_type_count'], limit=15, id_prefix='doc_types')}

                <h3>Languages</h3>
                {create_table(results['language_count'], limit=10, id_prefix='languages')}
            </section>

            <section id="people-network">
                <h2>People Network</h2>
                <p>Interactive network showing relationships between people mentioned in documents.
                People who frequently appear together in documents are connected by edges.
                Node size reflects mention frequency. Drag nodes to explore, scroll to zoom.</p>
                <div class="chart-container">
                    {people_network_html}
                </div>
            </section>

            <section id="org-network">
                <h2>Organization Network</h2>
                <p>Interactive network showing relationships between organizations mentioned in documents.
                Organizations that frequently appear together are connected by edges.</p>
                <div class="chart-container">
                    {org_network_html}
                </div>
            </section>

            <section id="geographic-map">
                <h2>Geographic Map</h2>
                <p>Interactive map showing locations mentioned in documents. Blue markers show document mentions
                (larger = more frequent). Red markers indicate known detention and torture centers.
                Country boundaries highlight Operation Condor member countries. Toggle layers using the checkboxes.</p>
                <div class="chart-container">
                    {geographic_map_html}
                </div>
            </section>

            <section id="entity-summary">
                <h2>Entity Summary</h2>
                <p>Overview of all people, organizations, keywords, and places extracted from documents.
                Use the Entity Explorer for advanced search and filtering.</p>
                {create_entity_summary_section(results)}

                <h3>Keyword Cloud</h3>
                <p>Visual representation of keyword frequency. Larger words appear more often in documents.</p>
                <div class="chart-container">
                    {keyword_cloud_html}
                </div>
            </section>

            <section id="sensitive-dashboard">
                <h2>Sensitive Content Dashboard</h2>

                <div class="sensitive-warning">
                    <h4>Content Warning</h4>
                    <p>This section contains analysis of violence, torture, and forced disappearances documented in declassified materials.
                    These visualizations are provided for historical research purposes.</p>
                </div>

                {sensitive_summary_html}

                <h3>Sensitive Content Over Time</h3>
                <p>Timeline showing how documentation of violence, torture, and disappearances changed over the years.
                Major historical events are marked with vertical lines.</p>
                <div class="chart-container">
                    {sensitive_timeline_html}
                </div>

                <h3>Perpetrator-Victim Network</h3>
                <p>Network graph connecting perpetrators (red) to victims (blue) who appear in the same documents.
                Amber nodes indicate individuals named as both perpetrators and victims. Arrows point from perpetrator to victim.</p>
                <div class="chart-container">
                    {perp_victim_network_html}
                </div>

                <h3>Incident Types & Methods</h3>
                <p>Breakdown of violence incident types and torture methods mentioned in documents.</p>
                <div class="chart-container">
                    {incident_types_html}
                </div>
            </section>

            <section id="violence">
                <h2>Violence References</h2>

                <div class="sensitive-warning">
                    <h4>Content Warning</h4>
                    <p>This section contains references to violence documented in declassified materials. Click document counts to access source PDFs.</p>
                </div>

                <p><strong>{format_number(results['docs_with_violence'])} documents</strong> ({pct(results['docs_with_violence'], total)}) contain violence-related content.</p>

                <div class="two-col">
                    <div>
                        <h3>Victims</h3>
                        {create_table_with_docs(results['violence_victims'], results.get('violence_victim_docs', {}), limit=50, id_prefix='violence_victims')}
                    </div>
                    <div>
                        <h3>Perpetrators</h3>
                        {create_table_with_docs(results['violence_perpetrators'], results.get('violence_perp_docs', {}), limit=50, id_prefix='violence_perps')}
                    </div>
                </div>
            </section>

            <section id="torture">
                <h2>Torture References</h2>

                <div class="sensitive-warning">
                    <h4>Content Warning</h4>
                    <p>This section contains references to torture and detention centers. Click document counts to access source PDFs.</p>
                </div>

                <p><strong>{format_number(results['docs_with_torture'])} documents</strong> ({pct(results['docs_with_torture'], total)}) contain torture-related content.</p>

                <h3>Detention Centers</h3>
                {create_table_with_docs(results['torture_detention_centers'], results.get('torture_center_docs', {}), limit=30, id_prefix='detention_centers')}

                <div class="two-col">
                    <div>
                        <h3>Victims</h3>
                        {create_table_with_docs(results['torture_victims'], results.get('torture_victim_docs', {}), limit=50, id_prefix='torture_victims')}
                    </div>
                    <div>
                        <h3>Perpetrators</h3>
                        {create_table_with_docs(results['torture_perpetrators'], results.get('torture_perp_docs', {}), limit=50, id_prefix='torture_perps')}
                    </div>
                </div>
            </section>

            <section id="disappearances">
                <h2>Disappearance References</h2>

                <div class="sensitive-warning">
                    <h4>Content Warning</h4>
                    <p>This section contains references to forced disappearances. Click document counts to access source PDFs.</p>
                </div>

                <p><strong>{format_number(results['docs_with_disappearance'])} documents</strong> ({pct(results['docs_with_disappearance'], total)}) contain disappearance-related content.</p>

                <div class="two-col">
                    <div>
                        <h3>Victims</h3>
                        {create_table_with_docs(results['disappearance_victims'], results.get('disappearance_victim_docs', {}), limit=50, id_prefix='disapp_victims')}
                    </div>
                    <div>
                        <h3>Perpetrators</h3>
                        {create_table_with_docs(results['disappearance_perpetrators'], results.get('disappearance_perp_docs', {}), limit=50, id_prefix='disapp_perps')}
                    </div>
                </div>
            </section>

            <section id="financial">
                <h2>Financial References</h2>

                {financial_category_html}

                {financial_summary_html}

                {create_financial_summary_section(results)}

                <h3>Financial Activity Timeline</h3>
                <div class="chart-container">
                    {financial_timeline_html}
                </div>

                <div class="two-col">
                    <div>
                        <h3>Funding Purposes Distribution</h3>
                        <div class="chart-container">
                            {financial_purposes_chart_html}
                        </div>
                    </div>
                    <div>
                        <h3>Top Financial Actors Distribution</h3>
                        <div class="chart-container">
                            {financial_actors_chart_html}
                        </div>
                    </div>
                </div>
            </section>

            <section id="confidence">
                <h2>Confidence Scores</h2>
                {f"<div class='chart-container'><img src='{confidence_src}' alt='Confidence Distribution'></div>" if confidence_exists else "<p><em>No confidence data available</em></p>"}

                <h3>Common Concerns</h3>
                <p>Issues flagged during transcription that may require human review.</p>
                {create_table(results['confidence_concerns'], limit=10, id_prefix='concerns', show_all=False)}
            </section>

            <footer style="margin-top: 50px; padding: 20px 0; border-top: 1px solid var(--gray-200); color: var(--gray-600); font-size: 0.85rem;">
                <p>This report analyzes declassified CIA documents related to the Chilean dictatorship (1973-1990).</p>
                <p><strong>{"Online Report:" if github_pages_mode else "Full Report Mode:"}</strong> {"Click PDF links to view documents in the embedded viewer." if external_pdf_viewer else ("This is an online version. Source PDFs are not available for download." if github_pages_mode else ("Click PDF links to view documents in the embedded viewer." if serve_mode else "PDF links are local file:// URLs and will only work on the machine where the PDFs are stored."))}</p>
                {"<p>Source code and data processing pipeline available on <a href='https://github.com/destefani/desclasificados-swd'>GitHub</a>.</p>" if github_pages_mode else ""}
            </footer>
        </main>
    </div>
    {generate_pdf_viewer_modal() if serve_mode else ""}
    {generate_pdf_link_interceptor() if serve_mode else ""}
    {generate_external_viewer_modal() if external_pdf_viewer else ""}
    {generate_external_link_interceptor() if external_pdf_viewer else ""}
</body>
</html>
"""

    output_path = os.path.join(output_dir, output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Full report saved to {output_path}")

    # Generate document explorer for GitHub Pages
    if github_pages_mode:
        _generate_explorer_files(results, output_dir, external_pdf_viewer)


def _generate_explorer_files(
    results: dict,
    output_dir: str,
    external_pdf_viewer: str | None = None,
) -> None:
    """Generate document explorer data and HTML page.

    Args:
        results: Processing results containing all_documents
        output_dir: Base output directory (e.g., 'docs')
        external_pdf_viewer: Base URL for external PDF viewer
    """
    all_documents = results.get("all_documents", [])
    if not all_documents:
        print("Warning: No documents to export for explorer")
        return

    # Generate documents.json
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    docs_json = []
    classifications_set: set[str] = set()
    types_set: set[str] = set()
    years: list[int] = []

    for doc in all_documents:
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

        classification = doc.get("classification", "Unknown") or "Unknown"
        classifications_set.add(classification)

        doc_type = doc.get("doc_type", "Unknown") or "Unknown"
        types_set.add(doc_type)

        keywords = doc.get("keywords", []) or []
        keywords = keywords[:5] if isinstance(keywords, list) else []

        people = doc.get("people", []) or []
        people = people[:5] if isinstance(people, list) else []

        title = doc.get("title", "") or ""
        if len(title) > 100:
            title = title[:97] + "..."

        summary = doc.get("summary", "") or ""
        if len(summary) > 200:
            summary = summary[:197] + "..."

        docs_json.append({
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

    # Sort by date descending
    docs_json.sort(key=lambda d: (d["date"] or "0000-00-00", d["id"]), reverse=True)

    facets = {
        "classifications": sorted(classifications_set),
        "types": sorted(types_set),
        "year_range": {
            "min": min(years) if years else 1963,
            "max": max(years) if years else 1993,
        },
    }

    output_data = {
        "generated": datetime.now().isoformat(),
        "total_count": len(docs_json),
        "schema_version": "1.0.0",
        "documents": docs_json,
        "facets": facets,
    }

    json_path = os.path.join(data_dir, "documents.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False)
    json_size = os.path.getsize(json_path) / 1024 / 1024
    print(f"Explorer data saved to {json_path} ({json_size:.2f} MB)")

    # Generate explorer HTML
    explorer_dir = os.path.join(output_dir, "explorer")
    os.makedirs(explorer_dir, exist_ok=True)

    explorer_html = generate_explorer_html(
        external_pdf_viewer=external_pdf_viewer or "https://declasseuucl.vercel.app"
    )
    explorer_path = os.path.join(explorer_dir, "index.html")
    with open(explorer_path, "w", encoding="utf-8") as f:
        f.write(explorer_html)
    explorer_size = os.path.getsize(explorer_path) / 1024
    print(f"Explorer page saved to {explorer_path} ({explorer_size:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze declassified CIA documents and generate an HTML report."
    )
    parser.add_argument("directory", help="Directory containing JSON transcript files")
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Output directory for report and images (default: reports)"
    )
    parser.add_argument(
        "--output",
        default="report.html",
        help="Output HTML filename (default: report.html)"
    )
    parser.add_argument(
        "--separate-images",
        action="store_true",
        help="Save chart images as separate PNG files instead of embedding them"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate full report with PDF links for local investigation"
    )
    parser.add_argument(
        "--pdf-dir",
        default="data/original_pdfs",
        help="Directory containing source PDFs (default: data/original_pdfs)"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Generate server-compatible report with embedded PDF viewer (use with app.serve_report)"
    )
    parser.add_argument(
        "--github-pages",
        action="store_true",
        help="Generate GitHub Pages compatible report (use with --external-pdf-viewer for PDF links)"
    )
    parser.add_argument(
        "--external-pdf-viewer",
        type=str,
        metavar="BASE_URL",
        help="Use external PDF viewer URL (e.g., https://declasseuucl.vercel.app)"
    )
    args = parser.parse_args()

    print(f"Processing documents from: {args.directory}")

    if args.full or args.serve or args.github_pages or args.external_pdf_viewer:
        print(f"Full mode enabled - PDFs from: {args.pdf_dir}")
        if args.serve:
            print("Serve mode enabled - generating server-compatible report with PDF viewer")
        if args.github_pages:
            if args.external_pdf_viewer:
                print(f"GitHub Pages mode enabled - using external PDF viewer: {args.external_pdf_viewer}")
            else:
                print("GitHub Pages mode enabled - generating report without PDF links")
        elif args.external_pdf_viewer:
            print(f"External PDF viewer enabled: {args.external_pdf_viewer}")
        results = process_documents(args.directory, full_mode=True, pdf_dir=args.pdf_dir)
        print(f"Processed {results['total_docs']:,} documents ({results['files_skipped']} files skipped)")

        # GitHub Pages mode overrides output directory and filename
        if args.github_pages:
            output_dir = "docs"
            output_file = "index.html"
        else:
            output_dir = args.output_dir
            output_file = args.output if args.output != "report.html" else "report_full.html"

        standalone = not args.separate_images
        generate_full_html_report(
            results,
            output_dir=output_dir,
            output_file=output_file,
            standalone=standalone,
            serve_mode=args.serve,
            github_pages_mode=args.github_pages,
            external_pdf_viewer=args.external_pdf_viewer,
        )
        if args.serve:
            print(f"\nTo view the report with PDF viewer, run:")
            print(f"  uv run python -m app.serve_report --report {output_dir}/{output_file}")
        if args.github_pages:
            print(f"\nGitHub Pages report generated at: {output_dir}/{output_file}")
            print("Push to GitHub and enable Pages from the 'docs/' folder in repository settings.")
    else:
        results = process_documents(args.directory)
        print(f"Processed {results['total_docs']:,} documents ({results['files_skipped']} files skipped)")

        standalone = not args.separate_images
        generate_html_report(
            results,
            output_dir=args.output_dir,
            output_file=args.output,
            standalone=standalone
        )
        if standalone:
            print("Report is standalone (images embedded as base64)")


if __name__ == "__main__":
    main()
