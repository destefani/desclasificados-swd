from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


def init_router(pdf_dir: Path) -> APIRouter:
    router = APIRouter()

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
