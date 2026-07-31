# AGENTS.md

Hi I'm iio.

I prefer ambitious ideas, simple systems, and software that feels obvious.
Understand the real constraint, avoid unnecessary machinery, and find the
smallest model that makes correct behavior unsurprising.

## Working Preferences

- Keep things simple. Channel "yagni" energy unless told otherwise. Do not
  preserve complexity because it already exists.
- Propose bold ideas when they can meaningfully improve the work.
- Prefer type-safe, inferred TypeScript. Avoid `any` and functions that only
  hide casts.
- Write focused, deterministic tests.
- Use comments to explain purpose or constraints, and keep them synchronized
  with the code.
- Fight scope creep. Honor the developer's intent in a minimal and realistic way.

## Questions Are Read-Only

- A question requests an answer, not a change. Answer without editing files.
- "How hard would it be", "what are your thoughts", "why does", "should we",
  "is it possible", "can X do Y", and similar phrasings are questions.
- If a change would help, offer it after you answer, and ask before you make it.

## Repository Guidance

Explicit user instructions override this file. The closest nested `AGENTS.md`
governs its subtree.

Use ASD-STE100 Simplified Technical English for agent messages, documentation,
and code comments. Keep quoted text exact. User-visible product copy follows the
explicit task direction, `FRONTEND.md`, and locale rules.

## Product And Architecture

SentinelX is a local-first cybersecurity workbench with one Flask shell and
three explicit workspaces: IOC analysis, security audits, and CTF work. Its
common workflow is `claim -> evidence -> reproducible check -> analyst decision
-> remediation or action -> regression proof`.

- Validate all HTTP input at the Flask boundary. Localhost is a deployment
  constraint, not authentication for a separately exposed proxy.
- Keep provider or scanner output separate from the analyst's disposition.
- Preserve source revision, scope, timestamps, tool identity, and partial
  failure with every saved result.
- Run local tools only from fixed profiles, explicit workspace roots, a minimal
  environment, bounded resources, and truthful timeout or truncation state.
- Keep one product shell. Do not add a second frontend runtime without an
  explicit migration plan and removal criteria.

## Boundaries And Routing

- Inspect the dirty tree and preserve unrelated work. A plan request does not
  authorize implementation. `keep going` resumes only an already approved
  implementation scope. Neither phrase authorizes Git, deployment, secrets,
  destructive actions, or external writes.
- **Model allowlist: Opus 5, Fable 5, and GPT-5.6 SOL, and no other model.**
  Never use Sonnet or Haiku: not as a subagent model, not for a bounded sweep,
  and not as a cheaper fallback when a route is busy or rate limited. Opus 4.8 is prohibited.
  If the intended model is unavailable, stop and say so rather
  than substituting one.
- **Fable High** owns final product and architecture synthesis. The GPT route uses GPT-5.6 SOL only.
- **High**: use for coding, implementation, debugging, and judgment-bearing
  review.
- **Medium**: use for search, mechanical inventory, and read-only evidence gathering.
- **Extra High (`xhigh`)**: use only when explicitly requested by the user.
- **Ultra**: use only when explicitly requested by the user.
- Delegate bounded work by default. Send large mechanical sweeps through
  `codex exec`, and send in-session work that needs repository context to a
  repository subagent.
- Repository skills and subagent definitions are canonical under `.agents/skills/`
  and `.agents/agents/`. Tracked symlinks under `.claude/skills/` and
  `.claude/agents/` expose them to Claude. A subagent definition pins the model but
  never the effort, because a subagent inherits the effort of the calling route and
  the Agent tool accepts no effort argument.

## Evidence

- For version-sensitive work, inspect the installed version and local pattern,
  then consult current official docs.
- Start with the smallest deterministic proof. Broaden only for explicit scope, a
  trust boundary, credible data loss, a broad contract, or a focused failure that
  reveals wider impact.
- Run focused tests first. Run `make verify-fast` for broad local verification and
  `make verify` only when browser E2E is justified.
- Run `pnpm workflow:gpt-routing` after routing or instruction changes.
- Preserve verification exit codes. Do not pipe test output unless `pipefail` or
  an equivalent status check is active.
- For layout changes, test the affected Flask page at desktop and 390 px mobile
  widths. Treat console CSP errors and horizontal document overflow as failures.

## Live Data, State, And Cleanup

- Trace values end to end before changing output. Label unknown, stale, cached,
  partial, failed, and not queried states honestly.
- Preserve source time separately from receipt or ingestion time. Do not present
  receipt time as source freshness.
- A trusted or known-good result does not erase conflicting malicious evidence.
- Detector comparisons use one replay tape and change one variable per variant.
- Treat persisted SQLite schemas as applied. Add compatible migrations and test
  existing-database upgrade paths.
- Raw submissions, analyst notes, and findings can contain secrets. Keep them
  local by default, define retention, and require explicit consent before export.
- Static cleanup reports are leads, not deletion proof. Check routes, imports,
  stores, tests, scripts, and compatibility paths before deleting.

## Git And Delivery

- Staging, commits, pushes, deployment, history changes, discards, and remote
  mutations require explicit current-turn authority limited to named scope.
- Inspect status and diff before staging. Stage only in-scope paths or hunks; stop
  when behind or diverged. Never force push.
- Use the `git-check` skill for authorized integration, the `sybil` skill for an
  explicitly authorized fresh-branch-to-green-draft-PR workflow, the `file-pr`
  skill to prepare an authorized pull request, and the `babysit-pr` skill to
  monitor one. Skills add no authority.
- Claim CI, deployment, or live success only from observed evidence.
