"""
AI conversation management.

In-memory conversation storage and management for AI chat sessions.
This provides conversation persistence during application runtime.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.log import logger

from .models import AIProvider, Conversation


class ConversationManager:
    """
    Manages AI conversations in memory.

    This is a simple in-memory implementation. In production, you might want
    to use a database or external storage for persistence across restarts.
    """

    def __init__(self):
        """Initialize conversation manager with empty storage."""
        self.conversations: dict[str, Conversation] = {}
        logger.info("Conversation manager initialized")

    def create_conversation(
        self,
        provider: AIProvider,
        model: str,
        user_id: str = "default",
        conversation_id: str | None = None,
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            provider: AI provider being used
            model: Model name
            user_id: User identifier
            conversation_id: Optional custom conversation ID

        Returns:
            Conversation: The created conversation
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        conversation = Conversation(
            id=conversation_id,
            provider=provider,
            model=model,
            metadata={"user_id": user_id, "created_by": "ai_service"},
        )

        self.conversations[conversation_id] = conversation
        logger.debug(f"Created conversation {conversation_id} for user {user_id}")

        return conversation

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """
        Get a conversation by ID.

        Args:
            conversation_id: The conversation identifier

        Returns:
            Conversation | None: The conversation if found, None otherwise
        """
        return self.conversations.get(conversation_id)

    def save_conversation(self, conversation: Conversation) -> None:
        """
        Save a conversation (update in memory storage).

        Args:
            conversation: The conversation to save
        """
        conversation.updated_at = datetime.now(UTC)
        self.conversations[conversation.id] = conversation
        logger.debug(f"Saved conversation {conversation.id}")

    def list_conversations(self, user_id: str | None = None) -> list[Conversation]:
        """
        List conversations, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            list[Conversation]: List of conversations
        """
        conversations = list(self.conversations.values())

        if user_id:
            conversations = [
                conv
                for conv in conversations
                if conv.metadata.get("user_id") == user_id
            ]

        # Sort by most recent activity
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: The conversation identifier

        Returns:
            bool: True if conversation was deleted, False if not found
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.debug(f"Deleted conversation {conversation_id}")
            return True
        return False

    def get_conversation_count(self, user_id: str | None = None) -> int:
        """
        Get count of conversations.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            int: Number of conversations
        """
        if user_id:
            return len(
                [
                    conv
                    for conv in self.conversations.values()
                    if conv.metadata.get("user_id") == user_id
                ]
            )
        return len(self.conversations)

    def get_recent_conversations(
        self, limit: int = 10, user_id: str | None = None
    ) -> list[Conversation]:
        """
        Get recent conversations.

        Args:
            limit: Maximum number of conversations to return
            user_id: Optional user ID to filter by

        Returns:
            list[Conversation]: Recent conversations
        """
        conversations = self.list_conversations(user_id)
        return conversations[:limit]

    def cleanup_old_conversations(self, max_age_hours: int = 24) -> int:
        """
        Clean up old conversations.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            int: Number of conversations cleaned up
        """
        cutoff_time = datetime.now(UTC).timestamp() - (max_age_hours * 3600)
        to_delete = []

        for conv_id, conversation in self.conversations.items():
            if conversation.updated_at.timestamp() < cutoff_time:
                to_delete.append(conv_id)

        for conv_id in to_delete:
            del self.conversations[conv_id]

        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old conversations")

        return len(to_delete)

    def get_stats(self) -> dict[str, Any]:
        """
        Get conversation manager statistics.

        Returns:
            dict: Statistics about conversations
        """
        total_conversations = len(self.conversations)
        total_messages = sum(
            conv.get_message_count() for conv in self.conversations.values()
        )

        # Get user breakdown
        users = set()
        for conv in self.conversations.values():
            user_id = conv.metadata.get("user_id")
            if user_id:
                users.add(user_id)

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "unique_users": len(users),
            "average_messages_per_conversation": (
                total_messages / total_conversations if total_conversations > 0 else 0
            ),
        }
