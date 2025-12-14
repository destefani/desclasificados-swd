"""
Sensitive content dashboard visualizations.

Generates interactive visualizations for analyzing violence, torture,
and disappearance data from declassified documents.
"""

import json
from collections import Counter
from typing import Any


# Colors for sensitive content categories
SENSITIVE_COLORS = {
    "violence": "#DC2626",      # Red
    "torture": "#7C3AED",       # Purple
    "disappearance": "#0891B2", # Cyan
}

# Chart.js is loaded by the main timeline - no need to load again

# vis.js CDN (same as network graph)
VISJS_CDN = "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"


def prepare_sensitive_timeline_data(
    sensitive_content_by_year: dict[str, dict[str, int]],
) -> dict[str, Any]:
    """
    Prepare data for sensitive content timeline chart.

    Args:
        sensitive_content_by_year: Dict mapping year -> {violence, torture, disappearance counts}

    Returns:
        Dictionary with labels and datasets for Chart.js
    """
    # Sort years chronologically, excluding Unknown
    years = sorted([y for y in sensitive_content_by_year.keys() if y != "Unknown"])

    if not years:
        return {"labels": [], "datasets": []}

    # Build datasets for each content type
    datasets = []

    for content_type, color in SENSITIVE_COLORS.items():
        data = [sensitive_content_by_year.get(year, {}).get(content_type, 0) for year in years]
        datasets.append({
            "label": content_type.title(),
            "data": data,
            "borderColor": color,
            "backgroundColor": color + "99",  # Semi-transparent fill
            "borderWidth": 2,
        })

    return {
        "labels": years,
        "datasets": datasets,
    }


def generate_sensitive_timeline(
    sensitive_content_by_year: dict[str, dict[str, int]],
    container_id: str = "sensitive-timeline",
    height: str = "400px",
    include_events: bool = True,
) -> str:
    """
    Generate an interactive timeline showing sensitive content over time.

    Args:
        sensitive_content_by_year: Dict mapping year -> content type counts
        container_id: HTML element ID
        height: CSS height for the container
        include_events: Whether to show historical event annotations (unused, kept for API compat)

    Returns:
        HTML string with embedded JavaScript
    """
    # Prepare data
    timeline_data = prepare_sensitive_timeline_data(sensitive_content_by_year)

    if not timeline_data["labels"]:
        return "<p><em>No sensitive content data available for timeline</em></p>"

    labels_json = json.dumps(timeline_data["labels"])
    datasets_json = json.dumps(timeline_data["datasets"])

    func_name = container_id.replace('-', '_')

    html = f'''
<div class="sensitive-timeline-section">
    <div class="timeline-legend" style="display: flex; gap: 15px; margin-bottom: 10px;">
        <span style="display: flex; align-items: center; gap: 4px;">
            <span style="width: 12px; height: 12px; background: {SENSITIVE_COLORS['violence']}; border-radius: 2px;"></span>
            <span style="font-size: 12px;">Violence</span>
        </span>
        <span style="display: flex; align-items: center; gap: 4px;">
            <span style="width: 12px; height: 12px; background: {SENSITIVE_COLORS['torture']}; border-radius: 2px;"></span>
            <span style="font-size: 12px;">Torture</span>
        </span>
        <span style="display: flex; align-items: center; gap: 4px;">
            <span style="width: 12px; height: 12px; background: {SENSITIVE_COLORS['disappearance']}; border-radius: 2px;"></span>
            <span style="font-size: 12px;">Disappearance</span>
        </span>
    </div>

    <div style="position: relative; height: {height}; width: 100%;">
        <canvas id="{container_id}"></canvas>
    </div>
</div>

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
                    text: 'Sensitive Content in Documents Over Time',
                    font: {{ size: 16 }}
                }},
                legend: {{
                    display: false
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
                    title: {{
                        display: true,
                        text: 'Documents'
                    }},
                    beginAtZero: true
                }}
            }}
        }}
    }});
}})();
</script>
'''
    return html


def build_perpetrator_victim_network(
    violence_victims: Counter,
    violence_perpetrators: Counter,
    torture_victims: Counter,
    torture_perpetrators: Counter,
    disappearance_victims: Counter,
    disappearance_perpetrators: Counter,
    violence_victim_docs: dict[str, list] | None = None,
    violence_perp_docs: dict[str, list] | None = None,
    torture_victim_docs: dict[str, list] | None = None,
    torture_perp_docs: dict[str, list] | None = None,
    disappearance_victim_docs: dict[str, list] | None = None,
    disappearance_perp_docs: dict[str, list] | None = None,
    max_nodes: int = 100,
    min_mentions: int = 2,
) -> dict[str, Any]:
    """
    Build network data connecting perpetrators and victims.

    Nodes represent individuals, colored by role (perpetrator/victim/both).
    Edges connect perpetrators to victims who appear in the same documents.

    Returns:
        Dictionary with nodes and edges for vis.js
    """
    # Combine all victims and perpetrators
    all_victims: Counter = Counter()
    all_perpetrators: Counter = Counter()

    all_victims.update(violence_victims)
    all_victims.update(torture_victims)
    all_victims.update(disappearance_victims)

    all_perpetrators.update(violence_perpetrators)
    all_perpetrators.update(torture_perpetrators)
    all_perpetrators.update(disappearance_perpetrators)

    # Filter by minimum mentions
    filtered_victims = {k: v for k, v in all_victims.items() if v >= min_mentions}
    filtered_perps = {k: v for k, v in all_perpetrators.items() if v >= min_mentions}

    # Build combined entity set with roles
    entities: dict[str, dict] = {}

    for name, count in filtered_victims.items():
        entities[name] = {"victim_count": count, "perp_count": 0}

    for name, count in filtered_perps.items():
        if name in entities:
            entities[name]["perp_count"] = count
        else:
            entities[name] = {"victim_count": 0, "perp_count": count}

    # Sort by total mentions and limit
    sorted_entities = sorted(
        entities.items(),
        key=lambda x: x[1]["victim_count"] + x[1]["perp_count"],
        reverse=True
    )[:max_nodes]

    # Create nodes
    nodes = []
    entity_to_id = {}

    for i, (name, data) in enumerate(sorted_entities):
        entity_to_id[name] = i
        victim_count = data["victim_count"]
        perp_count = data["perp_count"]
        total = victim_count + perp_count

        # Determine node color based on role
        if victim_count > 0 and perp_count > 0:
            color = "#F59E0B"  # Amber - both roles
            role = "Both"
        elif perp_count > 0:
            color = "#DC2626"  # Red - perpetrator
            role = "Perpetrator"
        else:
            color = "#3B82F6"  # Blue - victim
            role = "Victim"

        # Node size based on total mentions
        max_total = max(e[1]["victim_count"] + e[1]["perp_count"] for e in sorted_entities) or 1
        size = max(15, min(50, 15 + (total / max_total) * 35))

        nodes.append({
            "id": i,
            "label": name,
            "value": total,
            "title": f"{name}\\nRole: {role}\\nAs victim: {victim_count}\\nAs perpetrator: {perp_count}",
            "color": {
                "background": color,
                "border": color,
                "highlight": {"background": "#10B981", "border": "#059669"},
            },
            "font": {"size": 11},
            "role": role,
        })

    # Build edges from document co-occurrence
    # Connect perpetrators to victims who appear in the same documents
    edges = []
    edge_id = 0

    # Collect all doc mappings
    all_victim_docs = {}
    all_perp_docs = {}

    if violence_victim_docs:
        for name, docs in violence_victim_docs.items():
            if name not in all_victim_docs:
                all_victim_docs[name] = set()
            all_victim_docs[name].update(d[0] for d in docs)  # doc_id is first element

    if torture_victim_docs:
        for name, docs in torture_victim_docs.items():
            if name not in all_victim_docs:
                all_victim_docs[name] = set()
            all_victim_docs[name].update(d[0] for d in docs)

    if disappearance_victim_docs:
        for name, docs in disappearance_victim_docs.items():
            if name not in all_victim_docs:
                all_victim_docs[name] = set()
            all_victim_docs[name].update(d[0] for d in docs)

    if violence_perp_docs:
        for name, docs in violence_perp_docs.items():
            if name not in all_perp_docs:
                all_perp_docs[name] = set()
            all_perp_docs[name].update(d[0] for d in docs)

    if torture_perp_docs:
        for name, docs in torture_perp_docs.items():
            if name not in all_perp_docs:
                all_perp_docs[name] = set()
            all_perp_docs[name].update(d[0] for d in docs)

    if disappearance_perp_docs:
        for name, docs in disappearance_perp_docs.items():
            if name not in all_perp_docs:
                all_perp_docs[name] = set()
            all_perp_docs[name].update(d[0] for d in docs)

    # Create edges between perpetrators and victims in same documents
    for perp_name, perp_docs in all_perp_docs.items():
        if perp_name not in entity_to_id:
            continue
        for victim_name, victim_docs in all_victim_docs.items():
            if victim_name not in entity_to_id:
                continue
            if perp_name == victim_name:
                continue

            shared = perp_docs & victim_docs
            if len(shared) >= 1:
                edges.append({
                    "id": edge_id,
                    "from": entity_to_id[perp_name],
                    "to": entity_to_id[victim_name],
                    "value": len(shared),
                    "title": f"{len(shared)} shared documents",
                    "color": {"color": "#9CA3AF", "highlight": "#10B981"},
                    "arrows": "to",
                })
                edge_id += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "entity_to_id": entity_to_id,
    }


def generate_perpetrator_victim_network(
    violence_victims: Counter,
    violence_perpetrators: Counter,
    torture_victims: Counter,
    torture_perpetrators: Counter,
    disappearance_victims: Counter,
    disappearance_perpetrators: Counter,
    violence_victim_docs: dict[str, list] | None = None,
    violence_perp_docs: dict[str, list] | None = None,
    torture_victim_docs: dict[str, list] | None = None,
    torture_perp_docs: dict[str, list] | None = None,
    disappearance_victim_docs: dict[str, list] | None = None,
    disappearance_perp_docs: dict[str, list] | None = None,
    container_id: str = "perp-victim-network",
    height: str = "600px",
    max_nodes: int = 75,
    min_mentions: int = 2,
) -> str:
    """
    Generate an interactive perpetrator-victim network graph.

    Args:
        *_victims: Counter of victim names by category
        *_perpetrators: Counter of perpetrator names by category
        *_docs: Optional document mappings for edge creation
        container_id: HTML element ID
        height: CSS height
        max_nodes: Maximum nodes to display
        min_mentions: Minimum mentions to include

    Returns:
        HTML string with embedded JavaScript
    """
    network_data = build_perpetrator_victim_network(
        violence_victims=violence_victims,
        violence_perpetrators=violence_perpetrators,
        torture_victims=torture_victims,
        torture_perpetrators=torture_perpetrators,
        disappearance_victims=disappearance_victims,
        disappearance_perpetrators=disappearance_perpetrators,
        violence_victim_docs=violence_victim_docs,
        violence_perp_docs=violence_perp_docs,
        torture_victim_docs=torture_victim_docs,
        torture_perp_docs=torture_perp_docs,
        disappearance_victim_docs=disappearance_victim_docs,
        disappearance_perp_docs=disappearance_perp_docs,
        max_nodes=max_nodes,
        min_mentions=min_mentions,
    )

    if not network_data["nodes"]:
        return "<p><em>No perpetrator-victim network data available</em></p>"

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
            Arrows point from perpetrators to victims. Drag to explore.
        </span>
        <div style="flex: 1;"></div>
        <div class="network-legend" style="display: flex; gap: 15px; flex-wrap: wrap;">
            <span style="display: flex; align-items: center; gap: 4px;">
                <span style="width: 12px; height: 12px; background: #DC2626; border-radius: 50%;"></span>
                <span style="font-size: 12px;">Perpetrator</span>
            </span>
            <span style="display: flex; align-items: center; gap: 4px;">
                <span style="width: 12px; height: 12px; background: #3B82F6; border-radius: 50%;"></span>
                <span style="font-size: 12px;">Victim</span>
            </span>
            <span style="display: flex; align-items: center; gap: 4px;">
                <span style="width: 12px; height: 12px; background: #F59E0B; border-radius: 50%;"></span>
                <span style="font-size: 12px;">Both</span>
            </span>
        </div>
    </div>

    <div id="{container_id}" style="width: 100%; max-width: 100%; height: {height}; border: 1px solid #E5E7EB; border-radius: 8px; background: #FAFAFA; overflow: hidden;"></div>

    <div id="{container_id}-info" class="network-info" style="margin-top: 10px; padding: 10px; background: #F3F4F6; border-radius: 4px; display: none;">
        <strong>Selected:</strong> <span id="{container_id}-selected-name">-</span><br>
        <strong>Role:</strong> <span id="{container_id}-selected-role">-</span><br>
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
                min: 15,
                max: 50,
                label: {{
                    enabled: true,
                    min: 10,
                    max: 18
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
                max: 5
            }},
            smooth: {{
                type: 'continuous'
            }},
            arrows: {{
                to: {{ enabled: true, scaleFactor: 0.5 }}
            }}
        }},
        physics: {{
            enabled: true,
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {{
                gravitationalConstant: -30,
                centralGravity: 0.005,
                springLength: 150,
                springConstant: 0.05
            }},
            stabilization: {{
                iterations: 150,
                fit: true
            }}
        }},
        interaction: {{
            hover: true,
            tooltipDelay: 200,
            hideEdgesOnDrag: true
        }}
    }};

    const network_{func_name} = new vis.Network(container, data, options);

    let physicsEnabled = true;

    network_{func_name}.on('selectNode', function(params) {{
        if (params.nodes.length > 0) {{
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            const connectedEdges = network_{func_name}.getConnectedEdges(nodeId);

            document.getElementById('{container_id}-info').style.display = 'block';
            document.getElementById('{container_id}-selected-name').textContent = node.label;
            document.getElementById('{container_id}-selected-role').textContent = node.role;
            document.getElementById('{container_id}-selected-connections').textContent = connectedEdges.length;
        }}
    }});

    network_{func_name}.on('deselectNode', function() {{
        document.getElementById('{container_id}-info').style.display = 'none';
    }});

    window.togglePhysics_{func_name} = function() {{
        physicsEnabled = !physicsEnabled;
        network_{func_name}.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        document.getElementById('{container_id}-physics-btn').textContent = physicsEnabled ? 'Pause Physics' : 'Resume Physics';
    }};

    window.resetNetwork_{func_name} = function() {{
        network_{func_name}.fit();
    }};
}})();
</script>
'''
    return html


def generate_incident_types_chart(
    violence_incident_types: Counter,
    torture_methods: Counter,
    container_id: str = "incident-types-chart",
    height: str = "400px",
    max_items: int = 15,
) -> str:
    """
    Generate a horizontal bar chart showing incident types and torture methods.

    Args:
        violence_incident_types: Counter of violence incident types
        torture_methods: Counter of torture methods mentioned
        container_id: HTML element ID
        height: CSS height
        max_items: Maximum items per category

    Returns:
        HTML string with embedded JavaScript
    """
    # Get top items from each category
    top_incidents = violence_incident_types.most_common(max_items)
    top_methods = torture_methods.most_common(max_items)

    if not top_incidents and not top_methods:
        return "<p><em>No incident type data available</em></p>"

    # Prepare data for dual chart
    incident_labels = [item[0] for item in top_incidents]
    incident_data = [item[1] for item in top_incidents]

    method_labels = [item[0] for item in top_methods]
    method_data = [item[1] for item in top_methods]

    incident_labels_json = json.dumps(incident_labels)
    incident_data_json = json.dumps(incident_data)
    method_labels_json = json.dumps(method_labels)
    method_data_json = json.dumps(method_data)

    func_name = container_id.replace('-', '_')

    html = f'''
<div class="incident-charts" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 100%; overflow: hidden;">
    <div style="position: relative; height: {height}; min-width: 0;">
        <canvas id="{container_id}-incidents"></canvas>
    </div>
    <div style="position: relative; height: {height}; min-width: 0;">
        <canvas id="{container_id}-methods"></canvas>
    </div>
</div>

<script>
(function() {{
    // Violence Incident Types Chart
    const incidentCtx = document.getElementById('{container_id}-incidents').getContext('2d');
    new Chart(incidentCtx, {{
        type: 'bar',
        data: {{
            labels: {incident_labels_json},
            datasets: [{{
                label: 'Documents',
                data: {incident_data_json},
                backgroundColor: '{SENSITIVE_COLORS["violence"]}99',
                borderColor: '{SENSITIVE_COLORS["violence"]}',
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
                    text: 'Violence Incident Types',
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

    // Torture Methods Chart
    const methodCtx = document.getElementById('{container_id}-methods').getContext('2d');
    new Chart(methodCtx, {{
        type: 'bar',
        data: {{
            labels: {method_labels_json},
            datasets: [{{
                label: 'Documents',
                data: {method_data_json},
                backgroundColor: '{SENSITIVE_COLORS["torture"]}99',
                borderColor: '{SENSITIVE_COLORS["torture"]}',
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
                    text: 'Torture Methods Mentioned',
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


def generate_sensitive_summary_cards(
    docs_with_violence: int,
    docs_with_torture: int,
    docs_with_disappearance: int,
    total_docs: int,
    violence_victims: Counter,
    torture_victims: Counter,
    disappearance_victims: Counter,
    violence_perpetrators: Counter,
    torture_perpetrators: Counter,
    disappearance_perpetrators: Counter,
) -> str:
    """
    Generate summary cards for sensitive content statistics.

    Returns:
        HTML string with summary cards
    """
    def pct(part: int, total: int) -> str:
        if total == 0:
            return "0%"
        return f"{part/total*100:.1f}%"

    total_victims = len(set(violence_victims.keys()) | set(torture_victims.keys()) | set(disappearance_victims.keys()))
    total_perps = len(set(violence_perpetrators.keys()) | set(torture_perpetrators.keys()) | set(disappearance_perpetrators.keys()))

    html = f'''
<div class="sensitive-summary-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px;">
    <div class="summary-card danger" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {SENSITIVE_COLORS['violence']}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Violence</h4>
        <div style="font-size: 1.8rem; font-weight: bold; color: {SENSITIVE_COLORS['violence']};">{docs_with_violence:,}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">{pct(docs_with_violence, total_docs)} of documents</div>
    </div>
    <div class="summary-card danger" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {SENSITIVE_COLORS['torture']}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Torture</h4>
        <div style="font-size: 1.8rem; font-weight: bold; color: {SENSITIVE_COLORS['torture']};">{docs_with_torture:,}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">{pct(docs_with_torture, total_docs)} of documents</div>
    </div>
    <div class="summary-card danger" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {SENSITIVE_COLORS['disappearance']}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Disappearance</h4>
        <div style="font-size: 1.8rem; font-weight: bold; color: {SENSITIVE_COLORS['disappearance']};">{docs_with_disappearance:,}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">{pct(docs_with_disappearance, total_docs)} of documents</div>
    </div>
    <div class="summary-card" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #6B7280; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Unique Victims</h4>
        <div style="font-size: 1.8rem; font-weight: bold; color: #374151;">{total_victims:,}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">individuals named</div>
    </div>
    <div class="summary-card" style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #6B7280; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h4 style="margin: 0 0 5px 0; font-size: 0.8rem; color: #6B7280; text-transform: uppercase;">Perpetrators</h4>
        <div style="font-size: 1.8rem; font-weight: bold; color: #374151;">{total_perps:,}</div>
        <div style="font-size: 0.85rem; color: #6B7280;">individuals/entities named</div>
    </div>
</div>
'''
    return html
