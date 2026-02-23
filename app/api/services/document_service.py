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
