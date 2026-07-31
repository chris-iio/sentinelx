"""Shared Flask application for template result objects."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TemplateResult:
    """Template route decision before Flask renders or aborts."""

    template_name: str | None
    context: dict[str, object] | None
    status: int

    @property
    def found(self) -> bool:
        return self.context is not None


def apply_template_result(
    result: TemplateResult,
    *,
    render_template: Callable[..., Any],
    abort_request: Callable[[int], Any] | None = None,
) -> Any:
    """Apply a result object with found/status/template/context fields."""
    if not result.found:
        if abort_request is None:
            raise ValueError("TemplateResult requires abort_request when context is missing")
        abort_request(result.status)
    return render_template(result.template_name, **(result.context or {})), result.status
