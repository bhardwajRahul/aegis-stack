"""
Reddit post tracker.

Lightweight collector — primarily manual entry via CLI/API.
Stores post stats as snapshot rows with metadata.
"""

import logging
from datetime import datetime

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from ..constants import MetricKeys, Periods, SourceKeys
from ..schemas import RedditPostMetadata
from .base import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)


class RedditCollector(BaseCollector):
    """Tracks Reddit post stats."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    @property
    def source_key(self) -> str:
        return SourceKeys.REDDIT

    async def collect(self) -> CollectionResult:
        """Refresh stats for all tracked posts. Not scheduled — called on demand."""
        return CollectionResult(
            source_key=self.source_key,
            success=True,
            error="Reddit collection is on-demand only. Use add_post() or refresh_post().",
        )

    async def add_post(self, url: str) -> CollectionResult:
        """
        Add a Reddit post to track by fetching its current stats.

        Args:
            url: Reddit post URL (e.g., https://reddit.com/r/python/comments/abc123/...)
        """
        rows_written = 0

        try:
            post_type = await self.get_metric_type(MetricKeys.POST_STATS)

            # Fetch post data via Reddit JSON API (append .json to URL)
            json_url = url.rstrip("/") + ".json"

            async with httpx.AsyncClient(
                timeout=15.0,
                headers={"User-Agent": "aegis-insights/1.0"},
                follow_redirects=True,
            ) as client:
                resp = await client.get(json_url)
                resp.raise_for_status()
                data = resp.json()

            # Reddit returns an array of listings
            post_data = data[0]["data"]["children"][0]["data"]

            post_id = post_data.get("id", "")
            metadata = RedditPostMetadata(
                post_id=post_id,
                subreddit=post_data.get("subreddit", ""),
                title=post_data.get("title", ""),
                comments=post_data.get("num_comments", 0),
                views=post_data.get("view_count"),
                upvote_ratio=post_data.get("upvote_ratio"),
                url=url,
            )

            today = _today()
            upvotes = post_data.get("ups", 0)

            await self.upsert_metric(
                metric_type=post_type,
                date=today,
                value=float(upvotes),
                period=Periods.EVENT,
                metadata=metadata.model_dump(),
            )
            rows_written += 1

            # Also create an event for the timeline
            from sqlmodel import select

            from ..models import InsightEvent

            # Only create event if one doesn't exist for this post
            existing_events = await self.db.exec(
                select(InsightEvent).where(InsightEvent.event_type == "reddit_post")
            )
            already_tracked = any(
                (ev.metadata_ or {}).get("post_id") == post_id
                for ev in existing_events.all()
            )
            if not already_tracked:
                subreddit = post_data.get("subreddit", "")
                title = post_data.get("title", "")
                from datetime import datetime

                created = post_data.get("created_utc", 0)
                post_date = (
                    datetime.fromtimestamp(created).replace(tzinfo=None)
                    if created
                    else today
                )

                event = InsightEvent(
                    date=post_date,
                    event_type="reddit_post",
                    description=f"r/{subreddit} — {title[:80]}",
                    metadata_={"post_id": post_id, "subreddit": subreddit, "url": url},
                )
                self.db.add(event)

            await self.db.commit()

            logger.info(
                "Reddit post added: %s (%d upvotes)",
                post_id,
                upvotes,
            )

            return CollectionResult(
                source_key=self.source_key,
                success=True,
                rows_written=rows_written,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"Reddit API error: {e.response.status_code}"
            logger.error(error_msg)
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                error=error_msg,
            )
        except (KeyError, IndexError) as e:
            error_msg = f"Failed to parse Reddit response: {e}"
            logger.error(error_msg)
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                error=error_msg,
            )
        except Exception as e:
            error_msg = f"Reddit post tracking failed: {e}"
            logger.error(error_msg)
            return CollectionResult(
                source_key=self.source_key,
                success=False,
                error=error_msg,
            )


def _today() -> datetime:
    """Get today as a midnight datetime (no timezone)."""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
