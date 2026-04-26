"""LLM Vendor model for tracking AI providers."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .large_language_model import LargeLanguageModel
    from .llm_deployment import LLMDeployment
    from .llm_price import LLMPrice


class LLMVendor(SQLModel, table=True):
    """
    Represents an LLM provider/vendor (e.g., OpenAI, Anthropic, Groq).

    Stores vendor metadata including API configuration and UI styling.
    """

    __tablename__ = "llm_vendor"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str | None = None
    color: str = Field(default="#6B7280")
    icon_path: str = Field(default="")
    api_base: str | None = None
    auth_method: str = Field(default="api-key")

    # Relationships
    llms: list["LargeLanguageModel"] = Relationship(back_populates="llm_vendor")
    llm_prices: list["LLMPrice"] = Relationship(back_populates="llm_vendor")
    deployments: list["LLMDeployment"] = Relationship(back_populates="llm_vendor")
