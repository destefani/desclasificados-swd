"""
Financial dashboard visualizations.

Generates interactive visualizations for analyzing financial references
from declassified documents, including funding timelines and flow networks.
"""

import json
from collections import Counter
from typing import Any


# Color scheme (green/teal - distinct from red sensitive content)
FINANCIAL_COLORS = {
    "primary": "#10B981",      # Emerald green
    "secondary": "#3B82F6",    # Blue
    "accent": "#F59E0B",       # Amber for highlights
    "neutral": "#6B7280",      # Gray
}

# Purpose category colors for network graph
PURPOSE_COLORS = {
    "ELECTION SUPPORT": "#3B82F6",          # Blue
    "OPPOSITION SUPPORT": "#EF4444",        # Red
    "PROPAGANDA": "#F59E0B",                # Amber
    "MEDIA FUNDING": "#8B5CF6",             # Purple
    "POLITICAL ACTION": "#10B981",          # Green
    "INTELLIGENCE OPERATIONS": "#6366F1",   # Indigo
    "MILITARY AID": "#DC2626",              # Dark red
    "ECONOMIC DESTABILIZATION": "#F97316",  # Orange
    "LABOR UNION SUPPORT": "#14B8A6",       # Teal
    "CIVIC ACTION": "#06B6D4",              # Cyan
    "OTHER": "#6B7280",                     # Gray
}

# CDN URLs (same as other modules)
CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
VISJS_CDN = "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"


def prepare_financial_timeline_data(
    financial_amounts_by_year: dict[str, list[dict]],
) -> dict[str, Any]:
    """
    Prepare data for financial timeline chart.

    Args:
        financial_amounts_by_year: Dict mapping year -> list of amount records
            Each record: {value, normalized_usd, context, doc_id}

    Returns:
        Dictionary with labels and datasets for Chart.js bar chart
        - Stacked: USD amounts (green) + unknown amounts (gray count)
    """
    # Sort years chronologically, excluding Unknown
    years = sorted([y for y in financial_amounts_by_year.keys() if y != "Unknown"])

    if not years:
        return {"labels": [], "datasets": []}

    # Calculate totals per year
    usd_totals = []
    unknown_counts = []

    for year in years:
        amounts = financial_amounts_by_year.get(year, [])
        total_usd = 0
        unknown = 0

        for amount in amounts:
            normalized = amount.get("normalized_usd")
            if normalized is not None and isinstance(normalized, (int, float)):
                total_usd += normalized
            else:
                unknown += 1

        usd_totals.append(total_usd)
        unknown_counts.append(unknown)

    datasets = [
        {
            "label": "Total USD",
            "data": usd_totals,
            "backgroundColor": FINANCIAL_COLORS["primary"] + "CC",
            "borderColor": FINANCIAL_COLORS["primary"],
            "borderWidth": 1,
            "yAxisID": "y",
        },
        {
            "label": "Unknown Amount Documents",
            "data": unknown_counts,
            "backgroundColor": FINANCIAL_COLORS["neutral"] + "99",
            "borderColor": FINANCIAL_COLORS["neutral"],
            "borderWidth": 1,
            "yAxisID": "y1",
        },
    ]

    return {
        "labels": years,
        "datasets": datasets,
    }


def build_financial_flow_network(
    financial_actors_count: Counter,
    financial_purposes_count: Counter,
    financial_actor_purpose_links: list[dict],
    max_nodes: int = 50,
    min_mentions: int = 1,
) -> dict[str, Any]:
    """
    Build network data for Actor -> Purpose flow visualization.

    Nodes are bipartite: actors (left, green) and purposes (right, colored by type).
    Edges connect actors to purposes they funded in the same documents.

    Returns:
        Dictionary with nodes and edges for vis.js
    """
    # Filter actors by minimum mentions
    filtered_actors = {k: v for k, v in financial_actors_count.items() if v >= min_mentions}
    filtered_purposes = {k: v for k, v in financial_purposes_count.items() if v >= min_mentions}

    # Sort and limit - split max_nodes between actors and purposes
    max_actors = max_nodes // 2
    max_purposes = max_nodes - max_actors
    top_actors = sorted(filtered_actors.items(), key=lambda x: x[1], reverse=True)[:max_actors]
    top_purposes = sorted(filtered_purposes.items(), key=lambda x: x[1], reverse=True)[:max_purposes]

    # Create node ID mappings
    nodes = []
    actor_to_id = {}
    purpose_to_id = {}

    # Actor nodes (group 0 - left side)
    for i, (name, count) in enumerate(top_actors):
        actor_to_id[name] = i
        max_count = top_actors[0][1] if top_actors else 1
        size = max(20, min(50, 20 + (count / max_count) * 30))

        nodes.append({
            "id": i,
            "label": name,
            "value": count,
            "title": f"{name}\\nDocuments: {count}",
            "color": {
                "background": FINANCIAL_COLORS["primary"],
                "border": FINANCIAL_COLORS["primary"],
                "highlight": {"background": "#059669", "border": "#047857"},
            },
            "font": {"size": 11},
            "group": "actor",
            "level": 0,
        })

    # Purpose nodes (group 1 - right side)
    purpose_start_id = len(top_actors)
    for i, (name, count) in enumerate(top_purposes):
        node_id = purpose_start_id + i
        purpose_to_id[name] = node_id
        color = PURPOSE_COLORS.get(name, PURPOSE_COLORS["OTHER"])
        max_count = top_purposes[0][1] if top_purposes else 1
        size = max(20, min(50, 20 + (count / max_count) * 30))

        nodes.append({
            "id": node_id,
            "label": name,
            "value": count,
            "title": f"{name}\\nDocuments: {count}",
            "color": {
                "background": color,
                "border": color,
                "highlight": {"background": "#10B981", "border": "#059669"},
            },
            "font": {"size": 11},
            "group": "purpose",
            "level": 1,
        })

    # Count edges from links
    edge_counts: dict[tuple[str, str], int] = {}
    for link in financial_actor_purpose_links:
        actor = link.get("actor", "")
        purpose = link.get("purpose", "")
        if actor in actor_to_id and purpose in purpose_to_id:
            key = (actor, purpose)
            edge_counts[key] = edge_counts.get(key, 0) + 1

    # Create edges
    edges = []
    for i, ((actor, purpose), count) in enumerate(edge_counts.items()):
        edges.append({
            "id": i,
            "from": actor_to_id[actor],
            "to": purpose_to_id[purpose],
            "value": count,
            "title": f"{count} documents",
            "color": {"color": "#9CA3AF", "highlight": "#10B981"},
            "arrows": "to",
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "actor_to_id": actor_to_id,
        "purpose_to_id": purpose_to_id,
    }


def generate_financial_summary_cards(
    docs_with_financial: int,
    total_docs: int,
    financial_amounts: list[dict],
    financial_actors_count: Counter,
    financial_purposes_count: Counter,
) -> str:
    """
    Generate summary cards for financial content statistics.

    Cards include:
    - Total documents with financial content
    - Total USD (where normalized)
    - Unique actors count
    - Most common purpose

    Returns:
        HTML string with summary cards
    """
    def pct(part: int, total: int) -> str:
        if total == 0:
            return "0%"
        return f"{part/total*100:.1f}%"

    def format_usd(amount: float) -> str:
        if amount >= 1_000_000_000:
            return f"${amount/1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.1f}K"
        else:
            return f"${amount:,.0f}"

    # Calculate total USD
    total_usd = 0
    known_amounts = 0
    for amount in financial_amounts:
        normalized = amount.get("normalized_usd")
        if normalized is not None and isinstance(normalized, (int, float)):
            total_usd += normalized
            known_amounts += 1

    # Get top purpose
    top_purpose = financial_purposes_count.most_common(1)
    top_purpose_name = top_purpose[0][0] if top_purpose else "N/A"
    top_purpose_count = top_purpose[0][1] if top_purpose else 0

    # Unique actors
    unique_actors = len(financial_actors_count)

    html = f'''
<div class="financial-summary-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px;">
    <div class="summary-card" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {FINANCIAL_COLORS['primary']}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Documents</h4>
        <div style="font-size: 1.8rem; font-weight: bold; color: {FINANCIAL_COLORS['primary']};">{docs_with_financial:,}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">{pct(docs_with_financial, total_docs)} of total</div>
    </div>
    <div class="summary-card" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {FINANCIAL_COLORS['secondary']}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Total USD</h4>
        <div style="font-size: 1.8rem; font-weight: bold; color: {FINANCIAL_COLORS['secondary']};">{format_usd(total_usd)}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">{known_amounts:,} amounts normalized</div>
    </div>
    <div class="summary-card" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {FINANCIAL_COLORS['accent']}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Financial Actors</h4>
        <div style="font-size: 1.8rem; font-weight: bold; color: {FINANCIAL_COLORS['accent']};">{unique_actors:,}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">unique organizations</div>
    </div>
    <div class="summary-card" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {FINANCIAL_COLORS['neutral']}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Top Purpose</h4>
        <div style="font-size: 1.2rem; font-weight: bold; color: #374151;">{top_purpose_name}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">{top_purpose_count:,} documents</div>
    </div>
</div>
'''
    return html


def generate_financial_timeline(
    financial_amounts_by_year: dict[str, list[dict]],
    container_id: str = "financial-timeline",
    height: str = "400px",
) -> str:
    """
    Generate Chart.js bar chart showing financial amounts over time.

    Features:
    - Dual axis: USD amounts (left) vs document count (right)
    - Hover tooltips with amount details

    Returns:
        HTML string with embedded JavaScript
    """
    timeline_data = prepare_financial_timeline_data(financial_amounts_by_year)

    if not timeline_data["labels"]:
        return "<p><em>No financial timeline data available</em></p>"

    labels_json = json.dumps(timeline_data["labels"])
    datasets_json = json.dumps(timeline_data["datasets"])

    func_name = container_id.replace('-', '_')

    html = f'''
<div class="financial-timeline-section">
    <div class="timeline-legend" style="display: flex; gap: 15px; margin-bottom: 10px;">
        <span style="display: flex; align-items: center; gap: 4px;">
            <span style="width: 12px; height: 12px; background: {FINANCIAL_COLORS['primary']}; border-radius: 2px;"></span>
            <span style="font-size: 12px;">Total USD (left axis)</span>
        </span>
        <span style="display: flex; align-items: center; gap: 4px;">
            <span style="width: 12px; height: 12px; background: {FINANCIAL_COLORS['neutral']}; border-radius: 2px;"></span>
            <span style="font-size: 12px;">Documents with unknown amounts (right axis)</span>
        </span>
    </div>

    <div style="position: relative; height: {height}; width: 100%;">
        <canvas id="{container_id}"></canvas>
    </div>
</div>

<script src="{CHARTJS_CDN}"></script>

<script>
(function() {{
    const ctx = document.getElementById('{container_id}').getContext('2d');
    new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: {labels_json},
            datasets: {datasets_json}
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                title: {{
                    display: true,
                    text: 'Financial References Over Time',
                    font: {{ size: 16 }}
                }},
                legend: {{
                    display: false
                }},
                tooltip: {{
                    callbacks: {{
                        label: function(context) {{
                            if (context.datasetIndex === 0) {{
                                return 'Total: $' + context.raw.toLocaleString();
                            }} else {{
                                return context.raw + ' documents (unknown USD)';
                            }}
                        }}
                    }}
                }}
            }},
            scales: {{
                x: {{
                    title: {{
                        display: true,
                        text: 'Year'
                    }}
                }},
                y: {{
                    type: 'linear',
                    position: 'left',
                    title: {{
                        display: true,
                        text: 'Total USD'
                    }},
                    beginAtZero: true,
                    ticks: {{
                        callback: function(value) {{
                            if (value >= 1000000) {{
                                return '$' + (value / 1000000).toFixed(1) + 'M';
                            }} else if (value >= 1000) {{
                                return '$' + (value / 1000).toFixed(0) + 'K';
                            }}
                            return '$' + value;
                        }}
                    }}
                }},
                y1: {{
                    type: 'linear',
                    position: 'right',
                    title: {{
                        display: true,
                        text: 'Documents'
                    }},
                    beginAtZero: true,
                    grid: {{
                        drawOnChartArea: false
                    }}
                }}
            }}
        }}
    }});
}})();
</script>
'''
    return html


def generate_financial_flow_network(
    financial_actors_count: Counter,
    financial_purposes_count: Counter,
    financial_actor_purpose_links: list[dict],
    container_id: str = "financial-flow-network",
    height: str = "500px",
    max_nodes: int = 50,
    min_mentions: int = 1,
) -> str:
    """
    Generate vis.js directed graph showing Actor -> Purpose relationships.

    Layout:
    - Actors on left (green nodes)
    - Purposes on right (colored by category)
    - Edges show funding relationships
    - Edge width proportional to document count

    Returns:
        HTML string with embedded JavaScript
    """
    network_data = build_financial_flow_network(
        financial_actors_count=financial_actors_count,
        financial_purposes_count=financial_purposes_count,
        financial_actor_purpose_links=financial_actor_purpose_links,
        max_nodes=max_nodes,
        min_mentions=min_mentions,
    )

    if not network_data["nodes"]:
        return "<p><em>No financial network data available</em></p>"

    nodes_json = json.dumps(network_data["nodes"])
    edges_json = json.dumps(network_data["edges"])
    func_name = container_id.replace('-', '_')

    html = f'''
<div class="network-section">
    <div class="network-controls" style="margin-bottom: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
        <button onclick="togglePhysics_{func_name}()" class="network-btn" id="{container_id}-physics-btn">
            Pause Physics
        </button>
        <button onclick="resetNetwork_{func_name}()" class="network-btn">
            Reset View
        </button>
        <span style="color: #6B7280; font-size: 12px;">
            Actors (left) → Purposes (right). Drag to explore.
        </span>
        <div style="flex: 1;"></div>
        <div class="network-legend" style="display: flex; gap: 15px; flex-wrap: wrap;">
            <span style="display: flex; align-items: center; gap: 4px;">
                <span style="width: 12px; height: 12px; background: {FINANCIAL_COLORS['primary']}; border-radius: 50%;"></span>
                <span style="font-size: 12px;">Financial Actor</span>
            </span>
            <span style="display: flex; align-items: center; gap: 4px;">
                <span style="width: 12px; height: 12px; background: {PURPOSE_COLORS['POLITICAL ACTION']}; border-radius: 50%;"></span>
                <span style="font-size: 12px;">Purpose</span>
            </span>
        </div>
    </div>

    <div id="{container_id}" style="width: 100%; max-width: 100%; height: {height}; border: 1px solid #E5E7EB; border-radius: 8px; background: #FAFAFA; overflow: hidden;"></div>

    <div id="{container_id}-info" class="network-info" style="margin-top: 10px; padding: 10px; background: #F3F4F6; border-radius: 4px; display: none;">
        <strong>Selected:</strong> <span id="{container_id}-selected-name">-</span><br>
        <strong>Type:</strong> <span id="{container_id}-selected-type">-</span><br>
        <strong>Connections:</strong> <span id="{container_id}-selected-connections">-</span>
    </div>
</div>

<style>
.network-btn {{
    padding: 6px 12px;
    background: #E5E7EB;
    color: #374151;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}}
.network-btn:hover {{
    background: #D1D5DB;
}}
</style>

<script src="{VISJS_CDN}"></script>

<script>
(function() {{
    const nodes = new vis.DataSet({nodes_json});
    const edges = new vis.DataSet({edges_json});

    const container = document.getElementById('{container_id}');
    const data = {{ nodes: nodes, edges: edges }};

    const options = {{
        nodes: {{
            shape: 'dot',
            scaling: {{
                min: 20,
                max: 50,
                label: {{
                    enabled: true,
                    min: 10,
                    max: 16
                }}
            }},
            font: {{
                size: 11,
                face: 'Arial'
            }}
        }},
        edges: {{
            width: 1,
            scaling: {{
                min: 1,
                max: 8
            }},
            smooth: {{
                type: 'curvedCW',
                roundness: 0.2
            }},
            arrows: {{
                to: {{ enabled: true, scaleFactor: 0.5 }}
            }}
        }},
        layout: {{
            hierarchical: {{
                enabled: true,
                direction: 'LR',
                sortMethod: 'directed',
                nodeSpacing: 80,
                levelSeparation: 250
            }}
        }},
        physics: {{
            enabled: false
        }},
        interaction: {{
            hover: true,
            tooltipDelay: 200
        }}
    }};

    const network_{func_name} = new vis.Network(container, data, options);

    let physicsEnabled = false;

    network_{func_name}.on('selectNode', function(params) {{
        if (params.nodes.length > 0) {{
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            const connectedEdges = network_{func_name}.getConnectedEdges(nodeId);

            document.getElementById('{container_id}-info').style.display = 'block';
            document.getElementById('{container_id}-selected-name').textContent = node.label;
            document.getElementById('{container_id}-selected-type').textContent = node.group === 'actor' ? 'Financial Actor' : 'Funding Purpose';
            document.getElementById('{container_id}-selected-connections').textContent = connectedEdges.length;
        }}
    }});

    network_{func_name}.on('deselectNode', function() {{
        document.getElementById('{container_id}-info').style.display = 'none';
    }});

    window.togglePhysics_{func_name} = function() {{
        physicsEnabled = !physicsEnabled;
        network_{func_name}.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        document.getElementById('{container_id}-physics-btn').textContent = physicsEnabled ? 'Pause Physics' : 'Enable Physics';
    }};

    window.resetNetwork_{func_name} = function() {{
        network_{func_name}.fit();
    }};
}})();
</script>
'''
    return html


def generate_financial_purposes_chart(
    financial_purposes_count: Counter,
    container_id: str = "financial-purposes-chart",
    height: str = "300px",
) -> str:
    """
    Generate Chart.js doughnut chart of funding purposes.

    Returns:
        HTML string with embedded JavaScript
    """
    if not financial_purposes_count:
        return "<p><em>No funding purpose data available</em></p>"

    # Get all purposes sorted by count
    purposes = financial_purposes_count.most_common()

    labels = [item[0] for item in purposes]
    data = [item[1] for item in purposes]
    colors = [PURPOSE_COLORS.get(label, PURPOSE_COLORS["OTHER"]) for label in labels]

    labels_json = json.dumps(labels)
    data_json = json.dumps(data)
    colors_json = json.dumps(colors)

    html = f'''
<div style="position: relative; height: {height}; width: 100%; max-width: 500px; margin: 0 auto;">
    <canvas id="{container_id}"></canvas>
</div>

<script>
(function() {{
    const ctx = document.getElementById('{container_id}').getContext('2d');
    new Chart(ctx, {{
        type: 'doughnut',
        data: {{
            labels: {labels_json},
            datasets: [{{
                data: {data_json},
                backgroundColor: {colors_json},
                borderColor: '#ffffff',
                borderWidth: 2
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                title: {{
                    display: true,
                    text: 'Funding Purposes',
                    font: {{ size: 14 }}
                }},
                legend: {{
                    position: 'right',
                    labels: {{
                        boxWidth: 12,
                        padding: 8,
                        font: {{ size: 11 }}
                    }}
                }},
                tooltip: {{
                    callbacks: {{
                        label: function(context) {{
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return context.label + ': ' + context.raw + ' (' + percentage + '%)';
                        }}
                    }}
                }}
            }}
        }}
    }});
}})();
</script>
'''
    return html


def generate_financial_actors_chart(
    financial_actors_count: Counter,
    container_id: str = "financial-actors-chart",
    height: str = "400px",
    max_items: int = 15,
) -> str:
    """
    Generate Chart.js horizontal bar chart of top financial actors.

    Returns:
        HTML string with embedded JavaScript
    """
    if not financial_actors_count:
        return "<p><em>No financial actor data available</em></p>"

    # Get top actors
    top_actors = financial_actors_count.most_common(max_items)

    labels = [item[0] for item in top_actors]
    data = [item[1] for item in top_actors]

    labels_json = json.dumps(labels)
    data_json = json.dumps(data)

    html = f'''
<div style="position: relative; height: {height}; width: 100%;">
    <canvas id="{container_id}"></canvas>
</div>

<script>
(function() {{
    const ctx = document.getElementById('{container_id}').getContext('2d');
    new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: {labels_json},
            datasets: [{{
                label: 'Documents',
                data: {data_json},
                backgroundColor: '{FINANCIAL_COLORS["primary"]}99',
                borderColor: '{FINANCIAL_COLORS["primary"]}',
                borderWidth: 1
            }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                title: {{
                    display: true,
                    text: 'Top Financial Actors',
                    font: {{ size: 14 }}
                }},
                legend: {{
                    display: false
                }}
            }},
            scales: {{
                x: {{
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Number of Documents'
                    }}
                }}
            }}
        }}
    }});
}})();
</script>
'''
    return html
