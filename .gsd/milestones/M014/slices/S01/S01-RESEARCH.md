# S01 Research — Runtime state boundary hardening

## Summary

This is **targeted research**. The slice is primarily about **R061** and **R062**: stop runtime state from blocking normal Git workflows, and turn the durable/transient split into real repo behavior instead of an implied convention. It also sets up **R063** and **R064** by defining the boundary that later repair and dev-process work must preserve.

The repo already has a **partial** boundary in `.gitignore`, but the live Git/index state contradicts it. The triggering evidence is concrete: `.gsd/notifications.jsonl` records a 2026-04-25 `git stash pop` failure because tracked local changes to `.gsd/audit/events.jsonl` would be overwritten. That file is still tracked and currently modified. Earlier entries inside `.gsd/audit/events.jsonl` show the same failure class already happened on 2026-04-22 (`already exists, no checkout` / `could not restore untracked files from stash`). So the problem is not hypothetical and not limited to one transient filename.

Primary recommendation: **treat S01 as a repo-boundary codification slice, not a cleanup-command slice**. Build one small, testable path-classification/verifier seam first; then use it to (1) expand ignore rules for clearly transient outputs and (2) deindex already-tracked runtime files that `.gitignore` alone cannot fix. The important planner insight is: **ignore rules are necessary but insufficient** because several blocker-class files are already in the Git index.

## Recommendation

Take a three-part approach:

1. **Define the durable/transient policy explicitly in code/tests, not only in comments.**
   - Durable: `.gsd/milestones/**` and the canonical repo-scoped docs (`.gsd/DECISIONS.md`, `.gsd/REQUIREMENTS.md`, `.gsd/KNOWLEDGE.md`, `.gsd/PROJECT.md`, likely `.gsd/CODEBASE.md`).
   - Clearly transient: lock files, DB/WAL/runtime state, event streams, per-session manifests, generated reports/graphs/exec logs, background-shell state.
   - Adjacent/legacy mixed zones: `.planning/**` is not safe to treat as one class; it contains durable planning docs **and** runtime-like cursor files (`STATE.md`, `HANDOFF.json`, `.continue-here.md`, `.next-call-count`).

2. **Codify the repo fence in `.gitignore`, then separately deindex already-tracked runtime files.**
   `.gitignore` already ignores some GSD runtime surfaces (`.gsd/activity/`, `.gsd/runtime/`, `.gsd/journal/`, `.gsd/gsd.db*`, `.gsd/auto.lock`, `.gsd/metrics.json`, `.bg-shell/`), but it does **not** currently fence newer runtime outputs such as `.gsd/event-log.jsonl`, `.gsd/state-manifest.json`, `.gsd/completed-units-M*.json`, `.gsd/exec/`, `.gsd/reports/`, `.gsd/graphs/graph.json`, `.gsd/notifications.jsonl`, and `.gsd/safety/`. More importantly, several of those are already tracked, so S01 must plan for `git rm --cached`-style index cleanup (or equivalent scripted deindexing) for unequivocally transient paths.

3. **Prove the failure class with a temp-repo fixture before S02 builds repair tooling.**
   The safest contract for S01 is a reproducible Git fixture that shows:
   - why a tracked transient file like `.gsd/audit/events.jsonl` wedges stash/pop, and
   - that the hardened boundary prevents or at least surfaces the same class cleanly.

This keeps S01 narrow and gives S02 a trustworthy path-policy input instead of forcing the repair slice to rediscover what is safe to touch.

## Relevant skill guidance

- **`debug-like-expert`** informed the research method: verify the exact failure surface from repo evidence instead of assuming `.gitignore` is the only problem. The useful rule here is **“verify, don’t assume”** — the blocker came from actual tracked files, not from abstract path naming.
- **`verify-before-complete`** should shape the slice close: a boundary policy is not complete until a fresh Git fixture or `git check-ignore`/stash proof runs **after** the boundary changes. For S01, “looks right in `.gitignore`” is not sufficient evidence.

## Implementation Landscape

### Key Files

- `.gitignore` — current partial runtime-boundary policy. It already ignores `.gsd/activity/`, `.gsd/runtime/`, `.gsd/journal/`, `.gsd/gsd.db*`, `.gsd/auto.lock`, `.gsd/metrics.json`, `.gsd/STATE.md`, and `.bg-shell/`, but leaves several newer runtime outputs outside the fence.
- `.gsd/notifications.jsonl` — concrete proof of the triggering failure. Contains the 2026-04-25 `git stash pop` error naming `.gsd/audit/events.jsonl` as the overwrite blocker.
- `.gsd/audit/events.jsonl` — representative **tracked** append-only runtime event stream. `git status --short --ignored` currently shows it as modified, which explains the stash/pop collision. S01 should treat this as the canonical “tracked transient file” fixture.
- `.gsd/event-log.jsonl` / `.gsd/state-manifest.json` / `.gsd/completed-units-M*.json` — representative **untracked but not ignored** runtime outputs. These show the current fence is incomplete even for files not yet in the index.
- `.gsd/graphs/graph.json`, `.gsd/reports/*`, `.gsd/exec/*`, `.gsd/notifications.jsonl`, `.gsd/safety/*.json` — currently tracked non-milestone `.gsd` outputs that look runtime/generated rather than durable planning artifacts. I counted **20 tracked non-milestone `.gsd` paths** in these categories.
- `.planning/STATE.md` and `.planning/HANDOFF.json` — adjacent workflow-state examples. They are tracked and clearly runtime-like, but live inside a legacy planning tree that also contains durable docs, so cleanup logic must not treat all of `.planning/` as disposable.
- `Makefile` — current repo-native command surface exposes only build/verify/audit targets. No boundary verifier, repair, or local dev ownership command exists yet.
- `run.py` — current local app entrypoint is manual `python run.py`. This matters mostly for S03, but it confirms there is not yet a supported restart/ownership loop.
- `tools/optimization_audit.py` and `tests/test_optimization_audit.py` — best existing pattern for a small repo-native Python CLI plus subprocess/tmp-path verification. If S01 adds a boundary verifier or Git fixture helper, this is the local pattern to copy.

### Build Order

1. **Inventory and freeze the path policy first.**
   Start by writing the durable/transient classification in one testable seam (library function, script, or both). This is what S02 and S03 need as an input contract.

2. **Separate “ignore this in future” from “remove this from the index now.”**
   Update `.gitignore` for clearly transient outputs, but do not stop there. Already-tracked runtime files are the real blocker class, so the planner should budget a discrete deindex step for unequivocal transient paths.

3. **Add the Git fixture/verifier before recovery tooling.**
   A temp-repo reproduction of the stash/pop blocker should land in S01, not S02. S02’s recovery entrypoint can then consume a proven classifier and a proven failure fixture instead of inventing both at once.

4. **Leave ambiguous cleanup policy for later slices unless the path is unquestionably transient.**
   `.planning/**` and some report/audit surfaces are mixed enough that S01 should classify them explicitly and avoid aggressive cleanup behavior. The milestone context is conservative for a reason.

### Verification Approach

Use real Git behavior, not string-matching approximations:

- **Path-policy proof:** targeted tests around `git check-ignore -v` for representative paths.
  - Durable examples: `.gsd/milestones/M014/M014-CONTEXT.md`, `.gsd/DECISIONS.md`
  - Transient examples: `.gsd/runtime/stuck-state.json`, `.gsd/state-manifest.json`, `.gsd/event-log.jsonl`, `.bg-shell/manifest.json`
  - Mixed/adjacent examples: `.planning/STATE.md`, `.planning/HANDOFF.json`

- **Fixture proof:** a temp Git repo test that reproduces the stash/conflict class using representative `.gsd` runtime files. The important cases are:
  - tracked transient file modified locally (`.gsd/audit/events.jsonl`-style), and
  - untracked transient file that collides during stash/apply or checkout.

- **Repo smoke checks:**
  - `git status --short --ignored .gsd .planning .bg-shell`
  - `git ls-files .gsd .planning .bg-shell`

- **Final slice proof floor:** this slice should be able to stop at targeted pytest/subprocess checks plus repo smoke commands. Per the existing M012 verification pattern, **`make verify-fast` is the right escalation only if S01 ends up touching shared repo tooling/tests broadly**; `make verify-deep` should not be necessary unless the work unexpectedly crosses into app/browser behavior.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Determining whether a path is actually ignored | `git check-ignore -v` | Uses Git’s real ignore engine and shows which rule matched; avoids reimplementing ignore semantics incorrectly. |
| Reproducing the blocker class | Temp Git repos via `pytest` + `subprocess.run()` | The failure is a Git/index behavior problem, so the verifier should exercise real stash/status/checkout behavior, not a custom simulation. |
| Small repo-native CLI pattern | `tools/optimization_audit.py` + `tests/test_optimization_audit.py` | Shows the local precedent for a checked-in Python helper with subprocess-based tests and file-output verification. |

## Constraints

- **`.gitignore` does not fix already-tracked files.** Any path already in the index can still modify/stash/conflict until it is explicitly deindexed.
- **Cleanup must never auto-touch durable milestone artifacts.** `.gsd/milestones/**` and canonical planning ledgers stay out of the runtime-cleanup class.
- **This milestone is repo-boundary-first.** Do not assume upstream GSD relocation or engine redesign; S01 should solve the boundary with repo-local behavior.
- **`.planning/` is mixed state.** The repo’s security scanner already excludes `.planning/`, which is a signal it is not part of the app/runtime surface, but that does **not** mean all of it is safe to delete.

## Common Pitfalls

- **Assuming ignored means safe** — if the file is already tracked (`.gsd/audit/events.jsonl` is the proof), Git still treats it as normal repo content until it is removed from the index.
- **Treating all of `.gsd/` as one class** — the milestone directories are durable; the event/log/runtime/report surfaces are not. S02 cleanup will be dangerous unless S01 encodes this split first.
- **Over-correcting on `.planning/`** — it contains obvious runtime cursors, but also historical docs. Blanket cleanup there would violate the milestone’s conservative-cleanup rule.
- **Testing the policy with path strings only** — this slice is about Git workflow behavior. The proof needs real Git commands, not just unit assertions over glob patterns.

## Open Risks

- The repo has some **generated-but-tracked** `.gsd` outputs (`.gsd/reports/*`, `.gsd/graphs/graph.json`, `.gsd/safety/*.json`) that look transient, but the team may still value them as durable evidence. S01 should classify them explicitly before S02 starts deleting or quarantining anything.
- `.planning/` may be legacy enough that the safest choice is “never auto-clean this tree” except for named cursor files. That is a policy choice, not something Git can infer for us.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Git / local workflow repair | No directly relevant installed skill; `github/awesome-copilot@git-commit` and `gh-cli` were the closest search results and are not useful for this slice’s boundary problem | none found |
| Flask / local app process (mostly relevant to S03) | `aj-geddes/useful-ai-prompts@flask-api-development` | available |
| Flask / local app process (mostly relevant to S03) | `jezweb/claude-skills@flask` | available |

## Planner-facing conclusion

Plan S01 around **policy + index truth + fixture proof**:
- one authoritative path classifier,
- one `.gitignore`/deindex pass for unequivocal runtime outputs,
- one temp-repo Git fixture that proves the stash/pop blocker class,
- and explicit non-goals for ambiguous legacy state.

That gives S02 a safe cleanup contract and gives S03 the boundary its supported dev loop must preserve.