"""
GitHub Traffic API collector.

Collects clones, views, referrers, and popular paths from the GitHub Traffic API.
GitHub retains only 14 days of data — this collector persists it before expiry.
"""

from typing import Any

import httpx
from app.core.config import settings
from sqlmodel.ext.asyncio.session import AsyncSession

from ..constants import MetricKeys, Periods, SourceKeys
from ..schemas import PopularPathEntry, PopularPathsMetadata, ReferrerEntry
from .base import BaseCollector, CollectionResult, parse_github_date, today

GITHUB_API = "https://api.github.com"


class GitHubTrafficCollector(BaseCollector):
    """Collects traffic data from the GitHub REST API."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    @property
    def source_key(self) -> str:
        return SourceKeys.GITHUB_TRAFFIC

    async def collect(self) -> CollectionResult:
        """Collect clones, views, referrers, and popular paths."""
        token = settings.INSIGHT_GITHUB_TOKEN
        owner = settings.INSIGHT_GITHUB_OWNER
        repo = settings.INSIGHT_GITHUB_REPO

        if err := self._validate_config(
            INSIGHT_GITHUB_TOKEN=token,
            INSIGHT_GITHUB_OWNER=owner,
            INSIGHT_GITHUB_REPO=repo,
        ):
            return err

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        base_url = f"{GITHUB_API}/repos/{owner}/{repo}"

        rows_written = 0
        rows_skipped = 0

        try:
            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                clones_resp = await client.get(f"{base_url}/traffic/clones")
                views_resp = await client.get(f"{base_url}/traffic/views")
                referrers_resp = await client.get(
                    f"{base_url}/traffic/popular/referrers"
                )
                paths_resp = await client.get(f"{base_url}/traffic/popular/paths")

                for resp in [clones_resp, views_resp, referrers_resp, paths_resp]:
                    resp.raise_for_status()

                written, skipped = await self._process_clones(clones_resp.json())
                rows_written += written
                rows_skipped += skipped

                written, skipped = await self._process_views(views_resp.json())
                rows_written += written
                rows_skipped += skipped

                written, skipped = await self._process_referrers(referrers_resp.json())
                rows_written += written
                rows_skipped += skipped

                written, skipped = await self._process_popular_paths(paths_resp.json())
                rows_written += written
                rows_skipped += skipped

            await self.db.commit()
            return self._success(rows_written, rows_skipped)

        except httpx.HTTPStatusError as e:
            return self._error(
                f"GitHub API error: {e.response.status_code} {e.response.text[:200]}",
                rows_written,
                rows_skipped,
            )
        except Exception as e:
            return self._error(
                f"GitHub traffic collection failed: {e}",
                rows_written,
                rows_skipped,
            )

    async def _process_clones(self, data: dict[str, Any]) -> tuple[int, int]:
        """Process clones response — one row per day for clones + unique_cloners."""
        clones_type = await self.get_metric_type(MetricKeys.CLONES)
        unique_type = await self.get_metric_type(MetricKeys.UNIQUE_CLONERS)

        written = 0
        skipped = 0

        for entry in data.get("clones", []):
            date = parse_github_date(entry["timestamp"])

            _, created = await self.upsert_metric(
                metric_type=clones_type,
                date=date,
                value=float(entry["count"]),
                period=Periods.DAILY,
            )
            written += 1 if created else 0
            skipped += 0 if created else 1

            _, created = await self.upsert_metric(
                metric_type=unique_type,
                date=date,
                value=float(entry["uniques"]),
                period=Periods.DAILY,
            )
            written += 1 if created else 0
            skipped += 0 if created else 1

        return written, skipped

    async def _process_views(self, data: dict[str, Any]) -> tuple[int, int]:
        """Process views response — one row per day for views + unique_visitors."""
        views_type = await self.get_metric_type(MetricKeys.VIEWS)
        visitors_type = await self.get_metric_type(MetricKeys.UNIQUE_VISITORS)

        written = 0
        skipped = 0

        for entry in data.get("views", []):
            date = parse_github_date(entry["timestamp"])

            _, created = await self.upsert_metric(
                metric_type=views_type,
                date=date,
                value=float(entry["count"]),
                period=Periods.DAILY,
            )
            written += 1 if created else 0
            skipped += 0 if created else 1

            _, created = await self.upsert_metric(
                metric_type=visitors_type,
                date=date,
                value=float(entry["uniques"]),
                period=Periods.DAILY,
            )
            written += 1 if created else 0
            skipped += 0 if created else 1

        return written, skipped

    async def _process_referrers(self, data: list[dict[str, Any]]) -> tuple[int, int]:
        """Process referrers — single snapshot row with typed referrer entries."""
        referrers_type = await self.get_metric_type(MetricKeys.REFERRERS)

        referrer_map: dict[str, dict[str, int]] = {}
        for entry in data:
            validated = ReferrerEntry(
                views=entry["count"],
                uniques=entry["uniques"],
            )
            referrer_map[entry["referrer"]] = validated.model_dump()

        _today = today()
        _, created = await self.upsert_metric(
            metric_type=referrers_type,
            date=_today,
            value=float(len(data)),
            period=Periods.DAILY,
            metadata=referrer_map,
        )

        return (1, 0) if created else (0, 1)

    async def _process_popular_paths(
        self, data: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """Process popular paths — single snapshot row with typed path entries."""
        paths_type = await self.get_metric_type(MetricKeys.POPULAR_PATHS)

        paths = PopularPathsMetadata(
            paths=[
                PopularPathEntry(
                    path=entry["path"],
                    title=entry["title"],
                    views=entry["count"],
                    uniques=entry["uniques"],
                )
                for entry in data
            ]
        )

        _today = today()
        _, created = await self.upsert_metric(
            metric_type=paths_type,
            date=_today,
            value=float(len(data)),
            period=Periods.DAILY,
            metadata=paths.model_dump(),
        )

        return (1, 0) if created else (0, 1)
