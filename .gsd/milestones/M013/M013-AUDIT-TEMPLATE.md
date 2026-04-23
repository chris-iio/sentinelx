# M013 Optimization Audit — SentinelX

- Mode: `template`
- Generated at: `2026-04-23 08:33:23 UTC`
- Repo root: `/home/chris/projects/sentinelx`
- Output path: `.gsd/milestones/M013/M013-AUDIT-TEMPLATE.md`

## Workflow contract

- A finding must be backed by **measurement when practical**. If direct measurement is awkward or too invasive, the finding must cite **explicit code-path reasoning** instead of taste-based cleanup language.
- Every finding must land in exactly one ranked bucket: `do now`, `do next`, `later`, or `leave alone`.
- Every finding must call out the continuity guardrails it could endanger and the verification lanes that must be rerun before claiming the optimization is safe.
- `leave alone` is a valid outcome when current architecture is already intentional and the evidence does not justify churn.

## Command surface

| Entry point | Command | Purpose |
| --- | --- | --- |
| CLI help | `python3 tools/optimization_audit.py --help` | Show the supported modes, capture options, and output controls. |
| Template scaffold | `python3 tools/optimization_audit.py --mode template --output .gsd/milestones/M013/M013-AUDIT-TEMPLATE.md` | Create a reusable milestone-local ranked artifact template. |
| Working baseline artifact | `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` | Create/update the current audit document used by later optimization slices. |
| Convenience targets | `make audit-m013-template` / `make audit-m013` | Repo-native wrappers around the same workflow for contributors. |

## Verification lanes

| Lane | Command | Use when |
| --- | --- | --- |
| verify-fast | `make verify-fast` | Default rerun lane for backend/frontend logic, build/test plumbing, and any finding that does not change mocked-online browser behavior. |
| verify-deep | `make verify-deep` | Required whenever a change touches live enrichment orchestration, polling/status flow, results-page DOM/state, or mocked-online browser seams. |
| verify | `make verify` | Full pre-handoff lane when downstream slices need the unambiguous repo-wide proof command. |

## Continuity guardrails

| Requirement | Continuity guardrail |
| --- | --- |
| R008 | Preserve enrichment polling, export, filtering, detail links, copy buttons, and progress continuity. |
| R009 | Preserve CSP, CSRF, SSRF allowlist, host validation, and DOM-safety constraints. |
| R010 | Preserve or improve polling/render efficiency. |
| R014 | Preserve per-provider concurrency behavior unless evidence proves a better approach. |
| R015 | Preserve 429 backoff behavior unless evidence proves a better approach. |
| R018 | Preserve semaphore/backoff and snapshot correctness unless evidence proves otherwise. |
| R019 | Preserve cursor-based polling efficiency unless evidence proves otherwise. |
| R020 | Preserve persistent HTTP session behavior where still justified. |
| R022 | Preserve WAL-mode cache/history store behavior unless evidence supports change. |
| R040 | Keep strong verification continuity while refactoring and optimizing. |

## Measurement captures

No measurement commands were captured in this run. Use `--capture-command LABEL::COMMAND` to add timing metadata and command summaries.

## Seam checklist

### runtime/provider

- Continuity focus: Orchestrator concurrency, cache interaction, retry/backoff behavior, and provider dispatch cost.
- Audit prompt 1: What work is measured here, and what hot-path reasoning is still required?
- Audit prompt 2: Which guardrails and rerun lanes must stay attached if we change this seam?

### request/status

- Continuity focus: Flask route/helper status flow, next_since continuity, and history-save diagnostics.
- Audit prompt 1: What request-path work is actually hot versus only structurally central?
- Audit prompt 2: If a finding changes analyst-visible status behavior, which proof lane catches it?

### persistence

- Continuity focus: SQLite WAL cache/history store access, locking, query shape, and post-enrichment durability.
- Audit prompt 1: Is there measured contention, or should this seam remain a leave-alone decision?
- Audit prompt 2: What evidence would justify revisiting long-lived WAL-backed connections?

### frontend/render

- Continuity focus: Polling cadence, shared live/history result application, and DOM/render churn.
- Audit prompt 1: What analyst-visible work is actually happening per poll or per render flush?
- Audit prompt 2: Does the finding preserve live/history parity and deterministic mocked-online proof?

## Ranked finding schema

Use the same table shape in every bucket. Required fields per row:

- **Finding** — one concrete optimization or keep-decision.
- **Seam** — `runtime/provider`, `request/status`, `persistence`, or `frontend/render`.
- **Evidence kind** — `measurement` or `code-path reasoning`.
- **Evidence summary** — cite the measurement, command capture, or the exact path reasoning that justifies the rank.
- **Continuity guardrails** — list the requirement IDs that must remain protected.
- **Rerun lanes** — at minimum one of `make verify-fast`, `make verify-deep`, or `make verify`.
- **Continuity notes** — state what behavior must remain true after the future change ships, or why the seam should stay untouched.

## Ranked findings

### do now

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| _Fill during the do now pass_ | runtime/provider, request/status, persistence, or frontend/render | measurement or code-path reasoning | cite timing, command output, or the exact path reasoning | R040 plus the seam-specific continuity rules this finding could regress today. | `make verify-fast`; add `make verify-deep` for live-stack or DOM-state changes. | State what must remain true after any optimization ships. |

### do next

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| _Fill during the do next pass_ | runtime/provider, request/status, persistence, or frontend/render | measurement or code-path reasoning | cite timing, command output, or the exact path reasoning | List the guardrails that stay relevant after the current high-confidence fix ships. | Usually `make verify-fast`; escalate to `make verify` if the future change spans multiple seams. | State what must remain true after any optimization ships. |

### later

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| _Fill during the later pass_ | runtime/provider, request/status, persistence, or frontend/render | measurement or code-path reasoning | cite timing, command output, or the exact path reasoning | Call out why this stays deferred without losing current behavior/security guarantees. | Document the future lane now so the next slice does not need to reconstruct it. | State what must remain true after any optimization ships. |

### leave alone

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| _Fill during the leave alone pass_ | runtime/provider, request/status, persistence, or frontend/render | measurement or code-path reasoning | cite timing, command output, or the exact path reasoning | Name the proof showing the current seam is already intentionally shaped. | Record the lane that would need to fail before this bucket should be reconsidered. | State what must remain true after any optimization ships. |

## Audit notes

- Replace placeholder rows during the real baseline pass rather than appending free-form notes below the tables.
- Add `--capture-command LABEL::COMMAND` entries whenever a claim can be supported by timing or command output.
- If a seam cannot be measured directly, explain the exact control flow, persistence pattern, or DOM/render path that makes the keep/change decision credible.
