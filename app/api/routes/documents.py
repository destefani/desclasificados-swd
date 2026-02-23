from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

if TYPE_CHECKING:
    from app.api.services.document_service import DocumentService


def init_router(doc_service: DocumentService) -> APIRouter:
    router = APIRouter()

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
