# Runtime state boundary

`tools/runtime_state_boundary.py` is SentinelX's checked-in classifier for repo-local workflow state.
It gives later slices one authoritative seam instead of letting `.gitignore`, deindex steps, and
repair commands each guess their own glob set.

## Supported classes

- `durable`
  - Checked-in planning and audit artifacts that should stay tracked.
  - Representative examples: `.gsd/milestones/**`, `.gsd/CODEBASE.md`, `.gsd/DECISIONS.md`, `.gsd/KNOWLEDGE.md`, `.gsd/REQUIREMENTS.md`, `.gsd/audits/**`.
- `transient`
  - Repo-local runtime state, manifests, logs, locks, quarantine trees, and background-process surfaces that should be ignored and, when currently tracked or unignored, surfaced for repair.
  - Representative examples: `.gsd/audit/**`, `.gsd/state-manifest.json`, `.gsd/notifications.jsonl`, `.gsd/event-log.jsonl`, `.gsd/gsd.db*`, `.gsd/activity/**`, `.gsd/runtime/**`, `.gsd/runtime/dev-server/**`, `.bg-shell/**`.
- `manual-review`
  - Mixed or legacy workflow paths that must fail closed until a later slice gives them a migration plan.
  - Representative examples: `.planning/**` and any unclassified path under the supported boundary roots.

## Why `.planning/**` is not blanket-cleaned

`.planning` is intentionally **not** treated as automatically transient. The repo contains legacy
stateful planning files there, but it also contains human-readable workflow context that later work
may still need to inspect or migrate. Blanket ignore/deindex/cleanup would be fast but unsafe.

The classifier therefore treats `.planning/**` as `manual-review` on purpose. The audit and repair
commands will surface those paths explicitly, but they will not silently promote them into the
transient set.

## Supported dev-server workflow boundary

The supported SentinelX local-server loop is `make dev-server-start`, `make dev-server-status`,
`make dev-server-restart`, and `make dev-server-stop`. Those Make targets are thin wrappers over
`tools/dev_server.py`, which remains the single implementation source of truth for the managed
child process, health probe, restart count, and failure metadata.

The manager-owned runtime subtree is `.gsd/runtime/dev-server/**`. That subtree is transient by
policy: it is intentionally ignored, path-and-metadata only, and safe to inspect through
`make dev-server-status` or `python3 tools/dev_server.py status --format json`. Contributors
should not treat `status.json`, managed log paths, or recorded PID metadata as checked-in workflow
artifacts, and they should not manually clean or rewrite those files during routine recovery.

`.bg-shell/**` remains generic harness/process state, not the supported SentinelX server lifecycle
surface. `.planning/**` remains `manual-review` legacy workflow state, not a runtime recovery
surface. Keeping those distinctions explicit prevents later slices from widening the boundary until
policy changes have been reviewed.

## CLI contract

Classify representative paths:

```bash
python3 tools/runtime_state_boundary.py classify \
  .gsd/milestones/M014/M014-ROADMAP.md \
  .gsd/state-manifest.json \
  .gsd/audit/events.jsonl \
  .planning/STATE.md \
  .bg-shell/manifest.json
```

Audit the current repo boundary without mutating anything:

```bash
python3 tools/runtime_state_boundary.py audit --format text
python3 tools/runtime_state_boundary.py audit --format json --fail-on-issues
python3 tools/runtime_state_boundary.py audit \
  --format text \
  --fail-on-codes tracked-transient unignored-transient conflicting-rule-match unknown-root
make verify-runtime-boundary
```

Repair the supported transient classes, then re-run the inspection-only audit:

```bash
python3 tools/runtime_state_repair.py --format text
python3 tools/runtime_state_repair.py --format json
make repair-runtime-state
```

`make verify-runtime-boundary` runs both focused classifier coverage and a temp-repo Git regression
suite before the live repo audit, but it only fails on blocker classes (`tracked-transient`,
`unignored-transient`, `conflicting-rule-match`, and `unknown-root`).

`make repair-runtime-state` is the one supported repo-native recovery entrypoint. It applies the
repair action table below and then runs the same inspection-only audit gate so any remaining blocker
classes stay visible.

## Repair action table

| Issue code | Meaning | Repair action | Notes |
| --- | --- | --- | --- |
| `tracked-transient` | Transient runtime file is still tracked in Git | `git rm --cached -- <path>` | Preserves working-tree contents while removing the Git blocker. |
| `unignored-transient` | Transient runtime file is visible to Git because it is not ignored | Move to `.gsd/runtime/repair-quarantine/<timestamp>/<original-path>` | Preserves relative path context inside an already ignored subtree; reports the quarantine destination in text/JSON output. |
| `manual-review-path` | Legacy/mixed workflow path under `.planning/**` | Report only | Visible in repair output but never moved, deindexed, or deleted automatically. |
| `conflicting-rule-match` | Boundary rules disagree | Report only | Fail closed; fix the classifier/policy instead of widening cleanup logic. |
| `unknown-root` | Path falls outside the supported boundary contract | Report only | Fail closed; extend the authoritative boundary rules explicitly before adding automation. |

Repair diagnostics are intentionally path-only. Reports surface issue codes, per-path actions,
Git stderr, failure details, and quarantine destinations, but they do **not** print runtime file
contents.

## Quarantine contract

- Quarantined files land under `.gsd/runtime/repair-quarantine/<timestamp>/...`.
- The original repo-relative path is preserved under that timestamped subtree so later inspection
  can recover context without dumping contents into logs.
- The destination must already be ignored by Git. If the quarantine subtree is not ignored or a
  destination collision exists, the repair run fails closed and reports the reason.
- Re-running repair after a successful quarantine/deindex pass should converge to a no-op when no
  new actionable findings have appeared.

## Inspection and failure visibility

Use these surfaces when diagnosing boundary or repair behavior:

- `python3 tools/runtime_state_repair.py --format text|json`
- `make repair-runtime-state`
- `make verify-runtime-boundary`
- `.gsd/runtime/repair-quarantine/`

Expected visibility properties:

- blocked/manual-review findings remain visible in repair output
- follow-up audit failures stay visible after repair runs
- quarantine destinations are reported as paths, not file contents
- Git stderr and filesystem/quarantine errors are preserved in the action detail fields

## Handoff to later slices

- **S02** consumes this classifier when expanding `.gitignore`, deindexing already-tracked
  transient files, quarantining unignored transient files, and exposing `make repair-runtime-state`
  plus `make verify-runtime-boundary` as the supported repo-native loop.
- **S03** should reuse the same classes and issue codes when it hardens the supported dev-process
  loop, exposes `make dev-server-start|status|restart|stop`, and keeps the manager-owned
  `.gsd/runtime/dev-server/**` subtree explicit so the runtime boundary does not drift between
  cleanup and startup paths.

## Non-goals

- No blanket `.planning/**` cleanup.
- No blanket `.gsd/**` cleanup outside the supported boundary action table.
- No file-content inspection or secret dumping in diagnostics.
- No repo mutation from `audit`; it is inspection-only.
