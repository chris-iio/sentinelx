---
estimated_steps: 28
estimated_files: 5
skills_used:
  - tdd
  - verify-before-complete
---

# T02: Prove settings save and Online email provider-count reporting

Expected executor skills_used frontmatter: `tdd`, `verify-before-complete`.

Add route-level integration tests showing that a configured EmailRep key changes the analyst-visible Online coverage for email IOCs, while a missing EmailRep key leaves email coverage at zero. Inputs are the settings/analyze/template surfaces listed below; expected outputs are the focused route test file plus only the source files needing fixes.

## Steps
1. Add `tests/test_emailrep_online_coverage.py` using the Flask `client` fixture, mocked/temporary `ConfigStore` where needed, and `build_registry()` with controlled provider keys.
2. Cover `/settings` for EmailRep: `GET /settings` lists EmailRep metadata, and `POST /settings` with `provider_id=emailrep` uses `set_provider_key("emailrep", key)` plus registry rebuild; assert the raw key is not echoed in the response body.
3. Cover `/analyze` Online with an EmailRep-configured registry by patching `app.routes.analysis._setup_orchestrator` to return a deterministic job id and the same registry; assert the rendered results page includes email provider coverage of 1 via `data-provider-counts` and `0/1 providers complete` or equivalent progress text.
4. Cover `/analyze` Online without an EmailRep key but with another provider configured so the existing Online-mode guard passes; assert `provider_counts["email"] == 0` and no EmailRep dispatch/count is implied.
5. Keep tests at the route/HTML contract level; do not assert S03 row rendering details or S04 browser route-mock behavior in this slice.

## Must-Haves
- [ ] Settings save for `emailrep` uses the generic provider-key storage path and rebuilds `current_app.registry`.
- [ ] Configured EmailRep key makes Online mode report one email provider for email IOCs.
- [ ] Missing EmailRep key makes Online mode report zero email providers for email IOCs, without blocking Online mode if another provider is configured.
- [ ] Background enrichment is mocked; the test suite never contacts `emailrep.io`.
- [ ] Existing settings E2E coverage remains green with EmailRep in the provider accordion.

## Failure Modes
| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `/settings` form input | Unknown provider ids must flash/redirect without storing arbitrary keys | Not applicable | Empty API key must preserve existing validation and not rebuild to a configured provider |
| `_setup_orchestrator` background launch | Route tests patch it to avoid live work and assert provider-count rendering only | Patched out; timeout would indicate the patch did not take | Malformed return shape should fail the test loudly rather than hiding route coupling |
| Analyst email IOC parsing | If email extraction changes, route coverage should fail or use an explicit pipeline fixture to show expected email IOC behavior | Not applicable | Unexpected extra IOC types must not change `provider_counts["email"]` assertions |

## Load Profile
- **Shared resources**: Flask app registry, module-level orchestrator registry avoided by patching, settings `ConfigStore` file path mocked or isolated.
- **Per-operation cost**: One route render and O(IOC types × providers) count computation; no external API calls.
- **10x breakpoint**: Large IOC batches would make `enrichable_count` proportional to IOCs × configured providers; this slice only proves correctness for a representative email IOC and preserves existing counting mechanics.

## Negative Tests
- **Malformed inputs**: Empty EmailRep API key and unknown provider id should retain existing `/settings` validation behavior if touched.
- **Error paths**: No EmailRep key plus a configured non-email provider should render Online mode with `email: 0`, not redirect and not dispatch EmailRep.
- **Boundary conditions**: EmailRep key configured should affect `email` count only; route tests should not require S03 compact context rendering.

## Inputs

- `app/routes/settings.py`
- `app/routes/analysis.py`
- `app/templates/results.html`
- `app/enrichment/setup.py`
- `tests/e2e/test_settings.py`

## Expected Output

- `tests/test_emailrep_online_coverage.py`
- `app/routes/settings.py`
- `app/routes/analysis.py`
- `tests/e2e/test_settings.py`

## Verification

python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_settings.py tests/test_routes.py -q

## Observability Impact

Signals changed: route-level tests pin the existing analyst-visible diagnostics (`/settings` configured status, results page `data-provider-counts`, and progress text). Future inspection: failed tests distinguish settings persistence/rebuild failures from Online provider-count failures without needing a live EmailRep key or network request.
