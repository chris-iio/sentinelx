"""Model pool package: provider-agnostic access for agent tasks."""
from __future__ import annotations

from .pool import DEFAULT_OPENAI_BASE_URL, TASKS, ModelError, ModelPool

__all__ = ("DEFAULT_OPENAI_BASE_URL", "TASKS", "ModelError", "ModelPool")
