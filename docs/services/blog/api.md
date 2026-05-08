# API Reference

Complete reference for all blog API endpoints. All routes are mounted under:

```
http://localhost:8000/api/v1/blog/
```

---

## Authentication

| Auth level generated | Public reads | Write endpoints |
|----------------------|:---:|:---:|
| RBAC | open | `admin` or `moderator` |
| Basic auth | open | any active user |
| No auth | open | unprotected |

Pass a Bearer token for protected endpoints:

```bash
# Login first (basic or RBAC auth)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin@example.com&password=Admin1234!" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

---

## Public Endpoints

### GET /blog/posts

List published posts. Returns a paginated response.

**Auth:** None

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `integer` | `1` | Page number (1-based) |
| `page_size` | `integer` | `20` | Results per page, max 100 |
| `tag` | `string` | - | Filter by tag slug |

**Response: `200 OK`** — `BlogPostListResponse`

| Field | Type |
|-------|------|
| `posts` | `list[BlogPostResponse]` |
| `total` | `integer` |
| `page` | `integer` |
| `page_size` | `integer` |

**`BlogPostResponse` fields:**

| Field | Type |
|-------|------|
| `id` | `integer` |
| `title` | `string` |
| `slug` | `string` |
| `excerpt` | `string \| null` |
| `content` | `string` |
| `status` | `string` — `draft`, `published`, or `archived` |
| `author_id` | `integer \| null` |
| `author_name` | `string \| null` |
| `created_at` | `datetime` |
| `updated_at` | `datetime` |
| `published_at` | `datetime \| null` |
| `seo_title` | `string \| null` |
| `seo_description` | `string \| null` |
| `hero_image_url` | `string \| null` |
| `tags` | `list[BlogTagResponse]` |

```bash
# List published posts
curl http://localhost:8000/api/v1/blog/posts

# Filter by tag
curl "http://localhost:8000/api/v1/blog/posts?tag=python&page=1&page_size=10"
```

---

### GET /blog/posts/{slug}

Fetch a single published post by URL slug. Returns `404` if the post does not exist or is not published.

**Auth:** None

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `slug` | `string` | Post slug |

**Response: `200 OK`** — `BlogPostResponse`

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Post found and published |
| `404` | Post not found or not published |

```bash
curl http://localhost:8000/api/v1/blog/posts/my-first-post
```

---

## Editor Endpoints

### GET /blog/admin/posts

List all posts including drafts and archived, for editors.

**Auth:** Protected (see auth table above)

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `integer` | `1` | Page number |
| `page_size` | `integer` | `20` | Results per page, max 100 |
| `status` | `string` | - | Filter: `draft`, `published`, `archived` |
| `tag` | `string` | - | Filter by tag slug |

**Response: `200 OK`** — `BlogPostListResponse`

```bash
curl http://localhost:8000/api/v1/blog/admin/posts \
  -H "Authorization: Bearer $TOKEN"

# Drafts only
curl "http://localhost:8000/api/v1/blog/admin/posts?status=draft" \
  -H "Authorization: Bearer $TOKEN"
```

---

### POST /blog/posts

Create a draft post. The slug is derived from the title if omitted. Returns `409` if the slug already exists.

**Auth:** Protected

**Request body:** `BlogPostCreate`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | `string` | Yes | max 200 chars |
| `slug` | `string` | No | auto-derived from title if omitted; max 220 chars |
| `content` | `string` | No | Markdown; default `""` |
| `excerpt` | `string` | No | max 500 chars |
| `tag_slugs` | `list[string]` | No | list of existing tag slugs to attach |
| `seo_title` | `string` | No | max 200 chars |
| `seo_description` | `string` | No | max 320 chars |
| `hero_image_url` | `string` | No | max 1024 chars |

**Response: `201 Created`** — `BlogPostResponse`

**Status codes:**

| Code | Condition |
|------|-----------|
| `201` | Draft created |
| `409` | Slug already taken |
| `422` | Validation error |

```bash
curl -X POST http://localhost:8000/api/v1/blog/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Getting Started with Aegis Stack",
    "content": "# Hello\n\nThis is my first post.",
    "tag_slugs": ["aegis", "tutorial"]
  }'
```

---

### PUT /blog/posts/{post_id}

Update an existing post. Only fields included in the request body are changed. Pass `tag_slugs` to replace the full tag set; omit it to leave tags unchanged.

**Auth:** Protected

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `post_id` | `integer` | Post ID |

**Request body:** `BlogPostUpdate` — all fields optional

| Field | Type | Notes |
|-------|------|-------|
| `title` | `string \| null` | |
| `slug` | `string \| null` | Changing the slug on a published post updates the public URL |
| `content` | `string \| null` | |
| `excerpt` | `string \| null` | |
| `tag_slugs` | `list[string] \| null` | Replaces all tags if present; ignored when null |
| `seo_title` | `string \| null` | |
| `seo_description` | `string \| null` | |
| `hero_image_url` | `string \| null` | |

**Response: `200 OK`** — `BlogPostResponse`

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Post updated |
| `404` | Post not found |
| `409` | New slug already taken |
| `422` | Validation error |

```bash
curl -X PUT http://localhost:8000/api/v1/blog/posts/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "tag_slugs": ["aegis"]}'
```

---

### POST /blog/posts/{post_id}/publish

Publish a post. Sets `status` to `published` and records `published_at` (only on first publish; subsequent calls are idempotent on that field).

**Auth:** Protected

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `post_id` | `integer` | Post ID |

**Response: `200 OK`** — `BlogPostResponse` with `status: "published"`

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Post published |
| `404` | Post not found |

```bash
curl -X POST http://localhost:8000/api/v1/blog/posts/1/publish \
  -H "Authorization: Bearer $TOKEN"
```

---

### POST /blog/posts/{post_id}/archive

Archive a post. Sets `status` to `archived`. The post can be re-published later.

**Auth:** Protected

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `post_id` | `integer` | Post ID |

**Response: `200 OK`** — `BlogPostResponse` with `status: "archived"`

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Post archived |
| `404` | Post not found |

```bash
curl -X POST http://localhost:8000/api/v1/blog/posts/1/archive \
  -H "Authorization: Bearer $TOKEN"
```

---

### DELETE /blog/posts/{post_id}

Permanently delete a post and its tag associations.

**Auth:** Protected

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `post_id` | `integer` | Post ID |

**Response: `204 No Content`**

**Status codes:**

| Code | Condition |
|------|-----------|
| `204` | Post deleted |
| `404` | Post not found |

```bash
curl -X DELETE http://localhost:8000/api/v1/blog/posts/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Tag Endpoints

### GET /blog/tags

List all tags ordered by name.

**Auth:** None

**Response: `200 OK`** — `BlogTagListResponse`

| Field | Type |
|-------|------|
| `tags` | `list[BlogTagResponse]` |
| `total` | `integer` |

**`BlogTagResponse` fields:**

| Field | Type |
|-------|------|
| `id` | `integer` |
| `name` | `string` |
| `slug` | `string` |
| `created_at` | `datetime` |

```bash
curl http://localhost:8000/api/v1/blog/tags
```

---

### POST /blog/tags

Create a tag. The slug is derived from the name if omitted. Returns `409` if a tag with the same name or slug already exists.

**Auth:** Protected

**Request body:** `BlogTagCreate`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | `string` | Yes | max 80 chars, must be unique |
| `slug` | `string` | No | auto-derived from name if omitted; max 100 chars |

**Response: `201 Created`** — `BlogTagResponse`

**Status codes:**

| Code | Condition |
|------|-----------|
| `201` | Tag created |
| `409` | Name or slug already exists |
| `422` | Validation error |

```bash
curl -X POST http://localhost:8000/api/v1/blog/tags \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Tutorial"}'
```

---

### PUT /blog/tags/{tag_id}

Update a tag's name or slug.

**Auth:** Protected

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tag_id` | `integer` | Tag ID |

**Request body:** `BlogTagUpdate` — all fields optional

| Field | Type | Notes |
|-------|------|-------|
| `name` | `string \| null` | |
| `slug` | `string \| null` | |

**Response: `200 OK`** — `BlogTagResponse`

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Tag updated |
| `404` | Tag not found |
| `409` | Name or slug collision |

```bash
curl -X PUT http://localhost:8000/api/v1/blog/tags/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Tutorials"}'
```

---

### DELETE /blog/tags/{tag_id}

Delete a tag and remove it from all posts (cleans up `blog_post_tag` rows).

**Auth:** Protected

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tag_id` | `integer` | Tag ID |

**Response: `204 No Content`**

**Status codes:**

| Code | Condition |
|------|-----------|
| `204` | Tag deleted |
| `404` | Tag not found |

```bash
curl -X DELETE http://localhost:8000/api/v1/blog/tags/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Export / Import Endpoints

### GET /blog/export

Download all posts as a markdown zip archive or a single JSON document.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | `markdown` \| `json` | `markdown` | Output format |
| `status_filter` | string | (none) | Only export posts with this status |

**Response (`format=markdown`):** `Content-Type: application/zip` containing one `.md` file per post (named by slug).

**Response (`format=json`):** `Content-Type: application/json` — array of `ExportedPost` objects.

```bash
curl -OJ http://localhost:8000/api/v1/blog/export?format=markdown \
  -H "Authorization: Bearer $TOKEN"

curl -OJ http://localhost:8000/api/v1/blog/export?format=json&status_filter=published \
  -H "Authorization: Bearer $TOKEN"
```

### POST /blog/import

Import posts from a markdown file, a zip of markdown files, or a JSON document. The format is auto-detected from the upload's filename extension (`.md`, `.zip`, `.json`).

The importer is lenient on frontmatter fields and accepts Hugo, Jekyll, and Astro conventions. See the [CLI reference](cli.md#export-and-import) for the alias table and limitations.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `on_conflict` | `skip` \| `overwrite` \| `fail` | `skip` | Behavior when a slug already exists |

**Body:** `multipart/form-data` with a single `file` field.

**Response:** `200 OK` with an `ImportResult` JSON body:

```json
{
  "created": 12,
  "updated": 0,
  "skipped": 1,
  "failed": 0,
  "errors": []
}
```

`fail` mode rolls back the entire batch on the first slug collision (no rows committed).

```bash
curl -X POST http://localhost:8000/api/v1/blog/import?on_conflict=overwrite \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@blog-backup.zip"

curl -X POST http://localhost:8000/api/v1/blog/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@my-post.md"
```

**Status codes:** `200` on success (even with per-post errors recorded in the `errors` array). `400` if the upload's filename has no recognized extension or the body is not valid UTF-8.

---

## Common Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Resource created |
| `204` | Success, no content |
| `404` | Resource not found |
| `409` | Slug or name conflict |
| `422` | Request body validation error |

---

**See also:**

- **[Getting Started](index.md)** - Service overview and data model
- **[Dashboard](dashboard.md)** - Overseer editor UI
- **[Examples](examples.md)** - End-to-end workflow examples
