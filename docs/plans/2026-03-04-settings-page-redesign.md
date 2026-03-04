# Settings Page Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the flat vertical stack of provider sections with a modern tabbed layout (Providers | About) featuring accordion-style collapsible provider rows, reducing scroll from ~2500px to ~400px.

**Architecture:** Two-tab shell with CSS-driven accordion. Tabs switch content panels via `data-tab` attributes + JS. Accordion uses CSS `grid-template-rows: 0fr/1fr` for smooth expand/collapse. One section open at a time. First unconfigured provider auto-expands on load. Shodan listed as "free provider" footer note.

**Tech Stack:** Jinja2 templates, vanilla TypeScript, CSS custom properties, Tailwind CSS standalone CLI, Playwright E2E tests.

---

## Task 1: Add IOC type metadata to PROVIDER_INFO

**Files:**
- Modify: `app/enrichment/setup.py:27-77` (PROVIDER_INFO list)

**Step 1: Add `ioc_types` field to each PROVIDER_INFO entry**

Each entry in `PROVIDER_INFO` currently has `id`, `name`, `requires_key`, `signup_url`, `description`. Add an `ioc_types` string for the accordion subtitle.

```python
PROVIDER_INFO: list[dict[str, str | bool]] = [
    {
        "id": "virustotal",
        "name": "VirusTotal",
        "requires_key": True,
        "signup_url": "https://www.virustotal.com/gui/join-us",
        "description": "IP, domain, URL, hash enrichment",
        "ioc_types": "IP \u00b7 domain \u00b7 URL \u00b7 hash",
    },
    {
        "id": "malwarebazaar",
        "name": "MalwareBazaar",
        "requires_key": True,
        "signup_url": "https://auth.abuse.ch/",
        "description": "Hash only \u2014 malware sample database",
        "ioc_types": "hash",
    },
    {
        "id": "threatfox",
        "name": "ThreatFox",
        "requires_key": True,
        "signup_url": "https://auth.abuse.ch/",
        "description": "IP, domain, URL, hash \u2014 IOC sharing platform",
        "ioc_types": "IP \u00b7 domain \u00b7 URL \u00b7 hash",
    },
    {
        "id": "urlhaus",
        "name": "URLhaus",
        "requires_key": True,
        "signup_url": "https://auth.abuse.ch/",
        "description": "URL, hash, IP, domain \u2014 malware distribution tracking",
        "ioc_types": "URL \u00b7 hash \u00b7 IP \u00b7 domain",
    },
    {
        "id": "otx",
        "name": "OTX AlienVault",
        "requires_key": True,
        "signup_url": "https://otx.alienvault.com/api",
        "description": "All IOC types including CVE \u2014 community threat intel",
        "ioc_types": "IP \u00b7 domain \u00b7 URL \u00b7 hash \u00b7 CVE",
    },
    {
        "id": "greynoise",
        "name": "GreyNoise",
        "requires_key": True,
        "signup_url": "https://www.greynoise.io/",
        "description": "IP only \u2014 internet scanner noise classification",
        "ioc_types": "IP",
    },
    {
        "id": "abuseipdb",
        "name": "AbuseIPDB",
        "requires_key": True,
        "signup_url": "https://www.abuseipdb.com/register",
        "description": "IP only \u2014 crowd-sourced abuse reporting",
        "ioc_types": "IP",
    },
]
```

**Step 2: Verify existing tests still pass**

Run: `python -m pytest tests/ -x -q --ignore=tests/e2e 2>&1 | tail -5`
Expected: All pass (adding a field doesn't break anything)

**Step 3: Commit**

```bash
git add app/enrichment/setup.py
git commit -m "feat(settings): add ioc_types metadata to PROVIDER_INFO"
```

---

## Task 2: Add tab + accordion CSS styles

**Files:**
- Modify: `app/static/src/input.css:1335-1435` (settings page section)

**Step 1: Replace settings CSS block**

Replace the `/* ---- Settings page ---- */` section (lines 1335-1435) with the new styles. Key additions:

```css
/* ---- Settings page ---- */

.page-settings {
    max-width: 720px;
    animation: fadeSlideUp var(--duration-slow) var(--ease-out-expo) both;
    animation-delay: 100ms;
}

.settings-card {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-default);
    border-radius: var(--radius);
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
}

.settings-title {
    font-size: 1.25rem;
    font-weight: var(--weight-heading);
    margin-bottom: 1rem;
}

/* ---- Tabs ---- */

.settings-tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border-default);
    margin-bottom: 1.5rem;
}

.settings-tab {
    position: relative;
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    background: none;
    border: none;
    cursor: pointer;
    transition: color 150ms ease;
}

.settings-tab:hover {
    color: var(--text-primary);
}

.settings-tab[aria-selected="true"] {
    color: var(--accent);
}

.settings-tab::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    right: 0;
    height: 2px;
    background-color: var(--accent);
    transform: scaleX(0);
    transition: transform 150ms ease;
}

.settings-tab[aria-selected="true"]::after {
    transform: scaleX(1);
}

.settings-tab-panel {
    display: none;
}

.settings-tab-panel[data-active] {
    display: block;
    animation: fadeIn var(--duration-normal) ease both;
}

/* ---- Accordion ---- */

.settings-section {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background-color: var(--bg-primary);
    overflow: hidden;
    transition: border-color 150ms ease;
}

.settings-section:hover {
    border-color: var(--border-default);
}

.accordion-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.875rem 1rem;
    cursor: pointer;
    user-select: none;
    background: none;
    border: none;
    width: 100%;
    text-align: left;
    color: inherit;
}

.accordion-header:focus-visible {
    outline: 2px solid var(--accent-interactive);
    outline-offset: -2px;
    border-radius: var(--radius);
}

.accordion-chevron {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    color: var(--text-muted);
    transition: transform 200ms ease, color 150ms ease;
}

.settings-section[data-expanded] .accordion-chevron {
    transform: rotate(90deg);
    color: var(--accent);
}

.accordion-title-group {
    flex: 1;
    min-width: 0;
}

.settings-section-title {
    font-size: 0.9rem;
    font-weight: var(--weight-heading);
    color: var(--text-primary);
    line-height: 1.3;
}

.accordion-subtitle {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.125rem;
}

.accordion-body {
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows 200ms ease;
}

.settings-section[data-expanded] .accordion-body {
    grid-template-rows: 1fr;
}

.accordion-body-inner {
    overflow: hidden;
}

.accordion-content {
    padding: 0 1rem 1rem 2.75rem;
}

/* ---- Settings info / form (inside accordion) ---- */

.settings-info {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
    line-height: var(--line-height-body);
}

.settings-info a {
    color: var(--accent);
    text-decoration: none;
    transition: color var(--duration-fast) ease;
}

.settings-info a:hover {
    color: var(--accent-hover);
}

.settings-note {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-bottom: 1rem;
}

.input-group {
    display: flex;
    gap: 0.5rem;
    align-items: stretch;
}

.input-group .form-input {
    flex: 1;
    font-family: var(--font-mono);
    font-size: 0.85rem;
}

/* ---- Status badge ---- */

.api-key-status {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.7rem;
    font-weight: 500;
    padding: 0.125rem 0.5rem;
    border-radius: 2rem;
    flex-shrink: 0;
}

.api-key-status--configured {
    background-color: var(--verdict-clean-bg);
    color: var(--verdict-clean-text);
    border: 1px solid var(--verdict-clean-border);
}

.api-key-status--missing {
    background-color: var(--verdict-no-data-bg);
    color: var(--verdict-no-data-text);
    border: 1px solid var(--verdict-no-data-border);
}

.api-key-status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: currentColor;
}

/* ---- Free providers footer ---- */

.settings-free-providers {
    margin-top: 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    font-size: 0.8rem;
    color: var(--text-muted);
}

.settings-free-providers strong {
    color: var(--text-secondary);
    font-weight: 500;
}

/* ---- About tab ---- */

.about-panel {
    padding: 0.5rem 0;
}

.about-title {
    font-size: 1.1rem;
    font-weight: var(--weight-heading);
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}

.about-tagline {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
}

.about-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.5rem 1rem;
    font-size: 0.85rem;
}

.about-label {
    color: var(--text-muted);
    font-weight: 500;
}

.about-value {
    color: var(--text-secondary);
}

.about-value code {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    background-color: var(--bg-tertiary);
    padding: 0.1rem 0.35rem;
    border-radius: var(--radius-sm);
}
```

**Step 2: Build CSS**

Run: `make css`
Expected: Tailwind CLI compiles without errors

**Step 3: Commit**

```bash
git add app/static/src/input.css
git commit -m "feat(settings): add tab + accordion CSS styles"
```

---

## Task 3: Rewrite settings template with tabs + accordion

**Files:**
- Modify: `app/templates/settings.html` (full rewrite)

**Step 1: Rewrite the template**

Replace the entire `{% block content %}` with the new tabbed + accordion layout:

```html
{% extends "base.html" %}

{% block content %}
<div class="page-settings">
    <div class="settings-card">
        <h1 class="settings-title">Settings</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
        <div class="alert alert-{{ category }}" role="alert">{{ message }}</div>
        {% endfor %}
        {% endwith %}

        {# ---- Tab bar ---- #}
        <div class="settings-tabs" role="tablist">
            <button class="settings-tab" role="tab" aria-selected="true"
                    data-tab="providers" id="tab-providers"
                    aria-controls="panel-providers">Providers</button>
            <button class="settings-tab" role="tab" aria-selected="false"
                    data-tab="about" id="tab-about"
                    aria-controls="panel-about">About</button>
        </div>

        {# ---- Providers panel ---- #}
        <div class="settings-tab-panel" id="panel-providers" data-active
             role="tabpanel" aria-labelledby="tab-providers"
             data-panel="providers">

            <div class="accordion-list" data-accordion>
                {% for provider in providers %}
                <section class="settings-section" data-provider="{{ provider.id }}">
                    <button class="accordion-header" type="button"
                            aria-expanded="false"
                            aria-controls="accordion-body-{{ provider.id }}">
                        <svg class="accordion-chevron" viewBox="0 0 16 16" fill="none"
                             stroke="currentColor" stroke-width="2">
                            <path d="M6 4l4 4-4 4"/>
                        </svg>
                        <div class="accordion-title-group">
                            <h2 class="settings-section-title">
                                {{ provider.name }} API Key
                            </h2>
                            <span class="accordion-subtitle">{{ provider.ioc_types }}</span>
                        </div>
                        {% if provider.configured %}
                        <span class="api-key-status api-key-status--configured">
                            <span class="api-key-status-dot"></span> Configured
                        </span>
                        {% else %}
                        <span class="api-key-status api-key-status--missing">
                            <span class="api-key-status-dot"></span> Not configured
                        </span>
                        {% endif %}
                    </button>

                    <div class="accordion-body" id="accordion-body-{{ provider.id }}">
                        <div class="accordion-body-inner">
                            <div class="accordion-content">
                                <p class="settings-info">{{ provider.description }}</p>
                                <p class="settings-info">
                                    Get a free API key at
                                    <a href="{{ provider.signup_url }}" target="_blank"
                                       rel="noopener noreferrer">{{ provider.signup_url }}</a>
                                </p>

                                <form method="post" action="{{ url_for('main.settings_post') }}">
                                    <input type="hidden" name="csrf_token"
                                           value="{{ csrf_token() }}"/>
                                    <input type="hidden" name="provider_id"
                                           value="{{ provider.id }}"/>

                                    <div class="form-field">
                                        <label for="api-key-{{ provider.id }}"
                                               class="form-label">API Key</label>
                                        <div class="input-group">
                                            <input type="password"
                                                   id="api-key-{{ provider.id }}"
                                                   name="api_key"
                                                   class="form-input form-input--mono"
                                                   value="{{ provider.masked_key or '' }}"
                                                   placeholder="Paste your {{ provider.name }} API key here"
                                                   autocomplete="off"
                                                   spellcheck="false"/>
                                            <button type="button"
                                                    class="btn btn-secondary"
                                                    data-role="toggle-key"
                                                    aria-label="Show or hide {{ provider.name }} API key"
                                            >Show</button>
                                        </div>
                                    </div>

                                    <div class="form-actions">
                                        <button type="submit"
                                                class="btn btn-primary">Save API Key</button>
                                    </div>
                                </form>

                                <p class="settings-note">
                                    Stored in <code>~/.sentinelx/config.ini</code>.
                                    Validated on first use, not on save.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>
                {% endfor %}
            </div>

            <div class="settings-free-providers">
                <strong>Free providers (no key required):</strong>
                Shodan InternetDB
            </div>
        </div>

        {# ---- About panel ---- #}
        <div class="settings-tab-panel" id="panel-about"
             role="tabpanel" aria-labelledby="tab-about"
             data-panel="about">
            <div class="about-panel">
                <div class="about-title">SentinelX</div>
                <div class="about-tagline">Universal threat intelligence hub for SOC analysts</div>
                <div class="about-grid">
                    <span class="about-label">Providers</span>
                    <span class="about-value">{{ provider_count }} supported ({{ key_required_count }} require API key)</span>
                    <span class="about-label">Config</span>
                    <span class="about-value"><code>~/.sentinelx/config.ini</code></span>
                    <span class="about-label">Stack</span>
                    <span class="about-value">Python 3.10 \u00b7 Flask \u00b7 TypeScript</span>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

Key structural changes:
- `section.settings-section` is preserved (E2E selectors rely on it) but now wraps an accordion
- Each section gets `data-provider="{{ provider.id }}"` for accordion JS targeting
- `h2.settings-section-title` stays inside the button header (E2E selectors preserved)
- `input[name="provider_id"]` preserved inside accordion body forms
- `data-role="toggle-key"` preserved on show/hide buttons
- `id="api-key-{provider_id}"` preserved on inputs
- Status badges preserved with same classes
- Flash messages stay above tabs (visible on all tabs)
- ARIA: `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-expanded`, `aria-controls`

**Step 2: Verify template renders**

Run: `python -c "from app import create_app; app = create_app(); app.test_client().get('/settings')"`
Expected: No Jinja2 template errors

**Step 3: Commit**

```bash
git add app/templates/settings.html
git commit -m "feat(settings): rewrite template with tabs + accordion layout"
```

---

## Task 4: Update routes.py to pass About tab data

**Files:**
- Modify: `app/routes.py:172-198` (settings_get function)

**Step 1: Add provider_count and key_required_count to template context**

```python
@bp.route("/settings", methods=["GET"])
@limiter.limit("30 per minute")
def settings_get():
    """Settings page \u2014 shows per-provider API key configuration forms."""
    config_store = ConfigStore()
    providers_with_status = []
    for info in PROVIDER_INFO:
        pid = info["id"]
        if pid == "virustotal":
            key = config_store.get_vt_api_key()
        else:
            key = config_store.get_provider_key(pid)
        providers_with_status.append({
            **info,
            "masked_key": _mask_key(key),
            "configured": key is not None,
        })
    return render_template(
        "settings.html",
        providers=providers_with_status,
        provider_count=8,
        key_required_count=len(PROVIDER_INFO),
    )
```

The only change: add `provider_count=8` and `key_required_count=len(PROVIDER_INFO)` to the `render_template` call. `provider_count` is 8 (all registered providers including Shodan). `key_required_count` comes from PROVIDER_INFO length.

**Step 2: Verify route works**

Run: `python -m pytest tests/unit/ -x -q 2>&1 | tail -3`
Expected: All pass

**Step 3: Commit**

```bash
git add app/routes.py
git commit -m "feat(settings): pass provider counts to template for About tab"
```

---

## Task 5: Add tab switching + accordion JS to settings.ts

**Files:**
- Modify: `app/static/src/ts/modules/settings.ts` (extend existing init)

**Step 1: Rewrite settings.ts with tab + accordion logic**

```typescript
/**
 * Settings page module \u2014 tab switching, accordion, and API key toggles.
 */

/** Wire up the Providers | About tab bar. */
function initTabs(): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>(".settings-tab");
  const panels = document.querySelectorAll<HTMLElement>(".settings-tab-panel");
  if (tabs.length === 0) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      if (!target) return;

      tabs.forEach((t) => t.setAttribute("aria-selected", "false"));
      tab.setAttribute("aria-selected", "true");

      panels.forEach((p) => {
        if (p.dataset.panel === target) {
          p.setAttribute("data-active", "");
        } else {
          p.removeAttribute("data-active");
        }
      });
    });
  });
}

/** Wire up accordion sections \u2014 one open at a time. */
function initAccordion(): void {
  const sections = document.querySelectorAll<HTMLElement>(
    ".settings-section[data-provider]"
  );
  if (sections.length === 0) return;

  function expandSection(section: HTMLElement): void {
    sections.forEach((s) => {
      if (s !== section) {
        s.removeAttribute("data-expanded");
        const btn = s.querySelector(".accordion-header");
        if (btn) btn.setAttribute("aria-expanded", "false");
      }
    });
    section.setAttribute("data-expanded", "");
    const btn = section.querySelector(".accordion-header");
    if (btn) btn.setAttribute("aria-expanded", "true");
  }

  sections.forEach((section) => {
    const header = section.querySelector(".accordion-header");
    if (!header) return;
    header.addEventListener("click", () => {
      if (section.hasAttribute("data-expanded")) {
        section.removeAttribute("data-expanded");
        header.setAttribute("aria-expanded", "false");
      } else {
        expandSection(section);
      }
    });
  });

  // Auto-expand first unconfigured provider, or first provider if all configured
  const firstUnconfigured = document.querySelector<HTMLElement>(
    ".settings-section:has(.api-key-status--missing)"
  );
  const target = firstUnconfigured ?? sections[0];
  if (target) expandSection(target);
}

/** Wire up per-provider API key show/hide toggles. */
function initKeyToggles(): void {
  const sections = document.querySelectorAll(".settings-section");
  sections.forEach((section) => {
    const btn = section.querySelector(
      "[data-role='toggle-key']"
    ) as HTMLButtonElement | null;
    const input = section.querySelector(
      "input[type='password'], input[type='text']"
    ) as HTMLInputElement | null;
    if (!btn || !input) return;

    btn.addEventListener("click", () => {
      if (input.type === "password") {
        input.type = "text";
        btn.textContent = "Hide";
      } else {
        input.type = "password";
        btn.textContent = "Show";
      }
    });
  });
}

export function init(): void {
  initTabs();
  initAccordion();
  initKeyToggles();
}
```

**Step 2: Build JS**

Run: `make js`
Expected: esbuild compiles without errors

**Step 3: Verify in browser manually**

Open http://localhost:5000/settings \u2014 tabs should switch, accordion should expand/collapse, show/hide should work.

**Step 4: Commit**

```bash
git add app/static/src/ts/modules/settings.ts
git commit -m "feat(settings): add tab switching + accordion JS"
```

---

## Task 6: Build CSS + JS assets

**Files:**
- Output: `app/static/dist/style.css`, `app/static/dist/main.js`

**Step 1: Build all assets**

Run: `make build`
Expected: CSS and JS compile without errors

**Step 2: Commit built assets**

```bash
git add app/static/dist/
git commit -m "chore: rebuild CSS + JS assets"
```

---

## Task 7: Update E2E page object for accordion + tabs

**Files:**
- Modify: `tests/e2e/pages/settings_page.py`

**Step 1: Update SettingsPage class**

The page object needs new methods for tabs and accordion, and some existing selectors need updating since the structure changed. Key changes:

- Add `tab(name)` method to click a tab
- Add `expand_provider(pid)` method to expand an accordion section
- Update `provider_section()` \u2014 scoping selector is unchanged (`section.settings-section:has(input...)`)
- Update `provider_title()` \u2014 still `h2.settings-section-title` but now inside accordion header
- Update `provider_description()` \u2014 now inside `.accordion-content`
- `save_api_key()` needs to expand the section first if collapsed
- Add `expect_tab_active(name)` assertion
- Add `about_panel` locator

```python
"""Page Object Model for the SentinelX settings page."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class SettingsPage:
    """Encapsulates selectors and actions for the tabbed settings page."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

        # Top-level locators
        self.title = page.locator("h1.settings-title")
        self.flash_messages = page.locator("[role='alert']")

    def goto(self) -> None:
        """Navigate to the settings page."""
        self.page.goto(self.base_url + "/settings")

    # ---- Tabs ----

    def tab(self, name: str) -> Locator:
        """Return the tab button for a given tab name (providers/about)."""
        return self.page.locator(f'.settings-tab[data-tab="{name}"]')

    def tab_panel(self, name: str) -> Locator:
        """Return the tab panel for a given tab name."""
        return self.page.locator(f'.settings-tab-panel[data-panel="{name}"]')

    def click_tab(self, name: str) -> None:
        """Click a tab to switch panels."""
        self.tab(name).click()

    def expect_tab_active(self, name: str) -> None:
        """Assert a tab is currently active."""
        expect(self.tab(name)).to_have_attribute("aria-selected", "true")
        expect(self.tab_panel(name)).to_have_attribute("data-active", "")

    # ---- Provider Sections ----

    @property
    def provider_sections(self) -> Locator:
        """All provider configuration sections."""
        return self.page.locator("section.settings-section")

    def provider_section(self, provider_id: str) -> Locator:
        """Return the section for a specific provider by its hidden input value."""
        return self.page.locator(
            f'section.settings-section:has(input[name="provider_id"][value="{provider_id}"])'
        )

    def provider_title(self, provider_id: str) -> Locator:
        """Return the title heading for a provider section."""
        return self.provider_section(provider_id).locator("h2.settings-section-title")

    def provider_status(self, provider_id: str) -> Locator:
        """Return the status badge (Configured / Not configured) for a provider."""
        return self.provider_section(provider_id).locator(".api-key-status")

    def provider_description(self, provider_id: str) -> Locator:
        """Return the description paragraph for a provider."""
        return self.provider_section(provider_id).locator("p.settings-info").first

    def provider_signup_link(self, provider_id: str) -> Locator:
        """Return the signup link element for a provider."""
        return self.provider_section(provider_id).locator("a[target='_blank']")

    # ---- Accordion ----

    def accordion_header(self, provider_id: str) -> Locator:
        """Return the accordion header button for a provider."""
        return self.provider_section(provider_id).locator(".accordion-header")

    def expand_provider(self, provider_id: str) -> None:
        """Expand a provider's accordion section if not already expanded."""
        section = self.provider_section(provider_id)
        if not section.get_attribute("data-expanded"):
            self.accordion_header(provider_id).click()

    def collapse_provider(self, provider_id: str) -> None:
        """Collapse a provider's accordion section if expanded."""
        section = self.provider_section(provider_id)
        if section.get_attribute("data-expanded") is not None:
            self.accordion_header(provider_id).click()

    def expect_provider_expanded(self, provider_id: str) -> None:
        """Assert a provider's accordion section is expanded."""
        expect(self.provider_section(provider_id)).to_have_attribute(
            "data-expanded", ""
        )

    def expect_provider_collapsed(self, provider_id: str) -> None:
        """Assert a provider's accordion section is collapsed."""
        section = self.provider_section(provider_id)
        expect(section).not_to_have_attribute("data-expanded", "")

    # ---- Form Elements ----

    def api_key_input(self, provider_id: str) -> Locator:
        """Return the API key input field for a provider."""
        return self.page.locator(f"#api-key-{provider_id}")

    def save_button(self, provider_id: str) -> Locator:
        """Return the 'Save API Key' button for a provider."""
        return self.provider_section(provider_id).locator("button[type='submit']")

    def show_hide_button(self, provider_id: str) -> Locator:
        """Return the Show/Hide toggle button for a provider's API key field."""
        return self.provider_section(provider_id).locator("[data-role='toggle-key']")

    def csrf_token(self, provider_id: str) -> Locator:
        """Return the CSRF token hidden input for a provider's form."""
        return self.provider_section(provider_id).locator("input[name='csrf_token']")

    def form(self, provider_id: str) -> Locator:
        """Return the form element for a provider."""
        return self.provider_section(provider_id).locator("form")

    # ---- Actions ----

    def fill_api_key(self, provider_id: str, key: str) -> None:
        """Fill the API key input for a provider (expands section first)."""
        self.expand_provider(provider_id)
        self.api_key_input(provider_id).fill(key)

    def save_api_key(self, provider_id: str, key: str) -> None:
        """Fill and submit the API key form for a provider."""
        self.fill_api_key(provider_id, key)
        self.save_button(provider_id).click()

    def toggle_key_visibility(self, provider_id: str) -> None:
        """Click the Show/Hide button to toggle API key visibility."""
        self.expand_provider(provider_id)
        self.show_hide_button(provider_id).click()

    # ---- Assertions ----

    def expect_provider_count(self, count: int) -> None:
        """Assert the number of provider sections on the page."""
        expect(self.provider_sections).to_have_count(count)

    def expect_status_configured(self, provider_id: str) -> None:
        """Assert a provider shows 'Configured' status."""
        expect(self.provider_status(provider_id)).to_contain_text("Configured")
        expect(self.provider_status(provider_id)).to_have_class(
            "api-key-status api-key-status--configured"
        )

    def expect_status_not_configured(self, provider_id: str) -> None:
        """Assert a provider shows 'Not configured' status."""
        expect(self.provider_status(provider_id)).to_contain_text("Not configured")
        expect(self.provider_status(provider_id)).to_have_class(
            "api-key-status api-key-status--missing"
        )

    def expect_flash_success(self, text: str) -> None:
        """Assert a success flash message is visible with the given text."""
        alert = self.page.locator(".alert-success")
        expect(alert).to_be_visible()
        expect(alert).to_contain_text(text)

    def expect_flash_error(self, text: str) -> None:
        """Assert an error flash message is visible with the given text."""
        alert = self.page.locator(".alert-error")
        expect(alert).to_be_visible()
        expect(alert).to_contain_text(text)

    def expect_key_input_masked(self, provider_id: str) -> None:
        """Assert the API key input is type=password (masked)."""
        expect(self.api_key_input(provider_id)).to_have_attribute("type", "password")

    def expect_key_input_visible(self, provider_id: str) -> None:
        """Assert the API key input is type=text (visible)."""
        expect(self.api_key_input(provider_id)).to_have_attribute("type", "text")
```

**Step 2: Commit**

```bash
git add tests/e2e/pages/settings_page.py
git commit -m "test(e2e): update settings page object for accordion + tabs"
```

---

## Task 8: Update E2E tests for new structure

**Files:**
- Modify: `tests/e2e/test_settings.py`

**Step 1: Update existing tests and add new ones**

Key changes to existing tests:
- `EXPECTED_PROVIDERS` list must match all PROVIDER_INFO entries (7 providers, not 5)
- Tests that interact with forms (show/hide, submit) must expand the accordion first (handled by updated page object)
- `test_each_provider_has_description` \u2014 description is now inside accordion body, need to expand first
- `test_each_provider_has_signup_link` \u2014 same, need to expand first
- `test_each_provider_has_form_with_csrf` \u2014 need to expand first
- `test_each_provider_has_save_button` \u2014 need to expand first
- `test_api_key_inputs_have_placeholder` \u2014 need to expand first

New tests to add:
- `test_providers_tab_active_by_default` \u2014 Providers tab is selected on load
- `test_about_tab_shows_content` \u2014 clicking About shows about panel
- `test_tab_switching` \u2014 switching tabs hides/shows panels
- `test_accordion_expands_on_click` \u2014 clicking header expands section
- `test_accordion_one_at_a_time` \u2014 expanding one collapses others
- `test_accordion_auto_expands_first_unconfigured` \u2014 first unconfigured auto-expands
- `test_free_providers_listed` \u2014 Shodan listed in footer

```python
"""E2E tests for the SentinelX settings page.

Covers: page rendering, tabs, accordion, provider listing, API key forms,
status indicators, show/hide toggle (JS), flash messages, CSRF, navigation,
security headers.
"""

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage, SettingsPage

# All key-requiring providers displayed on the settings page.
EXPECTED_PROVIDERS = [
    "virustotal", "malwarebazaar", "threatfox", "urlhaus",
    "otx", "greynoise", "abuseipdb",
]


# -- Page Rendering --


def test_settings_page_loads(page: Page, live_server: str) -> None:
    """Settings page renders with a title."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    expect(sp.title).to_have_text("Settings")


def test_settings_page_title_tag(page: Page, live_server: str) -> None:
    """Browser tab title is set for the settings page."""
    page.goto(live_server + "/settings")
    expect(page).to_have_title("sentinelx")


def test_settings_security_headers(page: Page, live_server: str) -> None:
    """Settings page response includes required security headers."""
    from tests.e2e.conftest import assert_security_headers

    response = page.goto(live_server + "/settings")
    assert response is not None
    assert_security_headers(response.headers)


# -- Tabs --


def test_providers_tab_active_by_default(page: Page, live_server: str) -> None:
    """Providers tab is selected when the settings page loads."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    sp.expect_tab_active("providers")


def test_about_tab_shows_content(page: Page, live_server: str) -> None:
    """Clicking the About tab reveals the about panel."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    sp.click_tab("about")
    sp.expect_tab_active("about")
    expect(sp.tab_panel("about")).to_contain_text("SentinelX")
    expect(sp.tab_panel("about")).to_contain_text("SOC analysts")


def test_tab_switching_hides_other_panel(page: Page, live_server: str) -> None:
    """Switching to About hides Providers panel and vice versa."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    sp.click_tab("about")
    expect(sp.tab_panel("providers")).not_to_have_attribute("data-active", "")

    sp.click_tab("providers")
    sp.expect_tab_active("providers")
    expect(sp.tab_panel("about")).not_to_have_attribute("data-active", "")


# -- Accordion --


def test_accordion_auto_expands_first_unconfigured(page: Page, live_server: str) -> None:
    """First unconfigured provider is auto-expanded on page load."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    # In isolated config, all are unconfigured, so first provider should be expanded
    first_pid = EXPECTED_PROVIDERS[0]
    sp.expect_provider_expanded(first_pid)


def test_accordion_expands_on_click(page: Page, live_server: str) -> None:
    """Clicking an accordion header expands the section."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    pid = "greynoise"
    sp.expand_provider(pid)
    sp.expect_provider_expanded(pid)


def test_accordion_one_at_a_time(page: Page, live_server: str) -> None:
    """Expanding one section collapses the previously open one."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    sp.expand_provider("virustotal")
    sp.expect_provider_expanded("virustotal")

    sp.expand_provider("greynoise")
    sp.expect_provider_expanded("greynoise")
    sp.expect_provider_collapsed("virustotal")


# -- Provider Listing --


def test_settings_lists_all_providers(page: Page, live_server: str) -> None:
    """All key-requiring providers are listed as sections."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    sp.expect_provider_count(len(EXPECTED_PROVIDERS))


def test_each_provider_has_title(page: Page, live_server: str) -> None:
    """Each provider section displays a title with the provider name."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    expected_names = {
        "virustotal": "VirusTotal",
        "malwarebazaar": "MalwareBazaar",
        "threatfox": "ThreatFox",
        "urlhaus": "URLhaus",
        "otx": "OTX AlienVault",
        "greynoise": "GreyNoise",
        "abuseipdb": "AbuseIPDB",
    }
    for pid, name in expected_names.items():
        expect(sp.provider_title(pid)).to_contain_text(f"{name} API Key")


def test_each_provider_has_description(page: Page, live_server: str) -> None:
    """Each provider section shows a description when expanded."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        expect(sp.provider_description(pid)).to_be_visible()


def test_each_provider_has_signup_link(page: Page, live_server: str) -> None:
    """Each provider section includes an external signup link."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        link = sp.provider_signup_link(pid)
        expect(link).to_be_visible()
        href = link.get_attribute("href")
        assert href is not None
        assert href.startswith("https://"), f"Signup link for {pid} is not HTTPS: {href}"
        expect(link).to_have_attribute("target", "_blank")
        expect(link).to_have_attribute("rel", "noopener noreferrer")


def test_free_providers_listed(page: Page, live_server: str) -> None:
    """Free providers are listed in the footer note."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    footer = page.locator(".settings-free-providers")
    expect(footer).to_contain_text("Shodan InternetDB")


# -- Status Indicators --


def test_providers_show_not_configured_by_default(page: Page, live_server: str) -> None:
    """All providers show 'Not configured' status when no keys are stored."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expect_status_not_configured(pid)


# -- Form Elements --


def test_each_provider_has_form_with_csrf(page: Page, live_server: str) -> None:
    """Each provider form includes a CSRF token hidden input."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        csrf = sp.csrf_token(pid)
        expect(csrf).to_be_attached()
        token = csrf.get_attribute("value")
        assert token is not None
        assert len(token) > 10, f"CSRF token for {pid} looks too short"


def test_each_provider_has_hidden_provider_id(page: Page, live_server: str) -> None:
    """Each form includes a hidden provider_id input matching the provider."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        hidden = sp.provider_section(pid).locator(f'input[name="provider_id"][value="{pid}"]')
        expect(hidden).to_be_attached()


def test_api_key_inputs_are_password_type(page: Page, live_server: str) -> None:
    """All API key inputs default to type=password for security."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expect_key_input_masked(pid)


def test_api_key_inputs_have_placeholder(page: Page, live_server: str) -> None:
    """Each API key input has a helpful placeholder mentioning the provider."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        placeholder = sp.api_key_input(pid).get_attribute("placeholder")
        assert placeholder is not None
        assert "api key" in placeholder.lower()


def test_each_provider_has_save_button(page: Page, live_server: str) -> None:
    """Each provider section has a Save API Key button."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        expect(sp.save_button(pid)).to_be_visible()
        expect(sp.save_button(pid)).to_have_text("Save API Key")


# -- Show/Hide Toggle (JavaScript) --


def test_show_hide_toggle_reveals_key(page: Page, live_server: str) -> None:
    """Clicking Show changes input type to text and button label to Hide."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    pid = "virustotal"
    sp.expand_provider(pid)
    sp.expect_key_input_masked(pid)
    expect(sp.show_hide_button(pid)).to_have_text("Show")

    sp.toggle_key_visibility(pid)

    sp.expect_key_input_visible(pid)
    expect(sp.show_hide_button(pid)).to_have_text("Hide")


def test_show_hide_toggle_hides_key_again(page: Page, live_server: str) -> None:
    """Clicking Hide returns input to password type and button to Show."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    pid = "greynoise"
    sp.toggle_key_visibility(pid)
    sp.expect_key_input_visible(pid)

    sp.toggle_key_visibility(pid)
    sp.expect_key_input_masked(pid)
    expect(sp.show_hide_button(pid)).to_have_text("Show")


def test_show_hide_toggles_are_independent(page: Page, live_server: str) -> None:
    """Toggling one provider's visibility doesn't affect others."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    # Show virustotal key (first provider, auto-expanded)
    sp.expand_provider("virustotal")
    sp.toggle_key_visibility("virustotal")
    sp.expect_key_input_visible("virustotal")

    # Others remain masked (even though in different accordion sections)
    sp.expect_key_input_masked("urlhaus")
    sp.expect_key_input_masked("otx")
    sp.expect_key_input_masked("greynoise")
    sp.expect_key_input_masked("abuseipdb")


def test_show_hide_button_has_aria_label(page: Page, live_server: str) -> None:
    """Show/Hide button has an accessible aria-label."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        btn = sp.show_hide_button(pid)
        label = btn.get_attribute("aria-label")
        assert label is not None, f"Show/Hide button for {pid} missing aria-label"
        assert "api key" in label.lower() or "show" in label.lower()


# -- Form Submission (with isolated config) --


def test_empty_key_shows_error_flash(page: Page, live_server: str) -> None:
    """Submitting an empty API key shows an error flash message."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    sp.expand_provider("virustotal")
    sp.api_key_input("virustotal").fill("")
    sp.save_button("virustotal").click()

    sp.expect_flash_error("API key cannot be empty")


def test_save_key_shows_success_flash(page: Page, live_server: str) -> None:
    """Submitting a valid API key shows a success flash and 'Configured' status."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    sp.save_api_key("virustotal", "test-key-for-e2e-1234567890abcdef")

    sp.expect_flash_success("API key saved for virustotal")
    sp.expect_status_configured("virustotal")


def test_saved_key_is_masked_on_reload(page: Page, live_server: str) -> None:
    """After saving a key, reloading shows a masked version."""
    sp = SettingsPage(page, live_server)

    sp.goto()
    sp.save_api_key("otx", "my-test-api-key-abcd1234")
    sp.expect_flash_success("API key saved for otx")

    sp.goto()
    sp.expand_provider("otx")

    input_val = sp.api_key_input("otx").input_value()
    assert input_val.endswith("1234"), f"Masked key should end with last 4 chars, got: {input_val}"
    assert "****" in input_val or "***" in input_val, f"Should contain asterisks, got: {input_val}"


def test_save_key_for_non_vt_provider(page: Page, live_server: str) -> None:
    """Saving a key for a non-VirusTotal provider works correctly."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    sp.save_api_key("abuseipdb", "abuseipdb-test-key-xyz7890")

    sp.expect_flash_success("API key saved for abuseipdb")
    sp.expect_status_configured("abuseipdb")


# -- Navigation --


def test_settings_nav_from_index(page: Page, live_server: str) -> None:
    """Clicking the settings icon in the header navigates to settings page."""
    page.goto(live_server + "/")

    settings_link = page.locator("a[aria-label='Settings']")
    expect(settings_link).to_be_visible()
    settings_link.click()

    expect(page).to_have_url(live_server + "/settings")
    expect(page.locator("h1.settings-title")).to_have_text("Settings")


def test_settings_nav_from_results(page: Page, live_server: str) -> None:
    """Settings icon is accessible from the results page too."""
    idx = IndexPage(page, live_server)
    idx.goto()
    idx.extract_iocs("192.168.1.1")

    settings_link = page.locator("a[aria-label='Settings']")
    expect(settings_link).to_be_visible()
    settings_link.click()

    expect(page).to_have_url(live_server + "/settings")
```

**Step 2: Run E2E tests**

Run: `python -m pytest tests/e2e/test_settings.py -v 2>&1 | tail -40`
Expected: All tests pass (existing + new)

**Step 3: Commit**

```bash
git add tests/e2e/test_settings.py
git commit -m "test(e2e): update settings tests for accordion + tabs"
```

---

## Task 9: Run full test suite and fix any issues

**Files:**
- Potentially any file from Tasks 1-8

**Step 1: Run unit + integration tests**

Run: `python -m pytest tests/ -x -q --ignore=tests/e2e 2>&1 | tail -10`
Expected: All pass

**Step 2: Run E2E tests**

Run: `python -m pytest tests/e2e/ -v 2>&1 | tail -30`
Expected: All pass

**Step 3: Run TypeScript typecheck**

Run: `make typecheck`
Expected: No errors

**Step 4: Fix any failures**

If any tests fail, fix the root cause (likely selector mismatches or timing issues with accordion animations in E2E).

**Step 5: Final commit**

```bash
git add -A
git commit -m "fix: resolve test issues from settings redesign"
```

---

## Task 10: Squash into feature commit

**Step 1: Interactive rebase to squash**

Squash the 7-9 commits from this feature into a clean commit history. Two options:

Option A \u2014 Single commit:
```bash
git rebase -i HEAD~N  # where N is number of commits in this feature
# squash all into one
```

Option B \u2014 Keep logical grouping (recommended):
- One commit for backend changes (setup.py + routes.py)
- One commit for frontend changes (template + CSS + TS)
- One commit for test changes (page object + tests)

**Step 2: Verify clean state**

Run: `git status && python -m pytest tests/ -x -q 2>&1 | tail -5`
Expected: Clean working tree, all tests pass
