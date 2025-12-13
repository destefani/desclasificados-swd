# Visualization Research

**Created**: 2025-12-06
**Status**: Research & Planning
**Category**: Technical Research

## Overview

This document explores visualization strategies for the declassified CIA documents project. The goal is to make ~21,500 documents accessible through compelling, interactive, and informative visual representations that support historical research, public understanding, and narrative building.

## Current State

### Existing Visualization Capabilities

| Module | Type | Output | Status |
|--------|------|--------|--------|
| `app/visualize_transcripts.py` | Static | matplotlib charts | Basic |
| `app/analyze_documents.py` | Static | HTML report + timeline PNG | Basic |

### Current Visualizations

1. **Classification Distribution** - Bar chart of document classification levels
2. **Documents Over Time** - Line chart by year
3. **Top Keywords** - Bar chart of keyword frequency
4. **Timeline** - Bar chart of documents per date
5. **HTML Report** - Static tables for people, places, keywords, recipients, doc types

### Limitations

- **Static only**: No interactivity, filtering, or drill-down
- **No network graphs**: Missing relationship visualizations (people, organizations)
- **No geographic mapping**: Places mentioned but not visualized on maps
- **No sensitive content views**: New financial/violence/torture fields not visualized
- **No quality metrics**: Confidence scores not displayed
- **Single-page**: No dashboard or multi-view exploration

---

## Research Questions

1. What visualization types best serve historical research on declassified documents?
2. How can we visualize relationships between people, organizations, and events?
3. What interactive tools would enable researchers to explore 21,500 documents effectively?
4. How should sensitive content (violence, torture, financial) be visualized responsibly?
5. What are the deployment options (static site, Streamlit, Jupyter, web app)?

---

## Proposed Visualization Categories

### 1. Temporal Visualizations

**Purpose**: Understand document distribution and events over time (1973-1990)

| Visualization | Description | Priority |
|---------------|-------------|----------|
| Interactive Timeline | Zoomable timeline with event markers | High |
| Heatmap Calendar | Daily/monthly document frequency | Medium |
| Stacked Area Chart | Document types over time | Medium |
| Event Annotations | Key historical events overlaid | High |

**Key Historical Events to Annotate**:
- September 11, 1973: Military coup
- 1974-1977: DINA operations, Operation Condor
- September 21, 1976: Letelier assassination (Washington DC)
- 1978: Amnesty decree
- 1980: Constitution plebiscite
- 1988: Plebiscite ("No" vote)
- 1990: Return to democracy

### 2. Network Visualizations

**Purpose**: Map relationships between actors, organizations, and operations

| Visualization | Description | Priority |
|---------------|-------------|----------|
| Person-to-Person Network | Who appears together in documents | High |
| Organization Network | CIA, DINA, State Dept, Embassy relationships | High |
| Operation Clusters | Documents grouped by operation/theme | Medium |
| Geographic Flow | Information flow between locations | Medium |

**Network Data Sources**:
- `metadata.people_mentioned[]`
- `metadata.author`
- `metadata.recipients[]`
- `metadata.organizations[]` (if available)

### 3. Geographic Visualizations

**Purpose**: Map locations and geographic patterns

| Visualization | Description | Priority |
|---------------|-------------|----------|
| Document Origin Map | Where documents originated | Medium |
| Mentions Heatmap | Frequency of place mentions | Medium |
| Operation Condor Map | Cross-border connections (Chile, Argentina, Uruguay, Paraguay, Brazil, Bolivia) | High |
| Detention Centers | Map of known detention sites from `torture_references.detention_centers` | High |

**Key Locations**:
- Chile: Santiago, Valparaiso, Concepcion
- Argentina: Buenos Aires
- USA: Washington DC, Langley
- Detention centers: Villa Grimaldi, Londres 38, Tejas Verdes, etc.

### 4. Sensitive Content Visualizations

**Purpose**: Responsibly visualize financial, violence, and torture references

| Visualization | Description | Priority |
|---------------|-------------|----------|
| Financial Timeline | US funding/financial operations over time | High |
| Violence Incident Types | Categorized by type (assassination, kidnapping, etc.) | High |
| Detention Center Network | Known sites and connections | High |
| Victim/Perpetrator Lists | Extracted names (with ethical considerations) | Medium |

**Ethical Considerations**:
- Content warnings before displaying graphic data
- Option to filter out sensitive visualizations
- Focus on aggregate patterns rather than individual victim details
- Cite academic standards for presenting human rights data

### 5. Document Quality & Coverage

**Purpose**: Monitor transcription quality and identify gaps

| Visualization | Description | Priority |
|---------------|-------------|----------|
| Confidence Distribution | Histogram of `confidence.overall` scores | High |
| Low-Confidence Flags | Documents needing review | High |
| Coverage by Year | % transcribed per year | Medium |
| Model Performance | Success rates by model | Medium |

### 6. Text & Content Analysis

**Purpose**: Explore document content patterns

| Visualization | Description | Priority |
|---------------|-------------|----------|
| Word Cloud | Most common terms (excluding stopwords) | Low |
| Topic Clusters | LDA/embedding-based topic modeling | Medium |
| Keyword Co-occurrence | Which keywords appear together | Medium |
| Classification Trends | How classification levels change over time | Medium |

---

## Technology Options

### Static Site Generators

| Tool | Pros | Cons | Use Case |
|------|------|------|----------|
| **Altair/Vega-Lite** | Declarative, interactive, embeddable | Limited network graphs | Charts in HTML reports |
| **Plotly** | Rich interactivity, wide chart types | Larger bundle size | Dashboards |
| **D3.js** | Maximum flexibility | Steep learning curve | Custom network visualizations |

### Dashboard Frameworks

| Tool | Pros | Cons | Use Case |
|------|------|------|----------|
| **Streamlit** | Python-native, rapid prototyping | Limited customization | Internal research tool |
| **Panel/Holoviz** | Python, good for notebooks | Less polished | Jupyter integration |
| **Dash (Plotly)** | Production-ready, callbacks | More complex | Public-facing dashboard |
| **Observable** | Reactive, collaborative | JavaScript required | Shareable notebooks |

### Specialized Libraries

| Library | Purpose | Notes |
|---------|---------|-------|
| **NetworkX + PyVis** | Network graphs | Python-based, exports to HTML |
| **Gephi** | Advanced network analysis | Desktop app, export images |
| **Folium/Leaflet** | Geographic maps | Interactive maps in Python |
| **Kepler.gl** | Large-scale geospatial | WebGL-based, handles large datasets |

### Recommended Stack

**Phase 1 (Quick wins)**:
- Plotly for enhanced charts
- Folium for maps
- NetworkX + PyVis for simple networks

**Phase 2 (Dashboard)**:
- Streamlit for internal research dashboard
- Altair for embeddable static visualizations

**Phase 3 (Public)**:
- Dash or custom React app
- D3.js for advanced network visualizations
- Kepler.gl for geospatial

---

## Implementation Priorities

### High Priority (Phase 1)

1. **Interactive Timeline with Events**
   - Replace static matplotlib with Plotly
   - Add historical event annotations
   - Enable zoom and filter by classification level

2. **Network Graph: Key Actors**
   - People co-occurrence network
   - Filter by time period
   - Highlight key figures (Pinochet, Contreras, Letelier, etc.)

3. **Quality Dashboard**
   - Confidence score distribution
   - Coverage by year
   - Low-confidence document list

4. **Sensitive Content Summary**
   - Aggregate counts (not individual victims)
   - Financial totals by year
   - Detention center list

### Medium Priority (Phase 2)

5. **Geographic Map**
   - Document mentions by location
   - Operation Condor country connections

6. **Streamlit Research Dashboard**
   - Unified interface for all visualizations
   - Filtering and search
   - Export capabilities

7. **Keyword Analysis**
   - Co-occurrence matrix
   - Trend over time

### Lower Priority (Phase 3)

8. **Public-Facing Website**
   - Curated visualizations
   - Educational narrative

9. **Advanced Network Analysis**
   - Community detection
   - Centrality measures

10. **Topic Modeling Visualization**
    - Document clusters
    - Topic evolution over time

---

## Data Requirements

### Available Now

From existing transcript schema (`metadata`):
- `document_date` - Timeline
- `classification_level` - Distribution charts
- `document_type` - Type breakdown
- `keywords[]` - Keyword analysis
- `people_mentioned[]` - Network graphs
- `places_mentioned[]` - Geographic visualization (needs geocoding)
- `author`, `recipients[]` - Communication network

From new sensitive content fields:
- `financial_references.amounts[]`, `.financial_actors[]`, `.purposes[]`
- `violence_references.incident_types[]`, `.victims[]`, `.perpetrators[]`
- `torture_references.detention_centers[]`, `.victims[]`, `.perpetrators[]`

From quality metrics:
- `confidence.overall` - Quality distribution
- `confidence.concerns[]` - Issue tracking

### Needs Development

| Data Need | Source | Effort |
|-----------|--------|--------|
| Geocoded locations | OpenStreetMap Nominatim API | Medium |
| Historical event dates | Manual curation | Low |
| Organization extraction | NER or manual review | High |
| Document embeddings | Already have for RAG | Available |

---

## Example Visualizations to Prototype

### 1. Enhanced Timeline (Plotly)

```python
import plotly.express as px

# Timeline with event annotations
fig = px.scatter(df, x='document_date', y='classification_level',
                 color='document_type', hover_data=['keywords'])
fig.add_vline(x='1973-09-11', annotation_text='Coup')
fig.add_vline(x='1976-09-21', annotation_text='Letelier')
```

### 2. Person Network (NetworkX + PyVis)

```python
import networkx as nx
from pyvis.network import Network

G = nx.Graph()
# Add edges for people appearing in same document
for doc in documents:
    people = doc['metadata']['people_mentioned']
    for i, p1 in enumerate(people):
        for p2 in people[i+1:]:
            G.add_edge(p1, p2)

net = Network(notebook=True)
net.from_nx(G)
net.show('people_network.html')
```

### 3. Geographic Map (Folium)

```python
import folium

m = folium.Map(location=[-33.45, -70.65], zoom_start=4)  # Santiago
for place, count in places_count.items():
    # Geocode and add marker
    folium.CircleMarker(location=coords, radius=count/10).add_to(m)
m.save('document_map.html')
```

---

## Next Steps

1. [ ] Create `research/technical/visualizations/` directory structure
2. [ ] Prototype enhanced timeline with Plotly
3. [ ] Build person co-occurrence network
4. [ ] Create Streamlit dashboard skeleton
5. [ ] Add geographic mapping with Folium
6. [ ] Design sensitive content visualization approach
7. [ ] Document ethical guidelines for human rights data visualization

---

## References

- [Plotly Python Documentation](https://plotly.com/python/)
- [NetworkX Documentation](https://networkx.org/)
- [Folium Documentation](https://python-visualization.github.io/folium/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Responsible Data Visualization for Human Rights](https://www.theengineroom.org/)
- [D3.js Gallery](https://observablehq.com/@d3/gallery)

---

## Related Files

- `app/visualize_transcripts.py` - Current matplotlib visualizations
- `app/analyze_documents.py` - HTML report generation
- `tests/test_app.py` - Existing Streamlit exploration app
- `data/generated_transcripts/` - Source data for visualizations
