# Overseer Dashboard

The Insights service integrates with the Overseer dashboard as an interactive modal with 7 tabs.

## Overview Tab

![Insights Overview](../../images/insights_dashboard.png)

The landing tab shows a high-level summary with metric cards, a recent activity feed, and a key milestones grid.

Metric cards show period-over-period change arrows comparing the current 14-day window against the previous 14 days. The milestones grid shows the all-time record for each tracked category - only the highest value per category is displayed.

The activity feed uses the same expandable row pattern as the main Overseer activity panel. Expanding a release shows a link to the GitHub release page. Expanding a Reddit post shows upvotes, comments, and a link to the post.

## GitHub Tab

Interactive GitHub Traffic with full clone/view history going back as far as data has been collected.

![GitHub Clones](../../images/insights_clones.png)

### Features

- Date range selection (7d, 14d, 1m, 3m, 6m, 1y, All)
- Clones + Unique Cloners line chart with release annotation tooltips
- Views + Unique Visitors line chart
- Activity Summary stacked bar chart (Code, Issues, PRs, Community, Releases)
- Clickable referrers and popular paths (links to GitHub)
- Event chips with date highlighting - click a chip to highlight the data point on the chart

## Stars Tab

Cumulative star history chart showing growth over time.

![Star History](../../images/insights_stars.png)

- One data point per day that had star activity (no gap filling)
- Tooltips show star numbers and usernames
- Dynamic Y-axis scaling at zoomed ranges
- Event chips filtered to only show events on dates with star activity

## PyPI Tab

Download analytics with human vs bot separation.

![PyPI Downloads](../../images/insights_downloads.png)

### Features

- **CI/Mirror toggle** - Switch between total downloads (including bots) and human-only (pip + uv)
- Stacked area chart showing bot vs human split when CI toggle is on
- Version breakdown bar chart
- Side-by-side tables: Downloads by Version and Daily Downloads (scrollable)
- Period-over-period arrows on the Total Downloads card

## Docs Tab (Plausible)

Documentation site analytics from Plausible.

![Docs Analytics](../../images/insights_docs.png)

### Features

- Visitors + Pageviews dual-series line chart
- Country breakdown bar chart (range-aware - updates with date selection)
- Top Pages table with clickable links to your documentation site
- Bounce rate with inverted arrow (green when it decreases)

## Reddit Tab

Tracked Reddit post performance. Each post shows subreddit, title, upvotes, comments, upvote ratio, and a clickable link.

Posts are added on-demand via the CLI:

```bash
my-app insights reddit add https://reddit.com/r/FastAPI/comments/abc123/your-post
```

## Settings Tab

Data source status and configuration. Shows each source with Active/Stale/Disabled status and last collection timestamp.

## Shared Controls

All interactive tabs share a common base:

- **Date range chips** - 7d, 14d, 1m, 3m, 6m, 1y, All
- **Events toggle** - Show/hide event annotation chips
- **Event grouping** - At wider ranges, same-type events are grouped (weekly at 3m, monthly at 6m+)
- **Date highlighting** - Click an event chip to highlight all chart points in that date range
- **Last updated** - Shows the most recent data point date
