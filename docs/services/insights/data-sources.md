# Data Sources

Insights collects from 6 data sources across 4 external APIs. Each source has a dedicated collector that handles authentication, rate limiting, and data normalization.

## GitHub Traffic

**Source key:** `github_traffic`
**API:** GitHub REST API v3
**Requires:** `INSIGHT_GITHUB_TOKEN` (personal access token with `repo` scope)
**Default interval:** Every 6 hours

Collects the 14-day rolling traffic data from GitHub's Traffic API.

### Metrics collected

| Metric | Period | Description |
|--------|--------|-------------|
| clones | Daily | Total git clones per day |
| unique_cloners | Daily | Unique cloners per day |
| views | Daily | Repository page views per day |
| unique_visitors | Daily | Unique visitors per day |
| referrers | Snapshot | Top referral sources (Google, Reddit, etc.) |
| popular_paths | Snapshot | Most visited repo pages |

### Important notes

- GitHub only retains 14 days of traffic data. The collector preserves it permanently.
- **Run the collector at least once every 14 days** or you'll lose data that rolls off the window.
- Daily unique cloners overcount across multi-day ranges (a user who clones Monday and Tuesday counts as 1 in GitHub's 14-day window but 2 in summed daily counts).
- Clones are not deduplicated - every `git clone` counts, even from the same person.

## GitHub Stars

**Source key:** `github_stars`
**API:** GitHub REST API v3 (Stargazers endpoint)
**Requires:** `INSIGHT_GITHUB_TOKEN`
**Default interval:** Every 24 hours

Fetches all stargazers with their full GitHub profiles.

### Metrics collected

| Metric | Period | Description |
|--------|--------|-------------|
| new_star | Event | One row per star with user profile metadata |

### Star profile metadata

Each star event stores: username, name, location, company, bio, email, blog, followers, following, public repos, stars given, account age, GitHub Pro status.

### Star events

The collector automatically creates `InsightEvent` entries grouped by day:

- Single star days: `#99 - ncthuc`
- Multi-star days: `#80-#85 (6 stars)`

## GitHub Events (ClickHouse)

**Source key:** `github_events`
**API:** ClickHouse public SQL endpoint (`sql-clickhouse.clickhouse.com`)
**Requires:** No authentication
**Default interval:** Every 24 hours

Queries the public GitHub events dataset for repository-specific activity.

### Metrics collected

| Metric | Period | Description |
|--------|--------|-------------|
| forks | Event | Individual fork events with actor name (from GitHub API for complete list, ClickHouse as fallback) |
| releases | Event | Release events with tag, name, actor |
| star_events | Daily | Daily star count from ClickHouse (separate from API stars) |
| activity_summary | Daily | Breakdown by event type (push, issues, PRs, etc.) |

### Activity summary fields

`push`, `issues`, `pull_requests`, `pull_request_reviews`, `issue_comments`, `forks`, `stars`, `releases`, `creates`, `deletes`

## PyPI Downloads

**Source key:** `pypi`
**API:** ClickHouse public SQL endpoint (PyPI dataset)
**Requires:** `INSIGHT_PYPI_PACKAGE` (package name)
**Default interval:** Every 24 hours

Queries PyPI download data from the public ClickHouse mirror of BigQuery's `pypi.file_downloads` table.

### Metrics collected

| Metric | Period | Description |
|--------|--------|-------------|
| downloads_total | Cumulative | All-time total downloads |
| downloads_daily | Daily | Total downloads per day |
| downloads_daily_human | Daily | Human-only downloads (pip + uv) |
| downloads_by_version | Daily | Per-version breakdown with human/bot split |
| downloads_by_country | Daily | Country breakdown |
| downloads_by_installer | Daily | Installer breakdown (pip, uv, bandersnatch, etc.) |
| downloads_by_type | Daily | Distribution type (sdist, bdist_wheel) |

### Human vs Bot Classification

Downloads are classified by installer:

| Installer | Classification | Why |
|-----------|---------------|-----|
| pip | Human | Direct user install |
| uv | Human | Direct user install |
| bandersnatch | Bot | PyPI mirror sync |
| Browser | Bot | Security scanners (uniform download pattern) |
| requests | Bot | Scripts and automation |
| (empty) | Bot | No user agent = automated |
| Nexus | Bot | Sonatype corporate proxy |
| devpi | Bot | PyPI cache server |
| OS | Bot | OS package manager |

Typically ~97% of downloads are bots. The human count (pip + uv only) is the real adoption signal.

!!! example "Musings: On Download Classification (April 12th, 2026)"
    Honestly, I'm still trying to sort out these downloads. Hell, it's the reason why I built this service. I am currently taking a pretty conservative stance on what is and isn't a bot. I know the real number is most likely larger, I just need more information before I can put a new category in here, something like "behind mirror but human triggered", or something like that. The version distribution chart helps though. Newer versions getting pulled way more than old ones tells me there's real demand behind some of this "bot" traffic. More to come.

### Backfill support

```bash
my-app insights collect pypi --lookback-days 365
```

ClickHouse retains PyPI data for the full history. Backfill once and daily collection maintains it.

## Plausible Analytics

**Source key:** `plausible`
**API:** Plausible API v1
**Requires:** `INSIGHT_PLAUSIBLE_API_KEY`, `INSIGHT_PLAUSIBLE_SITES`
**Default interval:** Every 1 hour

Collects documentation site visitor metrics.

### Metrics collected

| Metric | Period | Description |
|--------|--------|-------------|
| visitors | Daily | Unique visitors per day |
| pageviews | Daily | Total page views per day |
| avg_duration | Daily | Average visit duration (seconds) |
| bounce_rate | Daily | Bounce rate percentage |
| top_pages | Daily | Per-page visitor and duration breakdown |
| top_countries | Daily | Per-country visitor breakdown |

### Backfill support

```bash
my-app insights collect plausible --lookback-days 365
```

Per-day country and page breakdowns are stored for each active day, enabling range-aware filtering in the dashboard.

## Reddit Posts

**Source key:** `reddit`
**API:** Reddit JSON API (append `.json` to any post URL)
**Requires:** No authentication
**Collection:** On-demand only (not scheduled)

Tracks Reddit post performance over time.

### Metrics collected

| Metric | Period | Description |
|--------|--------|-------------|
| post_stats | Event | Upvotes, comments, upvote ratio per post |

### Adding a post

```bash
my-app insights reddit add https://reddit.com/r/FastAPI/comments/abc123/your-post
```

The collector fetches current stats and creates an `InsightEvent` for the timeline.

## Data Storage

All metrics use a single generic table (`insight_metric`) with JSONB metadata. This means:

- **No migrations** when data shapes change
- **Flexible metadata** per metric type
- **Consistent querying** across all sources
- **One upsert pattern** for all collectors

```
insight_metric:
  id, date, metric_type_id, value, period, metadata, created_at

insight_metric_type:
  id, key, display_name, unit, source_id

insight_source:
  id, key, display_name, collection_interval_hours, enabled, last_collected_at
```
