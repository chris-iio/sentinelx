"""Contract tests for the index intake surface."""
from html.parser import HTMLParser
from typing import Any
from unittest.mock import MagicMock

import pytest


class TagCollector(HTMLParser):
    """Collect start tags and their attributes for lightweight HTML assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def parse_tags(html: str) -> list[tuple[str, dict[str, str | None]]]:
    parser = TagCollector()
    parser.feed(html)
    return parser.tags


def has_class(tags: list[tuple[str, dict[str, str | None]]], class_name: str) -> bool:
    return any(
        class_name in (attrs.get("class") or "").split()
        for _, attrs in tags
    )


def by_id(tags: list[tuple[str, dict[str, str | None]]], element_id: str) -> dict[str, str | None] | None:
    for _, attrs in tags:
        if attrs.get("id") == element_id:
            return attrs
    return None


def has_hidden_input(tags: list[tuple[str, dict[str, str | None]]], name: str) -> bool:
    return any(
        tag == "input" and attrs.get("type") == "hidden" and attrs.get("name") == name
        for tag, attrs in tags
    )


def assert_describedby_targets_exist(
    tags: list[tuple[str, dict[str, str | None]]], attrs: dict[str, str | None], element_name: str
) -> None:
    describedby = attrs.get("aria-describedby")
    assert describedby, f"Missing aria-describedby on {element_name}"
    for target_id in describedby.split():
        assert by_id(tags, target_id) is not None, (
            f"{element_name} aria-describedby references missing #{target_id}"
        )


def test_index_renders_command_card_intake_contract(client: Any) -> None:
    """GET / exposes the stable S01 command-card selectors and form controls."""
    response = client.get("/")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    tags = parse_tags(html)

    for class_name in ("page-index", "intake-workbench", "command-card"):
        assert has_class(tags, class_name), f"Missing .{class_name} index contract selector"

    form = by_id(tags, "analyze-form")
    assert form is not None, "Missing #analyze-form"
    assert form.get("method") == "post"
    assert form.get("action") == "/analyze"
    assert has_hidden_input(tags, "csrf_token"), "Missing hidden csrf_token input"

    textarea = by_id(tags, "ioc-text")
    assert textarea is not None, "Missing #ioc-text"
    assert textarea.get("name") == "text"
    assert textarea.get("rows") == "5"
    assert textarea.get("aria-label") == "IOC text input"

    submit = by_id(tags, "submit-btn")
    assert submit is not None, "Missing #submit-btn"
    assert submit.get("type") == "submit"
    assert "disabled" in submit

    clear = by_id(tags, "clear-btn")
    assert clear is not None, "Missing #clear-btn"
    assert clear.get("type") == "button"

    mode_input = by_id(tags, "mode-input")
    assert mode_input is not None, "Missing #mode-input"
    assert mode_input.get("type") == "hidden"
    assert mode_input.get("name") == "mode"
    assert mode_input.get("value") == "offline"

    mode_widget = by_id(tags, "mode-toggle-widget")
    assert mode_widget is not None, "Missing #mode-toggle-widget"
    assert mode_widget.get("data-mode") == "offline"

    mode_title = by_id(tags, "mode-title")
    assert mode_title is not None, "Missing #mode-title"
    mode_help = by_id(tags, "mode-help")
    assert mode_help is not None, "Missing #mode-help"
    mode_status = by_id(tags, "mode-status")
    assert mode_status is not None, "Missing #mode-status"
    assert "Analysis mode" in html
    assert "Offline" in html
    assert "Online" in html
    assert "Offline mode is the safe default" in html
    assert "without contacting external providers" in html
    assert "Online" in html and "configured providers" in html
    assert "Offline selected" in html
    assert "local extraction only" in html

    mode_button = by_id(tags, "mode-toggle-btn")
    assert mode_button is not None, "Missing #mode-toggle-btn"
    assert mode_button.get("type") == "button"
    assert mode_button.get("aria-pressed") == "false"
    assert_describedby_targets_exist(tags, mode_button, "#mode-toggle-btn")

    paste_feedback = by_id(tags, "paste-feedback")
    assert paste_feedback is not None, "Missing #paste-feedback"


def test_index_renders_recent_analysis_rows_when_history_exists(client: Any) -> None:
    """GET / shows bounded recent analysis summaries with detail links."""
    mock_store = MagicMock()
    mock_store.list_recent.return_value = [
        {
            "id": "abc123deadbeef",
            "input_text": "Alert from <b>10[.]0[.]0[.]1</b>",
            "mode": "online",
            "total_count": 2,
            "top_verdict": "malicious",
            "created_at": "2026-04-26T08:30:00+00:00",
        },
        {
            "id": "def456cafebabe",
            "input_text": "Second investigation",
            "mode": "offline",
            "total_count": 1,
            "top_verdict": "clean",
            "created_at": "2026-04-25T12:00:00+00:00",
        },
    ]
    client.application.history_store = mock_store

    response = client.get("/")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    tags = parse_tags(html)

    mock_store.list_recent.assert_called_once_with(limit=4)
    assert "Recent Analyses" in html
    assert has_class(tags, "recent-analyses-rail")
    assert has_class(tags, "recent-analysis-row")
    assert not has_class(tags, "recent-analyses-empty")
    assert not has_class(tags, "recent-analyses-unavailable")
    assert any(
        tag == "a"
        and attrs.get("href") == "/history/abc123deadbeef"
        and "recent-analysis-row" in (attrs.get("class") or "").split()
        for tag, attrs in tags
    )
    assert any(
        tag == "a"
        and attrs.get("href") == "/history/def456cafebabe"
        and "recent-analysis-row" in (attrs.get("class") or "").split()
        for tag, attrs in tags
    )
    assert "&lt;b&gt;10[.]0[.]0[.]1&lt;/b&gt;" in html
    assert "<b>10[.]0[.]0[.]1</b>" not in html


def test_index_renders_recent_analyses_empty_state(client: Any) -> None:
    """GET / renders a compact recent-analysis empty state when history is empty."""
    mock_store = MagicMock()
    mock_store.list_recent.return_value = []
    client.application.history_store = mock_store

    response = client.get("/")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    tags = parse_tags(html)

    mock_store.list_recent.assert_called_once_with(limit=4)
    assert has_class(tags, "recent-analyses-rail")
    assert has_class(tags, "recent-analyses-empty")
    assert not has_class(tags, "recent-analysis-row")
    assert "No analyses yet" in html
    assert by_id(tags, "analyze-form") is not None


def test_index_recent_history_failure_is_fail_open_and_sanitized(
    client: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """History lookup failures log a sanitized warning and keep intake usable."""
    mock_store = MagicMock()
    mock_store.list_recent.side_effect = RuntimeError(
        "DB corrupt while reading raw IOC 203.0.113.44 and token secret-value"
    )
    client.application.history_store = mock_store

    response = client.get("/")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    tags = parse_tags(html)

    mock_store.list_recent.assert_called_once_with(limit=4)
    assert has_class(tags, "recent-analyses-rail")
    assert has_class(tags, "recent-analyses-unavailable")
    assert not has_class(tags, "recent-analysis-row")
    for element_id in (
        "analyze-form",
        "ioc-text",
        "submit-btn",
        "mode-input",
        "mode-toggle-widget",
    ):
        assert by_id(tags, element_id) is not None, f"Missing #{element_id} after history failure"
    assert has_hidden_input(tags, "csrf_token"), "Missing hidden csrf_token input"
    assert "recent history lookup failed" in caplog.text.lower()
    assert "RuntimeError" in caplog.text
    assert "203.0.113.44" not in caplog.text
    assert "secret-value" not in caplog.text
    assert "DB corrupt" not in caplog.text


def test_index_recent_analysis_missing_optional_fields_degrades(client: Any) -> None:
    """Rows missing optional display fields render safe fallback text instead of breaking /.
    """
    mock_store = MagicMock()
    mock_store.list_recent.return_value = [
        {
            "id": "minimal-row",
            "input_text": "Stored text with <script>alert('x')</script>",
        }
    ]
    client.application.history_store = mock_store

    response = client.get("/")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    tags = parse_tags(html)

    assert has_class(tags, "recent-analysis-row")
    assert any(
        tag == "a" and attrs.get("href") == "/history/minimal-row"
        for tag, attrs in tags
    )
    assert "&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;" in html
    assert "<script>alert('x')</script>" not in html
    assert "Unknown count" in html


def test_index_does_not_render_future_preview_surfaces(client: Any) -> None:
    """S03 still keeps pre-submit preview UI out of the index page."""
    mock_store = MagicMock()
    mock_store.list_recent.return_value = []
    client.application.history_store = mock_store

    response = client.get("/")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    tags = parse_tags(html)

    for class_name in (
        "analysis-preview",
        "pre-submit-preview",
        "preview-panel",
    ):
        assert not has_class(tags, class_name), f"Unexpected .{class_name} rendered on /"
