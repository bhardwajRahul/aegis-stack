"""Large Language Model catalog model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .llm_deployment import LLMDeployment
    from .llm_modality import LLMModality
    from .llm_price import LLMPrice
    from .llm_vendor import LLMVendor


class LargeLanguageModel(SQLModel, table=True):
    """
    Represents an LLM model in the catalog (e.g., gpt-4o, claude-3-5-sonnet).

    Stores model metadata including capabilities and configuration.
    """

    __tablename__ = "large_language_model"

    id: int | None = Field(default=None, primary_key=True)
    model_id: str = Field(unique=True, index=True)
    title: str
    description: str = Field(default="")
    context_window: int = Field(default=4096, gt=0)
    training_data: str = Field(default="")
    streamable: bool = Field(default=True)
    enabled: bool = Field(default=True)
    color: str = Field(default="#6B7280")
    icon_path: str = Field(default="")
    license: str | None = None
    source_url: str | None = None
    released_on: datetime | None = None
    family: str | None = None

    # Foreign key
    llm_vendor_id: int | None = Field(
        default=None, foreign_key="llm_vendor.id", index=True
    )

    # Relationships
    llm_vendor: "LLMVendor" = Relationship(back_populates="llms")
    modalities: list["LLMModality"] = Relationship(back_populates="llm")
    llm_prices: list["LLMPrice"] = Relationship(back_populates="llm")
    deployments: list["LLMDeployment"] = Relationship(back_populates="llm")

    def __repr__(self) -> str:
        return f"<LargeLanguageModel title={self.title} model_id={self.model_id}>"
