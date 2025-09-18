"""
Auth service health check functions.

Health monitoring for authentication and authorization service functionality.
Checks JWT configuration, database connectivity, and service-specific metrics.
"""

from app.core.config import settings
from app.core.log import logger
from app.services.system.models import ComponentStatus, ComponentStatusType


async def check_auth_service_health() -> ComponentStatus:
    """
    Check auth service health including JWT configuration and dependencies.

    Returns:
        ComponentStatus indicating auth service health
    """
    try:
        # Check JWT configuration
        jwt_errors = []

        # Verify JWT secret key is configured
        # Note: 32 characters = 256 bits, which is secure for HS256 HMAC-SHA256 signing
        if not hasattr(settings, "SECRET_KEY") or not settings.SECRET_KEY:
            jwt_errors.append("SECRET_KEY not configured")
        elif len(settings.SECRET_KEY) < 32:
            jwt_errors.append("SECRET_KEY too short (minimum 32 characters for HS256)")

        # Verify JWT algorithm is supported
        algorithm = getattr(settings, "ALGORITHM", "HS256")
        supported_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if algorithm not in supported_algorithms:
            jwt_errors.append(f"Unsupported JWT algorithm: {algorithm}")

        # Verify token expiration is configured
        access_token_expire = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", None)
        if access_token_expire is None or access_token_expire <= 0:
            jwt_errors.append("ACCESS_TOKEN_EXPIRE_MINUTES not properly configured")

        # Check database dependency for user storage
        database_available = True
        try:
            from sqlalchemy import text

            from app.core.db import db_session

            with db_session() as session:
                # Test database connectivity with a simple query
                session.execute(text("SELECT 1"))
        except ImportError:
            database_available = False
            jwt_errors.append("Database module not available for user storage")
        except Exception as e:
            database_available = False
            jwt_errors.append(f"Database connectivity issue: {str(e)}")

        # Determine service status
        if jwt_errors:
            if not database_available:
                status = ComponentStatusType.UNHEALTHY
                message = f"Auth service misconfigured: {'; '.join(jwt_errors)}"
            else:
                # Some JWT config issues but database is available
                status = ComponentStatusType.WARNING
                message = (
                    f"Auth service has configuration warnings: {'; '.join(jwt_errors)}"
                )
        else:
            status = ComponentStatusType.HEALTHY
            message = "Auth service configured and ready"

        # Collect metadata
        metadata = {
            "service_type": "auth",
            "jwt_algorithm": algorithm,
            "token_expiry_minutes": access_token_expire,
            "database_available": database_available,
            "secret_key_configured": hasattr(settings, "SECRET_KEY")
            and bool(settings.SECRET_KEY),
            "secret_key_length": len(getattr(settings, "SECRET_KEY", ""))
            if hasattr(settings, "SECRET_KEY")
            else 0,
        }

        # Add configuration issues to metadata if any
        if jwt_errors:
            metadata["configuration_issues"] = jwt_errors

        # Add dependency status
        metadata["dependencies"] = {
            "database": "available" if database_available else "unavailable",
            "backend": "required",  # Auth service always requires backend
        }

        return ComponentStatus(
            name="auth",
            status=status,
            message=message,
            response_time_ms=None,  # Will be set by caller
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Auth service health check failed: {e}")
        return ComponentStatus(
            name="auth",
            status=ComponentStatusType.UNHEALTHY,
            message=f"Auth service health check failed: {str(e)}",
            response_time_ms=None,
            metadata={
                "service_type": "auth",
                "error": str(e),
                "error_type": "health_check_failure",
            },
        )
