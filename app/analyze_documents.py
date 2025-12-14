#!/usr/bin/env python3
"""
Analyze declassified CIA documents and generate an HTML report.

This module processes JSON transcript files and generates a comprehensive
HTML report with statistics, visualizations, and sensitive content analysis.
"""
import os
import json
import glob
import argparse
import collections
from datetime import datetime
from typing import Any

from dateutil import parser as date_parser
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt


def process_documents(directory: str) -> dict[str, Any]:
    """
    Process all JSON transcript files in the given directory.

    Skips non-transcript files (failed_*, incomplete_*, processing_*).

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

    total_docs = 0
    total_pages = 0

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

        # Page count
        page_count = metadata.get("page_count", 0)
        if isinstance(page_count, int):
            total_pages += page_count

        # Process document date
        doc_date_str = metadata.get("document_date", "")
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

        # Recipients
        for recipient in metadata.get("recipients", []):
            if recipient:
                recipients_count[recipient] += 1

        # Keywords
        for keyword in metadata.get("keywords", []):
            if keyword:
                keywords_count[keyword] += 1

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
            for incident in vio_refs.get("incident_types", []):
                if incident:
                    violence_incident_types[incident] += 1
            for victim in vio_refs.get("victims", []):
                if victim:
                    violence_victims[victim] += 1
            for perp in vio_refs.get("perpetrators", []):
                if perp:
                    violence_perpetrators[perp] += 1

        # Torture references
        tor_refs = metadata.get("torture_references", {})
        if isinstance(tor_refs, dict) and tor_refs.get("has_torture_content"):
            docs_with_torture += 1
            for center in tor_refs.get("detention_centers", []):
                if center:
                    torture_detention_centers[center] += 1
            for method in tor_refs.get("methods_mentioned", []):
                if method:
                    torture_methods[method] += 1
            for victim in tor_refs.get("victims", []):
                if victim:
                    torture_victims[victim] += 1
            for perp in tor_refs.get("perpetrators", []):
                if perp:
                    torture_perpetrators[perp] += 1

        # Disappearance references
        dis_refs = metadata.get("disappearance_references", {})
        if isinstance(dis_refs, dict) and dis_refs.get("has_disappearance_content"):
            docs_with_disappearance += 1
            for victim in dis_refs.get("victims", []):
                if victim:
                    disappearance_victims[victim] += 1
            for perp in dis_refs.get("perpetrators", []):
                if perp:
                    disappearance_perpetrators[perp] += 1
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


def generate_html_report(results: dict, output_dir: str, output_file: str = "report.html"):
    """Generate a comprehensive HTML report with all statistics and visualizations."""

    os.makedirs(output_dir, exist_ok=True)

    # Generate plots
    timeline_exists = plot_timeline(
        results["timeline_yearly"],
        os.path.join(output_dir, "timeline_yearly.png"),
        "Documents per Year"
    )
    classification_exists = plot_pie_chart(
        results["classification_count"],
        os.path.join(output_dir, "classification.png"),
        "Classification Levels"
    )
    doc_type_exists = plot_pie_chart(
        results["doc_type_count"],
        os.path.join(output_dir, "doc_types.png"),
        "Document Types"
    )
    confidence_exists = plot_confidence_histogram(
        results["confidence_scores"],
        os.path.join(output_dir, "confidence.png")
    )

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
                {"<div class='chart-container'><img src='timeline_yearly.png' alt='Timeline'></div>" if timeline_exists else "<p><em>No valid dates for timeline</em></p>"}

                <h3>Documents by Year</h3>
                {create_table(results['timeline_yearly'], limit=50, id_prefix='timeline_yearly')}
            </section>

            <section id="classification">
                <h2>Classification Levels</h2>
                <div class="two-col">
                    {"<div class='chart-container'><img src='classification.png' alt='Classification'></div>" if classification_exists else ""}
                    <div>
                        {create_table(results['classification_count'], limit=10, id_prefix='classification')}
                    </div>
                </div>
            </section>

            <section id="document-types">
                <h2>Document Types</h2>
                <div class="two-col">
                    {"<div class='chart-container'><img src='doc_types.png' alt='Document Types'></div>" if doc_type_exists else ""}
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

                {"<div class='chart-container'><img src='confidence.png' alt='Confidence Distribution'></div>" if confidence_exists else "<p><em>No confidence data available</em></p>"}

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
    args = parser.parse_args()

    print(f"Processing documents from: {args.directory}")
    results = process_documents(args.directory)
    print(f"Processed {results['total_docs']:,} documents ({results['files_skipped']} files skipped)")

    generate_html_report(results, output_dir=args.output_dir, output_file=args.output)


if __name__ == "__main__":
    main()
