# M016 Discussion Log

## Exchange — 2026-04-28T10:06:36.165Z

### Arch

How should SentinelX handle EmailRep’s optional API key model?

- **Key-gated provider (Recommended)** — Treat EmailRep as configured only when an API key is present, matching SentinelX’s existing key-gated provider model and avoiding anonymous rate-limit surprises.
- **Anonymous allowed** — Allow EmailRep lookups without a key and send a SentinelX User-Agent; optionally use a key when present for higher rate limits.
- **Key first, option later** — Make the adapter key-gated first, but include a later switch/setting for anonymous lookups if users want zero-setup email reputation.

**Selected:** Key-gated provider (Recommended)

---
## Exchange — 2026-05-03T07:47:24.343Z

### Signal

For EmailRep-style results, how should SentinelX treat the reputation signal in the analyst verdict flow?

- **Triage verdict (Recommended)** — Map high-confidence EmailRep flags into malicious/suspicious/clean so email rows become scannable like other IOCs.
- **Context only** — Show EmailRep facts, but avoid letting it drive the row verdict unless another provider also supports email.
- **Strict malicious only** — Only clear abuse indicators change verdict; weak signals remain detail-only context.

**Selected:** Triage verdict (Recommended)

### Surface

What should be visible at a glance for email IOCs after Online enrichment?

- **Compact risk summary (Recommended)** — Show reputation, suspicious state, and 2–4 strongest flags inline; keep full flags in expanded/detail views.
- **Minimal badge only** — Keep the row quiet with just the computed verdict and provider name; details require expanding.
- **Full flags inline** — Expose most EmailRep fields immediately, accepting a denser email row.

**Selected:** Compact risk summary (Recommended)

### Done

Which completion boundary best matches what you want M016 to prove?

- **Provider integration (Recommended)** — One key-gated EmailRep provider works end-to-end in Online mode, with UI rendering and tests, but no raw email parsing.
- **Broader phishing triage** — Expand scope toward raw email/header/body parsing and phishing-specific analysis beyond email reputation.
- **Backend proof only** — Build adapter/API coverage first and defer polished email-specific UI treatment to a later milestone.

**Selected:** Provider integration (Recommended)

---
