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
