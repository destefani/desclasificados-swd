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
)
from app.visualizations.pdf_viewer import (
    generate_pdf_viewer_modal,
    generate_pdf_link_interceptor,
    generate_external_viewer_modal,
    generate_external_link_interceptor,
)


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

        # Financial references
        fin_refs = metadata.get("financial_references", {})
        if isinstance(fin_refs, dict) and fin_refs.get("has_financial_content"):
            docs_with_financial += 1
            for purpose in fin_refs.get("purposes", []):
                if purpose:
                    financial_purposes_count[purpose] += 1
            for actor in fin_refs.get("financial_actors", []):
                if actor:
                    financial_actors_count[actor] += 1
            for amount in fin_refs.get("amounts", []):
                if isinstance(amount, dict):
                    financial_amounts.append(amount)

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

    def create_table(counter: dict, limit: int = 50, id_prefix: str = "") -> str:
        """Create an HTML table from a Counter, with optional collapsible rows."""
        if not counter:
            return "<p><em>No data available</em></p>"

        sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        total_items = len(sorted_items)

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

        if rows_hidden:
            html += f"""
            <tbody id="{table_id}_hidden" class="hidden">{''.join(rows_hidden)}</tbody>
            </table>
            <button class="show-more-btn" onclick="toggleRows('{table_id}')">
                Show all {total_items:,} items ({total_items - limit:,} more)
            </button>
            """
        else:
            html += "</table>"

        return html

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
                    <li><a href="#people">People Mentioned</a></li>
                    <li><a href="#organizations">Organizations</a></li>
                    <li><a href="#locations">Locations</a></li>
                    <li><a href="#keywords">Keywords</a></li>
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

            <section id="people">
                <h2>People Mentioned</h2>
                <p>Individuals mentioned in document bodies (excluding authors/recipients).</p>
                {create_table(results['people_count'], limit=50, id_prefix='people')}

                <h3>Recipients</h3>
                {create_table(results['recipients_count'], limit=50, id_prefix='recipients')}
            </section>

            <section id="organizations">
                <h2>Organizations</h2>

                <h3>All Organizations</h3>
                {create_table(results['org_count'], limit=50, id_prefix='orgs')}

                <div class="two-col">
                    <div>
                        <h3>By Type</h3>
                        {create_table(results['org_type_count'], limit=20, id_prefix='org_types')}
                    </div>
                    <div>
                        <h3>By Country</h3>
                        {create_table(results['org_country_count'], limit=20, id_prefix='org_countries')}
                    </div>
                </div>
            </section>

            <section id="locations">
                <h2>Locations</h2>

                <div class="two-col">
                    <div>
                        <h3>Countries</h3>
                        {create_table(results['country_count'], limit=30, id_prefix='countries')}
                    </div>
                    <div>
                        <h3>Cities</h3>
                        {create_table(results['city_count'], limit=30, id_prefix='cities')}
                    </div>
                </div>

                <h3>Other Places</h3>
                {create_table(results['other_place_count'], limit=30, id_prefix='other_places')}
            </section>

            <section id="keywords">
                <h2>Keywords</h2>
                {create_table(results['keywords_count'], limit=50, id_prefix='keywords')}
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

                <h3>Purposes</h3>
                {create_table(results['financial_purposes_count'], limit=20, id_prefix='financial_purposes')}

                <h3>Financial Actors</h3>
                {create_table(results['financial_actors_count'], limit=30, id_prefix='financial_actors')}
            </section>

            <section id="confidence">
                <h2>Confidence Scores</h2>

                {f"<div class='chart-container'><img src='{confidence_src}' alt='Confidence Distribution'></div>" if confidence_exists else "<p><em>No confidence data available</em></p>"}

                <h3>Common Concerns</h3>
                <p>Issues flagged during transcription that may require human review.</p>
                {create_table(results['confidence_concerns'], limit=30, id_prefix='concerns')}
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

    financial_purposes_chart_html = generate_financial_purposes_chart(
        financial_purposes_count=results.get("financial_purposes_count", Counter()),
        container_id="financial-purposes-chart",
        height="350px",
    )

    financial_actors_chart_html = generate_financial_actors_chart(
        financial_actors_count=results.get("financial_actors_count", Counter()),
        container_id="financial-actors-chart",
        height="400px",
        max_items=15,
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

    def create_table(counter: dict, limit: int = 50, id_prefix: str = "") -> str:
        """Create an HTML table from a Counter, with optional collapsible rows."""
        if not counter:
            return "<p><em>No data available</em></p>"

        sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        total_items = len(sorted_items)

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

        if rows_hidden:
            html += f"""
            <tbody id="{table_id}_hidden" class="hidden">{''.join(rows_hidden)}</tbody>
            </table>
            <button class="show-more-btn" onclick="toggleRows('{table_id}')">
                Show all {total_items:,} items ({total_items - limit:,} more)
            </button>
            """
        else:
            html += "</table>"

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
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <h2>Navigation</h2>
            <ul>
                <li><a href="#overview">Overview</a></li>
                <li><a href="#documents">Document Index</a></li>
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
                    <li><a href="#locations">Locations</a></li>
                </ul>
            </div>

            <div class="nav-section">
                <div class="nav-section-title">Entities</div>
                <ul>
                    <li><a href="#people">People Mentioned</a></li>
                    <li><a href="#organizations">Organizations</a></li>
                    <li><a href="#keywords">Keywords</a></li>
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
                <h2>Document Index</h2>
                <p>Browse all processed documents. Click "View PDF" to open the source document.</p>
                {create_document_index(results.get('all_documents', []))}
            </section>

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
                Dashed rectangles highlight Operation Condor member countries. Toggle layers using the checkboxes.</p>
                <div class="chart-container">
                    {geographic_map_html}
                </div>
            </section>

            <section id="locations">
                <h2>Locations</h2>
                <div class="two-col">
                    <div>
                        <h3>Countries</h3>
                        {create_table(results['country_count'], limit=30, id_prefix='countries')}
                    </div>
                    <div>
                        <h3>Cities</h3>
                        {create_table(results['city_count'], limit=30, id_prefix='cities')}
                    </div>
                </div>

                <h3>Other Places</h3>
                {create_table(results['other_place_count'], limit=30, id_prefix='other_places')}
            </section>

            <section id="people">
                <h2>People Mentioned</h2>
                <p>Click on the document count to see source documents for each person.</p>
                {create_table_with_docs(results['people_count'], results.get('people_docs', {}), limit=100, id_prefix='people')}

                <h3>Recipients</h3>
                <p>Document recipients (addressees).</p>
                {create_table(results['recipients_count'], limit=50, id_prefix='recipients')}
            </section>

            <section id="organizations">
                <h2>Organizations</h2>
                <p>Click on the document count to see source documents for each organization.</p>
                {create_table_with_docs(results['org_count'], results.get('org_docs', {}), limit=100, id_prefix='orgs')}
            </section>

            <section id="keywords">
                <h2>Keywords</h2>
                <p>Visual representation of keyword frequency. Larger words appear more often in documents.</p>
                <div class="chart-container">
                    {keyword_cloud_html}
                </div>
                <h3>Keyword Details</h3>
                <p>Click on the document count to see source documents for each keyword.</p>
                {create_table_with_docs(results['keywords_count'], results.get('keyword_docs', {}), limit=100, id_prefix='keywords')}
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

                {financial_summary_html}

                <div class="two-col">
                    <div>
                        <h3>Funding Purposes</h3>
                        <div class="chart-container">
                            {financial_purposes_chart_html}
                        </div>
                    </div>
                    <div>
                        <h3>Top Financial Actors</h3>
                        <div class="chart-container">
                            {financial_actors_chart_html}
                        </div>
                    </div>
                </div>

                <h3>Funding Purposes Details</h3>
                {create_table(results['financial_purposes_count'], limit=20, id_prefix='financial_purposes')}

                <h3>Financial Actors Details</h3>
                {create_table(results['financial_actors_count'], limit=30, id_prefix='financial_actors')}
            </section>

            <section id="confidence">
                <h2>Confidence Scores</h2>
                {f"<div class='chart-container'><img src='{confidence_src}' alt='Confidence Distribution'></div>" if confidence_exists else "<p><em>No confidence data available</em></p>"}

                <h3>Common Concerns</h3>
                <p>Issues flagged during transcription that may require human review.</p>
                {create_table(results['confidence_concerns'], limit=30, id_prefix='concerns')}
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
