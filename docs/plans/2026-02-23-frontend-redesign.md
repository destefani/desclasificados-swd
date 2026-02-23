# Frontend Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-stack web application (Next.js frontend + FastAPI backend) to replace the static GitHub Pages site for exploring 21,512 declassified CIA documents.

**Architecture:** FastAPI backend reads existing JSON transcripts from `data/generated_transcripts/gpt-5-mini-v2.2.0/` into memory at startup. Exposes REST API on port 8000. Next.js frontend on port 3000 consumes the API. Both in the same repo.

**Tech Stack:** Next.js 15 + TypeScript + Tailwind + shadcn/ui | FastAPI + Pydantic | Recharts, react-pdf, react-force-graph-2d, react-leaflet | TanStack Query | pnpm

**Design doc:** `docs/plans/2026-02-23-frontend-redesign-design.md`

---

## Task 1: FastAPI Backend — Document Service

The data layer that loads all 16k JSON transcripts into memory and provides search/filter/pagination.

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/services/__init__.py`
- Create: `app/api/services/document_service.py`
- Test: `tests/unit/test_document_service.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_document_service.py
import pytest
import json
import tempfile
from pathlib import Path


@pytest.fixture
def sample_transcripts(tmp_path: Path) -> Path:
    """Create a temp directory with 3 sample JSON transcript files."""
    for i, (doc_id, date, classification, doc_type) in enumerate([
        ("00001", "1973-09-11", "TOP SECRET", "MEMORANDUM"),
        ("00002", "1976-09-21", "SECRET", "CABLE"),
        ("00003", "1970-11-03", "CONFIDENTIAL", "REPORT"),
    ]):
        data = {
            "metadata": {
                "document_id": doc_id,
                "case_number": f"C00{i}",
                "document_date": date,
                "classification_level": classification,
                "document_type": doc_type,
                "document_title": f"Test Document {doc_id}",
                "document_summary": f"Summary for document {doc_id}",
                "author": "SMITH, JOHN",
                "recipients": ["DOE, JANE"],
                "people_mentioned": ["PINOCHET, AUGUSTO"],
                "organizations_mentioned": [
                    {"name": "CIA", "type": "INTELLIGENCE_AGENCY", "country": "UNITED STATES"}
                ],
                "keywords": ["COUP 1973", "CIA"],
                "country": ["CHILE"],
                "city": ["SANTIAGO"],
                "other_place": [],
                "language": "ENGLISH",
                "page_count": i + 1,
                "financial_references": {"has_financial_content": False, "amounts": [], "financial_actors": [], "purposes": []},
                "violence_references": {"has_violence_content": False, "incident_types": [], "victims": [], "perpetrators": []},
                "torture_references": {"has_torture_content": False, "detention_centers": [], "victims": [], "perpetrators": [], "methods_mentioned": []},
                "disappearance_references": {"has_disappearance_content": False, "victims": [], "perpetrators": [], "locations": [], "dates_mentioned": []},
            },
            "original_text": f"Original text for {doc_id}",
            "reviewed_text": f"Reviewed text for {doc_id}",
            "confidence": {"overall": 0.9, "concerns": []},
        }
        (tmp_path / f"{doc_id}.json").write_text(json.dumps(data))
    return tmp_path


class TestDocumentService:
    def test_load_documents(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        assert svc.total_documents == 3

    def test_list_documents_default(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(page=1, page_size=25)
        assert result["total"] == 3
        assert len(result["items"]) == 3
        # Default sort is date_desc
        assert result["items"][0]["id"] == "00002"  # 1976 first

    def test_list_documents_pagination(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(page=1, page_size=2)
        assert len(result["items"]) == 2
        assert result["total_pages"] == 2
        result2 = svc.list_documents(page=2, page_size=2)
        assert len(result2["items"]) == 1

    def test_filter_by_classification(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(classification=["SECRET"])
        assert result["total"] == 1
        assert result["items"][0]["id"] == "00002"

    def test_filter_by_date_range(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(date_from="1973-01-01", date_to="1976-12-31")
        assert result["total"] == 2

    def test_search_by_query(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(q="00002")
        assert result["total"] == 1

    def test_get_document_by_id(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        doc = svc.get_document("00001")
        assert doc is not None
        assert doc["id"] == "00001"
        assert "original_text" in doc
        assert "reviewed_text" in doc

    def test_get_document_not_found(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        doc = svc.get_document("99999")
        assert doc is None

    def test_sort_date_asc(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(sort="date_asc")
        assert result["items"][0]["id"] == "00003"  # 1970 first

    def test_filter_by_type(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        svc = DocumentService(sample_transcripts)
        result = svc.list_documents(doc_type=["CABLE"])
        assert result["total"] == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_document_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.api'`

**Step 3: Write minimal implementation**

```python
# app/api/__init__.py
# (empty)

# app/api/services/__init__.py
# (empty)

# app/api/services/document_service.py
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DocumentService:
    """Loads JSON transcripts into memory and provides search/filter/pagination."""

    def __init__(self, transcripts_dir: Path) -> None:
        self._documents: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}
        self._load(transcripts_dir)

    @property
    def total_documents(self) -> int:
        return len(self._documents)

    def _load(self, transcripts_dir: Path) -> None:
        """Load all JSON files from the transcripts directory."""
        files = sorted(transcripts_dir.glob("*.json"))
        for f in files:
            try:
                raw = json.loads(f.read_text())
                doc = self._normalize(raw)
                self._documents.append(doc)
                self._by_id[doc["id"]] = doc
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Skipping %s: %s", f.name, e)
        logger.info("Loaded %d documents from %s", len(self._documents), transcripts_dir)

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten transcript JSON into a consistent document dict."""
        meta = raw.get("metadata", {})
        confidence = raw.get("confidence", {})
        orgs = meta.get("organizations_mentioned", [])
        org_names = [o["name"] if isinstance(o, dict) else o for o in orgs]

        return {
            "id": meta.get("document_id", ""),
            "doc_id": meta.get("case_number", ""),
            "date": meta.get("document_date", ""),
            "classification": meta.get("classification_level", ""),
            "type": meta.get("document_type", ""),
            "title": meta.get("document_title", ""),
            "summary": meta.get("document_summary", ""),
            "pages": meta.get("page_count", 1),
            "confidence": confidence.get("overall", 0.0),
            "concerns": confidence.get("concerns", []),
            "author": meta.get("author", ""),
            "recipients": meta.get("recipients", []),
            "keywords": meta.get("keywords", []),
            "people_mentioned": meta.get("people_mentioned", []),
            "organizations_mentioned": org_names,
            "countries_mentioned": meta.get("country", []),
            "cities_mentioned": meta.get("city", []),
            "language": meta.get("language", ""),
            "original_text": raw.get("original_text", ""),
            "reviewed_text": raw.get("reviewed_text", ""),
            "has_financial_content": meta.get("financial_references", {}).get("has_financial_content", False),
            "has_violence_content": meta.get("violence_references", {}).get("has_violence_content", False),
            "has_torture_content": meta.get("torture_references", {}).get("has_torture_content", False),
            "has_disappearance_content": meta.get("disappearance_references", {}).get("has_disappearance_content", False),
            # Full metadata kept for detail view
            "_raw_metadata": meta,
            "_financial_references": meta.get("financial_references", {}),
            "_violence_references": meta.get("violence_references", {}),
            "_torture_references": meta.get("torture_references", {}),
            "_disappearance_references": meta.get("disappearance_references", {}),
        }

    def list_documents(
        self,
        page: int = 1,
        page_size: int = 25,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        classification: list[str] | None = None,
        doc_type: list[str] | None = None,
        keywords: list[str] | None = None,
        sort: str = "date_desc",
    ) -> dict[str, Any]:
        """Filter, sort, and paginate documents."""
        filtered = self._documents

        if q:
            q_lower = q.lower()
            filtered = [
                d for d in filtered
                if q_lower in d["title"].lower()
                or q_lower in d["summary"].lower()
                or q_lower in d["id"].lower()
                or q_lower in d["doc_id"].lower()
            ]

        if date_from:
            filtered = [d for d in filtered if d["date"] >= date_from]
        if date_to:
            filtered = [d for d in filtered if d["date"] <= date_to]

        if classification:
            cls_set = set(classification)
            filtered = [d for d in filtered if d["classification"] in cls_set]

        if doc_type:
            type_set = set(doc_type)
            filtered = [d for d in filtered if d["type"] in type_set]

        if keywords:
            kw_set = set(k.upper() for k in keywords)
            filtered = [d for d in filtered if kw_set & set(d["keywords"])]

        # Sort
        reverse = True
        sort_key = "date"
        if sort == "date_asc":
            sort_key, reverse = "date", False
        elif sort == "date_desc":
            sort_key, reverse = "date", True
        elif sort == "confidence":
            sort_key, reverse = "confidence", True
        elif sort == "pages":
            sort_key, reverse = "pages", True

        filtered = sorted(filtered, key=lambda d: d.get(sort_key, ""), reverse=reverse)

        # Paginate
        total = len(filtered)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        end = start + page_size
        page_items = filtered[start:end]

        # Strip heavy fields from list items
        items = [self._to_list_item(d) for d in page_items]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def _to_list_item(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Return document without text fields (for list views)."""
        return {
            k: v for k, v in doc.items()
            if k not in ("original_text", "reviewed_text", "_raw_metadata",
                         "_financial_references", "_violence_references",
                         "_torture_references", "_disappearance_references")
        }

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Return full document by ID, including text and raw metadata."""
        doc = self._by_id.get(doc_id)
        if doc is None:
            return None
        result = {k: v for k, v in doc.items() if not k.startswith("_")}
        result["has_pdf"] = True
        result["financial_references"] = doc.get("_financial_references", {})
        result["violence_references"] = doc.get("_violence_references", {})
        result["torture_references"] = doc.get("_torture_references", {})
        result["disappearance_references"] = doc.get("_disappearance_references", {})
        return result
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_document_service.py -v`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add app/api/__init__.py app/api/services/__init__.py app/api/services/document_service.py tests/unit/test_document_service.py
git commit -m "feat(api): add document service with search, filter, pagination"
```

---

## Task 2: FastAPI Backend — Entity Service

Aggregates entities (people, orgs, keywords, places) from loaded documents.

**Files:**
- Create: `app/api/services/entity_service.py`
- Test: `tests/unit/test_entity_service.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_entity_service.py
import pytest
from pathlib import Path
from tests.unit.test_document_service import sample_transcripts  # reuse fixture


class TestEntityService:
    def test_build_entities(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        assert ent_svc.total_entities > 0

    def test_list_entities_by_type(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.list_entities(entity_type="person")
        assert result["total"] > 0
        for item in result["items"]:
            assert item["type"] == "person"

    def test_list_entities_search(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.list_entities(q="pinochet")
        assert result["total"] >= 1

    def test_list_entities_min_docs(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.list_entities(min_docs=100)
        assert result["total"] == 0

    def test_entity_documents(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.entity_documents("PINOCHET, AUGUSTO", "person")
        assert result["total"] == 3  # all 3 docs mention PINOCHET

    def test_sort_by_doc_count(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.entity_service import EntityService
        doc_svc = DocumentService(sample_transcripts)
        ent_svc = EntityService(doc_svc)
        result = ent_svc.list_entities(sort="doc_count_desc")
        counts = [item["doc_count"] for item in result["items"]]
        assert counts == sorted(counts, reverse=True)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_entity_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.api.services.entity_service'`

**Step 3: Write minimal implementation**

```python
# app/api/services/entity_service.py
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.api.services.document_service import DocumentService


class EntityService:
    """Aggregates entities from documents and provides search/filter."""

    def __init__(self, document_service: DocumentService) -> None:
        self._entities: list[dict[str, Any]] = []
        self._by_key: dict[tuple[str, str], dict[str, Any]] = {}
        self._build(document_service)

    @property
    def total_entities(self) -> int:
        return len(self._entities)

    def _build(self, doc_svc: DocumentService) -> None:
        """Extract and count entities from all documents."""
        counts: dict[tuple[str, str], set[str]] = defaultdict(set)

        for doc in doc_svc._documents:
            doc_id = doc["id"]
            for person in doc.get("people_mentioned", []):
                counts[("person", person)].add(doc_id)
            for org in doc.get("organizations_mentioned", []):
                counts[("organization", org)].add(doc_id)
            for kw in doc.get("keywords", []):
                counts[("keyword", kw)].add(doc_id)
            for country in doc.get("countries_mentioned", []):
                counts[("place", country)].add(doc_id)
            for city in doc.get("cities_mentioned", []):
                counts[("place", city)].add(doc_id)

        for (etype, name), doc_ids in counts.items():
            entity = {
                "name": name,
                "type": etype,
                "doc_count": len(doc_ids),
                "doc_ids": doc_ids,
                "sample_doc_ids": sorted(doc_ids)[:5],
            }
            self._entities.append(entity)
            self._by_key[(etype, name)] = entity

    def list_entities(
        self,
        entity_type: str | None = None,
        q: str | None = None,
        min_docs: int = 1,
        sort: str = "doc_count_desc",
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        filtered = self._entities

        if entity_type:
            filtered = [e for e in filtered if e["type"] == entity_type]
        if q:
            q_lower = q.lower()
            filtered = [e for e in filtered if q_lower in e["name"].lower()]
        if min_docs > 1:
            filtered = [e for e in filtered if e["doc_count"] >= min_docs]

        # Sort
        if sort == "doc_count_desc":
            filtered = sorted(filtered, key=lambda e: e["doc_count"], reverse=True)
        elif sort == "doc_count_asc":
            filtered = sorted(filtered, key=lambda e: e["doc_count"])
        elif sort == "name_asc":
            filtered = sorted(filtered, key=lambda e: e["name"])

        total = len(filtered)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        items = [
            {"name": e["name"], "type": e["type"], "doc_count": e["doc_count"], "sample_doc_ids": e["sample_doc_ids"]}
            for e in filtered[start:start + page_size]
        ]

        return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}

    def entity_documents(
        self, name: str, entity_type: str, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        entity = self._by_key.get((entity_type, name))
        if entity is None:
            return {"entity": name, "type": entity_type, "items": [], "total": 0}
        doc_ids = sorted(entity["doc_ids"])
        total = len(doc_ids)
        start = (page - 1) * page_size
        return {
            "entity": name,
            "type": entity_type,
            "doc_ids": doc_ids[start:start + page_size],
            "total": total,
        }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_entity_service.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add app/api/services/entity_service.py tests/unit/test_entity_service.py
git commit -m "feat(api): add entity service with aggregation and filtering"
```

---

## Task 3: FastAPI Backend — Stats Service

Aggregates dashboard statistics from loaded documents.

**Files:**
- Create: `app/api/services/stats_service.py`
- Test: `tests/unit/test_stats_service.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_stats_service.py
import pytest
from pathlib import Path
from tests.unit.test_document_service import sample_transcripts


class TestStatsService:
    def test_compute_stats(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.stats_service import StatsService
        doc_svc = DocumentService(sample_transcripts)
        stats = StatsService(doc_svc)
        result = stats.get_stats(total_pdfs=21512)
        assert result["total_documents"] == 3
        assert result["transcription_progress"]["completed"] == 3
        assert result["transcription_progress"]["total"] == 21512

    def test_classification_distribution(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.stats_service import StatsService
        doc_svc = DocumentService(sample_transcripts)
        stats = StatsService(doc_svc)
        result = stats.get_stats(total_pdfs=3)
        dist = result["classification_distribution"]
        assert dist["TOP SECRET"] == 1
        assert dist["SECRET"] == 1
        assert dist["CONFIDENTIAL"] == 1

    def test_timeline(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.stats_service import StatsService
        doc_svc = DocumentService(sample_transcripts)
        stats = StatsService(doc_svc)
        result = stats.get_stats(total_pdfs=3)
        assert "1973" in result["timeline"]
        assert result["timeline"]["1973"] == 1

    def test_avg_confidence(self, sample_transcripts: Path):
        from app.api.services.document_service import DocumentService
        from app.api.services.stats_service import StatsService
        doc_svc = DocumentService(sample_transcripts)
        stats = StatsService(doc_svc)
        result = stats.get_stats(total_pdfs=3)
        assert result["avg_confidence"] == 0.9
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_stats_service.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/api/services/stats_service.py
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.api.services.document_service import DocumentService


class StatsService:
    """Computes aggregated statistics from loaded documents."""

    def __init__(self, document_service: DocumentService) -> None:
        self._doc_svc = document_service

    def get_stats(self, total_pdfs: int = 21512) -> dict[str, Any]:
        docs = self._doc_svc._documents
        total = len(docs)

        # Classification distribution
        classification_dist = Counter(d["classification"] for d in docs)

        # Type distribution
        type_dist = Counter(d["type"] for d in docs)

        # Timeline (yearly)
        timeline: dict[str, int] = defaultdict(int)
        for d in docs:
            year = d["date"][:4] if d["date"] else "unknown"
            if year != "unknown":
                timeline[year] += 1

        # Avg confidence
        confidences = [d["confidence"] for d in docs if d["confidence"] > 0]
        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        # Total pages
        total_pages = sum(d.get("pages", 1) for d in docs)

        # Sensitive content counts
        violence = sum(1 for d in docs if d.get("has_violence_content"))
        torture = sum(1 for d in docs if d.get("has_torture_content"))
        disappearances = sum(1 for d in docs if d.get("has_disappearance_content"))
        financial = sum(1 for d in docs if d.get("has_financial_content"))

        # Top entities
        people_counter: Counter[str] = Counter()
        org_counter: Counter[str] = Counter()
        kw_counter: Counter[str] = Counter()
        for d in docs:
            people_counter.update(d.get("people_mentioned", []))
            org_counter.update(d.get("organizations_mentioned", []))
            kw_counter.update(d.get("keywords", []))

        return {
            "total_documents": total,
            "total_pages": total_pages,
            "avg_confidence": avg_confidence,
            "transcription_progress": {"completed": total, "total": total_pdfs},
            "classification_distribution": dict(classification_dist),
            "type_distribution": dict(type_dist),
            "timeline": dict(sorted(timeline.items())),
            "sensitive_content": {
                "violence": violence,
                "torture": torture,
                "disappearances": disappearances,
                "financial": financial,
            },
            "top_people": [{"name": n, "count": c} for n, c in people_counter.most_common(20)],
            "top_organizations": [{"name": n, "count": c} for n, c in org_counter.most_common(20)],
            "top_keywords": [{"name": n, "count": c} for n, c in kw_counter.most_common(20)],
        }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_stats_service.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add app/api/services/stats_service.py tests/unit/test_stats_service.py
git commit -m "feat(api): add stats service for dashboard aggregation"
```

---

## Task 4: FastAPI Backend — API Routes & App

Wire up the services into FastAPI routes.

**Files:**
- Create: `app/api/routes/__init__.py`
- Create: `app/api/routes/documents.py`
- Create: `app/api/routes/entities.py`
- Create: `app/api/routes/stats.py`
- Create: `app/api/routes/pdf.py`
- Create: `app/api/routes/reports.py`
- Create: `app/api/main.py`
- Test: `tests/unit/test_api_routes.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_api_routes.py
import pytest
import json
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    """Create a test client with sample data."""
    # Create sample transcripts
    for i, (doc_id, date, classification) in enumerate([
        ("00001", "1973-09-11", "TOP SECRET"),
        ("00002", "1976-09-21", "SECRET"),
    ]):
        data = {
            "metadata": {
                "document_id": doc_id,
                "case_number": f"C00{i}",
                "document_date": date,
                "classification_level": classification,
                "document_type": "CABLE",
                "document_title": f"Test Doc {doc_id}",
                "document_summary": f"Summary {doc_id}",
                "author": "",
                "recipients": [],
                "people_mentioned": ["PINOCHET, AUGUSTO"],
                "organizations_mentioned": [],
                "keywords": ["CIA"],
                "country": ["CHILE"],
                "city": [],
                "other_place": [],
                "language": "ENGLISH",
                "page_count": 1,
                "financial_references": {"has_financial_content": False, "amounts": [], "financial_actors": [], "purposes": []},
                "violence_references": {"has_violence_content": False, "incident_types": [], "victims": [], "perpetrators": []},
                "torture_references": {"has_torture_content": False, "detention_centers": [], "victims": [], "perpetrators": [], "methods_mentioned": []},
                "disappearance_references": {"has_disappearance_content": False, "victims": [], "perpetrators": [], "locations": [], "dates_mentioned": []},
            },
            "original_text": "Text",
            "reviewed_text": "Reviewed",
            "confidence": {"overall": 0.9, "concerns": []},
        }
        (tmp_path / f"{doc_id}.json").write_text(json.dumps(data))

    # Create a sample PDF
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / "00001.pdf").write_bytes(b"%PDF-1.4 fake pdf")

    # Create research questions
    rq = tmp_path / "research_questions.json"
    rq.write_text(json.dumps({
        "version": "1.0.0",
        "description": "test",
        "questions": [{"id": "RQ-001", "question": "Test?", "date_asked": "2025-01-01",
                        "category": "OTHER", "status": "unanswered", "rag_results": "",
                        "relevance_score": 0, "related_docs": [], "notes": None,
                        "pdf_report": None, "html_report": None}]
    }))

    from app.api.main import create_app
    app = create_app(
        transcripts_dir=tmp_path,
        pdf_dir=pdf_dir,
        research_questions_path=rq,
        research_reports_dir=tmp_path,
        total_pdfs=100,
    )
    return TestClient(app)


class TestDocumentsAPI:
    def test_list_documents(self, api_client: TestClient):
        resp = api_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_documents_with_filter(self, api_client: TestClient):
        resp = api_client.get("/api/documents?classification=SECRET")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_document(self, api_client: TestClient):
        resp = api_client.get("/api/documents/00001")
        assert resp.status_code == 200
        assert resp.json()["id"] == "00001"
        assert "reviewed_text" in resp.json()

    def test_get_document_not_found(self, api_client: TestClient):
        resp = api_client.get("/api/documents/99999")
        assert resp.status_code == 404


class TestEntitiesAPI:
    def test_list_entities(self, api_client: TestClient):
        resp = api_client.get("/api/entities")
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_filter_by_type(self, api_client: TestClient):
        resp = api_client.get("/api/entities?type=person")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["type"] == "person"


class TestStatsAPI:
    def test_get_stats(self, api_client: TestClient):
        resp = api_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 2
        assert "classification_distribution" in data


class TestPdfAPI:
    def test_serve_pdf(self, api_client: TestClient):
        resp = api_client.get("/api/pdf/00001")
        assert resp.status_code == 200

    def test_pdf_not_found(self, api_client: TestClient):
        resp = api_client.get("/api/pdf/99999")
        assert resp.status_code == 404


class TestReportsAPI:
    def test_list_reports(self, api_client: TestClient):
        resp = api_client.get("/api/reports")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_api_routes.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# app/api/routes/__init__.py
# (empty)

# app/api/routes/documents.py
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def init_router(doc_service):
    @router.get("/api/documents")
    def list_documents(
        page: int = 1,
        page_size: int = 25,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        classification: str | None = None,
        type: str | None = None,
        keywords: str | None = None,
        sort: str = "date_desc",
    ):
        cls_list = classification.split(",") if classification else None
        type_list = type.split(",") if type else None
        kw_list = keywords.split(",") if keywords else None
        return doc_service.list_documents(
            page=page, page_size=page_size, q=q,
            date_from=date_from, date_to=date_to,
            classification=cls_list, doc_type=type_list,
            keywords=kw_list, sort=sort,
        )

    @router.get("/api/documents/{doc_id}")
    def get_document(doc_id: str):
        doc = doc_service.get_document(doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc

    return router


# app/api/routes/entities.py
from fastapi import APIRouter, HTTPException

router = APIRouter()


def init_router(entity_service):
    @router.get("/api/entities")
    def list_entities(
        type: str | None = None,
        q: str | None = None,
        min_docs: int = 1,
        sort: str = "doc_count_desc",
        page: int = 1,
        page_size: int = 50,
    ):
        return entity_service.list_entities(
            entity_type=type, q=q, min_docs=min_docs,
            sort=sort, page=page, page_size=page_size,
        )

    @router.get("/api/entities/{name}/documents")
    def entity_documents(name: str, type: str = "person", page: int = 1, page_size: int = 25):
        return entity_service.entity_documents(name, type, page=page, page_size=page_size)

    return router


# app/api/routes/stats.py
from fastapi import APIRouter

router = APIRouter()


def init_router(stats_service):
    @router.get("/api/stats")
    def get_stats():
        return stats_service.get_stats()

    return router


# app/api/routes/pdf.py
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


def init_router(pdf_dir: Path):
    @router.get("/api/pdf/{doc_id}")
    def serve_pdf(doc_id: str):
        # Prevent path traversal
        if ".." in doc_id:
            raise HTTPException(status_code=400, detail="Invalid document ID")
        pdf_path = pdf_dir / f"{doc_id}.pdf"
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF not found")
        return FileResponse(pdf_path, media_type="application/pdf")

    return router


# app/api/routes/reports.py
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()


def init_router(research_questions_path: Path, research_reports_dir: Path):
    @router.get("/api/reports")
    def list_reports():
        if not research_questions_path.exists():
            return {"items": []}
        data = json.loads(research_questions_path.read_text())
        return {"items": data.get("questions", [])}

    @router.get("/api/reports/{report_id}")
    def get_report(report_id: str):
        # Try rich report first
        report_file = research_reports_dir / f"{report_id.lower()}.json"
        if report_file.exists():
            return json.loads(report_file.read_text())
        # Fallback to basic info from tracker
        if research_questions_path.exists():
            data = json.loads(research_questions_path.read_text())
            for q in data.get("questions", []):
                if q["id"].lower() == report_id.lower():
                    return q
        raise HTTPException(status_code=404, detail="Report not found")

    return router


# app/api/main.py
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.services.document_service import DocumentService
from app.api.services.entity_service import EntityService
from app.api.services.stats_service import StatsService
from app.api.routes import documents, entities, stats, pdf, reports


def create_app(
    transcripts_dir: Path | None = None,
    pdf_dir: Path | None = None,
    research_questions_path: Path | None = None,
    research_reports_dir: Path | None = None,
    total_pdfs: int = 21512,
) -> FastAPI:
    from app.config import DATA_DIR, TRANSCRIPTS_DIR, METADATA_SCHEMA_VERSION

    if transcripts_dir is None:
        model_dir = f"gpt-5-mini-{METADATA_SCHEMA_VERSION}"
        transcripts_dir = TRANSCRIPTS_DIR / model_dir
    if pdf_dir is None:
        pdf_dir = DATA_DIR / "original_pdfs"
    if research_questions_path is None:
        research_questions_path = DATA_DIR / "research_questions.json"
    if research_reports_dir is None:
        research_reports_dir = DATA_DIR / "research_reports"

    # Initialize services
    doc_svc = DocumentService(transcripts_dir)
    ent_svc = EntityService(doc_svc)
    stats_svc = StatsService(doc_svc)
    stats_svc._total_pdfs = total_pdfs

    # Override get_stats to use configured total
    original_get_stats = stats_svc.get_stats
    stats_svc.get_stats = lambda: original_get_stats(total_pdfs=total_pdfs)

    app = FastAPI(title="Desclasificados API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Init and include routers
    app.include_router(documents.init_router(doc_svc))
    app.include_router(entities.init_router(ent_svc))
    app.include_router(stats.init_router(stats_svc))
    app.include_router(pdf.init_router(pdf_dir))
    app.include_router(reports.init_router(research_questions_path, research_reports_dir))

    @app.get("/api/health")
    def health():
        return {"status": "ok", "documents_loaded": doc_svc.total_documents}

    return app
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_api_routes.py -v`
Expected: All 9 tests PASS

**Step 5: Run all tests**

Run: `uv run pytest tests/unit/ -v`
Expected: All previous tests + new tests PASS

**Step 6: Add Makefile targets and CLI entrypoint**

Add to the end of `Makefile`:

```makefile
# Frontend Development
dev-backend:  ## Start FastAPI backend on port 8001
	uv run uvicorn app.api.main:app --reload --port 8001 --factory

dev-frontend:  ## Start Next.js frontend on port 3000
	cd frontend && pnpm dev

dev:  ## Start both backend and frontend
	@echo "Starting backend on :8001 and frontend on :3000..."
	@make dev-backend & make dev-frontend
```

Note: Use port 8001 for the API to avoid conflicting with `make serve` / `make explorer-serve` on 8000.

Update `app/api/main.py` to add a factory function:

```python
# Add at the bottom of app/api/main.py
app = create_app()
```

**Step 7: Commit**

```bash
git add app/api/routes/ app/api/main.py tests/unit/test_api_routes.py Makefile
git commit -m "feat(api): add FastAPI routes for documents, entities, stats, pdf, reports"
```

---

## Task 5: Next.js Frontend — Project Scaffolding

Set up the Next.js project with TypeScript, Tailwind, shadcn/ui.

**Files:**
- Create: `frontend/` (entire directory via CLI)

**Step 1: Scaffold Next.js project**

```bash
cd /Users/marcelo/code/desclasificados-swd
pnpm create next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-pnpm \
  --turbopack
```

**Step 2: Install dependencies**

```bash
cd frontend
pnpm add @tanstack/react-query recharts react-pdf
pnpm add -D @types/node
```

**Step 3: Initialize shadcn/ui**

```bash
cd frontend
pnpm dlx shadcn@latest init -d
```

**Step 4: Add commonly used shadcn components**

```bash
cd frontend
pnpm dlx shadcn@latest add badge button card input select tabs table dialog separator skeleton
```

**Step 5: Configure API proxy**

Edit `frontend/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8001/api/:path*",
      },
    ];
  },
};

export default nextConfig;
```

**Step 6: Create shared types**

```typescript
// frontend/src/lib/types.ts
export interface DocumentListItem {
  id: string;
  doc_id: string;
  date: string;
  classification: "TOP SECRET" | "SECRET" | "CONFIDENTIAL" | "UNCLASSIFIED";
  type: string;
  title: string;
  summary: string;
  pages: number;
  confidence: number;
  keywords: string[];
  people_mentioned: string[];
  organizations_mentioned: string[];
  countries_mentioned: string[];
}

export interface DocumentDetail extends DocumentListItem {
  author: string;
  recipients: string[];
  language: string;
  original_text: string;
  reviewed_text: string;
  has_pdf: boolean;
  financial_references: Record<string, unknown>;
  violence_references: Record<string, unknown>;
  torture_references: Record<string, unknown>;
  disappearance_references: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Entity {
  name: string;
  type: "person" | "organization" | "keyword" | "place";
  doc_count: number;
  sample_doc_ids: string[];
}

export interface StatsResponse {
  total_documents: number;
  total_pages: number;
  avg_confidence: number;
  transcription_progress: { completed: number; total: number };
  classification_distribution: Record<string, number>;
  type_distribution: Record<string, number>;
  timeline: Record<string, number>;
  sensitive_content: {
    violence: number;
    torture: number;
    disappearances: number;
    financial: number;
  };
  top_people: { name: string; count: number }[];
  top_organizations: { name: string; count: number }[];
  top_keywords: { name: string; count: number }[];
}

export interface ResearchQuestion {
  id: string;
  question: string;
  date_asked: string;
  category: string;
  status: "unanswered" | "partially_answered" | "answered" | "needs_more_data";
  rag_results: string;
  relevance_score: number;
  related_docs: string[];
}
```

**Step 7: Create API client**

```typescript
// frontend/src/lib/api.ts
import type {
  DocumentListItem,
  DocumentDetail,
  Entity,
  PaginatedResponse,
  StatsResponse,
  ResearchQuestion,
} from "./types";

const BASE = "/api";

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface DocumentFilters {
  page?: number;
  page_size?: number;
  q?: string;
  date_from?: string;
  date_to?: string;
  classification?: string[];
  type?: string[];
  keywords?: string[];
  sort?: string;
}

export function fetchDocuments(filters: DocumentFilters = {}) {
  const params = new URLSearchParams();
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  if (filters.q) params.set("q", filters.q);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.classification?.length) params.set("classification", filters.classification.join(","));
  if (filters.type?.length) params.set("type", filters.type.join(","));
  if (filters.keywords?.length) params.set("keywords", filters.keywords.join(","));
  if (filters.sort) params.set("sort", filters.sort);
  return fetchJSON<PaginatedResponse<DocumentListItem>>(`${BASE}/documents?${params}`);
}

export function fetchDocument(id: string) {
  return fetchJSON<DocumentDetail>(`${BASE}/documents/${id}`);
}

export interface EntityFilters {
  type?: string;
  q?: string;
  min_docs?: number;
  sort?: string;
  page?: number;
  page_size?: number;
}

export function fetchEntities(filters: EntityFilters = {}) {
  const params = new URLSearchParams();
  if (filters.type) params.set("type", filters.type);
  if (filters.q) params.set("q", filters.q);
  if (filters.min_docs) params.set("min_docs", String(filters.min_docs));
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  return fetchJSON<PaginatedResponse<Entity>>(`${BASE}/entities?${params}`);
}

export function fetchStats() {
  return fetchJSON<StatsResponse>(`${BASE}/stats`);
}

export function fetchReports() {
  return fetchJSON<{ items: ResearchQuestion[] }>(`${BASE}/reports`);
}

export function fetchReport(id: string) {
  return fetchJSON<Record<string, unknown>>(`${BASE}/reports/${id}`);
}

export function pdfUrl(docId: string) {
  return `${BASE}/pdf/${docId}`;
}
```

**Step 8: Create TanStack Query provider**

```typescript
// frontend/src/components/providers.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60 * 1000, retry: 1 },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

**Step 9: Update root layout**

```typescript
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Desclasificados — CIA Declassified Documents on Chile",
  description:
    "Explore 21,000+ declassified CIA documents about the Chilean dictatorship (1973-1990)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

**Step 10: Verify it runs**

```bash
cd frontend && pnpm dev
```

Open http://localhost:3000 — should see the default Next.js page with no errors.

**Step 11: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Next.js project with TypeScript, Tailwind, shadcn/ui, API client"
```

---

## Task 6: Frontend — Shared Layout & Navigation

Create the app shell: navbar, sidebar, and footer used on all pages.

**Files:**
- Create: `frontend/src/components/layout/navbar.tsx`
- Create: `frontend/src/components/layout/footer.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`

**Step 1: Create Navbar**

```typescript
// frontend/src/components/layout/navbar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/explorer", label: "Documents" },
  { href: "/entities", label: "Entities" },
  { href: "/reports", label: "Research" },
  { href: "/about", label: "About" },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <Link href="/" className="mr-8 font-bold text-lg">
          Desclasificados
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          {NAV_ITEMS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={
                pathname === href
                  ? "text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground transition-colors"
              }
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
```

**Step 2: Create Footer**

```typescript
// frontend/src/components/layout/footer.tsx
export function Footer() {
  return (
    <footer className="border-t py-6 text-center text-sm text-muted-foreground">
      <div className="container">
        Desclasificados — Declassified CIA documents on Chile (1973-1990).
        Open source research project.
      </div>
    </footer>
  );
}
```

**Step 3: Update layout.tsx to include Navbar and Footer**

Replace the `frontend/src/app/layout.tsx` body content:

```typescript
<body className={inter.className}>
  <Providers>
    <div className="relative flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  </Providers>
</body>
```

Add imports for Navbar and Footer at the top.

**Step 4: Verify**

```bash
cd frontend && pnpm dev
```

Check http://localhost:3000 — should see nav bar and footer.

**Step 5: Commit**

```bash
git add frontend/src/components/layout/ frontend/src/app/layout.tsx
git commit -m "feat(frontend): add navbar and footer layout components"
```

---

## Task 7: Frontend — Dashboard Page

The main landing page with stats, timeline chart, classification chart, and top entities.

**Files:**
- Create: `frontend/src/components/documents/classification-badge.tsx`
- Create: `frontend/src/components/charts/classification-chart.tsx`
- Create: `frontend/src/components/charts/timeline-chart.tsx`
- Create: `frontend/src/hooks/useStats.ts`
- Modify: `frontend/src/app/page.tsx`

**Step 1: Create ClassificationBadge (shared component)**

```typescript
// frontend/src/components/documents/classification-badge.tsx
import { Badge } from "@/components/ui/badge";

const COLORS: Record<string, string> = {
  "TOP SECRET": "bg-red-600 text-white hover:bg-red-600",
  SECRET: "bg-orange-500 text-white hover:bg-orange-500",
  CONFIDENTIAL: "bg-yellow-500 text-black hover:bg-yellow-500",
  UNCLASSIFIED: "bg-green-600 text-white hover:bg-green-600",
};

export function ClassificationBadge({
  level,
}: {
  level: string;
}) {
  return (
    <Badge className={COLORS[level] ?? "bg-gray-500 text-white"}>
      {level}
    </Badge>
  );
}
```

**Step 2: Create useStats hook**

```typescript
// frontend/src/hooks/useStats.ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchStats } from "@/lib/api";

export function useStats() {
  return useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
  });
}
```

**Step 3: Create ClassificationChart**

```typescript
// frontend/src/components/charts/classification-chart.tsx
"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";

const COLORS: Record<string, string> = {
  "TOP SECRET": "#dc2626",
  SECRET: "#f97316",
  CONFIDENTIAL: "#eab308",
  UNCLASSIFIED: "#16a34a",
};

export function ClassificationChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
          {chartData.map((entry) => (
            <Cell key={entry.name} fill={COLORS[entry.name] ?? "#6b7280"} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
```

**Step 4: Create TimelineChart**

```typescript
// frontend/src/components/charts/timeline-chart.tsx
"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

export function TimelineChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data)
    .map(([year, count]) => ({ year, count }))
    .sort((a, b) => a.year.localeCompare(b.year));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="year" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="count" fill="#2563eb" />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

**Step 5: Build the Dashboard page**

```typescript
// frontend/src/app/page.tsx
"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ClassificationChart } from "@/components/charts/classification-chart";
import { TimelineChart } from "@/components/charts/timeline-chart";
import { useStats } from "@/hooks/useStats";

export default function DashboardPage() {
  const { data: stats, isLoading } = useStats();

  if (isLoading || !stats) {
    return (
      <div className="container py-8 space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  const progress = stats.transcription_progress;

  return (
    <div className="container py-8 space-y-8">
      <h1 className="text-3xl font-bold">
        Declassified CIA Documents on Chile
      </h1>
      <p className="text-muted-foreground">
        Exploring {stats.total_documents.toLocaleString()} transcribed documents
        ({stats.total_pages.toLocaleString()} pages) from the US declassification
        program on the Chilean dictatorship (1973-1990).
      </p>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Documents" value={stats.total_documents.toLocaleString()} subtitle={`${stats.total_pages.toLocaleString()} pages`} />
        <StatCard
          title="Transcription"
          value={`${Math.round((progress.completed / progress.total) * 100)}%`}
          subtitle={`${progress.completed.toLocaleString()} / ${progress.total.toLocaleString()}`}
        />
        <StatCard title="Avg Confidence" value={`${(stats.avg_confidence * 100).toFixed(1)}%`} subtitle="across all transcripts" />
        <StatCard
          title="Sensitive Content"
          value={stats.sensitive_content.violence.toLocaleString()}
          subtitle={`violence refs | ${stats.sensitive_content.torture.toLocaleString()} torture | ${stats.sensitive_content.disappearances.toLocaleString()} disappearances`}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Documents Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <TimelineChart data={stats.timeline} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Classification Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ClassificationChart data={stats.classification_distribution} />
          </CardContent>
        </Card>
      </div>

      {/* Top entities */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <EntityList title="Top People" items={stats.top_people} href="/entities?type=person" />
        <EntityList title="Top Organizations" items={stats.top_organizations} href="/entities?type=organization" />
        <EntityList title="Top Keywords" items={stats.top_keywords} href="/entities?type=keyword" />
      </div>
    </div>
  );
}

function StatCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function EntityList({ title, items, href }: { title: string; items: { name: string; count: number }[]; href: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.slice(0, 10).map((item) => (
            <li key={item.name} className="flex justify-between text-sm">
              <span className="truncate">{item.name}</span>
              <span className="text-muted-foreground ml-2">{item.count.toLocaleString()}</span>
            </li>
          ))}
        </ul>
        <Link href={href} className="text-sm text-blue-600 hover:underline mt-4 inline-block">
          View all →
        </Link>
      </CardContent>
    </Card>
  );
}
```

**Step 6: Verify**

Start both servers:
- Terminal 1: `uv run uvicorn app.api.main:app --reload --port 8001 --factory`
- Terminal 2: `cd frontend && pnpm dev`

Open http://localhost:3000 — should see the dashboard with real data.

**Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add dashboard page with stats, timeline, classification chart"
```

---

## Task 8: Frontend — Document Explorer Page

Search, filter, paginate, and view documents with inline PDF.

**Files:**
- Create: `frontend/src/components/documents/document-card.tsx`
- Create: `frontend/src/components/documents/filter-sidebar.tsx`
- Create: `frontend/src/components/documents/document-detail.tsx`
- Create: `frontend/src/hooks/useDocuments.ts`
- Create: `frontend/src/app/explorer/page.tsx`

**Step 1: Create useDocuments hook**

```typescript
// frontend/src/hooks/useDocuments.ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchDocuments, fetchDocument, type DocumentFilters } from "@/lib/api";

export function useDocuments(filters: DocumentFilters) {
  return useQuery({
    queryKey: ["documents", filters],
    queryFn: () => fetchDocuments(filters),
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: ["document", id],
    queryFn: () => fetchDocument(id!),
    enabled: !!id,
  });
}
```

**Step 2: Create DocumentCard**

```typescript
// frontend/src/components/documents/document-card.tsx
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ClassificationBadge } from "./classification-badge";
import type { DocumentListItem } from "@/lib/types";

export function DocumentCard({
  doc,
  onClick,
}: {
  doc: DocumentListItem;
  onClick: () => void;
}) {
  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={onClick}
    >
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-mono">{doc.date}</span>
          <ClassificationBadge level={doc.classification} />
          <Badge variant="outline">{doc.type}</Badge>
        </div>
        <h3 className="font-medium text-sm line-clamp-2">{doc.title || `Document ${doc.id}`}</h3>
        <p className="text-xs text-muted-foreground line-clamp-2">{doc.summary}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{doc.pages} {doc.pages === 1 ? "page" : "pages"}</span>
          <span>ID: {doc.id}</span>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 3: Create FilterSidebar**

```typescript
// frontend/src/components/documents/filter-sidebar.tsx
"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { DocumentFilters } from "@/lib/api";

const CLASSIFICATIONS = ["TOP SECRET", "SECRET", "CONFIDENTIAL", "UNCLASSIFIED"];
const DOC_TYPES = ["MEMORANDUM", "LETTER", "TELEGRAM", "INTELLIGENCE BRIEF", "REPORT", "CABLE"];

export function FilterSidebar({
  filters,
  onChange,
}: {
  filters: DocumentFilters;
  onChange: (filters: DocumentFilters) => void;
}) {
  return (
    <div className="space-y-6 w-64 shrink-0">
      <div>
        <label className="text-sm font-medium mb-2 block">Search</label>
        <Input
          placeholder="Search documents..."
          value={filters.q ?? ""}
          onChange={(e) => onChange({ ...filters, q: e.target.value || undefined, page: 1 })}
        />
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">Date Range</label>
        <div className="flex gap-2">
          <Input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) => onChange({ ...filters, date_from: e.target.value || undefined, page: 1 })}
          />
          <Input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) => onChange({ ...filters, date_to: e.target.value || undefined, page: 1 })}
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">Classification</label>
        <div className="space-y-1">
          {CLASSIFICATIONS.map((c) => (
            <label key={c} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.classification?.includes(c) ?? false}
                onChange={(e) => {
                  const current = filters.classification ?? [];
                  const next = e.target.checked
                    ? [...current, c]
                    : current.filter((x) => x !== c);
                  onChange({ ...filters, classification: next.length ? next : undefined, page: 1 });
                }}
              />
              {c}
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">Document Type</label>
        <div className="space-y-1">
          {DOC_TYPES.map((t) => (
            <label key={t} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.type?.includes(t) ?? false}
                onChange={(e) => {
                  const current = filters.type ?? [];
                  const next = e.target.checked
                    ? [...current, t]
                    : current.filter((x) => x !== t);
                  onChange({ ...filters, type: next.length ? next : undefined, page: 1 });
                }}
              />
              {t}
            </label>
          ))}
        </div>
      </div>

      <Button
        variant="outline"
        className="w-full"
        onClick={() => onChange({ page: 1, page_size: 25, sort: "date_desc" })}
      >
        Clear Filters
      </Button>
    </div>
  );
}
```

**Step 4: Create DocumentDetail panel**

```typescript
// frontend/src/components/documents/document-detail.tsx
"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ClassificationBadge } from "./classification-badge";
import { useDocument } from "@/hooks/useDocuments";
import { pdfUrl } from "@/lib/api";

export function DocumentDetail({
  docId,
  onClose,
}: {
  docId: string | null;
  onClose: () => void;
}) {
  const { data: doc, isLoading } = useDocument(docId);

  return (
    <Dialog open={!!docId} onOpenChange={() => onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        {isLoading || !doc ? (
          <div className="space-y-4">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>{doc.title || `Document ${doc.id}`}</DialogTitle>
            </DialogHeader>

            <div className="flex flex-wrap gap-2 mb-4">
              <ClassificationBadge level={doc.classification} />
              <Badge variant="outline">{doc.type}</Badge>
              <Badge variant="secondary">{doc.date}</Badge>
              <Badge variant="secondary">{doc.pages} pages</Badge>
              <Badge variant="secondary">{doc.language}</Badge>
            </div>

            {doc.summary && (
              <p className="text-sm text-muted-foreground mb-4">{doc.summary}</p>
            )}

            <Separator />

            {/* Metadata grid */}
            <div className="grid grid-cols-2 gap-4 text-sm my-4">
              {doc.author && <div><span className="font-medium">Author:</span> {doc.author}</div>}
              {doc.recipients?.length > 0 && (
                <div><span className="font-medium">Recipients:</span> {doc.recipients.join(", ")}</div>
              )}
              {doc.keywords?.length > 0 && (
                <div className="col-span-2">
                  <span className="font-medium">Keywords:</span>{" "}
                  {doc.keywords.map((k) => <Badge key={k} variant="outline" className="mr-1 mb-1">{k}</Badge>)}
                </div>
              )}
              {doc.people_mentioned?.length > 0 && (
                <div className="col-span-2">
                  <span className="font-medium">People:</span> {doc.people_mentioned.join(", ")}
                </div>
              )}
            </div>

            <Separator />

            {/* PDF embed */}
            {doc.has_pdf && (
              <div className="my-4">
                <h3 className="font-medium mb-2">Document PDF</h3>
                <iframe
                  src={pdfUrl(doc.id)}
                  className="w-full h-[600px] border rounded"
                  title={`PDF: ${doc.id}`}
                />
              </div>
            )}

            {/* Text content */}
            {doc.reviewed_text && (
              <div className="my-4">
                <h3 className="font-medium mb-2">Reviewed Text</h3>
                <pre className="whitespace-pre-wrap text-xs bg-muted p-4 rounded max-h-96 overflow-y-auto">
                  {doc.reviewed_text}
                </pre>
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

**Step 5: Build the Explorer page**

```typescript
// frontend/src/app/explorer/page.tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DocumentCard } from "@/components/documents/document-card";
import { FilterSidebar } from "@/components/documents/filter-sidebar";
import { DocumentDetail } from "@/components/documents/document-detail";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocuments } from "@/hooks/useDocuments";
import type { DocumentFilters } from "@/lib/api";

export default function ExplorerPage() {
  const [filters, setFilters] = useState<DocumentFilters>({
    page: 1,
    page_size: 25,
    sort: "date_desc",
  });
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const { data, isLoading } = useDocuments(filters);

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold mb-6">Document Explorer</h1>

      <div className="flex gap-8">
        <FilterSidebar filters={filters} onChange={setFilters} />

        <div className="flex-1">
          {/* Results header */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">
              {data ? `${data.total.toLocaleString()} documents found` : "Loading..."}
            </p>
            <select
              className="text-sm border rounded px-2 py-1"
              value={filters.sort ?? "date_desc"}
              onChange={(e) => setFilters({ ...filters, sort: e.target.value, page: 1 })}
            >
              <option value="date_desc">Newest first</option>
              <option value="date_asc">Oldest first</option>
              <option value="confidence">Highest confidence</option>
              <option value="pages">Most pages</option>
            </select>
          </div>

          {/* Document grid */}
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-36" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data?.items.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  onClick={() => setSelectedDoc(doc.id)}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <Button
                variant="outline"
                size="sm"
                disabled={data.page <= 1}
                onClick={() => setFilters({ ...filters, page: data.page - 1 })}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {data.page} of {data.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={data.page >= data.total_pages}
                onClick={() => setFilters({ ...filters, page: data.page + 1 })}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      </div>

      <DocumentDetail docId={selectedDoc} onClose={() => setSelectedDoc(null)} />
    </div>
  );
}
```

**Step 6: Verify**

With both servers running, open http://localhost:3000/explorer — should see document cards with filters and pagination. Click a card to see the detail dialog with PDF.

**Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add document explorer with search, filters, pagination, PDF viewer"
```

---

## Task 9: Frontend — Entity Explorer Page

Browse people, organizations, keywords, places with search and filtering.

**Files:**
- Create: `frontend/src/hooks/useEntities.ts`
- Create: `frontend/src/app/entities/page.tsx`

**Step 1: Create useEntities hook**

```typescript
// frontend/src/hooks/useEntities.ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchEntities, type EntityFilters } from "@/lib/api";

export function useEntities(filters: EntityFilters) {
  return useQuery({
    queryKey: ["entities", filters],
    queryFn: () => fetchEntities(filters),
  });
}
```

**Step 2: Build the Entities page**

```typescript
// frontend/src/app/entities/page.tsx
"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { useEntities } from "@/hooks/useEntities";
import type { EntityFilters } from "@/lib/api";

const ENTITY_TYPES = [
  { value: "", label: "All" },
  { value: "person", label: "People" },
  { value: "organization", label: "Organizations" },
  { value: "keyword", label: "Keywords" },
  { value: "place", label: "Places" },
];

const TYPE_COLORS: Record<string, string> = {
  person: "bg-purple-100 text-purple-800",
  organization: "bg-cyan-100 text-cyan-800",
  keyword: "bg-orange-100 text-orange-800",
  place: "bg-green-100 text-green-800",
};

export default function EntitiesPage() {
  const searchParams = useSearchParams();
  const initialType = searchParams.get("type") ?? "";

  const [filters, setFilters] = useState<EntityFilters>({
    type: initialType || undefined,
    sort: "doc_count_desc",
    page: 1,
    page_size: 50,
  });
  const [search, setSearch] = useState("");
  const { data, isLoading } = useEntities({ ...filters, q: search || undefined });

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold mb-6">Entity Explorer</h1>

      {/* Tabs + Search */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <Tabs
          value={filters.type ?? ""}
          onValueChange={(v) => setFilters({ ...filters, type: v || undefined, page: 1 })}
        >
          <TabsList>
            {ENTITY_TYPES.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <Input
          placeholder="Search entities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {/* Results count */}
      <p className="text-sm text-muted-foreground mb-4">
        {data ? `${data.total.toLocaleString()} entities` : "Loading..."}
      </p>

      {/* Entity grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items.map((entity) => (
            <Card key={`${entity.type}-${entity.name}`}>
              <CardContent className="p-4 flex items-center justify-between">
                <div className="min-w-0">
                  <Badge className={TYPE_COLORS[entity.type] ?? ""} variant="secondary">
                    {entity.type}
                  </Badge>
                  <p className="font-medium text-sm mt-1 truncate">{entity.name}</p>
                </div>
                <div className="text-right shrink-0 ml-4">
                  <p className="text-2xl font-bold">{entity.doc_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">docs</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <Button
            variant="outline"
            size="sm"
            disabled={data.page <= 1}
            onClick={() => setFilters({ ...filters, page: data.page - 1 })}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {data.page} of {data.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={data.page >= data.total_pages}
            onClick={() => setFilters({ ...filters, page: data.page + 1 })}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
```

**Step 3: Verify**

Open http://localhost:3000/entities — should see entity cards with tabs and search.

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add entity explorer with tabs, search, pagination"
```

---

## Task 10: Frontend — Research Reports Pages

List research questions and display individual reports.

**Files:**
- Create: `frontend/src/app/reports/page.tsx`
- Create: `frontend/src/app/reports/[id]/page.tsx`

**Step 1: Create reports index page**

```typescript
// frontend/src/app/reports/page.tsx
"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchReports } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  answered: "bg-green-100 text-green-800",
  partially_answered: "bg-yellow-100 text-yellow-800",
  unanswered: "bg-gray-100 text-gray-800",
  needs_more_data: "bg-red-100 text-red-800",
};

export default function ReportsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: fetchReports,
  });

  if (isLoading) {
    return (
      <div className="container py-8 space-y-4">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  return (
    <div className="container py-8">
      <h1 className="text-2xl font-bold mb-6">Research Questions</h1>
      <div className="space-y-4">
        {data?.items.map((rq) => (
          <Link key={rq.id} href={`/reports/${rq.id}`}>
            <Card className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{rq.id}</Badge>
                  <Badge className={STATUS_COLORS[rq.status] ?? ""} variant="secondary">
                    {rq.status.replace("_", " ")}
                  </Badge>
                  <Badge variant="secondary">{rq.category}</Badge>
                </div>
                <CardTitle className="text-base mt-2">{rq.question}</CardTitle>
              </CardHeader>
              {rq.rag_results && (
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-3">{rq.rag_results}</p>
                </CardContent>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

**Step 2: Create individual report page**

```typescript
// frontend/src/app/reports/[id]/page.tsx
"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchReport } from "@/lib/api";

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: report, isLoading } = useQuery({
    queryKey: ["report", id],
    queryFn: () => fetchReport(id),
  });

  if (isLoading) {
    return (
      <div className="container max-w-3xl py-8 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!report) return <div className="container py-8">Report not found.</div>;

  // Rich report (has sections)
  const sections = (report.sections ?? []) as Array<{
    title: string;
    content: Array<{ type: string; text?: string; items?: string[]; doc_id?: string }>;
  }>;
  const hasRichContent = sections.length > 0;

  return (
    <div className="container max-w-3xl py-8">
      <h1 className="text-2xl font-bold mb-2">{report.title as string ?? `Report ${id}`}</h1>
      {report.subtitle && (
        <p className="text-lg text-muted-foreground mb-4">{report.subtitle as string}</p>
      )}

      <div className="flex gap-2 mb-6">
        <Badge variant="outline">{id}</Badge>
        {report.category && <Badge variant="secondary">{report.category as string}</Badge>}
      </div>

      {report.introduction && (
        <p className="text-sm mb-6">{report.introduction as string}</p>
      )}

      <Separator className="my-6" />

      {hasRichContent ? (
        sections.map((section, i) => (
          <div key={i} className="mb-8">
            <h2 className="text-xl font-semibold mb-4">{section.title}</h2>
            {section.content.map((block, j) => {
              if (block.type === "paragraph") return <p key={j} className="text-sm mb-3">{block.text}</p>;
              if (block.type === "quote") return <blockquote key={j} className="border-l-4 border-blue-500 pl-4 italic text-sm mb-3">{block.text}</blockquote>;
              if (block.type === "list") return (
                <ul key={j} className="list-disc pl-6 text-sm mb-3 space-y-1">
                  {block.items?.map((item, k) => <li key={k}>{item}</li>)}
                </ul>
              );
              if (block.type === "document_reference") return (
                <Card key={j} className="mb-3">
                  <CardContent className="p-3 text-xs">
                    <span className="font-mono font-medium">Doc {block.doc_id}</span>
                    {block.text && <span className="ml-2 text-muted-foreground">{block.text}</span>}
                  </CardContent>
                </Card>
              );
              return <p key={j} className="text-sm mb-3">{block.text}</p>;
            })}
          </div>
        ))
      ) : (
        // Basic report (from tracker)
        report.rag_results && (
          <div className="bg-muted p-4 rounded text-sm">{report.rag_results as string}</div>
        )
      )}
    </div>
  );
}
```

**Step 3: Verify**

Open http://localhost:3000/reports — should see research question cards. Click one to see the full report.

**Step 4: Commit**

```bash
git add frontend/src/app/reports/
git commit -m "feat(frontend): add research reports index and detail pages"
```

---

## Task 11: Frontend — About Page

Static content page about the project.

**Files:**
- Create: `frontend/src/app/about/page.tsx`

**Step 1: Create About page**

```typescript
// frontend/src/app/about/page.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function AboutPage() {
  return (
    <div className="container max-w-3xl py-8 space-y-8">
      <h1 className="text-3xl font-bold">About This Project</h1>
      <p className="text-muted-foreground">
        This project processes and makes accessible approximately 21,000 declassified CIA
        documents related to the Chilean dictatorship (1973-1990), released by the US government
        as part of its declassification program.
      </p>

      <Separator />

      <section>
        <h2 className="text-xl font-semibold mb-4">The Problem</h2>
        <p className="text-sm mb-4">
          While the US government declassified these documents, the sheer volume makes them
          practically inaccessible for researchers, journalists, and the general public.
          This project creates a searchable, structured database with AI-powered transcription
          and analysis to enable meaningful research at scale.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Methodology</h2>
        <div className="grid gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">1. PDF Transcription</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Each PDF is processed using OpenAI vision models that extract text and structured
              metadata (dates, people, organizations, classification levels, keywords).
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">2. Vector Indexing</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Transcribed documents are chunked and embedded into a vector database (ChromaDB)
              for semantic search and retrieval.
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">3. Analysis & Visualization</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Metadata is aggregated to produce timelines, entity networks, geographic maps,
              and thematic analysis across the entire corpus.
            </CardContent>
          </Card>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Limitations</h2>
        <ul className="list-disc pl-6 text-sm space-y-2 text-muted-foreground">
          <li>Not all documents have been transcribed yet. Coverage is ongoing.</li>
          <li>AI transcription may contain errors, especially with handwritten or degraded documents.</li>
          <li>Metadata extraction is automated and may misidentify entities or dates.</li>
          <li>This is a research tool, not a definitive historical record.</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Open Source</h2>
        <p className="text-sm text-muted-foreground">
          This project is open source. The code, methodology, and documentation are publicly
          available for review and contribution.
        </p>
      </section>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/app/about/
git commit -m "feat(frontend): add about page"
```

---

## Task 12: Integration Testing & Polish

Verify the full stack works end-to-end and fix any issues.

**Files:**
- Modify: `Makefile` (finalize dev targets)
- Modify: `STARTHERE.md` (add frontend section)

**Step 1: Start both servers and test all pages**

Terminal 1:
```bash
uv run uvicorn app.api.main:app --reload --port 8001 --factory
```

Terminal 2:
```bash
cd frontend && pnpm dev
```

Verify each page:
- http://localhost:3000 → Dashboard loads with real stats
- http://localhost:3000/explorer → Documents load, filters work, detail dialog opens
- http://localhost:3000/entities → Entities load, tabs work, search works
- http://localhost:3000/reports → Research questions list loads
- http://localhost:3000/reports/RQ-001 → Report content renders
- http://localhost:3000/about → Static content displays

**Step 2: Run all Python tests**

```bash
uv run pytest tests/unit/ -v
```

Expected: All tests pass (existing 382 + new API tests).

**Step 3: Run frontend lint**

```bash
cd frontend && pnpm lint
```

Fix any lint errors.

**Step 4: Update STARTHERE.md**

Add a new section at the top of STARTHERE.md:

```markdown
## New Frontend Application (2026-02-23)

**Full-stack web app replacing the static GitHub Pages site.**

**Quick Start:**
```bash
# Terminal 1: Start API backend
make dev-backend

# Terminal 2: Start Next.js frontend
cd frontend && pnpm dev

# Open http://localhost:3000
```

**Pages:**
- `/` — Dashboard with stats, timeline, classification chart, top entities
- `/explorer` — Document search with filters, pagination, inline PDF viewer
- `/entities` — Browse people, organizations, keywords, places
- `/reports` — Research question reports
- `/about` — Project context and methodology

**Tech:** Next.js 15 + TypeScript + Tailwind + shadcn/ui + TanStack Query + Recharts
**API:** FastAPI on port 8001 reading from existing JSON transcripts
```

**Step 5: Commit**

```bash
git add Makefile STARTHERE.md
git commit -m "feat: finalize frontend integration, update docs and Makefile"
```

---

## Summary

| Task | What | Key Files |
|------|------|-----------|
| 1 | Document Service | `app/api/services/document_service.py` |
| 2 | Entity Service | `app/api/services/entity_service.py` |
| 3 | Stats Service | `app/api/services/stats_service.py` |
| 4 | API Routes & App | `app/api/main.py`, `app/api/routes/*.py` |
| 5 | Next.js Scaffolding | `frontend/` project setup |
| 6 | Layout & Navigation | `frontend/src/components/layout/` |
| 7 | Dashboard Page | `frontend/src/app/page.tsx` |
| 8 | Document Explorer | `frontend/src/app/explorer/page.tsx` |
| 9 | Entity Explorer | `frontend/src/app/entities/page.tsx` |
| 10 | Research Reports | `frontend/src/app/reports/` |
| 11 | About Page | `frontend/src/app/about/page.tsx` |
| 12 | Integration & Polish | Full stack testing, docs update |

Total: 12 tasks, backend-first then frontend. Each task has tests and a commit.
