"""Abstract base class for HTTP-based enrichment adapters.

Provides the shared skeleton that all HTTP adapters follow:
  - Session creation with auth headers
  - is_configured() logic (api_key-gated or always-on)
  - Template-method lookup(): type guard → build URL → safe_request → parse

Subclasses define:
  - name, supported_types, requires_api_key (class-level)
  - _build_url(ioc) → str  (abstract)
  - _parse_response(ioc, body) → EnrichmentResult  (abstract)

Optional overrides:
  - _auth_headers() → dict (default: empty)
  - _make_pre_raise_hook(ioc) → callable | None (default: None)
  - _http_method: str class var (default: "GET")
  - _build_request_body(ioc) → (data, json_payload) tuple (default: (None, None))

Does NOT inherit from Provider — structural duck typing satisfies the protocol.
Does NOT import any adapter-specific module.
"""
from __future__ import annotations

import abc
import logging

import requests

from app.enrichment.http_safety import safe_request
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)


class BaseHTTPAdapter(abc.ABC):
    """Abstract base for HTTP-backed enrichment adapters.

    Absorbs the boilerplate every HTTP adapter repeats: session setup,
    is_configured() gating, type guard, safe_request() dispatch, and
    response parsing.  Subclasses plug in URL construction and response
    interpretation; everything else is inherited.

    Class attributes that subclasses MUST define:
        name:             str — human-readable provider name.
        supported_types:  frozenset[IOCType] — IOC types this adapter handles.
        requires_api_key: bool — whether an API key is needed.

    Args:
        allowed_hosts: SSRF allowlist (SEC-16).
        api_key:       Optional API key (keyword-only, default empty string).
    """

    # --- Subclass MUST define these -------------------------------------------
    name: str
    supported_types: frozenset[IOCType]
    requires_api_key: bool

    # --- Override points with sensible defaults --------------------------------
    _http_method: str = "GET"

    def __init__(self, allowed_hosts: list[str], *, api_key: str = "") -> None:
        self._allowed_hosts = allowed_hosts
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update(self._auth_headers())

    # --- Template method: the adapter contract ---------------------------------

    def is_configured(self) -> bool:
        """Return True if this adapter is ready to make requests.

        Key-required adapters: True only when a non-empty api_key is set.
        Public adapters: always True.
        """
        if self.requires_api_key:
            return bool(self._api_key)
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IOC via the template-method pipeline.

        Steps:
          1. Reject unsupported IOC types.
          2. Build the request URL via _build_url().
          3. Build optional pre-raise hook via _make_pre_raise_hook().
          4. Build optional request body via _build_request_body().
          5. Dispatch through safe_request().
          6. If safe_request returned an error, propagate it.
          7. Parse the JSON body via _parse_response().

        Args:
            ioc: The IOC to look up.

        Returns:
            EnrichmentResult on success, EnrichmentError on failure.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type",
            )

        url = self._build_url(ioc)
        hook = self._make_pre_raise_hook(ioc)
        data, json_payload = self._build_request_body(ioc)

        result = safe_request(
            self._session,
            url,
            self._allowed_hosts,
            ioc,
            self.name,
            method=self._http_method,
            data=data,
            json_payload=json_payload,
            pre_raise_hook=hook,
        )

        if not isinstance(result, dict):
            return result

        return self._parse_response(ioc, result)

    # --- Abstract methods subclasses MUST implement ----------------------------

    @abc.abstractmethod
    def _build_url(self, ioc: IOC) -> str:
        """Return the full request URL for this IOC."""

    @abc.abstractmethod
    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        """Parse a successful JSON response into an EnrichmentResult."""

    # --- Override points (safe defaults) ---------------------------------------

    def _auth_headers(self) -> dict:
        """Return extra headers to set on the session.

        Override in subclasses that need API-key or custom auth headers.
        Default: no extra headers.
        """
        return {}

    def _make_pre_raise_hook(self, ioc: IOC):
        """Return a pre-raise hook callback, or None.

        The hook receives the raw ``requests.Response`` before
        ``raise_for_status()``.  If it returns a non-None value, that
        value short-circuits the pipeline (e.g. 404 → no_data).

        Default: None (no hook).
        """
        return None

    def _build_request_body(self, ioc: IOC) -> tuple[dict | None, dict | None]:
        """Return (form-data, json-payload) for POST requests.

        First element is form-encoded ``data``; second is JSON ``json_payload``.
        Default: (None, None) — appropriate for GET adapters.
        """
        return (None, None)
