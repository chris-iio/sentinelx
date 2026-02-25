# Design Inspiration: SentinelX v1.2 Modern UI Redesign

**Domain:** Security tool UI — IOC triage for SOC analysts
**Researched:** 2026-02-25
**Overall confidence:** HIGH (grounded in verified design systems + real tool analysis)

---

## Executive Summary

SentinelX needs to look like it belongs alongside GreyNoise, Snyk, and Vercel — not like a Flask dev prototype. The gap between "functional tool" and "premium product" lives in four areas: surface layering, typography weight and spacing, component polish (badges, status dots, transitions), and empty/loading state craftsmanship.

The target aesthetic is **Linear-meets-GreyNoise**: near-monochromatic dark zinc background, emerald/teal accent for the security-domain accent color, crisp Inter typography at precise weights, and verdict badges with intentional semantic color coding. Every surface should feel slightly elevated from the one behind it — background → card → popover — each distinguished by a 4-8% lightness step, not a dramatic color change.

This is achievable in Tailwind CSS without a full component framework rewrite. The existing Alpine.js + vanilla JS frontend is the right architecture. What changes is the CSS design token system and component-level class choices.

---

## 1. Security Tool UI Pattern Analysis

### What premium security tools share

Research across GreyNoise Visualizer, Snyk, and CrowdStrike Falcon reveals consistent patterns:

**Near-monochromatic dark foundations**
- Backgrounds: `#0a0a0a` to `#121212` (near-black, not pure black)
- Surface 1 (page): `#0d0d0d`–`#111113`
- Surface 2 (cards): `#161618`–`#1c1c1e`
- Surface 3 (inputs, nested): `#1e1e21`–`#222225`
- Borders: `rgba(255,255,255, 0.08)`–`rgba(255,255,255, 0.12)` (barely visible white at 8–12% opacity)

**Semantic accent color = trust signal**
GreyNoise uses cyan (`#11e4e4`) as its primary interactive color. This is a deliberate choice: in security contexts, cyan/teal/emerald signals "active intelligence" rather than the "alert" red or "passive" blue of enterprise software. For SentinelX, emerald (`#10b981`) and teal (`#14b8a6`) fit this role perfectly.

**Verdict color coding is universal**
All security platforms studied use the same four-color verdict system:
- MALICIOUS / CRITICAL: Red — `#ef4444` or `#f14150`
- SUSPICIOUS / HIGH: Amber/Orange — `#f59e0b` or `#eea11b`
- CLEAN / SAFE: Green/Emerald — `#10b981` or `#22c55e`
- NO RECORD / UNKNOWN: Zinc/Gray — `#71717a` or `#94a3b8`

This matches VMRay's and Snyk's verdict systems. It's a learned pattern for analysts. Do not deviate.

**Typography: monospace for data, sans-serif for labels**
GreyNoise uses Inconsolata for IP addresses, hashes, and domains — treating them as data artifacts. Labels, headings, and navigation use Inter. SentinelX should follow this: all IOC values (IPs, domains, hashes, URLs) in a monospace font; all metadata and UI chrome in Inter.

**Information density without clutter**
Security analysts read dense data. The pattern is: tight card grids, small font sizes (12–13px for metadata), generous whitespace only at page level. Linear's 8px spacing scale (8, 16, 24, 32, 48, 64px) applied consistently achieves this.

---

## 2. Linear Design Patterns (Concrete)

Source: Linear's own redesign blog + linear.style CSS analysis.

### Color System

Linear uses LCH color space but maps to near-neutral zinc values:

```
Dark mode CSS variables (approximated to hex):
--background:    #111113  (zinc-900 equivalent)
--surface:       #1b1b1e  (between zinc-800 and zinc-900)
--alt-bg:        #222225  (zinc-800 equivalent)
--border:        rgba(255,255,255,0.08)
--text-primary:  #f4f4f5  (zinc-100)
--text-secondary:#a1a1aa  (zinc-400)
--text-muted:    #71717a  (zinc-500)
--accent:        #848CD0  (light purple in Linear; swap for emerald in SentinelX)
```

### Typography

- **Font**: Inter for body, Inter Display for headings (heavier optical weight at large sizes)
- **Body**: 13–14px, weight 400, letter-spacing: -0.01em
- **Labels/metadata**: 11–12px, weight 500, letter-spacing: 0.02em (slightly wider, uppercase optional)
- **Headings**: 16–20px, weight 600, letter-spacing: -0.02em
- **Data values (monospace)**: 12–13px JetBrains Mono or similar

### Spacing System

Linear uses an 8px base scale:
- `4px` — tight internal padding (icon gaps, badge padding)
- `8px` — standard gap between inline elements
- `12px` — card internal padding small
- `16px` — standard component padding
- `24px` — section spacing
- `32px` — card-to-card gap in grids
- `48px` — major section breaks
- `64px` — page-level padding

### Borders and Cards

- Border radius: `6px` for cards, `4px` for smaller elements, `999px` for badges/pills
- Card border: `1px solid rgba(255,255,255,0.08)`
- Card background: slightly lighter than page (4–6% lighter in perceptual lightness)
- No dramatic drop shadows on dark backgrounds — shadows read as glow artifacts
- Instead: subtle inset highlight `box-shadow: inset 0 1px 0 rgba(255,255,255,0.06)` gives cards a top-edge highlight

### Micro-interactions

- Hover state: background transitions to 2–4% lighter surface, `150ms ease-out`
- Focus ring: `2px offset, 2px solid currentColor` (matches accent color)
- Transitions: only on `background-color`, `color`, `border-color`, `opacity` — never on `width/height` (layout thrash)
- Click: `scale(0.98)` via `transform`, `80ms ease-in`

---

## 3. Vercel Geist Design Patterns (Concrete)

Source: Verified Geist design system CSS variables from community analysis.

### Color Tokens (Dark Mode)

```css
/* Geist dark mode verified values */
--geist-background:  #000000  (pure black — Vercel leans harder dark than Linear)
--geist-foreground:  #ffffff
--accents-1:         #111111  (lightest surface)
--accents-2:         #1a1a1a  (card surface)
--accents-3:         #333333  (muted elements)
--accents-4:         #444444
--accents-5:         #666666  (secondary text)
--accents-6:         #888888  (muted text)
--accents-7:         #999999
--accents-8:         #fafafa  (near white, used for subtle borders)
--geist-success:     #0070f3  (blue — not green; Vercel uses blue for "success")
--geist-error:       #ff0000
--geist-warning:     #f5a623
--geist-cyan:        #50e3c2  (used for status indicators)
```

Note: Vercel uses blue for "success" (deployment ready), which is a developer-tool convention. **SentinelX should use the security-domain convention instead: emerald green for CLEAN verdicts** since analysts expect red/green for threat/no-threat.

### Card Design

Vercel cards use:
- Background: `#111` on `#000` background
- Border: `1px solid #333` (about 20% white opacity equivalent)
- Border radius: `8px`
- No shadows — pure border + background distinction
- Hover: border color shifts to `#555`

### Status Indicators

Vercel's status dot component uses a `6px` diameter circle with:
- READY (success): `#50e3c2` (teal/cyan)
- ERROR: `#ff0000`
- BUILDING: pulsing amber `#f5a623`
- QUEUED: `#888888` (gray)

The "building" pulse animation is `scale(1)` → `scale(1.5)` with `opacity(1)` → `opacity(0)`, `1.5s ease-in-out infinite`. This is the standard "loading ping" pattern and directly applicable to SentinelX's enrichment-in-progress state.

---

## 4. Color System for SentinelX

### Recommended Palette

Using Tailwind v3 hex values as the source of truth (verified):

```
ZINC SCALE (foundation):
zinc-950: #09090b   ← page background
zinc-900: #18181b   ← primary card background
zinc-800: #27272a   ← input background, secondary surfaces
zinc-700: #3f3f46   ← active/hover states, dividers
zinc-600: #52525b   ← borders (can also use as rgba)
zinc-500: #71717a   ← muted text, disabled
zinc-400: #a1a1aa   ← secondary text, labels
zinc-300: #d4d4d8   ← primary text (softer than white)
zinc-100: #f4f4f5   ← headings, high-emphasis text
zinc-50:  #fafafa   ← pure white equivalent accents

EMERALD SCALE (primary accent — security domain "safe"):
emerald-950: #022c22
emerald-900: #064e3b
emerald-800: #065f46
emerald-700: #047857  ← badge background (dark)
emerald-600: #059669  ← badge border, secondary CTA
emerald-500: #10b981  ← primary accent, CLEAN verdict badge text
emerald-400: #34d399  ← hover state on emerald elements
emerald-300: #6ee7b7  ← text on dark emerald backgrounds
emerald-100: #d1fae5  ← very light emerald for subtle highlights

TEAL SCALE (secondary accent — interactive elements):
teal-600: #0d9488
teal-500: #14b8a6  ← interactive highlights, focus rings
teal-400: #2dd4bf  ← hover on interactive teal elements
teal-300: #5eead4  ← bright teal for active states

STATUS PALETTE (semantic, do not modify):
red-500:    #ef4444  ← MALICIOUS verdict
red-400:    #f87171  ← MALICIOUS badge text on dark bg
red-950:    #450a0a  ← MALICIOUS badge background
amber-500:  #f59e0b  ← SUSPICIOUS verdict
amber-400:  #fbbf24  ← SUSPICIOUS badge text
amber-950:  #451a03  ← SUSPICIOUS badge background
emerald-500:#10b981  ← CLEAN verdict
emerald-950:#022c22  ← CLEAN badge background
zinc-400:   #a1a1aa  ← NO RECORD verdict text
zinc-800:   #27272a  ← NO RECORD badge background
```

### CSS Variable Architecture

```css
:root {
  /* Surfaces — 4 layers */
  --surface-base:    #09090b;  /* zinc-950 — page */
  --surface-1:       #18181b;  /* zinc-900 — primary cards */
  --surface-2:       #27272a;  /* zinc-800 — inputs, nested cards */
  --surface-3:       #3f3f46;  /* zinc-700 — hover states */

  /* Borders */
  --border-subtle:   rgba(255,255,255,0.06);  /* barely visible */
  --border-default:  rgba(255,255,255,0.10);  /* standard card border */
  --border-emphasis: rgba(255,255,255,0.18);  /* hover/focus border */

  /* Text hierarchy — 4 levels */
  --text-primary:    #f4f4f5;  /* zinc-100 — headings */
  --text-secondary:  #d4d4d8;  /* zinc-300 — body text */
  --text-tertiary:   #a1a1aa;  /* zinc-400 — labels, metadata */
  --text-muted:      #71717a;  /* zinc-500 — disabled, placeholders */

  /* Accent */
  --accent:          #10b981;  /* emerald-500 */
  --accent-hover:    #34d399;  /* emerald-400 */
  --accent-subtle:   #022c22;  /* emerald-950 — bg for accent regions */
  --accent-border:   #047857;  /* emerald-700 — border for accent regions */

  /* Interactive secondary */
  --interactive:     #14b8a6;  /* teal-500 */
  --interactive-hover:#2dd4bf; /* teal-400 */

  /* Verdicts */
  --verdict-malicious-text:  #f87171;  /* red-400 */
  --verdict-malicious-bg:    #450a0a;  /* red-950 */
  --verdict-malicious-border:#ef4444;  /* red-500 */
  --verdict-suspicious-text: #fbbf24;  /* amber-400 */
  --verdict-suspicious-bg:   #451a03;  /* amber-950 */
  --verdict-suspicious-border:#f59e0b; /* amber-500 */
  --verdict-clean-text:      #34d399;  /* emerald-400 */
  --verdict-clean-bg:        #022c22;  /* emerald-950 */
  --verdict-clean-border:    #10b981;  /* emerald-500 */
  --verdict-norecord-text:   #a1a1aa;  /* zinc-400 */
  --verdict-norecord-bg:     #27272a;  /* zinc-800 */
  --verdict-norecord-border: #3f3f46;  /* zinc-700 */
}
```

---

## 5. Typography System

### Font Stack

```css
--font-sans: 'Inter', 'Inter var', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Menlo', monospace;
```

**Why Inter:** Linear, Vercel, and Linear-style SaaS universally use Inter. It was designed for screen readability, has a tall x-height (great for dense data), and 9 weights for fine-grained hierarchy. Available free from Google Fonts or via local hosting.

**Why JetBrains Mono for IOC values:** IP addresses, hashes, domains, and URLs are data artifacts — treating them as code with a monospace font creates instant visual distinction between "label" and "value", which is critical for analyst scanning speed.

### Scale

```
--text-xs:    11px / 1.4  weight: 500   letter-spacing: 0.04em   (labels, badges)
--text-sm:    12px / 1.5  weight: 400   letter-spacing: 0.01em   (metadata, secondary)
--text-base:  13px / 1.6  weight: 400   letter-spacing: 0      (body, card content)
--text-md:    14px / 1.5  weight: 500   letter-spacing: -0.01em  (card titles)
--text-lg:    16px / 1.4  weight: 600   letter-spacing: -0.015em (section headers)
--text-xl:    20px / 1.3  weight: 600   letter-spacing: -0.02em  (page title)
--text-2xl:   24px / 1.2  weight: 700   letter-spacing: -0.025em (hero heading)
```

### Text Hierarchy in Practice

```
Page title:        24px, weight 700, zinc-100, -0.025em
Section heading:   16px, weight 600, zinc-100, -0.015em
Card title:        14px, weight 500, zinc-300, -0.01em
Body / meta:       13px, weight 400, zinc-400
Labels (ALL CAPS): 11px, weight 500, zinc-500, 0.06em (uppercase tracking)
IOC values:        13px JetBrains Mono, weight 400, zinc-300
Muted / disabled:  12px, weight 400, zinc-600
```

The uppercase + wide-tracking pattern for labels (`MALICIOUS`, `IPv4`, `HASH`, `PROVIDER`) is universally used in security tools. It signals "system classification" vs "human content".

---

## 6. Component Gallery — Premium Signals

### 6.1 Verdict Badge (Pill)

```html
<!-- MALICIOUS example -->
<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold
             tracking-wide uppercase
             bg-red-950 text-red-400 border border-red-800/50">
  <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>
  MALICIOUS
</span>
```

Key specs:
- Shape: `border-radius: 9999px` (full pill)
- Padding: `4px 8px` (py-0.5 px-2)
- Font: 11px, weight 600, uppercase, letter-spacing 0.04em
- Leading dot: 6px circle in the pure status color
- Background: 950 shade (very dark tint)
- Text: 400 shade (readable on dark bg)
- Border: 800 shade at 50% opacity

Apply same pattern for all four verdict states using the palette above.

### 6.2 Status Indicator Dot (Loading)

For enrichment in-progress (Vercel-style status dot):

```css
/* Pulsing dot for "querying" state */
.status-loading {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #14b8a6;  /* teal-500 */
  position: relative;
}
.status-loading::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: inherit;
  animation: ping 1.2s cubic-bezier(0,0,0.2,1) infinite;
}
@keyframes ping {
  75%, 100% { transform: scale(2); opacity: 0; }
}
```

### 6.3 IOC Type Badge (Inline Tag)

For distinguishing IPv4, Domain, Hash, URL, CVE:

```html
<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono
             font-medium bg-zinc-800 text-zinc-400 border border-zinc-700/60">
  IPv4
</span>
```

These should be small (not pill — rectangular with 4px radius) and use a monospace font to feel like terminal type labels.

### 6.4 Card Component (IOC Result Card)

```
Anatomy from top to bottom:
┌─────────────────────────────────────────────┐ ← border: 1px solid rgba(255,255,255,0.08)
│ ████ [IOC type badge]    [verdict badge] ░░ │ ← card header: surface-2, px-4 py-3
│─────────────────────────────────────────────│ ← divider: 1px solid rgba(255,255,255,0.06)
│ [monospace IOC value]                       │ ← surface-1, px-4 py-3
│─────────────────────────────────────────────│
│ Provider results (3 rows)                   │ ← px-4 py-2, smaller text
└─────────────────────────────────────────────┘

- Border radius: 8px
- Background: zinc-900 (#18181b)
- Top header region: slightly darker zinc-800 bg OR accent left border for severity
- Left border accent: 3px solid [verdict color] (Carbon Design System pattern)
- No drop shadow (use border only)
- Hover: border-color shifts to rgba(255,255,255,0.16)
- Transition: border-color 150ms ease-out
```

The **left accent border** (3px colored bar on the card's left edge) is the Carbon Design System pattern for severity indication. It communicates verdict at a glance even before reading the badge. Use it on result cards.

### 6.5 Skeleton Loader

For the moment between submit and results appearing:

```css
.skeleton {
  background: linear-gradient(
    90deg,
    #27272a 25%,
    #3f3f46 37%,
    #27272a 63%
  );
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}
@keyframes shimmer {
  0%   { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
```

Show 3–5 skeleton card placeholders during enrichment loading. This communicates "results are coming" better than a spinner.

### 6.6 Toast Notification

```
Position: bottom-right, 16px from edge
Size: min-width 280px, max-width 360px
Background: zinc-800 (#27272a)
Border: 1px solid rgba(255,255,255,0.12)
Border radius: 8px
Shadow: 0 4px 16px rgba(0,0,0,0.6)  ← shadows read well on very dark UIs
Left border: 3px solid [success/error/info color]
Font: 13px Inter, zinc-300
Duration: 4000ms auto-dismiss
Animation: slide in from right, 200ms ease-out; slide out right, 150ms ease-in
```

### 6.7 Filter Bar (Results Page)

```
Position: sticky top-0 (stays visible while scrolling)
Background: zinc-950/95 with backdrop-filter: blur(12px)  ← glassmorphism nav
Border-bottom: 1px solid rgba(255,255,255,0.08)
Height: 48px
Padding: 0 24px

Filter pills: rounded-md (not full pill), 6px radius
Active filter: bg-zinc-800 border-zinc-600 text-zinc-100
Inactive filter: bg-transparent border-transparent text-zinc-400
Hover: border-zinc-700 text-zinc-300
```

The sticky blurred filter bar is the definitive "this is a premium product" signal. Linear uses it for sidebar nav, Vercel uses it for deployment filters, Netlify uses it for their dashboard.

---

## 7. Empty State Design

### Philosophy
Security-context empty states should communicate **readiness**, not absence. The input page before a scan, the results page with no filters matching — both need purposeful messaging.

### Recommended Pattern (Input Page — Pre-Scan)

```
NO ILLUSTRATION (decorative art on security tools feels incongruous)
Instead:
- Subtle terminal-style monospace text OR
- Simple geometric icon (shield, search, terminal cursor)
- Centered in the textarea focus area

Message pattern:
  [Icon — 24px, zinc-600]
  "Paste intelligence text to begin triage"
  [12px, zinc-500, centered]
```

### Recommended Pattern (Results — No Matches)

```
- Centered vertically in results area
- Icon: zinc-600 (not colored)
- Title: "No IOCs match current filters"  [14px, zinc-400, weight 500]
- Subtitle: "Clear filters to see all [N] extracted indicators"  [12px, zinc-500]
- CTA: "Clear all filters"  [text button, emerald-500, 13px]
```

Linear and Notion both use monochrome, minimal empty states — no illustrations, just purposeful copy and a single CTA. This is the correct pattern for tool UIs (not marketing sites).

---

## 8. Specific Recommendations per Page

### 8.1 INPUT PAGE

**Goal:** Feel like a focused, professional intake terminal.

```
Layout:
- Max-width: 720px centered
- Page background: zinc-950 (#09090b)
- Generous vertical centering (form vertically centered in viewport)

Header section:
- App name: "SentinelX" — 20px Inter, weight 700, zinc-100, letter-spacing -0.02em
- Subtitle: "IOC Extraction & Enrichment" — 13px, zinc-400
- Right-aligned: version badge (zinc-700 bg, zinc-400 text) + mode status dot

Textarea:
- Background: zinc-900 (#18181b)
- Border: 1px solid rgba(255,255,255,0.08)
- Border-radius: 8px
- Focus border: 1px solid teal-600 (#0d9488) with box-shadow: 0 0 0 3px rgba(14,165,233,0.15)
- Font: 13px JetBrains Mono — text is already "code-like data"
- Placeholder: zinc-600, "Paste alert text, email headers, threat reports..."
- Min-height: 240px

Toggle (Offline/Online mode):
- Track: zinc-700 (OFF) / emerald-700 (ON)
- Thumb: white circle, 2px shadow
- Label: "Offline" / "Online" — 13px, zinc-300, weight 500
- Online mode: show a teal status dot to the right of "Online"

Submit button:
- Background: emerald-600 (#059669) default / emerald-500 hover
- Text: white, 14px, weight 600
- Border-radius: 6px
- Padding: 10px 24px
- Transition: background 120ms ease, transform 80ms ease
- Active: scale(0.98)
- Disabled (no input): zinc-800 bg, zinc-600 text, cursor not-allowed
```

**Contextual submit button text (already implemented — maintain this):**
- 0 chars: "Paste text to analyze" (disabled)
- Offline mode: "Extract IOCs"
- Online mode: "Extract & Enrich"

### 8.2 RESULTS PAGE

**Goal:** Dense, scannable intelligence report. Not a pretty dashboard — an analyst's terminal.

```
Page layout:
- Max-width: 1200px
- Two-column: sidebar summary (280px) + main card grid

Sticky filter bar:
- height: 48px, backdrop-blur: 12px, bg: zinc-950/95
- Filter chips: verdict filter (ALL / MALICIOUS / SUSPICIOUS / CLEAN / NO RECORD)
  + type filter (ALL / IPv4 / Domain / URL / Hash / CVE)
- Search input: 200px wide, inline in filter bar, zinc-800 bg, teal focus ring
- Result count: "Showing 12 of 47 IOCs" — zinc-500, 12px, right-aligned

Summary dashboard (sidebar):
- Card: zinc-900, border rgba(255,255,255,0.08), border-radius 8px
- Title: "Scan Summary" — 13px, zinc-400, uppercase, weight 500, tracking wide
- Stats: large number (24px, weight 700) + label (11px, zinc-500)
- Color-coded counts: red-400, amber-400, emerald-400, zinc-400 for verdict counts

IOC result cards:
- Grid: 1 column (full width of main area)
- Card: zinc-900, border rgba(255,255,255,0.08), border-radius 8px
- Left border accent: 3px solid [verdict color — red/amber/emerald/zinc]
- Header row (px-4 py-3):
    - [IOC type tag] [monospace IOC value — zinc-200] [verdict badge right-aligned]
- Divider: 1px solid rgba(255,255,255,0.06)
- Provider section (px-4 py-3):
    - 3 columns for providers: [provider name] [timestamp] [verdict pill]
    - Provider name: 11px, zinc-500, uppercase
    - Verdict text: emerald/red/amber/zinc appropriate color
    - Timestamp: 11px, zinc-600, monospace

Enrichment loading state:
- Show skeleton cards (shimmer animation)
- Status: teal pulsing dot + "Querying providers..." text
```

**Card left border verdict accent is the highest-impact single change.** An analyst scanning 30 IOCs can immediately see the 3 red-bordered cards without reading any text.

### 8.3 SETTINGS PAGE

**Goal:** Clean, professional configuration form. Not a cluttered admin panel.

```
Layout:
- Max-width: 560px centered
- Single column

Header:
- "Settings" — 20px, weight 600, zinc-100
- "API key configuration" — 13px, zinc-400

Form groups (each provider):
Provider name row:
  - Icon (optional: provider logo or generic key icon, 16px, zinc-500)
  - Provider name: 14px, weight 500, zinc-200
  - Status badge: "Configured" (emerald) or "Not configured" (zinc-600 text)

Input:
  - Label: 12px, zinc-400, weight 500 (above input)
  - Input: zinc-800 bg, border rgba(255,255,255,0.1), border-radius 6px, 40px height
  - Font: 13px JetBrains Mono (API keys are code artifacts)
  - Type: password (show/hide toggle — eye icon, zinc-500)
  - Placeholder: "••••••••••••••••" or "VT-XXXXXXXXXXXXXXXX" pattern hint
  - Focus: teal ring (2px solid teal-500, 2px offset)
  - Saved state: green checkmark appears at right, "Saved" 11px text emerald-500

Sections:
  - Divider between providers: 1px solid rgba(255,255,255,0.06)
  - Optional: info callout for public APIs (MalwareBazaar, ThreatFox):
    bg: zinc-900, border: rgba(255,255,255,0.06), text: zinc-400, 12px
    "No configuration required — public API"
```

---

## 9. Animation and Transition Reference

### Approved transitions (all GPU-accelerated):

```css
/* Standard interactive */
transition: background-color 150ms ease-out, border-color 150ms ease-out, color 150ms ease-out;

/* Button press */
transition: transform 80ms ease-in, background-color 120ms ease-out;
transform: scale(0.98); /* active state */

/* Toast slide in */
animation: slideInRight 200ms cubic-bezier(0.16, 1, 0.3, 1);
@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}

/* Skeleton shimmer (1.4s, subtle) */
animation: shimmer 1.4s ease infinite;

/* Status dot pulse (1.2s, for enrichment loading) */
animation: ping 1.2s cubic-bezier(0,0,0.2,1) infinite;

/* Verdict badge reveal (when results arrive) */
animation: fadeIn 200ms ease-out;
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

**Never animate:** `width`, `height`, `max-height`, `top`, `left` (layout properties — cause reflow)
**Always animate:** `transform`, `opacity`, `background-color`, `border-color`, `color`

---

## 10. Typography Accessibility on Dark

WCAG AA requires 4.5:1 contrast for normal text, 3:1 for large text.

| Use | Color | On Background | Approximate Ratio | Pass? |
|-----|-------|--------------|-------------------|-------|
| Headings | zinc-100 (#f4f4f5) | zinc-950 (#09090b) | ~18:1 | AA+ |
| Body | zinc-300 (#d4d4d8) | zinc-950 (#09090b) | ~12:1 | AA+ |
| Secondary | zinc-400 (#a1a1aa) | zinc-950 (#09090b) | ~7:1 | AA |
| Muted | zinc-500 (#71717a) | zinc-950 (#09090b) | ~4.5:1 | AA (borderline) |
| Placeholders | zinc-600 (#52525b) | zinc-900 (#18181b) | ~2.5:1 | Fails AA |

**Action:** Placeholders should use zinc-500 on zinc-900 backgrounds (not zinc-600). Increase placeholder color to maintain at least 3:1.

---

## 11. What NOT to Do (Anti-Patterns)

| Anti-Pattern | Why It Fails | What to Do Instead |
|---|---|---|
| Pure black (#000) page background | Too stark, card elevation impossible | Use zinc-950 (#09090b) |
| Pure white text on dark | Eye strain, "overdone terminal" look | zinc-100 (#f4f4f5) for headings |
| Generic blue for all accents | Corporate enterprise feel | Emerald/teal for security domain signal |
| Illustrations in empty states | Incongruous with analyst tool UX | Minimal icon + purposeful copy |
| Combined/numeric threat scores | Obfuscates data, analysts hate this | Raw verdict labels per provider (already SentinelX's design) |
| Glassmorphism on cards | Readability sacrifice, trendy → dated | Glassmorphism only on sticky overlays (filter bar, modals) |
| Animated gradients on backgrounds | Distracting during analysis | Static surface layers only |
| Drop shadows on dark bg | Appear as glow artifacts | Use borders + background-color distinction |
| Sans-serif for IOC values | Values look like labels, not data | Monospace for all IOC values |
| Spinner for enrichment loading | No progress feedback | Skeleton cards + status text + status dot |

---

## 12. Reference Products Summary

| Product | What to Steal | Color | Typography | Component |
|---------|--------------|-------|------------|-----------|
| **GreyNoise Visualizer** | Monospace-first data display, cyan/teal as primary interactive | `#121212` bg, `#11e4e4` accent | Inconsolata + Inter | Dense IP lookup cards |
| **Linear** | 8px spacing scale, surface layering, LCH-based neutral palette | zinc-equivalent bg, violet accent | Inter + Inter Display | Card borders, sidebar density |
| **Vercel Geist** | Status dot (pulsing), sticky blurred nav bar, deployment-state badges | `#000` bg, `#50e3c2` teal status | Inter | Status indicators, filter bars |
| **Snyk** | Verdict severity badges (Critical/High/Medium/Low), issue card layout | Dark navy, red/amber severity | Inter | Severity badge system |
| **CrowdStrike Falcon** | Widget-based dashboard, dark neutral canvas | `#1a1a2e` deep navy bg | Sans-serif headings | Dashboard cards |
| **Carbon Design System** | Top-border/left-border severity pattern on cards | `#24a148` green, `#da1e28` red | IBM Plex Sans | Status indicator cards |

---

## Sources

- [Linear UI Redesign — linear.app/now](https://linear.app/now/how-we-redesigned-the-linear-ui)
- [Linear Design: LogRocket analysis](https://blog.logrocket.com/ux-design/linear-design/)
- [Linear Changelog March 2024](https://linear.app/changelog/2024-03-20-new-linear-ui)
- [Vercel Geist CSS Variables — community analysis](https://github.com/2nthony/vercel-css-vars)
- [Tailwind CSS Color Scales v3 (verified hex values)](https://v3.tailwindcss.com/docs/customizing-colors)
- [shadcn/ui Theming — dark mode CSS variables](https://ui.shadcn.com/docs/theming)
- [Carbon Design System — Status Indicator Pattern](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- [VMRay Verdict System design](https://www.vmray.com/cyber-security-blog/explained-vmray-verdict-system/)
- [GreyNoise Visualizer](https://viz.greynoise.io/)
- [Cyber security color palettes with hex values](https://produkto.io/color-palettes/cyber-security)
- [Skeleton loader shimmer pattern](https://frontend-hero.com/how-to-create-skeleton-loader)
- [CSS Transitions reference — Josh W. Comeau](https://www.joshwcomeau.com/animation/css-transitions/)
- [Command palette UX patterns — Mobbin](https://mobbin.com/glossary/command-palette)
- [Dark mode design guide — UI Deploy](https://ui-deploy.com/blog/complete-dark-mode-design-guide-ui-patterns-and-implementation-best-practices-2025)
