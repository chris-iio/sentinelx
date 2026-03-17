# GSD Knowledge Base

## Worktree CSS/Code Change Verification

**Pattern:** Before running a build/test verification task, always `git show <prior-commit-hash> --stat` to confirm the prior task actually committed the code files it claimed to change — not just the `.gsd` docs.

**Why it matters:** T01 (S02/M002) committed only `.gsd` documentation files while the git commit message and T01-SUMMARY.md both described CSS changes to `app/static/src/input.css`. The stat output revealed only 4 `.gsd` files changed. The next task (T02) had to apply the CSS changes before verification could proceed.

**Quick check:** `git show HEAD --stat | grep -v '\.gsd'` — if no non-gsd files appear and the task summary lists code files as modified, the code change was lost.

**Prevention:** Verify that `key_files` in a task summary appear in `git show <hash> --stat` output before treating that task's code changes as complete.
