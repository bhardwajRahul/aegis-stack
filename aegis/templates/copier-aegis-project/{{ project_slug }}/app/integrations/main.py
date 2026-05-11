import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import flet.fastapi as flet_fastapi
from app.components.backend.hooks import backend_hooks
from app.components.backend.main import create_backend_app
from app.components.frontend.main import create_frontend_app
from app.core.config import settings
from app.core.log import logger, setup_logging
from fastapi import Depends, FastAPI, HTTPException
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

_docs_security = HTTPBasic(auto_error=False)


def require_docs_auth(
    credentials: HTTPBasicCredentials | None = Depends(_docs_security),
) -> None:
    """Gate for OpenAPI docs endpoints.

    Unset creds -> open in dev (DX), 404 elsewhere (fail-closed).
    Set creds -> HTTP Basic required, constant-time compared.
    """
    expected_user = settings.DOCS_USERNAME
    expected_pass = settings.DOCS_PASSWORD

    if not expected_user or not expected_pass:
        if settings.APP_ENV == "dev":
            return
        raise HTTPException(status_code=404)

    if credentials is None:
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
        )

    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan manager.
    Handles startup/shutdown concerns using component-specific hooks.
    """
    # Ensure logging is configured (required for uvicorn reload mode)
    setup_logging()

    # --- STARTUP ---
    logger.info("--- Running application startup ---")

    # Discover startup and shutdown hooks
    await backend_hooks.discover_lifespan_hooks()

    # Start Flet app manager
    await flet_fastapi.app_manager.start()

    # Execute backend startup hooks
    await backend_hooks.execute_startup_hooks()

    logger.info("--- Application startup complete ---")

    yield

    # --- SHUTDOWN ---
    logger.info("--- Running application shutdown ---")

    # Execute backend shutdown hooks
    await backend_hooks.execute_shutdown_hooks()

    # Stop Flet app manager
    await flet_fastapi.app_manager.shutdown()

    logger.info("--- Application shutdown complete ---")


def create_integrated_app() -> FastAPI:
    """
    Creates the integrated Flet+FastAPI application using the officially
    recommended pattern and component-specific hooks.
    """
    app = FastAPI(
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/openapi.json", include_in_schema=False)
    def _openapi_json(_: None = Depends(require_docs_auth)) -> dict:
        return get_openapi(title=app.title, version=app.version, routes=app.routes)

    @app.get("/docs", include_in_schema=False)
    def _swagger_ui(_: None = Depends(require_docs_auth)) -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
        )

    @app.get("/redoc", include_in_schema=False)
    def _redoc_ui(_: None = Depends(require_docs_auth)) -> HTMLResponse:
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - ReDoc",
        )

    create_backend_app(app)
    # Create and mount the Flet app using the flet.fastapi module
    # First, get the actual session handler function from the factory
    session_handler = create_frontend_app()
    flet_app = flet_fastapi.app(session_handler, assets_dir=settings.FLET_ASSETS_DIR)
    # Mount Flet at /dashboard to avoid intercepting FastAPI routes like /health
    app.mount("/dashboard", flet_app)
    return app
