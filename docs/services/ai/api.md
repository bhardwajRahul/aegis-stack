# AI Service API Reference

Complete REST API documentation for AI service endpoints.

## Base URL

All AI endpoints are prefixed with `/ai`:

```
http://localhost:8000/ai
```

## Endpoints Overview

<div class="grid cards" markdown>

-   :material-message-text: **POST `/ai/chat`**

    ---

    Send chat message and receive AI response

    [:octicons-arrow-right-24: Details](#post-aichat)

-   :material-broadcast: **POST `/ai/chat/stream`**

    ---

    Stream AI responses with Server-Sent Events

    [:octicons-arrow-right-24: Details](#post-aichatstream)

-   :material-format-list-bulleted: **GET `/ai/conversations`**

    ---

    List user conversations with metadata

    [:octicons-arrow-right-24: Details](#get-aiconversations)

-   :material-message-reply-text: **GET `/ai/conversations/{id}`**

    ---

    Get conversation with full message history

    [:octicons-arrow-right-24: Details](#get-aiconversationsconversation_id)

-   :material-heart-pulse: **GET `/ai/health`**

    ---

    Check AI service health status

    [:octicons-arrow-right-24: Details](#get-aihealth)

-   :material-information: **GET `/ai/version`**

    ---

    Get service version and capabilities

    [:octicons-arrow-right-24: Details](#get-aiversion)

</div>

## Chat Endpoints

### POST `/ai/chat`

Send a chat message and receive AI response.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ Yes | User's chat message |
| `conversation_id` | string \| null | ❌ No | Existing conversation ID (creates new if null) |
| `user_id` | string | ❌ No | User identifier (default: "api-user") |

**Response:**

```json title="Response Schema"
{
  "message_id": "uuid",
  "content": "AI response text",
  "conversation_id": "uuid",
  "response_time_ms": 1234.5
}
```

**Examples:**

=== "cURL"

    ```bash
    curl -X POST http://localhost:8000/ai/chat \
      -H "Content-Type: application/json" \
      -d '{
        "message": "Explain FastAPI in one sentence",
        "user_id": "my-user"
      }'
    ```

=== "Python"

    ```python title="Basic Chat Request" hl_lines="3-8"
    import httpx

    response = httpx.post(  # (1)!
        "http://localhost:8000/ai/chat",
        json={
            "message": "What is async/await in Python?",  # (2)!
            "user_id": "my-user"  # (3)!
        }
    )

    data = response.json()
    print(f"AI: {data['content']}")  # (4)!
    print(f"Conversation: {data['conversation_id']}")  # (5)!
    ```

    1.  POST request to the chat endpoint
    2.  The user's message - this is what gets sent to the AI
    3.  User identifier for conversation tracking (optional, defaults to "api-user")
    4.  Extract and print the AI's response text
    5.  Save this conversation_id to continue the conversation in future requests

=== "JavaScript"

    ```javascript title="Fetch API Example"
    const response = await fetch('http://localhost:8000/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'How do I handle errors in async functions?',
        user_id: 'web-user'
      })
    });

    const data = await response.json();
    console.log(`AI: ${data.content}`);
    ```

**Continue Conversation:**

```bash
# First message
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is FastAPI?"}' \
  | jq -r '.conversation_id' > conv_id.txt

# Follow-up message (maintains context)
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Can you show me an example?\",
    \"conversation_id\": \"$(cat conv_id.txt)\"
  }"
```

### POST `/ai/chat/stream`

Stream chat response with Server-Sent Events (SSE).

**Request Body:**

Same as `/ai/chat`:

```json
{
  "message": "string",
  "conversation_id": "string | null",
  "user_id": "string"
}
```

**Response:**

Server-Sent Events stream with the following event types:

**Event: `connect`**
```
event: connect
data: {"status": "connected", "message": "Streaming started"}
```

**Event: `chunk`** (repeated for each content chunk)
```
event: chunk
data: {
  "content": "text delta",
  "is_final": false,
  "is_delta": true,
  "message_id": "uuid",
  "conversation_id": "uuid",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Event: `final`**
```
event: final
data: {
  "content": "complete response",
  "is_final": true,
  "is_delta": false,
  "message_id": "uuid",
  "conversation_id": "uuid",
  "timestamp": "2024-01-15T10:30:05Z",
  "response_time_ms": 1234.5,
  "provider": "groq",
  "model": "llama-3.1-70b-versatile"
}
```

**Event: `complete`**
```
event: complete
data: {"status": "completed", "message": "Stream finished"}
```

**Event: `error`** (on error)
```
event: error
data: {"error": "AI service error", "detail": "error message"}
```

**Examples:**

=== "cURL"

    ```bash
    curl -X POST http://localhost:8000/ai/chat/stream \
      -H "Content-Type: application/json" \
      -d '{"message": "Write a Python hello world"}' \
      --no-buffer
    ```

=== "JavaScript"

    ```javascript title="SSE Streaming Client" hl_lines="10-13"
    const eventSource = new EventSource(  // (1)!
      '/ai/chat/stream?' + new URLSearchParams({
        message: 'Explain async programming',
        user_id: 'web-user'
      })
    );

    let fullResponse = '';

    eventSource.addEventListener('chunk', (e) => {  // (2)!
      const data = JSON.parse(e.data);
      fullResponse += data.content;
      updateUI(fullResponse);  // (3)!
    });

    eventSource.addEventListener('final', (e) => {  // (4)!
      const data = JSON.parse(e.data);
      console.log('Complete response:', data.content);
      console.log('Response time:', data.response_time_ms);
    });

    eventSource.addEventListener('error', (e) => {  // (5)!
      const data = JSON.parse(e.data);
      console.error('Error:', data.detail);
      eventSource.close();
    });

    eventSource.addEventListener('complete', (e) => {  // (6)!
      console.log('Stream complete');
      eventSource.close();
    });
    ```

    1.  Create EventSource connection to the streaming endpoint
    2.  Handle each streamed chunk as it arrives
    3.  Update UI in real-time as tokens stream in
    4.  Handle final event with complete response and timing
    5.  Handle errors and close connection
    6.  Clean up connection when stream completes

=== "Python"

    ```python title="httpx Streaming" hl_lines="6-9"
    import httpx
    import json

    url = "http://localhost:8000/ai/chat/stream"
    data = {"message": "Explain decorators in Python", "user_id": "my-user"}

    with httpx.stream("POST", url, json=data) as response:  # (1)!
        for line in response.iter_lines():  # (2)!
            if line.startswith('event:'):
                event_type = line.split(':')[1].strip()
            elif line.startswith('data:'):
                data = json.loads(line.split('data:')[1])

                if event_type == 'chunk':  # (3)!
                    print(data['content'], end='', flush=True)
                elif event_type == 'final':  # (4)!
                    print(f"\n\nResponse time: {data['response_time_ms']}ms")
    ```

    1.  Open streaming connection with context manager
    2.  Iterate through Server-Sent Events line by line
    3.  Print each chunk as it arrives for real-time output
    4.  Show final response metadata when stream completes

## Conversation Management

### GET `/ai/conversations`

List conversations for a user.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_id` | string | ❌ No | "api-user" | User identifier |
| `limit` | integer | ❌ No | 50 | Maximum conversations to return |

**Response:**

```json
[
  {
    "id": "uuid",
    "title": "Conversation title",
    "message_count": 5,
    "last_activity": "2024-01-15T10:30:00Z",
    "provider": "groq",
    "model": "llama-3.1-70b-versatile"
  }
]
```

**Example:**

```bash
# List conversations
curl "http://localhost:8000/ai/conversations?user_id=my-user&limit=10"

# With Python
import httpx

response = httpx.get(
    "http://localhost:8000/ai/conversations",
    params={"user_id": "my-user", "limit": 10}
)

conversations = response.json()
for conv in conversations:
    print(f"{conv['id']}: {conv['title']} ({conv['message_count']} messages)")
```

### GET `/ai/conversations/{conversation_id}`

Get a specific conversation with full message history.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `conversation_id` | string | Conversation UUID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_id` | string | ❌ No | "api-user" | User identifier for access control |

**Response:**

```json
{
  "id": "uuid",
  "title": "Conversation title",
  "provider": "groq",
  "model": "llama-3.1-70b-versatile",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "message_count": 5,
  "messages": [
    {
      "id": "msg-uuid-1",
      "role": "user",
      "content": "What is FastAPI?",
      "timestamp": "2024-01-15T10:00:00Z"
    },
    {
      "id": "msg-uuid-2",
      "role": "assistant",
      "content": "FastAPI is a modern web framework...",
      "timestamp": "2024-01-15T10:00:02Z"
    }
  ],
  "metadata": {
    "user_id": "my-user",
    "last_response_time_ms": 1234.5
  }
}
```

**Example:**

```bash
curl "http://localhost:8000/ai/conversations/CONVERSATION_ID?user_id=my-user"
```

## Service Status

### GET `/ai/health`

AI service health status and configuration.

**Response:**

```json
{
  "service": "ai",
  "status": "healthy",
  "enabled": true,
  "provider": "groq",
  "model": "llama-3.1-70b-versatile",
  "agent_ready": true,
  "total_conversations": 42,
  "configuration_valid": true,
  "validation_errors": []
}
```

**Status Values:**
- `healthy` - Service operational and properly configured
- `unhealthy` - Configuration issues or service errors
- `error` - Critical service failure

**Example:**

```bash
curl http://localhost:8000/ai/health | jq
```

### GET `/ai/version`

Service version and feature information.

**Response:**

```json
{
  "service": "ai",
  "engine": "pydantic-ai",
  "version": "1.0",
  "features": [
    "chat",
    "conversation_management",
    "multi_provider_support",
    "health_monitoring",
    "api_endpoints",
    "cli_commands"
  ],
  "providers_supported": [
    "openai",
    "anthropic",
    "google",
    "groq",
    "mistral",
    "cohere"
  ]
}
```

**Example:**

```bash
curl http://localhost:8000/ai/version | jq
```

## Error Handling

### HTTP Status Codes

| Status | Description |
|--------|-------------|
| 200 | Success |
| 400 | Bad request (invalid conversation_id, missing required fields) |
| 403 | Forbidden (conversation access denied) |
| 404 | Not found (conversation doesn't exist) |
| 502 | Bad gateway (AI provider error) |
| 503 | Service unavailable (AI service disabled or misconfigured) |
| 500 | Internal server error |

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

### Common Errors

**AI Service Disabled:**
```json
{
  "detail": "AI service error: AI service is disabled"
}
```

**Missing API Key:**
```json
{
  "detail": "AI service error: Missing API key for openai provider. Set OPENAI_API_KEY environment variable."
}
```

**Provider Error:**
```json
{
  "detail": "AI provider error: Rate limit exceeded"
}
```

**Conversation Not Found:**
```json
{
  "detail": "Conversation error: Conversation abc-123 not found"
}
```

**Access Denied:**
```json
{
  "detail": "Access denied"
}
```

---

**Next Steps:**

- **[Service Layer](integration.md)** - Integration patterns and architecture
- **[CLI Commands](cli.md)** - Command-line interface reference
- **[Examples](examples.md)** - Real-world usage patterns
