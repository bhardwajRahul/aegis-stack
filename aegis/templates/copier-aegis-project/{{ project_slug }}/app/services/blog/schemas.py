"""Pydantic schemas for the blog service."""

from datetime import datetime

from pydantic import BaseModel, Field

from .constants import BlogPostStatus


class BlogTagCreate(BaseModel):
    """Create a blog tag."""

    name: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=100)


class BlogTagUpdate(BaseModel):
    """Update a blog tag."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=100)


class BlogTagResponse(BaseModel):
    """Serialized tag."""

    id: int
    name: str
    slug: str
    created_at: datetime


class BlogPostCreate(BaseModel):
    """Create a blog post."""

    title: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    excerpt: str | None = Field(default=None, max_length=500)
    content: str = Field(default="", max_length=200_000)
    tag_slugs: list[str] = Field(default_factory=list)
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    hero_image_url: str | None = Field(default=None, max_length=1024)


class BlogPostUpdate(BaseModel):
    """Update a blog post."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    excerpt: str | None = Field(default=None, max_length=500)
    content: str | None = Field(default=None, max_length=200_000)
    tag_slugs: list[str] | None = None
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    hero_image_url: str | None = Field(default=None, max_length=1024)


class BlogPostResponse(BaseModel):
    """Serialized blog post."""

    id: int
    title: str
    slug: str
    excerpt: str | None
    content: str
    status: str = BlogPostStatus.DRAFT
    author_id: int | None
    author_name: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    seo_title: str | None
    seo_description: str | None
    hero_image_url: str | None
    tags: list[BlogTagResponse] = Field(default_factory=list)


class BlogPostListResponse(BaseModel):
    """Paginated post list."""

    posts: list[BlogPostResponse]
    total: int
    page: int
    page_size: int


class BlogTagListResponse(BaseModel):
    """Tag list response."""

    tags: list[BlogTagResponse]
    total: int


class ExportedPost(BaseModel):
    """Portable post payload for export and import.

    Excludes ``author_id`` (FK to the source project's user table — does not
    transfer cleanly across projects). ``author_name`` survives as a string.
    Excludes the DB ``id``; ``slug`` is the natural key.
    """

    title: str
    slug: str
    excerpt: str | None = None
    content: str = ""
    status: str = BlogPostStatus.DRAFT
    author_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_at: datetime | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    hero_image_url: str | None = None
    tag_slugs: list[str] = Field(default_factory=list)


class ImportedPost(ExportedPost):
    """Same shape as ExportedPost; aliased for clarity at the API boundary."""


class BlogImportError(BaseModel):
    """Per-post import error."""

    slug: str
    message: str


class ImportResult(BaseModel):
    """Summary returned by ``BlogService.import_posts``."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[BlogImportError] = Field(default_factory=list)
