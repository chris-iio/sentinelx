/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.js",
  ],
  safelist: [
    // Dynamic Jinja2 classes: ioc-type-badge--{{ ioc.type.value }}
    "ioc-type-badge--ipv4",
    "ioc-type-badge--ipv6",
    "ioc-type-badge--domain",
    "ioc-type-badge--url",
    "ioc-type-badge--md5",
    "ioc-type-badge--sha1",
    "ioc-type-badge--sha256",
    "ioc-type-badge--cve",
    // Dynamic JS classes: verdict-label--{verdict}
    "verdict-label--malicious",
    "verdict-label--suspicious",
    "verdict-label--clean",
    "verdict-label--no_data",
    "verdict-label--error",
    // Dynamic JS classes: verdict-{verdict} (enrichment badges)
    "verdict-malicious",
    "verdict-suspicious",
    "verdict-clean",
    "verdict-no_data",
    "verdict-error",
    // Dynamic Alpine filter classes (Phase 7)
    "filter-btn--active",
    "filter-pill--active",
    "filter-pill--ipv4",
    "filter-pill--ipv6",
    "filter-pill--domain",
    "filter-pill--url",
    "filter-pill--md5",
    "filter-pill--sha1",
    "filter-pill--sha256",
    "filter-pill--cve",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
