"""Tests for the provider-agnostic model pool."""

import pytest

from app.models.pool import ModelError, ModelPool


def _pool(**kwargs):
    tasks = {
        "analysis": {"provider": "anthropic", "model": "claude-opus-x"},
        "poc": {"provider": "openai_compatible", "model": "gpt-x", "base_url": "http://local/v1"},
    }
    kwargs.setdefault("keys", {"anthropic": "ak", "openai_compatible": "ok"})
    return ModelPool(tasks, **kwargs)


def test_anthropic_payload_and_text_extraction(monkeypatch):
    captured = {}

    def fake_post(self, url, headers, payload):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return {"content": [{"text": "hello"}]}

    monkeypatch.setattr(ModelPool, "_post_json", fake_post)
    assert _pool().complete("analysis", "sys", "user") == "hello"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "ak"
    assert captured["payload"]["model"] == "claude-opus-x"
    assert captured["payload"]["system"] == "sys"
    assert captured["payload"]["messages"] == [{"role": "user", "content": "user"}]


def test_openai_payload_and_base_url(monkeypatch):
    captured = {}

    def fake_post(self, url, headers, payload):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "poc code"}}]}

    monkeypatch.setattr(ModelPool, "_post_json", fake_post)
    assert _pool().complete("poc", "sys", "user") == "poc code"
    assert captured["url"] == "http://local/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer ok"
    assert captured["payload"]["messages"][0] == {"role": "system", "content": "sys"}


def test_unknown_task_rejected():
    with pytest.raises(ModelError, match="unknown task"):
        _pool().complete("nope", "s", "u")


def test_unknown_provider_rejected():
    pool = ModelPool(
        {"analysis": {"provider": "bogus", "model": "m"}}, keys={"bogus": "k"}
    )
    with pytest.raises(ModelError, match="unknown provider"):
        pool.complete("analysis", "s", "u")


def test_missing_model_rejected():
    pool = ModelPool({"analysis": {"provider": "anthropic", "model": " "}})
    with pytest.raises(ModelError, match="no model configured"):
        pool.complete("analysis", "s", "u")


def test_missing_key_rejected(monkeypatch):
    monkeypatch.delenv("SENTINELX_ANTHROPIC_API_KEY", raising=False)
    pool = ModelPool({"analysis": {"provider": "anthropic", "model": "m"}})
    with pytest.raises(ModelError, match="missing API key"):
        pool.complete("analysis", "s", "u")


def test_allowlist_blocks_and_permits(monkeypatch):
    monkeypatch.setattr(
        ModelPool, "_post_json", lambda self, u, h, p: {"content": [{"text": "ok"}]}
    )
    pool = _pool(allowed={"analysis": ["claude-opus-x"]})
    assert pool.complete("analysis", "s", "u") == "ok"
    restricted = _pool(allowed={"analysis": ["some-other-model"]})
    with pytest.raises(ModelError, match="not allowed"):
        restricted.complete("analysis", "s", "u")


def test_http_error_status_raises(monkeypatch):
    class FakeResponse:
        status_code = 500

    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse())
    with pytest.raises(ModelError, match="HTTP 500"):
        _pool().complete("analysis", "s", "u")


def test_from_env_builds_task_slots(monkeypatch):
    monkeypatch.setenv("SENTINELX_PROVIDER", "openai_compatible")
    monkeypatch.setenv("SENTINELX_MODEL", "default-model")
    monkeypatch.setenv("SENTINELX_MODEL_POC", "poc-model")
    monkeypatch.setenv("SENTINELX_OPENAI_BASE_URL", "http://ollama/v1")
    pool = ModelPool.from_env()
    assert pool._tasks["analysis"] == {
        "provider": "openai_compatible",
        "model": "default-model",
        "base_url": "http://ollama/v1",
    }
    assert pool._tasks["poc"]["model"] == "poc-model"
