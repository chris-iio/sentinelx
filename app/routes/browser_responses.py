"""Shared browser response application helpers."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FlashRedirect:
    """Browser redirect decision with an optional flash message."""

    url: str
    message: str | None = None
    category: str | None = None


def apply_flash_redirect(
    result: FlashRedirect,
    *,
    flash_message: Callable[[str, str], object],
    redirect_to: Callable[[str], Any],
    resolve_url: Callable[[str], str] = lambda url: url,
) -> Any:
    """Apply a flash message, when present, before returning the redirect."""
    if result.message is not None and result.category is not None:
        flash_message(result.message, result.category)
    return redirect_to(resolve_url(result.url))
