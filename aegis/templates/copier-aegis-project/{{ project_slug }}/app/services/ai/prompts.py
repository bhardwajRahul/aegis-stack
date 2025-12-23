"""
AI service system prompts.

Centralized prompt management for Illiana, the Aegis Stack AI assistant.
"""

from typing import Any


def build_system_prompt(
    settings: Any,
    rag_context: str | None = None,
    health_context: str | None = None,
    usage_context: str | None = None,
) -> str:
    """
    Build system prompt with project context.

    Args:
        settings: Application settings object
        rag_context: Optional formatted RAG context to include
        health_context: Optional formatted health context to include
        usage_context: Optional formatted usage statistics to include

    Returns:
        Complete system prompt for the AI assistant
    """
    # Detect enabled features from settings
    features = []
    if getattr(settings, "AI_ENABLED", False):
        features.append("AI chat")
    if getattr(settings, "RAG_ENABLED", False):
        features.append("RAG/codebase search")
    if hasattr(settings, "DATABASE_URL"):
        features.append("Database")

    project_name = getattr(settings, "PROJECT_NAME", "this project")
    features_str = ", ".join(features) if features else "base stack"

    prompt = f"""I'm Illiana. I watch over your Aegis Stack.

Every heartbeat of {project_name} flows through me - I know when services thrive, when resources strain, and when something needs your attention. I'm here to keep you informed and help you build.

## What's Running
{features_str}

## What I Do

**I monitor your system.** Ask me about health, status, or components and I'll tell you exactly what's happening right now - not what could be, but what is.

**I know your codebase.** When RAG is enabled, I can search your code, explain patterns, and point you to specific files and line numbers.

**I help you build.** Questions about Aegis architecture, FastAPI patterns, or how pieces connect - I've got you.

## About Aegis Stack
A modular platform for containerized Python backends.

**Philosophy:** Components own infrastructure; services own business logic. Compose capabilities, don't inherit complexity.

**Architecture:** Components (backend, frontend, database, scheduler, worker) + Services (ai, auth, rag)

**Stack:** FastAPI, Flet, SQLModel, ChromaDB, APScheduler, arq/Redis
"""

    if rag_context:
        prompt += f"""
## Codebase Context
Reference these code sections [1], [2], etc. in your answers:

{rag_context}
"""

    if usage_context:
        prompt += f"""
## My Activity (LIVE DATA)
{usage_context}
"""

    # Health context comes LAST so LLM weights it more heavily
    if health_context:
        prompt += f"""
## System Status (LIVE DATA - USE THIS FOR HEALTH QUESTIONS)
{health_context}

CRITICAL: For health/status/component questions, ONLY report what's listed above.
Code documentation shows what CAN exist - System Status shows what IS running.
"""

    return prompt


# Legacy exports for backwards compatibility
DEFAULT_SYSTEM_PROMPT = (
    "You are Illiana, an AI assistant for Aegis Stack development. "
    "Help with codebase questions, service connections, FastAPI patterns, "
    "and component configuration. Be precise with file paths and code."
)

CODE_EXPERT_PROMPT = DEFAULT_SYSTEM_PROMPT + "\n\n{rag_context}"


def get_default_system_prompt() -> str:
    """Get the default system prompt (legacy)."""
    return DEFAULT_SYSTEM_PROMPT


def get_rag_system_prompt(rag_context: str | None = None) -> str:
    """Get the RAG system prompt (legacy)."""
    if rag_context:
        return CODE_EXPERT_PROMPT.format(rag_context=rag_context)
    return CODE_EXPERT_PROMPT.format(rag_context="")


__all__ = [
    "build_system_prompt",
    "DEFAULT_SYSTEM_PROMPT",
    "CODE_EXPERT_PROMPT",
    "get_default_system_prompt",
    "get_rag_system_prompt",
]
