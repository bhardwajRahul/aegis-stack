"""LLM fixture/seed data system.

Provides seed data for LLM vendors, models, and pricing.
"""

from app.services.ai.fixtures.llm_fixtures import load_all_llm_fixtures

__all__ = ["load_all_llm_fixtures"]
