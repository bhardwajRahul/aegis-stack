# CLI Commands

The Insights CLI provides commands for data collection, status monitoring, and manual event management.

## collect

Run data collection for one or all enabled sources.

```bash
# Collect all enabled sources
my-app insights collect

# Collect a specific source
my-app insights collect github_traffic
my-app insights collect pypi
my-app insights collect plausible

# Backfill historical data (PyPI and Plausible support this)
my-app insights collect pypi --lookback-days 365
my-app insights collect plausible --lookback-days 365
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--lookback-days` | `-d` | 1 | Number of days to fetch. Higher values for backfill. |

### Output

```
Collecting from all enabled sources...
  github_traffic: 6 written, 52 skipped
  github_stars: 0 written, 99 skipped
  pypi: 7 written, 78 skipped
    Records broken: PyPI Best Single Day: 850 (was 334)
  plausible: 4 written, 0 skipped
  reddit: 0 written, 0 skipped
  github_events: 2 written, 24 skipped
```

When a new all-time record is detected, it's reported in the output and automatically created as a milestone event.

## status

Display current collection status across all sources.

```bash
my-app insights status
```

### Output

```
Insights Status

                               Sources
+-----------------------+----------+----------------------+-----------+
| Source                | Enabled  | Last Collected       |   Metrics |
+-----------------------+----------+----------------------+-----------+
| GitHub Traffic        | Yes      | 2026-04-11 12:02:58  |         6 |
| GitHub Stars          | Yes      | 2026-04-11 09:05:30  |         1 |
| PyPI                  | Yes      | 2026-04-11 12:02:59  |         7 |
| Plausible             | Yes      | 2026-04-11 12:05:32  |         6 |
| Reddit                | Yes      | 2026-04-11 09:05:32  |         1 |
| GitHub Events         | Yes      | 2026-04-11 09:05:34  |         4 |
+-----------------------+----------+----------------------+-----------+
```

## stars

Display top stargazers with profile metadata.

```bash
# Show latest 10 stars
my-app insights stars

# Show more
my-app insights stars -n 20
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `-n` / `--limit` | `-n` | 10 | Number of stars to display |

## records

Display all-time records for each metric type.

```bash
my-app insights records
```

## sources

List all configured insight sources and their collection intervals.

```bash
my-app insights sources
```

## reddit add

Add a Reddit post for tracking.

```bash
my-app insights reddit add https://reddit.com/r/FastAPI/comments/abc123/your-post
```

The command fetches the post's current stats (upvotes, comments, subreddit, title) and creates both a metric row and a timeline event.

## event

Log a manual event for the timeline.

```bash
# Basic event (today's date)
my-app insights event feature "Added Japanese localization"

# Backdated event
my-app insights event external "Featured in Python Weekly" --date 2026-03-15

# Milestone with category (for record tracking on Overview)
my-app insights event milestone_github "900 clones" --date 2026-04-15 --category daily_clones

# Feature launch
my-app insights event feature "Traefik + Deploy shipped (v0.6.0)" --date 2026-02-09
```

### Options

| Option | Description |
|--------|-------------|
| `--date` | Event date in YYYY-MM-DD format. Defaults to today. |
| `--category` | Milestone category for record deduplication (e.g., `daily_clones`, `pypi_daily`). Used by the Overview milestones grid to show only the latest record per category. |

### Event types

| Type | Color | Description |
|------|-------|-------------|
| `release` | Green | Version releases (auto-detected) |
| `star` | Amber | Star events (auto-detected) |
| `reddit_post` | Orange | Reddit posts (via `reddit add`) |
| `feature` | Cyan | Feature launches |
| `milestone_github` | Pink | GitHub metric records (auto-detected) |
| `milestone_pypi` | Pink | PyPI metric records (auto-detected) |
| `anomaly_github` | Red | Data anomalies |
| `localization` | Blue | Localization events |
| `external` | Gray | External events |
