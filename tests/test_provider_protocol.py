"""Tests for Provider protocol conformance.

Verifies that all three existing adapters (VTAdapter, MBAdapter, TFAdapter)
satisfy the Provider protocol via isinstance() checks, and that the protocol
correctly rejects classes missing required attributes.
"""
from __future__ import annotations

import pytest

from app.enrichment.provider import Provider
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.threatfox import TFAdapter
from app.pipeline.models import IOCType


class TestProviderProtocolConformance:
    """isinstance() checks for all three adapters against the Provider protocol."""

    def test_vt_adapter_is_provider(self) -> None:
        """VTAdapter with a real key satisfies the Provider protocol."""
        adapter = VTAdapter(api_key="test-key", allowed_hosts=[])
        assert isinstance(adapter, Provider)

    def test_mb_adapter_is_provider(self) -> None:
        """MBAdapter satisfies the Provider protocol."""
        adapter = MBAdapter(api_key="test-key", allowed_hosts=[])
        assert isinstance(adapter, Provider)

    def test_tf_adapter_is_provider(self) -> None:
        """TFAdapter satisfies the Provider protocol."""
        adapter = TFAdapter(api_key="test-key", allowed_hosts=[])
        assert isinstance(adapter, Provider)

    def test_non_conforming_class_fails_isinstance(self) -> None:
        """A class missing the `name` attribute does not satisfy Provider."""
        class MissingName:
            supported_types = {IOCType.IPV4}
            requires_api_key = False

            def lookup(self, ioc):
                pass

            def is_configured(self) -> bool:
                return True

        obj = MissingName()
        assert not isinstance(obj, Provider)

    def test_non_conforming_class_missing_lookup_fails(self) -> None:
        """A class missing the `lookup` method does not satisfy Provider."""
        class MissingLookup:
            name = "Test"
            supported_types = {IOCType.IPV4}
            requires_api_key = False

            def is_configured(self) -> bool:
                return True

        obj = MissingLookup()
        assert not isinstance(obj, Provider)


class TestVTAdapterProtocolAttributes:
    """VTAdapter name, requires_api_key, and is_configured() behavior."""

    def test_vt_adapter_name(self) -> None:
        """VTAdapter.name is 'VirusTotal'."""
        adapter = VTAdapter(api_key="key", allowed_hosts=[])
        assert adapter.name == "VirusTotal"

    def test_vt_adapter_requires_api_key(self) -> None:
        """VTAdapter.requires_api_key is True."""
        adapter = VTAdapter(api_key="key", allowed_hosts=[])
        assert adapter.requires_api_key is True

    def test_vt_is_configured_true_for_nonempty_key(self) -> None:
        """VTAdapter.is_configured() returns True when api_key is non-empty."""
        adapter = VTAdapter(api_key="some-api-key", allowed_hosts=[])
        assert adapter.is_configured() is True

    def test_vt_is_configured_false_for_empty_key(self) -> None:
        """VTAdapter.is_configured() returns False when api_key is empty string."""
        adapter = VTAdapter(api_key="", allowed_hosts=[])
        assert adapter.is_configured() is False


class TestMBAdapterProtocolAttributes:
    """MBAdapter name, requires_api_key, and is_configured() behavior."""

    def test_mb_adapter_name(self) -> None:
        """MBAdapter.name is 'MalwareBazaar'."""
        adapter = MBAdapter(api_key="test-key", allowed_hosts=[])
        assert adapter.name == "MalwareBazaar"

    def test_mb_adapter_requires_api_key(self) -> None:
        """MBAdapter.requires_api_key is True (abuse.ch auth required)."""
        adapter = MBAdapter(api_key="test-key", allowed_hosts=[])
        assert adapter.requires_api_key is True

    def test_mb_is_configured_with_key(self) -> None:
        """MBAdapter.is_configured() returns True when API key is set."""
        adapter = MBAdapter(api_key="test-key", allowed_hosts=[])
        assert adapter.is_configured() is True

    def test_mb_is_not_configured_without_key(self) -> None:
        """MBAdapter.is_configured() returns False when API key is empty."""
        adapter = MBAdapter(api_key="", allowed_hosts=[])
        assert adapter.is_configured() is False


class TestTFAdapterProtocolAttributes:
    """TFAdapter name, requires_api_key, and is_configured() behavior."""

    def test_tf_adapter_name(self) -> None:
        """TFAdapter.name is 'ThreatFox'."""
        adapter = TFAdapter(api_key="test-key", allowed_hosts=[])
        assert adapter.name == "ThreatFox"

    def test_tf_adapter_requires_api_key(self) -> None:
        """TFAdapter.requires_api_key is True (abuse.ch auth required)."""
        adapter = TFAdapter(api_key="test-key", allowed_hosts=[])
        assert adapter.requires_api_key is True

    def test_tf_is_configured_with_key(self) -> None:
        """TFAdapter.is_configured() returns True when API key is set."""
        adapter = TFAdapter(api_key="test-key", allowed_hosts=[])
        assert adapter.is_configured() is True

    def test_tf_is_not_configured_without_key(self) -> None:
        """TFAdapter.is_configured() returns False when API key is empty."""
        adapter = TFAdapter(api_key="", allowed_hosts=[])
        assert adapter.is_configured() is False
