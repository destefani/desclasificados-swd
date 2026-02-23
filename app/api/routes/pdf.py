from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


def init_router(pdf_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/pdf/{file_id}")
    def serve_pdf(file_id: str):
        # Only allow numeric file IDs to prevent path traversal
        if not file_id.isdigit():
            raise HTTPException(status_code=400, detail="Invalid file ID: must be numeric")
        pdf_path = pdf_dir / f"{file_id}.pdf"
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF not found")
        return FileResponse(pdf_path, media_type="application/pdf")

    return router
