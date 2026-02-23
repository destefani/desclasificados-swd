from __future__ import annotations

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
    doc_svc = DocumentService(transcripts_dir, pdf_dir=pdf_dir)
    ent_svc = EntityService(doc_svc)
    stats_svc = StatsService(doc_svc)

    # Override get_stats to use configured total
    original_get_stats = stats_svc.get_stats
    stats_svc.get_stats = lambda: original_get_stats(total_pdfs=total_pdfs)  # type: ignore[assignment]

    application = FastAPI(title="Desclasificados API", version="1.0.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Init and include routers
    application.include_router(documents.init_router(doc_svc))
    application.include_router(entities.init_router(ent_svc))
    application.include_router(stats.init_router(stats_svc))
    application.include_router(pdf.init_router(pdf_dir))
    application.include_router(reports.init_router(research_questions_path, research_reports_dir))

    @application.get("/api/health")
    def health():
        return {"status": "ok", "documents_loaded": doc_svc.total_documents}

    return application


app = create_app()
