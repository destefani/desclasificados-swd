from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

if TYPE_CHECKING:
    from app.api.services.entity_service import EntityService


def init_router(entity_service: EntityService) -> APIRouter:
    router = APIRouter()

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
