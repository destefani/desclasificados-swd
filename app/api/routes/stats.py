from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

if TYPE_CHECKING:
    from app.api.services.stats_service import StatsService


def init_router(stats_service: StatsService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/stats")
    def get_stats():
        return stats_service.get_stats()

    return router
