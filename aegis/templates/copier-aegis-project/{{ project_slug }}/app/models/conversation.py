"""
SQLModel table definitions for AI conversation persistence.

These tables store conversation history in the project database.
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    """AI conversation table."""

    __tablename__ = "conversation"

    id: str = Field(primary_key=True, description="Conversation UUID")
    title: str | None = Field(
        default=None, description="Auto-generated conversation title"
    )
    provider: str = Field(
        index=True, description="AI provider (openai, anthropic, etc)"
    )
    model: str = Field(description="Model name")
    user_id: str = Field(index=True, description="User who owns this conversation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata_json: str | None = Field(default=None, description="JSON metadata")


class Message(SQLModel, table=True):
    """AI message table."""

    __tablename__ = "message"

    id: str = Field(primary_key=True, description="Message UUID")
    conversation_id: str = Field(
        foreign_key="conversation.id",
        index=True,
        description="Parent conversation ID",
    )
    role: str = Field(description="Message role: user, assistant, system")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata_json: str | None = Field(default=None, description="JSON metadata")
