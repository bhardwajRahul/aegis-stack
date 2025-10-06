"""
AI service core implementation using PydanticAI.

This module provides the main AIService class that handles AI chat functionality,
conversation management, and provider integration.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from app.core.log import logger

from .config import get_ai_config
from .conversation import ConversationManager
from .models import (
    Conversation,
    ConversationMessage,
    MessageRole,
    StreamingConversation,
    StreamingMessage,
)
from .providers import get_agent


class AIServiceError(Exception):
    """Base exception for AI service errors."""

    pass


class ProviderError(AIServiceError):
    """Exception raised when AI provider fails."""

    pass


class ConversationError(AIServiceError):
    """Exception raised when conversation management fails."""

    pass


class AIService:
    """
    Core AI service using PydanticAI for chat functionality.

    Handles chat completions, conversation management, and provider abstraction.
    Creates Agent instances per request for simplicity and resource efficiency.
    """

    def __init__(self, settings: Any):
        """Initialize AI service with configuration."""
        self.settings = settings
        self.config = get_ai_config(settings)
        self.conversation_manager = ConversationManager()

        # logger.info(
        #     f"AI service initialized - Provider: {self.config.provider}, "
        #     f"Enabled: {self.config.enabled}"
        # )

    async def chat(
        self, message: str, conversation_id: str | None = None, user_id: str = "default"
    ) -> ConversationMessage:
        """
        Send a chat message and get AI response.

        Args:
            message: The user's message
            conversation_id: Optional conversation ID (creates new if None)
            user_id: User identifier for conversation ownership

        Returns:
            ConversationMessage: The AI's response message

        Raises:
            AIServiceError: If service is disabled or not configured
            ProviderError: If AI provider fails
            ConversationError: If conversation management fails
        """
        if not self.config.enabled:
            raise AIServiceError("AI service is disabled")

        try:
            # Setup conversation and add user message
            conversation = self._setup_conversation(message, conversation_id, user_id)

            # Prepare agent and conversation context
            agent, conversation_context = self._prepare_agent_and_context(conversation)

            # Get AI response
            start_time = datetime.now(UTC)
            result = await agent.run(conversation_context)
            end_time = datetime.now(UTC)
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            # Add AI response to conversation
            ai_message = conversation.add_message(
                MessageRole.ASSISTANT, result.output, message_id=str(uuid.uuid4())
            )

            # Store conversation ID in message metadata for easy lookup
            ai_message.metadata["conversation_id"] = conversation.id

            # Finalize conversation (update metadata and save)
            self._finalize_conversation(conversation, response_time_ms)

            return ai_message

        except (ModelRetry, UnexpectedModelBehavior) as e:
            error_msg = f"AI provider error: {e}"
            logger.error(error_msg)
            raise ProviderError(error_msg) from e
        except Exception as e:
            error_msg = f"Chat processing failed: {e}"
            logger.error(error_msg)
            raise AIServiceError(error_msg) from e

    async def stream_chat(
        self,
        message: str,
        conversation_id: str | None = None,
        user_id: str = "default",
        stream_delta: bool = False,
    ) -> AsyncIterator[StreamingMessage]:
        """
        Stream a chat message with real-time response generation.

        Args:
            message: The user's message
            conversation_id: Optional conversation ID (creates new if None)
            user_id: User identifier for conversation ownership
            stream_delta: Whether to stream delta changes or full content

        Yields:
            StreamingMessage: Real-time message chunks

        Raises:
            AIServiceError: If service is disabled or not configured
            ProviderError: If AI provider fails
            ConversationError: If conversation management fails
        """
        if not self.config.enabled:
            raise AIServiceError("AI service is disabled")

        try:
            # Setup conversation and add user message
            conversation = self._setup_conversation(message, conversation_id, user_id)

            # Create streaming conversation wrapper
            streaming_conv = StreamingConversation(conversation=conversation)
            streaming_conv.reset_stream()

            # Prepare agent and conversation context
            agent, conversation_context = self._prepare_agent_and_context(conversation)

            # Start streaming
            start_time = datetime.now(UTC)

            # Generate a message ID for the streaming response
            message_id = str(uuid.uuid4())

            # Use PydanticAI's run_stream method for streaming
            async with agent.run_stream(conversation_context) as result:
                # Stream text chunks
                async for text_chunk in result.stream_text(delta=stream_delta):
                    # Accumulate content
                    total_content = streaming_conv.accumulate_content(
                        text_chunk, is_delta=stream_delta
                    )

                    # Yield streaming message chunk
                    yield StreamingMessage(
                        content=text_chunk if stream_delta else total_content,
                        is_final=False,
                        is_delta=stream_delta,
                        message_id=message_id,
                        conversation_id=conversation.id,
                        metadata={
                            "provider": self.config.provider,
                            "model": self.config.model,
                            "stream_delta": stream_delta,
                        },
                    )

            end_time = datetime.now(UTC)
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            # Add final message to conversation using accumulated streaming content
            final_content = streaming_conv.accumulated_content or "No content received"
            ai_message = conversation.add_message(
                MessageRole.ASSISTANT, final_content, message_id=message_id
            )

            # Store conversation metadata
            ai_message.metadata["conversation_id"] = conversation.id

            # Finalize conversation (update metadata and save)
            self._finalize_conversation(
                conversation, response_time_ms, is_streaming=True
            )

            # Yield final streaming message
            yield StreamingMessage(
                content=final_content,
                is_final=True,
                is_delta=False,
                message_id=message_id,
                conversation_id=conversation.id,
                metadata={
                    "provider": self.config.provider,
                    "model": self.config.model,
                    "response_time_ms": response_time_ms,
                    "stream_complete": True,
                },
            )

        except (ModelRetry, UnexpectedModelBehavior) as e:
            error_msg = f"AI provider streaming error: {e}"
            logger.error(error_msg)
            raise ProviderError(error_msg) from e
        except Exception as e:
            error_msg = f"Streaming failed: {e}"
            logger.error(error_msg)
            raise AIServiceError(error_msg) from e

    def _setup_conversation(
        self,
        message: str,
        conversation_id: str | None,
        user_id: str,
    ) -> Conversation:
        """
        Get or create conversation and add user message.

        Args:
            message: The user's message
            conversation_id: Optional conversation ID (creates new if None)
            user_id: User identifier for conversation ownership

        Returns:
            Conversation: The conversation with user message added

        Raises:
            ConversationError: If conversation_id provided but not found
        """
        # Get or create conversation
        if conversation_id:
            conversation = self.conversation_manager.get_conversation(conversation_id)
            if not conversation:
                raise ConversationError(f"Conversation {conversation_id} not found")
        else:
            conversation = self.conversation_manager.create_conversation(
                provider=self.config.provider,
                model=self.config.model,
                user_id=user_id,
            )

        # Add user message to conversation
        conversation.add_message(MessageRole.USER, message)

        return conversation

    def _prepare_agent_and_context(self, conversation: Conversation) -> tuple[Any, str]:
        """
        Create agent for request and build conversation context.

        Args:
            conversation: The conversation to prepare context from

        Returns:
            tuple[Any, str]: (agent instance, conversation context string)
        """
        # Create agent for this request
        agent = get_agent(self.config, self.settings)

        # Build conversation context for AI
        conversation_context = self._build_conversation_context(conversation)

        return agent, conversation_context

    def _finalize_conversation(
        self,
        conversation: Conversation,
        response_time_ms: float,
        is_streaming: bool = False,
    ) -> None:
        """
        Update conversation metadata and save.

        Args:
            conversation: The conversation to finalize
            response_time_ms: Response time in milliseconds
            is_streaming: Whether this was a streaming response
        """
        # Update conversation metadata
        metadata_update = {
            "last_response_time_ms": response_time_ms,
            "total_messages": conversation.get_message_count(),
            "last_activity": datetime.now(UTC).isoformat(),
        }

        if is_streaming:
            metadata_update["streaming"] = True

        conversation.metadata.update(metadata_update)

        # Save conversation
        self.conversation_manager.save_conversation(conversation)

    def _build_conversation_context(self, conversation: Conversation) -> str:
        """
        Build conversation context for AI from message history.

        Args:
            conversation: The conversation with message history

        Returns:
            str: Formatted conversation context for AI
        """
        if not conversation.messages:
            return ""

        # For continuous conversation, include recent message history
        # Limit to last 10 messages to manage context window
        recent_messages = conversation.messages[-10:]

        # Format messages for context
        context_parts = []
        for msg in recent_messages[:-1]:  # Exclude the latest message (just added)
            if msg.role == MessageRole.USER:
                context_parts.append(f"User: {msg.content}")
            elif msg.role == MessageRole.ASSISTANT:
                context_parts.append(f"Assistant: {msg.content}")

        # Add the current user message
        latest_message = conversation.get_last_message()
        if latest_message and latest_message.role == MessageRole.USER:
            if context_parts:
                # Include conversation history + current message
                return "\n".join(context_parts) + f"\n\nUser: {latest_message.content}"
            else:
                # First message in conversation
                return latest_message.content

        return ""

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self.conversation_manager.get_conversation(conversation_id)

    def list_conversations(self, user_id: str = "default") -> list[Conversation]:
        """List all conversations for a user."""
        return self.conversation_manager.list_conversations(user_id)

    def get_service_status(self) -> dict[str, Any]:
        """Get current service status and metrics."""
        total_conversations = len(self.conversation_manager.conversations)

        return {
            "enabled": self.config.enabled,
            "provider": self.config.provider,
            "model": self.config.model,
            "agent_initialized": True,  # Agents created per request, always available
            "total_conversations": total_conversations,
            "configuration_valid": len(
                self.config.validate_configuration(self.settings)
            )
            == 0,
        }

    def validate_service(self) -> list[str]:
        """Validate service configuration and return any issues."""
        errors = []

        # Check configuration
        config_errors = self.config.validate_configuration(self.settings)
        errors.extend(config_errors)

        # Check agent initialization (agents created per request,
        # always available when enabled)
        # No persistent agent check needed in agent-per-request pattern

        return errors
