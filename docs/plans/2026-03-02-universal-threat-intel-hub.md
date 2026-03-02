# Universal Threat Intel Hub Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand SentinelX from 3 hardcoded providers to 8+ via a plugin-style provider registry, with unified results UX showing per-IOC summary + expandable provider details.

**Architecture:** Provider registry pattern — each adapter implements a `Provider` protocol with `name`, `supported_types`, `requires_api_key`, `lookup()`, and `is_configured()`. A `ProviderRegistry` class auto-discovers adapters and the orchestrator queries it. ConfigStore expands from single VT key to multi-provider key storage. Frontend gets unified summary cards with expandable per-provider detail rows.

**Tech Stack:** Python 3.10 + Flask 3.1, TypeScript 5.8 + esbuild, pytest, Playwright

**Design doc:** `docs/plans/2026-03-02-universal-threat-intel-hub-design.md`

---

## Phase 24: Provider Registry Refactor

**Goal:** Extract a formal provider protocol and registry so adding new providers requires zero changes to orchestrator or route code.

### Task 24.1: Provider Protocol

**Files:**
- Create: `app/enrichment/provider.py`
- Test: `tests/test_provider_protocol.py`

**Step 1: Write the failing test**

```python
# tests/test_provider_protocol.py
"""Tests for Provider protocol compliance."""
from __future__ import annotations

from app.enrichment.provider import Provider
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.threatfox import TFAdapter


class TestProtocolCompliance:
    """All existing adapters must satisfy the Provider protocol."""

    def test_vt_adapter_is_provider(self) -> None:
        assert isinstance(VTAdapter(api_key="test", allowed_hosts=[]), Provider)

    def test_mb_adapter_is_provider(self) -> None:
        assert isinstance(MBAdapter(allowed_hosts=[]), Provider)

    def test_tf_adapter_is_provider(self) -> None:
        assert isinstance(TFAdapter(allowed_hosts=[]), Provider)

    def test_protocol_has_name(self) -> None:
        adapter = MBAdapter(allowed_hosts=[])
        assert isinstance(adapter.name, str)
        assert len(adapter.name) > 0

    def test_protocol_has_requires_api_key(self) -> None:
        vt = VTAdapter(api_key="test", allowed_hosts=[])
        mb = MBAdapter(allowed_hosts=[])
        assert vt.requires_api_key is True
        assert mb.requires_api_key is False

    def test_protocol_has_is_configured(self) -> None:
        adapter = MBAdapter(allowed_hosts=[])
        assert adapter.is_configured() is True  # no key needed = always configured
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_provider_protocol.py -v`
Expected: FAIL — `Provider` does not exist yet

**Step 3: Write the Provider protocol**

```python
# app/enrichment/provider.py
"""Provider protocol for threat intelligence adapters.

Defines the interface that all TI provider adapters must implement.
Uses typing.Protocol for structural subtyping — adapters don't need
to explicitly inherit, they just need to have the right attributes
and methods.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType


@runtime_checkable
class Provider(Protocol):
    """Protocol that all enrichment provider adapters must satisfy.

    Attributes:
        name:             Human-readable provider name (e.g., "VirusTotal").
        supported_types:  Set of IOC types this provider can enrich.
        requires_api_key: True if the provider needs an API key to function.
    """

    name: str
    supported_types: set[IOCType] | frozenset[IOCType]
    requires_api_key: bool

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IOC. Returns result or error."""
        ...

    def is_configured(self) -> bool:
        """Return True if this provider is ready to use (API key present if needed)."""
        ...
```

**Step 4: Add `name`, `requires_api_key`, and `is_configured()` to existing adapters**

Add to `app/enrichment/adapters/virustotal.py` (inside `VTAdapter` class):
```python
    name = "VirusTotal"
    requires_api_key = True

    def is_configured(self) -> bool:
        return bool(self._api_key)
```

Add to `app/enrichment/adapters/malwarebazaar.py` (inside `MBAdapter` class):
```python
    name = "MalwareBazaar"
    requires_api_key = False

    def is_configured(self) -> bool:
        return True  # No API key needed
```

Add to `app/enrichment/adapters/threatfox.py` (inside `TFAdapter` class):
```python
    name = "ThreatFox"
    requires_api_key = False

    def is_configured(self) -> bool:
        return True  # No API key needed
```

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_provider_protocol.py -v`
Expected: PASS — all 6 tests green

**Step 6: Run full test suite for regressions**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All 224+ tests PASS (adding attributes doesn't break existing behavior)

**Step 7: Commit**

```bash
git add app/enrichment/provider.py tests/test_provider_protocol.py \
       app/enrichment/adapters/virustotal.py \
       app/enrichment/adapters/malwarebazaar.py \
       app/enrichment/adapters/threatfox.py
git commit -m "feat(24-01): add Provider protocol and conform existing adapters"
```

---

### Task 24.2: Provider Registry

**Files:**
- Create: `app/enrichment/registry.py`
- Test: `tests/test_provider_registry.py`

**Step 1: Write the failing test**

```python
# tests/test_provider_registry.py
"""Tests for ProviderRegistry."""
from __future__ import annotations

from app.enrichment.registry import ProviderRegistry
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.threatfox import TFAdapter
from app.pipeline.models import IOCType


ALLOWED_HOSTS = ["mb-api.abuse.ch", "threatfox-api.abuse.ch"]


class TestProviderRegistry:

    def test_register_and_list(self) -> None:
        registry = ProviderRegistry()
        mb = MBAdapter(allowed_hosts=ALLOWED_HOSTS)
        registry.register(mb)
        assert "MalwareBazaar" in [p.name for p in registry.all()]

    def test_providers_for_type_hash(self) -> None:
        registry = ProviderRegistry()
        mb = MBAdapter(allowed_hosts=ALLOWED_HOSTS)
        tf = TFAdapter(allowed_hosts=ALLOWED_HOSTS)
        registry.register(mb)
        registry.register(tf)
        providers = registry.providers_for_type(IOCType.SHA256)
        names = [p.name for p in providers]
        assert "MalwareBazaar" in names
        assert "ThreatFox" in names

    def test_providers_for_type_ip_excludes_mb(self) -> None:
        registry = ProviderRegistry()
        mb = MBAdapter(allowed_hosts=ALLOWED_HOSTS)
        tf = TFAdapter(allowed_hosts=ALLOWED_HOSTS)
        registry.register(mb)
        registry.register(tf)
        providers = registry.providers_for_type(IOCType.IPV4)
        names = [p.name for p in providers]
        assert "MalwareBazaar" not in names
        assert "ThreatFox" in names

    def test_configured_only(self) -> None:
        registry = ProviderRegistry()
        mb = MBAdapter(allowed_hosts=ALLOWED_HOSTS)
        registry.register(mb)
        configured = registry.configured()
        assert len(configured) == 1  # MB is always configured (no key needed)

    def test_provider_count_for_type(self) -> None:
        registry = ProviderRegistry()
        mb = MBAdapter(allowed_hosts=ALLOWED_HOSTS)
        tf = TFAdapter(allowed_hosts=ALLOWED_HOSTS)
        registry.register(mb)
        registry.register(tf)
        assert registry.provider_count_for_type(IOCType.SHA256) == 2
        assert registry.provider_count_for_type(IOCType.IPV4) == 1  # only TF

    def test_duplicate_register_raises(self) -> None:
        registry = ProviderRegistry()
        mb = MBAdapter(allowed_hosts=ALLOWED_HOSTS)
        registry.register(mb)
        import pytest
        with pytest.raises(ValueError, match="already registered"):
            registry.register(mb)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_provider_registry.py -v`
Expected: FAIL — `ProviderRegistry` does not exist

**Step 3: Write the ProviderRegistry**

```python
# app/enrichment/registry.py
"""Provider registry for threat intelligence adapters.

Central registry that adapter instances register with at startup.
The orchestrator and routes query the registry instead of hardcoding
adapter lists. Adding a new provider = new adapter file + register call.
"""
from __future__ import annotations

from app.enrichment.provider import Provider
from app.pipeline.models import IOCType


class ProviderRegistry:
    """Registry mapping provider names to adapter instances.

    Thread safety: registry is populated once at app startup before any
    request handling. Read-only access during request processing.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider adapter. Raises ValueError if name already taken."""
        if provider.name in self._providers:
            raise ValueError(
                f"Provider {provider.name!r} already registered"
            )
        self._providers[provider.name] = provider

    def all(self) -> list[Provider]:
        """Return all registered providers."""
        return list(self._providers.values())

    def configured(self) -> list[Provider]:
        """Return only providers that are ready to use (is_configured() == True)."""
        return [p for p in self._providers.values() if p.is_configured()]

    def providers_for_type(self, ioc_type: IOCType) -> list[Provider]:
        """Return configured providers that support the given IOC type."""
        return [
            p for p in self._providers.values()
            if ioc_type in p.supported_types and p.is_configured()
        ]

    def provider_count_for_type(self, ioc_type: IOCType) -> int:
        """Return count of configured providers supporting this IOC type."""
        return len(self.providers_for_type(ioc_type))
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_provider_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/enrichment/registry.py tests/test_provider_registry.py
git commit -m "feat(24-02): add ProviderRegistry with type-based lookup"
```

---

### Task 24.3: Expand ConfigStore for Multiple Providers

**Files:**
- Modify: `app/enrichment/config_store.py`
- Test: `tests/test_config_store.py` (find existing tests and add to them)

**Step 1: Write the failing test**

Add these tests to the existing ConfigStore test file (find it with `grep -r "ConfigStore" tests/`):

```python
class TestMultiProviderKeys:

    def test_set_and_get_provider_key(self, tmp_path) -> None:
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_provider_key("greynoise", "gn-test-key")
        assert store.get_provider_key("greynoise") == "gn-test-key"

    def test_get_provider_key_missing(self, tmp_path) -> None:
        store = ConfigStore(config_path=tmp_path / "config.ini")
        assert store.get_provider_key("greynoise") is None

    def test_multiple_providers_coexist(self, tmp_path) -> None:
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_vt_api_key("vt-key")
        store.set_provider_key("greynoise", "gn-key")
        store.set_provider_key("otx", "otx-key")
        assert store.get_vt_api_key() == "vt-key"
        assert store.get_provider_key("greynoise") == "gn-key"
        assert store.get_provider_key("otx") == "otx-key"

    def test_all_provider_keys(self, tmp_path) -> None:
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_provider_key("greynoise", "gn-key")
        store.set_provider_key("otx", "otx-key")
        keys = store.all_provider_keys()
        assert keys == {"greynoise": "gn-key", "otx": "otx-key"}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/ -k "TestMultiProviderKeys" -v`
Expected: FAIL — methods don't exist

**Step 3: Add multi-provider methods to ConfigStore**

Add to `app/enrichment/config_store.py`:

```python
_PROVIDERS_SECTION = "providers"

class ConfigStore:
    # ... existing code ...

    def get_provider_key(self, provider_name: str) -> str | None:
        """Read an API key for any provider from config file.

        Args:
            provider_name: Lowercase provider identifier (e.g., "greynoise", "otx").

        Returns:
            The API key string, or None if not configured.
        """
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path)
        value = cfg.get(_PROVIDERS_SECTION, provider_name, fallback=None)
        return value or None

    def set_provider_key(self, provider_name: str, key: str) -> None:
        """Write an API key for any provider to config file.

        Args:
            provider_name: Lowercase provider identifier.
            key: The API key to store.
        """
        self._config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path)
        if _PROVIDERS_SECTION not in cfg:
            cfg[_PROVIDERS_SECTION] = {}
        cfg[_PROVIDERS_SECTION][provider_name] = key
        fd = os.open(str(self._config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            cfg.write(fh)

    def all_provider_keys(self) -> dict[str, str]:
        """Return all configured provider keys as {name: key} dict."""
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path)
        if _PROVIDERS_SECTION not in cfg:
            return {}
        return dict(cfg[_PROVIDERS_SECTION])
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ -k "TestMultiProviderKeys" -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add app/enrichment/config_store.py tests/test_config_store.py
git commit -m "feat(24-03): expand ConfigStore for multi-provider API keys"
```

---

### Task 24.4: Wire Registry into Routes

**Files:**
- Modify: `app/routes.py` (lines 28-31 imports, lines 125-132 adapter wiring)
- Modify: `app/__init__.py` (create registry at app startup)
- Create: `app/enrichment/setup.py` (registry builder)
- Test: `tests/test_routes.py` (existing route tests must still pass)

**Step 1: Write the registry builder**

```python
# app/enrichment/setup.py
"""Provider registry setup — called once at app startup.

Builds and populates the ProviderRegistry with all available adapters.
This is the single place where providers are registered.
"""
from __future__ import annotations

from app.enrichment.config_store import ConfigStore
from app.enrichment.registry import ProviderRegistry
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.threatfox import TFAdapter


def build_registry(allowed_hosts: list[str], config_store: ConfigStore) -> ProviderRegistry:
    """Build and populate the provider registry with all adapters.

    Args:
        allowed_hosts: SSRF allowlist from app config.
        config_store: ConfigStore for reading API keys.

    Returns:
        Populated ProviderRegistry ready for use.
    """
    registry = ProviderRegistry()

    # VirusTotal (requires API key from ConfigStore)
    vt_key = config_store.get_vt_api_key() or ""
    registry.register(VTAdapter(api_key=vt_key, allowed_hosts=allowed_hosts))

    # MalwareBazaar (no key needed)
    registry.register(MBAdapter(allowed_hosts=allowed_hosts))

    # ThreatFox (no key needed)
    registry.register(TFAdapter(allowed_hosts=allowed_hosts))

    return registry
```

**Step 2: Write failing test for registry builder**

```python
# tests/test_registry_setup.py
"""Tests for provider registry setup."""
from __future__ import annotations

from app.enrichment.setup import build_registry
from app.enrichment.config_store import ConfigStore


def test_build_registry_has_three_providers(tmp_path) -> None:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_vt_api_key("test-key")
    hosts = ["www.virustotal.com", "mb-api.abuse.ch", "threatfox-api.abuse.ch"]
    registry = build_registry(allowed_hosts=hosts, config_store=store)
    names = [p.name for p in registry.all()]
    assert "VirusTotal" in names
    assert "MalwareBazaar" in names
    assert "ThreatFox" in names
    assert len(names) == 3


def test_build_registry_vt_configured_with_key(tmp_path) -> None:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_vt_api_key("test-key")
    hosts = ["www.virustotal.com", "mb-api.abuse.ch", "threatfox-api.abuse.ch"]
    registry = build_registry(allowed_hosts=hosts, config_store=store)
    configured = registry.configured()
    names = [p.name for p in configured]
    assert "VirusTotal" in names


def test_build_registry_vt_unconfigured_without_key(tmp_path) -> None:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    # No VT key set
    hosts = ["www.virustotal.com", "mb-api.abuse.ch", "threatfox-api.abuse.ch"]
    registry = build_registry(allowed_hosts=hosts, config_store=store)
    configured = registry.configured()
    names = [p.name for p in configured]
    assert "VirusTotal" not in names  # VT not configured without key
    assert "MalwareBazaar" in names    # MB always configured
    assert "ThreatFox" in names        # TF always configured
```

**Step 3: Run test**

Run: `python -m pytest tests/test_registry_setup.py -v`
Expected: PASS (setup.py was written in step 1)

**Step 4: Update routes.py to use registry**

Replace the hardcoded adapter wiring in `app/routes.py`:

Remove imports (lines 28-30):
```python
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.threatfox import TFAdapter
from app.enrichment.adapters.virustotal import VTAdapter
```

Add import:
```python
from app.enrichment.setup import build_registry
```

Replace the adapter wiring block in `analyze()` (lines 127-131):
```python
        # OLD:
        # allowed_hosts = current_app.config.get("ALLOWED_API_HOSTS", [])
        # vt_adapter = VTAdapter(api_key=api_key, allowed_hosts=allowed_hosts)
        # mb_adapter = MBAdapter(allowed_hosts=allowed_hosts)
        # tf_adapter = TFAdapter(allowed_hosts=allowed_hosts)
        # adapters_list = [vt_adapter, mb_adapter, tf_adapter]

        # NEW:
        allowed_hosts = current_app.config.get("ALLOWED_API_HOSTS", [])
        config_store = ConfigStore()
        registry = build_registry(allowed_hosts=allowed_hosts, config_store=config_store)
        adapters_list = registry.configured()
```

Also update the VT key check — instead of requiring VT specifically, online mode should require at least one configured provider:
```python
        # OLD: if not api_key: redirect to settings
        # NEW: check if any enrichment providers are configured
        if not registry.configured():
            flash("Please configure at least one provider API key", "warning")
            return redirect(url_for("main.settings_get"))
```

**Step 5: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests PASS. Existing route tests should still work because the same 3 adapters are registered.

Note: If route tests mock adapter imports directly, they may need updating. Check `tests/test_routes.py` for patches like `@patch("app.routes.VTAdapter")` and update to patch the registry or setup module instead.

**Step 6: Commit**

```bash
git add app/enrichment/setup.py tests/test_registry_setup.py app/routes.py
git commit -m "feat(24-04): wire ProviderRegistry into routes, replace hardcoded adapters"
```

---

### Task 24.5: Update TypeScript Types for Dynamic Provider Counts

**Files:**
- Modify: `app/static/src/ts/types/ioc.ts`
- Modify: `app/static/src/ts/modules/enrichment.ts`
- Modify: `app/routes.py`
- Modify: `app/templates/results.html`

The `IOC_PROVIDER_COUNTS` constant in `types/ioc.ts` is currently hardcoded to 2-3 providers per type. With the registry, provider counts become dynamic. The frontend needs to get counts from the backend instead of hardcoding.

**Step 1: Pass provider_counts as template variable**

Modify `app/routes.py` `analyze()` — add to `template_extras`:
```python
        # Compute provider counts per IOC type for the frontend
        from app.pipeline.models import IOCType
        provider_counts = {}
        for ioc_type_enum in IOCType:
            count = registry.provider_count_for_type(ioc_type_enum)
            if count > 0:
                provider_counts[ioc_type_enum.value] = count
        template_extras["provider_counts"] = provider_counts
```

Modify `app/templates/results.html` — add data attribute:
```html
<div class="page-results" data-job-id="{{ job_id }}" data-mode="{{ mode }}"
     data-provider-counts='{{ provider_counts | tojson if provider_counts else "{}" }}'>
```

**Step 2: Update TypeScript to read from DOM**

Modify `app/static/src/ts/types/ioc.ts` — replace hardcoded `IOC_PROVIDER_COUNTS`:
```typescript
/**
 * Read provider counts from the DOM (set by Flask template).
 * Falls back to legacy hardcoded values if data attribute is missing.
 */
export function getProviderCounts(): Record<string, number> {
  const el = document.querySelector(".page-results");
  if (el) {
    const raw = el.getAttribute("data-provider-counts");
    if (raw) {
      try {
        return JSON.parse(raw) as Record<string, number>;
      } catch {
        // Fall through to defaults
      }
    }
  }
  // Legacy fallback
  return {
    ipv4: 2, ipv6: 2, domain: 2, url: 2,
    md5: 3, sha1: 3, sha256: 3,
  };
}
```

Update `app/static/src/ts/modules/enrichment.ts` to call `getProviderCounts()` instead of importing the static `IOC_PROVIDER_COUNTS` constant.

**Step 3: Build and verify**

Run: `make build && make typecheck`
Expected: Clean build, no type errors

**Step 4: Commit**

```bash
git add app/routes.py app/templates/results.html \
       app/static/src/ts/types/ioc.ts app/static/src/ts/modules/enrichment.ts \
       app/static/dist/main.js
git commit -m "feat(24-05): dynamic provider counts from registry to frontend"
```

---

## Phase 25: Shodan InternetDB (Zero-Auth Provider)

**Goal:** First new provider — zero auth, IP-only enrichment from Shodan InternetDB.

### Task 25.1: Shodan InternetDB Adapter

**Files:**
- Create: `app/enrichment/adapters/shodan_internetdb.py`
- Create: `tests/test_shodan_internetdb.py`

**Step 1: Write the failing tests**

```python
# tests/test_shodan_internetdb.py
"""Tests for Shodan InternetDB adapter."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import requests
import requests.exceptions

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.shodan_internetdb import ShodanInternetDBAdapter

ALLOWED_HOSTS = ["internetdb.shodan.io"]

SHODAN_RESPONSE_WITH_VULNS = {
    "ip": "1.2.3.4",
    "ports": [22, 80, 443],
    "cpes": ["cpe:/a:apache:http_server:2.4.51"],
    "hostnames": ["example.com"],
    "tags": [],
    "vulns": ["CVE-2021-41773", "CVE-2023-12345"],
}

SHODAN_RESPONSE_CLEAN = {
    "ip": "8.8.8.8",
    "ports": [53, 443],
    "cpes": [],
    "hostnames": ["dns.google"],
    "tags": ["cdn"],
    "vulns": [],
}


def _make_mock_get_response(status_code: int, body: dict | None = None) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if body is not None:
        raw_bytes = json.dumps(body).encode()
        mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_adapter() -> ShodanInternetDBAdapter:
    return ShodanInternetDBAdapter(allowed_hosts=ALLOWED_HOSTS)


class TestShodanProtocol:
    def test_name(self) -> None:
        assert _make_adapter().name == "Shodan InternetDB"

    def test_requires_api_key(self) -> None:
        assert _make_adapter().requires_api_key is False

    def test_is_configured(self) -> None:
        assert _make_adapter().is_configured() is True

    def test_supported_types(self) -> None:
        types = _make_adapter().supported_types
        assert IOCType.IPV4 in types
        assert IOCType.IPV6 in types
        assert IOCType.SHA256 not in types
        assert IOCType.DOMAIN not in types


class TestShodanLookup:
    def test_ip_with_vulns_returns_suspicious(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, SHODAN_RESPONSE_WITH_VULNS)
        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"
        assert result.provider == "Shodan InternetDB"
        assert "CVE-2021-41773" in result.raw_stats.get("vulns", [])

    def test_ip_clean_returns_clean(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = _make_mock_get_response(200, SHODAN_RESPONSE_CLEAN)
        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "clean"

    def test_ip_not_found_returns_no_data(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10.0.0.1")
        mock_resp = _make_mock_get_response(404)
        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_unsupported_type_returns_error(self) -> None:
        ioc = IOC(type=IOCType.SHA256, value="a" * 64, raw_match="a" * 64)
        result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentError)

    def test_timeout_returns_error(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        with patch("requests.get", side_effect=requests.exceptions.Timeout):
            result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentError)
        assert "timeout" in result.error.lower() or "Timeout" in result.error

    def test_ssrf_validation(self) -> None:
        adapter = ShodanInternetDBAdapter(allowed_hosts=["other.host.com"])
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        result = adapter.lookup(ioc)
        assert isinstance(result, EnrichmentError)
        assert "SSRF" in result.error or "allowlist" in result.error.lower()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shodan_internetdb.py -v`
Expected: FAIL — module does not exist

**Step 3: Write the adapter**

```python
# app/enrichment/adapters/shodan_internetdb.py
"""Shodan InternetDB adapter.

Queries the free, keyless Shodan InternetDB API for IP address context:
open ports, CPEs (software), hostnames, tags, and known CVEs.

Security:
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call
  - SEC-04: Strict timeout on all requests
  - SEC-05: Response size cap via streaming read
  - No API key required — InternetDB is a free public service

Verdict mapping:
  - Has vulns list (non-empty)     -> "suspicious" (known vulnerabilities)
  - No vulns, has ports            -> "clean" (visible but no known vulns)
  - 404 (not in database)          -> "no_data"
"""
from __future__ import annotations

import requests
import requests.exceptions

from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

INTERNETDB_BASE = "https://internetdb.shodan.io"


class ShodanInternetDBAdapter:
    """Adapter for the Shodan InternetDB API (free, no auth)."""

    name = "Shodan InternetDB"
    supported_types = frozenset({IOCType.IPV4, IOCType.IPV6})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        return True  # No API key needed

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name,
                error=f"IOC type {ioc.type.value!r} not supported by {self.name}",
            )

        url = f"{INTERNETDB_BASE}/{ioc.value}"

        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

        try:
            resp = requests.get(
                url, timeout=TIMEOUT, stream=True, allow_redirects=False,
            )
        except requests.exceptions.Timeout:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Request timed out",
            )
        except requests.exceptions.RequestException as exc:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error=str(exc),
            )

        if resp.status_code == 404:
            return EnrichmentResult(
                ioc=ioc, provider=self.name, verdict="no_data",
                detection_count=0, total_engines=0, scan_date=None,
                raw_stats={},
            )

        try:
            resp.raise_for_status()
            data = read_limited(resp)
        except (requests.exceptions.HTTPError, ValueError) as exc:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error=str(exc),
            )

        return self._parse_response(ioc, data)

    def _parse_response(self, ioc: IOC, data: dict) -> EnrichmentResult:
        vulns = data.get("vulns", [])
        ports = data.get("ports", [])

        if vulns:
            verdict = "suspicious"
            detection_count = len(vulns)
        elif ports:
            verdict = "clean"
            detection_count = 0
        else:
            verdict = "no_data"
            detection_count = 0

        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict=verdict,
            detection_count=detection_count,
            total_engines=len(ports),
            scan_date=None,
            raw_stats={
                "ports": ports,
                "cpes": data.get("cpes", []),
                "hostnames": data.get("hostnames", []),
                "tags": data.get("tags", []),
                "vulns": vulns,
            },
        )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_shodan_internetdb.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/enrichment/adapters/shodan_internetdb.py tests/test_shodan_internetdb.py
git commit -m "feat(25-01): add Shodan InternetDB adapter (zero-auth, IP enrichment)"
```

---

### Task 25.2: Register Shodan in Registry and Update Config

**Files:**
- Modify: `app/enrichment/setup.py` (add Shodan registration)
- Modify: `app/config.py` (add `internetdb.shodan.io` to ALLOWED_API_HOSTS)
- Test: Update `tests/test_registry_setup.py`

**Step 1: Write failing test**

```python
# Add to tests/test_registry_setup.py:
def test_build_registry_has_shodan(tmp_path) -> None:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    hosts = ["www.virustotal.com", "mb-api.abuse.ch", "threatfox-api.abuse.ch", "internetdb.shodan.io"]
    registry = build_registry(allowed_hosts=hosts, config_store=store)
    names = [p.name for p in registry.all()]
    assert "Shodan InternetDB" in names
```

**Step 2: Add Shodan to setup.py and config.py**

In `app/enrichment/setup.py`:
```python
from app.enrichment.adapters.shodan_internetdb import ShodanInternetDBAdapter

# Inside build_registry(), add:
    registry.register(ShodanInternetDBAdapter(allowed_hosts=allowed_hosts))
```

In `app/config.py`:
```python
    ALLOWED_API_HOSTS: list[str] = [
        "www.virustotal.com",
        "mb-api.abuse.ch",
        "threatfox-api.abuse.ch",
        "internetdb.shodan.io",
    ]
```

**Step 3: Run tests**

Run: `python -m pytest tests/test_registry_setup.py tests/test_shodan_internetdb.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add app/enrichment/setup.py app/config.py tests/test_registry_setup.py
git commit -m "feat(25-02): register Shodan InternetDB in provider registry"
```

---

## Phase 26: Free-Key Providers

**Goal:** Add URLhaus, OTX AlienVault, GreyNoise Community, and AbuseIPDB adapters + settings page expansion.

### Task 26.1: URLhaus Adapter

**Files:**
- Create: `app/enrichment/adapters/urlhaus.py`
- Create: `tests/test_urlhaus.py`

Follow the same TDD pattern as Task 25.1. Key implementation details:

- **Endpoint:** POST to `https://urlhaus-api.abuse.ch/v1/url/`, `/host/`, or `/payload/`
- **Endpoint selection:** URL type -> `/url/` with `{"url": value}`; IP/domain -> `/host/` with `{"host": value}`; hash -> `/payload/` with `{"md5_hash": value}` or `{"sha256_hash": value}`
- **Supported types:** `{IOCType.URL, IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, IOCType.MD5, IOCType.SHA256}` (no SHA1, no CVE)
- **Auth:** `Auth-Key` header from ConfigStore (`get_provider_key("urlhaus")`)
- **requires_api_key:** True (URLhaus requires registration)
- **Verdict:** `query_status == "is_listed"` or `query_status == "ok"` -> "malicious"; `"no_results"` -> "no_data"
- **ALLOWED_API_HOSTS:** Add `"urlhaus-api.abuse.ch"` to config.py
- **raw_stats:** Include malware family, tags, blacklist status, associated payloads

Write tests covering: found (malicious), not-found (no_data), each IOC type, timeout, SSRF, auth error (403).

**Commit:** `feat(26-01): add URLhaus adapter`

---

### Task 26.2: OTX AlienVault Adapter

**Files:**
- Create: `app/enrichment/adapters/otx.py`
- Create: `tests/test_otx.py`

Key implementation details:

- **Endpoint:** GET `https://otx.alienvault.com/api/v1/indicators/{type}/{value}/general`
- **Type mapping:** `IOCType.IPV4` -> `"IPv4"`, `IOCType.IPV6` -> `"IPv6"`, `IOCType.DOMAIN` -> `"domain"`, `IOCType.URL` -> `"url"`, `IOCType.MD5` / `IOCType.SHA1` / `IOCType.SHA256` -> `"file"`, `IOCType.CVE` -> `"cve"`
- **Supported types:** ALL types including CVE (first CVE provider!)
- **Auth:** `X-OTX-API-KEY` header from ConfigStore (`get_provider_key("otx")`)
- **requires_api_key:** True
- **Verdict:** `pulse_info.count >= 5` -> "malicious"; `1-4` -> "suspicious"; `0` -> "no_data"
- **ALLOWED_API_HOSTS:** Add `"otx.alienvault.com"` to config.py
- **raw_stats:** Include pulse_count, reputation, first/last seen, related pulses summary

Write tests covering: high pulse count (malicious), low pulse count (suspicious), zero (no_data), CVE lookup, timeout, SSRF, auth error.

**Commit:** `feat(26-02): add OTX AlienVault adapter (first CVE provider)`

---

### Task 26.3: GreyNoise Community Adapter

**Files:**
- Create: `app/enrichment/adapters/greynoise.py`
- Create: `tests/test_greynoise.py`

Key implementation details:

- **Endpoint:** GET `https://api.greynoise.io/v3/community/{ip}`
- **Supported types:** `{IOCType.IPV4, IOCType.IPV6}`
- **Auth:** `key` header from ConfigStore (`get_provider_key("greynoise")`)
- **requires_api_key:** True
- **Verdict logic:**
  - `riot == true` -> "clean" (known benign service: Google, Cloudflare, etc.)
  - `classification == "malicious"` -> "malicious"
  - `noise == true && classification != "malicious"` -> "suspicious" (mass scanner)
  - Everything else -> "no_data"
- **ALLOWED_API_HOSTS:** Add `"api.greynoise.io"` to config.py
- **raw_stats:** Include noise, riot, classification, name, link, last_seen

Write tests covering: RIOT IP (clean), malicious scanner, benign scanner (suspicious), unknown, 404, timeout, SSRF.

**Commit:** `feat(26-03): add GreyNoise Community adapter`

---

### Task 26.4: AbuseIPDB Adapter

**Files:**
- Create: `app/enrichment/adapters/abuseipdb.py`
- Create: `tests/test_abuseipdb.py`

Key implementation details:

- **Endpoint:** GET `https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90`
- **Supported types:** `{IOCType.IPV4, IOCType.IPV6}`
- **Auth:** `Key` header from ConfigStore (`get_provider_key("abuseipdb")`)
- **requires_api_key:** True
- **Verdict logic:**
  - `abuseConfidenceScore >= 75` -> "malicious"
  - `25 <= score < 75` -> "suspicious"
  - `score < 25 && totalReports > 0` -> "clean"
  - `totalReports == 0` -> "no_data"
- **detection_count:** `totalReports`
- **total_engines:** `numDistinctUsers`
- **ALLOWED_API_HOSTS:** Add `"api.abuseipdb.com"` to config.py
- **raw_stats:** Include abuseConfidenceScore, totalReports, numDistinctUsers, countryCode, isp, usageType, lastReportedAt

Write tests covering: high-confidence malicious, suspicious, low-confidence clean, no reports (no_data), timeout, SSRF, rate limit (429).

**Commit:** `feat(26-04): add AbuseIPDB adapter`

---

### Task 26.5: Register All New Providers in Registry

**Files:**
- Modify: `app/enrichment/setup.py`
- Modify: `app/config.py` (finalize ALLOWED_API_HOSTS)
- Test: Update `tests/test_registry_setup.py`

Add all 4 new providers to `build_registry()` in `app/enrichment/setup.py`. For providers requiring API keys, read from ConfigStore:

```python
    # URLhaus (key from providers section)
    urlhaus_key = config_store.get_provider_key("urlhaus") or ""
    registry.register(URLhausAdapter(api_key=urlhaus_key, allowed_hosts=allowed_hosts))

    # OTX (key from providers section)
    otx_key = config_store.get_provider_key("otx") or ""
    registry.register(OTXAdapter(api_key=otx_key, allowed_hosts=allowed_hosts))

    # GreyNoise (key from providers section)
    gn_key = config_store.get_provider_key("greynoise") or ""
    registry.register(GreyNoiseAdapter(api_key=gn_key, allowed_hosts=allowed_hosts))

    # AbuseIPDB (key from providers section)
    abuseipdb_key = config_store.get_provider_key("abuseipdb") or ""
    registry.register(AbuseIPDBAdapter(api_key=abuseipdb_key, allowed_hosts=allowed_hosts))
```

Final `ALLOWED_API_HOSTS` in `app/config.py`:
```python
    ALLOWED_API_HOSTS: list[str] = [
        "www.virustotal.com",
        "mb-api.abuse.ch",
        "threatfox-api.abuse.ch",
        "internetdb.shodan.io",
        "urlhaus-api.abuse.ch",
        "otx.alienvault.com",
        "api.greynoise.io",
        "api.abuseipdb.com",
    ]
```

Write test: `test_build_registry_has_eight_providers` that verifies all 8 provider names.

**Commit:** `feat(26-05): register all new providers in registry`

---

### Task 26.6: Settings Page Multi-Provider Key Management

**Files:**
- Modify: `app/routes.py` (settings_get, settings_post)
- Modify: `app/templates/settings.html`
- Modify: `app/enrichment/setup.py` (add provider metadata list)

**Step 1: Add provider metadata for the settings page**

Create a provider info list in `app/enrichment/setup.py`:

```python
PROVIDER_INFO = [
    {
        "id": "virustotal",
        "name": "VirusTotal",
        "requires_key": True,
        "signup_url": "https://www.virustotal.com/gui/join-us",
        "description": "IP, domain, URL, hash enrichment",
    },
    {
        "id": "urlhaus",
        "name": "URLhaus",
        "requires_key": True,
        "signup_url": "https://auth.abuse.ch/",
        "description": "URL, hash, IP, domain — malware distribution tracking",
    },
    {
        "id": "otx",
        "name": "OTX AlienVault",
        "requires_key": True,
        "signup_url": "https://otx.alienvault.com/api",
        "description": "All IOC types including CVE — community threat intel",
    },
    {
        "id": "greynoise",
        "name": "GreyNoise",
        "requires_key": True,
        "signup_url": "https://www.greynoise.io/",
        "description": "IP only — internet scanner noise classification",
    },
    {
        "id": "abuseipdb",
        "name": "AbuseIPDB",
        "requires_key": True,
        "signup_url": "https://www.abuseipdb.com/register",
        "description": "IP only — crowd-sourced abuse reporting",
    },
]
```

**Step 2: Update settings routes**

`settings_get()` — pass provider info + current key status:
```python
    config_store = ConfigStore()
    providers_with_status = []
    for info in PROVIDER_INFO:
        pid = info["id"]
        if pid == "virustotal":
            key = config_store.get_vt_api_key()
        else:
            key = config_store.get_provider_key(pid)
        providers_with_status.append({
            **info,
            "masked_key": _mask_key(key),
            "configured": key is not None,
        })
    return render_template("settings.html", providers=providers_with_status)
```

`settings_post()` — accept provider_id + api_key:
```python
    provider_id = request.form.get("provider_id", "").strip()
    api_key = request.form.get("api_key", "").strip()
    if not api_key:
        flash("API key cannot be empty.", "error")
        return redirect(url_for("main.settings_get"))
    config_store = ConfigStore()
    if provider_id == "virustotal":
        config_store.set_vt_api_key(api_key)
    else:
        config_store.set_provider_key(provider_id, api_key)
    flash(f"API key saved for {provider_id}.", "success")
    return redirect(url_for("main.settings_get"))
```

**Step 3: Update settings.html template**

Replace single VT form with a loop over providers:
```html
{% for provider in providers %}
<section class="settings-section">
    <h2 class="settings-section-title">
        {{ provider.name }}
        {% if provider.configured %}
        <span class="status-dot status-dot--active"></span>
        <span class="status-label">Configured</span>
        {% else %}
        <span class="status-dot status-dot--inactive"></span>
        <span class="status-label">Not configured</span>
        {% endif %}
    </h2>
    <p class="settings-info">{{ provider.description }}</p>
    {% if provider.signup_url %}
    <p class="settings-info">
        <a href="{{ provider.signup_url }}" target="_blank" rel="noopener">Get a free API key</a>
    </p>
    {% endif %}
    <form method="post" action="{{ url_for('main.settings_post') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
        <input type="hidden" name="provider_id" value="{{ provider.id }}"/>
        <div class="form-field">
            <label for="api-key-{{ provider.id }}">API Key</label>
            <div class="input-group">
                <input type="password"
                       id="api-key-{{ provider.id }}"
                       name="api_key"
                       value="{{ provider.masked_key or '' }}"
                       placeholder="Paste your {{ provider.name }} API key"
                       autocomplete="off" spellcheck="false"/>
            </div>
        </div>
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save</button>
        </div>
    </form>
</section>
{% endfor %}
```

**Step 4: Update settings.ts for multiple show/hide toggles**

If needed, update `app/static/src/ts/modules/settings.ts` to handle multiple password fields (one per provider).

**Step 5: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`

**Step 6: Commit**

```bash
git add app/routes.py app/templates/settings.html app/enrichment/setup.py \
       app/static/src/ts/modules/settings.ts app/static/dist/main.js
git commit -m "feat(26-06): multi-provider settings page with key management"
```

---

## Phase 27: Results UX Upgrade

**Goal:** Unified summary per IOC card with expandable per-provider details and provider consensus.

### Task 27.1: Update IOC Card Template for Expandable Details

**Files:**
- Modify: `app/templates/partials/_ioc_card.html`
- Modify: `app/static/src/ts/modules/enrichment.ts`
- Modify: `app/static/src/ts/modules/cards.ts`

**Step 1: Update _ioc_card.html**

Add a details container inside each card that enrichment.ts will populate:

```html
<!-- Inside the IOC card, after the verdict badge area -->
<div class="ioc-card__summary" data-role="summary">
    <!-- Populated by enrichment.ts: worst verdict + provider agreement -->
</div>
<button class="ioc-card__expand-btn" data-role="expand-toggle" style="display:none;">
    Show details (0 providers)
</button>
<div class="ioc-card__details" data-role="provider-details" style="display:none;">
    <!-- Populated by enrichment.ts: per-provider result rows -->
</div>
```

**Step 2: Update enrichment.ts**

Modify the result rendering logic to:
1. Render each provider result as a row inside `[data-role="provider-details"]`
2. Compute unified summary (worst verdict + agreement count) and render in `[data-role="summary"]`
3. Show the expand toggle button with provider count
4. Toggle `[data-role="provider-details"]` visibility on button click

Key TypeScript additions (use textContent for all user-facing data — never use dynamic HTML injection with untrusted content):
```typescript
function renderProviderRow(card: HTMLElement, item: EnrichmentResultItem): void {
    const details = card.querySelector('[data-role="provider-details"]');
    if (!details) return;
    const row = document.createElement('div');
    row.className = 'provider-row';
    // Build using createElement + textContent for XSS safety
    const nameEl = document.createElement('span');
    nameEl.className = 'provider-row__name';
    nameEl.textContent = item.provider;
    row.appendChild(nameEl);
    // ... add verdict badge, stats using same safe DOM pattern
    details.appendChild(row);
}

function updateSummary(card: HTMLElement, results: EnrichmentResultItem[]): void {
    const summary = card.querySelector('[data-role="summary"]');
    if (!summary) return;
    const worstVerdict = computeWorstVerdict(results);
    const flaggedCount = results.filter(
        r => r.verdict === 'malicious' || r.verdict === 'suspicious'
    ).length;
    // Update summary using textContent (safe)
    summary.textContent = '';
    const text = document.createElement('span');
    text.textContent = `${flaggedCount}/${results.length} providers flagged`;
    summary.appendChild(text);
}

function setupExpandToggle(card: HTMLElement): void {
    const btn = card.querySelector('[data-role="expand-toggle"]') as HTMLButtonElement | null;
    const details = card.querySelector('[data-role="provider-details"]');
    if (!btn || !details) return;
    btn.style.display = '';
    btn.addEventListener('click', () => {
        const expanded = details.style.display !== 'none';
        details.style.display = expanded ? 'none' : '';
        btn.textContent = expanded ? 'Show details' : 'Hide details';
    });
}
```

**Step 3: Add CSS for provider rows and expand/collapse**

Add to `app/static/src/input.css`:
```css
/* Provider detail rows inside IOC cards */
.provider-row { /* ... styling ... */ }
.ioc-card__expand-btn { /* ... styling ... */ }
.ioc-card__details { /* ... styling ... */ }
.ioc-card__summary { /* ... styling ... */ }
```

**Step 4: Build and test**

Run: `make build && make typecheck`
Run: `python -m pytest tests/ -v --tb=short`

**Step 5: Commit**

```bash
git add app/templates/partials/_ioc_card.html \
       app/static/src/ts/modules/enrichment.ts \
       app/static/src/ts/modules/cards.ts \
       app/static/src/input.css \
       app/static/dist/main.js app/static/dist/style.css
git commit -m "feat(27-01): unified summary + expandable provider details per IOC card"
```

---

### Task 27.2: Provider Consensus Indicator

**Files:**
- Modify: `app/static/src/ts/modules/enrichment.ts`
- Modify: `app/static/src/input.css`

Add a visual consensus indicator to each IOC card summary:
- "5/8 providers flagged" with color coding (green if 0, yellow if 1-2, red if 3+)
- Only counts providers that returned a result (not errors or no_data)

**Commit:** `feat(27-02): add provider consensus indicator to IOC cards`

---

### Task 27.3: Dashboard Provider Coverage

**Files:**
- Modify: `app/templates/partials/_verdict_dashboard.html`
- Modify: `app/static/src/ts/modules/cards.ts`

Add a "Provider Coverage" section to the verdict dashboard:
- "8 providers registered, 5 configured"
- Small badges per provider showing active/inactive status

Pass provider status info from `routes.py` via template variable.

**Commit:** `feat(27-03): add provider coverage to verdict dashboard`

---

### Task 27.4: Update TypeScript Type for CVE Support

**Files:**
- Modify: `app/static/src/ts/types/ioc.ts`

Add `"cve"` to the `IocType` union now that OTX supports it:

```typescript
export type IocType =
  | "ipv4"
  | "ipv6"
  | "domain"
  | "url"
  | "md5"
  | "sha1"
  | "sha256"
  | "cve";
```

Update `getProviderCounts()` fallback to include CVE.

**Commit:** `feat(27-04): add CVE to TypeScript IocType for OTX support`

---

### Task 27.5: Final Integration Test

**Files:**
- Modify: existing E2E tests or create `tests/test_e2e_providers.py`

Run the full test suite and E2E tests:

```bash
python -m pytest tests/ -v --tb=short
make build && make typecheck
# E2E if Playwright available:
python -m pytest tests/ -k "e2e" -v --tb=short
```

Verify:
- [ ] All 8 providers register correctly
- [ ] Settings page shows all providers with status
- [ ] Offline mode still works (zero network calls)
- [ ] Online mode enriches across all configured providers
- [ ] Results show unified summary + expandable details
- [ ] TypeScript builds cleanly with no errors
- [ ] All existing tests still pass

**Commit:** `test(27-05): verify full integration of universal search hub`

---

## Summary

| Phase | Tasks | What It Delivers |
|-------|-------|-----------------|
| 24 | 5 tasks | Provider protocol, registry, ConfigStore expansion, routes refactor, dynamic TS counts |
| 25 | 2 tasks | Shodan InternetDB (zero-auth, IP enrichment) |
| 26 | 6 tasks | URLhaus + OTX + GreyNoise + AbuseIPDB + multi-provider settings page |
| 27 | 5 tasks | Unified summary cards, expandable details, consensus indicator, dashboard coverage |

**Total: 18 tasks across 4 phases**

Each task follows TDD: write failing test -> implement -> verify -> commit.
