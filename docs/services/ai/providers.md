# AI Providers

Complete setup guide for all supported AI providers.

## Overview

The AI service supports multiple providers through either [Pydantic AI](https://ai.pydantic.dev/) or [LangChain](https://python.langchain.com/) (see [Engines](engines.md)), giving you flexibility to choose based on your needs: cost, speed, features, or specific model capabilities.

!!! tip "All Providers Work with Both Engines"
    Whether you chose Pydantic AI or LangChain as your engine, all 7 providers are fully supported with identical configuration.

**Quick comparison:**

| Provider | API Key Required | Speed | Best For |
|----------|------------------|-------|----------|
| **PUBLIC** | ❌ No | Basic | Instant testing, no setup |
| **Google Gemini** | ✅ Yes (free tier) | Good | Development, prototyping |
| **Groq** | ✅ Yes (free tier) | Very fast | Production, low cost |
| **OpenAI** | ✅ Yes | Good | Production, familiar API |
| **Anthropic** | ✅ Yes | Good | Claude models |
| **Mistral** | ✅ Yes | Good | Open models |
| **Cohere** | ✅ Yes (free tier) | Good | Command models |

!!! tip "Recommendation"
    **Start:** PUBLIC (no API key, instant) → **Develop:** Google Gemini (free tier) → **Production:** Groq (very fast, low cost)

## Configuration

All providers are configured through environment variables in your `.env` file:

```bash
# Core AI Service Settings
AI_ENABLED=true                    # Enable/disable service
AI_PROVIDER=public                 # Provider: openai, anthropic, google, groq, mistral, cohere, public
AI_MODEL=auto                      # Model name (varies by provider, "auto" for PUBLIC)
AI_TEMPERATURE=0.7                 # Response creativity (0.0-2.0)
AI_MAX_TOKENS=1000                 # Maximum response length
AI_TIMEOUT_SECONDS=30.0            # Request timeout

# Provider API Keys (only needed for non-PUBLIC providers)
OPENAI_API_KEY=sk-...              # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...       # Anthropic API key
GOOGLE_API_KEY=...                 # Google API key
GROQ_API_KEY=gsk_...               # Groq API key
MISTRAL_API_KEY=...                # Mistral API key
COHERE_API_KEY=...                 # Cohere API key
```

## Provider Setup Guides

=== "PUBLIC (Free)"

    **No setup required!** Works out of the box with zero configuration.

    **Setup:**

    ```bash
    # Already configured by default - just start chatting
    my-app ai chat "Hello! Can you help me?"
    ```

    **Best for:** Instant testing, demos, getting started without any setup

=== "Groq (Production)"

    Blazing fast inference with very generous free tier.

    **Setup:**

    1. Sign up at [console.groq.com](https://console.groq.com/)
    2. Create an API key (free tier available)
    3. Configure your environment:

    ```bash
    export AI_PROVIDER=groq
    export GROQ_API_KEY=gsk_your_key_here
    export AI_MODEL=llama-3.1-8b-instant  # Fastest model
    ```

    **Available Models:** See [Groq's model documentation](https://console.groq.com/docs/models) for the latest available models.

    **Best for:** Production use (very fast, extremely low cost)

=== "Google Gemini (Free Tier)"

    Generous free tier with daily rate limits. Great for development.

    **Setup:**

    1. Get free API key from [aistudio.google.com](https://aistudio.google.com/apikey)
    2. Configure your environment:

    ```bash
    export AI_PROVIDER=google
    export GOOGLE_API_KEY=your_key_here
    export AI_MODEL=gemini-2.0-flash-exp
    ```

    **Available Models:** See [Google's model documentation](https://ai.google.dev/gemini-api/docs/models/gemini) for the latest available models.

    **Best for:** Development and prototyping within rate limits

=== "OpenAI"

    Industry-standard GPT models. Most widely used and documented.

    **Setup:**

    1. Get API key from [platform.openai.com](https://platform.openai.com/)
    2. Add payment method (required for API access)
    3. Configure your environment:

    ```bash
    export AI_PROVIDER=openai
    export OPENAI_API_KEY=sk-your_key_here
    export AI_MODEL=gpt-3.5-turbo
    ```

    **Available Models:** See [OpenAI's model documentation](https://platform.openai.com/docs/models) for the latest available models.

    **Best for:** Production with familiar API, extensive ecosystem

=== "Anthropic"

    Claude models from Anthropic. Known for safety and reasoning.

    **Setup:**

    1. Get API key from [console.anthropic.com](https://console.anthropic.com/)
    2. Add payment method
    3. Configure your environment:

    ```bash
    export AI_PROVIDER=anthropic
    export ANTHROPIC_API_KEY=sk-ant-your_key_here
    export AI_MODEL=claude-3-5-sonnet-20241022
    ```

    **Available Models:** See [Anthropic's model documentation](https://docs.anthropic.com/en/docs/models-overview) for the latest available models.

    **Best for:** High-quality responses, safety-critical applications

=== "Mistral"

    Open-source Mistral models with European data residency.

    **Setup:**

    1. Get API key from [console.mistral.ai](https://console.mistral.ai/)
    2. Configure your environment:

    ```bash
    export AI_PROVIDER=mistral
    export MISTRAL_API_KEY=your_key_here
    export AI_MODEL=mistral-small-latest
    ```

    **Available Models:** See [Mistral's model documentation](https://docs.mistral.ai/getting-started/models/) for the latest available models.

    **Best for:** Open-source preference, European compliance requirements

=== "Cohere"

    Command models optimized for enterprise and RAG use cases.

    **Setup:**

    1. Get API key from [dashboard.cohere.com](https://dashboard.cohere.com/)
    2. Configure your environment:

    ```bash
    export AI_PROVIDER=cohere
    export COHERE_API_KEY=your_key_here
    export AI_MODEL=command-r-plus
    ```

    **Available Models:** See [Cohere's model documentation](https://docs.cohere.com/docs/models) for the latest available models.

    **Best for:** Enterprise features, RAG applications

## Switching Providers

You can switch providers at any time by changing your `.env` file:

```bash
# Switch from PUBLIC to Groq
AI_PROVIDER=groq
GROQ_API_KEY=your-key-here
AI_MODEL=llama-3.1-8b-instant
```

Then restart your application:

```bash
# Stop the server
make stop

# Start with new provider
make serve
```

**Testing the switch:**

```bash
# Verify new provider is active
my-app ai status

# Test with a message
my-app ai chat "Hello from the new provider!"
```

## Troubleshooting

### "Missing API key" Error

```bash
❌ Missing API key for groq provider. Set GROQ_API_KEY environment variable.
```

**Solution:** Add the API key to your `.env` file:

```bash
GROQ_API_KEY=your-actual-key-here
```

### "Provider not available" Error

**Check configuration:**

```bash
my-app ai status
```

**Verify provider is installed:**

```bash
my-app ai providers
```

---

**Next Steps:**

- **[CLI Commands](cli.md)** - Using the AI service from command line
- **[API Reference](api.md)** - Using the AI service via REST API
- **[Service Layer](integration.md)** - Using the AI service in your code
- **[Examples](examples.md)** - Real-world usage patterns
