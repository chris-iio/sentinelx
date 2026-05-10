---
estimated_steps: 25
estimated_files: 5
skills_used:
  - tdd
  - verify-before-complete
---

# T01: Harden EmailRep registry and settings metadata contracts

Expected executor skills_used frontmatter: `tdd`, `verify-before-complete`.

Add focused backend contract coverage for the EmailRep registry/settings layer before changing implementation. Inputs are the provider setup/registry/config files listed below; expected outputs are the focused test file plus only the source files needing fixes.

## Steps
1. Add `tests/test_emailrep_registry_settings.py` that builds a real `ProviderRegistry` with mocked `ConfigStore` responses for no EmailRep key and EmailRep-key-only states.
2. Assert `app.enrichment.setup.PROVIDER_INFO` contains an `emailrep` entry with name `EmailRep`, `requires_key=True`, HTTPS signup URL, and email-only `ioc_types`; assert `app.config.Config.ALLOWED_API_HOSTS` includes `emailrep.io`.
3. Assert `build_registry()` calls `get_provider_key("emailrep")`, registers EmailRep once, returns zero configured email providers without that key, and returns exactly one configured `EmailRep` provider for `IOCType.EMAIL` with the key.
4. Assert EmailRep does not appear in `providers_for_type()` for domains, URLs, IPs, hashes, or CVEs, preserving S01's email-only adapter boundary and existing OTX email exclusion.

## Must-Haves
- [ ] EmailRep registry behavior is proven through `ProviderRegistry.providers_for_type(IOCType.EMAIL)` and `provider_count_for_type(IOCType.EMAIL)`, not only by name lookup in `registry.all()`.
- [ ] Tests cover both no-key and key-present paths.
- [ ] Tests pin `emailrep.io` allowlist coverage and settings metadata without creating live network calls.
- [ ] If implementation fixes are needed, keep them in `app/enrichment/setup.py` and `app/config.py`; do not add a second registration path.

## Failure Modes
| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `ConfigStore.get_provider_key("emailrep")` | Treat as missing key and leave EmailRep unconfigured | Not applicable; config read is local and synchronous | Treat empty/non-string-equivalent values as unconfigured via existing adapter `is_configured()` behavior |
| `ALLOWED_API_HOSTS` | Adapter HTTP safety would reject EmailRep; test must fail before runtime | Not applicable | Stale or missing host entry fails the allowlist assertion |

## Load Profile
- **Shared resources**: Startup-time registry composition and a small in-memory provider list.
- **Per-operation cost**: O(number of providers) registry filtering; no HTTP, DB, or file writes in these tests.
- **10x breakpoint**: Provider list growth would make broad assertions harder to maintain, so tests should assert EmailRep-specific membership and counts rather than a brittle full ordering.

## Negative Tests
- **Malformed inputs**: `get_provider_key()` returning `None` or an empty value leaves email coverage at zero.
- **Error paths**: Missing `emailrep.io` in `ALLOWED_API_HOSTS` fails the contract test before a live lookup can be attempted.
- **Boundary conditions**: EmailRep key present for `IOCType.EMAIL` only; all non-email IOC types have no EmailRep provider.

## Inputs

- `app/enrichment/setup.py`
- `app/enrichment/registry.py`
- `app/config.py`
- `app/enrichment/adapters/emailrep.py`
- `tests/test_registry_setup.py`

## Expected Output

- `tests/test_emailrep_registry_settings.py`
- `app/enrichment/setup.py`
- `app/config.py`

## Verification

python3 -m pytest tests/test_emailrep_registry_settings.py tests/test_registry_setup.py tests/test_adapter_contract.py -q

## Observability Impact

Signals changed: none at runtime unless a fix is required; this task adds regression tests that localize EmailRep composition failures to registry/settings metadata before Online routes run. Future inspection: run `python3 -m pytest tests/test_emailrep_registry_settings.py tests/test_registry_setup.py -q` and inspect failed assertions for missing key, wrong IOC type, or stale allowlist coverage.
