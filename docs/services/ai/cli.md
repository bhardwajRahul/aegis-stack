# AI CLI Commands

**Part of the Generated Project CLI** - See [CLI Reference](../../cli-reference.md#service-clis) for complete overview.

Command-line interface for the AI service.

## Command Overview

All commands use the pattern: `<project-name> ai <command>`

```bash
my-app ai status          # Show configuration and validation
my-app ai providers       # List all providers
my-app ai chat "message"  # Send single message
my-app ai chat            # Interactive chat session
my-app ai conversations   # List conversations
my-app ai history <id>    # View conversation history
```

## Status Command

Show AI service status, configuration, and validation:

```bash
my-app ai status
```

**Output:**

```
AI Service Status
========================================
Engine: pydantic-ai
Status: Enabled
Provider: groq
Model: llama-3.1-70b-versatile
Temperature: 0.7
Max Tokens: 1000
API Key: Set

✓ Configuration valid
  Free tier
  Streaming supported

Available providers: 3 (run 'ai providers' to list)
```

**What it shows:**

- Engine (pydantic-ai or langchain)
- Enabled/Disabled status
- Current provider and model
- Temperature and max tokens settings
- API key status
- Validation errors (if any)
- Provider capabilities (free tier, streaming)
- Available providers count

## Providers Command

List all available AI providers and their status:

```bash
my-app ai providers
```

**Output:**

```
           AI Providers
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Provider ┃ Status                   ┃ Free ┃ Features         ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ public   │ Available (current)      │ Yes  │ Basic            │
│ groq     │ Need GROQ_API_KEY        │ Yes  │ Stream           │
│ openai   │ Need OPENAI_API_KEY      │ No   │ Stream, Functions│
│ anthropic│ Need ANTHROPIC_API_KEY   │ No   │ Stream, Vision   │
│ google   │ Need GOOGLE_API_KEY      │ Yes  │ Stream           │
│ mistral  │ Need MISTRAL_API_KEY     │ No   │ Stream           │
│ cohere   │ Need COHERE_API_KEY      │ No   │ Stream           │
└──────────┴──────────────────────────┴──────┴──────────────────┘
```

## Chat Command

Send messages to the AI or start interactive sessions.

### Single Message Mode

Send a single message and get a response:

```bash
my-app ai chat "What is FastAPI?"
```

**Options:**

- `--stream / --no-stream` - Enable/disable streaming (default: enabled)
- `--conversation-id, -c` - Continue an existing conversation
- `--user-id, -u` - User identifier (default: cli-user)
- `--verbose, -v` - Show conversation metadata

**Examples:**

```bash
# Simple message
my-app ai chat "Explain async/await in Python"

# Disable streaming
my-app ai chat "Quick question" --no-stream

# Continue a conversation
my-app ai chat -c abc123 "Tell me more about that"

# Custom user ID with verbose output
my-app ai chat "Hello" -u "user-456" --verbose
```

### Interactive Mode

Start an interactive chat session (no message argument):

```bash
my-app ai chat
```

**Features:**

- Conversation memory (context maintained during session)
- Markdown rendering
- Streaming responses (when supported)
- Type `exit`, `quit`, `bye`, or `Ctrl+C` to quit

**Example:**

```bash
$ my-app ai chat
┌────────────────────────────────────────────────────┐
│ AI Chat Session                                    │
│ Provider: groq | Model: llama-3.1-70b-versatile    │
│ Type 'exit', 'quit', 'bye' or press Ctrl+C to end  │
└────────────────────────────────────────────────────┘

You: What is FastAPI?
> FastAPI is a modern Python web framework...

You: Show me an example
> Here's a simple FastAPI example...

You: exit
Goodbye!
```

## Conversations Command

List conversations for a user:

```bash
my-app ai conversations
```

**Options:**

- `--user-id, -u` - User identifier (default: cli-user)
- `--limit, -l` - Number of conversations to show (default: 10)

**Output:**

```
Conversations for cli-user:

• abc12345... - FastAPI Discussion
  5 messages | 2024-01-15 14:30

• def67890... - Python Async Patterns
  12 messages | 2024-01-14 09:15
```

## History Command

View the message history of a conversation:

```bash
my-app ai history <conversation-id>
```

**Options:**

- `--user-id, -u` - User identifier (default: cli-user)

**Example:**

```bash
my-app ai history abc12345
```

**Output:**

```
Conversation: abc12345
Title: FastAPI Discussion
Provider: groq
Messages: 5

👤 [14:30:15] What is FastAPI?

🤖 [14:30:18] FastAPI is a modern, fast web framework...

👤 [14:31:02] How does dependency injection work?

🤖 [14:31:05] FastAPI uses a powerful dependency injection system...
```

---

## See Also

- **[CLI Reference](../../cli-reference.md)** - Complete CLI overview and all commands
- **[AI Service Documentation](index.md)** - Main AI service documentation
- **[Providers Guide](providers.md)** - Provider setup and configuration
- **[API Reference](api.md)** - REST API documentation
- **[Service Layer](integration.md)** - Using AI service in code
