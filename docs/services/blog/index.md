# Blog Service

First-party Markdown publishing with database-backed posts, tags, drafts, and the Overseer editor UI.

!!! warning "Experimental Service"
    Blog is currently experimental. The data model, API surface, and editor UI are functional and covered by tests, but expect refinements before the first stable release.

!!! info "Quick Start"
    Generate a project with the blog service:

    ```bash
    aegis init my-site --services blog
    cd my-site
    uv sync
    make serve
    ```

    The blog service requires the `database` component. Interactive generation adds it automatically when needed.

## What You Get

- **Public read API** - list published posts and fetch by slug, with optional tag filtering
- **Editor API** - create, update, publish, archive, and delete posts
- **Tag management** - create, rename, and delete reusable tags; deleting a tag cleans up its join-table rows automatically
- **Draft workflow** - posts move through `draft`, `published`, and `archived` states
- **Overseer editor** - four-tab modal (Overview, Posts, Tags, Editor) with Markdown preview, tag picker, status-aware actions, and snackbar feedback
- **Export / Import** - one-command portability via Markdown + YAML frontmatter (the same format Hugo, Jekyll, and Astro use). Move posts between Aegis projects, take human-readable backups, or import a foreign blog with `my-app blog import ./posts/` ([details](cli.md#export-and-import))
- **Health metadata** - post counts, tag count, latest published post title, and stale-draft detection

## Data Model

| Table | Key Columns |
|-------|-------------|
| `blog_post` | `id`, `title`, `slug` (unique), `excerpt`, `content` (text), `status`, `author_id`, `author_name`, `created_at`, `updated_at`, `published_at`, `seo_title`, `seo_description`, `hero_image_url` |
| `blog_tag` | `id`, `name` (unique), `slug` (unique) |
| `blog_post_tag` | `post_id`, `tag_id` — composite primary key, many-to-many join |

Statuses are enforced by a database check constraint: `draft`, `published`, `archived`.

## Post Lifecycle

```
draft --> published --> archived
            |              |
            +----<---------+   (re-publishing returns to published)
```

- A post always starts as `draft`.
- `published_at` is set once on first publish and never overwritten.
- Editing a post does not change its status. Use `archive_post` to take a published post offline.
- Archiving does not delete content; the post can be re-published.
- Slug auto-derives from title on drafts. Once a post leaves `draft` status the slug is locked and must be changed explicitly.

## Authentication

Write endpoints are protected based on which auth variant was generated into the project:

| Auth level | Who can write |
|------------|---------------|
| RBAC | `admin` or `moderator` role |
| Basic auth | any active user |
| No auth | unprotected (local-first / internal use) |

Public read endpoints (`GET /posts`, `GET /posts/{slug}`) are always open.

## Health Status

`check_blog_service_health()` maps the current state to one of four status types:

| State | Status | Message |
|-------|--------|---------|
| No posts | info | "No posts yet" |
| Posts, no stale drafts | healthy | "N published, M drafts" |
| Stale drafts present | warning | "N published, M drafts; X stale drafts" |
| DB error | unhealthy | error detail |

A draft is considered stale after 30 days without an update (`STALE_DRAFT_DAYS = 30`).

## Next Steps

| Topic | Description |
|-------|-------------|
| **[API Reference](api.md)** | Full route table with schemas and curl examples |
| **[Dashboard](dashboard.md)** | Overseer editor walkthrough |
| **[CLI Commands](cli.md)** | CLI availability |
| **[Examples](examples.md)** | Common workflows end to end |

---

**Related:**

- **[Services Overview](../index.md)** - Complete services architecture
- **[Database Component](../../components/database.md)** - Database component details
- **[CLI Reference](../../cli-reference.md)** - Generated project CLI overview
