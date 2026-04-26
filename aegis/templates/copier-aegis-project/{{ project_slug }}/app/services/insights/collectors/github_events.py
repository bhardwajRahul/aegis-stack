"""
GitHub Events collector via ClickHouse public SQL endpoint.

Collects forks, releases, star events, and activity summaries
from the public GitHub events dataset. No authentication required.
"""

import httpx
from app.core.config import settings
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..constants import MetricKeys, Periods, SourceKeys
from ..models import InsightMetric
from ..schemas import ActivitySummaryMetadata, ForkEventMetadata, ReleaseEventMetadata2
from .base import BaseCollector, CollectionResult, clickhouse_query, logger, parse_date

# Event type mapping from ClickHouse enum to ActivitySummaryMetadata fields
EVENT_TYPE_MAP = {
    "PushEvent": "push",
    "IssuesEvent": "issues",
    "PullRequestEvent": "pull_requests",
    "PullRequestReviewEvent": "pull_request_reviews",
    "IssueCommentEvent": "issue_comments",
    "ForkEvent": "forks",
    "WatchEvent": "stars",
    "ReleaseEvent": "releases",
    "CreateEvent": "creates",
    "DeleteEvent": "deletes",
}


class GitHubEventsCollector(BaseCollector):
    """Collects GitHub event data from ClickHouse public dataset."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    @property
    def source_key(self) -> str:
        return SourceKeys.GITHUB_EVENTS

    async def collect(self) -> CollectionResult:
        """Collect forks, releases, star events, and activity summary."""
        owner = settings.INSIGHT_GITHUB_OWNER
        repo = settings.INSIGHT_GITHUB_REPO

        if err := self._validate_config(
            INSIGHT_GITHUB_OWNER=owner, INSIGHT_GITHUB_REPO=repo
        ):
            return err

        repo_name = f"{owner}/{repo}"
        rows_written = 0
        rows_skipped = 0

        try:
            forks_type = await self.get_metric_type(MetricKeys.FORKS)
            releases_type = await self.get_metric_type(MetricKeys.RELEASES)
            stars_type = await self.get_metric_type(MetricKeys.STAR_EVENTS)
            activity_type = await self.get_metric_type(MetricKeys.ACTIVITY_SUMMARY)

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Forks — from GitHub REST API (complete list)
                # ClickHouse misses some forks, so we use the API as primary source
                from ..models import InsightEvent

                token = settings.INSIGHT_GITHUB_TOKEN
                fork_actors: list[tuple[str, str]] = []  # (actor, date_str)
                if token:
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    }
                    page = 1
                    while True:
                        resp = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo}/forks",
                            headers=headers,
                            params={"per_page": 100, "page": page, "sort": "oldest"},
                        )
                        resp.raise_for_status()
                        forks_page = resp.json()
                        if not forks_page:
                            break
                        for fork in forks_page:
                            actor = fork.get("owner", {}).get("login", "")
                            created = fork.get("created_at", "")[:10]
                            if actor and created:
                                fork_actors.append((actor, created))
                        if len(forks_page) < 100:
                            break
                        page += 1
                else:
                    # Fallback to ClickHouse if no GitHub token
                    fork_data = await clickhouse_query(
                        client,
                        f"""
                        SELECT actor_login, toDate(created_at) as day
                        FROM github.github_events
                        WHERE repo_name = '{repo_name}'
                          AND event_type = 'ForkEvent'
                          AND created_at >= '2020-01-01'
                        ORDER BY day DESC
                    """,
                    )
                    fork_actors = [(row[0], row[1]) for row in fork_data]

                # Get existing fork actors to skip duplicates
                existing_forks = await self.db.exec(
                    select(InsightMetric.metadata_).where(
                        InsightMetric.metric_type_id == forks_type.id,
                        InsightMetric.period == Periods.EVENT,
                    )
                )
                existing_actors = {
                    m.get("actor", "")
                    for m in existing_forks.all()
                    if isinstance(m, dict)
                }

                for actor, date_str in fork_actors:
                    if actor in existing_actors:
                        rows_skipped += 1
                        continue

                    date = parse_date(date_str)
                    metadata = ForkEventMetadata(actor=actor, date=date_str)
                    await self.upsert_metric(
                        metric_type=forks_type,
                        date=date,
                        value=1.0,
                        period=Periods.EVENT,
                        metadata=metadata.model_dump(),
                    )
                    rows_written += 1

                # Create InsightEvent for new forks (Recent Activity)
                existing_fork_events = await self.db.exec(
                    select(InsightEvent).where(InsightEvent.event_type == "fork")
                )
                existing_fork_event_actors = {
                    (ev.metadata_ or {}).get("actor", "")
                    for ev in existing_fork_events.all()
                }
                events_created = 0
                for i, (actor, date_str) in enumerate(fork_actors, 1):
                    if actor in existing_fork_event_actors:
                        continue
                    self.db.add(
                        InsightEvent(
                            date=parse_date(date_str),
                            event_type="fork",
                            description=f"Fork #{i}",
                            metadata_={"actor": actor, "number": i},
                        )
                    )
                    events_created += 1
                if events_created:
                    logger.info("Fork events created: %d", events_created)

                # Releases — individual events
                release_data = await clickhouse_query(
                    client,
                    f"""
                    SELECT actor_login, release_tag_name, release_name,
                           toDate(created_at) as day
                    FROM github.github_events
                    WHERE repo_name = '{repo_name}'
                      AND event_type = 'ReleaseEvent'
                      AND created_at >= '2020-01-01'
                    ORDER BY day DESC
                """,
                )

                existing_releases = await self.db.exec(
                    select(InsightMetric.metadata_).where(
                        InsightMetric.metric_type_id == releases_type.id,
                        InsightMetric.period == Periods.EVENT,
                    )
                )
                existing_tags = {
                    m.get("tag", "")
                    for m in existing_releases.all()
                    if isinstance(m, dict)
                }

                for row in release_data:
                    tag = row[1]
                    if tag in existing_tags:
                        rows_skipped += 1
                        continue

                    date = parse_date(row[3])
                    metadata = ReleaseEventMetadata2(
                        tag=tag,
                        name=row[2] or None,
                        actor=row[0],
                    )
                    await self.upsert_metric(
                        metric_type=releases_type,
                        date=date,
                        value=1.0,
                        period=Periods.EVENT,
                        metadata=metadata.model_dump(),
                    )
                    rows_written += 1

                # Daily star count (14 days)
                star_data = await clickhouse_query(
                    client,
                    f"""
                    SELECT toDate(created_at) as day, count() as stars
                    FROM github.github_events
                    WHERE repo_name = '{repo_name}'
                      AND event_type = 'WatchEvent'
                      AND created_at >= today() - 14
                    GROUP BY day ORDER BY day
                """,
                )

                for row in star_data:
                    date = parse_date(row[0])
                    _, created = await self.upsert_metric(
                        metric_type=stars_type,
                        date=date,
                        value=float(row[1]),
                        period=Periods.DAILY,
                    )
                    rows_written += 1 if created else 0
                    rows_skipped += 0 if created else 1

                # Activity summary (14 days, one row per day)
                activity_data = await clickhouse_query(
                    client,
                    f"""
                    SELECT toDate(created_at) as day, event_type, count() as cnt
                    FROM github.github_events
                    WHERE repo_name = '{repo_name}'
                      AND created_at >= today() - 14
                    GROUP BY day, event_type
                    ORDER BY day
                """,
                )

                # Group by day
                daily_activity: dict[str, dict[str, int]] = {}
                for row in activity_data:
                    day = row[0]
                    event_type = row[1]
                    count = int(row[2])
                    if day not in daily_activity:
                        daily_activity[day] = {}
                    field = EVENT_TYPE_MAP.get(event_type)
                    if field:
                        daily_activity[day][field] = count

                for day_str, events in daily_activity.items():
                    date = parse_date(day_str)
                    total_events = sum(events.values())
                    metadata = ActivitySummaryMetadata(**events)
                    _, created = await self.upsert_metric(
                        metric_type=activity_type,
                        date=date,
                        value=float(total_events),
                        period=Periods.DAILY,
                        metadata=metadata.model_dump(),
                    )
                    rows_written += 1 if created else 0
                    rows_skipped += 0 if created else 1

            await self.db.commit()
            return self._success(rows_written, rows_skipped)

        except Exception as e:
            return self._error(
                f"GitHub events collection failed: {e}", rows_written, rows_skipped
            )
