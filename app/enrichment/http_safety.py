"""Shared HTTP safety utilities for enrichment adapters.

Centralizes the security controls applied to all outbound API requests:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-16: SSRF allowlist enforcement before every network call

Each adapter imports these instead of duplicating the logic.

safe_request() is the single canonical HTTP+exception path for all adapters.
Adapters call it instead of making raw requests — it handles SSRF validation,
streaming reads, byte limits, and the full exception chain.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from app.enrichment.models import EnrichmentError, IOC

logger = logging.getLogger(__name__)


TIMEOUT = (5, 30)  # (connect, read) — SEC-04
MAX_RESPONSE_BYTES = 1 * 1024 * 1024  # 1 MB cap — SEC-05


def validate_endpoint(url: str, allowed_hosts: list[str]) -> None:
    """Raise ValueError if endpoint hostname is not on the SSRF allowlist.

    Enforces SEC-16: no outbound calls to hosts outside ALLOWED_API_HOSTS.
    Called before every network request.

    Args:
        url:           The full URL to be requested.
        allowed_hosts: SSRF allowlist of permitted hostnames.

    Raises:
        ValueError: If the URL hostname is not in the allowlist.
    """
    parsed = urlparse(url)
    if parsed.hostname not in allowed_hosts:
        raise ValueError(
            f"Endpoint hostname {parsed.hostname!r} not in allowed_hosts "
            f"(SSRF allowlist SEC-16). Allowed: {allowed_hosts!r}"
        )


def read_limited(resp: requests.Response) -> dict:
    """Read streaming response with byte cap (SEC-05).

    Reads response body in 8 KB chunks. Raises ValueError if total
    exceeds MAX_RESPONSE_BYTES before completing. Returns parsed JSON.

    Args:
        resp: An open streaming requests.Response.

    Raises:
        ValueError: If response body exceeds MAX_RESPONSE_BYTES.
        json.JSONDecodeError: If body is not valid JSON.
    """
    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise ValueError(
                f"Response exceeded size limit of {MAX_RESPONSE_BYTES} bytes (SEC-05)"
            )
        chunks.append(chunk)
    return json.loads(b"".join(chunks))


def safe_request(
    session: requests.Session,
    url: str,
    allowed_hosts: list[str],
    ioc: IOC,
    provider: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    json_payload: dict[str, Any] | None = None,
    pre_raise_hook: Callable[[requests.Response], Any | None] | None = None,
) -> dict | EnrichmentError:
    """Canonical HTTP request path for all enrichment adapters.

    Wraps SSRF validation, HTTP dispatch, byte-limited streaming read,
    and the full exception chain in one call.  Adapters build URL/params,
    then delegate here instead of duplicating HTTP + error handling.

    Uses ``getattr(session, method.lower())`` dispatch so that existing
    test mocks on ``session.get`` / ``session.post`` continue to work.

    Exception handler ordering is a correctness constraint — SSLError
    MUST be caught before ConnectionError (SSLError is a subclass).

    Args:
        session:        requests.Session with auth headers pre-configured.
        url:            Full request URL.
        allowed_hosts:  SSRF allowlist (SEC-16).
        ioc:            The IOC being looked up (used for error context).
        provider:       Provider name (used for error context).
        method:         HTTP method — 'GET' or 'POST'.
        data:           Form-encoded body (POST only).
        json_payload:   JSON body (POST only).  Named to avoid shadowing
                        the ``json`` stdlib module.
        pre_raise_hook: Optional callback invoked with the raw Response
                        *before* raise_for_status().  If the hook returns
                        a non-None value, that value is returned immediately
                        (short-circuit for 404→no_data patterns).

    Returns:
        Parsed JSON body as dict on success, or EnrichmentError on failure.
    """
    try:
        validate_endpoint(url, allowed_hosts)

        dispatch = getattr(session, method.lower())
        resp = dispatch(
            url,
            timeout=TIMEOUT,
            allow_redirects=False,
            stream=True,
            data=data,
            json=json_payload,
        )

        if pre_raise_hook is not None:
            hook_result = pre_raise_hook(resp)
            if hook_result is not None:
                return hook_result

        resp.raise_for_status()
        body = read_limited(resp)
        return body

    except requests.exceptions.Timeout:
        return EnrichmentError(ioc=ioc, provider=provider, error="Request timed out")
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        return EnrichmentError(ioc=ioc, provider=provider, error=f"HTTP {status}")
    except requests.exceptions.SSLError:
        return EnrichmentError(ioc=ioc, provider=provider, error="SSL/TLS error")
    except requests.exceptions.ConnectionError:
        return EnrichmentError(ioc=ioc, provider=provider, error="Connection failed")
    except ValueError as exc:
        return EnrichmentError(
            ioc=ioc, provider=provider, error="Endpoint validation failed"
        )
    except Exception as exc:
        logger.warning(
            "safe_request unexpected error provider=%s ioc=%s: %s",
            provider, ioc.value, exc,
        )
        return EnrichmentError(ioc=ioc, provider=provider, error=str(exc))
