"""
LLM catalog API router.

FastAPI router for LLM catalog endpoints providing model listing,
vendor information, and current configuration status.
"""

from typing import Any

from app.core.db import engine
from app.services.ai.etl import CatalogStats, get_catalog_stats
from app.services.ai.llm_service import (
    CurrentLLMConfig,
    LLMListResult,
    ModalityListResult,
    VendorListResult,
    get_current_config,
    list_modalities,
    list_models,
    list_vendors,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

router = APIRouter(prefix="/llm", tags=["llm"])


# Response models
class CatalogStatsResponse(BaseModel):
    """Catalog statistics response."""

    vendor_count: int
    model_count: int
    deployment_count: int
    price_count: int
    top_vendors: list[dict[str, Any]]


class VendorResponse(BaseModel):
    """Vendor list response."""

    name: str
    model_count: int


class ModelResponse(BaseModel):
    """Model list response."""

    model_id: str
    vendor: str
    context_window: int
    input_price: float | None
    output_price: float | None
    released_on: str | None


class CurrentConfigResponse(BaseModel):
    """Current LLM configuration response."""

    provider: str
    model: str
    temperature: float
    max_tokens: int
    context_window: int | None = None
    input_price: float | None = None
    output_price: float | None = None
    modalities: list[str] | None = None


class ModalityResponse(BaseModel):
    """Modality list response."""

    modality: str
    model_count: int


@router.get("/status", response_model=CatalogStatsResponse)
def get_catalog_status() -> CatalogStatsResponse:
    """
    Get LLM catalog statistics.

    Returns counts of vendors, models, deployments, prices,
    and top vendors by model count.
    """
    try:
        with Session(engine) as session:
            stats: CatalogStats = get_catalog_stats(session)

        return CatalogStatsResponse(
            vendor_count=stats.vendor_count,
            model_count=stats.model_count,
            deployment_count=stats.deployment_count,
            price_count=stats.price_count,
            top_vendors=[
                {"name": name, "model_count": count}
                for name, count in stats.top_vendors
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get catalog stats: {e}")


@router.get("/vendors", response_model=list[VendorResponse])
def get_vendors() -> list[VendorResponse]:
    """
    List all LLM vendors with model counts.

    Returns vendors sorted alphabetically by name.
    """
    try:
        results: list[VendorListResult] = list_vendors()
        return [VendorResponse(name=v.name, model_count=v.model_count) for v in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list vendors: {e}")


@router.get("/modalities", response_model=list[ModalityResponse])
def get_modalities() -> list[ModalityResponse]:
    """
    List all modalities with model counts.

    Returns modalities sorted alphabetically.
    """
    try:
        results: list[ModalityListResult] = list_modalities()
        return [
            ModalityResponse(modality=m.modality, model_count=m.model_count)
            for m in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list modalities: {e}")


@router.get("/models", response_model=list[ModelResponse])
async def get_models(
    pattern: str | None = Query(
        None, description="Search pattern for model ID or title"
    ),
    vendor: str | None = Query(None, description="Filter by vendor name"),
    modality: str | None = Query(None, description="Filter by modality"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    include_disabled: bool = Query(False, description="Include disabled models"),
) -> list[ModelResponse]:
    """
    List/search LLM models from catalog.

    Supports filtering by pattern, vendor, and modality.
    """
    try:
        results: list[LLMListResult] = await list_models(
            pattern=pattern,
            vendor=vendor,
            modality=modality,
            limit=limit,
            include_disabled=include_disabled,
        )
        return [
            ModelResponse(
                model_id=m.model_id,
                vendor=m.vendor,
                context_window=m.context_window,
                input_price=m.input_price,
                output_price=m.output_price,
                released_on=m.released_on,
            )
            for m in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")


@router.get("/current", response_model=CurrentConfigResponse)
async def get_current() -> CurrentConfigResponse:
    """
    Get current active LLM configuration.

    Returns provider, model, and settings from environment,
    enriched with catalog data if model exists in database.
    """
    try:
        config: CurrentLLMConfig = await get_current_config()
        return CurrentConfigResponse(
            provider=config.provider,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            context_window=config.context_window,
            input_price=config.input_price,
            output_price=config.output_price,
            modalities=config.modalities,
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to get current config: {e}"
        )
