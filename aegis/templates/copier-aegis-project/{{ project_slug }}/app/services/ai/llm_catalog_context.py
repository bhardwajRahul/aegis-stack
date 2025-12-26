"""
LLM catalog context for AI prompt injection.

Provides Illiana with awareness of available LLM models, their pricing,
and capabilities for informed model selection discussions.
"""

from dataclasses import dataclass

from app.services.ai.models.llm import (
    Direction,
    LargeLanguageModel,
    LLMDeployment,
    LLMModality,
    LLMPrice,
    LLMVendor,
    Modality,
)
from sqlmodel import Session, select

# Flagship models to show per vendor (ordered by preference)
# Each entry: vendor_name -> list of model_id patterns to match
FLAGSHIP_MODELS: dict[str, list[str]] = {
    "openai": ["gpt-4o"],
    "anthropic": ["claude-3-5-sonnet", "claude-3.5-sonnet"],
    "google": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
    "xai": ["grok-4", "grok-2", "grok-beta"],
    "mistral": ["mistral-large-latest", "mistral-large"],
    "groq": ["llama-3.3-70b", "llama-3.1-70b"],  # Groq for fast Llama inference
}


@dataclass
class FlagshipModel:
    """A flagship model from a vendor with key metrics."""

    vendor: str
    model_id: str
    title: str
    input_cost_per_m: float
    output_cost_per_m: float
    context_window: int
    function_calling: bool
    vision: bool
    structured_output: bool


class LLMCatalogContext:
    """
    Context for LLM catalog injection into AI prompts.

    Provides a curated view of flagship models from key vendors,
    formatted compactly for prompt injection.
    """

    def __init__(self, flagships: list[FlagshipModel]) -> None:
        """Initialize with list of flagship models."""
        self.flagships = flagships

    @classmethod
    def build(cls, session: Session) -> "LLMCatalogContext":
        """
        Build catalog context from database.

        Args:
            session: Database session for queries.

        Returns:
            LLMCatalogContext with flagship models from each vendor.
        """
        flagships: list[FlagshipModel] = []
        for vendor_name, model_patterns in FLAGSHIP_MODELS.items():
            model = cls._find_flagship(session, vendor_name, model_patterns)
            if model:
                flagships.append(model)
        return cls(flagships)

    @classmethod
    def _find_flagship(
        cls, session: Session, vendor_name: str, patterns: list[str]
    ) -> FlagshipModel | None:
        """
        Find the first matching flagship model for a vendor.

        Args:
            session: Database session.
            vendor_name: Vendor to search.
            patterns: Model ID patterns to match, in order of preference.

        Returns:
            FlagshipModel if found, None otherwise.
        """
        # Find vendor
        vendor = session.exec(
            select(LLMVendor).where(LLMVendor.name == vendor_name)
        ).first()
        if not vendor:
            return None

        # Try each pattern until we find a match
        for pattern in patterns:
            model = session.exec(
                select(LargeLanguageModel)
                .where(LargeLanguageModel.model_id.contains(pattern))
                .where(LargeLanguageModel.llm_vendor_id == vendor.id)
            ).first()

            if model:
                # Get pricing
                price = session.exec(
                    select(LLMPrice).where(LLMPrice.llm_id == model.id)
                ).first()

                # Get deployment capabilities
                deployment = session.exec(
                    select(LLMDeployment).where(LLMDeployment.llm_id == model.id)
                ).first()

                # Check for vision capability
                has_vision = cls._has_vision(session, model.id)

                return FlagshipModel(
                    vendor=vendor_name,
                    model_id=model.model_id,
                    title=model.title or model.model_id,
                    input_cost_per_m=(
                        (price.input_cost_per_token * 1_000_000) if price else 0.0
                    ),
                    output_cost_per_m=(
                        (price.output_cost_per_token * 1_000_000) if price else 0.0
                    ),
                    context_window=model.context_window or 0,
                    function_calling=(
                        deployment.function_calling if deployment else False
                    ),
                    vision=has_vision,
                    structured_output=(
                        deployment.structured_output if deployment else False
                    ),
                )

        return None

    @classmethod
    def _has_vision(cls, session: Session, model_id: int | None) -> bool:
        """
        Check if model has vision/image input capability.

        Args:
            session: Database session.
            model_id: Model database ID.

        Returns:
            True if model accepts image input.
        """
        if not model_id:
            return False

        modality = session.exec(
            select(LLMModality).where(
                LLMModality.llm_id == model_id,
                LLMModality.modality == Modality.IMAGE,
                LLMModality.direction == Direction.INPUT,
            )
        ).first()

        return modality is not None

    def format_for_prompt(self) -> str:
        """
        Format catalog data for prompt injection.

        Returns:
            Compact markdown string showing flagship models.
        """
        if not self.flagships:
            return ""

        lines = ["LLM Catalog (Flagship Models):"]
        for m in self.flagships:
            # Build capabilities list
            caps: list[str] = []
            if m.function_calling:
                caps.append("functions")
            if m.vision:
                caps.append("vision")
            if m.structured_output:
                caps.append("structured")
            caps_str = ", ".join(caps) if caps else "basic"

            # Format context window
            if m.context_window >= 1_000_000:
                ctx_str = f"{m.context_window // 1_000_000}M"
            elif m.context_window >= 1000:
                ctx_str = f"{m.context_window // 1000}K"
            else:
                ctx_str = str(m.context_window)

            # Format line
            lines.append(
                f"  {m.vendor.title()}: {m.title} | "
                f"${m.input_cost_per_m:.2f}/${m.output_cost_per_m:.2f} per M | "
                f"{ctx_str} ctx | {caps_str}"
            )

        return "\n".join(lines)


def get_llm_catalog_context(session: Session) -> str:
    """
    Get formatted LLM catalog context for prompt injection.

    Convenience function for building and formatting catalog context.

    Args:
        session: Database session.

    Returns:
        Formatted string for prompt injection, or empty string if no data.
    """
    context = LLMCatalogContext.build(session)
    return context.format_for_prompt()


__all__ = ["FlagshipModel", "LLMCatalogContext", "get_llm_catalog_context"]
