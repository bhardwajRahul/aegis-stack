# CLI Commands

**Part of the Generated Project CLI** - See [CLI Reference](../../cli-reference.md#service-clis) for complete overview.

The blog service registers a `blog` command group on the generated project CLI. Use it to inspect posts, transition post state (publish, archive, delete), and manage tags from scripts.

Authoring (writing post bodies in markdown) stays in the dashboard editor. The CLI intentionally has no `post-create` or `post-update` command, since multi-line markdown editing in a terminal is a worse experience than the editor already provides.

## Quick Reference

| Command | Description |
|---------|-------------|
| `blog status` | Show counts (drafts, published, archived) and latest activity |
| `blog posts` | List posts with optional `--status`, `--tag`, `--limit` filters |
| `blog post <slug>` | Show one post's metadata (not the full body) |
| `blog tags` | List all tags |
| `blog publish <slug>` | Move a post to published |
| `blog archive <slug>` | Hide a post from the public site |
| `blog delete <slug> --yes` | Permanently delete a post and its tag links |
| `blog tag-create <name>` | Create a tag (slug auto-generated unless `--slug` given) |
| `blog tag-update <slug>` | Rename a tag (`--name`) or change its slug (`--new-slug`) |
| `blog tag-delete <slug> --yes` | Delete a tag and remove it from all posts |

Run `my-app blog --help` or `my-app blog <command> --help` to see usage examples inline.

## Read Commands

### `blog status`

Counts of posts by status, tag total, stale draft count, and the latest published post.

```bash
my-app blog status
```

### `blog posts`

```bash
my-app blog posts
my-app blog posts --status draft
my-app blog posts --tag release-notes --limit 50
```

Options:

- `--status, -s` - Filter by `draft`, `published`, or `archived`
- `--tag, -t` - Filter by tag slug
- `--limit, -n` - Number of rows to show (default 20, max 100)

### `blog post <slug>`

Shows id, slug, status, author, tag slugs, timestamps, and excerpt for one post. The full markdown body is not printed; use the dashboard editor.

```bash
my-app blog post my-first-post
```

### `blog tags`

```bash
my-app blog tags
```

## Post State Transitions

These commands look up a post by slug and call the matching service operation. They are safe to run in scripts.

```bash
my-app blog publish my-first-post
my-app blog archive obsolete-post
my-app blog delete obsolete-post --yes
```

`blog delete` prompts for confirmation unless `--yes` (`-y`) is passed.

## Tag CRUD

```bash
my-app blog tag-create "Release Notes"
my-app blog tag-create "Release Notes" --slug releases

my-app blog tag-update releases --name "Product Releases"
my-app blog tag-update releases --new-slug release-notes

my-app blog tag-delete obsolete --yes
```

`tag-update` requires at least one of `--name` or `--new-slug`.

`tag-delete` removes the tag from all posts as well as deleting the tag itself.

## Export and Import

Posts are stored as plain markdown files with YAML frontmatter, the same format Hugo, Jekyll, and Astro use. Export produces files you can edit in any text editor or commit to a git repo. Import accepts the same format, plus zip archives and JSON dumps.

### `blog export <path>`

```bash
my-app blog export ./out                          # one .md per post into ./out
my-app blog export ./out --status published      # filter by status
my-app blog export blog.json --format json       # single JSON file (full fidelity)
```

Options:

- `--format, -f` - `markdown` (default, one file per post) or `json` (single file with all metadata)
- `--status, -s` - Only export posts in this status

A markdown file looks like:

```markdown
---
title: My Post
slug: my-post
status: published
tags: [release-notes]
published_at: 2026-05-01T12:00:00Z
---

# Body content

Full post body in markdown.
```

### `blog import <path>`

```bash
my-app blog import ./posts                        # directory of .md files
my-app blog import ./post.md                      # single markdown file
my-app blog import backup.zip                     # zip archive of .md files
my-app blog import blog.json                      # JSON document
my-app blog import ./posts --on-conflict overwrite
```

Options:

- `--on-conflict` - `skip` (default), `overwrite`, or `fail`
  - `skip` - existing slugs are left untouched
  - `overwrite` - existing posts are updated with imported data
  - `fail` - the entire batch is rolled back on the first slug collision

The importer is **lenient on frontmatter fields**, so foreign blogs work out of the box:

| Aegis field | Also accepts |
|-------------|--------------|
| `published_at` | `date`, `publishDate`, `pubDate` |
| `seo_description` | `description` |
| `hero_image_url` | `image`, `cover`, `coverImage` |
| `status` | `draft: true/false` (Hugo/Jekyll convention) |
| `tags` | comma-separated string or YAML list |

Filenames like `2024-01-15-my-post.md` (Jekyll convention) have the date prefix stripped to derive the slug.

#### What does NOT transfer

- **Hugo shortcodes** (`{{< youtube >}}`) and **Jekyll Liquid tags** (`{% include %}`) render as literal text. Aegis only parses standard markdown.
- **Image asset paths** (e.g. `/images/cover.jpg`) survive as URLs but the actual image files are not bundled. Re-upload them in the dashboard.
- **TOML frontmatter** (`+++` fences, supported by Hugo) is not parsed in v1. Convert to YAML first.
- **Categories** beyond `tags`, custom collections, and SSG-specific layout fields are silently dropped.

#### Round-tripping between Aegis projects

```bash
# On the source project
source-app blog export ./blog-backup

# Move the directory to the target project, then
target-app blog import ./blog-backup --on-conflict overwrite
```

JSON format gives perfect fidelity (all timestamps, SEO fields, etc.); markdown format is human-readable and survives manual editing.

## Exit Codes

- `0` - Success (or user cancelled at a confirmation prompt)
- `1` - Post or tag not found, or service raised a validation error
- `2` - Invalid invocation (e.g. `tag-update` with no fields to change)

---

**See also:**

- **[CLI Reference](../../cli-reference.md)** - Complete CLI overview
- **[API Reference](api.md)** - All blog endpoints
- **[Examples](examples.md)** - End-to-end workflow examples
