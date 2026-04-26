"""
Constants for the insights service.

Single source of truth for source keys, metric type keys, and period values.
"""


class SourceKeys:
    """Insight source identifiers. Must match seed data in insight_source table."""

    GITHUB_TRAFFIC = "github_traffic"
    GITHUB_STARS = "github_stars"
    GITHUB_EVENTS = "github_events"
    PYPI = "pypi"
    PLAUSIBLE = "plausible"
    REDDIT = "reddit"

    ALL = [GITHUB_TRAFFIC, GITHUB_STARS, GITHUB_EVENTS, PYPI, PLAUSIBLE, REDDIT]


class MetricKeys:
    """Metric type identifiers. Must match seed data in insight_metric_type table."""

    # github_traffic
    CLONES = "clones"
    UNIQUE_CLONERS = "unique_cloners"
    VIEWS = "views"
    UNIQUE_VISITORS = "unique_visitors"
    REFERRERS = "referrers"
    POPULAR_PATHS = "popular_paths"

    # github_stars
    NEW_STAR = "new_star"

    # pypi
    DOWNLOADS_TOTAL = "downloads_total"
    DOWNLOADS_DAILY = "downloads_daily"
    DOWNLOADS_DAILY_HUMAN = "downloads_daily_human"
    DOWNLOADS_BY_COUNTRY = "downloads_by_country"
    DOWNLOADS_BY_INSTALLER = "downloads_by_installer"
    DOWNLOADS_BY_VERSION = "downloads_by_version"
    DOWNLOADS_BY_TYPE = "downloads_by_type"

    # github_events
    FORKS = "forks"
    RELEASES = "releases"
    STAR_EVENTS = "star_events"
    ACTIVITY_SUMMARY = "activity_summary"

    # plausible
    VISITORS = "visitors"
    PAGEVIEWS = "pageviews"
    AVG_DURATION = "avg_duration"
    BOUNCE_RATE = "bounce_rate"
    TOP_PAGES = "top_pages"
    TOP_COUNTRIES = "top_countries"

    # reddit
    POST_STATS = "post_stats"


class Periods:
    """Time period classifications for metric rows."""

    DAILY = "daily"
    CUMULATIVE = "cumulative"
    SNAPSHOT = "snapshot"
    EVENT = "event"


class Units:
    """Metric type units. Used in seed data and display formatting."""

    COUNT = "count"
    SECONDS = "seconds"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    JSON = "json"


# Component name for health check registration
INSIGHT_COMPONENT_NAME = "insights"
