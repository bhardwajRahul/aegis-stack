# AI CLI Commands

Command-line interface for the AI service.

## Command Overview

All commands use the pattern: `<project-name> ai <command>`

```bash
my-app ai chat                  # Interactive chat session
my-app ai chat send "message"   # Send single message
my-app ai config show           # Show configuration
my-app ai config validate       # Validate setup
my-app ai providers list        # List providers
my-app ai version               # Show version
```

## Chat Commands

### Interactive Chat

Start an interactive chat session with conversation memory:

```bash
my-app ai chat
```

**Features:**

- Conversation memory (context maintained during session only)
- Markdown rendering
- Streaming responses (when supported)
- Type `exit`, `quit`, or `Ctrl+C` to quit

**Example:**


```bash
$ my-app ai chat
🤖 AI Chat Session
Provider: groq | Model: llama-3.1-70b-versatile
Type 'exit', 'quit', 'bye' or press Ctrl+C to end session

You: What is FastAPI?
🤖: FastAPI is a modern Python web framework...

You: Show me an example
🤖: Here's a simple FastAPI example...

You: exit
👋 Goodbye!
```

### Send Message

Send a single message:

```bash
my-app ai chat send "Your message here"
```

**Options:**

- `--stream / --no-stream` - Enable/disable streaming
- `--user-id ID` or `-u ID` - Set user identifier

**Examples:**

```bash
# Simple message
my-app ai chat send "Explain async/await"

# Disable streaming
my-app ai chat send "Quick question" --no-stream

# Custom user ID
my-app ai chat send "Hello" -u "user-456"
```

## Configuration Commands

### Show Configuration

Display current AI service configuration:

```bash
my-app ai config show
```

**Output:**

```
🔧 AI Service Configuration
========================================
Enabled: True
Provider: groq
Model: llama-3.1-70b-versatile
Temperature: 0.7
Max Tokens: 1000
Timeout: 30.0s

🔐 Provider Configuration (groq):
API Key: ✅ Set

✅ Available Providers (3):
  • public
  • groq
  • google
```

### Validate Configuration

Check if configuration is valid:

```bash
my-app ai config validate
```

**Success:**

```
🔍 Validating AI Service Configuration...
✅ Configuration is valid!
   Provider: groq
   Model: llama-3.1-70b-versatile
   💰 Uses free tier
```

**Errors:**

```
🔍 Validating AI Service Configuration...
❌ Configuration has issues:
   • Missing API key for openai provider. Set OPENAI_API_KEY environment variable.

💡 Try these free providers: public, groq, google
```

## Provider Commands

### List Providers

Show all available providers and their status:

```bash
my-app ai providers list
```

**Output:**

```
           🤖 AI Providers
┏━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━┓
┃ Provider┃ Status      ┃ Free┃ Features   ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━┩
│ public  │ ✅ Available│ Yes │ Basic      │
│ groq    │ ✅ Available│ Yes │ Stream     │
│ openai  │ ❌ Need key │ No  │ Stream,    │
│         │             │     │ Functions, │
│         │             │     │ Vision     │
└─────────┴─────────────┴─────┴────────────┘
```

## Version Command

Show AI service version and capabilities:

```bash
my-app ai version
```

**Output:**

```
🤖 AI Service Configuration System
Engine: PydanticAI
Status: ✅ Enabled
Provider: groq
Model: llama-3.1-70b-versatile

Available commands:
  • ai chat "message"       - Send a chat message
  • ai config show         - Show detailed configuration
  • ai config validate     - Validate current configuration
  • ai providers list      - List available providers
```

---

**Next Steps:**

- **[Examples](examples.md)** - Real-world usage examples
- **[API Reference](api.md)** - REST API documentation
- **[Service Layer](integration.md)** - Using AI service in code
