"""Shared route form-value normalization helpers."""
from __future__ import annotations

from collections.abc import Mapping

from app.text_utils import stripped_text_or_none


def stripped_form_value(form: Mapping[str, object], field_name: str) -> str:
    """Return a stripped form field value, or an empty string when absent/blank."""
    value = form.get(field_name)
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return stripped_text_or_none(value) or ""
