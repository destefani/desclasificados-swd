# Frontend Redesign Design

**Date:** 2026-02-23
**Status:** Approved

## Goal

Replace the static GitHub Pages site with a modern, public-facing web application for exploring 21,512 declassified CIA documents about the Chilean dictatorship (1973-1990). Rich interactivity, inline PDF viewing, and server-side search/filtering.

## Architecture

```
localhost:3000 (frontend)          localhost:8000 (backend)
┌─────────────────────────┐        ┌─────────────────────────────┐
│  Next.js 15 + TypeScript│        │  FastAPI (Python)            │
│  frontend/              │──API──▶│  app/api/                    │
│                         │        │                              │
│  Pages:                 │        │  Reads from existing:        │
│  / (dashboard)          │        │  data/generated_transcripts/ │
│  /explorer              │        │  data/original_pdfs/         │
│  /entities              │        │  data/research_questions.json│
│  /reports/[id]          │        │  data/research_reports/      │
│  /about                 │        │  data/rag-v1.0.0/ (later)   │
└─────────────────────────┘        └─────────────────────────────┘
```

- Frontend and backend in the **same repo**
- Backend reads existing `data/` directory — no database migration
- No RAG chat for now — API designed to add it later
- Local-first development, deployment decisions deferred

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Next.js 15 (App Router) | File-based routing, SSR/SSG, API routes |
| Language | TypeScript | Type safety, better autocomplete |
| Styling | Tailwind CSS + shadcn/ui | Utility-first CSS + polished pre-built components |
| Charts | Recharts | React-native charting, simpler API than D3 |
| Network Graphs | react-force-graph-2d | Force-directed graphs for entity networks |
| Maps | react-leaflet | Same Leaflet as current site, React wrapper |
| PDF Viewer | react-pdf (pdf.js) | Inline PDF rendering, no external service |
| API State | TanStack Query | Caching, pagination, loading states |
| Package Manager | pnpm | Fast, disk-efficient |

## Pages

### Dashboard (`/`)
- Summary stats cards (total docs, transcription progress, confidence, sensitive content counts)
- Interactive zoomable timeline with historical event annotations
- Classification breakdown chart
- Top entities preview (top 10 people, orgs, keywords) linking to `/entities`
- Recent research questions linking to `/reports/[id]`
- Quick links to explorer, entities

### Document Explorer (`/explorer`)
- Search bar with instant fuzzy search
- Filter sidebar: date range slider, classification, document type, keywords
- Results grid/list toggle with document cards
- Server-side pagination (API handles filtering for 16k docs)
- Document detail panel with full metadata, text, and inline PDF viewer

### Entity Explorer (`/entities`)
- Tabbed navigation: People, Organizations, Keywords, Places
- Search + filter within each tab
- Entity detail page: related documents, co-occurring entities, mention timeline
- Network graph for entity connections

### Research Reports (`/reports`)
- Report index listing all research questions with status
- Individual report pages (`/reports/[id]`) with sections, quotes, tables, citations
- Linked document references opening in explorer with PDF viewer

### About (`/about`)
- Project context, methodology, limitations, attribution
- Static content

## Shared Components

| Component | Used In | Purpose |
|-----------|---------|---------|
| ClassificationBadge | Explorer, Dashboard, Reports | Color-coded TOP SECRET/SECRET/etc. |
| DocumentCard | Explorer, Dashboard | Document preview with metadata |
| PDFViewer | Explorer, Reports | Inline PDF viewing (pdf.js) |
| TimelineChart | Dashboard, Entity detail | Interactive zoomable timeline |
| NetworkGraph | Entities, Dashboard | Force-directed entity graph |
| SearchBar | Explorer, Entities | Fuzzy search with debounce |
| FilterSidebar | Explorer, Entities | Reusable filter panel |
| StatCard | Dashboard | Metric card with icon |

## Frontend Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx            # Dashboard (/)
│   │   ├── explorer/
│   │   │   └── page.tsx        # Document Explorer
│   │   ├── entities/
│   │   │   └── page.tsx        # Entity Explorer
│   │   ├── reports/
│   │   │   ├── page.tsx        # Reports index
│   │   │   └── [id]/page.tsx   # Individual report
│   │   ├── about/
│   │   │   └── page.tsx        # About page
│   │   └── layout.tsx          # Root layout (nav, footer)
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── charts/             # Timeline, classification, etc.
│   │   ├── documents/          # DocumentCard, PDFViewer, etc.
│   │   ├── entities/           # EntityCard, NetworkGraph, etc.
│   │   └── layout/             # Navbar, Sidebar, Footer
│   ├── lib/
│   │   ├── api.ts              # API client (fetch wrappers)
│   │   └── types.ts            # TypeScript types matching API
│   └── hooks/
│       ├── useDocuments.ts     # TanStack Query hooks
│       └── useEntities.ts
├── public/                     # Static assets
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## Backend API Structure

```
app/
├── api/                        # NEW: FastAPI REST API
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, CORS, routes
│   ├── routes/
│   │   ├── documents.py        # /api/documents, /api/documents/:id
│   │   ├── entities.py         # /api/entities
│   │   ├── stats.py            # /api/stats
│   │   └── pdf.py              # /api/pdf/:id
│   └── services/
│       ├── document_service.py # Load + filter JSON transcripts
│       └── entity_service.py   # Aggregate entity data
```

## API Contract

### GET /api/documents

Paginated, filterable document list.

**Query params:** `?page=1&page_size=25&q=letelier&date_from=1973-01-01&date_to=1976-12-31&classification=SECRET,TOP SECRET&type=MEMORANDUM,CABLE&keywords=OPERATION CONDOR&sort=date_desc`

**Response:**
```json
{
  "items": [
    {
      "id": "24736",
      "doc_id": "SANTIAGO 89675",
      "date": "1976-09-21",
      "classification": "SECRET",
      "type": "CABLE",
      "title": "...",
      "summary": "...",
      "pages": 3,
      "confidence": 0.92,
      "keywords": ["LETELIER", "ASSASSINATION"],
      "people_mentioned": ["LETELIER, ORLANDO"],
      "organizations_mentioned": ["DINA"],
      "countries_mentioned": ["CHILE", "USA"]
    }
  ],
  "total": 16222,
  "page": 1,
  "page_size": 25,
  "total_pages": 649
}
```

### GET /api/documents/:id

Full document detail including text content.

**Response:**
```json
{
  "id": "24736",
  "doc_id": "SANTIAGO 89675",
  "date": "1976-09-21",
  "classification": "SECRET",
  "...all metadata fields...",
  "original_text": "...",
  "reviewed_text": "...",
  "has_pdf": true
}
```

### GET /api/entities

**Query params:** `?type=person&q=pinochet&min_docs=10&sort=doc_count_desc&page=1&page_size=50`

**Response:**
```json
{
  "items": [
    {
      "name": "PINOCHET, AUGUSTO",
      "type": "person",
      "doc_count": 2847,
      "sample_doc_ids": ["24736", "25001", "25102"]
    }
  ],
  "total": 1055,
  "page": 1,
  "page_size": 50
}
```

### GET /api/entities/:name/documents

Documents mentioning a specific entity.

**Query params:** `?page=1&page_size=25`

### GET /api/stats

Dashboard aggregated statistics.

**Response:**
```json
{
  "total_documents": 16222,
  "total_pages": 48221,
  "avg_confidence": 0.881,
  "transcription_progress": { "completed": 16222, "total": 21512 },
  "classification_distribution": { "SECRET": 8234, "CONFIDENTIAL": 4521 },
  "type_distribution": { "CABLE": 5234, "MEMORANDUM": 3421 },
  "timeline": { "1970": 342, "1971": 289 },
  "sensitive_content": { "violence": 10482, "torture": 2081, "disappearances": 2038 },
  "top_people": [{ "name": "...", "count": 0 }],
  "top_organizations": [],
  "top_keywords": []
}
```

### GET /api/pdf/:id

Serves PDF binary stream with `Content-Disposition: inline`.

### GET /api/reports

Research report list.

### GET /api/reports/:id

Full research report content.

## Performance

- Backend loads all 16k JSON files into memory at startup (~80MB)
- All filtering and search happens in-memory (sub-second responses)
- Frontend uses TanStack Query for client-side caching and deduplication

## What Stays the Same

- Existing `data/` directory structure (untouched)
- Existing transcription pipeline (`app/transcribe.py`)
- Existing RAG system (`app/rag/`) — will connect later
- Existing Makefile commands — new ones added alongside

## What's New

- `frontend/` — Next.js application
- `app/api/` — FastAPI REST API
- `make dev` — starts both servers
- `make dev-frontend` / `make dev-backend` — start individually

## Future (Not in Scope Now)

- RAG chat interface (`/chat` page + `POST /api/chat` streaming endpoint)
- Deployment to cloud hosting
- Authentication (if needed for admin features)
