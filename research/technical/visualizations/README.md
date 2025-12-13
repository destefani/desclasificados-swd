# Visualizations Technical Research

This directory contains technical research, prototypes, and experiments for visualizing the declassified CIA documents.

## Overview

See the main research document: [../../VISUALIZATIONS_RESEARCH.md](../../VISUALIZATIONS_RESEARCH.md)

## Directory Structure

```
visualizations/
├── README.md                 # This file
├── prototypes/               # Visualization prototypes and experiments
│   ├── timeline/             # Interactive timeline experiments
│   ├── networks/             # Network graph experiments
│   ├── maps/                 # Geographic visualization experiments
│   └── dashboards/           # Dashboard prototypes
├── data/                     # Processed data for visualizations
│   ├── aggregated/           # Pre-aggregated statistics
│   └── geocoded/             # Geocoded location data
└── exports/                  # Generated visualization outputs
    ├── images/               # Static image exports
    └── html/                 # Interactive HTML exports
```

## Current Focus Areas

1. **Interactive Timeline** - Plotly-based timeline with historical events
2. **Person Network** - NetworkX/PyVis co-occurrence graphs
3. **Geographic Maps** - Folium-based location mapping
4. **Streamlit Dashboard** - Unified research interface

## Quick Start

```bash
# Install visualization dependencies (if not already installed)
uv add plotly folium networkx pyvis

# Run existing visualization
uv run python -m app.visualize_transcripts

# Generate HTML report
uv run python -m app.analyze_documents data/generated_transcripts/chatgpt-5-1
```

## Related Files

- `app/visualize_transcripts.py` - Current matplotlib-based visualizations
- `app/analyze_documents.py` - HTML report generation with timeline
- `tests/test_app.py` - Streamlit document explorer

## Research Log

| Date | Activity | Outcome |
|------|----------|---------|
| 2025-12-06 | Initial research document created | Identified 6 visualization categories and priority order |
