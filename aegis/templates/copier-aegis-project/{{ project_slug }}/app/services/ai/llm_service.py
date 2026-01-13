"""LLM model management service.

Provides business logic for listing, viewing, and switching LLM models.
"""

from app.core.config import settings
from app.core.db import engine, get_async_session
from app.services.ai.models.llm import (
    LargeLanguageModel,
    LLMModality,
    LLMPrice,
    LLMVendor,
)
from app.services.ai.provider_management import update_env_file
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlmodel import Session, or_, select


class LLMListResult(BaseModel):
    """Result for a single model in list output."""

    model_id: str
    vendor: str
    context_window: int
    input_price: float | None
    output_price: float | None
    released_on: str | None


class VendorListResult(BaseModel):
    """Result for a single vendor in list output."""

    name: str
    model_count: int


class ModalityListResult(BaseModel):
    """Result for a single modality in list output."""

    modality: str
    model_count: int


class CurrentLLMConfig(BaseModel):
    """Current LLM configuration from environment."""

    provider: str
    model: str
    temperature: float
    max_tokens: int
    # Optional enrichment from catalog
    context_window: int | None = None
    input_price: float | None = None
    output_price: float | None = None
    modalities: list[str] | None = None


class SetModelResult(BaseModel):
    """Result of setting a new active model."""

    success: bool
    model_id: str
    vendor: str | None
    provider_updated: bool
    message: str


class LLMDetails(BaseModel):
    """Full details for a single LLM model."""

    model_id: str
    title: str
    description: str
    vendor: str
    context_window: int
    streamable: bool
    enabled: bool
    released_on: str | None
    input_price: float | None
    output_price: float | None
    modalities: list[str]


async def list_models(
    pattern: str | None = None,
    vendor: str | None = None,
    modality: str | None = None,
    limit: int = 50,
    include_disabled: bool = False,
) -> list[LLMListResult]:
    """List LLM models from catalog with optional filtering.

    Args:
        pattern: Search pattern for model_id or title (case-insensitive)
        vendor: Filter by vendor name
        modality: Filter by modality (text, vision, audio, etc.)
        limit: Maximum number of results to return
        include_disabled: Include disabled models in results

    Returns:
        List of LLMListResult with model summary data
    """
    async with get_async_session() as session:
        # Build base query with eager loading for vendor
        stmt = (
            select(LargeLanguageModel)
            .join(LLMVendor, LargeLanguageModel.llm_vendor_id == LLMVendor.id)
            .options(selectinload(LargeLanguageModel.llm_vendor))
        )

        # Apply filters
        if pattern:
            stmt = stmt.where(
                or_(
                    LargeLanguageModel.model_id.ilike(f"%{pattern}%"),
                    LargeLanguageModel.title.ilike(f"%{pattern}%"),
                )
            )

        if vendor:
            stmt = stmt.where(LLMVendor.name.ilike(f"%{vendor}%"))

        if modality:
            stmt = stmt.join(
                LLMModality, LargeLanguageModel.id == LLMModality.llm_id
            ).where(LLMModality.modality == modality)

        if not include_disabled:
            stmt = stmt.where(LargeLanguageModel.enabled == True)  # noqa: E712

        # Sort by release date (newest first), nulls last
        stmt = stmt.order_by(
            LargeLanguageModel.released_on.desc().nulls_last(),
            LargeLanguageModel.model_id,
        )
        stmt = stmt.limit(limit)

        result = await session.exec(stmt)
        models = result.all()

        # Batch-fetch prices to avoid N+1 queries
        model_ids = [m.id for m in models]
        price_map: dict[int, LLMPrice] = {}
        if model_ids:
            price_stmt = (
                select(LLMPrice)
                .where(LLMPrice.llm_id.in_(model_ids))
                .order_by(LLMPrice.llm_id, LLMPrice.effective_date.desc())
            )
            price_result = await session.exec(price_stmt)
            prices = price_result.all()
            # Keep only the latest price per model (first due to ordering)
            for price in prices:
                if price.llm_id not in price_map:
                    price_map[price.llm_id] = price

        results: list[LLMListResult] = []
        for model in models:
            price = price_map.get(model.id)
            results.append(
                LLMListResult(
                    model_id=model.model_id,
                    vendor=model.llm_vendor.name if model.llm_vendor else "Unknown",
                    context_window=model.context_window,
                    input_price=price.input_cost_per_token * 1_000_000
                    if price
                    else None,
                    output_price=price.output_cost_per_token * 1_000_000
                    if price
                    else None,
                    released_on=model.released_on.strftime("%Y-%m-%d")
                    if model.released_on
                    else None,
                )
            )

        return results


async def get_current_config() -> CurrentLLMConfig:
    """Get current LLM configuration from environment.

    Reads from settings (which loads .env) and enriches with catalog data
    if the model exists in the database.

    Returns:
        CurrentLLMConfig with current settings and optional catalog enrichment
    """
    config = CurrentLLMConfig(
        provider=settings.AI_PROVIDER,
        model=settings.AI_MODEL,
        temperature=settings.AI_TEMPERATURE,
        max_tokens=settings.AI_MAX_TOKENS,
    )

    # Try to enrich from catalog
    async with get_async_session() as session:
        stmt = select(LargeLanguageModel).where(
            LargeLanguageModel.model_id == config.model
        )
        result = await session.exec(stmt)
        model = result.first()

        if model:
            config.context_window = model.context_window

            # Get latest price
            price_stmt = (
                select(LLMPrice)
                .where(LLMPrice.llm_id == model.id)
                .order_by(LLMPrice.effective_date.desc())
                .limit(1)
            )
            price_result = await session.exec(price_stmt)
            price = price_result.first()
            if price:
                config.input_price = price.input_cost_per_token * 1_000_000
                config.output_price = price.output_cost_per_token * 1_000_000

            # Get modalities
            modality_stmt = select(LLMModality).where(LLMModality.llm_id == model.id)
            modality_result = await session.exec(modality_stmt)
            modalities = modality_result.all()
            config.modalities = list({str(m.modality) for m in modalities})

    return config


async def set_active_model(model_id: str, force: bool = False) -> SetModelResult:
    """Set the active LLM model.

    Updates AI_MODEL in .env, and optionally AI_PROVIDER if the model
    belongs to a different vendor and current provider is not 'public'.

    Args:
        model_id: The model ID to set as active
        force: Skip catalog validation and allow any model string

    Returns:
        SetModelResult indicating success/failure and what was changed
    """
    vendor_name: str | None = None
    provider_updated = False

    if not force:
        # Lookup model in catalog
        async with get_async_session() as session:
            stmt = (
                select(LargeLanguageModel)
                .join(LLMVendor, LargeLanguageModel.llm_vendor_id == LLMVendor.id)
                .options(selectinload(LargeLanguageModel.llm_vendor))
                .where(LargeLanguageModel.model_id == model_id)
            )
            result = await session.exec(stmt)
            model = result.first()

            if not model:
                return SetModelResult(
                    success=False,
                    model_id=model_id,
                    vendor=None,
                    provider_updated=False,
                    message=f"Model '{model_id}' not found in catalog. "
                    "Use --force to set anyway.",
                )

            vendor_name = model.llm_vendor.name if model.llm_vendor else None

    # Prepare updates
    updates: dict[str, str] = {"AI_MODEL": model_id}

    # Always update provider based on model's vendor (auto-detect)
    if vendor_name:
        vendor_lower = vendor_name.lower()
        updates["AI_PROVIDER"] = vendor_lower
        provider_updated = True

    # Apply updates
    update_env_file(updates)

    message = f"Switched to model '{model_id}'"
    if provider_updated:
        message += f" (provider changed to '{vendor_name}')"

    return SetModelResult(
        success=True,
        model_id=model_id,
        vendor=vendor_name,
        provider_updated=provider_updated,
        message=message,
    )


async def get_model_info(model_id: str) -> LLMDetails | None:
    """Get full details for a specific LLM model.

    Args:
        model_id: The model ID to look up

    Returns:
        LLMDetails with full model information, or None if not found
    """
    async with get_async_session() as session:
        stmt = (
            select(LargeLanguageModel)
            .join(LLMVendor, LargeLanguageModel.llm_vendor_id == LLMVendor.id)
            .options(selectinload(LargeLanguageModel.llm_vendor))
            .where(LargeLanguageModel.model_id == model_id)
        )
        result = await session.exec(stmt)
        model = result.first()

        if not model:
            return None

        # Get latest price
        price_stmt = (
            select(LLMPrice)
            .where(LLMPrice.llm_id == model.id)
            .order_by(LLMPrice.effective_date.desc())
            .limit(1)
        )
        price_result = await session.exec(price_stmt)
        price = price_result.first()

        # Get modalities
        modality_stmt = select(LLMModality).where(LLMModality.llm_id == model.id)
        modality_result = await session.exec(modality_stmt)
        modalities = modality_result.all()

        return LLMDetails(
            model_id=model.model_id,
            title=model.title,
            description=model.description,
            vendor=model.llm_vendor.name if model.llm_vendor else "Unknown",
            context_window=model.context_window,
            streamable=model.streamable,
            enabled=model.enabled,
            released_on=model.released_on.isoformat() if model.released_on else None,
            input_price=price.input_cost_per_token * 1_000_000 if price else None,
            output_price=price.output_cost_per_token * 1_000_000 if price else None,
            modalities=list({str(m.modality) for m in modalities}),
        )


def list_vendors() -> list[VendorListResult]:
    """List all LLM vendors with their model counts.

    Returns:
        List of VendorListResult sorted alphabetically by name.
    """
    from sqlmodel import func

    with Session(engine) as session:
        results = session.exec(
            select(
                LLMVendor.name,
                func.count(LargeLanguageModel.id).label("model_count"),
            )
            .join(LargeLanguageModel, isouter=True)
            .group_by(LLMVendor.id)
            .order_by(LLMVendor.name)
        ).all()

        return [
            VendorListResult(name=name, model_count=count) for name, count in results
        ]


def list_modalities() -> list[ModalityListResult]:
    """List all modalities with their model counts.

    Returns:
        List of ModalityListResult sorted alphabetically.
    """
    from sqlmodel import func

    with Session(engine) as session:
        results = session.exec(
            select(
                LLMModality.modality,
                func.count(func.distinct(LLMModality.llm_id)).label("model_count"),
            )
            .group_by(LLMModality.modality)
            .order_by(LLMModality.modality)
        ).all()

        return [
            ModalityListResult(modality=str(mod), model_count=count)
            for mod, count in results
        ]
