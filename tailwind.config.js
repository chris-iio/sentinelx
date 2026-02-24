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
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
