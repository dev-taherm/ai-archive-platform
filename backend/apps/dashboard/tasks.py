from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="dashboard.refresh_cache")
def refresh_dashboard_cache() -> str:
    """Refresh cached dashboard data."""

    from django.core.cache import cache
    from apps.dashboard.services import DashboardService

    overview = DashboardService.get_overview()
    storage = DashboardService.get_storage_stats()
    processing = DashboardService.get_processing_queue()

    cache.set("dashboard:overview", overview, timeout=300)
    cache.set("dashboard:storage", storage, timeout=300)
    cache.set("dashboard:processing", processing, timeout=120)

    logger.info("Dashboard cache refreshed")
    return "Dashboard cache refreshed"
