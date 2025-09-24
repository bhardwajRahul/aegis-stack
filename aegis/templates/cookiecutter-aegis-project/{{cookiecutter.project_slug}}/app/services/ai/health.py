"""
AI service health check functions.

Health monitoring for AI service functionality including provider configuration,
API connectivity, and service-specific metrics.
"""

from app.core.config import settings
from app.core.log import logger
from app.services.system.models import ComponentStatus, ComponentStatusType


async def check_ai_service_health() -> ComponentStatus:
    """
    Check AI service health including provider configuration and dependencies.

    Returns:
        ComponentStatus indicating AI service health
    """
    try:
        from .service import AIService

        # Initialize AI service for health check
        ai_service = AIService(settings)

        # Get service status
        service_status = ai_service.get_service_status()
        validation_errors = ai_service.validate_service()

        # Determine overall health
        if not service_status["enabled"]:
            status = ComponentStatusType.DEGRADED
            message = "AI service is disabled"
        elif validation_errors:
            status = ComponentStatusType.UNHEALTHY
            message = (
                f"AI service configuration issues: {'; '.join(validation_errors[:2])}"
            )
        else:
            status = ComponentStatusType.HEALTHY
            message = f"AI service ready - {service_status['provider']} provider"

        # Collect comprehensive metadata
        metadata = {
            "service_type": "ai",
            "engine": "pydantic-ai",
            "enabled": service_status["enabled"],
            "provider": service_status["provider"],
            "model": service_status["model"],
            "agent_ready": service_status["agent_initialized"],
            "conversations_active": service_status["total_conversations"],
            "configuration_valid": service_status["configuration_valid"],
            "validation_errors_count": len(validation_errors),
        }

        # Add dependency status
        metadata["dependencies"] = {
            "backend": "required",
            "pydantic_ai": "required",
        }

        # Add provider-specific info
        if service_status["enabled"]:
            from .models import get_free_providers, get_provider_capabilities

            provider_caps = get_provider_capabilities(ai_service.config.provider)
            free_providers = get_free_providers()

            metadata.update(
                {
                    "provider_supports_streaming": provider_caps.supports_streaming,
                    "provider_free_tier": ai_service.config.provider in free_providers,
                }
            )

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
                "engine": "pydantic-ai",
                "error": str(e),
                "error_type": "health_check_failure",
            },
        )
