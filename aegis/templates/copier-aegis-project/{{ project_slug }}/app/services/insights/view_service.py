"""Transform raw insight data into display-ready views.

InsightViewService is the single source of truth for all data
transformation logic. Both Flet and htmx frontends consume its output.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from .query_service import InsightQueryService
from .schemas import (
    BulkInsightsResponse,
    PlausibleTopCountriesMetadata,
    PlausibleTopPagesMetadata,
    PlausibleTopSourcesMetadata,
    PyPICountryBreakdown,
    PyPIDownloadMetadata,
    PyPIInstallerBreakdown,
    PyPITypeBreakdown,
)
from .view_schemas import (
    ActivityDay,
    ActivityEventView,
    BreakdownItem,
    DailyTrafficPoint,
    DailyValuePoint,
    DocsPageStats,
    DocsView,
    EventTypeOption,
    GitHubView,
    MetricCardView,
    MilestoneView,
    OverviewHero,
    OverviewView,
    ProjectInfoView,
    PyPIView,
    RedditPostView,
    RedditView,
    SpotlightCard,
    StargazerView,
    StarsView,
    TrafficItem,
    VersionSeries,
)


def _referrer_url(name: str) -> str:
    """Build a click-through URL for a referrer row.

    Names look like `github.com`, `google.com`, `lbedner.github.io`, or
    sometimes `com.reddit.frontpage` (mobile reverse-domain). We trust the
    first two cases (host shape) and skip anything that doesn't look like
    a hostname so we don't ship junk hrefs.
    """
    if not name or "." not in name or " " in name:
        return ""
    if name.startswith("http://") or name.startswith("https://"):
        return name
    return f"https://{name}"


def _page_url(site: str, path: str) -> str:
    """Build a docs page URL from a Plausible (site, path) pair.

    Plausible only stores the path (`/docs/cli/insights`); the site comes
    from the snapshot metadata (`docs.example.com`). Returns empty string
    if either piece is missing — UI then falls back to plain text.
    """
    if not site or not path:
        return ""
    site = site.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"https://{site}{path}"


def _semver_tuple(v: str) -> tuple[tuple[int, ...], str]:
    """Parse '0.6.10' → ((0, 6, 10), '') for sort; trailing pre-release suffix preserved."""
    import re

    m = re.match(r"^(\d+(?:\.\d+)*)(.*)$", v)
    if not m:
        return ((0,), v)
    nums = tuple(int(x) for x in m.group(1).split("."))
    return (nums, m.group(2))


# ---------------------------------------------------------------------------
# Event type filters per tab
# ---------------------------------------------------------------------------

GITHUB_EVENT_TYPES = {
    "release",
    "fork",
    "star",
    "feature",
    "milestone_github",
    "anomaly_github",
    "localization",
    "external",
}
PYPI_EVENT_TYPES = {
    "release",
    "reddit_post",
    "star",
    "feature",
    "milestone_pypi",
    "localization",
    "external",
}
DOCS_EVENT_TYPES = {
    "release",
    "feature",
    "milestone_plausible",
    "localization",
    "external",
}

# Event type → display color
EVENT_COLORS: dict[str, str] = {
    "release": "success",
    "star": "warning",
    "fork": "secondary",
    "reddit_post": "error",
    "feature": "info",
    "milestone_github": "accent",
    "milestone_pypi": "accent",
    "anomaly_github": "error",
    "localization": "info",
    "external": "neutral",
}

# Milestone event type → card color
MILESTONE_COLORS: dict[str, str] = {
    "milestone_github": "success",
    "milestone_pypi": "accent",
    "milestone_plausible": "secondary",
    "feature": "info",
}


class InsightViewService:
    """Transforms BulkInsightsResponse into display-ready view models."""

    def __init__(self, bulk: BulkInsightsResponse) -> None:
        self._bulk = bulk

    # -- static helpers (exposed for testing) --------------------------------

    @staticmethod
    def _pct(current: float, previous: float) -> int | None:
        """Period-over-period percentage change. None if no previous data."""
        if previous == 0:
            return None
        return int(((current - previous) / previous) * 100)

    @staticmethod
    def _extract_max_number(text: str) -> str:
        """Extract the largest number from text, preserving commas.

        e.g. '5,292 clones, 777 unique' → '5,292'
        """
        numbers = re.findall(r"\d[\d,]*", text)
        if not numbers:
            return ""
        return max(numbers, key=lambda n: int(n.replace(",", "")))

    @staticmethod
    def _event_color(event_type: str) -> str:
        """Map event type to a display color."""
        return EVENT_COLORS.get(event_type, "primary")

    @staticmethod
    def _pretty_date(dt: datetime | str) -> str:
        """Format date as 'March 20, 2026'."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return dt
        return dt.strftime("%B %d, %Y")

    @staticmethod
    def _short_date(dt: datetime | str) -> str:
        """Format date as 'Apr 03'."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return dt
        return dt.strftime("%b %d")

    @staticmethod
    def _day_str(dt: datetime | str) -> str:
        """Format date as '2026-04-10'."""
        if isinstance(dt, str):
            return dt[:10]
        return dt.strftime("%Y-%m-%d")

    # -- event helpers -------------------------------------------------------

    @staticmethod
    def _group_events(
        events: list[tuple[str, str, str]], days: int
    ) -> list[tuple[str, str, str, set[str]]]:
        """Group same-type events by time bucket for cleaner display.

        Ported from Overseer insights_modal._group_events.

        Args:
            events: list of (date_yyyy_mm_dd, label, event_type) tuples
            days: visible range in days

        Returns:
            list of (display_date, label, event_type, dates_set) tuples
        """
        if days <= 30 or not events:
            rows = [(date, label, etype, {date}) for date, label, etype in events]
            rows.sort(key=lambda x: x[0], reverse=True)
            return rows

        if days <= 90:

            def bucket_key(date_str: str) -> str:
                d = datetime.strptime(date_str, "%Y-%m-%d")
                iso = d.isocalendar()
                return f"{iso[0]}-W{iso[1]:02d}"
        else:

            def bucket_key(date_str: str) -> str:
                return date_str[:7]  # YYYY-MM

        buckets: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for date, label, etype in events:
            key = (bucket_key(date), etype)
            buckets.setdefault(key, []).append((date, label))

        result: list[tuple[str, str, str, set[str]]] = []
        for (_, etype), items in buckets.items():
            dates = {d for d, _ in items}
            first_date = min(dates)

            if len(items) == 1:
                result.append((items[0][0], items[0][1], etype, dates))
                continue

            if etype == "release":
                tags = [lbl for _, lbl in sorted(items)]
                label = f"{tags[0]}\u2013{tags[-1]}" if len(tags) > 1 else tags[0]
            elif etype == "star":
                nums: list[int] = []
                for _, lbl in items:
                    for m in re.findall(r"#(\d+)", lbl):
                        nums.append(int(m))
                if nums:
                    label = f"\u2b50 #{min(nums)}-#{max(nums)} ({len(items)} events)"
                else:
                    label = f"\u2b50 ({len(items)} stars)"
            elif etype == "reddit_post" or etype.startswith("milestone_"):
                # Keep these individual — each carries unique info (reddit
                # post title, or milestone value like "804 clones") that
                # would be lost under a "(N)" collapse.
                for date, lbl in items:
                    result.append((date, lbl, etype, {date}))
                continue
            else:
                label = f"{etype} ({len(items)})"

            result.append((first_date, label, etype, dates))

        result.sort(key=lambda x: x[0], reverse=True)
        return result

    def _raw_events(
        self, type_set: set[str] | None, cutoff: datetime | None = None
    ) -> list[tuple[str, str, str]]:
        """Gather (date, label, event_type) tuples from insight_events + release metrics."""
        results: list[tuple[str, str, str]] = []

        for e in self._bulk.insight_events:
            if type_set is not None and e.event_type not in type_set:
                continue
            if cutoff is not None and e.date < cutoff:
                continue
            results.append((self._day_str(e.date), e.description, e.event_type))

        include_releases = type_set is None or "release" in type_set
        if include_releases:
            for r in self._bulk.events.get("releases", []):
                if cutoff is not None and r.date < cutoff:
                    continue
                meta = r.metadata_ if hasattr(r, "metadata_") else {}
                tag = meta.get("tag", "") if isinstance(meta, dict) else ""
                if tag:
                    results.append((self._day_str(r.date), tag, "release"))

        return results

    def _event_type_options(
        self, events: list[ActivityEventView]
    ) -> list[EventTypeOption]:
        """Distinct event_type keys across a view's events, with friendly labels.

        Drives the filter chip menu on the frontend. Computed from the view's
        own events (not the full bulk) so each page gets only types that
        actually appear there — no dead chips.
        """
        from app.services.insights.models import event_type_display

        seen: set[str] = set()
        out: list[EventTypeOption] = []
        for ev in events:
            if ev.event_type in seen:
                continue
            seen.add(ev.event_type)
            out.append(
                EventTypeOption(
                    key=ev.event_type, label=event_type_display(ev.event_type)
                )
            )
        out.sort(key=lambda o: o.label.lower())
        return out

    def _to_activity_events(
        self, grouped: list[tuple[str, str, str, set[str]]]
    ) -> list[ActivityEventView]:
        """Convert grouped tuples to ActivityEventView list."""
        return [
            ActivityEventView(
                event_type=etype,
                description=label,
                date=self._short_date(date),
                date_keys=sorted(d[5:] for d in dates),
                color=self._event_color(etype),
            )
            for date, label, etype, dates in grouped
        ]

    def _filter_events(
        self, type_set: set[str], cutoff: datetime | None = None, days: int = 14
    ) -> list[ActivityEventView]:
        """Filter and format events for a tab, with range-dependent bucketing."""
        raw = self._raw_events(type_set, cutoff)
        grouped = self._group_events(raw, days)
        return self._to_activity_events(grouped)

    def _all_events(self, days: int = 14) -> list[ActivityEventView]:
        """All events in the date range, sorted newest first, with range-
        dependent bucketing. The `days` arg drives BOTH the cutoff (so
        out-of-range events don't leak through) and the bucket width.
        """
        cutoff, _ = InsightQueryService.compute_cutoffs(days)
        raw = self._raw_events(None, cutoff)
        grouped = self._group_events(raw, days)
        return self._to_activity_events(grouped)

    def _recent_events_ungrouped(self, days: int = 90) -> list[ActivityEventView]:
        """Raw sequential events (no same-type bucketing) for the Overview
        Recent Activity feed. Each `insight_event` / release row becomes its
        own entry so the user sees an actual timeline — two issues closed
        on the same day stay as two rows, not one merged "issue_closed (2)".
        """
        cutoff, _ = InsightQueryService.compute_cutoffs(days)
        raw = self._raw_events(None, cutoff)
        raw.sort(key=lambda t: t[0], reverse=True)
        return [
            ActivityEventView(
                event_type=etype,
                description=label,
                date=self._short_date(date),
                date_keys=[date[5:]],
                color=self._event_color(etype),
            )
            for date, label, etype in raw
        ]

    # -- referrers (shared between github + overview) ------------------------

    def _repo_referrers(self) -> list[TrafficItem]:
        """Parse GitHub repo referrer snapshot into TrafficItem list."""
        referrers: list[TrafficItem] = []
        row = self._bulk.latest.get("referrers")
        if not row or not row.metadata_:
            return referrers
        meta = row.metadata_
        if isinstance(meta, dict) and not meta.get("referrers"):
            for domain, counts in meta.items():
                if isinstance(counts, dict):
                    referrers.append(
                        TrafficItem(
                            name=domain,
                            views=counts.get("views", 0),
                            uniques=counts.get("uniques", 0),
                            url=_referrer_url(domain),
                        )
                    )
        else:
            for ref in meta.get("referrers", []):
                name = ref.get("referrer", ref.get("domain", "unknown"))
                referrers.append(
                    TrafficItem(
                        name=name,
                        views=ref.get("count", ref.get("views", 0)),
                        uniques=ref.get("uniques", 0),
                        url=_referrer_url(name),
                    )
                )
        referrers.sort(key=lambda x: -x.views)
        return referrers

    def _docs_referrers(self) -> list[TrafficItem]:
        """Parse Plausible docs referrer data into TrafficItem list.

        TODO: the Plausible collector doesn't yet call /stats/breakdown with
        `property=visit:source`. When it does, this will parse the resulting
        `top_sources` metric the same way `_repo_referrers` parses the GitHub
        `referrers` snapshot.
        """
        return []

    # -- milestone extraction ------------------------------------------------

    def _milestones(self) -> list[MilestoneView]:
        """Extract milestone cards: best value per category, sorted newest first."""
        best_per_category: dict[str, dict[str, Any]] = {}

        for ev in self._bulk.insight_events:
            if ev.event_type not in ("milestone_github", "milestone_pypi", "feature"):
                continue

            meta = ev.metadata_ if isinstance(ev.metadata_, dict) else {}
            category = meta.get("category", ev.description)

            hero_str = (
                self._extract_max_number(ev.description)
                if ev.event_type != "feature"
                else ""
            )
            value = int(hero_str.replace(",", "")) if hero_str else 0

            existing = best_per_category.get(category)
            if existing is None or value > existing.get("_value", 0):
                best_per_category[category] = {
                    "date": ev.date,
                    "description": ev.description,
                    "event_type": ev.event_type,
                    "category": category,
                    "hero_str": hero_str,
                    "_value": value,
                }

        milestones = sorted(
            best_per_category.values(), key=lambda m: m["date"], reverse=True
        )

        result: list[MilestoneView] = []
        for m in milestones:
            label = (
                m["category"].replace("_", " ").title()
                if m["category"] != m["description"]
                else m["description"][:30]
            )
            # Feature events show description as value; milestones show the number
            if m["event_type"] == "feature":
                display_value = m["description"]
            else:
                display_value = m["hero_str"] or "—"

            result.append(
                MilestoneView(
                    label=label,
                    value=display_value,
                    date=self._pretty_date(m["date"]),
                    color=MILESTONE_COLORS.get(m["event_type"], "primary"),
                    event_type=m["event_type"],
                )
            )

        return result

    # -- traffic helpers -----------------------------------------------------

    def _traffic_sums(self, days: int = 14) -> dict[str, Any]:
        """Compute current and previous period traffic sums."""
        cutoff, prev_cutoff = InsightQueryService.compute_cutoffs(days)
        bulk = self._bulk

        keys = ["clones", "unique_cloners", "views", "unique_visitors"]
        current: dict[str, float] = {}
        previous: dict[str, float] = {}

        for key in keys:
            rows = bulk.daily.get(key, [])
            current[key] = sum(r.value for r in rows if r.date >= cutoff)
            previous[key] = sum(r.value for r in rows if prev_cutoff <= r.date < cutoff)

        return {"current": current, "previous": previous, "cutoff": cutoff}

    # -- tab views -----------------------------------------------------------

    def overview(self, days: int = 14) -> OverviewView:
        """Build overview tab data.

        Hero metric is **average daily unique cloners** over the selected
        range — the editorial king metric. It's a rate, not a sum, so it
        stays interpretable across any range without the "are these
        deduplicated?" footgun that plagues a raw 14d-unique total.
        """
        cutoff, prev_cutoff = InsightQueryService.compute_cutoffs(days)
        bulk = self._bulk

        clones_rows = [r for r in bulk.daily.get("clones", []) if r.date >= cutoff]
        unique_rows = [
            r for r in bulk.daily.get("unique_cloners", []) if r.date >= cutoff
        ]
        views_rows = [r for r in bulk.daily.get("views", []) if r.date >= cutoff]
        visitors_rows = [
            r for r in bulk.daily.get("unique_visitors", []) if r.date >= cutoff
        ]

        # Build the daily series for the chart — same shape as the
        # GitHub tab so the chart renderer stays uniform.
        unique_map = {self._day_str(r.date): int(r.value) for r in unique_rows}
        views_map = {self._day_str(r.date): int(r.value) for r in views_rows}
        visitors_map = {self._day_str(r.date): int(r.value) for r in visitors_rows}
        daily: list[DailyTrafficPoint] = [
            DailyTrafficPoint(
                date=self._day_str(r.date),
                clones=int(r.value),
                unique_cloners=unique_map.get(self._day_str(r.date), 0),
                views=views_map.get(self._day_str(r.date), 0),
                unique_visitors=visitors_map.get(self._day_str(r.date), 0),
            )
            for r in clones_rows
        ]

        total_clones = sum(d.clones for d in daily)
        total_unique = sum(d.unique_cloners for d in daily)
        total_views = sum(d.views for d in daily)

        # Avg-daily metrics: sum across days we have data for, divide by
        # the count of those days. Using observed days (not the requested
        # range length) avoids deflating the average when collection
        # started mid-range or skipped a day.
        observed_days = len(daily) or 1
        avg_unique = total_unique / observed_days
        avg_clones = total_clones / observed_days

        # Prior-period comparison for the hero card. Symmetric window so
        # the % change is apples-to-apples.
        prev_unique_rows = [
            r
            for r in bulk.daily.get("unique_cloners", [])
            if prev_cutoff <= r.date < cutoff
        ]
        prev_observed = len(prev_unique_rows) or 1
        prev_avg_unique = sum(r.value for r in prev_unique_rows) / prev_observed
        hero_change = self._pct(avg_unique, prev_avg_unique)

        prev_clones_total = sum(
            r.value
            for r in bulk.daily.get("clones", [])
            if prev_cutoff <= r.date < cutoff
        )
        prev_views_total = sum(
            r.value
            for r in bulk.daily.get("views", [])
            if prev_cutoff <= r.date < cutoff
        )

        # Cumulative stars series — star-history style. Carries running
        # total forward on quiet days so the curve is monotonic.
        star_events = bulk.events.get("new_star", [])
        stars_daily: list[DailyValuePoint] = []
        if star_events:
            sorted_events = sorted(star_events, key=lambda r: r.date)
            per_day: dict[str, int] = {}
            for r in sorted_events:
                day = self._day_str(r.date)
                per_day[day] = per_day.get(day, 0) + 1
            start = datetime.strptime(self._day_str(sorted_events[0].date), "%Y-%m-%d")
            end = datetime.now(UTC).replace(tzinfo=None)
            running = 0
            cursor = start
            while cursor.date() <= end.date():
                day = cursor.strftime("%Y-%m-%d")
                running += per_day.get(day, 0)
                if cursor >= cutoff:
                    stars_daily.append(DailyValuePoint(date=day, value=running))
                cursor += timedelta(days=1)

        # --- Secondary metric cards ---------------------------------------
        # Last-day-delta labels for cards where "what happened yesterday"
        # is more interesting than the % change.
        def _last_day_label(key: str) -> str | None:
            rows = bulk.daily.get(key, [])
            if not rows:
                return None
            last = rows[-1]
            day_str = self._day_str(last.date)
            now = datetime.now(UTC).replace(tzinfo=None)
            try:
                dt = datetime.strptime(day_str, "%Y-%m-%d")
            except ValueError:
                return None
            days_ago = (now - dt).days
            val = int(last.value)
            prefix = f"+{val}" if val >= 0 else str(val)
            if days_ago == 0:
                return f"{prefix} today"
            if days_ago == 1:
                return f"{prefix} yesterday"
            return f"{prefix} {days_ago}d ago"

        # Stars label: last star event, e.g. "+1 8d ago"
        star_label = None
        if star_events:
            last_star = star_events[-1]
            day_str = self._day_str(last_star.date)
            now = datetime.now(UTC).replace(tzinfo=None)
            try:
                dt = datetime.strptime(day_str, "%Y-%m-%d")
                days_ago = (now - dt).days
                star_label = (
                    "+1 today"
                    if days_ago == 0
                    else "+1 yesterday"
                    if days_ago == 1
                    else f"+1 {days_ago}d ago"
                )
            except ValueError:
                pass

        total_row = bulk.latest.get("downloads_total")
        visitors_docs_in_range = sum(
            int(r.value) for r in bulk.daily.get("visitors", []) if r.date >= cutoff
        )
        prev_visitors_docs = sum(
            int(r.value)
            for r in bulk.daily.get("visitors", [])
            if prev_cutoff <= r.date < cutoff
        )

        # Five supporting cards. Repo-side Views shows reach beyond clones;
        # Docs Visitors shows the documentation funnel. Pageviews and unique
        # visitors are covered by their respective dedicated tabs — keep the
        # overview row to a clean single line on desktop.
        metrics = [
            MetricCardView(
                label="Stars",
                value=len(star_events),
                change_label=star_label,
            ),
            MetricCardView(
                label="PyPI Downloads",
                value=int(total_row.value) if total_row else 0,
                change_label=_last_day_label("downloads_daily"),
            ),
            MetricCardView(
                label="Clones",
                value=int(total_clones),
                change_pct=self._pct(total_clones, prev_clones_total),
                change_label=_last_day_label("clones"),
            ),
            MetricCardView(
                label="Repo Views",
                value=int(total_views),
                change_pct=self._pct(total_views, prev_views_total),
                change_label=_last_day_label("views"),
            ),
            MetricCardView(
                label="Docs Visitors",
                value=visitors_docs_in_range,
                change_pct=self._pct(visitors_docs_in_range, prev_visitors_docs),
            ),
        ]

        # Hero is None when we have zero cloner data — UI hides the card
        # rather than render an empty "0 / day" placeholder.
        hero: OverviewHero | None = None
        if unique_rows or clones_rows:
            hero = OverviewHero(
                avg_daily_unique_cloners=round(avg_unique, 1),
                range_days=days,
                change_pct=hero_change,
                total_unique_cloners=int(total_unique),
                total_clones=int(total_clones),
                avg_daily_clones=round(avg_clones, 1),
            )

        # Recent Activity feed is decoupled from the metric window (the
        # cards above already scope to `days`) and intentionally un-grouped
        # — the feed is a timeline of what happened, not a daily summary.
        events = self._recent_events_ungrouped(days=90)
        return OverviewView(
            project=self._project_info(),
            hero=hero,
            metrics=metrics,
            milestones=self._milestones(),
            daily=daily,
            stars_daily=stars_daily,
            events=events,
            event_types=self._event_type_options(events),
        )

    def _project_info(self) -> ProjectInfoView | None:
        """Build the hero card model from settings + live data.

        Returns None if nothing's configured (no GitHub owner/repo AND no
        explicit project name) so the UI can hide the card entirely rather
        than render an empty shell.
        """
        from app.core.config import settings

        owner = (settings.INSIGHT_GITHUB_OWNER or "").strip()
        repo = (settings.INSIGHT_GITHUB_REPO or "").strip()
        name = (settings.INSIGHT_PROJECT_NAME or "").strip() or repo
        if not name:
            return None

        github_repo_slug = f"{owner}/{repo}" if (owner and repo) else None
        github_url = (
            f"https://github.com/{github_repo_slug}" if github_repo_slug else None
        )

        pypi_package = (settings.INSIGHT_PYPI_PACKAGE or "").strip() or None
        pypi_url = f"https://pypi.org/project/{pypi_package}/" if pypi_package else None

        # Live counts pulled from bulk data. Different metrics are stored
        # differently: stars/forks as per-event rows, downloads as a single
        # cumulative snapshot, docs counters as daily aggregates — so the
        # card reads each from its native shape.
        bulk = self._bulk

        # Stars: count event rows; fall back to `insight_events` rows with
        # event_type='star' if the metric-events table is empty (e.g., data
        # migrated from an older collector version).
        stars = len(bulk.events.get("new_star", []))
        if stars == 0:
            stars = sum(1 for ev in bulk.insight_events if ev.event_type == "star")
        stars = stars or None

        # Forks: same treatment — metric-events first, fallback to insight_events.
        fork_events = bulk.events.get("forks") or bulk.events.get("fork") or []
        forks = len(fork_events)
        if forks == 0:
            forks = sum(
                1 for ev in bulk.insight_events if ev.event_type in {"fork", "forks"}
            )
        forks = forks or None

        # Downloads: cumulative snapshot.
        downloads_row = bulk.latest.get("downloads_total")
        downloads_total = int(downloads_row.value) if downloads_row else None

        # Docs: daily counters summed across all rows we have.
        pageviews = sum(int(r.value) for r in bulk.daily.get("pageviews", []))
        visitors = sum(int(r.value) for r in bulk.daily.get("visitors", []))

        return ProjectInfoView(
            name=name,
            description=(settings.INSIGHT_PROJECT_DESCRIPTION or "").strip(),
            github_url=github_url,
            github_repo=github_repo_slug,
            homepage_url=(settings.INSIGHT_PROJECT_HOMEPAGE or "").strip() or None,
            pypi_package=pypi_package,
            pypi_url=pypi_url,
            stars=stars,
            forks=forks,
            downloads_total=downloads_total,
            docs_pageviews=pageviews or None,
            docs_visitors=visitors or None,
        )

    def github(self, days: int = 14) -> GitHubView:
        """Build GitHub tab data."""
        cutoff, prev_cutoff = InsightQueryService.compute_cutoffs(days)
        bulk = self._bulk

        clones_rows = [r for r in bulk.daily.get("clones", []) if r.date >= cutoff]
        unique_rows = [
            r for r in bulk.daily.get("unique_cloners", []) if r.date >= cutoff
        ]
        views_rows = [r for r in bulk.daily.get("views", []) if r.date >= cutoff]
        visitors_rows = [
            r for r in bulk.daily.get("unique_visitors", []) if r.date >= cutoff
        ]

        unique_map = {self._day_str(r.date): int(r.value) for r in unique_rows}
        views_map = {self._day_str(r.date): int(r.value) for r in views_rows}
        visitors_map = {self._day_str(r.date): int(r.value) for r in visitors_rows}

        daily: list[DailyTrafficPoint] = []
        for r in clones_rows:
            day = self._day_str(r.date)
            daily.append(
                DailyTrafficPoint(
                    date=day,
                    clones=int(r.value),
                    unique_cloners=unique_map.get(day, 0),
                    views=views_map.get(day, 0),
                    unique_visitors=visitors_map.get(day, 0),
                )
            )

        total_clones = sum(d.clones for d in daily)
        total_unique = sum(d.unique_cloners for d in daily)
        total_views = sum(d.views for d in daily)
        total_visitors = sum(d.unique_visitors for d in daily)

        prev_clones = sum(
            r.value
            for r in bulk.daily.get("clones", [])
            if prev_cutoff <= r.date < cutoff
        )
        prev_unique = sum(
            r.value
            for r in bulk.daily.get("unique_cloners", [])
            if prev_cutoff <= r.date < cutoff
        )
        prev_views = sum(
            r.value
            for r in bulk.daily.get("views", [])
            if prev_cutoff <= r.date < cutoff
        )
        prev_visitors = sum(
            r.value
            for r in bulk.daily.get("unique_visitors", [])
            if prev_cutoff <= r.date < cutoff
        )

        # Forks & releases are event-keyed (each row = one fork/release), not daily counts.
        forks_total = sum(1 for r in bulk.events.get("forks", []) if r.date >= cutoff)
        releases_total = sum(
            1 for r in bulk.events.get("releases", []) if r.date >= cutoff
        )
        prev_forks = sum(
            1 for r in bulk.events.get("forks", []) if prev_cutoff <= r.date < cutoff
        )
        prev_releases = sum(
            1 for r in bulk.events.get("releases", []) if prev_cutoff <= r.date < cutoff
        )

        clone_ratio = (
            f"{total_clones / total_unique:.1f}:1" if total_unique > 0 else "—"
        )

        metrics = [
            MetricCardView(
                label="Clones",
                value=total_clones,
                change_pct=self._pct(total_clones, prev_clones),
            ),
            MetricCardView(
                label="Unique",
                value=total_unique,
                change_pct=self._pct(total_unique, prev_unique),
            ),
            MetricCardView(
                label="Views",
                value=total_views,
                change_pct=self._pct(total_views, prev_views),
            ),
            MetricCardView(
                label="Visitors",
                value=total_visitors,
                change_pct=self._pct(total_visitors, prev_visitors),
            ),
            MetricCardView(label="Clone Ratio", value=clone_ratio),
            MetricCardView(
                label="Forks",
                value=forks_total,
                change_pct=self._pct(forks_total, prev_forks),
            ),
            MetricCardView(
                label="Releases",
                value=releases_total,
                change_pct=self._pct(releases_total, prev_releases),
            ),
        ]

        referrers = self._repo_referrers()

        # Popular paths (latest snapshot)
        popular_paths: list[TrafficItem] = []
        paths_row = bulk.latest.get("popular_paths")
        if paths_row and paths_row.metadata_:
            for p in paths_row.metadata_.get(
                "paths", paths_row.metadata_.get("popular_paths", [])
            ):
                popular_paths.append(
                    TrafficItem(
                        name=p.get("path", "unknown"),
                        views=p.get("count", p.get("views", 0)),
                        uniques=p.get("uniques", 0),
                    )
                )
            popular_paths.sort(key=lambda x: -x.views)

        # Activity summary (bucketed into 5 categories)
        activity: list[ActivityDay] = []
        activity_rows = [
            r for r in bulk.daily.get("activity_summary", []) if r.date >= cutoff
        ]
        for r in activity_rows:
            meta = r.metadata_ if hasattr(r, "metadata_") else {}
            if not isinstance(meta, dict):
                meta = {}
            activity.append(
                ActivityDay(
                    date=self._day_str(r.date),
                    code=sum(meta.get(f, 0) for f in ("push", "creates", "deletes")),
                    issues=sum(meta.get(f, 0) for f in ("issues", "issue_comments")),
                    prs=sum(
                        meta.get(f, 0)
                        for f in ("pull_requests", "pull_request_reviews")
                    ),
                    community=sum(meta.get(f, 0) for f in ("forks", "stars")),
                    releases=meta.get("releases", 0),
                )
            )

        # Average unique cloners by day of week, Sun..Sat. Python's
        # weekday() is Mon=0..Sun=6; (w+1)%7 reorders it to Sun-first so
        # the client can index straight into a labels array. Days with no
        # metric row are simply absent from unique_rows (not zero-filled),
        # so the average only considers days we actually have data for.
        # Empty list when there's no cloner data at all — matches the
        # schema contract so the client can distinguish "no data" from
        # "all zeroes".
        unique_cloners_by_weekday: list[float]
        if not unique_rows:
            unique_cloners_by_weekday = []
        else:
            weekday_sums: list[int] = [0] * 7
            weekday_counts: list[int] = [0] * 7
            for r in unique_rows:
                idx = (r.date.weekday() + 1) % 7
                weekday_sums[idx] += int(r.value)
                weekday_counts[idx] += 1
            unique_cloners_by_weekday = [
                (weekday_sums[i] / weekday_counts[i]) if weekday_counts[i] else 0.0
                for i in range(7)
            ]

        events = self._filter_events(GITHUB_EVENT_TYPES, cutoff=cutoff, days=days)
        return GitHubView(
            metrics=metrics,
            daily=daily,
            events=events,
            event_types=self._event_type_options(events),
            referrers=referrers,
            popular_paths=popular_paths,
            activity=activity,
            unique_cloners_by_weekday=unique_cloners_by_weekday,
        )

    def stars(self, days: int = 14) -> StarsView:
        """Build stars tab data."""
        star_events = self._bulk.events.get("new_star", [])
        cutoff, _ = InsightQueryService.compute_cutoffs(days)

        # Build cumulative-by-day series: one point per calendar day from first
        # star to today, carrying running total forward on quiet days. This
        # gives a smooth monotonic curve (star-history.com style) instead of
        # jagged per-event spikes.
        daily: list[DailyValuePoint] = []
        if star_events:
            sorted_events = sorted(star_events, key=lambda r: r.date)
            per_day: dict[str, int] = {}
            for r in sorted_events:
                day = self._day_str(r.date)
                per_day[day] = per_day.get(day, 0) + 1

            start = datetime.strptime(self._day_str(sorted_events[0].date), "%Y-%m-%d")
            end = datetime.now(UTC).replace(tzinfo=None)
            running = 0
            cursor = start
            while cursor.date() <= end.date():
                day = cursor.strftime("%Y-%m-%d")
                running += per_day.get(day, 0)
                if cursor >= cutoff:
                    daily.append(DailyValuePoint(date=day, value=running))
                cursor += timedelta(days=1)

        # Recent stargazer profiles from metadata
        recent_stars: list[StargazerView] = []
        for r in reversed(star_events[-20:]):
            meta = r.metadata_ if hasattr(r, "metadata_") else {}
            if isinstance(meta, dict) and meta.get("username"):
                recent_stars.append(
                    StargazerView(
                        username=meta.get("username") or "",
                        location=meta.get("location") or "",
                        company=meta.get("company") or "",
                        followers=meta.get("followers") or 0,
                        date=self._short_date(r.date),
                    )
                )

        # Country aggregation from star locations
        country_counts: dict[str, int] = {}
        for r in star_events:
            meta = r.metadata_ if hasattr(r, "metadata_") else {}
            loc = meta.get("location", "") if isinstance(meta, dict) else ""
            if loc:
                country_counts[loc] = country_counts.get(loc, 0) + 1
        top_countries = [
            BreakdownItem(name=k, value=v)
            for k, v in sorted(country_counts.items(), key=lambda x: -x[1])[:10]
        ]

        total = len(star_events)
        now = datetime.now(UTC).replace(tzinfo=None)
        last_30 = len([r for r in star_events if r.date >= now - timedelta(days=30)])
        last_7 = len([r for r in star_events if r.date >= now - timedelta(days=7)])

        metrics = [
            MetricCardView(label="Total Stars", value=total),
            MetricCardView(label="Last 30 Days", value=last_30),
            MetricCardView(label="Last 7 Days", value=last_7),
        ]

        events = self._all_events(days=days)
        return StarsView(
            metrics=metrics,
            daily=daily,
            recent_stars=recent_stars,
            top_countries=top_countries,
            events=events,
            event_types=self._event_type_options(events),
        )

    def pypi(self, days: int = 14) -> PyPIView:
        """Build PyPI tab data."""
        bulk = self._bulk
        cutoff, prev_cutoff = InsightQueryService.compute_cutoffs(days)
        daily_dl = bulk.daily.get("downloads_daily", [])
        daily_human = bulk.daily.get("downloads_daily_human", [])

        daily_dl_in_range = [r for r in daily_dl if r.date >= cutoff]
        daily_human_in_range = [r for r in daily_human if r.date >= cutoff]
        daily_dl_prev = [r for r in daily_dl if prev_cutoff <= r.date < cutoff]
        daily_human_prev = [r for r in daily_human if prev_cutoff <= r.date < cutoff]

        days_count = len(daily_dl_in_range) or 1
        total_dl = sum(r.value for r in daily_dl_in_range)
        total_human = sum(r.value for r in daily_human_in_range)
        bot_pct = int((1 - total_human / total_dl) * 100) if total_dl > 0 else 0

        prev_days_count = len(daily_dl_prev) or 1
        prev_total_dl = sum(r.value for r in daily_dl_prev)
        prev_total_human = sum(r.value for r in daily_human_prev)
        prev_bot_pct = (
            int((1 - prev_total_human / prev_total_dl) * 100)
            if prev_total_dl > 0
            else 0
        )

        # Country / installer / dist-type breakdowns — aggregate per-day snapshots
        # within the selected range (same pattern as versions).
        def _aggregate(key: str, schema: Any, attr: str) -> dict[str, int]:
            totals: dict[str, int] = {}
            for r in bulk.daily.get(key, []):
                if r.date < cutoff:
                    continue
                meta = r.metadata_ if hasattr(r, "metadata_") else {}
                if not isinstance(meta, dict):
                    continue
                try:
                    parsed = schema.model_validate(meta)
                except Exception:
                    continue
                for k, v in getattr(parsed, attr).items():
                    totals[k] = totals.get(k, 0) + int(v)
            return totals

        country_counts = _aggregate(
            "downloads_by_country", PyPICountryBreakdown, "countries"
        )
        # `countries` feeds the world map — keep the long tail so small
        # countries still render. `top_countries` is the top-10 slice the
        # side table reads, capped server-side so the template doesn't
        # have to know about limits.
        countries = sorted(
            [
                BreakdownItem(name=self._country_label(k), value=v, code=k)
                for k, v in country_counts.items()
            ],
            key=lambda x: -x.value,
        )[:50]
        top_countries = countries[:10]

        installer_counts = _aggregate(
            "downloads_by_installer", PyPIInstallerBreakdown, "installers"
        )
        installers = sorted(
            [BreakdownItem(name=k, value=v) for k, v in installer_counts.items()],
            key=lambda x: -x.value,
        )[:10]

        type_counts = _aggregate("downloads_by_type", PyPITypeBreakdown, "types")
        dist_types = sorted(
            [BreakdownItem(name=k, value=v) for k, v in type_counts.items()],
            key=lambda x: -x.value,
        )[:10]

        # Version breakdown — aggregate per-day snapshots within the selected range.
        versions: list[BreakdownItem] = []
        version_totals: list[BreakdownItem] = []
        version_rows = bulk.daily.get("downloads_by_version", [])
        if version_rows:
            period_totals: dict[str, int] = {}
            for r in version_rows:
                if r.date < cutoff:
                    continue
                meta = r.metadata_ if hasattr(r, "metadata_") else {}
                if not isinstance(meta, dict):
                    continue
                try:
                    pm = PyPIDownloadMetadata.model_validate(meta)
                except Exception:
                    continue
                for k, v in pm.versions.items():
                    period_totals[k] = period_totals.get(k, 0) + v.total

            all_items = [
                BreakdownItem(name=k, value=v) for k, v in period_totals.items()
            ]
            versions = sorted(all_items, key=lambda x: -x.value)[:10]
            # Full list in semver ascending order for the period bar chart
            version_totals = sorted(all_items, key=lambda x: _semver_tuple(x.name))

        # Per-version daily time series for the secondary chart
        version_dates: list[str] = []
        version_series: list[VersionSeries] = []
        version_rows_in_range = [r for r in version_rows if r.date >= cutoff]
        if version_rows_in_range:
            version_dates = [self._day_str(r.date) for r in version_rows_in_range]
            # Sum per-version totals across the range to pick the top 5
            totals_in_range: dict[str, int] = {}
            parsed_per_day: list[dict[str, int]] = []
            for r in version_rows_in_range:
                meta = r.metadata_ if hasattr(r, "metadata_") else {}
                day_counts: dict[str, int] = {}
                if isinstance(meta, dict):
                    try:
                        pm = PyPIDownloadMetadata.model_validate(meta)
                        for k, v in pm.versions.items():
                            day_counts[k] = v.total
                            totals_in_range[k] = totals_in_range.get(k, 0) + v.total
                    except Exception:
                        pass
                parsed_per_day.append(day_counts)

            # Return up to 10 versions so the user can choose which to chart
            top_versions = [
                v for v, _ in sorted(totals_in_range.items(), key=lambda x: -x[1])[:10]
            ]
            for v in top_versions:
                values = [day.get(v, 0) for day in parsed_per_day]
                version_series.append(VersionSeries(version=v, values=values))

        metrics = [
            MetricCardView(
                label="Downloads",
                value=int(total_dl),
                change_pct=self._pct(total_dl, prev_total_dl),
            ),
            MetricCardView(
                label="Avg / Day",
                value=int(total_dl / days_count),
                change_pct=self._pct(
                    total_dl / days_count,
                    prev_total_dl / prev_days_count,
                ),
            ),
            MetricCardView(
                label="Avg / Week",
                value=int(total_dl / days_count * 7),
                change_pct=self._pct(
                    total_dl / days_count,
                    prev_total_dl / prev_days_count,
                ),
            ),
            MetricCardView(
                label="Avg / Month",
                value=int(total_dl / days_count * 30),
                change_pct=self._pct(
                    total_dl / days_count,
                    prev_total_dl / prev_days_count,
                ),
            ),
            MetricCardView(
                label="Bot %",
                value=f"{bot_pct}%",
                change_pct=self._pct(bot_pct, prev_bot_pct),
                lower_is_better=True,
            ),
        ]

        events = self._filter_events(PYPI_EVENT_TYPES, cutoff=cutoff, days=days)
        return PyPIView(
            metrics=metrics,
            daily=[
                DailyValuePoint(date=self._day_str(r.date), value=int(r.value))
                for r in daily_dl_in_range
            ],
            daily_human=[
                DailyValuePoint(date=self._day_str(r.date), value=int(r.value))
                for r in daily_human_in_range
            ],
            countries=countries,
            top_countries=top_countries,
            installers=installers,
            dist_types=dist_types,
            versions=versions,
            version_totals=version_totals,
            version_series=version_series,
            version_dates=version_dates,
            events=events,
            event_types=self._event_type_options(events),
        )

    def docs(self, days: int = 14) -> DocsView:
        """Build docs/Plausible tab data."""
        bulk = self._bulk
        cutoff, prev_cutoff = InsightQueryService.compute_cutoffs(days)

        def _split(key: str) -> tuple[list[Any], list[Any]]:
            rows = bulk.daily.get(key, [])
            cur = [r for r in rows if r.date >= cutoff]
            prev = [r for r in rows if prev_cutoff <= r.date < cutoff]
            return cur, prev

        visitors, prev_visitors = _split("visitors")
        pageviews, prev_pageviews = _split("pageviews")
        bounce_rows, prev_bounce = _split("bounce_rate")
        duration_rows, prev_duration = _split("avg_duration")

        # Top pages — aggregate per-day snapshots across the selected
        # range. Each row accumulates visitors + pageviews (sums), while
        # time/bounce/scroll are visitor-weighted averages so a low-traffic
        # day can't drag a high-traffic day's number sideways. Plausible
        # only stores the path; the owning site comes from the snapshot
        # metadata so we can build the full click-through URL.
        page_totals: dict[str, dict[str, float]] = {}
        page_site: dict[str, str] = {}
        for r in (r for r in bulk.daily.get("top_pages", []) if r.date >= cutoff):
            meta = r.metadata_ if isinstance(r.metadata_, dict) else {}
            try:
                parsed = PlausibleTopPagesMetadata.model_validate(meta)
            except Exception:
                continue
            for p in parsed.pages:
                entry = page_totals.setdefault(
                    p.url,
                    {
                        "visitors": 0.0,
                        "pageviews": 0.0,
                        # Running weighted sums: value * visitors, divided by
                        # total visitors at the end. Skipped when the field is
                        # None (Plausible didn't report it for that day).
                        "time_w": 0.0,
                        "time_visitors": 0.0,
                        "bounce_w": 0.0,
                        "bounce_visitors": 0.0,
                        "scroll_w": 0.0,
                        "scroll_visitors": 0.0,
                    },
                )
                v = float(p.visitors or 0)
                entry["visitors"] += v
                entry["pageviews"] += float(p.pageviews or 0)
                if p.time_s is not None:
                    entry["time_w"] += p.time_s * v
                    entry["time_visitors"] += v
                if p.bounce_rate is not None:
                    entry["bounce_w"] += p.bounce_rate * v
                    entry["bounce_visitors"] += v
                if p.scroll is not None:
                    entry["scroll_w"] += p.scroll * v
                    entry["scroll_visitors"] += v
                page_site.setdefault(p.url, parsed.site)

        def _weighted(w: float, n: float) -> float | None:
            return (w / n) if n > 0 else None

        all_pages = sorted(
            [
                DocsPageStats(
                    path=path,
                    url=_page_url(page_site.get(path, ""), path),
                    visitors=int(v["visitors"]),
                    pageviews=int(v["pageviews"]),
                    time_s=_weighted(v["time_w"], v["time_visitors"]),
                    bounce_rate=_weighted(v["bounce_w"], v["bounce_visitors"]),
                    scroll=_weighted(v["scroll_w"], v["scroll_visitors"]),
                )
                for path, v in page_totals.items()
            ],
            key=lambda x: -x.visitors,
        )
        # Wire-payload is capped at 10; spotlight cards still see the full
        # list so Most Read can surface a slow-burn page that isn't top-10
        # by visitor count.
        top_pages = all_pages[:10]

        # Top countries — aggregate per-day snapshots across selected range
        country_totals: dict[str, int] = {}
        for r in (r for r in bulk.daily.get("top_countries", []) if r.date >= cutoff):
            meta = r.metadata_ if isinstance(r.metadata_, dict) else {}
            try:
                parsed_countries = PlausibleTopCountriesMetadata.model_validate(
                    meta
                ).countries
            except Exception:
                continue
            for c in parsed_countries:
                country_totals[c.country] = (
                    country_totals.get(c.country, 0) + c.visitors
                )
        # Full country list (with ISO codes) for the world map; top-10 slice
        # for the side table — same shape as the PyPI tab.
        all_countries = [
            BreakdownItem(name=self._country_label(code), value=count, code=code)
            for code, count in sorted(country_totals.items(), key=lambda x: -x[1])
        ]
        top_countries = all_countries[:10]
        countries = all_countries[:50]  # cap the wire payload, matches PyPI

        # Top sources — aggregate per-day snapshots across selected range.
        # Each row's `name` is something like "Direct / None", "Google",
        # "github.com" — _referrer_url() turns hostname-shaped names into
        # click-throughs and skips the others (e.g. "Direct / None").
        source_totals: dict[str, int] = {}
        for r in (r for r in bulk.daily.get("top_sources", []) if r.date >= cutoff):
            meta = r.metadata_ if isinstance(r.metadata_, dict) else {}
            try:
                parsed_sources = PlausibleTopSourcesMetadata.model_validate(
                    meta
                ).sources
            except Exception:
                continue
            for s in parsed_sources:
                source_totals[s.source] = source_totals.get(s.source, 0) + s.visitors
        top_sources = [
            BreakdownItem(name=name, value=count, url=_referrer_url(name))
            for name, count in sorted(source_totals.items(), key=lambda x: -x[1])[:10]
        ]

        def _sum(rows: list[Any]) -> int:
            return int(sum(r.value for r in rows))

        def _avg(rows: list[Any]) -> int:
            return int(sum(r.value for r in rows) / len(rows)) if rows else 0

        total_visitors = _sum(visitors)
        total_pageviews = _sum(pageviews)
        views_per_visit = (
            round(total_pageviews / total_visitors, 1) if total_visitors else 0
        )
        avg_bounce = _avg(bounce_rows)
        avg_duration_s = _avg(duration_rows)
        duration_str = (
            f"{avg_duration_s // 60}m {avg_duration_s % 60}s"
            if avg_duration_s >= 60
            else f"{avg_duration_s}s"
        )

        prev_total_visitors = _sum(prev_visitors)
        prev_total_pageviews = _sum(prev_pageviews)
        prev_views_per_visit = (
            round(prev_total_pageviews / prev_total_visitors, 1)
            if prev_total_visitors
            else 0
        )
        prev_avg_bounce = _avg(prev_bounce)
        prev_avg_duration_s = _avg(prev_duration)

        metrics = [
            MetricCardView(
                label="Visitors",
                value=total_visitors,
                change_pct=self._pct(total_visitors, prev_total_visitors),
            ),
            MetricCardView(
                label="Pageviews",
                value=total_pageviews,
                change_pct=self._pct(total_pageviews, prev_total_pageviews),
            ),
            MetricCardView(
                label="Views/Visit",
                value=views_per_visit,
                change_pct=self._pct(views_per_visit, prev_views_per_visit),
            ),
            MetricCardView(
                label="Bounce Rate",
                value=f"{avg_bounce}%",
                change_pct=self._pct(avg_bounce, prev_avg_bounce),
                lower_is_better=True,
            ),
            MetricCardView(
                label="Avg Duration",
                value=duration_str,
                change_pct=self._pct(avg_duration_s, prev_avg_duration_s),
            ),
        ]

        spotlights = self._docs_spotlights(all_pages, top_countries)

        events = self._all_events(days=days)
        return DocsView(
            metrics=metrics,
            visitors=[
                DailyValuePoint(date=self._day_str(r.date), value=int(r.value))
                for r in visitors
            ],
            pageviews=[
                DailyValuePoint(date=self._day_str(r.date), value=int(r.value))
                for r in pageviews
            ],
            top_pages=top_pages,
            top_countries=top_countries,
            countries=countries,
            top_sources=top_sources,
            spotlights=spotlights,
            events=events,
            event_types=self._event_type_options(events),
        )

    @staticmethod
    def _country_label(code: str) -> str:
        """e.g. 'US' → '🇺🇸 United States'. COUNTRY_NAMES already embeds the flag;
        we just fall back to the raw code when unknown."""
        from app.core.constants import COUNTRY_NAMES

        return COUNTRY_NAMES.get(code.upper(), code) if code else code

    @staticmethod
    def _page_title(url: str) -> str:
        parts = [p for p in url.strip("/").split("/") if p]
        return parts[-1].replace("-", " ").title() if parts else "Home"

    def _docs_spotlights(
        self,
        pages: list[DocsPageStats],
        countries: list[BreakdownItem],
    ) -> list[SpotlightCard]:
        """Build Most Read / Most Visited / Top Country spotlight cards.

        `pages` is the already-aggregated DocsPageStats list so we don't
        re-walk the raw Plausible metadata here.
        """
        spotlights: list[SpotlightCard] = []
        content_pages = [p for p in pages if len(p.path.strip("/").split("/")) >= 2]
        read_pages = sorted(
            [p for p in content_pages if (p.time_s or 0) > 0],
            key=lambda p: -(p.time_s or 0),
        )
        by_visitors = sorted(content_pages, key=lambda p: -p.visitors)

        most_read_path = ""
        if read_pages:
            mr = read_pages[0]
            mr_time = int(mr.time_s or 0)
            most_read_path = mr.path
            spotlights.append(
                SpotlightCard(
                    label="Most Read",
                    value=self._page_title(mr.path),
                    sublabel=f"{mr_time // 60}m {mr_time % 60}s read time",
                    tooltip=mr.path,
                )
            )

        if by_visitors and by_visitors[0].path != most_read_path:
            tv = by_visitors[0]
            spotlights.append(
                SpotlightCard(
                    label="Most Visited",
                    value=self._page_title(tv.path),
                    sublabel=f"{tv.visitors} visitors",
                    tooltip=tv.path,
                )
            )

        if countries:
            top = countries[0]
            spotlights.append(
                SpotlightCard(
                    label="Top Country",
                    value=top.name,
                    sublabel=f"{top.value} visitors",
                )
            )

        if len(countries) >= 2:
            spotlights.append(
                SpotlightCard(
                    label="Top Countries",
                    items=countries[:3],
                )
            )

        return spotlights

    def reddit(self, days: int = 14) -> RedditView:
        """Build Reddit tab data.

        Pulls from `insight_metric` rows with period=EVENT for the post_stats
        metric type (the collector stores full post metadata there; the
        `insight_events` timeline row is a thin link-only pointer). The
        metric row's `value` column holds the latest upvote count.

        Honors the `days` range so the post list filters in lockstep with
        the rest of the dashboard — the range picker on /app/reddit used
        to be inert.
        """
        cutoff, _ = InsightQueryService.compute_cutoffs(days)
        post_metrics = sorted(
            (m for m in self._bulk.events.get("post_stats", []) if m.date >= cutoff),
            key=lambda m: m.date,
            reverse=True,
        )

        posts: list[RedditPostView] = []
        for row in post_metrics[:20]:
            meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
            subreddit = meta.get("subreddit", "")
            title = meta.get("title", "")
            hourly = meta.get("hourly_views_48h") or []
            peak_hour: int | None = None
            if hourly:
                # argmax + 1 so the UI can say "Peak: hour 2" (1-indexed,
                # matches how Reddit's own analytics labels the buckets).
                peak_hour = max(range(len(hourly)), key=lambda i: hourly[i]) + 1
            # Route known ISO codes through `_country_label` so each row
            # renders with the flag emoji (e.g. "🇺🇸 United States") — same
            # treatment the Docs tab uses. "OTHER" / empty code rows keep
            # their raw name (no flag for the catch-all bucket).
            raw_countries = meta.get("top_countries") or []
            decorated_countries = [
                {
                    **c,
                    "name": self._country_label(c["code"])
                    if c.get("code") and c["code"].upper() != "OTHER"
                    else c.get("name", ""),
                }
                for c in raw_countries
                if isinstance(c, dict)
            ]
            posts.append(
                RedditPostView(
                    description=f"r/{subreddit} \u2014 {title[:80]}"
                    if subreddit
                    else title,
                    title=title,
                    date=self._day_str(row.date),
                    subreddit=subreddit,
                    upvotes=int(row.value) if row.value is not None else 0,
                    comments=meta.get("comments", 0) or 0,
                    upvote_ratio=meta.get("upvote_ratio"),
                    views=meta.get("views"),
                    shares=meta.get("shares"),
                    url=meta.get("url", ""),
                    top_countries=decorated_countries,
                    hourly_views_48h=hourly,
                    peak_hour=peak_hour,
                    top_comments=meta.get("top_comments") or [],
                )
            )

        return RedditView(total=len(post_metrics), posts=posts)
