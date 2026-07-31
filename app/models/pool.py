"""Provider-agnostic model pool for agent tasks.

One pool, named task slots, user-supplied keys. Callers ask for a task
("analysis", "poc"); the pool routes to the configured provider and model.
Model choice stays swappable on purpose: the prompts, verification, and
memory are the product, the weights are plumbing.

Keys come from the environment (CI-friendly) or explicit arguments:

- ``SENTINELX_ANTHROPIC_API_KEY`` for the Anthropic Messages API
- ``SENTINELX_OPENAI_API_KEY`` for any OpenAI-compatible Chat Completions API
- ``SENTINELX_OPENAI_BASE_URL`` to point that provider at Ollama, vLLM, or
  OpenRouter (default: https://api.openai.com/v1)

An optional per-task allowlist caps which models a task may use. It is the
same governance shape as a zero-retention provider toggle: policy over
prompts.
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests

__all__ = ("DEFAULT_OPENAI_BASE_URL", "TASKS", "ModelError", "ModelPool")

TASKS = ("analysis", "poc")

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

_ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"

# Output is bounded by max_tokens in the payload, so responses stay small
# enough that a plain (non-streaming) read is safe here.
_MAX_TOKENS = 8192


class ModelError(RuntimeError):
    """Raised when a model call cannot be completed or configured."""


class ModelPool:
    """Route named agent tasks to configured provider models.

    Args:
        tasks: mapping of task name to a config dict with ``provider``
               ("anthropic" or "openai_compatible"), ``model``, and an
               optional ``base_url`` for the OpenAI-compatible provider.
        keys: explicit provider keys; falls back to the environment.
        allowed: optional mapping of task name to a list of permitted model
                 names. A task absent from the mapping allows any model.
        timeout: read timeout in seconds for one model call.
    """

    def __init__(
        self,
        tasks: dict[str, dict[str, str]],
        *,
        keys: dict[str, str] | None = None,
        allowed: dict[str, list[str]] | None = None,
        timeout: int = 120,
    ) -> None:
        self._tasks = dict(tasks)
        self._keys = keys or {}
        self._allowed = allowed or {}
        self._timeout = (5, timeout)  # connect, read — same shape as SEC-04

    @classmethod
    def from_env(cls, **kwargs: Any) -> "ModelPool":
        """Build a pool from environment configuration.

        ``SENTINELX_PROVIDER`` picks the default provider ("anthropic" or
        "openai_compatible"). ``SENTINELX_MODEL_ANALYSIS`` and
        ``SENTINELX_MODEL_POC`` set per-task models, falling back to
        ``SENTINELX_MODEL`` for both.
        """
        provider = os.environ.get("SENTINELX_PROVIDER", "anthropic").strip()
        default_model = os.environ.get("SENTINELX_MODEL", "").strip()
        tasks: dict[str, dict[str, str]] = {}
        for task in TASKS:
            model = os.environ.get(f"SENTINELX_MODEL_{task.upper()}", default_model).strip()
            tasks[task] = {"provider": provider, "model": model}
        base_url = os.environ.get("SENTINELX_OPENAI_BASE_URL", "").strip()
        if base_url:
            for config in tasks.values():
                config["base_url"] = base_url
        return cls(tasks, **kwargs)

    # ------------------------------------------------------------------
    # Public API

    def complete(self, task: str, system: str, user: str) -> str:
        """Return the model completion for one task prompt.

        Raises ModelError on unknown tasks, missing configuration or keys,
        disallowed models, and HTTP or payload failures.
        """
        config = self._config_for(task)
        provider = config["provider"]
        if provider == "anthropic":
            return self._complete_anthropic(config, system, user)
        if provider == "openai_compatible":
            return self._complete_openai(config, system, user)
        raise ModelError(f"unknown provider for task '{task}': {provider!r}")

    # ------------------------------------------------------------------
    # Internals

    def _config_for(self, task: str) -> dict[str, str]:
        config = self._tasks.get(task)
        if config is None:
            raise ModelError(f"unknown task: {task!r}")
        model = config.get("model", "").strip()
        if not model:
            raise ModelError(f"no model configured for task '{task}'")
        allowed = self._allowed.get(task)
        if allowed is not None and model not in allowed:
            raise ModelError(f"model {model!r} is not allowed for task '{task}'")
        return config

    def _key(self, env_name: str, provider: str) -> str:
        key = self._keys.get(provider) or os.environ.get(env_name, "")
        key = key.strip()
        if not key:
            raise ModelError(f"missing API key for provider '{provider}' ({env_name})")
        return key

    def _post_json(self, url: str, headers: dict[str, str], payload: dict) -> dict:
        """Single HTTP seam, monkeypatched by tests."""
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self._timeout)
        except requests.RequestException as exc:
            raise ModelError(f"model request failed: {exc}") from exc
        if response.status_code != 200:
            raise ModelError(f"model request returned HTTP {response.status_code}")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ModelError("model response was not JSON") from exc

    def _complete_anthropic(self, config: dict[str, str], system: str, user: str) -> str:
        payload = {
            "model": config["model"],
            "max_tokens": _MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self._key("SENTINELX_ANTHROPIC_API_KEY", "anthropic"),
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        data = self._post_json(_ANTHROPIC_MESSAGES_URL, headers, payload)
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError("unexpected Anthropic response shape") from exc

    def _complete_openai(self, config: dict[str, str], system: str, user: str) -> str:
        base_url = config.get("base_url") or os.environ.get(
            "SENTINELX_OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL
        )
        payload = {
            "model": config["model"],
            "max_tokens": _MAX_TOKENS,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "authorization": f"Bearer {self._key('SENTINELX_OPENAI_API_KEY', 'openai_compatible')}",
            "content-type": "application/json",
        }
        data = self._post_json(f"{base_url.rstrip('/')}/chat/completions", headers, payload)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError("unexpected OpenAI-compatible response shape") from exc
