"""
Interactive timeline visualization using Chart.js.

Generates an embeddable HTML/JavaScript timeline with:
- Zoomable/pannable time axis
- Stacked bars by classification level
- Historical event annotations
- Hover tooltips with document counts
"""

import json
from collections import Counter
from typing import Any

from app.visualizations.historical_events import HISTORICAL_EVENTS, get_major_events


# Chart.js CDN URLs (we'll embed these inline for standalone reports)
CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
CHARTJS_ADAPTER_CDN = "https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"
CHARTJS_ZOOM_CDN = "https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"
CHARTJS_ANNOTATION_CDN = "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"

# Classification level colors (consistent with research documentation)
CLASSIFICATION_COLORS = {
    "TOP SECRET": "#8B5CF6",      # Purple
    "SECRET": "#EF4444",          # Red
    "CONFIDENTIAL": "#F59E0B",    # Yellow/Amber
    "LIMITED OFFICIAL USE": "#3B82F6",  # Blue
    "UNCLASSIFIED": "#6B7280",    # Gray
    "Unknown": "#9CA3AF",         # Light gray
}

# Event category colors
EVENT_COLORS = {
    "major": "#DC2626",     # Red - major events
    "moderate": "#2563EB",  # Blue - moderate events
    "minor": "#6B7280",     # Gray - minor events
}


def prepare_timeline_data(
    timeline_yearly: Counter,
    timeline_monthly: Counter | None = None,
    classification_by_year: dict[str, Counter] | None = None,
) -> dict[str, Any]:
    """
    Prepare timeline data for Chart.js visualization.

    Args:
        timeline_yearly: Counter of documents per year
        timeline_monthly: Optional Counter of documents per month (YYYY-MM)
        classification_by_year: Optional dict mapping year to Counter of classifications

    Returns:
        Dictionary with formatted data for Chart.js
    """
    # Sort years chronologically, excluding "Unknown"
    years = sorted([y for y in timeline_yearly.keys() if y != "Unknown" and y.isdigit()])

    # If we have classification breakdown, create stacked data
    if classification_by_year:
        datasets = []
        classifications = ["TOP SECRET", "SECRET", "CONFIDENTIAL",
                          "LIMITED OFFICIAL USE", "UNCLASSIFIED", "Unknown"]

        for classification in classifications:
            data = []
            for year in years:
                year_counts = classification_by_year.get(year, Counter())
                data.append(year_counts.get(classification, 0))

            # Only add dataset if it has any non-zero values
            if any(d > 0 for d in data):
                datasets.append({
                    "label": classification,
                    "data": data,
                    "backgroundColor": CLASSIFICATION_COLORS.get(classification, "#9CA3AF"),
                    "borderColor": CLASSIFICATION_COLORS.get(classification, "#9CA3AF"),
                    "borderWidth": 1,
                })

        return {
            "labels": years,
            "datasets": datasets,
            "stacked": True,
        }
    else:
        # Simple non-stacked data
        data = [timeline_yearly.get(year, 0) for year in years]
        return {
            "labels": years,
            "datasets": [{
                "label": "Documents",
                "data": data,
                "backgroundColor": "#3B82F6",
                "borderColor": "#2563EB",
                "borderWidth": 1,
            }],
            "stacked": False,
        }


def prepare_event_annotations(major_only: bool = False) -> list[dict]:
    """
    Prepare historical event annotations for Chart.js annotation plugin.

    Args:
        major_only: If True, only include major events

    Returns:
        List of annotation configurations
    """
    events = get_major_events() if major_only else HISTORICAL_EVENTS
    annotations = []

    for i, event in enumerate(events):
        year = event.date[:4]

        # Vertical line annotation
        annotations.append({
            "type": "line",
            "xMin": year,
            "xMax": year,
            "borderColor": EVENT_COLORS.get(event.category, "#6B7280"),
            "borderWidth": 2 if event.category == "major" else 1,
            "borderDash": [] if event.category == "major" else [5, 5],
            "label": {
                "display": event.category == "major",  # Only show labels for major events
                "content": event.name,
                "position": "start",
                "backgroundColor": EVENT_COLORS.get(event.category, "#6B7280"),
                "color": "#FFFFFF",
                "font": {"size": 10, "weight": "bold"},
                "padding": 4,
                "rotation": -90,
                "yAdjust": -60 - (i % 3) * 20,  # Stagger labels to avoid overlap
            },
        })

    return annotations


def generate_interactive_timeline(
    timeline_yearly: Counter,
    classification_by_year: dict[str, Counter] | None = None,
    container_id: str = "timeline-chart",
    height: str = "500px",
    include_events: bool = True,
    major_events_only: bool = True,
) -> str:
    """
    Generate HTML/JavaScript for an interactive timeline visualization.

    Args:
        timeline_yearly: Counter of documents per year
        classification_by_year: Optional dict mapping year to Counter of classifications
        container_id: HTML element ID for the chart container
        height: CSS height for the chart container
        include_events: Whether to include historical event annotations
        major_events_only: If True, only annotate major events

    Returns:
        HTML string with embedded JavaScript for the interactive timeline
    """
    # Prepare data
    chart_data = prepare_timeline_data(timeline_yearly, classification_by_year=classification_by_year)

    # Prepare event annotations
    annotations = {}
    if include_events:
        event_annotations = prepare_event_annotations(major_only=major_events_only)
        annotations = {f"event_{i}": ann for i, ann in enumerate(event_annotations)}

    # Prepare events list for JavaScript (must be done outside f-string to avoid parsing issues)
    events_for_js = get_major_events() if major_events_only else HISTORICAL_EVENTS
    events_json = json.dumps([
        {"date": e.date, "name": e.name, "description": e.description, "category": e.category}
        for e in events_for_js
    ])

    # Build the HTML with embedded JavaScript
    html = f'''
<div class="timeline-container" style="width: 100%; height: {height}; position: relative;">
    <canvas id="{container_id}"></canvas>
</div>

<div class="timeline-controls" style="margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
    <button onclick="resetZoom_{container_id.replace('-', '_')}()" class="timeline-btn">
        Reset Zoom
    </button>
    <span style="color: #6B7280; font-size: 12px;">
        Scroll to zoom, drag to pan
    </span>
    <div style="flex: 1;"></div>
    <div class="timeline-legend" style="display: flex; gap: 15px; flex-wrap: wrap;">
        {"".join(f'<span style="display: flex; align-items: center; gap: 4px;"><span style="width: 12px; height: 12px; background: {color}; border-radius: 2px;"></span><span style="font-size: 12px;">{label}</span></span>' for label, color in [("Major Event", EVENT_COLORS["major"]), ("Other Event", EVENT_COLORS["moderate"])] if include_events)}
    </div>
</div>

<style>
.timeline-btn {{
    padding: 6px 12px;
    background: #3B82F6;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}}
.timeline-btn:hover {{
    background: #2563EB;
}}
</style>

<script src="{CHARTJS_CDN}"></script>
<script src="{CHARTJS_ADAPTER_CDN}"></script>
<script src="{CHARTJS_ZOOM_CDN}"></script>
<script src="{CHARTJS_ANNOTATION_CDN}"></script>

<script>
(function() {{
    const ctx = document.getElementById('{container_id}').getContext('2d');

    const chartData = {json.dumps(chart_data)};
    const annotations = {json.dumps(annotations)};
    const events = {events_json};

    const chart_{container_id.replace('-', '_')} = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: chartData.labels,
            datasets: chartData.datasets
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
                mode: 'index',
                intersect: false
            }},
            scales: {{
                x: {{
                    stacked: chartData.stacked,
                    title: {{
                        display: true,
                        text: 'Year',
                        font: {{ size: 14, weight: 'bold' }}
                    }},
                    grid: {{
                        display: false
                    }}
                }},
                y: {{
                    stacked: chartData.stacked,
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Number of Documents',
                        font: {{ size: 14, weight: 'bold' }}
                    }}
                }}
            }},
            plugins: {{
                legend: {{
                    display: chartData.stacked,
                    position: 'bottom',
                    labels: {{
                        usePointStyle: true,
                        padding: 15
                    }}
                }},
                tooltip: {{
                    callbacks: {{
                        afterBody: function(context) {{
                            const year = context[0].label;
                            const yearEvents = events.filter(e => e.date.startsWith(year));
                            if (yearEvents.length > 0) {{
                                return '\\n' + yearEvents.map(e => '• ' + e.name).join('\\n');
                            }}
                            return '';
                        }}
                    }}
                }},
                zoom: {{
                    pan: {{
                        enabled: true,
                        mode: 'x'
                    }},
                    zoom: {{
                        wheel: {{
                            enabled: true
                        }},
                        pinch: {{
                            enabled: true
                        }},
                        mode: 'x'
                    }}
                }},
                annotation: {{
                    annotations: annotations
                }}
            }}
        }}
    }});

    // Export reset function globally
    window.resetZoom_{container_id.replace('-', '_')} = function() {{
        chart_{container_id.replace('-', '_')}.resetZoom();
    }};
}})();
</script>
'''

    return html


def generate_timeline_with_monthly_detail(
    timeline_yearly: Counter,
    timeline_monthly: Counter,
    classification_by_year: dict[str, Counter] | None = None,
    container_id: str = "timeline-chart-detailed",
    height: str = "600px",
) -> str:
    """
    Generate an enhanced timeline with year/month toggle capability.

    This version allows users to switch between yearly and monthly views.
    """
    # Prepare yearly data
    yearly_data = prepare_timeline_data(timeline_yearly, classification_by_year=classification_by_year)

    # Prepare monthly data (sorted chronologically)
    months = sorted([m for m in timeline_monthly.keys() if m != "Unknown"])
    monthly_data = {
        "labels": months,
        "datasets": [{
            "label": "Documents",
            "data": [timeline_monthly[m] for m in months],
            "backgroundColor": "#3B82F6",
            "borderColor": "#2563EB",
            "borderWidth": 1,
        }],
        "stacked": False,
    }

    # Prepare event annotations
    annotations = prepare_event_annotations(major_only=True)
    annotations_dict = {f"event_{i}": ann for i, ann in enumerate(annotations)}

    html = f'''
<div class="timeline-container" style="width: 100%; height: {height}; position: relative;">
    <canvas id="{container_id}"></canvas>
</div>

<div class="timeline-controls" style="margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
    <div class="btn-group" style="display: flex;">
        <button id="{container_id}-yearly-btn" onclick="showYearly_{container_id.replace('-', '_')}()" class="timeline-btn active">
            Yearly
        </button>
        <button id="{container_id}-monthly-btn" onclick="showMonthly_{container_id.replace('-', '_')}()" class="timeline-btn">
            Monthly
        </button>
    </div>
    <button onclick="resetZoom_{container_id.replace('-', '_')}()" class="timeline-btn">
        Reset Zoom
    </button>
    <span style="color: #6B7280; font-size: 12px;">
        Scroll to zoom, drag to pan
    </span>
</div>

<style>
.timeline-btn {{
    padding: 6px 12px;
    background: #E5E7EB;
    color: #374151;
    border: 1px solid #D1D5DB;
    cursor: pointer;
    font-size: 12px;
}}
.timeline-btn:first-child {{
    border-radius: 4px 0 0 4px;
}}
.timeline-btn:last-child {{
    border-radius: 0 4px 4px 0;
}}
.timeline-btn.active {{
    background: #3B82F6;
    color: white;
    border-color: #3B82F6;
}}
.timeline-btn:hover:not(.active) {{
    background: #D1D5DB;
}}
.btn-group .timeline-btn {{
    border-radius: 0;
}}
.btn-group .timeline-btn:first-child {{
    border-radius: 4px 0 0 4px;
}}
.btn-group .timeline-btn:last-child {{
    border-radius: 0 4px 4px 0;
}}
</style>

<script src="{CHARTJS_CDN}"></script>
<script src="{CHARTJS_ADAPTER_CDN}"></script>
<script src="{CHARTJS_ZOOM_CDN}"></script>
<script src="{CHARTJS_ANNOTATION_CDN}"></script>

<script>
(function() {{
    const ctx = document.getElementById('{container_id}').getContext('2d');

    const yearlyData = {json.dumps(yearly_data)};
    const monthlyData = {json.dumps(monthly_data)};
    const annotations = {json.dumps(annotations_dict)};

    let currentView = 'yearly';

    const chart_{container_id.replace('-', '_')} = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: yearlyData.labels,
            datasets: yearlyData.datasets
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            animation: {{ duration: 300 }},
            scales: {{
                x: {{
                    stacked: yearlyData.stacked,
                    title: {{
                        display: true,
                        text: 'Year',
                        font: {{ size: 14, weight: 'bold' }}
                    }}
                }},
                y: {{
                    stacked: yearlyData.stacked,
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Number of Documents',
                        font: {{ size: 14, weight: 'bold' }}
                    }}
                }}
            }},
            plugins: {{
                legend: {{ display: yearlyData.stacked, position: 'bottom' }},
                zoom: {{
                    pan: {{ enabled: true, mode: 'x' }},
                    zoom: {{
                        wheel: {{ enabled: true }},
                        pinch: {{ enabled: true }},
                        mode: 'x'
                    }}
                }},
                annotation: {{ annotations: annotations }}
            }}
        }}
    }});

    window.showYearly_{container_id.replace('-', '_')} = function() {{
        if (currentView === 'yearly') return;
        currentView = 'yearly';
        chart_{container_id.replace('-', '_')}.data.labels = yearlyData.labels;
        chart_{container_id.replace('-', '_')}.data.datasets = yearlyData.datasets;
        chart_{container_id.replace('-', '_')}.options.scales.x.title.text = 'Year';
        chart_{container_id.replace('-', '_')}.options.plugins.annotation.annotations = annotations;
        chart_{container_id.replace('-', '_')}.update();
        document.getElementById('{container_id}-yearly-btn').classList.add('active');
        document.getElementById('{container_id}-monthly-btn').classList.remove('active');
    }};

    window.showMonthly_{container_id.replace('-', '_')} = function() {{
        if (currentView === 'monthly') return;
        currentView = 'monthly';
        chart_{container_id.replace('-', '_')}.data.labels = monthlyData.labels;
        chart_{container_id.replace('-', '_')}.data.datasets = monthlyData.datasets;
        chart_{container_id.replace('-', '_')}.options.scales.x.title.text = 'Month';
        chart_{container_id.replace('-', '_')}.options.plugins.annotation.annotations = {{}};
        chart_{container_id.replace('-', '_')}.update();
        document.getElementById('{container_id}-monthly-btn').classList.add('active');
        document.getElementById('{container_id}-yearly-btn').classList.remove('active');
    }};

    window.resetZoom_{container_id.replace('-', '_')} = function() {{
        chart_{container_id.replace('-', '_')}.resetZoom();
    }};
}})();
</script>
'''

    return html
