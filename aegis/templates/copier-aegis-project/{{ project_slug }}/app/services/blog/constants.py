"""Constants for the blog service."""

from enum import StrEnum

BLOG_COMPONENT_NAME = "blog"


class BlogPostStatus:
    """Blog post lifecycle states."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    ALL = [DRAFT, PUBLISHED, ARCHIVED]


class ImportConflictPolicy(StrEnum):
    """How import_posts should handle a slug that already exists."""

    SKIP = "skip"
    OVERWRITE = "overwrite"
    FAIL = "fail"


STALE_DRAFT_DAYS = 30
