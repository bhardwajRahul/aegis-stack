# Examples

Real-world patterns for using the Insights service effectively.

## Initial Setup and Backfill

After creating a project with Insights, backfill historical data before starting scheduled collection:

```bash
# 1. Configure .env with API keys
# 2. Run initial collection for all sources
my-app insights collect

# 3. Backfill PyPI (goes back to package creation)
my-app insights collect pypi --lookback-days 365

# 4. Backfill Plausible (goes back to site creation)
my-app insights collect plausible --lookback-days 365

# 5. GitHub Traffic only has 14 days - collect immediately, then keep the scheduler running
# 6. GitHub Stars and Events backfill automatically on first collection
```

## Understanding the Bot vs Human Split

PyPI download numbers are dominated by automated traffic. Here's how to interpret them:

```
Total PyPI Downloads: 16,485
Human Downloads (pip + uv): 462
Bot/Mirror Traffic: 97%
```

The 462 is your real adoption number. The 16,485 is useful for public comparison (everyone's numbers are equally inflated) but not for internal decision-making.

### What the installers mean

- **pip + uv** - Real humans installing your package
- **bandersnatch** - PyPI mirror operators syncing everything. Some corporate mirrors sync on-demand (triggered by real users), so not all bandersnatch traffic is noise
- **Browser** - Security scanners downloading source to audit. Uniform download pattern across all versions confirms automated behavior
- **requests** - Scripts and CI/CD pipelines
- **(empty)** - No user agent, fully automated

### The version chart signal

If bots were blindly mirroring, every version would have equal downloads. An upward slope toward newer versions indicates demand-driven traffic - real users (or their corporate proxies) pulling the latest release.

## Tracking Reddit Post Impact

```bash
# Add a post after publishing
my-app insights reddit add https://reddit.com/r/FastAPI/comments/abc123/my-post

# Run collection to see impact on other metrics
my-app insights collect github_traffic
my-app insights collect pypi
```

The Reddit post appears as an event chip on all tabs, letting you correlate the post timing with traffic spikes.

## Event Correlation

The event system lets you see what drove metric changes. Events show up as:

- **Chips above charts** - Clickable, highlight the data point on that date
- **Chart annotation tooltips** - Hover over a data point to see events on that day
- **Activity feed on Overview** - Chronological feed with expandable details

### Manual events for context

```bash
# Log a feature launch
my-app insights event feature "Added Mandarin CLI localization"

# Log an external mention
my-app insights event external "Featured in Python Weekly #523"

# Log an anomaly
my-app insights event anomaly_github "CI/CD spike - 44:1 clone ratio"
```

## Record Tracking

Records are detected automatically after each collection. When a new all-time high is set for any tracked metric, the system:

1. Creates an `InsightEvent` with the record value and category
2. Reports it in the CLI output
3. Shows it in the Overview milestones grid

### What's tracked

- GitHub 1-Day Clones, Unique, Views, Visitors
- GitHub 14-Day Clones, Unique
- PyPI Best Single Day
- Plausible 1-Day Visitors, Pageviews

### Milestone cards on Overview

The Overview tab shows the latest record per category as trophy-style cards with the hero number prominently displayed. Only the all-time high per category shows - superseded records are kept in the database but don't display.

## Geographic Analysis

Stars carry location metadata (self-reported GitHub profiles). Plausible provides country-level visitor data. Together they reveal organic geographic spread without any marketing effort.

The Plausible country data is range-aware - switching date ranges in the Docs tab updates both the chart and the country breakdown.
