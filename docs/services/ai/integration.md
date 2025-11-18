# AI Service Layer

How the AI service works internally and basic usage in your code.

## AIService Class

**Location:** `app/services/ai/service.py`

Basic usage:

```python
import asyncio
from app.core.config import settings
from app.services.ai.service import AIService

async def main():
    ai_service = AIService(settings)

    # Send message (creates new conversation)
    print("=" * 60)
    print("Question 1: Explain FastAPI")
    print("=" * 60)
    response = await ai_service.chat(
        message="Explain FastAPI",
        user_id="my-user"
    )
    print(response.content)

    # Continue conversation using ID from response metadata
    print("\n" + "=" * 60)
    print("Question 2: Show me an example (same conversation)")
    print("=" * 60)
    conversation_id = response.metadata["conversation_id"]
    response2 = await ai_service.chat(
        message="Show me an example",
        conversation_id=conversation_id,
        user_id="my-user"
    )
    print(response2.content)

    # Stream response (creates new conversation)
    print("\n" + "=" * 60)
    print("Question 3: Hello (streaming, new conversation)")
    print("=" * 60)
    async for chunk in ai_service.stream_chat(message="Hello", user_id="my-user"):
        print(chunk.content, end='', flush=True)
    print()  # Newline after stream

    # Get conversation by ID
    print("\n" + "=" * 60)
    print("Conversation Statistics")
    print("=" * 60)
    conversation = ai_service.get_conversation(conversation_id)
    print(f"Conversation {conversation_id[:8]}... has {len(conversation.messages)} messages")

    # List all conversations for a user
    conversations = ai_service.list_conversations(user_id="my-user")
    print(f"User 'my-user' has {len(conversations)} total conversations")

# Run the async function
asyncio.run(main())
```

## Configuration

**Location:** `app/services/ai/config.py`

```python
from app.services.ai.config import get_ai_config

config = get_ai_config(settings)

# Check configuration
errors = config.validate_configuration(settings)
if errors:
    print(f"Config issues: {errors}")

# Get available providers
available = config.get_available_providers(settings)
```

## Conversation Management

**Location:** `app/services/ai/conversation.py`

Conversations are stored in memory and reset on restart.

```python
from app.services.ai.conversation import ConversationManager

manager = ConversationManager()

# Conversations are created automatically by AIService
# Access them via AIService methods:
conversation = ai_service.get_conversation(conv_id)
conversations = ai_service.list_conversations(user_id="user-123")
```

!!! example "Musings: Persistent Storage Coming (October 2025)"
    Right now conversations are in-memory and reset on restart. That's intentional for v0.1.0 - keeps things simple while I focus on getting the core experience right.

    Database-backed storage is definitely planned. The architecture's pretty straightforward: "If database component detected, store conversations there." The design is solid, I just need to think through some things.

    In the meantime, anyone who knows what they're doing can easily modify ConversationManager to add their own datastore.

## Provider Capabilities

**Location:** `app/services/ai/models.py`

```python
from app.services.ai.models import (
    AIProvider,
    get_provider_capabilities,
    get_free_providers
)

# Check what a provider supports
caps = get_provider_capabilities(AIProvider.GROQ)
print(f"Streaming: {caps.supports_streaming}")
print(f"Free tier: {caps.free_tier_available}")

# Get free providers
free = get_free_providers()
# [AIProvider.PUBLIC, AIProvider.GROQ, AIProvider.GOOGLE, AIProvider.COHERE]
```

## Health Monitoring

**Location:** `app/services/ai/health.py`

```python
from app.services.ai.health import check_ai_service_health

status = await check_ai_service_health()
print(f"Status: {status.status}")  # HEALTHY, DEGRADED, or UNHEALTHY
```

---

**Next Steps:**

- **[API Reference](api.md)** - REST API endpoints
- **[CLI Commands](cli.md)** - Command-line interface
- **[Examples](examples.md)** - Usage examples
