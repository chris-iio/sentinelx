---
estimated_steps: 3
estimated_files: 12
---

# T02: Add ConnectionError/SSLError handlers to requests-based adapters

**Slice:** S01 — Backend Concurrency & Error Correctness
**Milestone:** M004

## Description

Add explicit `requests.exceptions.SSLError` and `requests.exceptions.ConnectionError` exception handlers to all 12 requests-based adapters. Currently, these exceptions are silently caught by the blanket `except Exception` handler, producing the unhelpful message "Unexpected error during lookup". The new handlers produce actionable error strings: "SSL/TLS error" and "Connection failed".

**Critical ordering constraint:** `SSLError` is a subclass of `ConnectionError` in the `requests` library. The `except SSLError` clause MUST appear BEFORE `except ConnectionError` in each adapter, or SSLError will be caught by the ConnectionError handler and the more specific "SSL/TLS error" message will never fire.

**Scope:** Only the 12 adapters that use `requests`. Do NOT modify:
- `app/enrichment/adapters/asn_cymru.py` — uses `dns.resolver` (socket-based), not `requests`
- `app/enrichment/adapters/dns_lookup.py` — uses `dnspython`, not `requests`

## Steps

1. **Apply the same two-handler pattern to all 12 adapter files.** In each file, locate the `except Exception:` block in the `lookup()` method and insert these two handlers immediately before it:

   ```python
   except requests.exceptions.SSLError:
       return EnrichmentError(
           ioc=ioc, provider=self.name, error="SSL/TLS error"
       )
   except requests.exceptions.ConnectionError:
       return EnrichmentError(
           ioc=ioc, provider=self.name, error="Connection failed"
       )
   ```

   The existing `except requests.exceptions.Timeout:` and `except requests.exceptions.HTTPError as exc:` handlers remain unchanged. The existing `except Exception:` handler also remains unchanged as the final catch-all.

   The 12 files to edit (in alphabetical order):
   - `app/enrichment/adapters/abuseipdb.py`
   - `app/enrichment/adapters/crtsh.py`
   - `app/enrichment/adapters/greynoise.py`
   - `app/enrichment/adapters/hashlookup.py`
   - `app/enrichment/adapters/ip_api.py`
   - `app/enrichment/adapters/malwarebazaar.py`
   - `app/enrichment/adapters/otx.py`
   - `app/enrichment/adapters/shodan.py`
   - `app/enrichment/adapters/threatfox.py`
   - `app/enrichment/adapters/threatminer.py`
   - `app/enrichment/adapters/urlhaus.py`
   - `app/enrichment/adapters/virustotal.py`

   **Note on `virustotal.py`:** This adapter uses `provider="VirusTotal"` (hardcoded string) instead of `self.name` in its error returns. Match the existing pattern — use `provider="VirusTotal"` for consistency.

   **Note on indentation:** Each adapter may have slightly different indentation depths for the try/except block. Match the indentation of the existing `except requests.exceptions.Timeout:` line in each file.

2. **Verify exception handler ordering.** After all edits, confirm that in every file the order is: `Timeout` → `HTTPError` → `SSLError` → `ConnectionError` → `Exception`. The SSLError handler MUST precede ConnectionError.

3. **Run the full test suite** to ensure no regressions. The new handlers should not change any existing test behavior because no existing tests mock `ConnectionError` or `SSLError` — they're currently caught by the blanket handler.

## Must-Haves

- [ ] All 12 requests-based adapters have `except requests.exceptions.SSLError` returning `error="SSL/TLS error"`
- [ ] All 12 requests-based adapters have `except requests.exceptions.ConnectionError` returning `error="Connection failed"`
- [ ] `SSLError` handler precedes `ConnectionError` handler in every file
- [ ] `asn_cymru.py` and `dns_lookup.py` are NOT modified
- [ ] Existing `except Exception` handler preserved in all files
- [ ] Full test suite passes with no regressions

## Verification

- `rg 'SSLError' app/enrichment/adapters/ --type py -c` → exactly 12 files (not asn_cymru.py, not dns_lookup.py)
- `rg 'ConnectionError' app/enrichment/adapters/ --type py -c` → exactly 12 files
- `rg 'Unexpected error' app/enrichment/adapters/ --type py -c` → still 14 files (blanket handler preserved)
- `python3 -m pytest tests/ -x -q` → 933+ pass, 0 fail

## Inputs

- `app/enrichment/adapters/abuseipdb.py` — existing adapter with Timeout/HTTPError/Exception pattern
- `app/enrichment/adapters/crtsh.py` — existing adapter
- `app/enrichment/adapters/greynoise.py` — existing adapter
- `app/enrichment/adapters/hashlookup.py` — existing adapter
- `app/enrichment/adapters/ip_api.py` — existing adapter
- `app/enrichment/adapters/malwarebazaar.py` — existing adapter
- `app/enrichment/adapters/otx.py` — existing adapter
- `app/enrichment/adapters/shodan.py` — existing adapter
- `app/enrichment/adapters/threatfox.py` — existing adapter
- `app/enrichment/adapters/threatminer.py` — existing adapter
- `app/enrichment/adapters/urlhaus.py` — existing adapter
- `app/enrichment/adapters/virustotal.py` — existing adapter

## Expected Output

- `app/enrichment/adapters/abuseipdb.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/crtsh.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/greynoise.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/hashlookup.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/ip_api.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/malwarebazaar.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/otx.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/shodan.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/threatfox.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/threatminer.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/urlhaus.py` — SSLError + ConnectionError handlers added
- `app/enrichment/adapters/virustotal.py` — SSLError + ConnectionError handlers added
