"""
AI service API router.

FastAPI router for AI chat endpoints. Core functionality will be
implemented in ticket #159 (Core Implementation).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/health")
async def ai_health() -> dict[str, str]:
    """
    AI service health endpoint.

    Returns basic health status. Full health check implementation
    will be added in ticket #159.
    """
    return {
        "service": "ai",
        "status": "foundation_ready",
        "message": "AI service foundation ready (implementation pending)",
    }


@router.get("/version")
async def ai_version() -> dict[str, str]:
    """AI service version information."""
    return {
        "service": "ai",
        "engine": "pydantic-ai",
        "version": "foundation",
        "features": ["health_check", "configuration_stub"],
        "pending": ["chat", "streaming", "conversation_management"],
    }
