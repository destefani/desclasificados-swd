"""
Network graph visualization using vis.js.

Generates interactive network graphs showing relationships between:
- People who appear together in documents
- Organizations and their connections
- Key actors and their networks
"""

import json
from collections import Counter, defaultdict
from typing import Any


# vis.js CDN URL
VISJS_CDN = "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"

# Node colors by category
NODE_COLORS = {
    "high_frequency": "#DC2626",    # Red - very frequent (top 10%)
    "medium_frequency": "#F59E0B",  # Amber - medium frequency
    "low_frequency": "#3B82F6",     # Blue - lower frequency
    "default": "#6B7280",           # Gray
}

# Edge colors
EDGE_COLORS = {
    "strong": "#1F2937",    # Dark - strong connection (many co-occurrences)
    "medium": "#6B7280",    # Gray - medium connection
    "weak": "#D1D5DB",      # Light gray - weak connection
}


def compute_cooccurrence(
    documents: list[dict[str, Any]],
    field: str = "people_mentioned",
    min_occurrences: int = 2,
) -> tuple[Counter, dict[str, list[str]]]:
    """
    Compute co-occurrence relationships from document data.

    Args:
        documents: List of document metadata dictionaries
        field: The metadata field to extract entities from
        min_occurrences: Minimum times an entity must appear to be included

    Returns:
        Tuple of:
        - Counter of entity frequencies
        - Dict mapping entity pairs (tuple) to list of document IDs where they co-occur
    """
    entity_count: Counter = Counter()
    cooccurrence: dict[tuple[str, str], list[str]] = defaultdict(list)

    for doc in documents:
        metadata = doc.get("metadata", {})
        entities = metadata.get(field, [])
        doc_id = metadata.get("document_id", "unknown")

        # Filter out empty values
        entities = [e for e in entities if e and isinstance(e, str)]

        # Count entities
        for entity in entities:
            entity_count[entity] += 1

        # Record co-occurrences (all pairs in this document)
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i + 1:]:
                # Sort to ensure consistent key ordering
                pair = tuple(sorted([entity1, entity2]))
                cooccurrence[pair].append(doc_id)

    # Filter by minimum occurrences
    filtered_count = Counter({k: v for k, v in entity_count.items() if v >= min_occurrences})

    # Filter co-occurrences to only include entities that meet minimum
    filtered_cooccurrence = {
        pair: docs for pair, docs in cooccurrence.items()
        if pair[0] in filtered_count and pair[1] in filtered_count
    }

    return filtered_count, filtered_cooccurrence


def prepare_network_data(
    entity_count: Counter,
    cooccurrence: dict[tuple[str, str], list[str]],
    max_nodes: int = 100,
    min_edge_weight: int = 2,
) -> dict[str, Any]:
    """
    Prepare network data for vis.js visualization.

    Args:
        entity_count: Counter of entity frequencies
        cooccurrence: Dict mapping entity pairs to document lists
        max_nodes: Maximum number of nodes to include
        min_edge_weight: Minimum co-occurrence count to create an edge

    Returns:
        Dictionary with nodes and edges for vis.js
    """
    # Get top entities by frequency
    top_entities = [entity for entity, _ in entity_count.most_common(max_nodes)]
    top_set = set(top_entities)

    # Calculate frequency thresholds for coloring
    frequencies = [entity_count[e] for e in top_entities]
    if frequencies:
        max_freq = max(frequencies)
        high_threshold = max_freq * 0.5
        medium_threshold = max_freq * 0.2
    else:
        high_threshold = medium_threshold = 0

    # Create nodes
    nodes = []
    for i, entity in enumerate(top_entities):
        freq = entity_count[entity]

        # Determine color based on frequency
        if freq >= high_threshold:
            color = NODE_COLORS["high_frequency"]
        elif freq >= medium_threshold:
            color = NODE_COLORS["medium_frequency"]
        else:
            color = NODE_COLORS["low_frequency"]

        # Scale node size by frequency (min 10, max 50)
        size = min(50, max(10, 10 + (freq / max_freq) * 40)) if max_freq > 0 else 15

        nodes.append({
            "id": i,
            "label": entity,
            "value": freq,
            "title": f"{entity}\n{freq} documents",
            "color": {
                "background": color,
                "border": color,
                "highlight": {"background": "#10B981", "border": "#059669"},
            },
            "font": {"size": 12},
        })

    # Create entity to ID mapping
    entity_to_id = {entity: i for i, entity in enumerate(top_entities)}

    # Create edges
    edges = []
    edge_id = 0
    for (entity1, entity2), doc_ids in cooccurrence.items():
        # Only include edges between nodes in our graph
        if entity1 not in top_set or entity2 not in top_set:
            continue

        weight = len(doc_ids)
        if weight < min_edge_weight:
            continue

        # Determine edge color based on weight
        max_edge_weight = max(len(docs) for docs in cooccurrence.values()) if cooccurrence else 1
        if weight >= max_edge_weight * 0.5:
            color = EDGE_COLORS["strong"]
        elif weight >= max_edge_weight * 0.2:
            color = EDGE_COLORS["medium"]
        else:
            color = EDGE_COLORS["weak"]

        edges.append({
            "id": edge_id,
            "from": entity_to_id[entity1],
            "to": entity_to_id[entity2],
            "value": weight,
            "title": f"{weight} shared documents",
            "color": {"color": color, "highlight": "#10B981"},
        })
        edge_id += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "entity_to_id": entity_to_id,
    }


def generate_network_graph(
    entity_count: Counter,
    cooccurrence: dict[tuple[str, str], list[str]],
    container_id: str = "network-graph",
    height: str = "600px",
    title: str = "Entity Network",
    max_nodes: int = 75,
    min_edge_weight: int = 2,
    physics_enabled: bool = True,
) -> str:
    """
    Generate HTML/JavaScript for an interactive network graph.

    Args:
        entity_count: Counter of entity frequencies
        cooccurrence: Dict mapping entity pairs to document lists
        container_id: HTML element ID for the graph container
        height: CSS height for the container
        title: Title displayed above the graph
        max_nodes: Maximum number of nodes to display
        min_edge_weight: Minimum shared documents to show an edge
        physics_enabled: Whether to enable physics simulation

    Returns:
        HTML string with embedded JavaScript for the network graph
    """
    # Prepare data
    network_data = prepare_network_data(
        entity_count,
        cooccurrence,
        max_nodes=max_nodes,
        min_edge_weight=min_edge_weight,
    )

    nodes_json = json.dumps(network_data["nodes"])
    edges_json = json.dumps(network_data["edges"])

    # Build the HTML
    html = f'''
<div class="network-section">
    <div class="network-controls" style="margin-bottom: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
        <button onclick="togglePhysics_{container_id.replace('-', '_')}()" class="network-btn" id="{container_id}-physics-btn">
            Pause Physics
        </button>
        <button onclick="resetNetwork_{container_id.replace('-', '_')}()" class="network-btn">
            Reset View
        </button>
        <span style="color: #6B7280; font-size: 12px;">
            Drag nodes to rearrange, scroll to zoom, click node for details
        </span>
        <div style="flex: 1;"></div>
        <div class="network-legend" style="display: flex; gap: 15px; flex-wrap: wrap;">
            <span style="display: flex; align-items: center; gap: 4px;">
                <span style="width: 12px; height: 12px; background: {NODE_COLORS['high_frequency']}; border-radius: 50%;"></span>
                <span style="font-size: 12px;">High frequency</span>
            </span>
            <span style="display: flex; align-items: center; gap: 4px;">
                <span style="width: 12px; height: 12px; background: {NODE_COLORS['medium_frequency']}; border-radius: 50%;"></span>
                <span style="font-size: 12px;">Medium</span>
            </span>
            <span style="display: flex; align-items: center; gap: 4px;">
                <span style="width: 12px; height: 12px; background: {NODE_COLORS['low_frequency']}; border-radius: 50%;"></span>
                <span style="font-size: 12px;">Lower</span>
            </span>
        </div>
    </div>

    <div id="{container_id}" style="width: 100%; max-width: 100%; height: {height}; border: 1px solid #E5E7EB; border-radius: 8px; background: #FAFAFA; overflow: hidden;"></div>

    <div id="{container_id}-info" class="network-info" style="margin-top: 10px; padding: 10px; background: #F3F4F6; border-radius: 4px; display: none;">
        <strong>Selected:</strong> <span id="{container_id}-selected-name">-</span><br>
        <strong>Documents:</strong> <span id="{container_id}-selected-count">-</span><br>
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
.network-btn.active {{
    background: #3B82F6;
    color: white;
    border-color: #3B82F6;
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
                min: 10,
                max: 50,
                label: {{
                    enabled: true,
                    min: 10,
                    max: 20
                }}
            }},
            font: {{
                size: 12,
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
                type: 'continuous'
            }}
        }},
        physics: {{
            enabled: {str(physics_enabled).lower()},
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {{
                gravitationalConstant: -50,
                centralGravity: 0.01,
                springLength: 100,
                springConstant: 0.08
            }},
            stabilization: {{
                iterations: 100,
                fit: true
            }}
        }},
        interaction: {{
            hover: true,
            tooltipDelay: 200,
            hideEdgesOnDrag: true,
            hideEdgesOnZoom: true
        }}
    }};

    const network_{container_id.replace('-', '_')} = new vis.Network(container, data, options);

    let physicsEnabled = {str(physics_enabled).lower()};

    // Track selected node info
    network_{container_id.replace('-', '_')}.on('selectNode', function(params) {{
        if (params.nodes.length > 0) {{
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            const connectedEdges = network_{container_id.replace('-', '_')}.getConnectedEdges(nodeId);

            document.getElementById('{container_id}-info').style.display = 'block';
            document.getElementById('{container_id}-selected-name').textContent = node.label;
            document.getElementById('{container_id}-selected-count').textContent = node.value + ' documents';
            document.getElementById('{container_id}-selected-connections').textContent = connectedEdges.length + ' connections';
        }}
    }});

    network_{container_id.replace('-', '_')}.on('deselectNode', function() {{
        document.getElementById('{container_id}-info').style.display = 'none';
    }});

    // Export functions globally
    window.togglePhysics_{container_id.replace('-', '_')} = function() {{
        physicsEnabled = !physicsEnabled;
        network_{container_id.replace('-', '_')}.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        document.getElementById('{container_id}-physics-btn').textContent = physicsEnabled ? 'Pause Physics' : 'Resume Physics';
    }};

    window.resetNetwork_{container_id.replace('-', '_')} = function() {{
        network_{container_id.replace('-', '_')}.fit();
    }};
}})();
</script>
'''

    return html


def generate_people_network(
    documents: list[dict[str, Any]],
    container_id: str = "people-network",
    height: str = "600px",
    max_nodes: int = 75,
    min_occurrences: int = 3,
    min_edge_weight: int = 2,
) -> str:
    """
    Generate a network graph of people mentioned in documents.

    Convenience function that extracts people_mentioned and generates the graph.

    Args:
        documents: List of document data with metadata
        container_id: HTML element ID
        height: CSS height
        max_nodes: Maximum nodes to display
        min_occurrences: Minimum document mentions to include a person
        min_edge_weight: Minimum shared documents for an edge

    Returns:
        HTML string with the network graph
    """
    entity_count, cooccurrence = compute_cooccurrence(
        documents,
        field="people_mentioned",
        min_occurrences=min_occurrences,
    )

    return generate_network_graph(
        entity_count,
        cooccurrence,
        container_id=container_id,
        height=height,
        title="People Network",
        max_nodes=max_nodes,
        min_edge_weight=min_edge_weight,
    )


def generate_organization_network(
    documents: list[dict[str, Any]],
    container_id: str = "org-network",
    height: str = "600px",
    max_nodes: int = 50,
    min_occurrences: int = 3,
    min_edge_weight: int = 2,
) -> str:
    """
    Generate a network graph of organizations mentioned in documents.

    Args:
        documents: List of document data with metadata
        container_id: HTML element ID
        height: CSS height
        max_nodes: Maximum nodes to display
        min_occurrences: Minimum document mentions to include an org
        min_edge_weight: Minimum shared documents for an edge

    Returns:
        HTML string with the network graph
    """
    # Extract organization names from the nested structure
    processed_docs = []
    for doc in documents:
        metadata = doc.get("metadata", {})
        orgs = metadata.get("organizations_mentioned", [])
        # Extract just the names
        org_names = [org.get("name", "") for org in orgs if isinstance(org, dict) and org.get("name")]
        processed_docs.append({
            "metadata": {
                "document_id": metadata.get("document_id", ""),
                "org_names": org_names,
            }
        })

    entity_count, cooccurrence = compute_cooccurrence(
        processed_docs,
        field="org_names",
        min_occurrences=min_occurrences,
    )

    return generate_network_graph(
        entity_count,
        cooccurrence,
        container_id=container_id,
        height=height,
        title="Organization Network",
        max_nodes=max_nodes,
        min_edge_weight=min_edge_weight,
    )
