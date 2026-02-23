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
