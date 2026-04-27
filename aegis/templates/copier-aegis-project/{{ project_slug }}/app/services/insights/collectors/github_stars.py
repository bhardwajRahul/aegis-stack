"""
GitHub Stargazers API collector.

Collects star events with user profiles stored as JSONB metadata.
Only fetches profiles for new stars not already in the database.
"""

import logging
from datetime import datetime

import httpx
from app.core.config import settings
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..constants import MetricKeys, Periods, SourceKeys
from ..models import InsightMetric
from ..schemas import StarProfileMetadata
from .base import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubStarsCollector(BaseCollector):
    """Collects stargazer data from the GitHub REST API."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    @property
    def source_key(self) -> str:
        return SourceKeys.GITHUB_STARS

    async def collect(self) -> CollectionResult:
        """Collect new stars with user profiles."""
        token = settings.INSIGHT_GITHUB_TOKEN
        owner = settings.INSIGHT_GITHUB_OWNER
        repo = settings.INSIGHT_GITHUB_REPO

        if not token or not owner or not repo:
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                error="Missing INSIGHT_GITHUB_TOKEN, INSIGHT_GITHUB_OWNER, or INSIGHT_GITHUB_REPO",
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.star+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        base_url = f"{GITHUB_API}/repos/{owner}/{repo}"

        rows_written = 0
        rows_skipped = 0

        try:
            star_type = await self.get_metric_type(MetricKeys.NEW_STAR)

            # Get existing star numbers to skip
            existing_result = await self.db.exec(
                select(InsightMetric.value).where(
                    InsightMetric.metric_type_id == star_type.id,
                    InsightMetric.period == Periods.EVENT,
                )
            )
            existing_star_numbers = {int(v) for v in existing_result.all()}

            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                # Paginate through all stargazers
                page = 1
                star_number = 0

                while True:
                    resp = await client.get(
                        f"{base_url}/stargazers",
                        params={"per_page": 100, "page": page},
                    )
                    resp.raise_for_status()
                    stargazers = resp.json()

                    if not stargazers:
                        break

                    for stargazer in stargazers:
                        star_number += 1

                        if star_number in existing_star_numbers:
                            rows_skipped += 1
                            continue

                        # Fetch user profile
                        user_data = stargazer.get("user", {})
                        starred_at = stargazer.get("starred_at", "")

                        profile = await self._fetch_profile(client, user_data)

                        date = _parse_star_date(starred_at)
                        await self.upsert_metric(
                            metric_type=star_type,
                            date=date,
                            value=float(star_number),
                            period=Periods.EVENT,
                            metadata=profile.model_dump(),
                        )
                        rows_written += 1

                    if len(stargazers) < 100:
                        break
                    page += 1

            # Create InsightEvent entries grouped by day
            from ..models import InsightEvent

            # Get all star metrics to group by date
            all_stars = await self.db.exec(
                select(InsightMetric)
                .where(
                    InsightMetric.metric_type_id == star_type.id,
                    InsightMetric.period == Periods.EVENT,
                )
                .order_by(InsightMetric.date.asc())
            )
            stars_by_date: dict[str, list[dict]] = {}
            for s in all_stars.all():
                day = str(s.date)[:10]
                meta = s.metadata_ if isinstance(s.metadata_, dict) else {}
                stars_by_date.setdefault(day, []).append(
                    {
                        "number": int(s.value),
                        "username": meta.get("username", "unknown"),
                    }
                )

            # Get existing star events to avoid duplicates
            existing_star_events = await self.db.exec(
                select(InsightEvent).where(InsightEvent.event_type == "star")
            )
            existing_star_dates = {
                str(ev.date)[:10] for ev in existing_star_events.all()
            }

            for day, stars in stars_by_date.items():
                if day in existing_star_dates:
                    continue
                stars.sort(key=lambda x: x["number"])
                usernames = [s["username"] for s in stars]
                numbers = [s["number"] for s in stars]
                if len(stars) == 1:
                    desc = f"\u2b50 #{numbers[0]} — {usernames[0]}"
                else:
                    desc = f"\u2b50 #{numbers[0]}-#{numbers[-1]} ({len(stars)} stars)"
                event = InsightEvent(
                    date=datetime.strptime(day, "%Y-%m-%d"),
                    event_type="star",
                    description=desc,
                    metadata_={"usernames": usernames, "numbers": numbers},
                )
                self.db.add(event)

            await self.db.commit()

            logger.info(
                "GitHub stars collected: %d new, %d existing",
                rows_written,
                rows_skipped,
            )

            return CollectionResult(
                source_key=self.source_key,
                success=True,
                rows_written=rows_written,
                rows_skipped=rows_skipped,
            )

        except httpx.HTTPStatusError as e:
            error_msg = (
                f"GitHub API error: {e.response.status_code} {e.response.text[:200]}"
            )
            logger.error(error_msg)
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                rows_written=rows_written,
                rows_skipped=rows_skipped,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"GitHub stars collection failed: {e}"
            logger.error(error_msg)
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                rows_written=rows_written,
                rows_skipped=rows_skipped,
                error=error_msg,
            )

    async def _fetch_profile(
        self, client: httpx.AsyncClient, user_data: dict
    ) -> StarProfileMetadata:
        """Fetch full user profile from GitHub API."""
        username = user_data.get("login", "unknown")

        try:
            resp = await client.get(f"{GITHUB_API}/users/{username}")
            resp.raise_for_status()
            profile_data = resp.json()
        except Exception:
            # If profile fetch fails, use what we have from stargazer response
            profile_data = user_data

        created_at = profile_data.get("created_at", "")
        account_age = None
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                account_age = (
                    datetime.now() - created_dt.replace(tzinfo=None)
                ).days / 365.25
            except (ValueError, TypeError):
                pass

        return StarProfileMetadata(
            username=username,
            name=profile_data.get("name"),
            location=profile_data.get("location"),
            company=profile_data.get("company"),
            bio=profile_data.get("bio"),
            email=profile_data.get("email"),
            blog=profile_data.get("blog"),
            followers=profile_data.get("followers", 0),
            following=profile_data.get("following", 0),
            public_repos=profile_data.get("public_repos", 0),
            stars_given=profile_data.get("starred_repos_count", 0),
            account_created=created_at or None,
            account_age_years=round(account_age, 1) if account_age else None,
            github_pro=profile_data.get("plan", {}).get("name", "") == "pro",
        )


def _parse_star_date(timestamp: str) -> datetime:
    """Parse starred_at timestamp to date-only datetime."""
    if not timestamp:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
