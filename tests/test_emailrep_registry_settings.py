"""Focused EmailRep registry/settings metadata contract tests."""
from __future__ import annotations

from types import MappingProxyType
from unittest.mock import MagicMock

import pytest

from app.config import Config
from app.enrichment.provider_catalog import PROVIDER_INFO
from app.enrichment.setup import build_registry
from app.pipeline.models import IOCType


_NON_EMAIL_TYPES = (
    IOCType.IPV4,
    IOCType.IPV6,
    IOCType.DOMAIN,
    IOCType.URL,
    IOCType.MD5,
    IOCType.SHA1,
    IOCType.SHA256,
    IOCType.CVE,
)


def _config_store_with_provider_keys(provider_keys: dict[str, str | None]) -> MagicMock:
    """Return a ConfigStore mock that serves a provider-key map."""
    config_store = MagicMock()
    config_store.get_vt_api_key.return_value = None
    config_store.all_provider_keys.return_value = provider_keys
    return config_store


def _registry_with_provider_keys(provider_keys: dict[str, str | None]):
    return build_registry(
        allowed_hosts=Config.ALLOWED_API_HOSTS,
        config_store=_config_store_with_provider_keys(provider_keys),
    )


def _emailrep_providers(registry, ioc_type: IOCType):
    return [provider for provider in registry.providers_for_type(ioc_type) if provider.name == "EmailRep"]


def test_emailrep_settings_metadata_and_allowed_host_contract() -> None:
    """Settings metadata advertises EmailRep as an email-only HTTPS key provider."""
    emailrep_entries = [entry for entry in PROVIDER_INFO if entry["id"] == "emailrep"]

    assert isinstance(PROVIDER_INFO, tuple)
    assert len(emailrep_entries) == 1
    emailrep = emailrep_entries[0]
    assert isinstance(emailrep, MappingProxyType)
    assert emailrep["name"] == "EmailRep"
    assert emailrep["requires_key"] is True
    assert str(emailrep["signup_url"]).startswith("https://")
    assert str(emailrep["ioc_types"]).lower() == "email"
    assert "emailrep.io" in Config.ALLOWED_API_HOSTS


def test_emailrep_missing_key_leaves_email_coverage_at_zero() -> None:
    """EmailRep is registered once but excluded from email dispatch without a key."""
    registry = _registry_with_provider_keys({})

    assert sum(1 for provider in registry.all() if provider.name == "EmailRep") == 1
    assert _emailrep_providers(registry, IOCType.EMAIL) == []
    assert registry.provider_count_for_type(IOCType.EMAIL) == 0


def test_emailrep_empty_key_leaves_email_coverage_at_zero() -> None:
    """Empty provider keys are treated as unconfigured by the adapter contract."""
    registry = _registry_with_provider_keys({"emailrep": ""})

    assert _emailrep_providers(registry, IOCType.EMAIL) == []
    assert registry.provider_count_for_type(IOCType.EMAIL) == 0


def test_emailrep_key_creates_exactly_one_configured_email_provider() -> None:
    """An EmailRep key contributes exactly one configured email provider."""
    registry = _registry_with_provider_keys({"emailrep": "emailrep-test-key"})

    email_providers = _emailrep_providers(registry, IOCType.EMAIL)
    assert len(email_providers) == 1
    assert email_providers[0].is_configured() is True
    assert registry.provider_count_for_type(IOCType.EMAIL) == 1


@pytest.mark.parametrize("ioc_type", _NON_EMAIL_TYPES)
def test_emailrep_key_does_not_add_non_email_provider_coverage(ioc_type: IOCType) -> None:
    """EmailRep remains email-only and OTX does not backfill email coverage."""
    registry = _registry_with_provider_keys({"emailrep": "emailrep-test-key"})

    assert _emailrep_providers(registry, ioc_type) == []


def test_build_registry_reads_emailrep_key_from_config_store() -> None:
    """Registry composition reads provider settings once and configures EmailRep."""
    config_store = _config_store_with_provider_keys({"emailrep": "emailrep-test-key"})

    registry = build_registry(
        allowed_hosts=Config.ALLOWED_API_HOSTS,
        config_store=config_store,
    )

    config_store.all_provider_keys.assert_called_once_with()
    config_store.get_provider_key.assert_not_called()
    assert len(_emailrep_providers(registry, IOCType.EMAIL)) == 1


def test_emailrep_key_lookup_error_is_treated_as_missing_key() -> None:
    """A local config read failure leaves EmailRep unconfigured instead of aborting startup."""
    config_store = MagicMock()
    config_store.get_vt_api_key.return_value = None
    config_store.all_provider_keys.side_effect = RuntimeError("local config store read failed")

    registry = build_registry(
        allowed_hosts=Config.ALLOWED_API_HOSTS,
        config_store=config_store,
    )

    assert _emailrep_providers(registry, IOCType.EMAIL) == []
    assert registry.provider_count_for_type(IOCType.EMAIL) == 0
