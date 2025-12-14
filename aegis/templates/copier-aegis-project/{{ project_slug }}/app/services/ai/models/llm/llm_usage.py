"""LLM Usage model for tracking AI interactions."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .large_language_model import LargeLanguageModel


class LLMUsage(SQLModel, table=True):
    """
    Records every LLM call with token usage and calculated costs.

    The action field accepts any string value for flexibility -
    callers can define their own action types (e.g., "chat", "stream_chat",
    "completion", etc.).
    """

    __tablename__ = "llm_usage"

    id: int | None = Field(default=None, primary_key=True)
    llm_id: int = Field(foreign_key="large_language_model.id", index=True)
    user_id: str | None = Field(default=None, index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_cost: float = Field(ge=0)
    success: bool = Field(default=True)
    error_message: str | None = None
    action: str = Field(index=True)

    # Relationship
    llm: "LargeLanguageModel" = Relationship(back_populates="usages")
