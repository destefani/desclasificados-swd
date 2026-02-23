from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException


def init_router(research_questions_path: Path, research_reports_dir: Path) -> APIRouter:
    router = APIRouter()

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
