# Timeline Visualization Plan

**Created**: 2025-12-06
**Status**: Planning
**Data Source**: `data/generated_transcripts/gpt-4.1-mini/` (4,924 documents)

## Executive Summary

This plan proposes an interactive timeline visualization for ~5,000 declassified CIA documents about the Chilean dictatorship (1973-1990). The timeline will contextualize document production against key historical events, enabling researchers to understand information flow, US government attention patterns, and correlations between events and intelligence activity.

---

## Data Analysis Summary

### Document Coverage

| Metric | Value |
|--------|-------|
| Total Documents | 4,924 |
| Date Range | 1937 - 1991 |
| Core Period | 1970 - 1991 |
| Peak Years | 1987-1988 (231 documents in sample) |

### Year Distribution (Sample of 500)

```
1970-1973 (Pre/During Coup):  17 documents
1974-1976 (Early Dictatorship): 20 documents
1977-1979:                      18 documents
1980-1986:                      36 documents
1987-1988 (Plebiscite Era):    231 documents  ← PEAK
1989-1991 (Transition):        140 documents
```

**Key Observation**: Document production peaks dramatically around the 1988 plebiscite, suggesting heightened US interest during Chile's democratic transition.

### Classification Distribution

| Level | Count | Percentage |
|-------|-------|------------|
| UNCLASSIFIED | 246 | 49% |
| CONFIDENTIAL | 123 | 25% |
| SECRET | 62 | 12% |
| LIMITED OFFICIAL USE | 16 | 3% |
| Unknown/Empty | 53 | 11% |

### Document Types

| Type | Count |
|------|-------|
| MEMORANDUM | 237 |
| LETTER | 120 |
| TELEGRAM | 53 |
| REPORT | 39 |
| Other | 51 |

### Sensitive Content Frequency (Sample 500)

- **Violence References**: 231 documents (46%)
- **Torture References**: 32 documents (6%)
- **Financial References**: 32 documents (6%)

### Top Keywords

1. US-CHILE RELATIONS (353)
2. HUMAN RIGHTS (218)
3. DIPLOMACY (213)
4. STATE DEPARTMENT (190)
5. EMBASSY (168)
6. LETELIER ASSASSINATION (122)
7. MILITARY (102)
8. OPPOSITION (87)
9. 1988 PLEBISCITE (55)
10. OPERATION CONDOR (appears in data)

---

## Historical Context: Key Events to Annotate

### Pre-Coup Period (1970-1973)

| Date | Event | Significance |
|------|-------|--------------|
| 1970-09-04 | Allende wins election | First democratically elected Marxist president |
| 1970-10-22 | General Schneider assassination | CIA-linked coup attempt fails |
| 1970-11-03 | Allende inaugurated | Start of socialist government |
| 1972-10 | October Strike | Economic crisis, truckers' strike |
| 1973-06-29 | Tanquetazo | Failed military coup attempt |

### The Coup (September 1973)

| Date | Event | Significance |
|------|-------|--------------|
| 1973-09-11 | Military coup | Allende dies, Pinochet takes power |
| 1973-09-12 | Junta formed | Four-member military junta established |
| 1973-09-13 | Congress dissolved | End of democratic institutions |

### Consolidation of Dictatorship (1973-1977)

| Date | Event | Significance |
|------|-------|--------------|
| 1973-09-20 | Caravan of Death begins | Mass executions across Chile |
| 1974-06-18 | DINA established | Secret police formation |
| 1974-09-30 | Carlos Prats assassination (Buenos Aires) | DINA international operations begin |
| 1975 | Operation Condor formalized | Cross-border repression coordination |
| 1976-09-21 | **Letelier assassination (Washington DC)** | Most significant international incident |
| 1977-08 | DINA dissolved, CNI created | Reorganization after Letelier scandal |

### International Pressure Era (1977-1983)

| Date | Event | Significance |
|------|-------|--------------|
| 1978-04 | Amnesty Law decreed | Self-amnesty for human rights crimes |
| 1980-09-11 | New Constitution plebiscite | Institutionalization of regime |
| 1982-08 | Economic crisis | Chile defaults on debt |
| 1983-05-11 | First national protest | Beginning of mass opposition |

### Transition Period (1984-1990)

| Date | Event | Significance |
|------|-------|--------------|
| 1985-09-30 | Case of the Degollados | Murder of three opposition members |
| 1986-07-02 | Carmen Gloria Quintana case | Protesters burned alive |
| 1986-09-07 | Pinochet assassination attempt | FPMR attack on convoy |
| 1987-09-05 | Visit of Pope John Paul II | International spotlight |
| **1988-10-05** | **Plebiscite "No" wins** | Beginning of end of dictatorship |
| 1989-12-14 | Aylwin wins election | Democratic transition |
| 1990-03-11 | Pinochet leaves power | Return to democracy |

### Post-Dictatorship (1990-1991)

| Date | Event | Significance |
|------|-------|--------------|
| 1990-04-25 | Rettig Commission created | Truth commission for human rights |
| 1991-02-08 | Rettig Report published | Official documentation of victims |

---

## Visualization Design

### 1. Primary View: Document Volume Timeline

**Concept**: A zoomable area chart showing document production over time.

```
     ▲ Documents
     │
  50 │                                    ████
     │                                  ██████
  40 │                                ████████
     │                              ██████████
  30 │                            ████████████
     │         ▼Coup           ██████████████
  20 │          │             ████████████████
     │  ████    │    ████  ██████████████████
  10 │████████  ▼  ██████████████████████████
     │████████████████████████████████████████
   0 └────────────────────────────────────────→
     1970  1975  1980  1985  1988  1990     Time
                              ▲
                        Plebiscite
```

**Features**:
- Stacked by classification level (color-coded)
- Historical event markers as vertical lines with tooltips
- Brush selection for zooming into specific periods
- Click to drill down to monthly/daily view

### 2. Secondary View: Event Correlation Heatmap

**Concept**: Heatmap showing document density around key events.

```
                    Days Before/After Event
Event              -30  -15   0  +15  +30
──────────────────────────────────────────
Coup (1973-09-11)   ░░   ░░  ██  ███  ██
Letelier (1976-09)  ░░   ░░  ██  ████ ███
Plebiscite (1988)   ██   ██  ██  ██   ██
```

**Value**: Shows how CIA document production correlates with major events.

### 3. Tertiary View: Keyword Timeline

**Concept**: Multi-series line chart showing keyword frequency over time.

```
     ▲ Mentions
     │
  40 │  ╭─╮                    ╭────╮
     │ ╱   ╲ LETELIER         ╱      ╲ PLEBISCITE
  20 │╱     ╲────────────────╱        ╲
     │       ╲              ╱          ╲
   0 └────────╲────────────╱────────────╲───→
     1975     1978        1985         1990
```

**Keywords to Track**:
- OPERATION CONDOR
- LETELIER ASSASSINATION
- HUMAN RIGHTS
- 1988 PLEBISCITE
- PINOCHET
- DINA

### 4. Interactive Features

| Feature | Description |
|---------|-------------|
| **Zoom/Pan** | Navigate through 20-year timeline |
| **Brush Selection** | Select date range for detailed view |
| **Event Tooltips** | Hover over event markers for context |
| **Document List** | Click on bar segment to see document list |
| **Classification Filter** | Toggle visibility by classification level |
| **Keyword Filter** | Filter documents by keyword |
| **Sensitive Content Toggle** | Highlight/filter documents with violence/torture |

### 5. Document Detail Panel

When clicking a specific time period or document:

```
┌─────────────────────────────────────────────────┐
│ Document: D790478-OZSB                          │
│ Date: 1979-10-18                                │
│ Type: TELEGRAM          Class: SECRET           │
│ Title: LETELIER/MOFFITT CASE: HERNANDEZ...     │
├─────────────────────────────────────────────────┤
│ Summary: This SECRET telegram from the U.S.     │
│ Embassy in Santiago reports on military         │
│ personnel transfers...                          │
├─────────────────────────────────────────────────┤
│ Keywords: MILITARY, LETELIER ASSASSINATION      │
│ People: HERNANDEZ, OSVALDO | MOREL, ENRIQUE    │
│ Violence: ⚠️ Assassination mentioned            │
├─────────────────────────────────────────────────┤
│ [View Full Text] [View Original PDF]            │
└─────────────────────────────────────────────────┘
```

---

## Technical Architecture

### Option A: Plotly + Dash (Recommended)

**Pros**:
- Python-native, integrates with existing codebase
- Rich interactivity out of the box
- Supports zoom, pan, brush selection
- Easy to deploy as standalone web app

**Cons**:
- Slightly larger bundle size
- Less customizable than D3.js

**Implementation**:
```python
# Core dependencies
plotly>=5.18.0
dash>=2.14.0
pandas>=2.0.0
```

### Option B: Streamlit + Altair

**Pros**:
- Rapid prototyping
- Simple deployment
- Good for internal research tool

**Cons**:
- Less suitable for public-facing visualization
- Limited customization

### Option C: Observable/D3.js

**Pros**:
- Maximum flexibility
- Beautiful, publication-quality visualizations
- Shareable notebooks

**Cons**:
- Requires JavaScript expertise
- More development time

### Recommended: Hybrid Approach

1. **Phase 1**: Plotly prototype for validation
2. **Phase 2**: Dash app for internal research
3. **Phase 3**: D3.js/Observable for public-facing version

---

## Data Processing Pipeline

### Step 1: Extract Timeline Data

```python
# Pseudocode
def extract_timeline_data(docs_path):
    records = []
    for json_file in docs_path.glob('*.json'):
        doc = json.load(json_file)
        meta = doc['metadata']
        records.append({
            'document_id': meta['document_id'],
            'date': meta['document_date'],
            'classification': meta['classification_level'],
            'doc_type': meta['document_type'],
            'title': meta['document_title'],
            'keywords': meta['keywords'],
            'has_violence': meta['violence_references']['has_violence_content'],
            'has_torture': meta['torture_references']['has_torture_content'],
            'confidence': doc['confidence']['overall']
        })
    return pd.DataFrame(records)
```

### Step 2: Aggregate by Time Period

```python
def aggregate_timeline(df, period='M'):  # Monthly
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    return df.groupby([
        df['date'].dt.to_period(period),
        'classification'
    ]).size().unstack(fill_value=0)
```

### Step 3: Generate Historical Events Dataset

```python
HISTORICAL_EVENTS = [
    {'date': '1973-09-11', 'event': 'Military Coup', 'category': 'major'},
    {'date': '1976-09-21', 'event': 'Letelier Assassination', 'category': 'major'},
    {'date': '1988-10-05', 'event': 'Plebiscite', 'category': 'major'},
    # ... more events
]
```

---

## Implementation Phases

### Phase 1: Data Preparation (Day 1)

1. Create `app/timeline/data_processor.py`
   - Load all 4,924 JSON documents
   - Parse dates, handle edge cases
   - Calculate aggregations (daily, monthly, yearly)
   - Export to timeline-optimized format

2. Create `app/timeline/events.py`
   - Historical events database
   - Event categories (major, moderate, minor)
   - Event metadata (description, sources)

### Phase 2: Static Visualization (Day 2)

1. Create `app/timeline/charts.py`
   - Basic Plotly timeline chart
   - Event markers
   - Classification color coding

2. Create `app/timeline/export.py`
   - Export to standalone HTML
   - Export to PNG for reports

### Phase 3: Interactive Dashboard (Day 3-4)

1. Create `app/timeline/app.py` (Dash application)
   - Main timeline view
   - Event correlation view
   - Keyword timeline
   - Document detail panel

2. Add filters and interactions
   - Date range selector
   - Classification filter
   - Keyword search
   - Document drill-down

### Phase 4: Integration & Polish (Day 5)

1. Add to Makefile
   - `make timeline` - Generate static timeline
   - `make timeline-app` - Run interactive dashboard

2. Documentation
   - Usage guide
   - Interpretation notes

---

## Design Considerations

### Color Palette

| Classification | Color | Hex |
|----------------|-------|-----|
| UNCLASSIFIED | Gray | #6B7280 |
| LIMITED OFFICIAL USE | Blue | #3B82F6 |
| CONFIDENTIAL | Yellow | #F59E0B |
| SECRET | Red | #EF4444 |
| TOP SECRET | Purple | #8B5CF6 |

### Event Marker Styles

| Category | Style |
|----------|-------|
| Major Event | Solid vertical line + label |
| Moderate Event | Dashed line + tooltip |
| Minor Event | Dot marker only |

### Sensitive Content Indicators

| Content Type | Indicator |
|--------------|-----------|
| Violence | ⚠️ Warning icon |
| Torture | 🔴 Red marker |
| Financial | 💰 Money icon |

---

## Ethical Considerations

1. **Content Warnings**: Display warning before showing documents with violence/torture content

2. **Victim Respect**: Focus on aggregate patterns rather than individual victim details in main views

3. **Context**: Provide historical context for events to avoid misinterpretation

4. **Attribution**: Clearly indicate that visualizations represent CIA documents, not historical truth

5. **Accessibility**: Ensure color choices work for colorblind users (use patterns + colors)

---

## Success Metrics

1. **Functionality**: Can researchers navigate 20 years of documents in <30 seconds?
2. **Discovery**: Does the timeline reveal non-obvious patterns?
3. **Context**: Do event markers help users understand document significance?
4. **Performance**: Does the visualization load in <3 seconds?
5. **Usability**: Can non-technical users operate all features?

---

## Open Questions

1. **Granularity**: Should the default view be monthly or yearly?
2. **Mobile**: Is mobile support required?
3. **Export**: What export formats are needed (PNG, PDF, SVG)?
4. **Hosting**: Where will the interactive dashboard be deployed?
5. **Updates**: Will new transcriptions need to be added incrementally?

---

## Dependencies

```
# Core visualization
plotly>=5.18.0
dash>=2.14.0
dash-bootstrap-components>=1.5.0

# Data processing
pandas>=2.0.0
numpy>=1.24.0

# Export
kaleido>=0.2.1  # For static image export
```

---

## File Structure

```
app/
└── timeline/
    ├── __init__.py
    ├── data_processor.py    # Data loading and aggregation
    ├── events.py            # Historical events database
    ├── charts.py            # Plotly chart generators
    ├── app.py               # Dash application
    └── export.py            # Static export utilities

research/technical/visualizations/
├── TIMELINE_PLAN.md         # This document
└── prototypes/
    └── timeline/            # Prototype notebooks/scripts
```

---

## Next Steps

1. [ ] Review and approve this plan
2. [ ] Create `app/timeline/` directory structure
3. [ ] Implement data processor
4. [ ] Build static Plotly prototype
5. [ ] Develop Dash interactive dashboard
6. [ ] Add Makefile targets
7. [ ] Document usage

---

## References

- [Plotly Timeline Examples](https://plotly.com/python/time-series/)
- [Dash User Guide](https://dash.plotly.com/)
- [Chile Declassification Project History](https://nsarchive.gwu.edu/project/chile-documentation-project)
- [Museum of Memory and Human Rights](https://ww3.museodelamemoria.cl/)
