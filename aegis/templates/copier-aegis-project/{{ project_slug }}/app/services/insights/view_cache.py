"""Shared cache helper for insight tab views.

The API (`/api/v1/insights/view/{tab}`) and the page handler that inlines
initial dashboard content (`/app/{section}`) need the exact same thing:
"give me the cached tab view, rebuild from DB on miss." Keeping both
behind one function guarantees the cache key shape (`view:{tab}:{days}`)
and TTL stay in lockstep — a hit from one reader is a hit for the other.

Additionally caches the raw `BulkInsightsResponse` under `insights:bulk`
so views for different (tab, days) combos don't each re-run the
~25-query `load_all()` — they re-slice the same in-memory bulk instead.
This key is internal to the view-cache flow; the public bulk endpoint
`/api/v1/insights/all` caches separately under `insights:all` and is
invalidated by `CollectorService` after each successful collection.
"""

from collections.abc import Callable
from typing import TypeVar

from app.core.cache import CacheService
from app.services.insights.query_service import InsightQueryService
from app.services.insights.schemas import BulkInsightsResponse
from app.services.insights.view_service import InsightViewService

T = TypeVar("T")

BULK_CACHE_KEY = "insights:bulk"

# Section (URL slug under /app/<section>) → attribute on InsightViewService.
# Only tabs with a display-ready view schema are listed. Sections like
# "goals" and "events" render content from other services and have no
# single `initial_view` to pre-compute; they fall through to their own
# lazy fetches.
SECTION_TO_VIEW_METHOD: dict[str, str] = {
    "overview": "overview",
    "github": "github",
    "stars": "stars",
    "pypi": "pypi",
    "docs": "docs",
    "reddit": "reddit",
}


async def cached_bulk(
    cache: CacheService,
    qs: InsightQueryService,
) -> BulkInsightsResponse:
    """Return the shared raw BulkInsightsResponse; load from DB on miss.

    Every tab+range view slices the same underlying bulk — caching it in
    one key means the first cache miss pays load_all() once and all
    subsequent views in the session re-slice in memory (~20ms) instead
    of re-querying 25 times.
    """
    cached = await cache.get(BULK_CACHE_KEY)
    if cached is not None:
        return cached  # type: ignore[no-any-return]
    bulk = await qs.load_all()
    await cache.set(BULK_CACHE_KEY, bulk)
    return bulk


async def cached_view(
    cache: CacheService,
    qs: InsightQueryService,
    tab: str,
    days: int,
    compute: Callable[[InsightViewService], T],
) -> T:
    """Return a tab view from cache; rebuild via `compute` on miss.

    Shares a single in-memory bulk (`insights:bulk`) across every
    (tab, days) combo, so toggling tabs or ranges only re-runs the
    lightweight view-service transform — not the ~25-query DB load.
    """
    key = f"view:{tab}:{days}"
    cached = await cache.get(key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]
    bulk = await cached_bulk(cache, qs)
    view_svc = InsightViewService(bulk)
    result = compute(view_svc)
    await cache.set(key, result)
    return result


async def cached_view_for_section(
    cache: CacheService,
    qs: InsightQueryService,
    section: str,
    days: int,
) -> object | None:
    """Dispatch `section` to the matching InsightViewService method and
    return the cached result. `None` for sections without a pre-computable
    view (goals, events, etc.) — caller should fall back to the lazy path.
    """
    method_name = SECTION_TO_VIEW_METHOD.get(section)
    if method_name is None:
        return None
    return await cached_view(
        cache,
        qs,
        method_name,
        days,
        lambda svc: getattr(svc, method_name)(days=days),
    )
