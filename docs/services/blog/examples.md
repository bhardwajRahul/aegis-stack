# Examples

Copy-paste recipes for common blog workflows. All examples assume the app is running at `http://localhost:8000` and was generated with auth enabled.

---

## 1. Setup

```bash
aegis init my-site --services blog auth --components database
cd my-site
uv sync && source .venv/bin/activate
make serve
```

In a second terminal, get an auth token:

```bash
# Register an admin user or use an existing one
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "editor@example.com", "password": "Editor1234!"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=editor@example.com&password=Editor1234!" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

---

## 2. Create Tags

Tags must exist before you can attach them to posts.

```bash
# Create a few tags
curl -s -X POST http://localhost:8000/api/v1/blog/tags \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Tutorial"}' \
  | python3 -m json.tool

curl -s -X POST http://localhost:8000/api/v1/blog/tags \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Aegis Stack"}' \
  | python3 -m json.tool
```

Expected response for the first tag:

```json
{
    "id": 1,
    "name": "Tutorial",
    "slug": "tutorial",
    "created_at": "2026-05-06T10:00:00"
}
```

Verify all tags:

```bash
curl -s http://localhost:8000/api/v1/blog/tags | python3 -m json.tool
```

---

## 3. Create a Draft Post

```bash
curl -s -X POST http://localhost:8000/api/v1/blog/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Getting Started with Aegis Stack",
    "content": "# Getting Started\n\nThis guide covers the basics.\n\n## Installation\n\n```bash\npip install aegis-stack\n```",
    "excerpt": "A quick guide to getting up and running.",
    "tag_slugs": ["tutorial", "aegis-stack"]
  }' \
  | python3 -m json.tool
```

Expected response (trimmed):

```json
{
    "id": 1,
    "title": "Getting Started with Aegis Stack",
    "slug": "getting-started-with-aegis-stack",
    "status": "draft",
    "author_id": null,
    "author_name": null,
    "published_at": null,
    "tags": [
        {"id": 1, "name": "Tutorial", "slug": "tutorial", "created_at": "..."},
        {"id": 2, "name": "Aegis Stack", "slug": "aegis-stack", "created_at": "..."}
    ]
}
```

The slug is auto-derived from the title. The post status is `draft`.

---

## 4. Update the Draft

Add SEO metadata and update the content before publishing:

```bash
curl -s -X PUT http://localhost:8000/api/v1/blog/posts/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seo_title": "Aegis Stack Quickstart Guide",
    "seo_description": "Install and run your first Aegis Stack project in under 5 minutes.",
    "hero_image_url": "https://example.com/images/aegis-hero.png"
  }' \
  | python3 -m json.tool
```

Only the fields you include are changed. Tags are unchanged because `tag_slugs` was not sent.

To replace tags, include `tag_slugs` with the full new set:

```bash
curl -s -X PUT http://localhost:8000/api/v1/blog/posts/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag_slugs": ["tutorial"]}' \
  | python3 -m json.tool
```

---

## 5. Publish the Post

```bash
curl -s -X POST http://localhost:8000/api/v1/blog/posts/1/publish \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

```json
{
    "id": 1,
    "status": "published",
    "published_at": "2026-05-06T10:05:00",
    ...
}
```

`published_at` is set once and never overwritten on subsequent publish calls.

Verify the post is now publicly readable:

```bash
# No auth required
curl -s http://localhost:8000/api/v1/blog/posts/getting-started-with-aegis-stack \
  | python3 -m json.tool
```

---

## 6. List Posts by Tag

```bash
# Public endpoint, no auth
curl -s "http://localhost:8000/api/v1/blog/posts?tag=tutorial" \
  | python3 -m json.tool
```

```json
{
    "posts": [...],
    "total": 1,
    "page": 1,
    "page_size": 20
}
```

---

## 7. Archive a Post

Archiving removes it from public listings without deleting the content.

```bash
curl -s -X POST http://localhost:8000/api/v1/blog/posts/1/archive \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d['status'])"
```

```
status: archived
```

The post is no longer returned by `GET /api/v1/blog/posts` (public endpoint), but is still visible in `GET /api/v1/blog/admin/posts`.

To re-publish an archived post:

```bash
curl -s -X POST http://localhost:8000/api/v1/blog/posts/1/publish \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d['status'])"
```

```
status: published
```

---

## 8. Inspect Health Metadata

The health summary is available from the dashboard endpoint used by the Overseer:

```bash
curl -s http://localhost:8000/health/dashboard \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
blog = data['dashboard_data']['components'].get('blog', {})
print('status:', blog.get('status'))
print('message:', blog.get('message'))
meta = blog.get('metadata', {})
print('published:', meta.get('published_posts'))
print('drafts:', meta.get('draft_posts'))
print('stale drafts:', meta.get('stale_draft_count'))
latest = meta.get('latest_published_post')
if latest:
    print('latest:', latest.get('title'))
"
```

```
status: healthy
message: 1 published, 0 drafts
published: 1
drafts: 0
stale drafts: 0
latest: Getting Started with Aegis Stack
```

---

## 9. Delete a Tag

Deleting a tag removes it from all posts automatically.

```bash
# Check current tags on the post
curl -s http://localhost:8000/api/v1/blog/posts/getting-started-with-aegis-stack \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print([t['slug'] for t in d['tags']])"

# ['tutorial']

# Delete the tag
curl -s -X DELETE http://localhost:8000/api/v1/blog/tags/1 \
  -H "Authorization: Bearer $TOKEN" \
  -o /dev/null -w "%{http_code}\n"

# 204

# Verify the post no longer has the tag
curl -s http://localhost:8000/api/v1/blog/posts/getting-started-with-aegis-stack \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print([t['slug'] for t in d['tags']])"

# []
```

---

## 10. Paginate the Admin Post List

```bash
# Get page 2 with 5 posts per page, drafts only
curl -s "http://localhost:8000/api/v1/blog/admin/posts?status=draft&page=2&page_size=5" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

```json
{
    "posts": [...],
    "total": 12,
    "page": 2,
    "page_size": 5
}
```

---

**Next steps:**

- **[API Reference](api.md)** - Full route and schema documentation
- **[Dashboard](dashboard.md)** - Overseer editor UI walkthrough
- **[CLI Commands](cli.md)** - CLI availability note
