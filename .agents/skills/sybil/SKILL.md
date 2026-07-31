---
name: sybil
description: Run an explicitly authorized change from fresh origin/main through a green draft pull request.
---

# Sybil

Read root `AGENTS.md`. This workflow adds no authority.

## Baseline

1. Inspect the active checkout and worktrees without changing them.
2. Fetch `origin`; create a unique `codex/<slug>` branch and clean worktree from
   the exact `origin/main` SHA.
3. Stop on dirty overlap, branch collision, or an unexpected ref. Record baseline
   evidence only when needed to identify a pre-existing failure.

## Implement And Publish

Use one writer. Inspect the diff and run the smallest proof. Use
`make verify-fast`, `make verify-deep`, `make verify`, and
`npm run workflow:gpt-routing` according to the changed boundaries. Repair only
verified in-scope issues; stop for scope, credentials, infrastructure,
unavailable checks, or owner decisions.

Recheck `origin/main`, stage reviewed paths or hunks, inspect the cached diff,
commit intentionally, push without force, and open a draft PR against `main`.
Local `HEAD` and the PR head must match.

## Verify The Exact Head

Derive applicable checks from repository rules and tracked workflows. Inspect
failures, annotations, reviews, comments, and unresolved threads for the current
PR SHA. Do not infer `not_applicable` without authoritative evidence.

After repair, rerun affected proof, push the reviewed state, confirm the new SHA,
and resume monitoring. Call the draft green only when proof and checks refer to
the same final SHA, heads match, failures are fixed or proven identical baseline
failures, and no actionable finding remains.

Leave the PR as a draft. Never infer authority to mark ready, merge, auto-merge,
force push, or deploy manually.
