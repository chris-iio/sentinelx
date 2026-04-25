# Runtime state boundary

`tools/runtime_state_boundary.py` is SentinelX's checked-in classifier for repo-local workflow state.
It gives later slices one authoritative seam instead of letting `.gitignore`, deindex steps, and
repair commands each guess their own glob set.

## Supported classes

- `durable`
  - Checked-in planning and audit artifacts that should stay tracked.
  - Representative examples: `.gsd/milestones/**`, `.gsd/CODEBASE.md`, `.gsd/DECISIONS.md`, `.gsd/KNOWLEDGE.md`, `.gsd/REQUIREMENTS.md`, `.gsd/audits/**`.
- `transient`
  - Repo-local runtime state, manifests, logs, locks, and background-process surfaces that should be ignored and, when currently tracked, surfaced as blockers.
  - Representative examples: `.gsd/audit/**`, `.gsd/state-manifest.json`, `.gsd/notifications.jsonl`, `.gsd/event-log.jsonl`, `.gsd/gsd.db*`, `.gsd/activity/**`, `.bg-shell/**`.
- `manual-review`
  - Mixed or legacy workflow paths that must fail closed until a later slice gives them a migration plan.
  - Representative examples: `.planning/**` and any unclassified path under the supported boundary roots.

## Why `.planning/**` is not blanket-cleaned

`.planning` is intentionally **not** treated as automatically transient. The repo contains legacy
stateful planning files there, but it also contains human-readable workflow context that later work
may still need to inspect or migrate. Blanket ignore/deindex/cleanup would be fast but unsafe.

The classifier therefore treats `.planning/**` as `manual-review` on purpose. The audit command will
surface those paths explicitly, but it will not silently promote them into the transient set.

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
```

The audit surfaces three issue codes for later slices and CI-style verification:

- `tracked-transient`
- `unignored-transient`
- `manual-review-path`

Conflicting rule matches are reported as `conflicting-rule-match`, and paths outside the supported
boundary roots fail closed as `unknown-root`.

## Handoff to later slices

- **S02** should consume this classifier when expanding `.gitignore`, deindexing already-tracked
  transient files, and building the supported repair/recovery command.
- **S03** should reuse the same classes and issue codes when it hardens the supported dev-process
  loop, so the runtime boundary does not drift between cleanup and startup paths.

## Non-goals

- No blanket `.planning/**` cleanup.
- No file-content inspection or secret dumping in diagnostics.
- No repo mutation from `audit`; it is inspection-only.
