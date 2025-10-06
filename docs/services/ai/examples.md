# AI Service Examples

Real-world usage patterns and configuration examples for the AI service.

!!! info "Command Reference"
    For command syntax and options, see **[CLI Commands](cli.md)**.
    For REST API specifications, see **[API Reference](api.md)**.
    This page focuses on practical usage patterns and configuration.

## Common Use Cases

### Code Explanation

```bash
my-app ai chat send "Explain this code step by step:
def fibonacci(n):
    if n <= 1: return n
    return fibonacci(n-1) + fibonacci(n-2)"
```

### Generate Code

```bash
my-app ai chat send "Write a Python function that validates email addresses using regex"
```

### Debug Help

```bash
my-app ai chat send "Why might I get 'NoneType object is not iterable' in Python?"
```

### Learn Concepts

```bash
my-app ai chat send "Explain dependency injection with a simple Python example"
```

### API Documentation

```bash
my-app ai chat send "How do I use FastAPI's Path parameters with type hints?"
```

## Configuration Patterns

### Adjust Model Parameters

Tune AI behavior by adjusting model parameters in your `.env` file:

```bash
# .env file
AI_TEMPERATURE=0.7      # Creativity (0.0 = deterministic, 2.0 = very creative)
AI_MAX_TOKENS=1000      # Max response length
AI_TIMEOUT_SECONDS=30   # Request timeout
```

**Temperature guide:**
- `0.0-0.3` - Deterministic, focused responses (code generation, facts)
- `0.4-0.7` - Balanced creativity (explanations, tutorials)
- `0.8-2.0` - Creative, varied responses (brainstorming, writing)

### Switch Models for Different Tasks

Choose the right model for your use case:

```bash
# Groq models (FREE tier available)
export AI_MODEL=llama-3.1-70b-versatile    # Best quality, slower
export AI_MODEL=llama-3.1-8b-instant       # Fastest responses
export AI_MODEL=mixtral-8x7b-32768         # Long context (32K tokens)

# OpenAI models (requires paid account)
export AI_MODEL=gpt-3.5-turbo     # Fast, economical
export AI_MODEL=gpt-4o-mini       # Best balance
export AI_MODEL=gpt-4             # Highest quality

# Google models (generous free tier)
export AI_MODEL=gemini-pro        # Default Gemini
export AI_MODEL=gemini-flash      # Faster responses
```

---

**Next Steps:**

- **[Getting Started](index.md)** - Setup and configuration
- **[API Reference](api.md)** - REST API documentation
- **[CLI Commands](cli.md)** - Command-line reference
