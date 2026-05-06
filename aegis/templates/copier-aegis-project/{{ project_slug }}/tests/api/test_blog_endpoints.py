"""Tests for blog API endpoints."""

import io
import json
import zipfile

from fastapi.testclient import TestClient
import pytest


def _post_payload(slug: str = "hello") -> dict[str, object]:
    return {
        "title": "Hello",
        "slug": slug,
        "excerpt": "Short intro",
        "content": "# Hello",
        "tag_slugs": ["news"],
    }


@pytest.mark.asyncio
async def test_blog_create_publish_and_public_read(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_response = async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload(),
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    draft = create_response.json()
    assert draft["status"] == "draft"
    assert draft["slug"] == "hello"

    hidden_response = async_client_with_db.get("/api/v1/blog/posts/hello")
    assert hidden_response.status_code == 404

    publish_response = async_client_with_db.post(
        f"/api/v1/blog/posts/{draft['id']}/publish",
        headers=auth_headers,
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"

    public_response = async_client_with_db.get("/api/v1/blog/posts/hello")
    assert public_response.status_code == 200
    assert public_response.json()["title"] == "Hello"

    list_response = async_client_with_db.get("/api/v1/blog/posts")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


@pytest.mark.asyncio
async def test_blog_duplicate_slug_returns_conflict(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    first = async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("same"),
        headers=auth_headers,
    )
    assert first.status_code == 201

    duplicate = async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("same"),
        headers=auth_headers,
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_blog_archive_hides_public_post(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("archive-me"),
        headers=auth_headers,
    ).json()
    async_client_with_db.post(
        f"/api/v1/blog/posts/{created['id']}/publish",
        headers=auth_headers,
    )

    archive_response = async_client_with_db.post(
        f"/api/v1/blog/posts/{created['id']}/archive",
        headers=auth_headers,
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    public_response = async_client_with_db.get("/api/v1/blog/posts/archive-me")
    assert public_response.status_code == 404


@pytest.mark.asyncio
async def test_blog_tag_crud(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_response = async_client_with_db.post(
        "/api/v1/blog/tags",
        json={"name": "Product"},
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    tag = create_response.json()
    assert tag["slug"] == "product"

    list_response = async_client_with_db.get("/api/v1/blog/tags")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    delete_response = async_client_with_db.delete(
        f"/api/v1/blog/tags/{tag['id']}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_blog_export_markdown_returns_zip(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Export in markdown format returns a zip file."""
    async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("export-1"),
        headers=auth_headers,
    )
    async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("export-2"),
        headers=auth_headers,
    )

    response = async_client_with_db.get(
        "/api/v1/blog/export?format=markdown",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        names = zf.namelist()
        assert "export-1.md" in names
        assert "export-2.md" in names
        content1 = zf.read("export-1.md").decode("utf-8")
        assert "title: Hello" in content1


@pytest.mark.asyncio
async def test_blog_export_json_returns_json(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Export in JSON format returns a JSON array."""
    async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("json-1"),
        headers=auth_headers,
    )
    async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("json-2"),
        headers=auth_headers,
    )

    response = async_client_with_db.get(
        "/api/v1/blog/export?format=json",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"

    data = json.loads(response.content)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["title"] == "Hello"


@pytest.mark.asyncio
async def test_blog_export_status_filter(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Export respects status_filter query parameter."""
    async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("draft-export"),
        headers=auth_headers,
    )
    pub = async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("pub-export"),
        headers=auth_headers,
    ).json()
    async_client_with_db.post(
        f"/api/v1/blog/posts/{pub['id']}/publish",
        headers=auth_headers,
    )

    response = async_client_with_db.get(
        "/api/v1/blog/export?format=json&status_filter=published",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = json.loads(response.content)
    assert len(data) == 1
    assert data[0]["slug"] == "pub-export"


@pytest.mark.asyncio
async def test_blog_import_zip_creates_posts(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Import a zip file creates posts."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "imported-1.md",
            "---\ntitle: Imported 1\nslug: imported-1\n---\nContent 1",
        )
        zf.writestr(
            "imported-2.md",
            "---\ntitle: Imported 2\nslug: imported-2\n---\nContent 2",
        )

    response = async_client_with_db.post(
        "/api/v1/blog/import",
        files={"file": ("posts.zip", buf.getvalue(), "application/zip")},
        headers=auth_headers,
    )
    assert response.status_code == 200

    result = response.json()
    assert result["created"] == 2
    assert result["skipped"] == 0

    list_response = async_client_with_db.get(
        "/api/v1/blog/admin/posts?page=1&page_size=100",
        headers=auth_headers,
    )
    posts = list_response.json()["posts"]
    assert len(posts) == 2


@pytest.mark.asyncio
async def test_blog_import_json_creates_posts(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Import a JSON file creates posts."""
    json_payload = json.dumps([
        {
            "title": "JSON Post 1",
            "slug": "json-1",
            "content": "c1",
            "status": "draft",
            "tag_slugs": [],
        },
        {
            "title": "JSON Post 2",
            "slug": "json-2",
            "content": "c2",
            "status": "published",
            "tag_slugs": ["tag1"],
        },
    ])

    response = async_client_with_db.post(
        "/api/v1/blog/import",
        files={
            "file": (
                "posts.json",
                json_payload.encode("utf-8"),
                "application/json",
            )
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    result = response.json()
    assert result["created"] == 2

    list_response = async_client_with_db.get(
        "/api/v1/blog/admin/posts?page=1&page_size=100",
        headers=auth_headers,
    )
    posts = list_response.json()["posts"]
    assert len(posts) == 2
    titles = {post["title"] for post in posts}
    assert titles == {"JSON Post 1", "JSON Post 2"}


@pytest.mark.asyncio
async def test_blog_import_markdown_single_file(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Import a single markdown file."""
    md_content = "---\ntitle: Single Post\nslug: single\n---\n# Content"

    response = async_client_with_db.post(
        "/api/v1/blog/import",
        files={"file": ("post.md", md_content.encode("utf-8"), "text/markdown")},
        headers=auth_headers,
    )
    assert response.status_code == 200

    result = response.json()
    assert result["created"] == 1

    list_response = async_client_with_db.get(
        "/api/v1/blog/admin/posts",
        headers=auth_headers,
    )
    posts = list_response.json()["posts"]
    assert len(posts) == 1
    assert posts[0]["slug"] == "single"


@pytest.mark.asyncio
async def test_blog_import_unsupported_extension(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Import with unsupported file type returns 400."""
    response = async_client_with_db.post(
        "/api/v1/blog/import",
        files={"file": ("posts.txt", b"some content", "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_blog_import_on_conflict_skip(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Import with on_conflict=skip skips existing slugs."""
    async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("skip-conflict"),
        headers=auth_headers,
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "skip-conflict.md",
            "---\ntitle: Updated Title\nslug: skip-conflict\n---\nNew Content",
        )

    response = async_client_with_db.post(
        "/api/v1/blog/import?on_conflict=skip",
        files={"file": ("posts.zip", buf.getvalue(), "application/zip")},
        headers=auth_headers,
    )
    assert response.status_code == 200

    result = response.json()
    assert result["skipped"] == 1

    list_response = async_client_with_db.get(
        "/api/v1/blog/admin/posts?status=draft",
        headers=auth_headers,
    )
    posts = list_response.json()["posts"]
    assert len(posts) == 1
    assert posts[0]["title"] == "Hello"


@pytest.mark.asyncio
async def test_blog_import_on_conflict_overwrite(
    async_client_with_db: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Import with on_conflict=overwrite updates existing posts."""
    async_client_with_db.post(
        "/api/v1/blog/posts",
        json=_post_payload("update-me"),
        headers=auth_headers,
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "update-me.md",
            "---\ntitle: Brand New Title\nslug: update-me\n---\nFresh Content",
        )

    response = async_client_with_db.post(
        "/api/v1/blog/import?on_conflict=overwrite",
        files={"file": ("posts.zip", buf.getvalue(), "application/zip")},
        headers=auth_headers,
    )
    assert response.status_code == 200

    result = response.json()
    assert result["updated"] == 1

    list_response = async_client_with_db.get(
        "/api/v1/blog/admin/posts",
        headers=auth_headers,
    )
    posts = list_response.json()["posts"]
    update_me = [p for p in posts if p["slug"] == "update-me"]
    assert len(update_me) == 1
    assert update_me[0]["title"] == "Brand New Title"
