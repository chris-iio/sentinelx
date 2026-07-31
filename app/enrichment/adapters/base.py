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
  - _no_data_on_404: bool (default: False)
  - _rate_limit_on_429: bool (default: False)
  - _http_method: str class var (default: "GET")
  - _build_request_body(ioc) → (data, json_payload) tuple (default: (None, None))

Does NOT inherit from Provider — structural duck typing satisfies the protocol.
Does NOT import any adapter-specific module.
"""
from __future__ import annotations

import abc
import threading
from collections.abc import Collection, Mapping
from types import MappingProxyType
from typing import Any

import requests

from ..http_safety import safe_request
from ..models import EnrichmentError, EnrichmentResult, error_result, no_data_result
from app.pipeline.models import IOC, IOCType

_EMPTY_AUTH_HEADERS: Mapping[str, str] = MappingProxyType({})
_EMPTY_ALLOWED_HOSTS: frozenset[str] = frozenset()


def _allowed_hosts_membership(allowed_hosts: Collection[str]) -> frozenset[str]:
    if isinstance(allowed_hosts, frozenset):
        return allowed_hosts
    if not allowed_hosts:
        return _EMPTY_ALLOWED_HOSTS
    if isinstance(allowed_hosts, (list, tuple)):
        host_count = len(allowed_hosts)
        if host_count == 1:
            return frozenset((allowed_hosts[0],))
        if host_count == 2:
            return frozenset((allowed_hosts[0], allowed_hosts[1]))
        if host_count == 3:
            return frozenset((allowed_hosts[0], allowed_hosts[1], allowed_hosts[2]))
        if host_count == 4:
            return frozenset((
                allowed_hosts[0],
                allowed_hosts[1],
                allowed_hosts[2],
                allowed_hosts[3],
            ))
    return frozenset(allowed_hosts)


def _auth_headers_snapshot(headers: Mapping[str, str]) -> Mapping[str, str]:
    """Return an immutable auth-header snapshot without constructor-copying."""
    if not headers:
        return _EMPTY_AUTH_HEADERS
    header_count = len(headers)
    if header_count == 1:
        for key in headers:
            return MappingProxyType({key: headers[key]})
    if header_count == 2:
        key_iter = iter(headers)
        first = next(key_iter)
        second = next(key_iter)
        return MappingProxyType({
            first: headers[first],
            second: headers[second],
        })
    if header_count == 3:
        key_iter = iter(headers)
        first = next(key_iter)
        second = next(key_iter)
        third = next(key_iter)
        return MappingProxyType({
            first: headers[first],
            second: headers[second],
            third: headers[third],
        })
    if header_count == 4:
        key_iter = iter(headers)
        first = next(key_iter)
        second = next(key_iter)
        third = next(key_iter)
        fourth = next(key_iter)
        return MappingProxyType({
            first: headers[first],
            second: headers[second],
            third: headers[third],
            fourth: headers[fourth],
        })

    copied_headers: dict[str, str] = {}
    for key in headers:
        append_auth_header_snapshot(copied_headers, headers, key)
    return MappingProxyType(copied_headers)


def append_auth_header_snapshot(
    copied_headers: dict[str, str],
    headers: Mapping[str, str],
    key: str,
) -> None:
    copied_headers[key] = headers[key]


def _no_data_on_404_hook(ioc: IOC, provider: str):
    def _hook(resp):
        if resp.status_code == 404:
            return no_data_result(ioc, provider)
        return None

    return _hook


def _rate_limit_on_429(resp, ioc: IOC, provider: str):
    if resp.status_code == 429:
        return error_result(ioc, provider, "Rate limit exceeded (429)")
    return None


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
    _no_data_on_404: bool = False
    _rate_limit_on_429: bool = False

    def __init__(self, allowed_hosts: Collection[str], *, api_key: str = "") -> None:
        self._allowed_hosts = _allowed_hosts_membership(allowed_hosts)
        self._api_key = api_key
        self._session_state = threading.local()
        self._auth_header_cache = _auth_headers_snapshot(self._auth_headers())
        self._session = self._new_session()

    @property
    def _session(self) -> requests.Session:
        session = getattr(self._session_state, "session", None)
        if session is None:
            session = self._new_session()
            self._session_state.session = session
        return session

    @_session.setter
    def _session(self, session: requests.Session) -> None:
        self._session_state.session = session

    def _new_session(self) -> requests.Session:
        session = requests.Session()
        if self._auth_header_cache:
            session.headers.update(self._auth_header_cache)
        return session

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
          6. If safe_request returned a terminal result/error, propagate it.
          7. Parse the JSON body via _parse_response().

        Args:
            ioc: The IOC to look up.

        Returns:
            EnrichmentResult on success, EnrichmentError on failure.
        """
        if ioc.type not in self.supported_types:
            return error_result(ioc, self.name, "Unsupported type")

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

        if isinstance(result, (EnrichmentError, EnrichmentResult)):
            return result

        return self._parse_response(ioc, result)

    # --- Abstract methods subclasses MUST implement ----------------------------

    @abc.abstractmethod
    def _build_url(self, ioc: IOC) -> str:
        """Return the full request URL for this IOC."""

    @abc.abstractmethod
    def _parse_response(self, ioc: IOC, body: Any) -> EnrichmentResult:
        """Parse a successful JSON response into an EnrichmentResult."""

    # --- Override points (safe defaults) ---------------------------------------

    def _auth_headers(self) -> Mapping[str, str]:
        """Return extra headers to set on the session.

        Override in subclasses that need API-key or custom auth headers.
        Default: no extra headers.
        """
        return _EMPTY_AUTH_HEADERS

    def _make_pre_raise_hook(self, ioc: IOC):
        """Return a pre-raise hook callback, or None.

        The hook receives the raw ``requests.Response`` before
        ``raise_for_status()``.  If it returns a non-None value, that
        value short-circuits the pipeline (e.g. 404 → no_data).

        Default: build a hook from declarative generic status policies, or
        return None when no generic policy is enabled.
        """
        if not self._no_data_on_404 and not self._rate_limit_on_429:
            return None

        no_data_on_404 = (
            _no_data_on_404_hook(ioc, self.name) if self._no_data_on_404 else None
        )

        def _hook(resp):
            if no_data_on_404 is not None:
                no_data = no_data_on_404(resp)
                if no_data is not None:
                    return no_data
            if self._rate_limit_on_429:
                rate_limit = _rate_limit_on_429(resp, ioc, self.name)
                if rate_limit is not None:
                    return rate_limit
            return None

        return _hook

    def _build_request_body(self, ioc: IOC) -> tuple[dict | None, dict | None]:
        """Return (form-data, json-payload) for POST requests.

        First element is form-encoded ``data``; second is JSON ``json_payload``.
        Default: (None, None) — appropriate for GET adapters.
        """
        return (None, None)
