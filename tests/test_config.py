from __future__ import annotations

import pytest

from app import create_app
from app.config import (
    Config,
    SESSION_COOKIE_SAMESITE_VALUES,
    _validate_non_empty_string_sequence,
    _validate_session_cookie_samesite,
    validate_config_values,
)


def test_config_validate_accepts_default_static_invariants() -> None:
    Config().validate()


@pytest.mark.parametrize("field", ["ONLINE_MAX_IOCS", "ONLINE_MAX_DISPATCHES", "HISTORY_MAX_ROWS"])
def test_config_validate_rejects_invalid_admission_limits(field: str) -> None:
    config = Config()
    setattr(config, field, 0)

    with pytest.raises(ValueError, match=f"{field} must be a positive integer"):
        config.validate()


@pytest.mark.parametrize("field", ["TRUSTED_HOSTS", "ALLOWED_API_HOSTS"])
def test_config_validate_rejects_empty_host_sequences(field: str) -> None:
    config = Config()
    setattr(config, field, [])

    with pytest.raises(ValueError, match=f"{field} must be a non-empty sequence"):
        config.validate()


@pytest.mark.parametrize("field", ["TRUSTED_HOSTS", "ALLOWED_API_HOSTS"])
def test_config_validate_rejects_blank_host_values(field: str) -> None:
    config = Config()
    setattr(config, field, ["localhost", "  "])

    with pytest.raises(ValueError, match=f"{field} must contain only non-empty hostnames"):
        config.validate()


def test_host_sequence_validation_uses_direct_whitespace_scan() -> None:
    class NoStripHost(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("host validation should not allocate stripped host strings")

    _validate_non_empty_string_sequence("TRUSTED_HOSTS", [NoStripHost("localhost")])
    with pytest.raises(ValueError, match="TRUSTED_HOSTS must contain only non-empty hostnames"):
        _validate_non_empty_string_sequence("TRUSTED_HOSTS", [NoStripHost(" \n\t ")])

    assert "strip" not in _validate_non_empty_string_sequence.__code__.co_names
    assert "has_non_whitespace" in _validate_non_empty_string_sequence.__code__.co_names


def test_config_validate_rejects_invalid_samesite_value() -> None:
    config = Config()
    config.SESSION_COOKIE_SAMESITE = "Invalid"

    with pytest.raises(ValueError, match="SESSION_COOKIE_SAMESITE must be one of"):
        config.validate()


def test_samesite_validation_uses_precomputed_policy_values() -> None:
    assert SESSION_COOKIE_SAMESITE_VALUES == frozenset(("Strict", "Lax", "None"))
    for value in SESSION_COOKIE_SAMESITE_VALUES:
        _validate_session_cookie_samesite(value)

    with pytest.raises(ValueError, match="SESSION_COOKIE_SAMESITE must be one of"):
        _validate_session_cookie_samesite("Invalid")

    assert "_validate_session_cookie_samesite" in validate_config_values.__code__.co_names
    assert {"Strict", "Lax", "None"} not in validate_config_values.__code__.co_consts


def test_create_app_validates_effective_config_after_overrides() -> None:
    with pytest.raises(ValueError, match="ONLINE_MAX_IOCS must be a positive integer"):
        create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "ONLINE_MAX_IOCS": 0,
        })


def test_create_app_passes_history_retention_to_store() -> None:
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "HISTORY_MAX_ROWS": 3,
    })

    assert app.history_store._max_rows == 3
