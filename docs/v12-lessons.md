# V12 sweep: lessons and what we built

Date of sweep: 2026-07-31. Source: https://v12.sh/ (homepage, full docs tree,
benchmarks, blog, and the public PoC repository).

## What V12 is

V12 is an autonomous security-audit agent. It audits a repository or a pull
request diff, proves each finding with an executable exploit, generates a
patch, and re-runs the exploit against the patch to verify the fix. Pricing is
pay-per-run with a fixed quote shown before the run starts.

## Lessons worth keeping

1. **Evidence gates the output.** If a proof of concept cannot be made to
   pass, the finding is invalidated before it reaches the user. Evidence is a
   gate, not an ornament.
2. **Two-axis triage.** Severity ("how bad if real") stays separate from
   validity ("is it real": unreviewed, valid, invalid, acknowledged). The
   machine proposes; the human decides.
3. **Reasons are the teaching signal.** An invalid finding requires a reason.
   Vague reasons ("not a bug") clean up one list but teach nothing. Decisions
   with reasons feed workspace memory and shape future runs.
4. **Quote and cost never share a field.** Every run shows an estimate first
   (exact scope, fixed price, p90 bound) and records the realized cost
   separately. Estimates pin the exact revision they were computed for.
5. **Honest limits sit next to every artifact.** PoC scope limits, remediation
   disclaimers, and "no artifact recorded" 404s are explicit, not implied.
6. **One state machine per job.** `queued -> running -> completed | failed |
   cancelled`, with named terminal states, drives the CLI, API, and UI.
7. **Constrained automation rules.** Autopilot watches one branch or each new
   pull request once. There is no every-branch option. Constraints keep cost
   and noise predictable.
8. **Every surface speaks to the same backend.** Web, GitHub bot, Slack, CLI,
   REST, and MCP. The MCP server ships tools, resources, workflow prompts, and
   a short skill in its instructions field.

## What SentinelX already had

- A job state machine for enrichment (`app/enrichment/job_state.py`) with
  explicit terminal failure states.
- An audit-engagement workbench (`app/audit/`) with finding severity, a status
  lifecycle, proof-of-concept skeleton generation, and report rendering.

## What this change builds

`app/review/` applies lessons 2 and 3 to the analyst IOC loop:

- `app/review/store.py` — `ReviewStore`, a SQLite store (same WAL pattern as
  `CtfStore` and `AuditStore`) that records one disposition per scoped
  indicator: `unreviewed`, `confirmed`, `false_positive`, or `acknowledged`. A false
  positive requires a non-empty reason. Resetting to `unreviewed` clears the
  stored reason and note so stale decisions cannot linger.
- `app/review/memory.py` — pure read models: `summarize` for per-disposition
  counts, `memory_context` for a compact local text block (false positives
  first, reasons verbatim), and `annotate` to mark IOC result rows with their
  recorded review. External transmission requires explicit consent and
  redaction because indicator values and analyst reasons can contain secrets.
- `tests/test_review_store.py` and `tests/test_review_memory.py` — 25 focused
  deterministic tests.

Route and UI wiring is deliberately out of scope while the enrichment and
routes refactor is in flight; the store and memory seams are stable for that
integration.

## The V12-shaped MVP core loop

A second change adds the smallest end-to-end version of the V12 loop, CLI
first so it does not touch the in-flight routes refactor:

- `app/models/pool.py` — `ModelPool`, a provider-agnostic pool with named
  task slots (`analysis`, `poc`), Anthropic and OpenAI-compatible providers,
  keys from the environment, and a per-task model allowlist (the same
  governance shape as V12's zero-retention provider toggle).
- `app/audit/agent.py` — `analyze` runs one scoped pass with prior findings
  injected as memory and a strict JSON output contract; unparseable output
  is dropped and counted. Scope limits are hard errors, never silent
  truncation. `generate_poc` completes the Foundry skeleton for one finding.
- `app/audit/verify.py` — `verify_poc` copies a bounded Foundry scope into a
  disposable directory and runs `forge test` inside fail-closed bubblewrap
  isolation. The sandbox has no network, parent home, or writable host path.
  It reports `verified`, `unproven`, or `unverified` for the exact artifact.
- `tools/audit_run.py` — the composition: enforce configured workspace roots,
  collect a local scope, analyze only with explicit external-transmission
  consent, verify an executable PoC, and record findings in the audit store.
  Verified findings land as `triaged`; non-strict runs keep unproven and
  unverified hypotheses as labeled drafts. `--strict` stores only findings
  whose exact PoC artifact passed verification.

## Remaining candidates

- **Enrichment quote before a run** (lesson 4): estimate provider calls per
  IOC batch against cache state and rate limits; record realized calls after.
- **MCP surface** (lesson 8): expose extraction and enrichment to agents with
  the tools + resources + prompts + instructions-skill layout.
- **Dated provider evaluation page** (lesson 1): replay recorded fixtures, one
  tape, one variable per variant, published with a generation date.
- **Review-memory feedback into enrichment display** (lesson 3): attach
  `memory_context` output to analysis results so known noise is labeled on
  sight.
