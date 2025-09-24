"""
AI service API router.

FastAPI router for AI chat endpoints implementing core chat functionality,
conversation management, and service status.
"""

from typing import Any

from app.core.config import settings
from app.services.ai.service import (
    AIService,
    AIServiceError,
    ConversationError,
    ProviderError,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ai", tags=["ai"])

# Initialize AI service
ai_service = AIService(settings)


# Request/Response models
class ChatRequest(BaseModel):
    """Request model for chat messages."""

    message: str
    conversation_id: str | None = None
    user_id: str = "api-user"


class ChatResponse(BaseModel):
    """Response model for chat messages."""

    message_id: str
    content: str
    conversation_id: str
    response_time_ms: float | None = None


class ConversationSummary(BaseModel):
    """Summary model for conversation listing."""

    id: str
    title: str | None
    message_count: int
    last_activity: str
    provider: str
    model: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a chat message and get AI response.

    Args:
        request: Chat request with message and optional conversation ID

    Returns:
        ChatResponse: AI response with conversation details

    Raises:
        HTTPException: If chat processing fails
    """
    try:
        response_message = await ai_service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
        )

        # Get updated conversation for metadata
        conversation_id = response_message.metadata.get("conversation_id")
        conversation = (
            ai_service.get_conversation(conversation_id) if conversation_id else None
        )
        response_time = None
        if conversation and "last_response_time_ms" in conversation.metadata:
            response_time = conversation.metadata["last_response_time_ms"]

        return ChatResponse(
            message_id=response_message.id,
            content=response_message.content,
            conversation_id=conversation.id if conversation else "unknown",
            response_time_ms=response_time,
        )

    except AIServiceError as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=f"AI provider error: {e}")
    except ConversationError as e:
        raise HTTPException(status_code=400, detail=f"Conversation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    user_id: str = "api-user", limit: int = 50
) -> list[ConversationSummary]:
    """
    List conversations for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of conversations to return

    Returns:
        List of conversation summaries
    """
    try:
        conversations = ai_service.list_conversations(user_id)[:limit]

        return [
            ConversationSummary(
                id=conv.id,
                title=conv.title,
                message_count=conv.get_message_count(),
                last_activity=conv.updated_at.isoformat(),
                provider=conv.provider.value,
                model=conv.model,
            )
            for conv in conversations
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list conversations: {e}"
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str, user_id: str = "api-user"
) -> dict[str, Any]:
    """
    Get a specific conversation with full message history.

    Args:
        conversation_id: The conversation identifier
        user_id: User identifier for access control

    Returns:
        Full conversation details with messages

    Raises:
        HTTPException: If conversation not found or access denied
    """
    try:
        conversation = ai_service.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Check access (basic user matching)
        if conversation.metadata.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "id": conversation.id,
            "title": conversation.title,
            "provider": conversation.provider.value,
            "model": conversation.model,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "message_count": conversation.get_message_count(),
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                for msg in conversation.messages
            ],
            "metadata": conversation.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {e}")


@router.get("/health")
async def ai_health() -> dict[str, Any]:
    """
    AI service health endpoint.

    Returns comprehensive health status including configuration,
    conversation count, and service availability.
    """
    try:
        status = ai_service.get_service_status()
        validation_errors = ai_service.validate_service()

        return {
            "service": "ai",
            "status": "healthy" if not validation_errors else "unhealthy",
            "enabled": status["enabled"],
            "provider": status["provider"],
            "model": status["model"],
            "agent_ready": status["agent_initialized"],
            "total_conversations": status["total_conversations"],
            "configuration_valid": status["configuration_valid"],
            "validation_errors": validation_errors,
        }

    except Exception as e:
        return {
            "service": "ai",
            "status": "error",
            "error": str(e),
        }


@router.get("/version")
async def ai_version() -> dict[str, Any]:
    """AI service version and feature information."""
    return {
        "service": "ai",
        "engine": "pydantic-ai",
        "version": "1.0",
        "features": [
            "chat",
            "conversation_management",
            "multi_provider_support",
            "health_monitoring",
            "api_endpoints",
            "cli_commands",
        ],
        "providers_supported": [
            "openai",
            "anthropic",
            "google",
            "groq",
            "mistral",
            "cohere",
        ],
    }
