---
id: T02
parent: S01
milestone: M004
provides:
  - All 12 requests-based adapters now catch SSLError with error="SSL/TLS error" before the ConnectionError handler
  - All 12 requests-based adapters now catch ConnectionError with error="Connection failed" before the blanket Exception handler
  - asn_cymru.py and dns_lookup.py untouched (dns.resolver-based, not requests)
key_files:
  - app/enrichment/adapters/abuseipdb.py
  - app/enrichment/adapters/crtsh.py
  - app/enrichment/adapters/greynoise.py
  - app/enrichment/adapters/hashlookup.py
  - app/enrichment/adapters/ip_api.py
  - app/enrichment/adapters/malwarebazaar.py
  - app/enrichment/adapters/otx.py
  - app/enrichment/adapters/shodan.py
  - app/enrichment/adapters/threatfox.py
  - app/enrichment/adapters/threatminer.py
  - app/enrichment/adapters/urlhaus.py
  - app/enrichment/adapters/virustotal.py
key_decisions:
  - Used hardcoded provider strings ("MalwareBazaar", "ThreatFox", "VirusTotal") in the three adapters that already used string literals for other exception handlers, matching existing per-file convention
  - SSLError handler always precedes ConnectionError handler — SSLError is a subclass of ConnectionError in requests, so ordering is critical
patterns_established:
  - Exception handler ordering in requests adapters: Timeout → HTTPError → SSLError → ConnectionError → Exception (blanket)
  - SSLError-before-ConnectionError is a safety constraint when both are present, not a style preference
observability_surfaces:
  - EnrichmentError.error field now has four distinct values for network failures: "Timeout", "SSL/TLS error", "Connection failed", "Unexpected error during lookup" — log messages from adapter-level logger.exception() calls include provider name and IOC value
duration: ~10 minutes
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Add ConnectionError/SSLError handlers to requests-based adapters

**Added explicit SSLError and ConnectionError exception handlers to all 12 requests-based adapters, replacing silent "Unexpected error during lookup" catch-all with actionable "SSL/TLS error" and "Connection failed" messages.**

## What Happened

Inserted two new exception handlers immediately before `except Exception:` in every requests-based adapter's `lookup()` method:

```python
except requests.exceptions.SSLError:
    return EnrichmentError(ioc=ioc, provider=self.name, error="SSL/TLS error")
except requests.exceptions.ConnectionError:
    return EnrichmentError(ioc=ioc, provider=self.name, error="Connection failed")
```

Three adapters (`malwarebazaar.py`, `threatfox.py`, `virustotal.py`) already used hardcoded provider name strings for their other error returns; the new handlers matched that existing convention. The `virustotal.py` adapter has a slightly different `HTTPError` handler (delegates to `_map_http_error()`), but the SSLError/ConnectionError insertions were identical.

The critical subclass ordering constraint was validated: in all 12 files, the line number of `SSLError` is less than `ConnectionError` which is less than the bare `Exception` handler. Since `SSLError` inherits from `ConnectionError` in the `requests` library, reversing this order would silently drop the more specific SSL message.

The two non-requests adapters (`asn_cymru.py`, `dns_lookup.py`) were confirmed to have zero matches for `SSLError`/`ConnectionError` — they were not modified.

## Verification

All four task-plan verification commands and two slice-level checks were run:

```
rg 'SSLError' app/enrichment/adapters/ --type py -c    → 12 files (1 match each)
rg 'ConnectionError' app/enrichment/adapters/ --type py -c → 12 files (1 match each)
rg 'Unexpected error' app/enrichment/adapters/ --type py -c → 14 files (blanket handler preserved)
python3 -m pytest tests/ -x -q                         → 936 passed, 0 failed
python3 -m pytest tests/test_orchestrator.py -v        → 27 passed (all T01 tests still green)
python3 -c "from app.enrichment.orchestrator import _BACKOFF_BASE, _MAX_RATE_LIMIT_RETRIES; print('OK')" → OK
```

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'SSLError' app/enrichment/adapters/ --type py -c` | 0 | ✅ pass | <1s |
| 2 | `rg 'ConnectionError' app/enrichment/adapters/ --type py -c` | 0 | ✅ pass | <1s |
| 3 | `rg 'Unexpected error' app/enrichment/adapters/ --type py -c` | 0 | ✅ pass | <1s |
| 4 | `python3 -m pytest tests/ -x -q` | 0 | ✅ pass | 44.37s (936 passed) |
| 5 | `python3 -m pytest tests/test_orchestrator.py -v` | 0 | ✅ pass | 6.27s (27 passed) |
| 6 | `python3 -c "from app.enrichment.orchestrator import _BACKOFF_BASE, _MAX_RATE_LIMIT_RETRIES; print('OK')"` | 0 | ✅ pass | <1s |

## Diagnostics

- `EnrichmentError.error` now distinguishes four network failure modes: `"Timeout"` (connect/read timeout), `"SSL/TLS error"` (certificate or TLS handshake failure), `"Connection failed"` (DNS failure, refused connection, unreachable host), `"Unexpected error during lookup"` (truly unknown exception).
- `logger.exception()` in the blanket `except Exception:` handler still fires with a stack trace for anything not covered by the specific handlers — these log entries include provider name and IOC value.
- To test the new handlers: mock `requests.get` (or `session.get` for VirusTotal) to raise `requests.exceptions.SSLError()` or `requests.exceptions.ConnectionError()` and assert the returned `EnrichmentError.error` value.

## Deviations

None — all changes followed the exact pattern described in the task plan.

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/adapters/abuseipdb.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/crtsh.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/greynoise.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/hashlookup.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/ip_api.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/malwarebazaar.py` — SSLError + ConnectionError handlers added before except Exception (uses hardcoded "MalwareBazaar" string)
- `app/enrichment/adapters/otx.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/shodan.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/threatfox.py` — SSLError + ConnectionError handlers added before except Exception (uses hardcoded "ThreatFox" string)
- `app/enrichment/adapters/threatminer.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/urlhaus.py` — SSLError + ConnectionError handlers added before except Exception
- `app/enrichment/adapters/virustotal.py` — SSLError + ConnectionError handlers added before except Exception (uses hardcoded "VirusTotal" string)
