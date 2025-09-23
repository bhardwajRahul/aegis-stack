"""
AI service health check functions.

Health monitoring for AI service functionality including provider configuration,
API connectivity, and service-specific metrics.
"""

from app.core.log import logger
from app.services.system.models import ComponentStatus, ComponentStatusType


async def check_ai_service_health() -> ComponentStatus:
    """
    Check AI service health including provider configuration and dependencies.

    Returns:
        ComponentStatus indicating AI service health
    """
    try:
        # Basic health check - full implementation in ticket #162 (Configuration)
        status = ComponentStatusType.HEALTHY
        message = "AI service foundation ready (configuration pending)"

        # Collect basic metadata
        metadata = {
            "service_type": "ai",
            "engine": "pydantic-ai",
            "providers_configured": 0,  # Will be updated in #162
            "conversations_active": 0,  # Will be updated in #159
            "configuration_status": "pending",
        }

        # Add dependency status
        metadata["dependencies"] = {
            "backend": "required",  # AI service always requires backend
        }

        return ComponentStatus(
            name="ai",
            status=status,
            message=message,
            response_time_ms=None,  # Will be set by caller
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"AI service health check failed: {e}")
        return ComponentStatus(
            name="ai",
            status=ComponentStatusType.UNHEALTHY,
            message=f"AI service health check failed: {str(e)}",
            response_time_ms=None,
            metadata={
                "service_type": "ai",
                "error": str(e),
                "error_type": "health_check_failure",
            },
        )
