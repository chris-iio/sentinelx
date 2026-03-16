"use strict";
(() => {
  // app/static/src/ts/utils/dom.ts
  function attr(el, name, fallback = "") {
    return el.getAttribute(name) ?? fallback;
  }

  // app/static/src/ts/modules/form.ts
  var pasteTimer = null;
  function showPasteFeedback(charCount) {
    const feedback = document.getElementById("paste-feedback");
    if (!feedback) return;
    feedback.textContent = charCount + " characters pasted";
    feedback.style.display = "";
    feedback.classList.remove("is-hiding");
    feedback.classList.add("is-visible");
    if (pasteTimer !== null) clearTimeout(pasteTimer);
    pasteTimer = setTimeout(function() {
      feedback.classList.remove("is-visible");
      feedback.classList.add("is-hiding");
      setTimeout(function() {
        feedback.style.display = "none";
        feedback.classList.remove("is-hiding");
      }, 250);
    }, 2e3);
  }
  function updateSubmitLabel(mode) {
    const submitBtn = document.getElementById("submit-btn");
    if (!submitBtn) return;
    submitBtn.textContent = "Extract";
    submitBtn.classList.remove("mode-online", "mode-offline");
    submitBtn.classList.add(mode === "online" ? "mode-online" : "mode-offline");
  }
  function initSubmitButton() {
    const form = document.getElementById("analyze-form");
    if (!form) return;
    const textarea = document.querySelector("#ioc-text");
    const submitBtn = document.querySelector("#submit-btn");
    const clearBtn = document.getElementById("clear-btn");
    if (!textarea || !submitBtn) return;
    const ta = textarea;
    const sb = submitBtn;
    function updateSubmitState() {
      sb.disabled = ta.value.trim().length === 0;
    }
    ta.addEventListener("input", updateSubmitState);
    ta.addEventListener("paste", function() {
      setTimeout(function() {
        updateSubmitState();
        showPasteFeedback(ta.value.length);
      }, 0);
    });
    updateSubmitState();
    if (clearBtn) {
      clearBtn.addEventListener("click", function() {
        ta.value = "";
        updateSubmitState();
        ta.focus();
      });
    }
  }
  function initAutoGrow() {
    const textarea = document.querySelector("#ioc-text");
    if (!textarea) return;
    const ta = textarea;
    function grow() {
      ta.style.height = "auto";
      ta.style.height = ta.scrollHeight + "px";
    }
    ta.addEventListener("input", grow);
    ta.addEventListener("paste", function() {
      setTimeout(grow, 0);
    });
    grow();
  }
  function initModeToggle() {
    const widget = document.getElementById("mode-toggle-widget");
    const toggleBtn = document.getElementById("mode-toggle-btn");
    const modeInput = document.querySelector("#mode-input");
    if (!widget || !toggleBtn || !modeInput) return;
    const w = widget;
    const tb = toggleBtn;
    const mi = modeInput;
    tb.addEventListener("click", function() {
      const current = attr(w, "data-mode");
      const next = current === "offline" ? "online" : "offline";
      w.setAttribute("data-mode", next);
      mi.value = next;
      tb.setAttribute("aria-pressed", next === "online" ? "true" : "false");
      updateSubmitLabel(next);
    });
    updateSubmitLabel(mi.value);
  }
  function init() {
    initSubmitButton();
    initAutoGrow();
    initModeToggle();
  }

  // app/static/src/ts/modules/clipboard.ts
  function showCopiedFeedback(btn) {
    const original = btn.textContent ?? "Copy";
    btn.textContent = "Copied!";
    btn.classList.add("copied");
    setTimeout(function() {
      btn.textContent = original;
      btn.classList.remove("copied");
    }, 1500);
  }
  function fallbackCopy(text, btn) {
    const tmp = document.createElement("textarea");
    tmp.value = text;
    tmp.style.position = "fixed";
    tmp.style.top = "-9999px";
    tmp.style.left = "-9999px";
    document.body.appendChild(tmp);
    tmp.focus();
    tmp.select();
    try {
      document.execCommand("copy");
      showCopiedFeedback(btn);
    } catch {
    } finally {
      document.body.removeChild(tmp);
    }
  }
  function writeToClipboard(text, btn) {
    if (!navigator.clipboard) {
      fallbackCopy(text, btn);
      return;
    }
    navigator.clipboard.writeText(text).then(function() {
      showCopiedFeedback(btn);
    }).catch(function() {
      fallbackCopy(text, btn);
    });
  }
  function init2() {
    const copyButtons = document.querySelectorAll(".copy-btn");
    copyButtons.forEach(function(btn) {
      btn.addEventListener("click", function() {
        const value = attr(btn, "data-value");
        if (!value) return;
        const enrichment = attr(btn, "data-enrichment");
        const copyText = enrichment ? value + " | " + enrichment : value;
        writeToClipboard(copyText, btn);
      });
    });
  }

  // app/static/src/ts/types/ioc.ts
  var VERDICT_SEVERITY = [
    "error",
    "no_data",
    "clean",
    "suspicious",
    "malicious"
  ];
  function verdictSeverityIndex(verdict) {
    return VERDICT_SEVERITY.indexOf(verdict);
  }
  var VERDICT_LABELS = {
    malicious: "MALICIOUS",
    suspicious: "SUSPICIOUS",
    clean: "CLEAN",
    known_good: "KNOWN GOOD",
    no_data: "NO DATA",
    error: "ERROR"
  };
  var _defaultProviderCounts = {
    ipv4: 2,
    ipv6: 2,
    domain: 2,
    url: 2,
    md5: 3,
    sha1: 3,
    sha256: 3
  };
  function getProviderCounts() {
    const el = document.querySelector(".page-results");
    if (el === null) return _defaultProviderCounts;
    const raw = el.getAttribute("data-provider-counts");
    if (raw === null) return _defaultProviderCounts;
    try {
      return JSON.parse(raw);
    } catch {
      return _defaultProviderCounts;
    }
  }

  // app/static/src/ts/modules/cards.ts
  var sortTimer = null;
  function init3() {
  }
  function findCardForIoc(iocValue) {
    return document.querySelector(
      '.ioc-card[data-ioc-value="' + CSS.escape(iocValue) + '"]'
    );
  }
  function updateCardVerdict(iocValue, worstVerdict) {
    const card = findCardForIoc(iocValue);
    if (!card) return;
    card.setAttribute("data-verdict", worstVerdict);
    const label = card.querySelector(".verdict-label");
    if (label) {
      const classes = label.className.split(" ").filter((c) => !c.startsWith("verdict-label--"));
      classes.push("verdict-label--" + worstVerdict);
      label.className = classes.join(" ");
      label.textContent = VERDICT_LABELS[worstVerdict] || worstVerdict.toUpperCase();
    }
  }
  function updateDashboardCounts() {
    const dashboard = document.getElementById("verdict-dashboard");
    if (!dashboard) return;
    const cards = document.querySelectorAll(".ioc-card");
    const counts = {
      malicious: 0,
      suspicious: 0,
      clean: 0,
      known_good: 0,
      no_data: 0
    };
    cards.forEach((card) => {
      const v = attr(card, "data-verdict");
      if (Object.prototype.hasOwnProperty.call(counts, v)) {
        counts[v] = (counts[v] ?? 0) + 1;
      }
    });
    const verdicts = ["malicious", "suspicious", "clean", "known_good", "no_data"];
    verdicts.forEach((verdict) => {
      const countEl = dashboard.querySelector(
        '[data-verdict-count="' + verdict + '"]'
      );
      if (countEl) {
        countEl.textContent = String(counts[verdict] ?? 0);
      }
    });
  }
  function sortCardsBySeverity() {
    if (sortTimer !== null) clearTimeout(sortTimer);
    sortTimer = setTimeout(doSortCards, 100);
  }
  function doSortCards() {
    const grid = document.getElementById("ioc-cards-grid");
    if (!grid) return;
    const cards = Array.from(grid.querySelectorAll(".ioc-card"));
    if (cards.length === 0) return;
    cards.sort((a, b) => {
      const va = verdictSeverityIndex(
        attr(a, "data-verdict", "no_data")
      );
      const vb = verdictSeverityIndex(
        attr(b, "data-verdict", "no_data")
      );
      return vb - va;
    });
    cards.forEach((card) => grid.appendChild(card));
  }

  // app/static/src/ts/modules/filter.ts
  function init4() {
    const filterRootEl = document.getElementById("filter-root");
    if (!filterRootEl) return;
    const filterRoot = filterRootEl;
    const filterState = {
      verdict: "all",
      type: "all",
      search: ""
    };
    function applyFilter() {
      const cards = filterRoot.querySelectorAll(".ioc-card");
      const verdictLC = filterState.verdict.toLowerCase();
      const typeLC = filterState.type.toLowerCase();
      const searchLC = filterState.search.toLowerCase();
      cards.forEach((card) => {
        const cardVerdict = attr(card, "data-verdict").toLowerCase();
        const cardType = attr(card, "data-ioc-type").toLowerCase();
        const cardValue = attr(card, "data-ioc-value").toLowerCase();
        const verdictMatch = verdictLC === "all" || cardVerdict === verdictLC;
        const typeMatch = typeLC === "all" || cardType === typeLC;
        const searchMatch = searchLC === "" || cardValue.indexOf(searchLC) !== -1;
        card.style.display = verdictMatch && typeMatch && searchMatch ? "" : "none";
      });
      const verdictBtns2 = filterRoot.querySelectorAll(
        "[data-filter-verdict]"
      );
      verdictBtns2.forEach((btn) => {
        const btnVerdict = attr(btn, "data-filter-verdict");
        if (btnVerdict === filterState.verdict) {
          btn.classList.add("filter-btn--active");
        } else {
          btn.classList.remove("filter-btn--active");
        }
      });
      const typePills2 = filterRoot.querySelectorAll(
        "[data-filter-type]"
      );
      typePills2.forEach((pill) => {
        const pillType = attr(pill, "data-filter-type");
        if (pillType === filterState.type) {
          pill.classList.add("filter-pill--active");
        } else {
          pill.classList.remove("filter-pill--active");
        }
      });
    }
    const verdictBtns = filterRoot.querySelectorAll(
      "[data-filter-verdict]"
    );
    verdictBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const verdict = attr(btn, "data-filter-verdict");
        if (verdict === "all") {
          filterState.verdict = "all";
        } else {
          filterState.verdict = filterState.verdict === verdict ? "all" : verdict;
        }
        applyFilter();
      });
    });
    const typePills = filterRoot.querySelectorAll(
      "[data-filter-type]"
    );
    typePills.forEach((pill) => {
      pill.addEventListener("click", () => {
        const type = attr(pill, "data-filter-type");
        if (type === "all") {
          filterState.type = "all";
        } else {
          filterState.type = filterState.type === type ? "all" : type;
        }
        applyFilter();
      });
    });
    const searchInput = document.getElementById(
      "filter-search-input"
    );
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        filterState.search = searchInput.value;
        applyFilter();
      });
    }
    const dashboard = document.getElementById("verdict-dashboard");
    if (dashboard) {
      const dashBadges = dashboard.querySelectorAll(
        ".verdict-kpi-card[data-verdict]"
      );
      dashBadges.forEach((badge) => {
        badge.addEventListener("click", () => {
          const verdict = attr(badge, "data-verdict");
          filterState.verdict = filterState.verdict === verdict ? "all" : verdict;
          applyFilter();
        });
      });
    }
  }

  // app/static/src/ts/modules/export.ts
  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }
  function timestamp() {
    return (/* @__PURE__ */ new Date()).toISOString().replace(/[:.]/g, "-").slice(0, 19);
  }
  function csvEscape(value) {
    if (value.indexOf(",") !== -1 || value.indexOf('"') !== -1 || value.indexOf("\n") !== -1) {
      return '"' + value.replace(/"/g, '""') + '"';
    }
    return value;
  }
  function rawStatField(raw, key) {
    if (!raw) return "";
    const val = raw[key];
    if (val === void 0 || val === null) return "";
    if (Array.isArray(val)) return val.join("; ");
    return String(val);
  }
  var CSV_COLUMNS = [
    "ioc_value",
    "ioc_type",
    "provider",
    "verdict",
    "detection_count",
    "total_engines",
    "scan_date",
    "signature",
    "malware_printable",
    "threat_type",
    "countryCode",
    "isp",
    "top_detections"
  ];
  function exportJSON(results) {
    const json = JSON.stringify(results, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    downloadBlob(blob, "sentinelx-export-" + timestamp() + ".json");
  }
  function exportCSV(results) {
    const header = CSV_COLUMNS.join(",") + "\n";
    const rows = [];
    for (const r of results) {
      if (r.type !== "result") continue;
      const raw = r.raw_stats;
      const row = [
        csvEscape(r.ioc_value),
        csvEscape(r.ioc_type),
        csvEscape(r.provider),
        csvEscape(r.verdict),
        String(r.detection_count),
        String(r.total_engines),
        csvEscape(r.scan_date ?? ""),
        csvEscape(rawStatField(raw, "signature")),
        csvEscape(rawStatField(raw, "malware_printable")),
        csvEscape(rawStatField(raw, "threat_type")),
        csvEscape(rawStatField(raw, "countryCode")),
        csvEscape(rawStatField(raw, "isp")),
        csvEscape(rawStatField(raw, "top_detections"))
      ];
      rows.push(row.join(","));
    }
    const csv = header + rows.join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    downloadBlob(blob, "sentinelx-export-" + timestamp() + ".csv");
  }
  function copyAllIOCs(btn) {
    const cards = document.querySelectorAll(".ioc-card[data-ioc-value]");
    const seen = /* @__PURE__ */ new Set();
    const values = [];
    cards.forEach((card) => {
      const val = card.getAttribute("data-ioc-value");
      if (val && !seen.has(val)) {
        seen.add(val);
        values.push(val);
      }
    });
    writeToClipboard(values.join("\n"), btn);
  }

  // app/static/src/ts/modules/verdict-compute.ts
  function computeWorstVerdict(entries) {
    if (entries.some((e) => e.verdict === "known_good")) {
      return "known_good";
    }
    const worst = findWorstEntry(entries);
    return worst ? worst.verdict : "no_data";
  }
  function computeConsensus(entries) {
    let flagged = 0;
    let responded = 0;
    for (const entry of entries) {
      if (entry.verdict === "malicious" || entry.verdict === "suspicious") {
        flagged++;
        responded++;
      } else if (entry.verdict === "clean") {
        responded++;
      }
    }
    return { flagged, responded };
  }
  function consensusBadgeClass(flagged) {
    if (flagged === 0) return "consensus-badge--green";
    if (flagged <= 2) return "consensus-badge--yellow";
    return "consensus-badge--red";
  }
  function computeAttribution(entries) {
    const candidates = entries.filter(
      (e) => e.verdict !== "no_data" && e.verdict !== "error"
    );
    if (candidates.length === 0) {
      return { provider: "", text: "No providers returned data for this IOC" };
    }
    const sorted = [...candidates].sort((a, b) => {
      if (b.totalEngines !== a.totalEngines) return b.totalEngines - a.totalEngines;
      return verdictSeverityIndex(b.verdict) - verdictSeverityIndex(a.verdict);
    });
    const best = sorted[0];
    if (!best) return { provider: "", text: "No providers returned data for this IOC" };
    return { provider: best.provider, text: best.provider + ": " + best.statText };
  }
  function findWorstEntry(entries) {
    const first = entries[0];
    if (!first) return void 0;
    let worst = first;
    for (let i = 1; i < entries.length; i++) {
      const current = entries[i];
      if (!current) continue;
      if (verdictSeverityIndex(current.verdict) > verdictSeverityIndex(worst.verdict)) {
        worst = current;
      }
    }
    return worst;
  }

  // app/static/src/ts/modules/row-factory.ts
  function formatDate(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleDateString();
    } catch {
      return iso;
    }
  }
  function formatRelativeTime(iso) {
    try {
      const diffMs = Date.now() - new Date(iso).getTime();
      const diffMin = Math.floor(diffMs / 6e4);
      if (diffMin < 1) return "just now";
      if (diffMin < 60) return diffMin + "m ago";
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return diffHr + "h ago";
      const diffDay = Math.floor(diffHr / 24);
      return diffDay + "d ago";
    } catch {
      return iso;
    }
  }
  var PROVIDER_CONTEXT_FIELDS = {
    VirusTotal: [
      { key: "top_detections", label: "Detections", type: "tags" },
      { key: "reputation", label: "Reputation", type: "text" }
    ],
    MalwareBazaar: [
      { key: "signature", label: "Signature", type: "text" },
      { key: "tags", label: "Tags", type: "tags" },
      { key: "file_type", label: "File type", type: "text" },
      { key: "first_seen", label: "First seen", type: "text" },
      { key: "last_seen", label: "Last seen", type: "text" }
    ],
    ThreatFox: [
      { key: "malware_printable", label: "Malware", type: "text" },
      { key: "threat_type", label: "Threat type", type: "text" },
      { key: "confidence_level", label: "Confidence", type: "text" }
    ],
    AbuseIPDB: [
      { key: "abuseConfidenceScore", label: "Confidence", type: "text" },
      { key: "totalReports", label: "Reports", type: "text" },
      { key: "countryCode", label: "Country", type: "text" },
      { key: "isp", label: "ISP", type: "text" },
      { key: "usageType", label: "Usage", type: "text" }
    ],
    "Shodan InternetDB": [
      { key: "ports", label: "Ports", type: "tags" },
      { key: "vulns", label: "Vulns", type: "tags" },
      { key: "hostnames", label: "Hostnames", type: "tags" },
      { key: "cpes", label: "CPEs", type: "tags" },
      // EPROV-01
      { key: "tags", label: "Tags", type: "tags" }
      // EPROV-01
    ],
    "CIRCL Hashlookup": [
      { key: "file_name", label: "File", type: "text" },
      { key: "source", label: "Source", type: "text" }
    ],
    "GreyNoise Community": [
      { key: "noise", label: "Noise", type: "text" },
      { key: "riot", label: "RIOT", type: "text" },
      { key: "classification", label: "Classification", type: "text" }
    ],
    URLhaus: [
      { key: "threat", label: "Threat", type: "text" },
      { key: "url_status", label: "Status", type: "text" },
      { key: "tags", label: "Tags", type: "tags" }
    ],
    "OTX AlienVault": [
      { key: "pulse_count", label: "Pulses", type: "text" },
      { key: "reputation", label: "Reputation", type: "text" }
    ],
    "IP Context": [
      { key: "geo", label: "Location", type: "text" },
      { key: "reverse", label: "PTR", type: "text" },
      { key: "flags", label: "Flags", type: "tags" }
    ],
    "DNS Records": [
      { key: "a", label: "A", type: "tags" },
      { key: "mx", label: "MX", type: "tags" },
      { key: "ns", label: "NS", type: "tags" },
      { key: "txt", label: "TXT", type: "tags" }
    ],
    "Cert History": [
      { key: "cert_count", label: "Certs", type: "text" },
      { key: "earliest", label: "First seen", type: "text" },
      { key: "latest", label: "Latest", type: "text" },
      { key: "subdomains", label: "Subdomains", type: "tags" }
    ],
    ThreatMiner: [
      { key: "passive_dns", label: "Passive DNS", type: "tags" },
      { key: "samples", label: "Samples", type: "tags" }
    ],
    "ASN Intel": [
      { key: "asn", label: "ASN", type: "text" },
      { key: "prefix", label: "Prefix", type: "text" },
      { key: "rir", label: "RIR", type: "text" },
      { key: "allocated", label: "Allocated", type: "text" }
    ]
  };
  var CONTEXT_PROVIDERS = /* @__PURE__ */ new Set(["IP Context", "DNS Records", "Cert History", "ThreatMiner", "ASN Intel"]);
  function createLabeledField(label) {
    const fieldEl = document.createElement("span");
    fieldEl.className = "provider-context-field";
    const labelEl = document.createElement("span");
    labelEl.className = "provider-context-label";
    labelEl.textContent = label + ": ";
    fieldEl.appendChild(labelEl);
    return fieldEl;
  }
  function createContextFields(result) {
    const fieldDefs = PROVIDER_CONTEXT_FIELDS[result.provider];
    if (!fieldDefs) return null;
    const stats = result.raw_stats;
    if (!stats) return null;
    const container = document.createElement("div");
    container.className = "provider-context";
    let hasFields = false;
    for (const def of fieldDefs) {
      const value = stats[def.key];
      if (value === void 0 || value === null || value === "") continue;
      if (def.type === "tags" && Array.isArray(value) && value.length > 0) {
        const fieldEl = createLabeledField(def.label);
        for (const tag of value) {
          if (typeof tag !== "string" && typeof tag !== "number") continue;
          const tagEl = document.createElement("span");
          tagEl.className = "context-tag";
          tagEl.textContent = String(tag);
          fieldEl.appendChild(tagEl);
        }
        container.appendChild(fieldEl);
        hasFields = true;
      } else if (def.type === "text" && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) {
        const fieldEl = createLabeledField(def.label);
        const valEl = document.createElement("span");
        valEl.textContent = String(value);
        fieldEl.appendChild(valEl);
        container.appendChild(fieldEl);
        hasFields = true;
      }
    }
    return hasFields ? container : null;
  }
  function getOrCreateSummaryRow(slot) {
    const existing = slot.querySelector(".ioc-summary-row");
    if (existing) return existing;
    const row = document.createElement("div");
    row.className = "ioc-summary-row";
    const chevron = slot.querySelector(".chevron-toggle");
    if (chevron) {
      slot.insertBefore(row, chevron);
    } else {
      slot.appendChild(row);
    }
    return row;
  }
  function updateSummaryRow(slot, iocValue, iocVerdicts) {
    const entries = iocVerdicts[iocValue];
    if (!entries || entries.length === 0) return;
    const worstVerdict = computeWorstVerdict(entries);
    const attribution = computeAttribution(entries);
    const { flagged, responded } = computeConsensus(entries);
    const summaryRow = getOrCreateSummaryRow(slot);
    summaryRow.textContent = "";
    const verdictBadge = document.createElement("span");
    verdictBadge.className = "verdict-badge verdict-" + worstVerdict;
    verdictBadge.textContent = VERDICT_LABELS[worstVerdict];
    summaryRow.appendChild(verdictBadge);
    const attributionSpan = document.createElement("span");
    attributionSpan.className = "ioc-summary-attribution";
    attributionSpan.textContent = attribution.text;
    summaryRow.appendChild(attributionSpan);
    const consensusBadge = document.createElement("span");
    consensusBadge.className = "consensus-badge " + consensusBadgeClass(flagged);
    consensusBadge.textContent = "[" + flagged + "/" + responded + "]";
    summaryRow.appendChild(consensusBadge);
  }
  function createContextRow(result) {
    const row = document.createElement("div");
    row.className = "provider-detail-row provider-context-row";
    row.setAttribute("data-verdict", "context");
    const nameSpan = document.createElement("span");
    nameSpan.className = "provider-detail-name";
    nameSpan.textContent = result.provider;
    row.appendChild(nameSpan);
    const contextEl = createContextFields(result);
    if (contextEl) {
      row.appendChild(contextEl);
    }
    if (result.cached_at) {
      const cacheBadge = document.createElement("span");
      cacheBadge.className = "cache-badge";
      cacheBadge.textContent = "cached " + formatRelativeTime(result.cached_at);
      row.appendChild(cacheBadge);
    }
    return row;
  }
  function createDetailRow(provider, verdict, statText, result) {
    const row = document.createElement("div");
    row.className = "provider-detail-row";
    row.setAttribute("data-verdict", verdict);
    const nameSpan = document.createElement("span");
    nameSpan.className = "provider-detail-name";
    nameSpan.textContent = provider;
    const badge = document.createElement("span");
    badge.className = "verdict-badge verdict-" + verdict;
    badge.textContent = VERDICT_LABELS[verdict];
    const statSpan = document.createElement("span");
    statSpan.className = "provider-detail-stat";
    statSpan.textContent = statText;
    row.appendChild(nameSpan);
    row.appendChild(badge);
    row.appendChild(statSpan);
    if (result && result.type === "result" && result.cached_at) {
      const cacheBadge = document.createElement("span");
      cacheBadge.className = "cache-badge";
      const ago = formatRelativeTime(result.cached_at);
      cacheBadge.textContent = "cached " + ago;
      row.appendChild(cacheBadge);
    }
    if (result && result.type === "result") {
      const contextEl = createContextFields(result);
      if (contextEl) {
        row.appendChild(contextEl);
      }
    }
    return row;
  }

  // app/static/src/ts/modules/enrichment.ts
  var sortTimers = /* @__PURE__ */ new Map();
  var allResults = [];
  function sortDetailRows(detailsContainer, iocValue) {
    const existing = sortTimers.get(iocValue);
    if (existing !== void 0) {
      clearTimeout(existing);
    }
    const timer = setTimeout(() => {
      sortTimers.delete(iocValue);
      const rows = Array.from(
        detailsContainer.querySelectorAll(".provider-detail-row")
      );
      rows.sort((a, b) => {
        const aVerdict = a.getAttribute("data-verdict");
        const bVerdict = b.getAttribute("data-verdict");
        const aIdx = aVerdict ? verdictSeverityIndex(aVerdict) : -1;
        const bIdx = bVerdict ? verdictSeverityIndex(bVerdict) : -1;
        return bIdx - aIdx;
      });
      for (const row of rows) {
        detailsContainer.appendChild(row);
      }
      const contextRows = Array.from(
        detailsContainer.querySelectorAll('.provider-detail-row[data-verdict="context"]')
      );
      for (const cr of contextRows) {
        detailsContainer.insertBefore(cr, detailsContainer.firstChild);
      }
    }, 100);
    sortTimers.set(iocValue, timer);
  }
  function findCopyButtonForIoc(iocValue) {
    const btns = document.querySelectorAll(".copy-btn");
    for (let i = 0; i < btns.length; i++) {
      const btn = btns[i];
      if (btn && attr(btn, "data-value") === iocValue) {
        return btn;
      }
    }
    return null;
  }
  function updateCopyButtonWorstVerdict(iocValue, iocVerdicts) {
    const copyBtn = findCopyButtonForIoc(iocValue);
    if (!copyBtn) return;
    const worstEntry = findWorstEntry(iocVerdicts[iocValue] ?? []);
    if (!worstEntry) return;
    copyBtn.setAttribute("data-enrichment", worstEntry.summaryText);
  }
  function updateProgressBar(done, total) {
    const fill = document.getElementById("enrich-progress-fill");
    const text = document.getElementById("enrich-progress-text");
    if (!fill || !text) return;
    const pct = total > 0 ? Math.round(done / total * 100) : 0;
    fill.style.width = pct + "%";
    text.textContent = done + "/" + total + " providers complete";
  }
  function updatePendingIndicator(slot, card, receivedCount) {
    const iocType = card ? attr(card, "data-ioc-type") : "";
    const providerCounts = getProviderCounts();
    const totalExpected = Object.prototype.hasOwnProperty.call(providerCounts, iocType) ? providerCounts[iocType] ?? 0 : 0;
    const remaining = totalExpected - receivedCount;
    if (remaining <= 0) {
      const existingIndicator = slot.querySelector(".enrichment-waiting-text");
      if (existingIndicator) {
        slot.removeChild(existingIndicator);
      }
      return;
    }
    let indicator = slot.querySelector(".enrichment-waiting-text");
    if (!indicator) {
      indicator = document.createElement("span");
      indicator.className = "enrichment-waiting-text enrichment-pending-text";
      slot.appendChild(indicator);
    }
    indicator.textContent = remaining + " provider" + (remaining !== 1 ? "s" : "") + " still loading...";
  }
  function showEnrichWarning(message) {
    const banner = document.getElementById("enrich-warning");
    if (!banner) return;
    banner.style.display = "block";
    banner.textContent = "Warning: " + message + " Consider using offline mode or checking your API key in Settings.";
  }
  function markEnrichmentComplete() {
    const container = document.getElementById("enrich-progress");
    if (container) {
      container.classList.add("complete");
    }
    const text = document.getElementById("enrich-progress-text");
    if (text) {
      text.textContent = "Enrichment complete";
    }
    const exportBtn = document.getElementById("export-btn");
    if (exportBtn) {
      exportBtn.removeAttribute("disabled");
    }
  }
  function renderEnrichmentResult(result, iocVerdicts, iocResultCounts) {
    const card = findCardForIoc(result.ioc_value);
    if (!card) return;
    const slot = card.querySelector(".enrichment-slot");
    if (!slot) return;
    if (CONTEXT_PROVIDERS.has(result.provider)) {
      const spinnerWrapper2 = slot.querySelector(".spinner-wrapper");
      if (spinnerWrapper2) slot.removeChild(spinnerWrapper2);
      slot.classList.add("enrichment-slot--loaded");
      iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;
      const detailsContainer2 = slot.querySelector(".enrichment-details");
      if (detailsContainer2 && result.type === "result") {
        const contextRow = createContextRow(result);
        detailsContainer2.insertBefore(contextRow, detailsContainer2.firstChild);
      }
      updatePendingIndicator(slot, card, iocResultCounts[result.ioc_value] ?? 1);
      return;
    }
    const spinnerWrapper = slot.querySelector(".spinner-wrapper");
    if (spinnerWrapper) {
      slot.removeChild(spinnerWrapper);
    }
    slot.classList.add("enrichment-slot--loaded");
    iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;
    const receivedCount = iocResultCounts[result.ioc_value] ?? 1;
    let verdict;
    let statText;
    let summaryText;
    let detectionCount = 0;
    let totalEngines = 0;
    if (result.type === "result") {
      verdict = result.verdict;
      detectionCount = result.detection_count;
      totalEngines = result.total_engines;
      if (verdict === "malicious") {
        statText = result.detection_count + "/" + result.total_engines + " engines";
      } else if (verdict === "suspicious") {
        statText = result.total_engines > 1 ? result.detection_count + "/" + result.total_engines + " engines" : "Suspicious";
      } else if (verdict === "clean") {
        statText = "Clean, " + result.total_engines + " engines";
      } else if (verdict === "known_good") {
        statText = "NSRL match";
      } else {
        statText = "Not in database";
      }
      const scanDateStr = formatDate(result.scan_date);
      summaryText = result.provider + ": " + verdict + " (" + statText + (scanDateStr ? ", scanned " + scanDateStr : "") + ")";
    } else {
      verdict = "error";
      statText = result.error;
      summaryText = result.provider + ": error, " + result.error;
    }
    const entries = iocVerdicts[result.ioc_value] ?? [];
    iocVerdicts[result.ioc_value] = entries;
    entries.push({ provider: result.provider, verdict, summaryText, detectionCount, totalEngines, statText });
    const detailsContainer = slot.querySelector(".enrichment-details");
    if (detailsContainer) {
      const detailRow = createDetailRow(result.provider, verdict, statText, result);
      detailsContainer.appendChild(detailRow);
      sortDetailRows(detailsContainer, result.ioc_value);
    }
    updateSummaryRow(slot, result.ioc_value, iocVerdicts);
    updatePendingIndicator(slot, card, receivedCount);
    const worstVerdict = computeWorstVerdict(iocVerdicts[result.ioc_value] ?? []);
    updateCardVerdict(result.ioc_value, worstVerdict);
    updateDashboardCounts();
    sortCardsBySeverity();
    updateCopyButtonWorstVerdict(result.ioc_value, iocVerdicts);
  }
  function wireExpandToggles() {
    const toggles = document.querySelectorAll(".chevron-toggle");
    toggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const details = toggle.nextElementSibling;
        if (!details || !details.classList.contains("enrichment-details")) return;
        const isOpen = details.classList.toggle("is-open");
        toggle.classList.toggle("is-open", isOpen);
        toggle.setAttribute("aria-expanded", String(isOpen));
      });
    });
  }
  function initExportButton() {
    const exportBtn = document.getElementById("export-btn");
    const dropdown = document.getElementById("export-dropdown");
    if (!exportBtn || !dropdown) return;
    exportBtn.addEventListener("click", function() {
      const isVisible = dropdown.style.display !== "none";
      dropdown.style.display = isVisible ? "none" : "";
    });
    document.addEventListener("click", function(e) {
      const target = e.target;
      if (!target.closest(".export-group")) {
        dropdown.style.display = "none";
      }
    });
    const buttons = dropdown.querySelectorAll("[data-export]");
    buttons.forEach(function(btn) {
      btn.addEventListener("click", function() {
        const action = btn.getAttribute("data-export");
        if (action === "json") {
          exportJSON(allResults);
        } else if (action === "csv") {
          exportCSV(allResults);
        } else if (action === "iocs") {
          copyAllIOCs(btn);
        }
        dropdown.style.display = "none";
      });
    });
  }
  function init5() {
    const pageResults = document.querySelector(".page-results");
    if (!pageResults) return;
    const jobId = attr(pageResults, "data-job-id");
    const mode = attr(pageResults, "data-mode");
    if (!jobId || mode !== "online") return;
    wireExpandToggles();
    const rendered = {};
    const iocVerdicts = {};
    const iocResultCounts = {};
    const intervalId = setInterval(function() {
      fetch("/enrichment/status/" + jobId).then(function(resp) {
        if (!resp.ok) return null;
        return resp.json();
      }).then(function(data) {
        if (!data) return;
        updateProgressBar(data.done, data.total);
        const results = data.results;
        for (let i = 0; i < results.length; i++) {
          const result = results[i];
          if (!result) continue;
          const dedupKey = result.ioc_value + "|" + result.provider;
          if (!rendered[dedupKey]) {
            rendered[dedupKey] = true;
            allResults.push(result);
            renderEnrichmentResult(result, iocVerdicts, iocResultCounts);
          }
          if (result.type === "error" && result.error) {
            const errLower = result.error.toLowerCase();
            if (errLower.indexOf("rate limit") !== -1 || errLower.indexOf("429") !== -1) {
              showEnrichWarning("Rate limit reached for " + result.provider + ".");
            } else if (errLower.indexOf("authentication") !== -1 || errLower.indexOf("401") !== -1 || errLower.indexOf("403") !== -1) {
              showEnrichWarning(
                "Authentication error for " + result.provider + ". Please check your API key in Settings."
              );
            }
          }
        }
        if (data.complete) {
          clearInterval(intervalId);
          markEnrichmentComplete();
        }
      }).catch(function() {
      });
    }, 750);
    initExportButton();
  }

  // app/static/src/ts/modules/settings.ts
  function initAccordion() {
    const sections = document.querySelectorAll(
      ".settings-section[data-provider]"
    );
    if (sections.length === 0) return;
    function expandSection(section) {
      sections.forEach((s) => {
        if (s !== section) {
          s.removeAttribute("data-expanded");
          const btn2 = s.querySelector(".accordion-header");
          if (btn2) btn2.setAttribute("aria-expanded", "false");
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
  }
  function initKeyToggles() {
    const sections = document.querySelectorAll(".settings-section");
    sections.forEach((section) => {
      const btn = section.querySelector(
        "[data-role='toggle-key']"
      );
      const input = section.querySelector(
        "input[type='password'], input[type='text']"
      );
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
  function init6() {
    initAccordion();
    initKeyToggles();
  }

  // app/static/src/ts/modules/ui.ts
  function initScrollAwareFilterBar() {
    const filterBar = document.querySelector(".filter-bar-wrapper");
    if (!filterBar) return;
    let scrolled = false;
    window.addEventListener(
      "scroll",
      function() {
        const isScrolled = window.scrollY > 40;
        if (isScrolled !== scrolled) {
          scrolled = isScrolled;
          filterBar.classList.toggle("is-scrolled", scrolled);
        }
      },
      { passive: true }
    );
  }
  function initCardStagger() {
    const cards = document.querySelectorAll(".ioc-card");
    cards.forEach((card, i) => {
      card.style.setProperty("--card-index", String(Math.min(i, 15)));
    });
  }
  function init7() {
    initScrollAwareFilterBar();
    initCardStagger();
  }

  // app/static/src/ts/modules/graph.ts
  var VERDICT_COLORS = {
    malicious: "#ef4444",
    suspicious: "#f97316",
    clean: "#22c55e",
    known_good: "#3b82f6",
    no_data: "#6b7280",
    error: "#6b7280",
    ioc: "#8b5cf6"
  };
  var SVG_NS = "http://www.w3.org/2000/svg";
  function verdictColor(verdict) {
    return VERDICT_COLORS[verdict] ?? "#6b7280";
  }
  function svgEl(tag) {
    return document.createElementNS(SVG_NS, tag);
  }
  function renderRelationshipGraph(container) {
    const nodesAttr = container.getAttribute("data-graph-nodes");
    const edgesAttr = container.getAttribute("data-graph-edges");
    let nodes = [];
    let edges = [];
    try {
      nodes = nodesAttr ? JSON.parse(nodesAttr) : [];
      edges = edgesAttr ? JSON.parse(edgesAttr) : [];
    } catch {
      nodes = [];
      edges = [];
    }
    const providerNodes = nodes.filter((n) => n.role === "provider");
    const iocNode = nodes.find((n) => n.role === "ioc");
    if (!iocNode || providerNodes.length === 0) {
      const msg = document.createElement("p");
      msg.className = "graph-empty";
      msg.appendChild(document.createTextNode("No provider data to graph"));
      container.appendChild(msg);
      return;
    }
    const svg = svgEl("svg");
    svg.setAttribute("viewBox", "0 0 600 400");
    svg.setAttribute("width", "100%");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Provider relationship graph");
    const cx = 300;
    const cy = 200;
    const orbitRadius = 150;
    const iocrr = 30;
    const prrr = 20;
    const edgeGroup = svgEl("g");
    edgeGroup.setAttribute("class", "graph-edges");
    for (const edge of edges) {
      const targetNode = providerNodes.find((n) => n.id === edge.to);
      if (!targetNode) continue;
      const idx = providerNodes.indexOf(targetNode);
      const angle = 2 * Math.PI * idx / providerNodes.length - Math.PI / 2;
      const px = cx + orbitRadius * Math.cos(angle);
      const py = cy + orbitRadius * Math.sin(angle);
      const line = svgEl("line");
      line.setAttribute("x1", String(cx));
      line.setAttribute("y1", String(cy));
      line.setAttribute("x2", String(Math.round(px)));
      line.setAttribute("y2", String(Math.round(py)));
      line.setAttribute("stroke", verdictColor(edge.verdict));
      line.setAttribute("stroke-width", "2");
      line.setAttribute("opacity", "0.6");
      edgeGroup.appendChild(line);
    }
    svg.appendChild(edgeGroup);
    const nodeGroup = svgEl("g");
    nodeGroup.setAttribute("class", "graph-nodes");
    providerNodes.forEach((node, idx) => {
      const angle = 2 * Math.PI * idx / providerNodes.length - Math.PI / 2;
      const px = cx + orbitRadius * Math.cos(angle);
      const py = cy + orbitRadius * Math.sin(angle);
      const group = svgEl("g");
      group.setAttribute("class", "graph-node graph-node--provider");
      const title = svgEl("title");
      title.appendChild(document.createTextNode(node.id));
      group.appendChild(title);
      const circle = svgEl("circle");
      circle.setAttribute("cx", String(Math.round(px)));
      circle.setAttribute("cy", String(Math.round(py)));
      circle.setAttribute("r", String(prrr));
      circle.setAttribute("fill", verdictColor(node.verdict));
      group.appendChild(circle);
      const text = svgEl("text");
      text.setAttribute("x", String(Math.round(px)));
      text.setAttribute("y", String(Math.round(py + prrr + 14)));
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("font-size", "11");
      text.setAttribute("fill", "#e5e7eb");
      text.appendChild(document.createTextNode(node.label.slice(0, 12)));
      group.appendChild(text);
      nodeGroup.appendChild(group);
    });
    svg.appendChild(nodeGroup);
    const iocGroup = svgEl("g");
    iocGroup.setAttribute("class", "graph-node graph-node--ioc");
    const iocTitle = svgEl("title");
    iocTitle.appendChild(document.createTextNode(iocNode.id));
    iocGroup.appendChild(iocTitle);
    const iocCircle = svgEl("circle");
    iocCircle.setAttribute("cx", String(cx));
    iocCircle.setAttribute("cy", String(cy));
    iocCircle.setAttribute("r", String(iocrr));
    iocCircle.setAttribute("fill", verdictColor("ioc"));
    iocGroup.appendChild(iocCircle);
    const iocText = svgEl("text");
    iocText.setAttribute("x", String(cx));
    iocText.setAttribute("y", String(cy + 4));
    iocText.setAttribute("text-anchor", "middle");
    iocText.setAttribute("font-size", "10");
    iocText.setAttribute("fill", "#fff");
    iocText.setAttribute("font-weight", "bold");
    iocText.appendChild(document.createTextNode(iocNode.label.slice(0, 20)));
    iocGroup.appendChild(iocText);
    svg.appendChild(iocGroup);
    container.appendChild(svg);
  }
  function init8() {
    const container = document.getElementById("relationship-graph");
    if (container) {
      renderRelationshipGraph(container);
    }
  }

  // app/static/src/ts/main.ts
  function init9() {
    init();
    init2();
    init3();
    init4();
    init5();
    init6();
    init7();
    init8();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init9);
  } else {
    init9();
  }
})();
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vc3JjL3RzL3V0aWxzL2RvbS50cyIsICIuLi9zcmMvdHMvbW9kdWxlcy9mb3JtLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2NsaXBib2FyZC50cyIsICIuLi9zcmMvdHMvdHlwZXMvaW9jLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2NhcmRzLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2ZpbHRlci50cyIsICIuLi9zcmMvdHMvbW9kdWxlcy9leHBvcnQudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvdmVyZGljdC1jb21wdXRlLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL3Jvdy1mYWN0b3J5LnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2VucmljaG1lbnQudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvc2V0dGluZ3MudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvdWkudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvZ3JhcGgudHMiLCAiLi4vc3JjL3RzL21haW4udHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbIi8qKlxuICogU2hhcmVkIERPTSB1dGlsaXRpZXMgZm9yIFNlbnRpbmVsWCBUeXBlU2NyaXB0IG1vZHVsZXMuXG4gKi9cblxuLyoqXG4gKiBUeXBlZCBnZXRBdHRyaWJ1dGUgd3JhcHBlciBcdTIwMTQgcmV0dXJucyBzdHJpbmcgaW5zdGVhZCBvZiBzdHJpbmcgfCBudWxsLlxuICogQ2FsbGVycyBwYXNzIGEgZmFsbGJhY2sgKGRlZmF1bHQ6IFwiXCIpIHRvIGF2b2lkIG51bGwgcHJvcGFnYXRpb24uXG4gKiBBdHRyaWJ1dGUgbmFtZXMgYXJlIGludGVudGlvbmFsbHkgdHlwZWQgYXMgc3RyaW5nIChub3QgYSB1bmlvbikgZm9yIGZsZXhpYmlsaXR5LlxuICovXG5leHBvcnQgZnVuY3Rpb24gYXR0cihlbDogRWxlbWVudCwgbmFtZTogc3RyaW5nLCBmYWxsYmFjayA9IFwiXCIpOiBzdHJpbmcge1xuICByZXR1cm4gZWwuZ2V0QXR0cmlidXRlKG5hbWUpID8/IGZhbGxiYWNrO1xufVxuIiwgIi8qKlxuICogRm9ybSBjb250cm9scyBtb2R1bGUgXHUyMDE0IHN1Ym1pdCBidXR0b24gc3RhdGUsIGF1dG8tZ3JvdyB0ZXh0YXJlYSxcbiAqIG1vZGUgdG9nZ2xlLCBhbmQgcGFzdGUgZmVlZGJhY2suXG4gKlxuICogRXh0cmFjdGVkIGZyb20gbWFpbi5qcyBpbml0U3VibWl0QnV0dG9uKCksIGluaXRBdXRvR3JvdygpLFxuICogaW5pdE1vZGVUb2dnbGUoKSwgdXBkYXRlU3VibWl0TGFiZWwoKSwgc2hvd1Bhc3RlRmVlZGJhY2soKSAobGluZXMgMzQtMTYyKS5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vLyBNb2R1bGUtbGV2ZWwgdGltZXIgZm9yIHBhc3RlIGZlZWRiYWNrIGFuaW1hdGlvbiBcdTIwMTQgYXZvaWRzIHN0b3Jpbmcgb24gSFRNTEVsZW1lbnRcbmxldCBwYXN0ZVRpbWVyOiBSZXR1cm5UeXBlPHR5cGVvZiBzZXRUaW1lb3V0PiB8IG51bGwgPSBudWxsO1xuXG4vLyAtLS0tIFBhc3RlIGNoYXJhY3RlciBjb3VudCBmZWVkYmFjayAoSU5QVVQtMDIpIC0tLS1cblxuZnVuY3Rpb24gc2hvd1Bhc3RlRmVlZGJhY2soY2hhckNvdW50OiBudW1iZXIpOiB2b2lkIHtcbiAgY29uc3QgZmVlZGJhY2sgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInBhc3RlLWZlZWRiYWNrXCIpO1xuICBpZiAoIWZlZWRiYWNrKSByZXR1cm47XG4gIGZlZWRiYWNrLnRleHRDb250ZW50ID0gY2hhckNvdW50ICsgXCIgY2hhcmFjdGVycyBwYXN0ZWRcIjtcbiAgZmVlZGJhY2suc3R5bGUuZGlzcGxheSA9IFwiXCI7XG4gIGZlZWRiYWNrLmNsYXNzTGlzdC5yZW1vdmUoXCJpcy1oaWRpbmdcIik7XG4gIGZlZWRiYWNrLmNsYXNzTGlzdC5hZGQoXCJpcy12aXNpYmxlXCIpO1xuICBpZiAocGFzdGVUaW1lciAhPT0gbnVsbCkgY2xlYXJUaW1lb3V0KHBhc3RlVGltZXIpO1xuICBwYXN0ZVRpbWVyID0gc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgZmVlZGJhY2suY2xhc3NMaXN0LnJlbW92ZShcImlzLXZpc2libGVcIik7XG4gICAgZmVlZGJhY2suY2xhc3NMaXN0LmFkZChcImlzLWhpZGluZ1wiKTtcbiAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcbiAgICAgIGZlZWRiYWNrLnN0eWxlLmRpc3BsYXkgPSBcIm5vbmVcIjtcbiAgICAgIGZlZWRiYWNrLmNsYXNzTGlzdC5yZW1vdmUoXCJpcy1oaWRpbmdcIik7XG4gICAgfSwgMjUwKTtcbiAgfSwgMjAwMCk7XG59XG5cbi8vIC0tLS0gU3VibWl0IGxhYmVsIChtb2RlLWF3YXJlKSAtLS0tXG5cbmZ1bmN0aW9uIHVwZGF0ZVN1Ym1pdExhYmVsKG1vZGU6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCBzdWJtaXRCdG4gPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInN1Ym1pdC1idG5cIik7XG4gIGlmICghc3VibWl0QnRuKSByZXR1cm47XG4gIHN1Ym1pdEJ0bi50ZXh0Q29udGVudCA9IFwiRXh0cmFjdFwiO1xuICAvLyBNb2RlLWF3YXJlIGJ1dHRvbiBjb2xvclxuICBzdWJtaXRCdG4uY2xhc3NMaXN0LnJlbW92ZShcIm1vZGUtb25saW5lXCIsIFwibW9kZS1vZmZsaW5lXCIpO1xuICBzdWJtaXRCdG4uY2xhc3NMaXN0LmFkZChtb2RlID09PSBcIm9ubGluZVwiID8gXCJtb2RlLW9ubGluZVwiIDogXCJtb2RlLW9mZmxpbmVcIik7XG59XG5cbi8vIC0tLS0gU3VibWl0IGJ1dHRvbjogZGlzYWJsZSB3aGVuIHRleHRhcmVhIGlzIGVtcHR5IC0tLS1cblxuZnVuY3Rpb24gaW5pdFN1Ym1pdEJ1dHRvbigpOiB2b2lkIHtcbiAgY29uc3QgZm9ybSA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiYW5hbHl6ZS1mb3JtXCIpO1xuICBpZiAoIWZvcm0pIHJldHVybjtcblxuICBjb25zdCB0ZXh0YXJlYSA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTFRleHRBcmVhRWxlbWVudD4oXCIjaW9jLXRleHRcIik7XG4gIGNvbnN0IHN1Ym1pdEJ0biA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTEJ1dHRvbkVsZW1lbnQ+KFwiI3N1Ym1pdC1idG5cIik7XG4gIGNvbnN0IGNsZWFyQnRuID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJjbGVhci1idG5cIik7XG5cbiAgaWYgKCF0ZXh0YXJlYSB8fCAhc3VibWl0QnRuKSByZXR1cm47XG5cbiAgLy8gUmUtYmluZCB0byBub24tbnVsbGFibGUgYWxpYXNlcyBzbyBjbG9zdXJlcyBiZWxvdyBkb24ndCBuZWVkIGFzc2VydGlvbnMuXG4gIC8vIFR5cGVTY3JpcHQgbmFycm93cyB0aGUgb3V0ZXIgYGNvbnN0YCBhZnRlciB0aGUgaWYtY2hlY2ssIGJ1dCBjbG9zdXJlc1xuICAvLyAoZXZlbiBub24tYXN5bmMgb25lcykgY2Fubm90IHNlZSB0aGF0IG5hcnJvd2luZyBcdTIwMTQgd2UgdGhlcmVmb3JlIGludHJvZHVjZVxuICAvLyBuZXcgYGNvbnN0YCBiaW5kaW5ncyB0aGF0IGFyZSBndWFyYW50ZWVkIG5vbi1udWxsLlxuICBjb25zdCB0YTogSFRNTFRleHRBcmVhRWxlbWVudCA9IHRleHRhcmVhO1xuICBjb25zdCBzYjogSFRNTEJ1dHRvbkVsZW1lbnQgPSBzdWJtaXRCdG47XG5cbiAgZnVuY3Rpb24gdXBkYXRlU3VibWl0U3RhdGUoKTogdm9pZCB7XG4gICAgc2IuZGlzYWJsZWQgPSB0YS52YWx1ZS50cmltKCkubGVuZ3RoID09PSAwO1xuICB9XG5cbiAgdGEuYWRkRXZlbnRMaXN0ZW5lcihcImlucHV0XCIsIHVwZGF0ZVN1Ym1pdFN0YXRlKTtcblxuICAvLyBBbHNvIGhhbmRsZSBwYXN0ZSBldmVudHMgKGJyb3dzZXIgbWF5IG5vdCBmaXJlIFwiaW5wdXRcIiBpbW1lZGlhdGVseSlcbiAgdGEuYWRkRXZlbnRMaXN0ZW5lcihcInBhc3RlXCIsIGZ1bmN0aW9uICgpIHtcbiAgICAvLyBEZWZlciB1bnRpbCBhZnRlciBwYXN0ZSBjb250ZW50IGlzIGFwcGxpZWRcbiAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcbiAgICAgIHVwZGF0ZVN1Ym1pdFN0YXRlKCk7XG4gICAgICBzaG93UGFzdGVGZWVkYmFjayh0YS52YWx1ZS5sZW5ndGgpO1xuICAgIH0sIDApO1xuICB9KTtcblxuICAvLyBJbml0aWFsIHN0YXRlIChwYWdlIGxvYWQgd2l0aCBwcmUtZmlsbGVkIGNvbnRlbnQpXG4gIHVwZGF0ZVN1Ym1pdFN0YXRlKCk7XG5cbiAgLy8gLS0tLSBDbGVhciBidXR0b24gLS0tLVxuICBpZiAoY2xlYXJCdG4pIHtcbiAgICBjbGVhckJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgICAgdGEudmFsdWUgPSBcIlwiO1xuICAgICAgdXBkYXRlU3VibWl0U3RhdGUoKTtcbiAgICAgIHRhLmZvY3VzKCk7XG4gICAgfSk7XG4gIH1cbn1cblxuLy8gLS0tLSBBdXRvLWdyb3cgdGV4dGFyZWEgKElOUC0wMikgLS0tLVxuXG5mdW5jdGlvbiBpbml0QXV0b0dyb3coKTogdm9pZCB7XG4gIGNvbnN0IHRleHRhcmVhID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcjxIVE1MVGV4dEFyZWFFbGVtZW50PihcIiNpb2MtdGV4dFwiKTtcbiAgaWYgKCF0ZXh0YXJlYSkgcmV0dXJuO1xuXG4gIC8vIE5vbi1udWxsYWJsZSBhbGlhcyBmb3IgdXNlIGluc2lkZSBjbG9zdXJlcyAoVHlwZVNjcmlwdCBjYW4ndCBuYXJyb3cgdGhyb3VnaCBjbG9zdXJlcylcbiAgY29uc3QgdGE6IEhUTUxUZXh0QXJlYUVsZW1lbnQgPSB0ZXh0YXJlYTtcblxuICBmdW5jdGlvbiBncm93KCk6IHZvaWQge1xuICAgIHRhLnN0eWxlLmhlaWdodCA9IFwiYXV0b1wiO1xuICAgIHRhLnN0eWxlLmhlaWdodCA9IHRhLnNjcm9sbEhlaWdodCArIFwicHhcIjtcbiAgfVxuXG4gIHRhLmFkZEV2ZW50TGlzdGVuZXIoXCJpbnB1dFwiLCBncm93KTtcblxuICB0YS5hZGRFdmVudExpc3RlbmVyKFwicGFzdGVcIiwgZnVuY3Rpb24gKCkge1xuICAgIHNldFRpbWVvdXQoZ3JvdywgMCk7XG4gIH0pO1xuXG4gIGdyb3coKTtcbn1cblxuLy8gLS0tLSBNb2RlIHRvZ2dsZSBzd2l0Y2ggKElOUFVULTAxLCBJTlBVVC0wMykgLS0tLVxuXG5mdW5jdGlvbiBpbml0TW9kZVRvZ2dsZSgpOiB2b2lkIHtcbiAgY29uc3Qgd2lkZ2V0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJtb2RlLXRvZ2dsZS13aWRnZXRcIik7XG4gIGNvbnN0IHRvZ2dsZUJ0biA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwibW9kZS10b2dnbGUtYnRuXCIpO1xuICBjb25zdCBtb2RlSW5wdXQgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yPEhUTUxJbnB1dEVsZW1lbnQ+KFwiI21vZGUtaW5wdXRcIik7XG4gIGlmICghd2lkZ2V0IHx8ICF0b2dnbGVCdG4gfHwgIW1vZGVJbnB1dCkgcmV0dXJuO1xuXG4gIC8vIE5vbi1udWxsYWJsZSBhbGlhc2VzIGZvciBjbG9zdXJlc1xuICBjb25zdCB3OiBIVE1MRWxlbWVudCA9IHdpZGdldDtcbiAgY29uc3QgdGI6IEhUTUxFbGVtZW50ID0gdG9nZ2xlQnRuO1xuICBjb25zdCBtaTogSFRNTElucHV0RWxlbWVudCA9IG1vZGVJbnB1dDtcblxuICB0Yi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgIGNvbnN0IGN1cnJlbnQgPSBhdHRyKHcsIFwiZGF0YS1tb2RlXCIpO1xuICAgIGNvbnN0IG5leHQgPSBjdXJyZW50ID09PSBcIm9mZmxpbmVcIiA/IFwib25saW5lXCIgOiBcIm9mZmxpbmVcIjtcbiAgICB3LnNldEF0dHJpYnV0ZShcImRhdGEtbW9kZVwiLCBuZXh0KTtcbiAgICBtaS52YWx1ZSA9IG5leHQ7XG4gICAgdGIuc2V0QXR0cmlidXRlKFwiYXJpYS1wcmVzc2VkXCIsIG5leHQgPT09IFwib25saW5lXCIgPyBcInRydWVcIiA6IFwiZmFsc2VcIik7XG4gICAgdXBkYXRlU3VibWl0TGFiZWwobmV4dCk7XG4gIH0pO1xuXG4gIC8vIFNldCBpbml0aWFsIGxhYmVsIGJhc2VkIG9uIGN1cnJlbnQgbW9kZSAoZGVmZW5zaXZlKVxuICB1cGRhdGVTdWJtaXRMYWJlbChtaS52YWx1ZSk7XG59XG5cbi8vIC0tLS0gUHVibGljIEFQSSAtLS0tXG5cbi8qKlxuICogSW5pdGlhbGlzZSBhbGwgZm9ybSBjb250cm9sczogc3VibWl0IGJ1dHRvbiBzdGF0ZSwgYXV0by1ncm93LCBhbmQgbW9kZSB0b2dnbGUuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBpbml0U3VibWl0QnV0dG9uKCk7XG4gIGluaXRBdXRvR3JvdygpO1xuICBpbml0TW9kZVRvZ2dsZSgpO1xufVxuIiwgIi8qKlxuICogQ2xpcGJvYXJkIG1vZHVsZSBcdTIwMTQgY29weSBidXR0b25zLCBjb3B5LXdpdGgtZW5yaWNobWVudCwgYW5kIGZhbGxiYWNrIGNvcHkuXG4gKlxuICogRXh0cmFjdGVkIGZyb20gbWFpbi5qcyBpbml0Q29weUJ1dHRvbnMoKSwgc2hvd0NvcGllZEZlZWRiYWNrKCksXG4gKiBmYWxsYmFja0NvcHkoKSwgYW5kIHdyaXRlVG9DbGlwYm9hcmQoKSAobGluZXMgMTY2LTIyMykuXG4gKlxuICogd3JpdGVUb0NsaXBib2FyZCBpcyBleHBvcnRlZCBmb3IgdXNlIGJ5IFBoYXNlIDIyJ3MgZW5yaWNobWVudCBtb2R1bGVcbiAqIChleHBvcnQgYnV0dG9uIG5lZWRzIHRvIGNvcHkgbXVsdGktSU9DIHRleHQgdG8gY2xpcGJvYXJkKS5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vLyAtLS0tIFByaXZhdGUgaGVscGVycyAtLS0tXG5cbi8qKlxuICogVGVtcG9yYXJpbHkgcmVwbGFjZSBidXR0b24gdGV4dCB3aXRoIFwiQ29waWVkIVwiIHRoZW4gcmVzdG9yZSBhZnRlciAxNTAwbXMuXG4gKiB0ZXh0Q29udGVudCBpcyB0eXBlZCBzdHJpbmd8bnVsbCBcdTIwMTQgPz8gZW5zdXJlcyB0aGUgb3JpZ2luYWwgdmFsdWUgaXMgbmV2ZXIgbnVsbC5cbiAqL1xuZnVuY3Rpb24gc2hvd0NvcGllZEZlZWRiYWNrKGJ0bjogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgY29uc3Qgb3JpZ2luYWwgPSBidG4udGV4dENvbnRlbnQgPz8gXCJDb3B5XCI7XG4gIGJ0bi50ZXh0Q29udGVudCA9IFwiQ29waWVkIVwiO1xuICBidG4uY2xhc3NMaXN0LmFkZChcImNvcGllZFwiKTtcbiAgc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgYnRuLnRleHRDb250ZW50ID0gb3JpZ2luYWw7XG4gICAgYnRuLmNsYXNzTGlzdC5yZW1vdmUoXCJjb3BpZWRcIik7XG4gIH0sIDE1MDApO1xufVxuXG4vKipcbiAqIEZhbGxiYWNrIGNvcHkgdmlhIGEgdGVtcG9yYXJ5IG9mZi1zY3JlZW4gdGV4dGFyZWEgYW5kIGV4ZWNDb21tYW5kKFwiY29weVwiKS5cbiAqIFVzZWQgd2hlbiBuYXZpZ2F0b3IuY2xpcGJvYXJkIGlzIHVuYXZhaWxhYmxlIChub24tSFRUUFMsIG9sZGVyIGJyb3dzZXIpLlxuICovXG5mdW5jdGlvbiBmYWxsYmFja0NvcHkodGV4dDogc3RyaW5nLCBidG46IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gIC8vIENyZWF0ZSBhIHRlbXBvcmFyeSB0ZXh0YXJlYSwgc2VsZWN0IGl0cyBjb250ZW50LCBhbmQgY29weVxuICBjb25zdCB0bXAgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwidGV4dGFyZWFcIik7XG4gIHRtcC52YWx1ZSA9IHRleHQ7XG4gIHRtcC5zdHlsZS5wb3NpdGlvbiA9IFwiZml4ZWRcIjtcbiAgdG1wLnN0eWxlLnRvcCA9IFwiLTk5OTlweFwiO1xuICB0bXAuc3R5bGUubGVmdCA9IFwiLTk5OTlweFwiO1xuICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKHRtcCk7XG4gIHRtcC5mb2N1cygpO1xuICB0bXAuc2VsZWN0KCk7XG4gIHRyeSB7XG4gICAgZG9jdW1lbnQuZXhlY0NvbW1hbmQoXCJjb3B5XCIpO1xuICAgIHNob3dDb3BpZWRGZWVkYmFjayhidG4pO1xuICB9IGNhdGNoIHtcbiAgICAvLyBDb3B5IGZhaWxlZCBzaWxlbnRseSBcdTIwMTQgdXNlciBjYW4gc3RpbGwgbWFudWFsbHkgc2VsZWN0IHRoZSB2YWx1ZVxuICB9IGZpbmFsbHkge1xuICAgIGRvY3VtZW50LmJvZHkucmVtb3ZlQ2hpbGQodG1wKTtcbiAgfVxufVxuXG4vLyAtLS0tIFB1YmxpYyBBUEkgLS0tLVxuXG4vKipcbiAqIENvcHkgdGV4dCB0byB0aGUgY2xpcGJvYXJkIHVzaW5nIHRoZSBDbGlwYm9hcmQgQVBJLCBmYWxsaW5nIGJhY2sgdG9cbiAqIGV4ZWNDb21tYW5kIHdoZW4gdW5hdmFpbGFibGUuIFNob3dzIGZlZWRiYWNrIG9uIHRoZSB0cmlnZ2VyaW5nIGJ1dHRvbi5cbiAqXG4gKiBFeHBvcnRlZCBzbyBQaGFzZSAyMidzIGVucmljaG1lbnQgbW9kdWxlIGNhbiBjYWxsIGl0IGZvciB0aGUgZXhwb3J0IGJ1dHRvbi5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIHdyaXRlVG9DbGlwYm9hcmQodGV4dDogc3RyaW5nLCBidG46IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gIGlmICghbmF2aWdhdG9yLmNsaXBib2FyZCkge1xuICAgIGZhbGxiYWNrQ29weSh0ZXh0LCBidG4pO1xuICAgIHJldHVybjtcbiAgfVxuICBuYXZpZ2F0b3IuY2xpcGJvYXJkLndyaXRlVGV4dCh0ZXh0KS50aGVuKGZ1bmN0aW9uICgpIHtcbiAgICBzaG93Q29waWVkRmVlZGJhY2soYnRuKTtcbiAgfSkuY2F0Y2goZnVuY3Rpb24gKCkge1xuICAgIGZhbGxiYWNrQ29weSh0ZXh0LCBidG4pO1xuICB9KTtcbn1cblxuLyoqXG4gKiBBdHRhY2ggY2xpY2sgaGFuZGxlcnMgdG8gYWxsIC5jb3B5LWJ0biBlbGVtZW50cyBwcmVzZW50IGluIHRoZSBET00uXG4gKiBFYWNoIGJ1dHRvbiByZWFkcyBkYXRhLXZhbHVlIChJT0MpIGFuZCBvcHRpb25hbGx5IGRhdGEtZW5yaWNobWVudCAod29yc3QgdmVyZGljdCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBjb25zdCBjb3B5QnV0dG9ucyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmNvcHktYnRuXCIpO1xuXG4gIGNvcHlCdXR0b25zLmZvckVhY2goZnVuY3Rpb24gKGJ0bikge1xuICAgIGJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgICAgY29uc3QgdmFsdWUgPSBhdHRyKGJ0biwgXCJkYXRhLXZhbHVlXCIpO1xuICAgICAgaWYgKCF2YWx1ZSkgcmV0dXJuO1xuXG4gICAgICAvLyBDaGVjayBmb3IgZW5yaWNobWVudCBzdW1tYXJ5IHNldCBieSBwb2xsaW5nIGxvb3AgKHdvcnN0IHZlcmRpY3QpXG4gICAgICBjb25zdCBlbnJpY2htZW50ID0gYXR0cihidG4sIFwiZGF0YS1lbnJpY2htZW50XCIpO1xuICAgICAgLy8gYXR0cigpIHJldHVybnMgXCJcIiB3aGVuIGF0dHJpYnV0ZSBpcyBhYnNlbnQgKGZhbHN5KSBcdTIwMTQgc2FtZSB0ZXJuYXJ5IGFzIG9yaWdpbmFsXG4gICAgICBjb25zdCBjb3B5VGV4dCA9IGVucmljaG1lbnQgPyAodmFsdWUgKyBcIiB8IFwiICsgZW5yaWNobWVudCkgOiB2YWx1ZTtcblxuICAgICAgd3JpdGVUb0NsaXBib2FyZChjb3B5VGV4dCwgYnRuKTtcbiAgICB9KTtcbiAgfSk7XG59XG4iLCAiLyoqXG4gKiBEb21haW4gdHlwZXMgYW5kIGNvbnN0YW50cyBmb3IgSU9DIChJbmRpY2F0b3Igb2YgQ29tcHJvbWlzZSkgZW5yaWNobWVudC5cbiAqXG4gKiBUaGlzIG1vZHVsZSBkZWZpbmVzIHRoZSBzaGFyZWQgdHlwZSBsYXllciBmb3IgdmVyZGljdCB2YWx1ZXMgYW5kIElPQyBtZXRhZGF0YS5cbiAqIEFsbCBjb25zdGFudHMgYXJlIHNvdXJjZWQgZnJvbSBhcHAvc3RhdGljL21haW4uanMgYW5kIG11c3QgcmVtYWluIGluIHN5bmNcbiAqIHdpdGggdGhlIEZsYXNrIGJhY2tlbmQgdmVyZGljdCB2YWx1ZXMuXG4gKlxuICogU2hhcmVkIHR5cGUgZGVmaW5pdGlvbnMsIHR5cGVkIGNvbnN0YW50cywgYW5kIHZlcmRpY3QgdXRpbGl0eSBmdW5jdGlvbnMuXG4gKi9cblxuLyoqXG4gKiBUaGUgdmVyZGljdCBrZXlzIHJldHVybmVkIGJ5IHRoZSBGbGFzayBlbnJpY2htZW50IEFQSS5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgVkVSRElDVF9MQUJFTFMga2V5cyAobGluZXMgMjMxXHUyMDEzMjM3KS5cbiAqIFVzZWQgYXMgZGlzY3JpbWluYW50IHZhbHVlcyB0aHJvdWdob3V0IGVucmljaG1lbnQgcmVzdWx0IHByb2Nlc3NpbmcuXG4gKlxuICogTm90ZToga25vd25fZ29vZCBpcyBpbnRlbnRpb25hbGx5IGV4Y2x1ZGVkIGZyb20gVkVSRElDVF9TRVZFUklUWSBcdTIwMTQgaXQgaXNcbiAqIG5vdCBhIHNldmVyaXR5IGxldmVsIGJ1dCBhIGNsYXNzaWZpY2F0aW9uIG92ZXJyaWRlLiB2ZXJkaWN0U2V2ZXJpdHlJbmRleCgpXG4gKiByZXR1cm5zIC0xIGZvciBrbm93bl9nb29kLCB3aGljaCBpcyBjb3JyZWN0IGFuZCBpbnRlbnRpb25hbC5cbiAqL1xuZXhwb3J0IHR5cGUgVmVyZGljdEtleSA9XG4gIHwgXCJlcnJvclwiXG4gIHwgXCJub19kYXRhXCJcbiAgfCBcImNsZWFuXCJcbiAgfCBcInN1c3BpY2lvdXNcIlxuICB8IFwibWFsaWNpb3VzXCJcbiAgfCBcImtub3duX2dvb2RcIjtcblxuLyoqXG4gKiBUaGUgc2V2ZW4gSU9DIHR5cGVzIHN1cHBvcnRlZCBmb3IgZW5yaWNobWVudC5cbiAqXG4gKiBPbmx5IGVucmljaGFibGUgdHlwZXMgYXJlIGluY2x1ZGVkIFx1MjAxNCBOT1QgXCJjdmVcIiAoQ1ZFcyBhcmUgZXh0cmFjdGVkIGJ1dFxuICogbmV2ZXIgZW5yaWNoZWQsIGFuZCBJT0NfUFJPVklERVJfQ09VTlRTIGhhcyBubyBcImN2ZVwiIGVudHJ5KS5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgSU9DX1BST1ZJREVSX0NPVU5UUyBrZXlzIChsaW5lcyAyNDJcdTIwMTMyNTApLlxuICovXG50eXBlIElvY1R5cGUgPVxuICB8IFwiaXB2NFwiXG4gIHwgXCJpcHY2XCJcbiAgfCBcImRvbWFpblwiXG4gIHwgXCJ1cmxcIlxuICB8IFwibWQ1XCJcbiAgfCBcInNoYTFcIlxuICB8IFwic2hhMjU2XCI7XG5cbi8qKlxuICogUmFua2VkIHNldmVyaXR5IHZlcmRpY3RzIFx1MjAxNCBpbmRleCAwIGlzIGxlYXN0IHNldmVyZSwgaW5kZXggNCBpcyBtb3N0IHNldmVyZS5cbiAqXG4gKiBrbm93bl9nb29kIGlzIGludGVudGlvbmFsbHkgZXhjbHVkZWQ6IGl0IGlzIGEgY2xhc3NpZmljYXRpb24gb3ZlcnJpZGUsIG5vdFxuICogYSBzZXZlcml0eSBsZXZlbC4gdmVyZGljdFNldmVyaXR5SW5kZXggcmV0dXJucyAtMSBmb3Iga25vd25fZ29vZCwgd2hpY2ggaXNcbiAqIHRoZSBjb3JyZWN0IGFuZCBleHBlY3RlZCBiZWhhdmlvciAoaXQgYWx3YXlzIHdpbnMgdmlhIGNvbXB1dGVXb3JzdFZlcmRpY3Qnc1xuICogZWFybHktcmV0dXJuIGNoZWNrLCBub3QgYnkgc2V2ZXJpdHkgcmFua2luZykuXG4gKlxuICogU291cmNlOiBtYWluLmpzIGxpbmUgMjI4LlxuICovXG50eXBlIFJhbmtlZFZlcmRpY3QgPSBcImVycm9yXCIgfCBcIm5vX2RhdGFcIiB8IFwiY2xlYW5cIiB8IFwic3VzcGljaW91c1wiIHwgXCJtYWxpY2lvdXNcIjtcblxuY29uc3QgVkVSRElDVF9TRVZFUklUWSA9IFtcbiAgXCJlcnJvclwiLFxuICBcIm5vX2RhdGFcIixcbiAgXCJjbGVhblwiLFxuICBcInN1c3BpY2lvdXNcIixcbiAgXCJtYWxpY2lvdXNcIixcbl0gYXMgY29uc3Qgc2F0aXNmaWVzIHJlYWRvbmx5IFJhbmtlZFZlcmRpY3RbXTtcblxuLyoqXG4gKiBSZXR1cm5zIHRoZSBzZXZlcml0eSBpbmRleCBmb3IgYSB2ZXJkaWN0IGtleS5cbiAqIEhpZ2hlciBpbmRleCA9IGhpZ2hlciBzZXZlcml0eS4gUmV0dXJucyAtMSBpZiBub3QgZm91bmQgKGUuZy4ga25vd25fZ29vZCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiB2ZXJkaWN0U2V2ZXJpdHlJbmRleCh2ZXJkaWN0OiBWZXJkaWN0S2V5KTogbnVtYmVyIHtcbiAgcmV0dXJuIChWRVJESUNUX1NFVkVSSVRZIGFzIHJlYWRvbmx5IHN0cmluZ1tdKS5pbmRleE9mKHZlcmRpY3QpO1xufVxuXG4vKipcbiAqIEh1bWFuLXJlYWRhYmxlIGRpc3BsYXkgbGFiZWxzIGZvciBlYWNoIHZlcmRpY3Qga2V5LlxuICpcbiAqIFR5cGVkIGFzIGBSZWNvcmQ8VmVyZGljdEtleSwgc3RyaW5nPmAgdG8gZW5zdXJlIGFsbCBmaXZlIGtleXMgYXJlIHByZXNlbnRcbiAqIGFuZCB0aGF0IGluZGV4aW5nIHdpdGggYW4gaW52YWxpZCBrZXkgcHJvZHVjZXMgYSBjb21waWxlIGVycm9yIHVuZGVyXG4gKiBgbm9VbmNoZWNrZWRJbmRleGVkQWNjZXNzYC5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgbGluZXMgMjMxXHUyMDEzMjM3LlxuICovXG5leHBvcnQgY29uc3QgVkVSRElDVF9MQUJFTFM6IFJlY29yZDxWZXJkaWN0S2V5LCBzdHJpbmc+ID0ge1xuICBtYWxpY2lvdXM6IFwiTUFMSUNJT1VTXCIsXG4gIHN1c3BpY2lvdXM6IFwiU1VTUElDSU9VU1wiLFxuICBjbGVhbjogXCJDTEVBTlwiLFxuICBrbm93bl9nb29kOiBcIktOT1dOIEdPT0RcIixcbiAgbm9fZGF0YTogXCJOTyBEQVRBXCIsXG4gIGVycm9yOiBcIkVSUk9SXCIsXG59IGFzIGNvbnN0O1xuXG4vKipcbiAqIEhhcmRjb2RlZCBmYWxsYmFjayBwcm92aWRlciBjb3VudHMgcGVyIGVucmljaGFibGUgSU9DIHR5cGUuXG4gKlxuICogVXNlZCBhcyBhIGZhbGxiYWNrIHdoZW4gdGhlIGRhdGEtcHJvdmlkZXItY291bnRzIERPTSBhdHRyaWJ1dGUgaXMgYWJzZW50XG4gKiAob2ZmbGluZSBtb2RlIG9yIHNlcnZlciBlcnJvcikuIFJlZmxlY3RzIHRoZSBiYXNlbGluZSAzLXByb3ZpZGVyIHNldHVwOlxuICogVmlydXNUb3RhbCBzdXBwb3J0cyBhbGwgNyB0eXBlcywgTWFsd2FyZUJhemFhciBzdXBwb3J0cyBtZDUvc2hhMS9zaGEyNTYsXG4gKiBUaHJlYXRGb3ggc3VwcG9ydHMgYWxsIDcuXG4gKlxuICogUHJpdmF0ZSBcdTIwMTQgY2FsbGVycyBtdXN0IHVzZSBnZXRQcm92aWRlckNvdW50cygpIHRvIGFsbG93IHJ1bnRpbWUgb3ZlcnJpZGVcbiAqIGZyb20gdGhlIERPTSBhdHRyaWJ1dGUgcG9wdWxhdGVkIGJ5IHRoZSBGbGFzayByb3V0ZS5cbiAqL1xuY29uc3QgX2RlZmF1bHRQcm92aWRlckNvdW50czogUmVjb3JkPElvY1R5cGUsIG51bWJlcj4gPSB7XG4gIGlwdjQ6IDIsXG4gIGlwdjY6IDIsXG4gIGRvbWFpbjogMixcbiAgdXJsOiAyLFxuICBtZDU6IDMsXG4gIHNoYTE6IDMsXG4gIHNoYTI1NjogMyxcbn0gYXMgY29uc3Q7XG5cbi8qKlxuICogUmV0dXJuIHByb3ZpZGVyIGNvdW50cyBwZXIgSU9DIHR5cGUsIHJlYWRpbmcgZnJvbSB0aGUgRE9NIHdoZW4gYXZhaWxhYmxlLlxuICpcbiAqIE9uIHRoZSByZXN1bHRzIHBhZ2UgaW4gb25saW5lIG1vZGUsIEZsYXNrIGluamVjdHMgdGhlIGFjdHVhbCByZWdpc3RyeSBjb3VudHNcbiAqIHZpYSBkYXRhLXByb3ZpZGVyLWNvdW50cyBvbiAucGFnZS1yZXN1bHRzLiBUaGlzIGZ1bmN0aW9uIHJlYWRzIHRoYXQgYXR0cmlidXRlXG4gKiBzbyB0aGUgcGVuZGluZy1pbmRpY2F0b3IgbG9naWMgcmVmbGVjdHMgdGhlIHJlYWwgY29uZmlndXJlZCBwcm92aWRlciBzZXRcbiAqIChlLmcuLCA4KyBwcm92aWRlcnMgaW4gdjQuMCkgcmF0aGVyIHRoYW4gYSBzdGFsZSBoYXJkY29kZWQgdmFsdWUuXG4gKlxuICogRmFsbHMgYmFjayB0byBfZGVmYXVsdFByb3ZpZGVyQ291bnRzIHdoZW46XG4gKiAgIC0gLnBhZ2UtcmVzdWx0cyBlbGVtZW50IGlzIGFic2VudCAobm90IG9uIHJlc3VsdHMgcGFnZSlcbiAqICAgLSBkYXRhLXByb3ZpZGVyLWNvdW50cyBhdHRyaWJ1dGUgaXMgbWlzc2luZyAob2ZmbGluZSBtb2RlKVxuICogICAtIEpTT04gcGFyc2UgZmFpbHMgKG1hbGZvcm1lZCBhdHRyaWJ1dGUpXG4gKlxuICogUmV0dXJuczpcbiAqICAgUmVjb3JkIG1hcHBpbmcgSU9DIHR5cGUgc3RyaW5nIFx1MjE5MiBjb25maWd1cmVkIHByb3ZpZGVyIGNvdW50LlxuICovXG5leHBvcnQgZnVuY3Rpb24gZ2V0UHJvdmlkZXJDb3VudHMoKTogUmVjb3JkPHN0cmluZywgbnVtYmVyPiB7XG4gIGNvbnN0IGVsID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIucGFnZS1yZXN1bHRzXCIpO1xuICBpZiAoZWwgPT09IG51bGwpIHJldHVybiBfZGVmYXVsdFByb3ZpZGVyQ291bnRzO1xuICBjb25zdCByYXcgPSBlbC5nZXRBdHRyaWJ1dGUoXCJkYXRhLXByb3ZpZGVyLWNvdW50c1wiKTtcbiAgaWYgKHJhdyA9PT0gbnVsbCkgcmV0dXJuIF9kZWZhdWx0UHJvdmlkZXJDb3VudHM7XG4gIHRyeSB7XG4gICAgcmV0dXJuIEpTT04ucGFyc2UocmF3KSBhcyBSZWNvcmQ8c3RyaW5nLCBudW1iZXI+O1xuICB9IGNhdGNoIHtcbiAgICByZXR1cm4gX2RlZmF1bHRQcm92aWRlckNvdW50cztcbiAgfVxufVxuIiwgIi8qKlxuICogQ2FyZCBtYW5hZ2VtZW50IG1vZHVsZSBcdTIwMTQgdmVyZGljdCB1cGRhdGVzLCBkYXNoYm9hcmQgY291bnRzLCBzZXZlcml0eSBzb3J0aW5nLlxuICpcbiAqIEV4dHJhY3RlZCBmcm9tIG1haW4uanMgbGluZXMgMjUyLTMzNi5cbiAqIFByb3ZpZGVzIHRoZSBwdWJsaWMgQVBJIGNvbnN1bWVkIGJ5IFBoYXNlIDIyJ3MgZW5yaWNobWVudCBtb2R1bGUuXG4gKi9cblxuaW1wb3J0IHR5cGUgeyBWZXJkaWN0S2V5IH0gZnJvbSBcIi4uL3R5cGVzL2lvY1wiO1xuaW1wb3J0IHsgVkVSRElDVF9MQUJFTFMsIHZlcmRpY3RTZXZlcml0eUluZGV4IH0gZnJvbSBcIi4uL3R5cGVzL2lvY1wiO1xuaW1wb3J0IHsgYXR0ciB9IGZyb20gXCIuLi91dGlscy9kb21cIjtcblxuLyoqXG4gKiBNb2R1bGUtbGV2ZWwgZGVib3VuY2UgdGltZXIgZm9yIHNvcnRDYXJkc0J5U2V2ZXJpdHkuXG4gKiBVc2VzIFJldHVyblR5cGU8dHlwZW9mIHNldFRpbWVvdXQ+IHRvIGF2b2lkIE5vZGVKUy5UaW1lb3V0IGNvbmZsaWN0LlxuICovXG5sZXQgc29ydFRpbWVyOiBSZXR1cm5UeXBlPHR5cGVvZiBzZXRUaW1lb3V0PiB8IG51bGwgPSBudWxsO1xuXG4vKipcbiAqIEluaXRpYWxpc2UgdGhlIGNhcmRzIG1vZHVsZS5cbiAqIENhcmRzIGhhdmUgbm8gRE9NQ29udGVudExvYWRlZCBzZXR1cCBcdTIwMTQgdGhlaXIgZnVuY3Rpb25zIGFyZSBjYWxsZWQgYnkgdGhlXG4gKiBlbnJpY2htZW50IG1vZHVsZS4gRXhwb3J0ZWQgZm9yIGNvbnNpc3RlbmN5IHdpdGggdGhlIG1vZHVsZSBwYXR0ZXJuO1xuICogbWFpbi50cyB3aWxsIGNhbGwgaXQgaW4gUGhhc2UgMjIuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICAvLyBOby1vcCBmb3IgUGhhc2UgMjEgXHUyMDE0IGNhcmRzIG1vZHVsZSBoYXMgbm8gRE9NQ29udGVudExvYWRlZCB3aXJpbmcuXG4gIC8vIENhbGxlZCBieSBtYWluLnRzIGZvciBjb25zaXN0ZW50IG1vZHVsZSBpbml0aWFsaXNhdGlvbi5cbn1cblxuLyoqXG4gKiBGaW5kIHRoZSBJT0MgY2FyZCBlbGVtZW50IGZvciBhIGdpdmVuIElPQyB2YWx1ZSB1c2luZyBDU1MuZXNjYXBlLlxuICogUmV0dXJucyBudWxsIGlmIG5vIG1hdGNoaW5nIGNhcmQgaXMgZm91bmQuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBmaW5kQ2FyZEZvcklvYyhpb2NWYWx1ZTogc3RyaW5nKTogSFRNTEVsZW1lbnQgfCBudWxsIHtcbiAgcmV0dXJuIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFxuICAgICcuaW9jLWNhcmRbZGF0YS1pb2MtdmFsdWU9XCInICsgQ1NTLmVzY2FwZShpb2NWYWx1ZSkgKyAnXCJdJ1xuICApO1xufVxuXG4vKipcbiAqIFVwZGF0ZSBhIGNhcmQncyB2ZXJkaWN0OiBzZXRzIGRhdGEtdmVyZGljdCBhdHRyaWJ1dGUsIHZlcmRpY3QgbGFiZWwgdGV4dCxcbiAqIGFuZCB2ZXJkaWN0IGxhYmVsIENTUyBjbGFzcy5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIHVwZGF0ZUNhcmRWZXJkaWN0KFxuICBpb2NWYWx1ZTogc3RyaW5nLFxuICB3b3JzdFZlcmRpY3Q6IFZlcmRpY3RLZXlcbik6IHZvaWQge1xuICBjb25zdCBjYXJkID0gZmluZENhcmRGb3JJb2MoaW9jVmFsdWUpO1xuICBpZiAoIWNhcmQpIHJldHVybjtcblxuICAvLyBVcGRhdGUgZGF0YS12ZXJkaWN0IGF0dHJpYnV0ZSAoZHJpdmVzIENTUyBib3JkZXIgY29sb3VyKVxuICBjYXJkLnNldEF0dHJpYnV0ZShcImRhdGEtdmVyZGljdFwiLCB3b3JzdFZlcmRpY3QpO1xuXG4gIC8vIFVwZGF0ZSB2ZXJkaWN0IGxhYmVsIHRleHQgYW5kIGNsYXNzXG4gIGNvbnN0IGxhYmVsID0gY2FyZC5xdWVyeVNlbGVjdG9yKFwiLnZlcmRpY3QtbGFiZWxcIik7XG4gIGlmIChsYWJlbCkge1xuICAgIC8vIFJlbW92ZSBhbGwgdmVyZGljdC1sYWJlbC0tKiBjbGFzc2VzLCB0aGVuIGFkZCB0aGUgY29ycmVjdCBvbmVcbiAgICBjb25zdCBjbGFzc2VzID0gbGFiZWwuY2xhc3NOYW1lXG4gICAgICAuc3BsaXQoXCIgXCIpXG4gICAgICAuZmlsdGVyKChjKSA9PiAhYy5zdGFydHNXaXRoKFwidmVyZGljdC1sYWJlbC0tXCIpKTtcbiAgICBjbGFzc2VzLnB1c2goXCJ2ZXJkaWN0LWxhYmVsLS1cIiArIHdvcnN0VmVyZGljdCk7XG4gICAgbGFiZWwuY2xhc3NOYW1lID0gY2xhc3Nlcy5qb2luKFwiIFwiKTtcbiAgICBsYWJlbC50ZXh0Q29udGVudCA9IFZFUkRJQ1RfTEFCRUxTW3dvcnN0VmVyZGljdF0gfHwgd29yc3RWZXJkaWN0LnRvVXBwZXJDYXNlKCk7XG4gIH1cbn1cblxuLyoqXG4gKiBDb3VudCBjYXJkcyBieSB2ZXJkaWN0IGFuZCB1cGRhdGUgZGFzaGJvYXJkIGNvdW50IGVsZW1lbnRzLlxuICovXG5leHBvcnQgZnVuY3Rpb24gdXBkYXRlRGFzaGJvYXJkQ291bnRzKCk6IHZvaWQge1xuICBjb25zdCBkYXNoYm9hcmQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInZlcmRpY3QtZGFzaGJvYXJkXCIpO1xuICBpZiAoIWRhc2hib2FyZCkgcmV0dXJuO1xuXG4gIGNvbnN0IGNhcmRzID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuaW9jLWNhcmRcIik7XG4gIGNvbnN0IGNvdW50czogUmVjb3JkPHN0cmluZywgbnVtYmVyPiA9IHtcbiAgICBtYWxpY2lvdXM6IDAsXG4gICAgc3VzcGljaW91czogMCxcbiAgICBjbGVhbjogMCxcbiAgICBrbm93bl9nb29kOiAwLFxuICAgIG5vX2RhdGE6IDAsXG4gIH07XG5cbiAgY2FyZHMuZm9yRWFjaCgoY2FyZCkgPT4ge1xuICAgIGNvbnN0IHYgPSBhdHRyKGNhcmQsIFwiZGF0YS12ZXJkaWN0XCIpO1xuICAgIGlmIChPYmplY3QucHJvdG90eXBlLmhhc093blByb3BlcnR5LmNhbGwoY291bnRzLCB2KSkge1xuICAgICAgY291bnRzW3ZdID0gKGNvdW50c1t2XSA/PyAwKSArIDE7XG4gICAgfVxuICB9KTtcblxuICBjb25zdCB2ZXJkaWN0cyA9IFtcIm1hbGljaW91c1wiLCBcInN1c3BpY2lvdXNcIiwgXCJjbGVhblwiLCBcImtub3duX2dvb2RcIiwgXCJub19kYXRhXCJdO1xuICB2ZXJkaWN0cy5mb3JFYWNoKCh2ZXJkaWN0KSA9PiB7XG4gICAgY29uc3QgY291bnRFbCA9IGRhc2hib2FyZC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcbiAgICAgICdbZGF0YS12ZXJkaWN0LWNvdW50PVwiJyArIHZlcmRpY3QgKyAnXCJdJ1xuICAgICk7XG4gICAgaWYgKGNvdW50RWwpIHtcbiAgICAgIGNvdW50RWwudGV4dENvbnRlbnQgPSBTdHJpbmcoY291bnRzW3ZlcmRpY3RdID8/IDApO1xuICAgIH1cbiAgfSk7XG59XG5cbi8qKlxuICogRGVib3VuY2VkIGVudHJ5IHBvaW50OiBzY2hlZHVsZXMgZG9Tb3J0Q2FyZHMgd2l0aCBhIDEwMCBtcyBkZWxheS5cbiAqIENhbGxpbmcgdGhpcyBtdWx0aXBsZSB0aW1lcyBpbiBxdWljayBzdWNjZXNzaW9uIG9ubHkgdHJpZ2dlcnMgb25lIHNvcnQuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBzb3J0Q2FyZHNCeVNldmVyaXR5KCk6IHZvaWQge1xuICBpZiAoc29ydFRpbWVyICE9PSBudWxsKSBjbGVhclRpbWVvdXQoc29ydFRpbWVyKTtcbiAgc29ydFRpbWVyID0gc2V0VGltZW91dChkb1NvcnRDYXJkcywgMTAwKTtcbn1cblxuLy8gLS0tLSBQcml2YXRlIGhlbHBlcnMgLS0tLVxuXG4vKipcbiAqIFJlb3JkZXJzIC5pb2MtY2FyZCBlbGVtZW50cyBpbiAjaW9jLWNhcmRzLWdyaWQgYnkgdmVyZGljdCBzZXZlcml0eSAobW9zdFxuICogc2V2ZXJlIGZpcnN0KS4gQ2FsbGVkIGJ5IHNvcnRDYXJkc0J5U2V2ZXJpdHkgdmlhIHNldFRpbWVvdXQgZGVib3VuY2UuXG4gKi9cbmZ1bmN0aW9uIGRvU29ydENhcmRzKCk6IHZvaWQge1xuICBjb25zdCBncmlkID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJpb2MtY2FyZHMtZ3JpZFwiKTtcbiAgaWYgKCFncmlkKSByZXR1cm47XG5cbiAgY29uc3QgY2FyZHMgPSBBcnJheS5mcm9tKGdyaWQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuaW9jLWNhcmRcIikpO1xuICBpZiAoY2FyZHMubGVuZ3RoID09PSAwKSByZXR1cm47XG5cbiAgY2FyZHMuc29ydCgoYSwgYikgPT4ge1xuICAgIGNvbnN0IHZhID0gdmVyZGljdFNldmVyaXR5SW5kZXgoXG4gICAgICBhdHRyKGEsIFwiZGF0YS12ZXJkaWN0XCIsIFwibm9fZGF0YVwiKSBhcyBWZXJkaWN0S2V5XG4gICAgKTtcbiAgICBjb25zdCB2YiA9IHZlcmRpY3RTZXZlcml0eUluZGV4KFxuICAgICAgYXR0cihiLCBcImRhdGEtdmVyZGljdFwiLCBcIm5vX2RhdGFcIikgYXMgVmVyZGljdEtleVxuICAgICk7XG4gICAgLy8gSGlnaGVyIHNldmVyaXR5IGZpcnN0IChkZXNjZW5kaW5nKVxuICAgIHJldHVybiB2YiAtIHZhO1xuICB9KTtcblxuICAvLyBSZW9yZGVyIERPTSBlbGVtZW50cyB3aXRob3V0IHJlbW92aW5nIHRoZW0gZnJvbSB0aGUgZG9jdW1lbnRcbiAgY2FyZHMuZm9yRWFjaCgoY2FyZCkgPT4gZ3JpZC5hcHBlbmRDaGlsZChjYXJkKSk7XG59XG4iLCAiLyoqXG4gKiBGaWx0ZXIgYmFyIG1vZHVsZSBcdTIwMTQgdmVyZGljdC90eXBlL3NlYXJjaCBmaWx0ZXJpbmcgd2l0aCBkYXNoYm9hcmQgYmFkZ2Ugc3luYy5cbiAqXG4gKiBFeHRyYWN0ZWQgZnJvbSBtYWluLmpzIGluaXRGaWx0ZXJCYXIoKSAobGluZXMgNjc3LTc4OCkuXG4gKiBNYW5hZ2VzIGZpbHRlclN0YXRlIGFuZCB3aXJlcyB1cCBhbGwgZmlsdGVyIGV2ZW50IGxpc3RlbmVycy5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vKipcbiAqIEludGVybmFsIHN0YXRlIGZvciBhbGwgYWN0aXZlIGZpbHRlciBkaW1lbnNpb25zLlxuICogTm90IGV4cG9ydGVkIFx1MjAxNCB0aGlzIGlzIHByaXZhdGUgdG8gdGhlIG1vZHVsZSBjbG9zdXJlIGluc2lkZSBpbml0KCkuXG4gKi9cbmludGVyZmFjZSBGaWx0ZXJTdGF0ZSB7XG4gIHZlcmRpY3Q6IHN0cmluZztcbiAgdHlwZTogc3RyaW5nO1xuICBzZWFyY2g6IHN0cmluZztcbn1cblxuLyoqXG4gKiBJbml0aWFsaXNlIHRoZSBmaWx0ZXIgYmFyLlxuICogV2lyZXMgdmVyZGljdCBidXR0b25zLCB0eXBlIHBpbGxzLCBzZWFyY2ggaW5wdXQsIGFuZCBkYXNoYm9hcmQgYmFkZ2UgY2xpY2tzLlxuICogQWxsIGV2ZW50IGxpc3RlbmVycyBzaGFyZSB0aGUgZmlsdGVyU3RhdGUgY2xvc3VyZS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGluaXQoKTogdm9pZCB7XG4gIGNvbnN0IGZpbHRlclJvb3RFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZmlsdGVyLXJvb3RcIik7XG4gIGlmICghZmlsdGVyUm9vdEVsKSByZXR1cm47IC8vIE5vdCBvbiByZXN1bHRzIHBhZ2VcbiAgY29uc3QgZmlsdGVyUm9vdDogSFRNTEVsZW1lbnQgPSBmaWx0ZXJSb290RWw7XG5cbiAgY29uc3QgZmlsdGVyU3RhdGU6IEZpbHRlclN0YXRlID0ge1xuICAgIHZlcmRpY3Q6IFwiYWxsXCIsXG4gICAgdHlwZTogXCJhbGxcIixcbiAgICBzZWFyY2g6IFwiXCIsXG4gIH07XG5cbiAgLy8gQXBwbHkgZmlsdGVyIHN0YXRlOiBzaG93L2hpZGUgZWFjaCBjYXJkIGFuZCB1cGRhdGUgYWN0aXZlIGJ1dHRvbiBzdHlsZXNcbiAgZnVuY3Rpb24gYXBwbHlGaWx0ZXIoKTogdm9pZCB7XG4gICAgY29uc3QgY2FyZHMgPSBmaWx0ZXJSb290LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmlvYy1jYXJkXCIpO1xuICAgIGNvbnN0IHZlcmRpY3RMQyA9IGZpbHRlclN0YXRlLnZlcmRpY3QudG9Mb3dlckNhc2UoKTtcbiAgICBjb25zdCB0eXBlTEMgPSBmaWx0ZXJTdGF0ZS50eXBlLnRvTG93ZXJDYXNlKCk7XG4gICAgY29uc3Qgc2VhcmNoTEMgPSBmaWx0ZXJTdGF0ZS5zZWFyY2gudG9Mb3dlckNhc2UoKTtcblxuICAgIGNhcmRzLmZvckVhY2goKGNhcmQpID0+IHtcbiAgICAgIGNvbnN0IGNhcmRWZXJkaWN0ID0gYXR0cihjYXJkLCBcImRhdGEtdmVyZGljdFwiKS50b0xvd2VyQ2FzZSgpO1xuICAgICAgY29uc3QgY2FyZFR5cGUgPSBhdHRyKGNhcmQsIFwiZGF0YS1pb2MtdHlwZVwiKS50b0xvd2VyQ2FzZSgpO1xuICAgICAgY29uc3QgY2FyZFZhbHVlID0gYXR0cihjYXJkLCBcImRhdGEtaW9jLXZhbHVlXCIpLnRvTG93ZXJDYXNlKCk7XG5cbiAgICAgIGNvbnN0IHZlcmRpY3RNYXRjaCA9IHZlcmRpY3RMQyA9PT0gXCJhbGxcIiB8fCBjYXJkVmVyZGljdCA9PT0gdmVyZGljdExDO1xuICAgICAgY29uc3QgdHlwZU1hdGNoID0gdHlwZUxDID09PSBcImFsbFwiIHx8IGNhcmRUeXBlID09PSB0eXBlTEM7XG4gICAgICBjb25zdCBzZWFyY2hNYXRjaCA9IHNlYXJjaExDID09PSBcIlwiIHx8IGNhcmRWYWx1ZS5pbmRleE9mKHNlYXJjaExDKSAhPT0gLTE7XG5cbiAgICAgIGNhcmQuc3R5bGUuZGlzcGxheSA9XG4gICAgICAgIHZlcmRpY3RNYXRjaCAmJiB0eXBlTWF0Y2ggJiYgc2VhcmNoTWF0Y2ggPyBcIlwiIDogXCJub25lXCI7XG4gICAgfSk7XG5cbiAgICAvLyBVcGRhdGUgYWN0aXZlIHN0YXRlIG9uIHZlcmRpY3QgYnV0dG9uc1xuICAgIGNvbnN0IHZlcmRpY3RCdG5zID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICAgIFwiW2RhdGEtZmlsdGVyLXZlcmRpY3RdXCJcbiAgICApO1xuICAgIHZlcmRpY3RCdG5zLmZvckVhY2goKGJ0bikgPT4ge1xuICAgICAgY29uc3QgYnRuVmVyZGljdCA9IGF0dHIoYnRuLCBcImRhdGEtZmlsdGVyLXZlcmRpY3RcIik7XG4gICAgICBpZiAoYnRuVmVyZGljdCA9PT0gZmlsdGVyU3RhdGUudmVyZGljdCkge1xuICAgICAgICBidG4uY2xhc3NMaXN0LmFkZChcImZpbHRlci1idG4tLWFjdGl2ZVwiKTtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIGJ0bi5jbGFzc0xpc3QucmVtb3ZlKFwiZmlsdGVyLWJ0bi0tYWN0aXZlXCIpO1xuICAgICAgfVxuICAgIH0pO1xuXG4gICAgLy8gVXBkYXRlIGFjdGl2ZSBzdGF0ZSBvbiB0eXBlIHBpbGxzXG4gICAgY29uc3QgdHlwZVBpbGxzID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICAgIFwiW2RhdGEtZmlsdGVyLXR5cGVdXCJcbiAgICApO1xuICAgIHR5cGVQaWxscy5mb3JFYWNoKChwaWxsKSA9PiB7XG4gICAgICBjb25zdCBwaWxsVHlwZSA9IGF0dHIocGlsbCwgXCJkYXRhLWZpbHRlci10eXBlXCIpO1xuICAgICAgaWYgKHBpbGxUeXBlID09PSBmaWx0ZXJTdGF0ZS50eXBlKSB7XG4gICAgICAgIHBpbGwuY2xhc3NMaXN0LmFkZChcImZpbHRlci1waWxsLS1hY3RpdmVcIik7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwaWxsLmNsYXNzTGlzdC5yZW1vdmUoXCJmaWx0ZXItcGlsbC0tYWN0aXZlXCIpO1xuICAgICAgfVxuICAgIH0pO1xuICB9XG5cbiAgLy8gVmVyZGljdCBidXR0b24gY2xpY2sgaGFuZGxlclxuICBjb25zdCB2ZXJkaWN0QnRucyA9IGZpbHRlclJvb3QucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXG4gICAgXCJbZGF0YS1maWx0ZXItdmVyZGljdF1cIlxuICApO1xuICB2ZXJkaWN0QnRucy5mb3JFYWNoKChidG4pID0+IHtcbiAgICBidG4uYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgIGNvbnN0IHZlcmRpY3QgPSBhdHRyKGJ0biwgXCJkYXRhLWZpbHRlci12ZXJkaWN0XCIpO1xuICAgICAgaWYgKHZlcmRpY3QgPT09IFwiYWxsXCIpIHtcbiAgICAgICAgZmlsdGVyU3RhdGUudmVyZGljdCA9IFwiYWxsXCI7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICAvLyBUb2dnbGU6IGNsaWNraW5nIGFjdGl2ZSB2ZXJkaWN0IHJlc2V0cyB0byAnYWxsJ1xuICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID0gZmlsdGVyU3RhdGUudmVyZGljdCA9PT0gdmVyZGljdCA/IFwiYWxsXCIgOiB2ZXJkaWN0O1xuICAgICAgfVxuICAgICAgYXBwbHlGaWx0ZXIoKTtcbiAgICB9KTtcbiAgfSk7XG5cbiAgLy8gVHlwZSBwaWxsIGNsaWNrIGhhbmRsZXJcbiAgY29uc3QgdHlwZVBpbGxzID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICBcIltkYXRhLWZpbHRlci10eXBlXVwiXG4gICk7XG4gIHR5cGVQaWxscy5mb3JFYWNoKChwaWxsKSA9PiB7XG4gICAgcGlsbC5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgKCkgPT4ge1xuICAgICAgY29uc3QgdHlwZSA9IGF0dHIocGlsbCwgXCJkYXRhLWZpbHRlci10eXBlXCIpO1xuICAgICAgaWYgKHR5cGUgPT09IFwiYWxsXCIpIHtcbiAgICAgICAgZmlsdGVyU3RhdGUudHlwZSA9IFwiYWxsXCI7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBmaWx0ZXJTdGF0ZS50eXBlID0gZmlsdGVyU3RhdGUudHlwZSA9PT0gdHlwZSA/IFwiYWxsXCIgOiB0eXBlO1xuICAgICAgfVxuICAgICAgYXBwbHlGaWx0ZXIoKTtcbiAgICB9KTtcbiAgfSk7XG5cbiAgLy8gU2VhcmNoIGlucHV0IGhhbmRsZXJcbiAgY29uc3Qgc2VhcmNoSW5wdXQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcbiAgICBcImZpbHRlci1zZWFyY2gtaW5wdXRcIlxuICApIGFzIEhUTUxJbnB1dEVsZW1lbnQgfCBudWxsO1xuICBpZiAoc2VhcmNoSW5wdXQpIHtcbiAgICBzZWFyY2hJbnB1dC5hZGRFdmVudExpc3RlbmVyKFwiaW5wdXRcIiwgKCkgPT4ge1xuICAgICAgZmlsdGVyU3RhdGUuc2VhcmNoID0gc2VhcmNoSW5wdXQudmFsdWU7XG4gICAgICBhcHBseUZpbHRlcigpO1xuICAgIH0pO1xuICB9XG5cbiAgLy8gVmVyZGljdCBkYXNoYm9hcmQgYmFkZ2UgY2xpY2sgaGFuZGxlciAodG9nZ2xlIGZpbHRlciBmcm9tIGRhc2hib2FyZClcbiAgY29uc3QgZGFzaGJvYXJkID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJ2ZXJkaWN0LWRhc2hib2FyZFwiKTtcbiAgaWYgKGRhc2hib2FyZCkge1xuICAgIGNvbnN0IGRhc2hCYWRnZXMgPSBkYXNoYm9hcmQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXG4gICAgICBcIi52ZXJkaWN0LWtwaS1jYXJkW2RhdGEtdmVyZGljdF1cIlxuICAgICk7XG4gICAgZGFzaEJhZGdlcy5mb3JFYWNoKChiYWRnZSkgPT4ge1xuICAgICAgYmFkZ2UuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgICAgY29uc3QgdmVyZGljdCA9IGF0dHIoYmFkZ2UsIFwiZGF0YS12ZXJkaWN0XCIpO1xuICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID1cbiAgICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID09PSB2ZXJkaWN0ID8gXCJhbGxcIiA6IHZlcmRpY3Q7XG4gICAgICAgIGFwcGx5RmlsdGVyKCk7XG4gICAgICB9KTtcbiAgICB9KTtcbiAgfVxuXG59XG4iLCAiLyoqXG4gKiBFeHBvcnQgbW9kdWxlIC0tIEpTT04gZG93bmxvYWQsIENTViBkb3dubG9hZCwgYW5kIGNvcHktYWxsLUlPQ3MuXG4gKlxuICogQWxsIGV4cG9ydHMgb3BlcmF0ZSBvbiB0aGUgYWNjdW11bGF0ZWQgcmVzdWx0cyBhcnJheSBidWlsdCBkdXJpbmdcbiAqIHRoZSBlbnJpY2htZW50IHBvbGxpbmcgbG9vcC4gTm8gc2VydmVyIHJvdW5kdHJpcCByZXF1aXJlZC5cbiAqL1xuXG5pbXBvcnQgdHlwZSB7IEVucmljaG1lbnRJdGVtIH0gZnJvbSBcIi4uL3R5cGVzL2FwaVwiO1xuaW1wb3J0IHsgd3JpdGVUb0NsaXBib2FyZCB9IGZyb20gXCIuL2NsaXBib2FyZFwiO1xuXG4vLyAtLS0tIEhlbHBlcnMgLS0tLVxuXG5mdW5jdGlvbiBkb3dubG9hZEJsb2IoYmxvYjogQmxvYiwgZmlsZW5hbWU6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCB1cmwgPSBVUkwuY3JlYXRlT2JqZWN0VVJMKGJsb2IpO1xuICBjb25zdCBhbmNob3IgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiYVwiKTtcbiAgYW5jaG9yLmhyZWYgPSB1cmw7XG4gIGFuY2hvci5kb3dubG9hZCA9IGZpbGVuYW1lO1xuICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKGFuY2hvcik7XG4gIGFuY2hvci5jbGljaygpO1xuICBkb2N1bWVudC5ib2R5LnJlbW92ZUNoaWxkKGFuY2hvcik7XG4gIFVSTC5yZXZva2VPYmplY3RVUkwodXJsKTtcbn1cblxuZnVuY3Rpb24gdGltZXN0YW1wKCk6IHN0cmluZyB7XG4gIHJldHVybiBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCkucmVwbGFjZSgvWzouXS9nLCBcIi1cIikuc2xpY2UoMCwgMTkpO1xufVxuXG5mdW5jdGlvbiBjc3ZFc2NhcGUodmFsdWU6IHN0cmluZyk6IHN0cmluZyB7XG4gIGlmICh2YWx1ZS5pbmRleE9mKFwiLFwiKSAhPT0gLTEgfHwgdmFsdWUuaW5kZXhPZignXCInKSAhPT0gLTEgfHwgdmFsdWUuaW5kZXhPZihcIlxcblwiKSAhPT0gLTEpIHtcbiAgICByZXR1cm4gJ1wiJyArIHZhbHVlLnJlcGxhY2UoL1wiL2csICdcIlwiJykgKyAnXCInO1xuICB9XG4gIHJldHVybiB2YWx1ZTtcbn1cblxuZnVuY3Rpb24gcmF3U3RhdEZpZWxkKHJhdzogUmVjb3JkPHN0cmluZywgdW5rbm93bj4gfCB1bmRlZmluZWQsIGtleTogc3RyaW5nKTogc3RyaW5nIHtcbiAgaWYgKCFyYXcpIHJldHVybiBcIlwiO1xuICBjb25zdCB2YWwgPSByYXdba2V5XTtcbiAgaWYgKHZhbCA9PT0gdW5kZWZpbmVkIHx8IHZhbCA9PT0gbnVsbCkgcmV0dXJuIFwiXCI7XG4gIGlmIChBcnJheS5pc0FycmF5KHZhbCkpIHJldHVybiB2YWwuam9pbihcIjsgXCIpO1xuICByZXR1cm4gU3RyaW5nKHZhbCk7XG59XG5cbi8vIC0tLS0gUHVibGljIEFQSSAtLS0tXG5cbmNvbnN0IENTVl9DT0xVTU5TID0gW1xuICBcImlvY192YWx1ZVwiLCBcImlvY190eXBlXCIsIFwicHJvdmlkZXJcIiwgXCJ2ZXJkaWN0XCIsXG4gIFwiZGV0ZWN0aW9uX2NvdW50XCIsIFwidG90YWxfZW5naW5lc1wiLCBcInNjYW5fZGF0ZVwiLFxuICBcInNpZ25hdHVyZVwiLCBcIm1hbHdhcmVfcHJpbnRhYmxlXCIsIFwidGhyZWF0X3R5cGVcIixcbiAgXCJjb3VudHJ5Q29kZVwiLCBcImlzcFwiLCBcInRvcF9kZXRlY3Rpb25zXCIsXG5dIGFzIGNvbnN0O1xuXG5leHBvcnQgZnVuY3Rpb24gZXhwb3J0SlNPTihyZXN1bHRzOiBFbnJpY2htZW50SXRlbVtdKTogdm9pZCB7XG4gIGNvbnN0IGpzb24gPSBKU09OLnN0cmluZ2lmeShyZXN1bHRzLCBudWxsLCAyKTtcbiAgY29uc3QgYmxvYiA9IG5ldyBCbG9iKFtqc29uXSwgeyB0eXBlOiBcImFwcGxpY2F0aW9uL2pzb25cIiB9KTtcbiAgZG93bmxvYWRCbG9iKGJsb2IsIFwic2VudGluZWx4LWV4cG9ydC1cIiArIHRpbWVzdGFtcCgpICsgXCIuanNvblwiKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGV4cG9ydENTVihyZXN1bHRzOiBFbnJpY2htZW50SXRlbVtdKTogdm9pZCB7XG4gIGNvbnN0IGhlYWRlciA9IENTVl9DT0xVTU5TLmpvaW4oXCIsXCIpICsgXCJcXG5cIjtcbiAgY29uc3Qgcm93czogc3RyaW5nW10gPSBbXTtcblxuICBmb3IgKGNvbnN0IHIgb2YgcmVzdWx0cykge1xuICAgIGlmIChyLnR5cGUgIT09IFwicmVzdWx0XCIpIGNvbnRpbnVlO1xuICAgIGNvbnN0IHJhdyA9IHIucmF3X3N0YXRzO1xuICAgIGNvbnN0IHJvdyA9IFtcbiAgICAgIGNzdkVzY2FwZShyLmlvY192YWx1ZSksXG4gICAgICBjc3ZFc2NhcGUoci5pb2NfdHlwZSksXG4gICAgICBjc3ZFc2NhcGUoci5wcm92aWRlciksXG4gICAgICBjc3ZFc2NhcGUoci52ZXJkaWN0KSxcbiAgICAgIFN0cmluZyhyLmRldGVjdGlvbl9jb3VudCksXG4gICAgICBTdHJpbmcoci50b3RhbF9lbmdpbmVzKSxcbiAgICAgIGNzdkVzY2FwZShyLnNjYW5fZGF0ZSA/PyBcIlwiKSxcbiAgICAgIGNzdkVzY2FwZShyYXdTdGF0RmllbGQocmF3LCBcInNpZ25hdHVyZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJtYWx3YXJlX3ByaW50YWJsZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJ0aHJlYXRfdHlwZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJjb3VudHJ5Q29kZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJpc3BcIikpLFxuICAgICAgY3N2RXNjYXBlKHJhd1N0YXRGaWVsZChyYXcsIFwidG9wX2RldGVjdGlvbnNcIikpLFxuICAgIF07XG4gICAgcm93cy5wdXNoKHJvdy5qb2luKFwiLFwiKSk7XG4gIH1cblxuICBjb25zdCBjc3YgPSBoZWFkZXIgKyByb3dzLmpvaW4oXCJcXG5cIik7XG4gIGNvbnN0IGJsb2IgPSBuZXcgQmxvYihbY3N2XSwgeyB0eXBlOiBcInRleHQvY3N2XCIgfSk7XG4gIGRvd25sb2FkQmxvYihibG9iLCBcInNlbnRpbmVseC1leHBvcnQtXCIgKyB0aW1lc3RhbXAoKSArIFwiLmNzdlwiKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGNvcHlBbGxJT0NzKGJ0bjogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgY29uc3QgY2FyZHMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcIi5pb2MtY2FyZFtkYXRhLWlvYy12YWx1ZV1cIik7XG4gIGNvbnN0IHNlZW4gPSBuZXcgU2V0PHN0cmluZz4oKTtcbiAgY29uc3QgdmFsdWVzOiBzdHJpbmdbXSA9IFtdO1xuXG4gIGNhcmRzLmZvckVhY2goKGNhcmQpID0+IHtcbiAgICBjb25zdCB2YWwgPSBjYXJkLmdldEF0dHJpYnV0ZShcImRhdGEtaW9jLXZhbHVlXCIpO1xuICAgIGlmICh2YWwgJiYgIXNlZW4uaGFzKHZhbCkpIHtcbiAgICAgIHNlZW4uYWRkKHZhbCk7XG4gICAgICB2YWx1ZXMucHVzaCh2YWwpO1xuICAgIH1cbiAgfSk7XG5cbiAgd3JpdGVUb0NsaXBib2FyZCh2YWx1ZXMuam9pbihcIlxcblwiKSwgYnRuKTtcbn1cbiIsICIvKipcbiAqIFB1cmUgdmVyZGljdCBjb21wdXRhdGlvbiBmdW5jdGlvbnMgXHUyMDE0IG5vIERPTSBhY2Nlc3MsIG5vIHNpZGUgZWZmZWN0cy5cbiAqXG4gKiBFeHRyYWN0ZWQgZnJvbSBlbnJpY2htZW50LnRzIChQaGFzZSAyKS4gVGhlc2UgZnVuY3Rpb25zIHRha2UgVmVyZGljdEVudHJ5W11cbiAqIGFycmF5cyBhbmQgcmV0dXJuIGNvbXB1dGVkIHJlc3VsdHMuIFRoZXkgYXJlIHRoZSBzaGFyZWQgY29tcHV0YXRpb24gbGF5ZXJcbiAqIHVzZWQgYnkgYm90aCByb3ctZmFjdG9yeS50cyAoc3VtbWFyeSByb3cgcmVuZGVyaW5nKSBhbmQgZW5yaWNobWVudC50c1xuICogKG9yY2hlc3RyYXRvciB2ZXJkaWN0IHRyYWNraW5nKS5cbiAqL1xuXG5pbXBvcnQgdHlwZSB7IFZlcmRpY3RLZXkgfSBmcm9tIFwiLi4vdHlwZXMvaW9jXCI7XG5pbXBvcnQgeyB2ZXJkaWN0U2V2ZXJpdHlJbmRleCB9IGZyb20gXCIuLi90eXBlcy9pb2NcIjtcblxuLyoqXG4gKiBQZXItcHJvdmlkZXIgdmVyZGljdCByZWNvcmQgYWNjdW11bGF0ZWQgZHVyaW5nIHRoZSBwb2xsaW5nIGxvb3AuXG4gKiBVc2VkIGZvciB3b3JzdC12ZXJkaWN0IGNvbXB1dGF0aW9uIGFjcm9zcyBhbGwgcHJvdmlkZXJzIGZvciBhbiBJT0MuXG4gKi9cbmV4cG9ydCBpbnRlcmZhY2UgVmVyZGljdEVudHJ5IHtcbiAgcHJvdmlkZXI6IHN0cmluZztcbiAgdmVyZGljdDogVmVyZGljdEtleTtcbiAgc3VtbWFyeVRleHQ6IHN0cmluZztcbiAgZGV0ZWN0aW9uQ291bnQ6IG51bWJlcjsgICAvLyBmcm9tIHJlc3VsdC5kZXRlY3Rpb25fY291bnQgKDAgZm9yIGVycm9ycylcbiAgdG90YWxFbmdpbmVzOiBudW1iZXI7ICAgICAvLyBmcm9tIHJlc3VsdC50b3RhbF9lbmdpbmVzICgwIGZvciBlcnJvcnMpXG4gIHN0YXRUZXh0OiBzdHJpbmc7ICAgICAgICAgLy8ga2V5IHN0YXQgc3RyaW5nIGZvciBkaXNwbGF5IChlLmcuLCBcIjQ1LzcyIGVuZ2luZXNcIilcbn1cblxuLyoqXG4gKiBDb21wdXRlIHRoZSB3b3JzdCAoaGlnaGVzdCBzZXZlcml0eSkgdmVyZGljdCBmcm9tIGEgbGlzdCBvZiBWZXJkaWN0RW50cnkgcmVjb3Jkcy5cbiAqXG4gKiBrbm93bl9nb29kIGZyb20gYW55IHByb3ZpZGVyIG92ZXJyaWRlcyBhbGwgb3RoZXIgdmVyZGljdHMgYXQgc3VtbWFyeSBsZXZlbC5cbiAqIFRoaXMgaXMgYW4gaW50ZW50aW9uYWwgZGVzaWduIGRlY2lzaW9uOiBrbm93bl9nb29kIChlLmcuIE5TUkwgbWF0Y2gpIG1lYW5zXG4gKiB0aGUgSU9DIGlzIGEgcmVjb2duaXplZCBzYWZlIGFydGlmYWN0IHJlZ2FyZGxlc3Mgb2Ygb3RoZXIgc2lnbmFscy5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgY29tcHV0ZVdvcnN0VmVyZGljdCgpIChsaW5lcyA1NDItNTUxKS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNvbXB1dGVXb3JzdFZlcmRpY3QoZW50cmllczogVmVyZGljdEVudHJ5W10pOiBWZXJkaWN0S2V5IHtcbiAgLy8ga25vd25fZ29vZCBmcm9tIGFueSBwcm92aWRlciBvdmVycmlkZXMgZXZlcnl0aGluZyBhdCBzdW1tYXJ5IGxldmVsXG4gIGlmIChlbnRyaWVzLnNvbWUoKGUpID0+IGUudmVyZGljdCA9PT0gXCJrbm93bl9nb29kXCIpKSB7XG4gICAgcmV0dXJuIFwia25vd25fZ29vZFwiO1xuICB9XG4gIGNvbnN0IHdvcnN0ID0gZmluZFdvcnN0RW50cnkoZW50cmllcyk7XG4gIHJldHVybiB3b3JzdCA/IHdvcnN0LnZlcmRpY3QgOiBcIm5vX2RhdGFcIjtcbn1cblxuLyoqXG4gKiBDb21wdXRlIGNvbnNlbnN1czogY291bnQgZmxhZ2dlZCAobWFsaWNpb3VzL3N1c3BpY2lvdXMpIGFuZCByZXNwb25kZWRcbiAqIChtYWxpY2lvdXMgKyBzdXNwaWNpb3VzICsgY2xlYW4pIHByb3ZpZGVycy5cbiAqIFBlciBkZXNpZ246IG5vX2RhdGEgYW5kIGVycm9yIGRvIE5PVCBjb3VudCBhcyB2b3Rlcy5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNvbXB1dGVDb25zZW5zdXMoZW50cmllczogVmVyZGljdEVudHJ5W10pOiB7IGZsYWdnZWQ6IG51bWJlcjsgcmVzcG9uZGVkOiBudW1iZXIgfSB7XG4gIGxldCBmbGFnZ2VkID0gMDtcbiAgbGV0IHJlc3BvbmRlZCA9IDA7XG4gIGZvciAoY29uc3QgZW50cnkgb2YgZW50cmllcykge1xuICAgIGlmIChlbnRyeS52ZXJkaWN0ID09PSBcIm1hbGljaW91c1wiIHx8IGVudHJ5LnZlcmRpY3QgPT09IFwic3VzcGljaW91c1wiKSB7XG4gICAgICBmbGFnZ2VkKys7XG4gICAgICByZXNwb25kZWQrKztcbiAgICB9IGVsc2UgaWYgKGVudHJ5LnZlcmRpY3QgPT09IFwiY2xlYW5cIikge1xuICAgICAgcmVzcG9uZGVkKys7XG4gICAgfVxuICAgIC8vIGVycm9yIGFuZCBub19kYXRhIGRvIE5PVCBjb3VudFxuICB9XG4gIHJldHVybiB7IGZsYWdnZWQsIHJlc3BvbmRlZCB9O1xufVxuXG4vKipcbiAqIFJldHVybiB0aGUgQ1NTIG1vZGlmaWVyIGNsYXNzIGZvciB0aGUgY29uc2Vuc3VzIGJhZGdlIGJhc2VkIG9uIGZsYWdnZWQgY291bnQuXG4gKiAwIGZsYWdnZWQgXHUyMTkyIGdyZWVuLCAxLTIgXHUyMTkyIHllbGxvdywgMysgXHUyMTkyIHJlZC5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNvbnNlbnN1c0JhZGdlQ2xhc3MoZmxhZ2dlZDogbnVtYmVyKTogc3RyaW5nIHtcbiAgaWYgKGZsYWdnZWQgPT09IDApIHJldHVybiBcImNvbnNlbnN1cy1iYWRnZS0tZ3JlZW5cIjtcbiAgaWYgKGZsYWdnZWQgPD0gMikgcmV0dXJuIFwiY29uc2Vuc3VzLWJhZGdlLS15ZWxsb3dcIjtcbiAgcmV0dXJuIFwiY29uc2Vuc3VzLWJhZGdlLS1yZWRcIjtcbn1cblxuLyoqXG4gKiBDb21wdXRlIGF0dHJpYnV0aW9uOiBmaW5kIHRoZSBcIm1vc3QgZGV0YWlsZWRcIiBwcm92aWRlciB0byBzaG93IGluIHN1bW1hcnkuXG4gKiBIZXVyaXN0aWM6IGhpZ2hlc3QgdG90YWxFbmdpbmVzIHdpbnMuIFRpZXMgYnJva2VuIGJ5IHZlcmRpY3Qgc2V2ZXJpdHkgZGVzY2VuZGluZy5cbiAqIFByb3ZpZGVycyB3aXRoIG5vX2RhdGEgb3IgZXJyb3IgYXJlIGV4Y2x1ZGVkIGFzIGNhbmRpZGF0ZXMuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjb21wdXRlQXR0cmlidXRpb24oZW50cmllczogVmVyZGljdEVudHJ5W10pOiB7IHByb3ZpZGVyOiBzdHJpbmc7IHRleHQ6IHN0cmluZyB9IHtcbiAgLy8gT25seSBjYW5kaWRhdGVzIHdpdGggYWN0dWFsIGRhdGEgKG5vdCBub19kYXRhIG9yIGVycm9yKVxuICBjb25zdCBjYW5kaWRhdGVzID0gZW50cmllcy5maWx0ZXIoXG4gICAgKGUpID0+IGUudmVyZGljdCAhPT0gXCJub19kYXRhXCIgJiYgZS52ZXJkaWN0ICE9PSBcImVycm9yXCJcbiAgKTtcblxuICBpZiAoY2FuZGlkYXRlcy5sZW5ndGggPT09IDApIHtcbiAgICByZXR1cm4geyBwcm92aWRlcjogXCJcIiwgdGV4dDogXCJObyBwcm92aWRlcnMgcmV0dXJuZWQgZGF0YSBmb3IgdGhpcyBJT0NcIiB9O1xuICB9XG5cbiAgLy8gU29ydDogaGlnaGVzdCB0b3RhbEVuZ2luZXMgZmlyc3QuIFRpZXMgYnJva2VuIGJ5IHNldmVyaXR5IGRlc2NlbmRpbmcuXG4gIGNvbnN0IHNvcnRlZCA9IFsuLi5jYW5kaWRhdGVzXS5zb3J0KChhLCBiKSA9PiB7XG4gICAgaWYgKGIudG90YWxFbmdpbmVzICE9PSBhLnRvdGFsRW5naW5lcykgcmV0dXJuIGIudG90YWxFbmdpbmVzIC0gYS50b3RhbEVuZ2luZXM7XG4gICAgcmV0dXJuIHZlcmRpY3RTZXZlcml0eUluZGV4KGIudmVyZGljdCkgLSB2ZXJkaWN0U2V2ZXJpdHlJbmRleChhLnZlcmRpY3QpO1xuICB9KTtcblxuICBjb25zdCBiZXN0ID0gc29ydGVkWzBdO1xuICBpZiAoIWJlc3QpIHJldHVybiB7IHByb3ZpZGVyOiBcIlwiLCB0ZXh0OiBcIk5vIHByb3ZpZGVycyByZXR1cm5lZCBkYXRhIGZvciB0aGlzIElPQ1wiIH07XG5cbiAgcmV0dXJuIHsgcHJvdmlkZXI6IGJlc3QucHJvdmlkZXIsIHRleHQ6IGJlc3QucHJvdmlkZXIgKyBcIjogXCIgKyBiZXN0LnN0YXRUZXh0IH07XG59XG5cbi8qKlxuICogRmluZCB0aGUgd29yc3QgKGhpZ2hlc3Qgc2V2ZXJpdHkpIFZlcmRpY3RFbnRyeSBmcm9tIGEgbGlzdC5cbiAqIFJldHVybnMgdW5kZWZpbmVkIGlmIHRoZSBsaXN0IGlzIGVtcHR5LlxuICovXG5leHBvcnQgZnVuY3Rpb24gZmluZFdvcnN0RW50cnkoZW50cmllczogVmVyZGljdEVudHJ5W10pOiBWZXJkaWN0RW50cnkgfCB1bmRlZmluZWQge1xuICBjb25zdCBmaXJzdCA9IGVudHJpZXNbMF07XG4gIGlmICghZmlyc3QpIHJldHVybiB1bmRlZmluZWQ7XG5cbiAgbGV0IHdvcnN0ID0gZmlyc3Q7XG4gIGZvciAobGV0IGkgPSAxOyBpIDwgZW50cmllcy5sZW5ndGg7IGkrKykge1xuICAgIGNvbnN0IGN1cnJlbnQgPSBlbnRyaWVzW2ldO1xuICAgIGlmICghY3VycmVudCkgY29udGludWU7XG4gICAgaWYgKHZlcmRpY3RTZXZlcml0eUluZGV4KGN1cnJlbnQudmVyZGljdCkgPiB2ZXJkaWN0U2V2ZXJpdHlJbmRleCh3b3JzdC52ZXJkaWN0KSkge1xuICAgICAgd29yc3QgPSBjdXJyZW50O1xuICAgIH1cbiAgfVxuICByZXR1cm4gd29yc3Q7XG59XG4iLCAiLyoqXG4gKiBET00gcm93IGNvbnN0cnVjdGlvbiBmb3IgZW5yaWNobWVudCByZXN1bHQgZGlzcGxheS5cbiAqXG4gKiBFeHRyYWN0ZWQgZnJvbSBlbnJpY2htZW50LnRzIChQaGFzZSAyKS4gT3ducyBhbGwgRE9NIGVsZW1lbnQgY3JlYXRpb25cbiAqIGZvciBwcm92aWRlciByb3dzLCBzdW1tYXJ5IHJvd3MsIGFuZCBjb250ZXh0IGZpZWxkcy4gVGhlIENPTlRFWFRfUFJPVklERVJTXG4gKiBzZXQgbGl2ZXMgaGVyZSBhcyBpdCBjb250cm9scyByb3cgcmVuZGVyaW5nIGRpc3BhdGNoLlxuICpcbiAqIERlcGVuZHMgb246XG4gKiAgIC0gdmVyZGljdC1jb21wdXRlLnRzIGZvciBWZXJkaWN0RW50cnkgdHlwZSBhbmQgY29tcHV0YXRpb24gZnVuY3Rpb25zXG4gKiAgIC0gdHlwZXMvYXBpLnRzICAgICAgIGZvciBFbnJpY2htZW50UmVzdWx0SXRlbSwgRW5yaWNobWVudEl0ZW1cbiAqICAgLSB0eXBlcy9pb2MudHMgICAgICAgZm9yIFZlcmRpY3RLZXksIFZFUkRJQ1RfTEFCRUxTXG4gKi9cblxuaW1wb3J0IHR5cGUgeyBFbnJpY2htZW50SXRlbSwgRW5yaWNobWVudFJlc3VsdEl0ZW0gfSBmcm9tIFwiLi4vdHlwZXMvYXBpXCI7XG5pbXBvcnQgdHlwZSB7IFZlcmRpY3RLZXkgfSBmcm9tIFwiLi4vdHlwZXMvaW9jXCI7XG5pbXBvcnQgeyBWRVJESUNUX0xBQkVMUyB9IGZyb20gXCIuLi90eXBlcy9pb2NcIjtcbmltcG9ydCB0eXBlIHsgVmVyZGljdEVudHJ5IH0gZnJvbSBcIi4vdmVyZGljdC1jb21wdXRlXCI7XG5pbXBvcnQgeyBjb21wdXRlV29yc3RWZXJkaWN0LCBjb21wdXRlQ29uc2Vuc3VzLCBjb21wdXRlQXR0cmlidXRpb24sXG4gICAgICAgICBjb25zZW5zdXNCYWRnZUNsYXNzIH0gZnJvbSBcIi4vdmVyZGljdC1jb21wdXRlXCI7XG5cbi8vIC0tLS0gUHJpdmF0ZSBoZWxwZXJzIC0tLS1cblxuLyoqXG4gKiBGb3JtYXQgYW4gSVNPIDg2MDEgZGF0ZSBzdHJpbmcgZm9yIGRpc3BsYXkuXG4gKiBSZXR1cm5zIFwiXCIgZm9yIG51bGwgaW5wdXQgKHNjYW5fZGF0ZSBjYW4gYmUgbnVsbCBwZXIgQVBJIGNvbnRyYWN0KS5cbiAqIFNvdXJjZTogbWFpbi5qcyBmb3JtYXREYXRlKCkgKGxpbmVzIDU4MS01ODgpLlxuICovXG5leHBvcnQgZnVuY3Rpb24gZm9ybWF0RGF0ZShpc286IHN0cmluZyB8IG51bGwpOiBzdHJpbmcge1xuICBpZiAoIWlzbykgcmV0dXJuIFwiXCI7XG4gIHRyeSB7XG4gICAgcmV0dXJuIG5ldyBEYXRlKGlzbykudG9Mb2NhbGVEYXRlU3RyaW5nKCk7XG4gIH0gY2F0Y2gge1xuICAgIHJldHVybiBpc287XG4gIH1cbn1cblxuLyoqXG4gKiBGb3JtYXQgYW4gSVNPIDg2MDEgdGltZXN0YW1wIGFzIGEgcmVsYXRpdmUgdGltZSBzdHJpbmcgKGUuZy4gXCIyaCBhZ29cIikuXG4gKiBGYWxscyBiYWNrIHRvIHRoZSByYXcgSVNPIHN0cmluZyBpZiBwYXJzaW5nIGZhaWxzLlxuICovXG5mdW5jdGlvbiBmb3JtYXRSZWxhdGl2ZVRpbWUoaXNvOiBzdHJpbmcpOiBzdHJpbmcge1xuICB0cnkge1xuICAgIGNvbnN0IGRpZmZNcyA9IERhdGUubm93KCkgLSBuZXcgRGF0ZShpc28pLmdldFRpbWUoKTtcbiAgICBjb25zdCBkaWZmTWluID0gTWF0aC5mbG9vcihkaWZmTXMgLyA2MDAwMCk7XG4gICAgaWYgKGRpZmZNaW4gPCAxKSByZXR1cm4gXCJqdXN0IG5vd1wiO1xuICAgIGlmIChkaWZmTWluIDwgNjApIHJldHVybiBkaWZmTWluICsgXCJtIGFnb1wiO1xuICAgIGNvbnN0IGRpZmZIciA9IE1hdGguZmxvb3IoZGlmZk1pbiAvIDYwKTtcbiAgICBpZiAoZGlmZkhyIDwgMjQpIHJldHVybiBkaWZmSHIgKyBcImggYWdvXCI7XG4gICAgY29uc3QgZGlmZkRheSA9IE1hdGguZmxvb3IoZGlmZkhyIC8gMjQpO1xuICAgIHJldHVybiBkaWZmRGF5ICsgXCJkIGFnb1wiO1xuICB9IGNhdGNoIHtcbiAgICByZXR1cm4gaXNvO1xuICB9XG59XG5cbi8vIC0tLS0gUHJvdmlkZXIgY29udGV4dCBmaWVsZCBkZWZpbml0aW9ucyAtLS0tXG5cbi8qKiBNYXBwaW5nIG9mIHByb3ZpZGVyIG5hbWUgLT4gZmllbGRzIHRvIGV4dHJhY3QgZnJvbSByYXdfc3RhdHMuICovXG5pbnRlcmZhY2UgQ29udGV4dEZpZWxkRGVmIHtcbiAga2V5OiBzdHJpbmc7XG4gIGxhYmVsOiBzdHJpbmc7XG4gIHR5cGU6IFwidGV4dFwiIHwgXCJ0YWdzXCI7XG59XG5cbmNvbnN0IFBST1ZJREVSX0NPTlRFWFRfRklFTERTOiBSZWNvcmQ8c3RyaW5nLCBDb250ZXh0RmllbGREZWZbXT4gPSB7XG4gIFZpcnVzVG90YWw6IFtcbiAgICB7IGtleTogXCJ0b3BfZGV0ZWN0aW9uc1wiLCBsYWJlbDogXCJEZXRlY3Rpb25zXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwicmVwdXRhdGlvblwiLCBsYWJlbDogXCJSZXB1dGF0aW9uXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIE1hbHdhcmVCYXphYXI6IFtcbiAgICB7IGtleTogXCJzaWduYXR1cmVcIiwgbGFiZWw6IFwiU2lnbmF0dXJlXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwidGFnc1wiLCBsYWJlbDogXCJUYWdzXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwiZmlsZV90eXBlXCIsIGxhYmVsOiBcIkZpbGUgdHlwZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImZpcnN0X3NlZW5cIiwgbGFiZWw6IFwiRmlyc3Qgc2VlblwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImxhc3Rfc2VlblwiLCBsYWJlbDogXCJMYXN0IHNlZW5cIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgXSxcbiAgVGhyZWF0Rm94OiBbXG4gICAgeyBrZXk6IFwibWFsd2FyZV9wcmludGFibGVcIiwgbGFiZWw6IFwiTWFsd2FyZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInRocmVhdF90eXBlXCIsIGxhYmVsOiBcIlRocmVhdCB0eXBlXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwiY29uZmlkZW5jZV9sZXZlbFwiLCBsYWJlbDogXCJDb25maWRlbmNlXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIEFidXNlSVBEQjogW1xuICAgIHsga2V5OiBcImFidXNlQ29uZmlkZW5jZVNjb3JlXCIsIGxhYmVsOiBcIkNvbmZpZGVuY2VcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJ0b3RhbFJlcG9ydHNcIiwgbGFiZWw6IFwiUmVwb3J0c1wiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImNvdW50cnlDb2RlXCIsIGxhYmVsOiBcIkNvdW50cnlcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJpc3BcIiwgbGFiZWw6IFwiSVNQXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwidXNhZ2VUeXBlXCIsIGxhYmVsOiBcIlVzYWdlXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIFwiU2hvZGFuIEludGVybmV0REJcIjogW1xuICAgIHsga2V5OiBcInBvcnRzXCIsIGxhYmVsOiBcIlBvcnRzXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwidnVsbnNcIiwgbGFiZWw6IFwiVnVsbnNcIiwgdHlwZTogXCJ0YWdzXCIgfSxcbiAgICB7IGtleTogXCJob3N0bmFtZXNcIiwgbGFiZWw6IFwiSG9zdG5hbWVzXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwiY3Blc1wiLCBsYWJlbDogXCJDUEVzXCIsIHR5cGU6IFwidGFnc1wiIH0sICAgICAgLy8gRVBST1YtMDFcbiAgICB7IGtleTogXCJ0YWdzXCIsIGxhYmVsOiBcIlRhZ3NcIiwgdHlwZTogXCJ0YWdzXCIgfSwgICAgICAvLyBFUFJPVi0wMVxuICBdLFxuICBcIkNJUkNMIEhhc2hsb29rdXBcIjogW1xuICAgIHsga2V5OiBcImZpbGVfbmFtZVwiLCBsYWJlbDogXCJGaWxlXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwic291cmNlXCIsIGxhYmVsOiBcIlNvdXJjZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICBdLFxuICBcIkdyZXlOb2lzZSBDb21tdW5pdHlcIjogW1xuICAgIHsga2V5OiBcIm5vaXNlXCIsIGxhYmVsOiBcIk5vaXNlXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwicmlvdFwiLCBsYWJlbDogXCJSSU9UXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwiY2xhc3NpZmljYXRpb25cIiwgbGFiZWw6IFwiQ2xhc3NpZmljYXRpb25cIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgXSxcbiAgVVJMaGF1czogW1xuICAgIHsga2V5OiBcInRocmVhdFwiLCBsYWJlbDogXCJUaHJlYXRcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJ1cmxfc3RhdHVzXCIsIGxhYmVsOiBcIlN0YXR1c1wiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInRhZ3NcIiwgbGFiZWw6IFwiVGFnc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICBdLFxuICBcIk9UWCBBbGllblZhdWx0XCI6IFtcbiAgICB7IGtleTogXCJwdWxzZV9jb3VudFwiLCBsYWJlbDogXCJQdWxzZXNcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJyZXB1dGF0aW9uXCIsIGxhYmVsOiBcIlJlcHV0YXRpb25cIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgXSxcbiAgXCJJUCBDb250ZXh0XCI6IFtcbiAgICB7IGtleTogXCJnZW9cIiwgbGFiZWw6IFwiTG9jYXRpb25cIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJyZXZlcnNlXCIsIGxhYmVsOiBcIlBUUlwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImZsYWdzXCIsIGxhYmVsOiBcIkZsYWdzXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gIF0sXG4gIFwiRE5TIFJlY29yZHNcIjogW1xuICAgIHsga2V5OiBcImFcIiwgICBsYWJlbDogXCJBXCIsICAgdHlwZTogXCJ0YWdzXCIgfSxcbiAgICB7IGtleTogXCJteFwiLCAgbGFiZWw6IFwiTVhcIiwgIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwibnNcIiwgIGxhYmVsOiBcIk5TXCIsICB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcInR4dFwiLCBsYWJlbDogXCJUWFRcIiwgdHlwZTogXCJ0YWdzXCIgfSxcbiAgXSxcbiAgXCJDZXJ0IEhpc3RvcnlcIjogW1xuICAgIHsga2V5OiBcImNlcnRfY291bnRcIiwgbGFiZWw6IFwiQ2VydHNcIiwgICAgICB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImVhcmxpZXN0XCIsICAgbGFiZWw6IFwiRmlyc3Qgc2VlblwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImxhdGVzdFwiLCAgICAgbGFiZWw6IFwiTGF0ZXN0XCIsICAgICB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInN1YmRvbWFpbnNcIiwgbGFiZWw6IFwiU3ViZG9tYWluc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICBdLFxuICBUaHJlYXRNaW5lcjogW1xuICAgIHsga2V5OiBcInBhc3NpdmVfZG5zXCIsIGxhYmVsOiBcIlBhc3NpdmUgRE5TXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwic2FtcGxlc1wiLCAgICAgbGFiZWw6IFwiU2FtcGxlc1wiLCAgICAgdHlwZTogXCJ0YWdzXCIgfSxcbiAgXSxcbiAgXCJBU04gSW50ZWxcIjogW1xuICAgIHsga2V5OiBcImFzblwiLCAgICAgICBsYWJlbDogXCJBU05cIiwgICAgICAgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJwcmVmaXhcIiwgICAgbGFiZWw6IFwiUHJlZml4XCIsICAgIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwicmlyXCIsICAgICAgIGxhYmVsOiBcIlJJUlwiLCAgICAgICB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImFsbG9jYXRlZFwiLCBsYWJlbDogXCJBbGxvY2F0ZWRcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgXSxcbn07XG5cbi8qKlxuICogUHJvdmlkZXJzIHRoYXQgdXNlIHRoZSBjb250ZXh0IHJvdyByZW5kZXJpbmcgcGF0aCAobm8gdmVyZGljdCBiYWRnZSwgcGlubmVkIHRvIHRvcCkuXG4gKiBFeHRlbmQgdGhpcyBzZXQgd2hlbiBhZGRpbmcgbmV3IGNvbnRleHQtb25seSBwcm92aWRlcnMuXG4gKi9cbmV4cG9ydCBjb25zdCBDT05URVhUX1BST1ZJREVSUyA9IG5ldyBTZXQoW1wiSVAgQ29udGV4dFwiLCBcIkROUyBSZWNvcmRzXCIsIFwiQ2VydCBIaXN0b3J5XCIsIFwiVGhyZWF0TWluZXJcIiwgXCJBU04gSW50ZWxcIl0pO1xuXG4vKipcbiAqIENyZWF0ZSBhIGxhYmVsZWQgY29udGV4dCBmaWVsZCBlbGVtZW50IHdpdGggdGhlIHByb3ZpZGVyLWNvbnRleHQtZmllbGQgY2xhc3MuXG4gKiBBbGwgRE9NIGNvbnN0cnVjdGlvbiB1c2VzIGNyZWF0ZUVsZW1lbnQgKyB0ZXh0Q29udGVudCAoU0VDLTA4KS5cbiAqL1xuZnVuY3Rpb24gY3JlYXRlTGFiZWxlZEZpZWxkKGxhYmVsOiBzdHJpbmcpOiBIVE1MRWxlbWVudCB7XG4gIGNvbnN0IGZpZWxkRWwgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgZmllbGRFbC5jbGFzc05hbWUgPSBcInByb3ZpZGVyLWNvbnRleHQtZmllbGRcIjtcblxuICBjb25zdCBsYWJlbEVsID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gIGxhYmVsRWwuY2xhc3NOYW1lID0gXCJwcm92aWRlci1jb250ZXh0LWxhYmVsXCI7XG4gIGxhYmVsRWwudGV4dENvbnRlbnQgPSBsYWJlbCArIFwiOiBcIjtcbiAgZmllbGRFbC5hcHBlbmRDaGlsZChsYWJlbEVsKTtcblxuICByZXR1cm4gZmllbGRFbDtcbn1cblxuLyoqXG4gKiBDcmVhdGUgY29udGV4dHVhbCBmaWVsZHMgZnJvbSBhIHByb3ZpZGVyIHJlc3VsdCdzIHJhd19zdGF0cy5cbiAqIFJldHVybnMgbnVsbCBpZiBubyBjb250ZXh0IGZpZWxkcyBhcmUgYXZhaWxhYmxlIGZvciB0aGlzIHByb3ZpZGVyLlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmZ1bmN0aW9uIGNyZWF0ZUNvbnRleHRGaWVsZHMocmVzdWx0OiBFbnJpY2htZW50UmVzdWx0SXRlbSk6IEhUTUxFbGVtZW50IHwgbnVsbCB7XG4gIGNvbnN0IGZpZWxkRGVmcyA9IFBST1ZJREVSX0NPTlRFWFRfRklFTERTW3Jlc3VsdC5wcm92aWRlcl07XG4gIGlmICghZmllbGREZWZzKSByZXR1cm4gbnVsbDtcblxuICBjb25zdCBzdGF0cyA9IHJlc3VsdC5yYXdfc3RhdHM7XG4gIGlmICghc3RhdHMpIHJldHVybiBudWxsO1xuXG4gIGNvbnN0IGNvbnRhaW5lciA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIik7XG4gIGNvbnRhaW5lci5jbGFzc05hbWUgPSBcInByb3ZpZGVyLWNvbnRleHRcIjtcblxuICBsZXQgaGFzRmllbGRzID0gZmFsc2U7XG5cbiAgZm9yIChjb25zdCBkZWYgb2YgZmllbGREZWZzKSB7XG4gICAgY29uc3QgdmFsdWUgPSBzdGF0c1tkZWYua2V5XTtcbiAgICBpZiAodmFsdWUgPT09IHVuZGVmaW5lZCB8fCB2YWx1ZSA9PT0gbnVsbCB8fCB2YWx1ZSA9PT0gXCJcIikgY29udGludWU7XG5cbiAgICBpZiAoZGVmLnR5cGUgPT09IFwidGFnc1wiICYmIEFycmF5LmlzQXJyYXkodmFsdWUpICYmIHZhbHVlLmxlbmd0aCA+IDApIHtcbiAgICAgIGNvbnN0IGZpZWxkRWwgPSBjcmVhdGVMYWJlbGVkRmllbGQoZGVmLmxhYmVsKTtcbiAgICAgIGZvciAoY29uc3QgdGFnIG9mIHZhbHVlKSB7XG4gICAgICAgIGlmICh0eXBlb2YgdGFnICE9PSBcInN0cmluZ1wiICYmIHR5cGVvZiB0YWcgIT09IFwibnVtYmVyXCIpIGNvbnRpbnVlO1xuICAgICAgICBjb25zdCB0YWdFbCA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICAgICAgICB0YWdFbC5jbGFzc05hbWUgPSBcImNvbnRleHQtdGFnXCI7XG4gICAgICAgIHRhZ0VsLnRleHRDb250ZW50ID0gU3RyaW5nKHRhZyk7XG4gICAgICAgIGZpZWxkRWwuYXBwZW5kQ2hpbGQodGFnRWwpO1xuICAgICAgfVxuICAgICAgY29udGFpbmVyLmFwcGVuZENoaWxkKGZpZWxkRWwpO1xuICAgICAgaGFzRmllbGRzID0gdHJ1ZTtcbiAgICB9IGVsc2UgaWYgKGRlZi50eXBlID09PSBcInRleHRcIiAmJiAodHlwZW9mIHZhbHVlID09PSBcInN0cmluZ1wiIHx8IHR5cGVvZiB2YWx1ZSA9PT0gXCJudW1iZXJcIiB8fCB0eXBlb2YgdmFsdWUgPT09IFwiYm9vbGVhblwiKSkge1xuICAgICAgY29uc3QgZmllbGRFbCA9IGNyZWF0ZUxhYmVsZWRGaWVsZChkZWYubGFiZWwpO1xuICAgICAgY29uc3QgdmFsRWwgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICAgIHZhbEVsLnRleHRDb250ZW50ID0gU3RyaW5nKHZhbHVlKTtcbiAgICAgIGZpZWxkRWwuYXBwZW5kQ2hpbGQodmFsRWwpO1xuICAgICAgY29udGFpbmVyLmFwcGVuZENoaWxkKGZpZWxkRWwpO1xuICAgICAgaGFzRmllbGRzID0gdHJ1ZTtcbiAgICB9XG4gIH1cblxuICByZXR1cm4gaGFzRmllbGRzID8gY29udGFpbmVyIDogbnVsbDtcbn1cblxuLy8gLS0tLSBFeHBvcnRlZCByb3cgYnVpbGRlcnMgLS0tLVxuXG4vKipcbiAqIEdldCBvciBjcmVhdGUgdGhlIC5pb2Mtc3VtbWFyeS1yb3cgZWxlbWVudCBpbnNpZGUgdGhlIHNsb3QuXG4gKiBJbnNlcnRzIGJlZm9yZSAuY2hldnJvbi10b2dnbGUgaWYgcHJlc2VudCwgb3RoZXJ3aXNlIGFzIGZpcnN0IGNoaWxkLlxuICovXG5leHBvcnQgZnVuY3Rpb24gZ2V0T3JDcmVhdGVTdW1tYXJ5Um93KHNsb3Q6IEhUTUxFbGVtZW50KTogSFRNTEVsZW1lbnQge1xuICBjb25zdCBleGlzdGluZyA9IHNsb3QucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIuaW9jLXN1bW1hcnktcm93XCIpO1xuICBpZiAoZXhpc3RpbmcpIHJldHVybiBleGlzdGluZztcblxuICBjb25zdCByb3cgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiZGl2XCIpO1xuICByb3cuY2xhc3NOYW1lID0gXCJpb2Mtc3VtbWFyeS1yb3dcIjtcblxuICAvLyBJbnNlcnQgYmVmb3JlIGNoZXZyb24tdG9nZ2xlIGlmIHByZXNlbnRcbiAgY29uc3QgY2hldnJvbiA9IHNsb3QucXVlcnlTZWxlY3RvcihcIi5jaGV2cm9uLXRvZ2dsZVwiKTtcbiAgaWYgKGNoZXZyb24pIHtcbiAgICBzbG90Lmluc2VydEJlZm9yZShyb3csIGNoZXZyb24pO1xuICB9IGVsc2Uge1xuICAgIHNsb3QuYXBwZW5kQ2hpbGQocm93KTtcbiAgfVxuXG4gIHJldHVybiByb3c7XG59XG5cbi8qKlxuICogVXBkYXRlIChvciBjcmVhdGUpIHRoZSBzdW1tYXJ5IHJvdyBmb3IgYW4gSU9DIGluIGl0cyBlbnJpY2htZW50IHNsb3QuXG4gKiBTaG93cyB3b3JzdCB2ZXJkaWN0IGJhZGdlLCBhdHRyaWJ1dGlvbiB0ZXh0LCBhbmQgY29uc2Vuc3VzIGJhZGdlLlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiB1cGRhdGVTdW1tYXJ5Um93KFxuICBzbG90OiBIVE1MRWxlbWVudCxcbiAgaW9jVmFsdWU6IHN0cmluZyxcbiAgaW9jVmVyZGljdHM6IFJlY29yZDxzdHJpbmcsIFZlcmRpY3RFbnRyeVtdPlxuKTogdm9pZCB7XG4gIGNvbnN0IGVudHJpZXMgPSBpb2NWZXJkaWN0c1tpb2NWYWx1ZV07XG4gIGlmICghZW50cmllcyB8fCBlbnRyaWVzLmxlbmd0aCA9PT0gMCkgcmV0dXJuO1xuXG4gIGNvbnN0IHdvcnN0VmVyZGljdCA9IGNvbXB1dGVXb3JzdFZlcmRpY3QoZW50cmllcyk7XG4gIGNvbnN0IGF0dHJpYnV0aW9uID0gY29tcHV0ZUF0dHJpYnV0aW9uKGVudHJpZXMpO1xuICBjb25zdCB7IGZsYWdnZWQsIHJlc3BvbmRlZCB9ID0gY29tcHV0ZUNvbnNlbnN1cyhlbnRyaWVzKTtcblxuICBjb25zdCBzdW1tYXJ5Um93ID0gZ2V0T3JDcmVhdGVTdW1tYXJ5Um93KHNsb3QpO1xuXG4gIC8vIENsZWFyIGV4aXN0aW5nIGNoaWxkcmVuIChpbW11dGFibGUgcmVidWlsZCBwYXR0ZXJuKVxuICBzdW1tYXJ5Um93LnRleHRDb250ZW50ID0gXCJcIjtcblxuICAvLyBhLiBWZXJkaWN0IGJhZGdlXG4gIGNvbnN0IHZlcmRpY3RCYWRnZSA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICB2ZXJkaWN0QmFkZ2UuY2xhc3NOYW1lID0gXCJ2ZXJkaWN0LWJhZGdlIHZlcmRpY3QtXCIgKyB3b3JzdFZlcmRpY3Q7XG4gIHZlcmRpY3RCYWRnZS50ZXh0Q29udGVudCA9IFZFUkRJQ1RfTEFCRUxTW3dvcnN0VmVyZGljdF07XG4gIHN1bW1hcnlSb3cuYXBwZW5kQ2hpbGQodmVyZGljdEJhZGdlKTtcblxuICAvLyBiLiBBdHRyaWJ1dGlvbiB0ZXh0XG4gIGNvbnN0IGF0dHJpYnV0aW9uU3BhbiA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBhdHRyaWJ1dGlvblNwYW4uY2xhc3NOYW1lID0gXCJpb2Mtc3VtbWFyeS1hdHRyaWJ1dGlvblwiO1xuICBhdHRyaWJ1dGlvblNwYW4udGV4dENvbnRlbnQgPSBhdHRyaWJ1dGlvbi50ZXh0O1xuICBzdW1tYXJ5Um93LmFwcGVuZENoaWxkKGF0dHJpYnV0aW9uU3Bhbik7XG5cbiAgLy8gYy4gQ29uc2Vuc3VzIGJhZGdlXG4gIGNvbnN0IGNvbnNlbnN1c0JhZGdlID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gIGNvbnNlbnN1c0JhZGdlLmNsYXNzTmFtZSA9IFwiY29uc2Vuc3VzLWJhZGdlIFwiICsgY29uc2Vuc3VzQmFkZ2VDbGFzcyhmbGFnZ2VkKTtcbiAgY29uc2Vuc3VzQmFkZ2UudGV4dENvbnRlbnQgPSBcIltcIiArIGZsYWdnZWQgKyBcIi9cIiArIHJlc3BvbmRlZCArIFwiXVwiO1xuICBzdW1tYXJ5Um93LmFwcGVuZENoaWxkKGNvbnNlbnN1c0JhZGdlKTtcbn1cblxuLyoqXG4gKiBDcmVhdGUgYSBjb250ZXh0IHJvdyBcdTIwMTQgcHVyZWx5IGluZm9ybWF0aW9uYWwsIG5vIHZlcmRpY3QgYmFkZ2UuXG4gKiBDb250ZXh0IHByb3ZpZGVycyAoSVAgQ29udGV4dCwgRE5TIFJlY29yZHMsIENlcnQgSGlzdG9yeSkgY2FycnkgbWV0YWRhdGFcbiAqIGFuZCBtdXN0IG5vdCBwYXJ0aWNpcGF0ZSBpbiBjb25zZW5zdXMvYXR0cmlidXRpb24gb3IgY2FyZCB2ZXJkaWN0IHVwZGF0ZXMuXG4gKiBBbGwgRE9NIGNvbnN0cnVjdGlvbiB1c2VzIGNyZWF0ZUVsZW1lbnQgKyB0ZXh0Q29udGVudCAoU0VDLTA4KS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNyZWF0ZUNvbnRleHRSb3cocmVzdWx0OiBFbnJpY2htZW50UmVzdWx0SXRlbSk6IEhUTUxFbGVtZW50IHtcbiAgY29uc3Qgcm93ID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcImRpdlwiKTtcbiAgcm93LmNsYXNzTmFtZSA9IFwicHJvdmlkZXItZGV0YWlsLXJvdyBwcm92aWRlci1jb250ZXh0LXJvd1wiO1xuICByb3cuc2V0QXR0cmlidXRlKFwiZGF0YS12ZXJkaWN0XCIsIFwiY29udGV4dFwiKTsgLy8gc2VudGluZWwgZm9yIHNvcnQgcGlubmluZ1xuXG4gIGNvbnN0IG5hbWVTcGFuID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gIG5hbWVTcGFuLmNsYXNzTmFtZSA9IFwicHJvdmlkZXItZGV0YWlsLW5hbWVcIjtcbiAgbmFtZVNwYW4udGV4dENvbnRlbnQgPSByZXN1bHQucHJvdmlkZXI7XG4gIHJvdy5hcHBlbmRDaGlsZChuYW1lU3Bhbik7XG5cbiAgLy8gTk8gdmVyZGljdCBiYWRnZSBcdTIwMTQgSVAgQ29udGV4dCBpcyBwdXJlbHkgaW5mb3JtYXRpb25hbFxuXG4gIC8vIEFkZCBjb250ZXh0IGZpZWxkcyAoZ2VvLCBQVFIsIGZsYWdzKSB1c2luZyBleGlzdGluZyBjcmVhdGVDb250ZXh0RmllbGRzKClcbiAgY29uc3QgY29udGV4dEVsID0gY3JlYXRlQ29udGV4dEZpZWxkcyhyZXN1bHQpO1xuICBpZiAoY29udGV4dEVsKSB7XG4gICAgcm93LmFwcGVuZENoaWxkKGNvbnRleHRFbCk7XG4gIH1cblxuICAvLyBDYWNoZSBiYWRnZSBpZiByZXN1bHQgd2FzIHNlcnZlZCBmcm9tIGNhY2hlXG4gIGlmIChyZXN1bHQuY2FjaGVkX2F0KSB7XG4gICAgY29uc3QgY2FjaGVCYWRnZSA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICAgIGNhY2hlQmFkZ2UuY2xhc3NOYW1lID0gXCJjYWNoZS1iYWRnZVwiO1xuICAgIGNhY2hlQmFkZ2UudGV4dENvbnRlbnQgPSBcImNhY2hlZCBcIiArIGZvcm1hdFJlbGF0aXZlVGltZShyZXN1bHQuY2FjaGVkX2F0KTtcbiAgICByb3cuYXBwZW5kQ2hpbGQoY2FjaGVCYWRnZSk7XG4gIH1cblxuICByZXR1cm4gcm93O1xufVxuXG4vKipcbiAqIENyZWF0ZSBhIHNpbmdsZSBwcm92aWRlciBkZXRhaWwgcm93IGZvciB0aGUgLmVucmljaG1lbnQtZGV0YWlscyBjb250YWluZXIuXG4gKiBBbGwgRE9NIGNvbnN0cnVjdGlvbiB1c2VzIGNyZWF0ZUVsZW1lbnQgKyB0ZXh0Q29udGVudCAoU0VDLTA4KS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNyZWF0ZURldGFpbFJvdyhcbiAgcHJvdmlkZXI6IHN0cmluZyxcbiAgdmVyZGljdDogVmVyZGljdEtleSxcbiAgc3RhdFRleHQ6IHN0cmluZyxcbiAgcmVzdWx0PzogRW5yaWNobWVudEl0ZW1cbik6IEhUTUxFbGVtZW50IHtcbiAgY29uc3Qgcm93ID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcImRpdlwiKTtcbiAgcm93LmNsYXNzTmFtZSA9IFwicHJvdmlkZXItZGV0YWlsLXJvd1wiO1xuICByb3cuc2V0QXR0cmlidXRlKFwiZGF0YS12ZXJkaWN0XCIsIHZlcmRpY3QpO1xuXG4gIGNvbnN0IG5hbWVTcGFuID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gIG5hbWVTcGFuLmNsYXNzTmFtZSA9IFwicHJvdmlkZXItZGV0YWlsLW5hbWVcIjtcbiAgbmFtZVNwYW4udGV4dENvbnRlbnQgPSBwcm92aWRlcjtcblxuICBjb25zdCBiYWRnZSA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBiYWRnZS5jbGFzc05hbWUgPSBcInZlcmRpY3QtYmFkZ2UgdmVyZGljdC1cIiArIHZlcmRpY3Q7XG4gIGJhZGdlLnRleHRDb250ZW50ID0gVkVSRElDVF9MQUJFTFNbdmVyZGljdF07XG5cbiAgY29uc3Qgc3RhdFNwYW4gPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgc3RhdFNwYW4uY2xhc3NOYW1lID0gXCJwcm92aWRlci1kZXRhaWwtc3RhdFwiO1xuICBzdGF0U3Bhbi50ZXh0Q29udGVudCA9IHN0YXRUZXh0O1xuXG4gIHJvdy5hcHBlbmRDaGlsZChuYW1lU3Bhbik7XG4gIHJvdy5hcHBlbmRDaGlsZChiYWRnZSk7XG4gIHJvdy5hcHBlbmRDaGlsZChzdGF0U3Bhbik7XG5cbiAgLy8gQ2FjaGUgYmFkZ2UgXHUyMDE0IHNob3cgcmVsYXRpdmUgdGltZSBpZiByZXN1bHQgd2FzIHNlcnZlZCBmcm9tIGNhY2hlXG4gIGlmIChyZXN1bHQgJiYgcmVzdWx0LnR5cGUgPT09IFwicmVzdWx0XCIgJiYgcmVzdWx0LmNhY2hlZF9hdCkge1xuICAgIGNvbnN0IGNhY2hlQmFkZ2UgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICBjYWNoZUJhZGdlLmNsYXNzTmFtZSA9IFwiY2FjaGUtYmFkZ2VcIjtcbiAgICBjb25zdCBhZ28gPSBmb3JtYXRSZWxhdGl2ZVRpbWUocmVzdWx0LmNhY2hlZF9hdCk7XG4gICAgY2FjaGVCYWRnZS50ZXh0Q29udGVudCA9IFwiY2FjaGVkIFwiICsgYWdvO1xuICAgIHJvdy5hcHBlbmRDaGlsZChjYWNoZUJhZGdlKTtcbiAgfVxuXG4gIC8vIENvbnRleHQgZmllbGRzIFx1MjAxNCBwcm92aWRlci1zcGVjaWZpYyBpbnRlbGxpZ2VuY2UgZnJvbSByYXdfc3RhdHNcbiAgaWYgKHJlc3VsdCAmJiByZXN1bHQudHlwZSA9PT0gXCJyZXN1bHRcIikge1xuICAgIGNvbnN0IGNvbnRleHRFbCA9IGNyZWF0ZUNvbnRleHRGaWVsZHMocmVzdWx0KTtcbiAgICBpZiAoY29udGV4dEVsKSB7XG4gICAgICByb3cuYXBwZW5kQ2hpbGQoY29udGV4dEVsKTtcbiAgICB9XG4gIH1cblxuICByZXR1cm4gcm93O1xufVxuXG4vKipcbiAqIFVuaWZpZWQgcm93IGNyZWF0aW9uIGRpc3BhdGNoZXIgXHUyMDE0IHJvdXRlcyB0byBjcmVhdGVDb250ZXh0Um93IG9yIGNyZWF0ZURldGFpbFJvd1xuICogYmFzZWQgb24gdGhlIGtpbmQgcGFyYW1ldGVyLiBQcm92aWRlcyBhIHN0YWJsZSBBUEkgZm9yIFBoYXNlIDMgdmlzdWFsIHdvcmsuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjcmVhdGVQcm92aWRlclJvdyhcbiAgcmVzdWx0OiBFbnJpY2htZW50UmVzdWx0SXRlbSxcbiAga2luZDogXCJjb250ZXh0XCIgfCBcImRldGFpbFwiLFxuICBzdGF0VGV4dDogc3RyaW5nXG4pOiBIVE1MRWxlbWVudCB7XG4gIGlmIChraW5kID09PSBcImNvbnRleHRcIikge1xuICAgIHJldHVybiBjcmVhdGVDb250ZXh0Um93KHJlc3VsdCk7XG4gIH1cbiAgcmV0dXJuIGNyZWF0ZURldGFpbFJvdyhyZXN1bHQucHJvdmlkZXIsIHJlc3VsdC52ZXJkaWN0LCBzdGF0VGV4dCwgcmVzdWx0KTtcbn1cbiIsICIvKipcbiAqIEVucmljaG1lbnQgcG9sbGluZyBvcmNoZXN0cmF0b3IgXHUyMDE0IHBvbGxpbmcgbG9vcCwgcHJvZ3Jlc3MgdHJhY2tpbmcsXG4gKiByZXN1bHQgZGlzcGF0Y2gsIGFuZCBtb2R1bGUgc3RhdGUuXG4gKlxuICogVmVyZGljdCBjb21wdXRhdGlvbiBsaXZlcyBpbiB2ZXJkaWN0LWNvbXB1dGUudHMuXG4gKiBET00gcm93IGNvbnN0cnVjdGlvbiBsaXZlcyBpbiByb3ctZmFjdG9yeS50cy5cbiAqIFRoaXMgbW9kdWxlIG93bnMgdGhlIHBvbGxpbmcgaW50ZXJ2YWwsIGRlZHVwIG1hcCwgcGVyLUlPQyBzdGF0ZSxcbiAqIGFuZCBjb29yZGluYXRlcyByZW5kZXJpbmcgdGhyb3VnaCBpbXBvcnRlZCBmdW5jdGlvbnMuXG4gKi9cblxuaW1wb3J0IHR5cGUgeyBFbnJpY2htZW50SXRlbSwgRW5yaWNobWVudFN0YXR1cyB9IGZyb20gXCIuLi90eXBlcy9hcGlcIjtcbmltcG9ydCB0eXBlIHsgVmVyZGljdEtleSB9IGZyb20gXCIuLi90eXBlcy9pb2NcIjtcbmltcG9ydCB7IHZlcmRpY3RTZXZlcml0eUluZGV4LCBnZXRQcm92aWRlckNvdW50cyB9IGZyb20gXCIuLi90eXBlcy9pb2NcIjtcbmltcG9ydCB7IGF0dHIgfSBmcm9tIFwiLi4vdXRpbHMvZG9tXCI7XG5pbXBvcnQge1xuICBmaW5kQ2FyZEZvcklvYyxcbiAgdXBkYXRlQ2FyZFZlcmRpY3QsXG4gIHVwZGF0ZURhc2hib2FyZENvdW50cyxcbiAgc29ydENhcmRzQnlTZXZlcml0eSxcbn0gZnJvbSBcIi4vY2FyZHNcIjtcbmltcG9ydCB7IGV4cG9ydEpTT04sIGV4cG9ydENTViwgY29weUFsbElPQ3MgfSBmcm9tIFwiLi9leHBvcnRcIjtcbmltcG9ydCB0eXBlIHsgVmVyZGljdEVudHJ5IH0gZnJvbSBcIi4vdmVyZGljdC1jb21wdXRlXCI7XG5pbXBvcnQgeyBjb21wdXRlV29yc3RWZXJkaWN0LCBmaW5kV29yc3RFbnRyeSB9IGZyb20gXCIuL3ZlcmRpY3QtY29tcHV0ZVwiO1xuaW1wb3J0IHsgQ09OVEVYVF9QUk9WSURFUlMsIGNyZWF0ZUNvbnRleHRSb3csIGNyZWF0ZURldGFpbFJvdyxcbiAgICAgICAgIHVwZGF0ZVN1bW1hcnlSb3csIGZvcm1hdERhdGUgfSBmcm9tIFwiLi9yb3ctZmFjdG9yeVwiO1xuXG4vLyAtLS0tIE1vZHVsZS1wcml2YXRlIHN0YXRlIC0tLS1cblxuLyoqIERlYm91bmNlIHRpbWVycyBmb3Igc29ydERldGFpbFJvd3MgXHUyMDE0IGtleWVkIGJ5IGlvY192YWx1ZSAqL1xuY29uc3Qgc29ydFRpbWVyczogTWFwPHN0cmluZywgUmV0dXJuVHlwZTx0eXBlb2Ygc2V0VGltZW91dD4+ID0gbmV3IE1hcCgpO1xuXG4vKiogQWNjdW11bGF0ZWQgZW5yaWNobWVudCByZXN1bHRzIGZvciBleHBvcnQgKi9cbmNvbnN0IGFsbFJlc3VsdHM6IEVucmljaG1lbnRJdGVtW10gPSBbXTtcblxuLy8gLS0tLSBQcml2YXRlIGhlbHBlcnMgLS0tLVxuXG4vKipcbiAqIFNvcnQgYWxsIC5wcm92aWRlci1kZXRhaWwtcm93IGVsZW1lbnRzIGluIGEgY29udGFpbmVyIGJ5IHNldmVyaXR5IGRlc2NlbmRpbmcuXG4gKiBtYWxpY2lvdXMgKGluZGV4IDQpIGZpcnN0LCBlcnJvciAoaW5kZXggMCkgbGFzdC5cbiAqIERlYm91bmNlZCBhdCAxMDBtcyBwZXIgSU9DIHRvIGF2b2lkIHRocmFzaGluZyBkdXJpbmcgYmF0Y2ggcmVzdWx0IGRlbGl2ZXJ5LlxuICovXG5mdW5jdGlvbiBzb3J0RGV0YWlsUm93cyhkZXRhaWxzQ29udGFpbmVyOiBIVE1MRWxlbWVudCwgaW9jVmFsdWU6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCBleGlzdGluZyA9IHNvcnRUaW1lcnMuZ2V0KGlvY1ZhbHVlKTtcbiAgaWYgKGV4aXN0aW5nICE9PSB1bmRlZmluZWQpIHtcbiAgICBjbGVhclRpbWVvdXQoZXhpc3RpbmcpO1xuICB9XG4gIGNvbnN0IHRpbWVyID0gc2V0VGltZW91dCgoKSA9PiB7XG4gICAgc29ydFRpbWVycy5kZWxldGUoaW9jVmFsdWUpO1xuICAgIGNvbnN0IHJvd3MgPSBBcnJheS5mcm9tKFxuICAgICAgZGV0YWlsc0NvbnRhaW5lci5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcIi5wcm92aWRlci1kZXRhaWwtcm93XCIpXG4gICAgKTtcbiAgICByb3dzLnNvcnQoKGEsIGIpID0+IHtcbiAgICAgIGNvbnN0IGFWZXJkaWN0ID0gYS5nZXRBdHRyaWJ1dGUoXCJkYXRhLXZlcmRpY3RcIikgYXMgVmVyZGljdEtleSB8IG51bGw7XG4gICAgICBjb25zdCBiVmVyZGljdCA9IGIuZ2V0QXR0cmlidXRlKFwiZGF0YS12ZXJkaWN0XCIpIGFzIFZlcmRpY3RLZXkgfCBudWxsO1xuICAgICAgY29uc3QgYUlkeCA9IGFWZXJkaWN0ID8gdmVyZGljdFNldmVyaXR5SW5kZXgoYVZlcmRpY3QpIDogLTE7XG4gICAgICBjb25zdCBiSWR4ID0gYlZlcmRpY3QgPyB2ZXJkaWN0U2V2ZXJpdHlJbmRleChiVmVyZGljdCkgOiAtMTtcbiAgICAgIHJldHVybiBiSWR4IC0gYUlkeDsgLy8gZGVzY2VuZGluZzogbWFsaWNpb3VzIGZpcnN0XG4gICAgfSk7XG4gICAgZm9yIChjb25zdCByb3cgb2Ygcm93cykge1xuICAgICAgZGV0YWlsc0NvbnRhaW5lci5hcHBlbmRDaGlsZChyb3cpO1xuICAgIH1cblxuICAgIC8vIFBpbiBjb250ZXh0IHJvd3MgKElQIENvbnRleHQpIHRvIHRvcCBhZnRlciBzZXZlcml0eSBzb3J0XG4gICAgY29uc3QgY29udGV4dFJvd3MgPSBBcnJheS5mcm9tKFxuICAgICAgZGV0YWlsc0NvbnRhaW5lci5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PignLnByb3ZpZGVyLWRldGFpbC1yb3dbZGF0YS12ZXJkaWN0PVwiY29udGV4dFwiXScpXG4gICAgKTtcbiAgICBmb3IgKGNvbnN0IGNyIG9mIGNvbnRleHRSb3dzKSB7XG4gICAgICBkZXRhaWxzQ29udGFpbmVyLmluc2VydEJlZm9yZShjciwgZGV0YWlsc0NvbnRhaW5lci5maXJzdENoaWxkKTtcbiAgICB9XG4gIH0sIDEwMCk7XG4gIHNvcnRUaW1lcnMuc2V0KGlvY1ZhbHVlLCB0aW1lcik7XG59XG5cbi8qKlxuICogRmluZCB0aGUgY29weSBidXR0b24gZm9yIGEgZ2l2ZW4gSU9DIHZhbHVlIGJ5IGl0ZXJhdGluZyAuY29weS1idG4gZWxlbWVudHMuXG4gKiBTb3VyY2U6IG1haW4uanMgZmluZENvcHlCdXR0b25Gb3JJb2MoKSAobGluZXMgNTcxLTU3OSkuXG4gKi9cbmZ1bmN0aW9uIGZpbmRDb3B5QnV0dG9uRm9ySW9jKGlvY1ZhbHVlOiBzdHJpbmcpOiBIVE1MRWxlbWVudCB8IG51bGwge1xuICBjb25zdCBidG5zID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuY29weS1idG5cIik7XG4gIGZvciAobGV0IGkgPSAwOyBpIDwgYnRucy5sZW5ndGg7IGkrKykge1xuICAgIGNvbnN0IGJ0biA9IGJ0bnNbaV07XG4gICAgaWYgKGJ0biAmJiBhdHRyKGJ0biwgXCJkYXRhLXZhbHVlXCIpID09PSBpb2NWYWx1ZSkge1xuICAgICAgcmV0dXJuIGJ0bjtcbiAgICB9XG4gIH1cbiAgcmV0dXJuIG51bGw7XG59XG5cbi8qKlxuICogVXBkYXRlIHRoZSBjb3B5IGJ1dHRvbidzIGRhdGEtZW5yaWNobWVudCBhdHRyaWJ1dGUgd2l0aCB0aGUgd29yc3QgdmVyZGljdFxuICogc3VtbWFyeSB0ZXh0IGFjcm9zcyBhbGwgcHJvdmlkZXJzIGZvciB0aGUgZ2l2ZW4gSU9DLlxuICogU291cmNlOiBtYWluLmpzIHVwZGF0ZUNvcHlCdXR0b25Xb3JzdFZlcmRpY3QoKSAobGluZXMgNTUzLTU2OSkuXG4gKi9cbmZ1bmN0aW9uIHVwZGF0ZUNvcHlCdXR0b25Xb3JzdFZlcmRpY3QoXG4gIGlvY1ZhbHVlOiBzdHJpbmcsXG4gIGlvY1ZlcmRpY3RzOiBSZWNvcmQ8c3RyaW5nLCBWZXJkaWN0RW50cnlbXT5cbik6IHZvaWQge1xuICBjb25zdCBjb3B5QnRuID0gZmluZENvcHlCdXR0b25Gb3JJb2MoaW9jVmFsdWUpO1xuICBpZiAoIWNvcHlCdG4pIHJldHVybjtcblxuICBjb25zdCB3b3JzdEVudHJ5ID0gZmluZFdvcnN0RW50cnkoaW9jVmVyZGljdHNbaW9jVmFsdWVdID8/IFtdKTtcbiAgaWYgKCF3b3JzdEVudHJ5KSByZXR1cm47XG5cbiAgY29weUJ0bi5zZXRBdHRyaWJ1dGUoXCJkYXRhLWVucmljaG1lbnRcIiwgd29yc3RFbnRyeS5zdW1tYXJ5VGV4dCk7XG59XG5cbi8qKlxuICogVXBkYXRlIHRoZSBwcm9ncmVzcyBiYXIgZmlsbCBhbmQgdGV4dC5cbiAqIFNvdXJjZTogbWFpbi5qcyB1cGRhdGVQcm9ncmVzc0JhcigpIChsaW5lcyAzNzUtMzgzKS5cbiAqL1xuZnVuY3Rpb24gdXBkYXRlUHJvZ3Jlc3NCYXIoZG9uZTogbnVtYmVyLCB0b3RhbDogbnVtYmVyKTogdm9pZCB7XG4gIGNvbnN0IGZpbGwgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcImVucmljaC1wcm9ncmVzcy1maWxsXCIpO1xuICBjb25zdCB0ZXh0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJlbnJpY2gtcHJvZ3Jlc3MtdGV4dFwiKTtcbiAgaWYgKCFmaWxsIHx8ICF0ZXh0KSByZXR1cm47XG5cbiAgY29uc3QgcGN0ID0gdG90YWwgPiAwID8gTWF0aC5yb3VuZCgoZG9uZSAvIHRvdGFsKSAqIDEwMCkgOiAwO1xuICBmaWxsLnN0eWxlLndpZHRoID0gcGN0ICsgXCIlXCI7XG4gIHRleHQudGV4dENvbnRlbnQgPSBkb25lICsgXCIvXCIgKyB0b3RhbCArIFwiIHByb3ZpZGVycyBjb21wbGV0ZVwiO1xufVxuXG4vKipcbiAqIFNob3cgb3IgdXBkYXRlIHRoZSBwZW5kaW5nIHByb3ZpZGVyIGluZGljYXRvciBhZnRlciB0aGUgZmlyc3QgcmVzdWx0IGZvciBhbiBJT0MuXG4gKiBSZWFkcyBwcm92aWRlciBjb3VudHMgZnJvbSB0aGUgRE9NIHZpYSBnZXRQcm92aWRlckNvdW50cygpIFx1MjAxNCByZWZsZWN0cyB0aGUgYWN0dWFsXG4gKiBjb25maWd1cmVkIHByb3ZpZGVyIHNldCBpbmplY3RlZCBieSB0aGUgRmxhc2sgcm91dGUgaW50byBkYXRhLXByb3ZpZGVyLWNvdW50cy5cbiAqIFNvdXJjZTogbWFpbi5qcyB1cGRhdGVQZW5kaW5nSW5kaWNhdG9yKCkgKGxpbmVzIDQxMi00NDEpLlxuICovXG5mdW5jdGlvbiB1cGRhdGVQZW5kaW5nSW5kaWNhdG9yKFxuICBzbG90OiBIVE1MRWxlbWVudCxcbiAgY2FyZDogSFRNTEVsZW1lbnQgfCBudWxsLFxuICByZWNlaXZlZENvdW50OiBudW1iZXJcbik6IHZvaWQge1xuICBjb25zdCBpb2NUeXBlID0gY2FyZCA/IGF0dHIoY2FyZCwgXCJkYXRhLWlvYy10eXBlXCIpIDogXCJcIjtcbiAgY29uc3QgcHJvdmlkZXJDb3VudHMgPSBnZXRQcm92aWRlckNvdW50cygpO1xuICBjb25zdCB0b3RhbEV4cGVjdGVkID0gT2JqZWN0LnByb3RvdHlwZS5oYXNPd25Qcm9wZXJ0eS5jYWxsKHByb3ZpZGVyQ291bnRzLCBpb2NUeXBlKVxuICAgID8gKHByb3ZpZGVyQ291bnRzW2lvY1R5cGVdID8/IDApXG4gICAgOiAwO1xuICBjb25zdCByZW1haW5pbmcgPSB0b3RhbEV4cGVjdGVkIC0gcmVjZWl2ZWRDb3VudDtcblxuICBpZiAocmVtYWluaW5nIDw9IDApIHtcbiAgICAvLyBBbGwgcHJvdmlkZXJzIGFjY291bnRlZCBmb3IgXHUyMDE0IHJlbW92ZSB3YWl0aW5nIGluZGljYXRvciBpZiBwcmVzZW50XG4gICAgY29uc3QgZXhpc3RpbmdJbmRpY2F0b3IgPSBzbG90LnF1ZXJ5U2VsZWN0b3IoXCIuZW5yaWNobWVudC13YWl0aW5nLXRleHRcIik7XG4gICAgaWYgKGV4aXN0aW5nSW5kaWNhdG9yKSB7XG4gICAgICBzbG90LnJlbW92ZUNoaWxkKGV4aXN0aW5nSW5kaWNhdG9yKTtcbiAgICB9XG4gICAgcmV0dXJuO1xuICB9XG5cbiAgLy8gRmluZCBvciBjcmVhdGUgdGhlIHdhaXRpbmcgaW5kaWNhdG9yIHNwYW5cbiAgbGV0IGluZGljYXRvciA9IHNsb3QucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIuZW5yaWNobWVudC13YWl0aW5nLXRleHRcIik7XG4gIGlmICghaW5kaWNhdG9yKSB7XG4gICAgaW5kaWNhdG9yID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gICAgaW5kaWNhdG9yLmNsYXNzTmFtZSA9IFwiZW5yaWNobWVudC13YWl0aW5nLXRleHQgZW5yaWNobWVudC1wZW5kaW5nLXRleHRcIjtcbiAgICBzbG90LmFwcGVuZENoaWxkKGluZGljYXRvcik7XG4gIH1cbiAgaW5kaWNhdG9yLnRleHRDb250ZW50ID0gcmVtYWluaW5nICsgXCIgcHJvdmlkZXJcIiArIChyZW1haW5pbmcgIT09IDEgPyBcInNcIiA6IFwiXCIpICsgXCIgc3RpbGwgbG9hZGluZy4uLlwiO1xufVxuXG4vKipcbiAqIFNob3cgYSB3YXJuaW5nIGJhbm5lciBmb3IgcmF0ZS1saW1pdCBvciBhdXRoZW50aWNhdGlvbiBlcnJvcnMuXG4gKiBTb3VyY2U6IG1haW4uanMgc2hvd0VucmljaFdhcm5pbmcoKSAobGluZXMgNjA1LTYxMSkuXG4gKi9cbmZ1bmN0aW9uIHNob3dFbnJpY2hXYXJuaW5nKG1lc3NhZ2U6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCBiYW5uZXIgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcImVucmljaC13YXJuaW5nXCIpO1xuICBpZiAoIWJhbm5lcikgcmV0dXJuO1xuICBiYW5uZXIuc3R5bGUuZGlzcGxheSA9IFwiYmxvY2tcIjtcbiAgLy8gVXNlIHRleHRDb250ZW50IHRvIHNhZmVseSBzZXQgdGhlIHdhcm5pbmcgbWVzc2FnZSAoU0VDLTA4KVxuICBiYW5uZXIudGV4dENvbnRlbnQgPSBcIldhcm5pbmc6IFwiICsgbWVzc2FnZSArIFwiIENvbnNpZGVyIHVzaW5nIG9mZmxpbmUgbW9kZSBvciBjaGVja2luZyB5b3VyIEFQSSBrZXkgaW4gU2V0dGluZ3MuXCI7XG59XG5cbi8qKlxuICogTWFyayBlbnJpY2htZW50IGNvbXBsZXRlOiBhZGQgLmNvbXBsZXRlIGNsYXNzIHRvIHByb2dyZXNzIGNvbnRhaW5lcixcbiAqIHVwZGF0ZSB0ZXh0LCBhbmQgZW5hYmxlIHRoZSBleHBvcnQgYnV0dG9uLlxuICogU291cmNlOiBtYWluLmpzIG1hcmtFbnJpY2htZW50Q29tcGxldGUoKSAobGluZXMgNTkwLTYwMykuXG4gKi9cbmZ1bmN0aW9uIG1hcmtFbnJpY2htZW50Q29tcGxldGUoKTogdm9pZCB7XG4gIGNvbnN0IGNvbnRhaW5lciA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZW5yaWNoLXByb2dyZXNzXCIpO1xuICBpZiAoY29udGFpbmVyKSB7XG4gICAgY29udGFpbmVyLmNsYXNzTGlzdC5hZGQoXCJjb21wbGV0ZVwiKTtcbiAgfVxuICBjb25zdCB0ZXh0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJlbnJpY2gtcHJvZ3Jlc3MtdGV4dFwiKTtcbiAgaWYgKHRleHQpIHtcbiAgICB0ZXh0LnRleHRDb250ZW50ID0gXCJFbnJpY2htZW50IGNvbXBsZXRlXCI7XG4gIH1cbiAgY29uc3QgZXhwb3J0QnRuID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJleHBvcnQtYnRuXCIpO1xuICBpZiAoZXhwb3J0QnRuKSB7XG4gICAgZXhwb3J0QnRuLnJlbW92ZUF0dHJpYnV0ZShcImRpc2FibGVkXCIpO1xuICB9XG59XG5cbi8qKlxuICogUmVuZGVyIGEgc2luZ2xlIGVucmljaG1lbnQgcmVzdWx0IGl0ZW0gaW50byB0aGUgYXBwcm9wcmlhdGUgSU9DIGNhcmQgc2xvdC5cbiAqIEhhbmRsZXMgYm90aCBcInJlc3VsdFwiIGFuZCBcImVycm9yXCIgZGlzY3JpbWluYXRlZCB1bmlvbiBicmFuY2hlcy5cbiAqXG4gKiBOZXcgYmVoYXZpb3IgKFBsYW4gMDIpOlxuICogLSBBTEwgcmVzdWx0cyBnbyBpbnRvIC5lbnJpY2htZW50LWRldGFpbHMgY29udGFpbmVyIChubyBkaXJlY3Qgc2xvdCBhcHBlbmQpXG4gKiAtIFN1bW1hcnkgcm93IHVwZGF0ZWQgb24gZWFjaCByZXN1bHQ6IHdvcnN0IHZlcmRpY3QgYmFkZ2UgKyBhdHRyaWJ1dGlvbiArIGNvbnNlbnN1cyBiYWRnZVxuICogLSBEZXRhaWwgcm93cyBzb3J0ZWQgYnkgc2V2ZXJpdHkgZGVzY2VuZGluZyAoZGVib3VuY2VkIDEwMG1zKVxuICogLSAuZW5yaWNobWVudC1zbG90LS1sb2FkZWQgY2xhc3MgYWRkZWQgb24gZmlyc3QgcmVzdWx0IChyZXZlYWxzIGNoZXZyb24gdmlhIENTUylcbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgcmVuZGVyRW5yaWNobWVudFJlc3VsdCgpIChsaW5lcyA0NDMtNTQwKS5cbiAqL1xuZnVuY3Rpb24gcmVuZGVyRW5yaWNobWVudFJlc3VsdChcbiAgcmVzdWx0OiBFbnJpY2htZW50SXRlbSxcbiAgaW9jVmVyZGljdHM6IFJlY29yZDxzdHJpbmcsIFZlcmRpY3RFbnRyeVtdPixcbiAgaW9jUmVzdWx0Q291bnRzOiBSZWNvcmQ8c3RyaW5nLCBudW1iZXI+XG4pOiB2b2lkIHtcbiAgLy8gRmluZCB0aGUgY2FyZCBmb3IgdGhpcyBJT0MgdmFsdWVcbiAgY29uc3QgY2FyZCA9IGZpbmRDYXJkRm9ySW9jKHJlc3VsdC5pb2NfdmFsdWUpO1xuICBpZiAoIWNhcmQpIHJldHVybjtcblxuICBjb25zdCBzbG90ID0gY2FyZC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcIi5lbnJpY2htZW50LXNsb3RcIik7XG4gIGlmICghc2xvdCkgcmV0dXJuO1xuXG4gIC8vIENvbnRleHQgcHJvdmlkZXJzIChJUCBDb250ZXh0LCBETlMgUmVjb3JkcywgQ2VydCBIaXN0b3J5KSBhcmUgcHVyZWx5IGluZm9ybWF0aW9uYWwgXHUyMDE0XG4gIC8vIHNlcGFyYXRlIHJlbmRlcmluZyBwYXRoLiBObyBWZXJkaWN0RW50cnkgYWNjdW11bGF0aW9uLCBubyBjb25zZW5zdXMvYXR0cmlidXRpb24sXG4gIC8vIG5vIGNhcmQgdmVyZGljdCB1cGRhdGUuXG4gIGlmIChDT05URVhUX1BST1ZJREVSUy5oYXMocmVzdWx0LnByb3ZpZGVyKSkge1xuICAgIC8vIFJlbW92ZSBzcGlubmVyIG9uIGZpcnN0IHJlc3VsdFxuICAgIGNvbnN0IHNwaW5uZXJXcmFwcGVyID0gc2xvdC5xdWVyeVNlbGVjdG9yKFwiLnNwaW5uZXItd3JhcHBlclwiKTtcbiAgICBpZiAoc3Bpbm5lcldyYXBwZXIpIHNsb3QucmVtb3ZlQ2hpbGQoc3Bpbm5lcldyYXBwZXIpO1xuICAgIHNsb3QuY2xhc3NMaXN0LmFkZChcImVucmljaG1lbnQtc2xvdC0tbG9hZGVkXCIpO1xuXG4gICAgLy8gVHJhY2sgcmVzdWx0IGNvdW50IGZvciBwZW5kaW5nIGluZGljYXRvclxuICAgIGlvY1Jlc3VsdENvdW50c1tyZXN1bHQuaW9jX3ZhbHVlXSA9IChpb2NSZXN1bHRDb3VudHNbcmVzdWx0LmlvY192YWx1ZV0gPz8gMCkgKyAxO1xuXG4gICAgLy8gUmVuZGVyIGNvbnRleHQgcm93IGFuZCBQUkVQRU5EIHRvIGRldGFpbHMgY29udGFpbmVyIChmaXJzdCBwb3NpdGlvbilcbiAgICBjb25zdCBkZXRhaWxzQ29udGFpbmVyID0gc2xvdC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcIi5lbnJpY2htZW50LWRldGFpbHNcIik7XG4gICAgaWYgKGRldGFpbHNDb250YWluZXIgJiYgcmVzdWx0LnR5cGUgPT09IFwicmVzdWx0XCIpIHtcbiAgICAgIGNvbnN0IGNvbnRleHRSb3cgPSBjcmVhdGVDb250ZXh0Um93KHJlc3VsdCk7XG4gICAgICBkZXRhaWxzQ29udGFpbmVyLmluc2VydEJlZm9yZShjb250ZXh0Um93LCBkZXRhaWxzQ29udGFpbmVyLmZpcnN0Q2hpbGQpO1xuICAgIH1cblxuICAgIC8vIFVwZGF0ZSBwZW5kaW5nIGluZGljYXRvclxuICAgIHVwZGF0ZVBlbmRpbmdJbmRpY2F0b3Ioc2xvdCwgY2FyZCwgaW9jUmVzdWx0Q291bnRzW3Jlc3VsdC5pb2NfdmFsdWVdID8/IDEpO1xuICAgIHJldHVybjsgLy8gU2tpcCBhbGwgdmVyZGljdC9zdW1tYXJ5L3NvcnQvZGFzaGJvYXJkIGxvZ2ljXG4gIH1cblxuICAvLyBSZW1vdmUgc3Bpbm5lciB3cmFwcGVyIG9uIGZpcnN0IHJlc3VsdCBmb3IgdGhpcyBJT0NcbiAgY29uc3Qgc3Bpbm5lcldyYXBwZXIgPSBzbG90LnF1ZXJ5U2VsZWN0b3IoXCIuc3Bpbm5lci13cmFwcGVyXCIpO1xuICBpZiAoc3Bpbm5lcldyYXBwZXIpIHtcbiAgICBzbG90LnJlbW92ZUNoaWxkKHNwaW5uZXJXcmFwcGVyKTtcbiAgfVxuXG4gIC8vIEFkZCAuZW5yaWNobWVudC1zbG90LS1sb2FkZWQgY2xhc3MgXHUyMDE0IHRyaWdnZXJzIGNoZXZyb24gdmlzaWJpbGl0eSB2aWEgQ1NTIGd1YXJkXG4gIHNsb3QuY2xhc3NMaXN0LmFkZChcImVucmljaG1lbnQtc2xvdC0tbG9hZGVkXCIpO1xuXG4gIC8vIFRyYWNrIHJlY2VpdmVkIGNvdW50IGZvciB0aGlzIElPQ1xuICBpb2NSZXN1bHRDb3VudHNbcmVzdWx0LmlvY192YWx1ZV0gPSAoaW9jUmVzdWx0Q291bnRzW3Jlc3VsdC5pb2NfdmFsdWVdID8/IDApICsgMTtcbiAgY29uc3QgcmVjZWl2ZWRDb3VudCA9IGlvY1Jlc3VsdENvdW50c1tyZXN1bHQuaW9jX3ZhbHVlXSA/PyAxO1xuXG4gIC8vIERldGVybWluZSB2ZXJkaWN0IGFuZCBzdGF0VGV4dFxuICBsZXQgdmVyZGljdDogVmVyZGljdEtleTtcbiAgbGV0IHN0YXRUZXh0OiBzdHJpbmc7XG4gIGxldCBzdW1tYXJ5VGV4dDogc3RyaW5nO1xuICBsZXQgZGV0ZWN0aW9uQ291bnQgPSAwO1xuICBsZXQgdG90YWxFbmdpbmVzID0gMDtcblxuICBpZiAocmVzdWx0LnR5cGUgPT09IFwicmVzdWx0XCIpIHtcbiAgICB2ZXJkaWN0ID0gcmVzdWx0LnZlcmRpY3Q7XG4gICAgZGV0ZWN0aW9uQ291bnQgPSByZXN1bHQuZGV0ZWN0aW9uX2NvdW50O1xuICAgIHRvdGFsRW5naW5lcyA9IHJlc3VsdC50b3RhbF9lbmdpbmVzO1xuXG4gICAgaWYgKHZlcmRpY3QgPT09IFwibWFsaWNpb3VzXCIpIHtcbiAgICAgIHN0YXRUZXh0ID0gcmVzdWx0LmRldGVjdGlvbl9jb3VudCArIFwiL1wiICsgcmVzdWx0LnRvdGFsX2VuZ2luZXMgKyBcIiBlbmdpbmVzXCI7XG4gICAgfSBlbHNlIGlmICh2ZXJkaWN0ID09PSBcInN1c3BpY2lvdXNcIikge1xuICAgICAgc3RhdFRleHQgPVxuICAgICAgICByZXN1bHQudG90YWxfZW5naW5lcyA+IDFcbiAgICAgICAgICA/IHJlc3VsdC5kZXRlY3Rpb25fY291bnQgKyBcIi9cIiArIHJlc3VsdC50b3RhbF9lbmdpbmVzICsgXCIgZW5naW5lc1wiXG4gICAgICAgICAgOiBcIlN1c3BpY2lvdXNcIjtcbiAgICB9IGVsc2UgaWYgKHZlcmRpY3QgPT09IFwiY2xlYW5cIikge1xuICAgICAgc3RhdFRleHQgPSBcIkNsZWFuLCBcIiArIHJlc3VsdC50b3RhbF9lbmdpbmVzICsgXCIgZW5naW5lc1wiO1xuICAgIH0gZWxzZSBpZiAodmVyZGljdCA9PT0gXCJrbm93bl9nb29kXCIpIHtcbiAgICAgIHN0YXRUZXh0ID0gXCJOU1JMIG1hdGNoXCI7XG4gICAgfSBlbHNlIHtcbiAgICAgIC8vIG5vX2RhdGFcbiAgICAgIHN0YXRUZXh0ID0gXCJOb3QgaW4gZGF0YWJhc2VcIjtcbiAgICB9XG5cbiAgICBjb25zdCBzY2FuRGF0ZVN0ciA9IGZvcm1hdERhdGUocmVzdWx0LnNjYW5fZGF0ZSk7XG4gICAgc3VtbWFyeVRleHQgPVxuICAgICAgcmVzdWx0LnByb3ZpZGVyICtcbiAgICAgIFwiOiBcIiArXG4gICAgICB2ZXJkaWN0ICtcbiAgICAgIFwiIChcIiArXG4gICAgICBzdGF0VGV4dCArXG4gICAgICAoc2NhbkRhdGVTdHIgPyBcIiwgc2Nhbm5lZCBcIiArIHNjYW5EYXRlU3RyIDogXCJcIikgK1xuICAgICAgXCIpXCI7XG4gIH0gZWxzZSB7XG4gICAgLy8gRXJyb3IgcmVzdWx0XG4gICAgdmVyZGljdCA9IFwiZXJyb3JcIjtcbiAgICBzdGF0VGV4dCA9IHJlc3VsdC5lcnJvcjtcbiAgICBzdW1tYXJ5VGV4dCA9IHJlc3VsdC5wcm92aWRlciArIFwiOiBlcnJvciwgXCIgKyByZXN1bHQuZXJyb3I7XG4gIH1cblxuICAvLyBQdXNoIHRvIGlvY1ZlcmRpY3RzIHdpdGggZXh0ZW5kZWQgZmllbGRzXG4gIGNvbnN0IGVudHJpZXMgPSBpb2NWZXJkaWN0c1tyZXN1bHQuaW9jX3ZhbHVlXSA/PyBbXTtcbiAgaW9jVmVyZGljdHNbcmVzdWx0LmlvY192YWx1ZV0gPSBlbnRyaWVzO1xuICBlbnRyaWVzLnB1c2goeyBwcm92aWRlcjogcmVzdWx0LnByb3ZpZGVyLCB2ZXJkaWN0LCBzdW1tYXJ5VGV4dCwgZGV0ZWN0aW9uQ291bnQsIHRvdGFsRW5naW5lcywgc3RhdFRleHQgfSk7XG5cbiAgLy8gQnVpbGQgZGV0YWlsIHJvdyBhbmQgYXBwZW5kIHRvIC5lbnJpY2htZW50LWRldGFpbHMgY29udGFpbmVyXG4gIGNvbnN0IGRldGFpbHNDb250YWluZXIgPSBzbG90LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLmVucmljaG1lbnQtZGV0YWlsc1wiKTtcbiAgaWYgKGRldGFpbHNDb250YWluZXIpIHtcbiAgICBjb25zdCBkZXRhaWxSb3cgPSBjcmVhdGVEZXRhaWxSb3cocmVzdWx0LnByb3ZpZGVyLCB2ZXJkaWN0LCBzdGF0VGV4dCwgcmVzdWx0KTtcbiAgICBkZXRhaWxzQ29udGFpbmVyLmFwcGVuZENoaWxkKGRldGFpbFJvdyk7XG4gICAgc29ydERldGFpbFJvd3MoZGV0YWlsc0NvbnRhaW5lciwgcmVzdWx0LmlvY192YWx1ZSk7XG4gIH1cblxuICAvLyBVcGRhdGUgc3VtbWFyeSByb3cgKHdvcnN0IHZlcmRpY3QgKyBhdHRyaWJ1dGlvbiArIGNvbnNlbnN1cylcbiAgdXBkYXRlU3VtbWFyeVJvdyhzbG90LCByZXN1bHQuaW9jX3ZhbHVlLCBpb2NWZXJkaWN0cyk7XG5cbiAgLy8gVXBkYXRlIHBlbmRpbmcgaW5kaWNhdG9yIGZvciByZW1haW5pbmcgcHJvdmlkZXJzXG4gIHVwZGF0ZVBlbmRpbmdJbmRpY2F0b3Ioc2xvdCwgY2FyZCwgcmVjZWl2ZWRDb3VudCk7XG5cbiAgLy8gQ29tcHV0ZSB3b3JzdCB2ZXJkaWN0IGZvciB0aGlzIElPQ1xuICBjb25zdCB3b3JzdFZlcmRpY3QgPSBjb21wdXRlV29yc3RWZXJkaWN0KGlvY1ZlcmRpY3RzW3Jlc3VsdC5pb2NfdmFsdWVdID8/IFtdKTtcblxuICAvLyBVcGRhdGUgY2FyZCB2ZXJkaWN0LCBkYXNoYm9hcmQsIGFuZCBzb3J0XG4gIHVwZGF0ZUNhcmRWZXJkaWN0KHJlc3VsdC5pb2NfdmFsdWUsIHdvcnN0VmVyZGljdCk7XG4gIHVwZGF0ZURhc2hib2FyZENvdW50cygpO1xuICBzb3J0Q2FyZHNCeVNldmVyaXR5KCk7XG5cbiAgLy8gVXBkYXRlIGNvcHkgYnV0dG9uIHdpdGggd29yc3QgdmVyZGljdCBhY3Jvc3MgYWxsIHByb3ZpZGVycyBmb3IgdGhpcyBJT0NcbiAgdXBkYXRlQ29weUJ1dHRvbldvcnN0VmVyZGljdChyZXN1bHQuaW9jX3ZhbHVlLCBpb2NWZXJkaWN0cyk7XG59XG5cbi8qKlxuICogV2lyZSBleHBhbmQvY29sbGFwc2UgdG9nZ2xlIGZvciBhbGwgLmNoZXZyb24tdG9nZ2xlIGJ1dHRvbnMgb24gdGhlIHBhZ2UuXG4gKiBDYWxsZWQgb25jZSBmcm9tIGluaXQoKS4gQ2xpY2sgbGlzdGVuZXIgdG9nZ2xlcyAuaXMtb3BlbiBvbiB0aGUgc2libGluZ1xuICogLmVucmljaG1lbnQtZGV0YWlscyBjb250YWluZXIgYW5kIHNldHMgYXJpYS1leHBhbmRlZCBhY2NvcmRpbmdseS5cbiAqIE11bHRpcGxlIGNhcmRzIGNhbiBiZSBpbmRlcGVuZGVudGx5IG9wZW5lZCBcdTIwMTQgbm8gY29sbGFwc2Utb3RoZXJzIGxvZ2ljLlxuICovXG5mdW5jdGlvbiB3aXJlRXhwYW5kVG9nZ2xlcygpOiB2b2lkIHtcbiAgY29uc3QgdG9nZ2xlcyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmNoZXZyb24tdG9nZ2xlXCIpO1xuICB0b2dnbGVzLmZvckVhY2goKHRvZ2dsZSkgPT4ge1xuICAgIHRvZ2dsZS5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgKCkgPT4ge1xuICAgICAgY29uc3QgZGV0YWlscyA9IHRvZ2dsZS5uZXh0RWxlbWVudFNpYmxpbmcgYXMgSFRNTEVsZW1lbnQgfCBudWxsO1xuICAgICAgaWYgKCFkZXRhaWxzIHx8ICFkZXRhaWxzLmNsYXNzTGlzdC5jb250YWlucyhcImVucmljaG1lbnQtZGV0YWlsc1wiKSkgcmV0dXJuO1xuICAgICAgY29uc3QgaXNPcGVuID0gZGV0YWlscy5jbGFzc0xpc3QudG9nZ2xlKFwiaXMtb3BlblwiKTtcbiAgICAgIHRvZ2dsZS5jbGFzc0xpc3QudG9nZ2xlKFwiaXMtb3BlblwiLCBpc09wZW4pO1xuICAgICAgdG9nZ2xlLnNldEF0dHJpYnV0ZShcImFyaWEtZXhwYW5kZWRcIiwgU3RyaW5nKGlzT3BlbikpO1xuICAgIH0pO1xuICB9KTtcbn1cblxuLy8gLS0tLSBQcml2YXRlIGluaXQgaGVscGVycyAtLS0tXG5cbi8qKlxuICogV2lyZSB0aGUgZXhwb3J0IGRyb3Bkb3duIHdpdGggSlNPTiwgQ1NWLCBhbmQgY29weS1hbGwtSU9DcyBvcHRpb25zLlxuICovXG5mdW5jdGlvbiBpbml0RXhwb3J0QnV0dG9uKCk6IHZvaWQge1xuICBjb25zdCBleHBvcnRCdG4gPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcImV4cG9ydC1idG5cIik7XG4gIGNvbnN0IGRyb3Bkb3duID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJleHBvcnQtZHJvcGRvd25cIik7XG4gIGlmICghZXhwb3J0QnRuIHx8ICFkcm9wZG93bikgcmV0dXJuO1xuXG4gIGV4cG9ydEJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgIGNvbnN0IGlzVmlzaWJsZSA9IGRyb3Bkb3duLnN0eWxlLmRpc3BsYXkgIT09IFwibm9uZVwiO1xuICAgIGRyb3Bkb3duLnN0eWxlLmRpc3BsYXkgPSBpc1Zpc2libGUgPyBcIm5vbmVcIiA6IFwiXCI7XG4gIH0pO1xuXG4gIC8vIENsb3NlIGRyb3Bkb3duIHdoZW4gY2xpY2tpbmcgb3V0c2lkZVxuICBkb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKGUpIHtcbiAgICBjb25zdCB0YXJnZXQgPSBlLnRhcmdldCBhcyBIVE1MRWxlbWVudDtcbiAgICBpZiAoIXRhcmdldC5jbG9zZXN0KFwiLmV4cG9ydC1ncm91cFwiKSkge1xuICAgICAgZHJvcGRvd24uc3R5bGUuZGlzcGxheSA9IFwibm9uZVwiO1xuICAgIH1cbiAgfSk7XG5cbiAgY29uc3QgYnV0dG9ucyA9IGRyb3Bkb3duLnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiW2RhdGEtZXhwb3J0XVwiKTtcbiAgYnV0dG9ucy5mb3JFYWNoKGZ1bmN0aW9uIChidG4pIHtcbiAgICBidG4uYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsIGZ1bmN0aW9uICgpIHtcbiAgICAgIGNvbnN0IGFjdGlvbiA9IGJ0bi5nZXRBdHRyaWJ1dGUoXCJkYXRhLWV4cG9ydFwiKTtcbiAgICAgIGlmIChhY3Rpb24gPT09IFwianNvblwiKSB7XG4gICAgICAgIGV4cG9ydEpTT04oYWxsUmVzdWx0cyk7XG4gICAgICB9IGVsc2UgaWYgKGFjdGlvbiA9PT0gXCJjc3ZcIikge1xuICAgICAgICBleHBvcnRDU1YoYWxsUmVzdWx0cyk7XG4gICAgICB9IGVsc2UgaWYgKGFjdGlvbiA9PT0gXCJpb2NzXCIpIHtcbiAgICAgICAgY29weUFsbElPQ3MoYnRuKTtcbiAgICAgIH1cbiAgICAgIGRyb3Bkb3duLnN0eWxlLmRpc3BsYXkgPSBcIm5vbmVcIjtcbiAgICB9KTtcbiAgfSk7XG59XG5cbi8vIC0tLS0gUHVibGljIEFQSSAtLS0tXG5cbi8qKlxuICogSW5pdGlhbGlzZSB0aGUgZW5yaWNobWVudCBwb2xsaW5nIG1vZHVsZS5cbiAqXG4gKiBHdWFyZHMgb24gLnBhZ2UtcmVzdWx0cyBwcmVzZW5jZSBhbmQgZGF0YS1tb2RlPVwib25saW5lXCIgXHUyMDE0IHJldHVybnMgZWFybHlcbiAqIG9uIG9mZmxpbmUgbW9kZSBvciB3aGVuIGVucmljaG1lbnQgVUkgZWxlbWVudHMgYXJlIGFic2VudC5cbiAqXG4gKiBXaXJlcyBjaGV2cm9uIGV4cGFuZC9jb2xsYXBzZSB0b2dnbGVzIG9uY2UgYXQgaW5pdCB0aW1lIChiZWZvcmUgcG9sbGluZ1xuICogc3RhcnRzKSBzbyB0aGV5IHdvcmsgcmVnYXJkbGVzcyBvZiB3aGVuIHJlc3VsdHMgcG9wdWxhdGUgZGV0YWlscy5cbiAqXG4gKiBTdGFydHMgYSA3NTBtcyBwb2xsaW5nIGludGVydmFsIGZvciAvZW5yaWNobWVudC9zdGF0dXMvPGpvYl9pZD4sXG4gKiByZW5kZXJzIGluY3JlbWVudGFsIHJlc3VsdHMsIHNob3dzIHdhcm5pbmcgYmFubmVycyBmb3IgZXJyb3JzLCBhbmRcbiAqIG1hcmtzIGVucmljaG1lbnQgY29tcGxldGUgd2hlbiBhbGwgdGFza3MgYXJlIGRvbmUuXG4gKlxuICogU291cmNlOiBtYWluLmpzIGluaXRFbnJpY2htZW50UG9sbGluZygpIChsaW5lcyAzMTYtMzczKSArXG4gKiAgICAgICAgIGluaXRFeHBvcnRCdXR0b24oKSAobGluZXMgNjE1LTY0MykuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBjb25zdCBwYWdlUmVzdWx0cyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLnBhZ2UtcmVzdWx0c1wiKTtcbiAgaWYgKCFwYWdlUmVzdWx0cykgcmV0dXJuO1xuXG4gIGNvbnN0IGpvYklkID0gYXR0cihwYWdlUmVzdWx0cywgXCJkYXRhLWpvYi1pZFwiKTtcbiAgY29uc3QgbW9kZSA9IGF0dHIocGFnZVJlc3VsdHMsIFwiZGF0YS1tb2RlXCIpO1xuXG4gIGlmICgham9iSWQgfHwgbW9kZSAhPT0gXCJvbmxpbmVcIikgcmV0dXJuO1xuXG4gIC8vIFdpcmUgZXhwYW5kL2NvbGxhcHNlIHRvZ2dsZXMgb25jZSBhdCBpbml0IChiZWZvcmUgcG9sbGluZyBzdGFydHMpXG4gIHdpcmVFeHBhbmRUb2dnbGVzKCk7XG5cbiAgLy8gRGVkdXAga2V5OiBcImlvY192YWx1ZXxwcm92aWRlclwiIFx1MjAxNCBlYWNoIHByb3ZpZGVyIHJlc3VsdCBwZXIgSU9DIHJlbmRlcmVkIG9uY2VcbiAgY29uc3QgcmVuZGVyZWQ6IFJlY29yZDxzdHJpbmcsIGJvb2xlYW4+ID0ge307XG5cbiAgLy8gUGVyLUlPQyB2ZXJkaWN0IHRyYWNraW5nIGZvciB3b3JzdC12ZXJkaWN0IGNvcHkvZXhwb3J0IGNvbXB1dGF0aW9uXG4gIC8vIGlvY1ZlcmRpY3RzW2lvY192YWx1ZV0gPSBbe3Byb3ZpZGVyLCB2ZXJkaWN0LCBzdW1tYXJ5VGV4dCwgZGV0ZWN0aW9uQ291bnQsIHRvdGFsRW5naW5lcywgc3RhdFRleHR9XVxuICBjb25zdCBpb2NWZXJkaWN0czogUmVjb3JkPHN0cmluZywgVmVyZGljdEVudHJ5W10+ID0ge307XG5cbiAgLy8gUGVyLUlPQyByZXN1bHQgY291bnQgdHJhY2tpbmcgZm9yIHBlbmRpbmcgaW5kaWNhdG9yXG4gIGNvbnN0IGlvY1Jlc3VsdENvdW50czogUmVjb3JkPHN0cmluZywgbnVtYmVyPiA9IHt9O1xuXG4gIC8vIFVzZSBSZXR1cm5UeXBlPHR5cGVvZiBzZXRJbnRlcnZhbD4gdG8gYXZvaWQgTm9kZUpTLlRpbWVvdXQgY29uZmxpY3RcbiAgY29uc3QgaW50ZXJ2YWxJZDogUmV0dXJuVHlwZTx0eXBlb2Ygc2V0SW50ZXJ2YWw+ID0gc2V0SW50ZXJ2YWwoZnVuY3Rpb24gKCkge1xuICAgIGZldGNoKFwiL2VucmljaG1lbnQvc3RhdHVzL1wiICsgam9iSWQpXG4gICAgICAudGhlbihmdW5jdGlvbiAocmVzcCkge1xuICAgICAgICBpZiAoIXJlc3Aub2spIHJldHVybiBudWxsO1xuICAgICAgICByZXR1cm4gcmVzcC5qc29uKCkgYXMgUHJvbWlzZTxFbnJpY2htZW50U3RhdHVzPjtcbiAgICAgIH0pXG4gICAgICAudGhlbihmdW5jdGlvbiAoZGF0YSkge1xuICAgICAgICBpZiAoIWRhdGEpIHJldHVybjtcblxuICAgICAgICB1cGRhdGVQcm9ncmVzc0JhcihkYXRhLmRvbmUsIGRhdGEudG90YWwpO1xuXG4gICAgICAgIC8vIFJlbmRlciBhbnkgbmV3IHJlc3VsdHMgbm90IHlldCBkaXNwbGF5ZWQsIGFuZCBjaGVjayBmb3Igd2FybmluZ3NcbiAgICAgICAgY29uc3QgcmVzdWx0cyA9IGRhdGEucmVzdWx0cztcbiAgICAgICAgZm9yIChsZXQgaSA9IDA7IGkgPCByZXN1bHRzLmxlbmd0aDsgaSsrKSB7XG4gICAgICAgICAgY29uc3QgcmVzdWx0ID0gcmVzdWx0c1tpXTtcbiAgICAgICAgICBpZiAoIXJlc3VsdCkgY29udGludWU7XG4gICAgICAgICAgY29uc3QgZGVkdXBLZXkgPSByZXN1bHQuaW9jX3ZhbHVlICsgXCJ8XCIgKyByZXN1bHQucHJvdmlkZXI7XG4gICAgICAgICAgaWYgKCFyZW5kZXJlZFtkZWR1cEtleV0pIHtcbiAgICAgICAgICAgIHJlbmRlcmVkW2RlZHVwS2V5XSA9IHRydWU7XG4gICAgICAgICAgICBhbGxSZXN1bHRzLnB1c2gocmVzdWx0KTtcbiAgICAgICAgICAgIHJlbmRlckVucmljaG1lbnRSZXN1bHQocmVzdWx0LCBpb2NWZXJkaWN0cywgaW9jUmVzdWx0Q291bnRzKTtcbiAgICAgICAgICB9XG5cbiAgICAgICAgICAvLyBTaG93IHdhcm5pbmcgYmFubmVyIGZvciByYXRlLWxpbWl0IG9yIGF1dGggZXJyb3JzXG4gICAgICAgICAgaWYgKHJlc3VsdC50eXBlID09PSBcImVycm9yXCIgJiYgcmVzdWx0LmVycm9yKSB7XG4gICAgICAgICAgICBjb25zdCBlcnJMb3dlciA9IHJlc3VsdC5lcnJvci50b0xvd2VyQ2FzZSgpO1xuICAgICAgICAgICAgaWYgKFxuICAgICAgICAgICAgICBlcnJMb3dlci5pbmRleE9mKFwicmF0ZSBsaW1pdFwiKSAhPT0gLTEgfHxcbiAgICAgICAgICAgICAgZXJyTG93ZXIuaW5kZXhPZihcIjQyOVwiKSAhPT0gLTFcbiAgICAgICAgICAgICkge1xuICAgICAgICAgICAgICBzaG93RW5yaWNoV2FybmluZyhcIlJhdGUgbGltaXQgcmVhY2hlZCBmb3IgXCIgKyByZXN1bHQucHJvdmlkZXIgKyBcIi5cIik7XG4gICAgICAgICAgICB9IGVsc2UgaWYgKFxuICAgICAgICAgICAgICBlcnJMb3dlci5pbmRleE9mKFwiYXV0aGVudGljYXRpb25cIikgIT09IC0xIHx8XG4gICAgICAgICAgICAgIGVyckxvd2VyLmluZGV4T2YoXCI0MDFcIikgIT09IC0xIHx8XG4gICAgICAgICAgICAgIGVyckxvd2VyLmluZGV4T2YoXCI0MDNcIikgIT09IC0xXG4gICAgICAgICAgICApIHtcbiAgICAgICAgICAgICAgc2hvd0VucmljaFdhcm5pbmcoXG4gICAgICAgICAgICAgICAgXCJBdXRoZW50aWNhdGlvbiBlcnJvciBmb3IgXCIgK1xuICAgICAgICAgICAgICAgICAgcmVzdWx0LnByb3ZpZGVyICtcbiAgICAgICAgICAgICAgICAgIFwiLiBQbGVhc2UgY2hlY2sgeW91ciBBUEkga2V5IGluIFNldHRpbmdzLlwiXG4gICAgICAgICAgICAgICk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuICAgICAgICB9XG5cbiAgICAgICAgaWYgKGRhdGEuY29tcGxldGUpIHtcbiAgICAgICAgICBjbGVhckludGVydmFsKGludGVydmFsSWQpO1xuICAgICAgICAgIG1hcmtFbnJpY2htZW50Q29tcGxldGUoKTtcbiAgICAgICAgfVxuICAgICAgfSlcbiAgICAgIC5jYXRjaChmdW5jdGlvbiAoKSB7XG4gICAgICAgIC8vIEZldGNoIGVycm9yIFx1MjAxNCBzaWxlbnRseSBjb250aW51ZTsgcmV0cnkgb24gbmV4dCBpbnRlcnZhbCB0aWNrXG4gICAgICB9KTtcbiAgfSwgNzUwKTtcblxuICAvLyBXaXJlIHRoZSBleHBvcnQgYnV0dG9uXG4gIGluaXRFeHBvcnRCdXR0b24oKTtcbn1cbiIsICIvKipcbiAqIFNldHRpbmdzIHBhZ2UgbW9kdWxlIFx1MjAxNCBhY2NvcmRpb24gYW5kIEFQSSBrZXkgdG9nZ2xlcy5cbiAqL1xuXG4vKiogV2lyZSB1cCBhY2NvcmRpb24gc2VjdGlvbnMgXHUyMDE0IG9uZSBvcGVuIGF0IGEgdGltZS4gKi9cbmZ1bmN0aW9uIGluaXRBY2NvcmRpb24oKTogdm9pZCB7XG4gIGNvbnN0IHNlY3Rpb25zID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXG4gICAgXCIuc2V0dGluZ3Mtc2VjdGlvbltkYXRhLXByb3ZpZGVyXVwiXG4gICk7XG4gIGlmIChzZWN0aW9ucy5sZW5ndGggPT09IDApIHJldHVybjtcblxuICBmdW5jdGlvbiBleHBhbmRTZWN0aW9uKHNlY3Rpb246IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gICAgc2VjdGlvbnMuZm9yRWFjaCgocykgPT4ge1xuICAgICAgaWYgKHMgIT09IHNlY3Rpb24pIHtcbiAgICAgICAgcy5yZW1vdmVBdHRyaWJ1dGUoXCJkYXRhLWV4cGFuZGVkXCIpO1xuICAgICAgICBjb25zdCBidG4gPSBzLnF1ZXJ5U2VsZWN0b3IoXCIuYWNjb3JkaW9uLWhlYWRlclwiKTtcbiAgICAgICAgaWYgKGJ0bikgYnRuLnNldEF0dHJpYnV0ZShcImFyaWEtZXhwYW5kZWRcIiwgXCJmYWxzZVwiKTtcbiAgICAgIH1cbiAgICB9KTtcbiAgICBzZWN0aW9uLnNldEF0dHJpYnV0ZShcImRhdGEtZXhwYW5kZWRcIiwgXCJcIik7XG4gICAgY29uc3QgYnRuID0gc2VjdGlvbi5xdWVyeVNlbGVjdG9yKFwiLmFjY29yZGlvbi1oZWFkZXJcIik7XG4gICAgaWYgKGJ0bikgYnRuLnNldEF0dHJpYnV0ZShcImFyaWEtZXhwYW5kZWRcIiwgXCJ0cnVlXCIpO1xuICB9XG5cbiAgc2VjdGlvbnMuZm9yRWFjaCgoc2VjdGlvbikgPT4ge1xuICAgIGNvbnN0IGhlYWRlciA9IHNlY3Rpb24ucXVlcnlTZWxlY3RvcihcIi5hY2NvcmRpb24taGVhZGVyXCIpO1xuICAgIGlmICghaGVhZGVyKSByZXR1cm47XG4gICAgaGVhZGVyLmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCAoKSA9PiB7XG4gICAgICBpZiAoc2VjdGlvbi5oYXNBdHRyaWJ1dGUoXCJkYXRhLWV4cGFuZGVkXCIpKSB7XG4gICAgICAgIHNlY3Rpb24ucmVtb3ZlQXR0cmlidXRlKFwiZGF0YS1leHBhbmRlZFwiKTtcbiAgICAgICAgaGVhZGVyLnNldEF0dHJpYnV0ZShcImFyaWEtZXhwYW5kZWRcIiwgXCJmYWxzZVwiKTtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIGV4cGFuZFNlY3Rpb24oc2VjdGlvbik7XG4gICAgICB9XG4gICAgfSk7XG4gIH0pO1xuXG59XG5cbi8qKiBXaXJlIHVwIHBlci1wcm92aWRlciBBUEkga2V5IHNob3cvaGlkZSB0b2dnbGVzLiAqL1xuZnVuY3Rpb24gaW5pdEtleVRvZ2dsZXMoKTogdm9pZCB7XG4gIGNvbnN0IHNlY3Rpb25zID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbChcIi5zZXR0aW5ncy1zZWN0aW9uXCIpO1xuICBzZWN0aW9ucy5mb3JFYWNoKChzZWN0aW9uKSA9PiB7XG4gICAgY29uc3QgYnRuID0gc2VjdGlvbi5xdWVyeVNlbGVjdG9yKFxuICAgICAgXCJbZGF0YS1yb2xlPSd0b2dnbGUta2V5J11cIlxuICAgICkgYXMgSFRNTEJ1dHRvbkVsZW1lbnQgfCBudWxsO1xuICAgIGNvbnN0IGlucHV0ID0gc2VjdGlvbi5xdWVyeVNlbGVjdG9yKFxuICAgICAgXCJpbnB1dFt0eXBlPSdwYXNzd29yZCddLCBpbnB1dFt0eXBlPSd0ZXh0J11cIlxuICAgICkgYXMgSFRNTElucHV0RWxlbWVudCB8IG51bGw7XG4gICAgaWYgKCFidG4gfHwgIWlucHV0KSByZXR1cm47XG5cbiAgICBidG4uYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgIGlmIChpbnB1dC50eXBlID09PSBcInBhc3N3b3JkXCIpIHtcbiAgICAgICAgaW5wdXQudHlwZSA9IFwidGV4dFwiO1xuICAgICAgICBidG4udGV4dENvbnRlbnQgPSBcIkhpZGVcIjtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIGlucHV0LnR5cGUgPSBcInBhc3N3b3JkXCI7XG4gICAgICAgIGJ0bi50ZXh0Q29udGVudCA9IFwiU2hvd1wiO1xuICAgICAgfVxuICAgIH0pO1xuICB9KTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGluaXQoKTogdm9pZCB7XG4gIGluaXRBY2NvcmRpb24oKTtcbiAgaW5pdEtleVRvZ2dsZXMoKTtcbn1cbiIsICIvKipcbiAqIFVJIHV0aWxpdGllcyBtb2R1bGUgXHUyMDE0IHNjcm9sbC1hd2FyZSBmaWx0ZXIgYmFyIGFuZCBjYXJkIHN0YWdnZXIgYW5pbWF0aW9uLlxuICpcbiAqIEV4dHJhY3RlZCBmcm9tIG1haW4uanMgaW5pdFNjcm9sbEF3YXJlRmlsdGVyQmFyKCkgKGxpbmVzIDgxMS04MjYpXG4gKiBhbmQgaW5pdENhcmRTdGFnZ2VyKCkgKGxpbmVzIDgzMC04MzUpLlxuICovXG5cbi8qKlxuICogQWRkIHNjcm9sbCBsaXN0ZW5lciB0aGF0IHRvZ2dsZXMgXCJpcy1zY3JvbGxlZFwiIGNsYXNzIG9uIC5maWx0ZXItYmFyLXdyYXBwZXJcbiAqIG9uY2UgdGhlIHBhZ2Ugc2Nyb2xscyBwYXN0IDQwcHguXG4gKi9cbmZ1bmN0aW9uIGluaXRTY3JvbGxBd2FyZUZpbHRlckJhcigpOiB2b2lkIHtcbiAgY29uc3QgZmlsdGVyQmFyID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIuZmlsdGVyLWJhci13cmFwcGVyXCIpO1xuICBpZiAoIWZpbHRlckJhcikgcmV0dXJuO1xuXG4gIGxldCBzY3JvbGxlZCA9IGZhbHNlO1xuICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcihcbiAgICBcInNjcm9sbFwiLFxuICAgIGZ1bmN0aW9uICgpIHtcbiAgICAgIGNvbnN0IGlzU2Nyb2xsZWQgPSB3aW5kb3cuc2Nyb2xsWSA+IDQwO1xuICAgICAgaWYgKGlzU2Nyb2xsZWQgIT09IHNjcm9sbGVkKSB7XG4gICAgICAgIHNjcm9sbGVkID0gaXNTY3JvbGxlZDtcbiAgICAgICAgZmlsdGVyQmFyLmNsYXNzTGlzdC50b2dnbGUoXCJpcy1zY3JvbGxlZFwiLCBzY3JvbGxlZCk7XG4gICAgICB9XG4gICAgfSxcbiAgICB7IHBhc3NpdmU6IHRydWUgfVxuICApO1xufVxuXG4vKipcbiAqIFNldCAtLWNhcmQtaW5kZXggQ1NTIGN1c3RvbSBwcm9wZXJ0eSBvbiBlYWNoIC5pb2MtY2FyZCBlbGVtZW50LFxuICogY2FwcGVkIGF0IDE1IHRvIGxpbWl0IHN0YWdnZXIgZGVsYXkgb24gbG9uZyBsaXN0cy5cbiAqL1xuZnVuY3Rpb24gaW5pdENhcmRTdGFnZ2VyKCk6IHZvaWQge1xuICBjb25zdCBjYXJkcyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmlvYy1jYXJkXCIpO1xuICBjYXJkcy5mb3JFYWNoKChjYXJkLCBpKSA9PiB7XG4gICAgY2FyZC5zdHlsZS5zZXRQcm9wZXJ0eShcIi0tY2FyZC1pbmRleFwiLCBTdHJpbmcoTWF0aC5taW4oaSwgMTUpKSk7XG4gIH0pO1xufVxuXG4vKipcbiAqIEluaXRpYWxpc2UgYWxsIFVJIGVuaGFuY2VtZW50czogc2Nyb2xsLWF3YXJlIGZpbHRlciBiYXIgYW5kIGNhcmQgc3RhZ2dlci5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGluaXQoKTogdm9pZCB7XG4gIGluaXRTY3JvbGxBd2FyZUZpbHRlckJhcigpO1xuICBpbml0Q2FyZFN0YWdnZXIoKTtcbn1cbiIsICIvKipcbiAqIFNWRyByZWxhdGlvbnNoaXAgZ3JhcGggcmVuZGVyZXIgZm9yIHRoZSBJT0MgZGV0YWlsIHBhZ2UuXG4gKlxuICogUmVhZHMgZ3JhcGhfbm9kZXMgYW5kIGdyYXBoX2VkZ2VzIGZyb20gZGF0YSBhdHRyaWJ1dGVzIG9uIHRoZVxuICogI3JlbGF0aW9uc2hpcC1ncmFwaCBjb250YWluZXIsIHRoZW4gZHJhd3MgYSBodWItYW5kLXNwb2tlIFNWRyBkaWFncmFtXG4gKiB3aXRoIHRoZSBJT0MgYXQgdGhlIGNlbnRlciBhbmQgcHJvdmlkZXIgbm9kZXMgYXJyYW5nZWQgaW4gYSBjaXJjbGUgYXJvdW5kIGl0LlxuICpcbiAqIE5vZGVzIGFyZSBjb2xvcmVkIGJ5IHZlcmRpY3QgdG8gZ2l2ZSBpbnN0YW50IHZpc3VhbCB0cmlhZ2UgY29udGV4dC5cbiAqXG4gKiBTRUMtMDg6IEFsbCB0ZXh0IGNvbnRlbnQgdXNlcyBkb2N1bWVudC5jcmVhdGVUZXh0Tm9kZSgpIFx1MjAxNCBuZXZlciBpbm5lckhUTUxcbiAqIG9yIHRleHRDb250ZW50IG9uIGVsZW1lbnRzIHdpdGggY2hpbGRyZW4uIElPQyB2YWx1ZXMgYW5kIHByb3ZpZGVyIG5hbWVzXG4gKiBhcmUgcGFzc2VkIHRocm91Z2ggY3JlYXRlVGV4dE5vZGUgb25seSB0byBwcmV2ZW50IFhTUy5cbiAqL1xuXG5pbnRlcmZhY2UgR3JhcGhOb2RlIHtcbiAgaWQ6IHN0cmluZztcbiAgbGFiZWw6IHN0cmluZztcbiAgdmVyZGljdDogc3RyaW5nO1xuICByb2xlOiBcImlvY1wiIHwgXCJwcm92aWRlclwiO1xufVxuXG5pbnRlcmZhY2UgR3JhcGhFZGdlIHtcbiAgZnJvbTogc3RyaW5nO1xuICB0bzogc3RyaW5nO1xuICB2ZXJkaWN0OiBzdHJpbmc7XG59XG5cbi8qKiBWZXJkaWN0LXRvLWZpbGwtY29sb3IgbWFwcGluZyAobWF0Y2hlcyBDU1MgdmVyZGljdCB2YXJpYWJsZXMpLiAqL1xuY29uc3QgVkVSRElDVF9DT0xPUlM6IFJlY29yZDxzdHJpbmcsIHN0cmluZz4gPSB7XG4gIG1hbGljaW91czogIFwiI2VmNDQ0NFwiLFxuICBzdXNwaWNpb3VzOiBcIiNmOTczMTZcIixcbiAgY2xlYW46ICAgICAgXCIjMjJjNTVlXCIsXG4gIGtub3duX2dvb2Q6IFwiIzNiODJmNlwiLFxuICBub19kYXRhOiAgICBcIiM2YjcyODBcIixcbiAgZXJyb3I6ICAgICAgXCIjNmI3MjgwXCIsXG4gIGlvYzogICAgICAgIFwiIzhiNWNmNlwiLFxufTtcblxuY29uc3QgU1ZHX05TID0gXCJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2Z1wiO1xuXG5mdW5jdGlvbiB2ZXJkaWN0Q29sb3IodmVyZGljdDogc3RyaW5nKTogc3RyaW5nIHtcbiAgcmV0dXJuIFZFUkRJQ1RfQ09MT1JTW3ZlcmRpY3RdID8/IFwiIzZiNzI4MFwiO1xufVxuXG4vKipcbiAqIENyZWF0ZSBhbiBTVkcgZWxlbWVudCBpbiB0aGUgU1ZHIG5hbWVzcGFjZS5cbiAqL1xuZnVuY3Rpb24gc3ZnRWwodGFnOiBzdHJpbmcpOiBTVkdFbGVtZW50IHtcbiAgcmV0dXJuIGRvY3VtZW50LmNyZWF0ZUVsZW1lbnROUyhTVkdfTlMsIHRhZykgYXMgU1ZHRWxlbWVudDtcbn1cblxuLyoqXG4gKiBSZW5kZXIgdGhlIGh1Yi1hbmQtc3Bva2UgcmVsYXRpb25zaGlwIGdyYXBoIGludG8gdGhlIGdpdmVuIGNvbnRhaW5lci5cbiAqIFNhZmUgdG8gY2FsbCB3aGVuIG5vIHByb3ZpZGVyIGRhdGEgaXMgcHJlc2VudCBcdTIwMTQgc2hvd3MgYSBmYWxsYmFjayBtZXNzYWdlLlxuICovXG5mdW5jdGlvbiByZW5kZXJSZWxhdGlvbnNoaXBHcmFwaChjb250YWluZXI6IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gIGNvbnN0IG5vZGVzQXR0ciA9IGNvbnRhaW5lci5nZXRBdHRyaWJ1dGUoXCJkYXRhLWdyYXBoLW5vZGVzXCIpO1xuICBjb25zdCBlZGdlc0F0dHIgPSBjb250YWluZXIuZ2V0QXR0cmlidXRlKFwiZGF0YS1ncmFwaC1lZGdlc1wiKTtcblxuICBsZXQgbm9kZXM6IEdyYXBoTm9kZVtdID0gW107XG4gIGxldCBlZGdlczogR3JhcGhFZGdlW10gPSBbXTtcblxuICB0cnkge1xuICAgIG5vZGVzID0gbm9kZXNBdHRyID8gKEpTT04ucGFyc2Uobm9kZXNBdHRyKSBhcyBHcmFwaE5vZGVbXSkgOiBbXTtcbiAgICBlZGdlcyA9IGVkZ2VzQXR0ciA/IChKU09OLnBhcnNlKGVkZ2VzQXR0cikgYXMgR3JhcGhFZGdlW10pIDogW107XG4gIH0gY2F0Y2gge1xuICAgIC8vIE1hbGZvcm1lZCBKU09OIFx1MjAxNCBzaG93IGVtcHR5IHN0YXRlXG4gICAgbm9kZXMgPSBbXTtcbiAgICBlZGdlcyA9IFtdO1xuICB9XG5cbiAgY29uc3QgcHJvdmlkZXJOb2RlcyA9IG5vZGVzLmZpbHRlcigobikgPT4gbi5yb2xlID09PSBcInByb3ZpZGVyXCIpO1xuICBjb25zdCBpb2NOb2RlID0gbm9kZXMuZmluZCgobikgPT4gbi5yb2xlID09PSBcImlvY1wiKTtcblxuICBpZiAoIWlvY05vZGUgfHwgcHJvdmlkZXJOb2Rlcy5sZW5ndGggPT09IDApIHtcbiAgICBjb25zdCBtc2cgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwicFwiKTtcbiAgICBtc2cuY2xhc3NOYW1lID0gXCJncmFwaC1lbXB0eVwiO1xuICAgIG1zZy5hcHBlbmRDaGlsZChkb2N1bWVudC5jcmVhdGVUZXh0Tm9kZShcIk5vIHByb3ZpZGVyIGRhdGEgdG8gZ3JhcGhcIikpO1xuICAgIGNvbnRhaW5lci5hcHBlbmRDaGlsZChtc2cpO1xuICAgIHJldHVybjtcbiAgfVxuXG4gIC8vIC0tLS0gU1ZHIGNhbnZhcyAtLS0tXG4gIGNvbnN0IHN2ZyA9IHN2Z0VsKFwic3ZnXCIpO1xuICBzdmcuc2V0QXR0cmlidXRlKFwidmlld0JveFwiLCBcIjAgMCA2MDAgNDAwXCIpO1xuICBzdmcuc2V0QXR0cmlidXRlKFwid2lkdGhcIiwgXCIxMDAlXCIpO1xuICBzdmcuc2V0QXR0cmlidXRlKFwicm9sZVwiLCBcImltZ1wiKTtcbiAgc3ZnLnNldEF0dHJpYnV0ZShcImFyaWEtbGFiZWxcIiwgXCJQcm92aWRlciByZWxhdGlvbnNoaXAgZ3JhcGhcIik7XG5cbiAgY29uc3QgY3ggPSAzMDA7ICAvLyBjZW50ZXIgeFxuICBjb25zdCBjeSA9IDIwMDsgIC8vIGNlbnRlciB5XG4gIGNvbnN0IG9yYml0UmFkaXVzID0gMTUwO1xuICBjb25zdCBpb2NyciA9IDMwOyAgLy8gSU9DIG5vZGUgcmFkaXVzXG4gIGNvbnN0IHBycnIgPSAyMDsgICAvLyBwcm92aWRlciBub2RlIHJhZGl1c1xuXG4gIC8vIC0tLS0gRHJhdyBlZGdlcyBmaXJzdCAoYmVoaW5kIG5vZGVzKSAtLS0tXG4gIGNvbnN0IGVkZ2VHcm91cCA9IHN2Z0VsKFwiZ1wiKTtcbiAgZWRnZUdyb3VwLnNldEF0dHJpYnV0ZShcImNsYXNzXCIsIFwiZ3JhcGgtZWRnZXNcIik7XG5cbiAgZm9yIChjb25zdCBlZGdlIG9mIGVkZ2VzKSB7XG4gICAgY29uc3QgdGFyZ2V0Tm9kZSA9IHByb3ZpZGVyTm9kZXMuZmluZCgobikgPT4gbi5pZCA9PT0gZWRnZS50byk7XG4gICAgaWYgKCF0YXJnZXROb2RlKSBjb250aW51ZTtcblxuICAgIGNvbnN0IGlkeCA9IHByb3ZpZGVyTm9kZXMuaW5kZXhPZih0YXJnZXROb2RlKTtcbiAgICBjb25zdCBhbmdsZSA9ICgyICogTWF0aC5QSSAqIGlkeCkgLyBwcm92aWRlck5vZGVzLmxlbmd0aCAtIE1hdGguUEkgLyAyO1xuICAgIGNvbnN0IHB4ID0gY3ggKyBvcmJpdFJhZGl1cyAqIE1hdGguY29zKGFuZ2xlKTtcbiAgICBjb25zdCBweSA9IGN5ICsgb3JiaXRSYWRpdXMgKiBNYXRoLnNpbihhbmdsZSk7XG5cbiAgICBjb25zdCBsaW5lID0gc3ZnRWwoXCJsaW5lXCIpO1xuICAgIGxpbmUuc2V0QXR0cmlidXRlKFwieDFcIiwgU3RyaW5nKGN4KSk7XG4gICAgbGluZS5zZXRBdHRyaWJ1dGUoXCJ5MVwiLCBTdHJpbmcoY3kpKTtcbiAgICBsaW5lLnNldEF0dHJpYnV0ZShcIngyXCIsIFN0cmluZyhNYXRoLnJvdW5kKHB4KSkpO1xuICAgIGxpbmUuc2V0QXR0cmlidXRlKFwieTJcIiwgU3RyaW5nKE1hdGgucm91bmQocHkpKSk7XG4gICAgbGluZS5zZXRBdHRyaWJ1dGUoXCJzdHJva2VcIiwgdmVyZGljdENvbG9yKGVkZ2UudmVyZGljdCkpO1xuICAgIGxpbmUuc2V0QXR0cmlidXRlKFwic3Ryb2tlLXdpZHRoXCIsIFwiMlwiKTtcbiAgICBsaW5lLnNldEF0dHJpYnV0ZShcIm9wYWNpdHlcIiwgXCIwLjZcIik7XG4gICAgZWRnZUdyb3VwLmFwcGVuZENoaWxkKGxpbmUpO1xuICB9XG5cbiAgc3ZnLmFwcGVuZENoaWxkKGVkZ2VHcm91cCk7XG5cbiAgLy8gLS0tLSBEcmF3IHByb3ZpZGVyIG5vZGVzIC0tLS1cbiAgY29uc3Qgbm9kZUdyb3VwID0gc3ZnRWwoXCJnXCIpO1xuICBub2RlR3JvdXAuc2V0QXR0cmlidXRlKFwiY2xhc3NcIiwgXCJncmFwaC1ub2Rlc1wiKTtcblxuICBwcm92aWRlck5vZGVzLmZvckVhY2goKG5vZGUsIGlkeCkgPT4ge1xuICAgIGNvbnN0IGFuZ2xlID0gKDIgKiBNYXRoLlBJICogaWR4KSAvIHByb3ZpZGVyTm9kZXMubGVuZ3RoIC0gTWF0aC5QSSAvIDI7XG4gICAgY29uc3QgcHggPSBjeCArIG9yYml0UmFkaXVzICogTWF0aC5jb3MoYW5nbGUpO1xuICAgIGNvbnN0IHB5ID0gY3kgKyBvcmJpdFJhZGl1cyAqIE1hdGguc2luKGFuZ2xlKTtcblxuICAgIGNvbnN0IGdyb3VwID0gc3ZnRWwoXCJnXCIpO1xuICAgIGdyb3VwLnNldEF0dHJpYnV0ZShcImNsYXNzXCIsIFwiZ3JhcGgtbm9kZSBncmFwaC1ub2RlLS1wcm92aWRlclwiKTtcblxuICAgIC8vIEFjY2Vzc2libGUgdG9vbHRpcFxuICAgIGNvbnN0IHRpdGxlID0gc3ZnRWwoXCJ0aXRsZVwiKTtcbiAgICB0aXRsZS5hcHBlbmRDaGlsZChkb2N1bWVudC5jcmVhdGVUZXh0Tm9kZShub2RlLmlkKSk7XG4gICAgZ3JvdXAuYXBwZW5kQ2hpbGQodGl0bGUpO1xuXG4gICAgLy8gQ2lyY2xlXG4gICAgY29uc3QgY2lyY2xlID0gc3ZnRWwoXCJjaXJjbGVcIik7XG4gICAgY2lyY2xlLnNldEF0dHJpYnV0ZShcImN4XCIsIFN0cmluZyhNYXRoLnJvdW5kKHB4KSkpO1xuICAgIGNpcmNsZS5zZXRBdHRyaWJ1dGUoXCJjeVwiLCBTdHJpbmcoTWF0aC5yb3VuZChweSkpKTtcbiAgICBjaXJjbGUuc2V0QXR0cmlidXRlKFwiclwiLCBTdHJpbmcocHJycikpO1xuICAgIGNpcmNsZS5zZXRBdHRyaWJ1dGUoXCJmaWxsXCIsIHZlcmRpY3RDb2xvcihub2RlLnZlcmRpY3QpKTtcbiAgICBncm91cC5hcHBlbmRDaGlsZChjaXJjbGUpO1xuXG4gICAgLy8gTGFiZWwgYmVsb3cgY2lyY2xlIChTRUMtMDg6IGNyZWF0ZVRleHROb2RlKVxuICAgIGNvbnN0IHRleHQgPSBzdmdFbChcInRleHRcIik7XG4gICAgdGV4dC5zZXRBdHRyaWJ1dGUoXCJ4XCIsIFN0cmluZyhNYXRoLnJvdW5kKHB4KSkpO1xuICAgIHRleHQuc2V0QXR0cmlidXRlKFwieVwiLCBTdHJpbmcoTWF0aC5yb3VuZChweSArIHBycnIgKyAxNCkpKTtcbiAgICB0ZXh0LnNldEF0dHJpYnV0ZShcInRleHQtYW5jaG9yXCIsIFwibWlkZGxlXCIpO1xuICAgIHRleHQuc2V0QXR0cmlidXRlKFwiZm9udC1zaXplXCIsIFwiMTFcIik7XG4gICAgdGV4dC5zZXRBdHRyaWJ1dGUoXCJmaWxsXCIsIFwiI2U1ZTdlYlwiKTtcbiAgICB0ZXh0LmFwcGVuZENoaWxkKGRvY3VtZW50LmNyZWF0ZVRleHROb2RlKG5vZGUubGFiZWwuc2xpY2UoMCwgMTIpKSk7XG4gICAgZ3JvdXAuYXBwZW5kQ2hpbGQodGV4dCk7XG5cbiAgICBub2RlR3JvdXAuYXBwZW5kQ2hpbGQoZ3JvdXApO1xuICB9KTtcblxuICBzdmcuYXBwZW5kQ2hpbGQobm9kZUdyb3VwKTtcblxuICAvLyAtLS0tIERyYXcgSU9DIGNlbnRlciBub2RlIChvbiB0b3ApIC0tLS1cbiAgY29uc3QgaW9jR3JvdXAgPSBzdmdFbChcImdcIik7XG4gIGlvY0dyb3VwLnNldEF0dHJpYnV0ZShcImNsYXNzXCIsIFwiZ3JhcGgtbm9kZSBncmFwaC1ub2RlLS1pb2NcIik7XG5cbiAgY29uc3QgaW9jVGl0bGUgPSBzdmdFbChcInRpdGxlXCIpO1xuICBpb2NUaXRsZS5hcHBlbmRDaGlsZChkb2N1bWVudC5jcmVhdGVUZXh0Tm9kZShpb2NOb2RlLmlkKSk7XG4gIGlvY0dyb3VwLmFwcGVuZENoaWxkKGlvY1RpdGxlKTtcblxuICBjb25zdCBpb2NDaXJjbGUgPSBzdmdFbChcImNpcmNsZVwiKTtcbiAgaW9jQ2lyY2xlLnNldEF0dHJpYnV0ZShcImN4XCIsIFN0cmluZyhjeCkpO1xuICBpb2NDaXJjbGUuc2V0QXR0cmlidXRlKFwiY3lcIiwgU3RyaW5nKGN5KSk7XG4gIGlvY0NpcmNsZS5zZXRBdHRyaWJ1dGUoXCJyXCIsIFN0cmluZyhpb2NycikpO1xuICBpb2NDaXJjbGUuc2V0QXR0cmlidXRlKFwiZmlsbFwiLCB2ZXJkaWN0Q29sb3IoXCJpb2NcIikpO1xuICBpb2NHcm91cC5hcHBlbmRDaGlsZChpb2NDaXJjbGUpO1xuXG4gIGNvbnN0IGlvY1RleHQgPSBzdmdFbChcInRleHRcIik7XG4gIGlvY1RleHQuc2V0QXR0cmlidXRlKFwieFwiLCBTdHJpbmcoY3gpKTtcbiAgaW9jVGV4dC5zZXRBdHRyaWJ1dGUoXCJ5XCIsIFN0cmluZyhjeSArIDQpKTtcbiAgaW9jVGV4dC5zZXRBdHRyaWJ1dGUoXCJ0ZXh0LWFuY2hvclwiLCBcIm1pZGRsZVwiKTtcbiAgaW9jVGV4dC5zZXRBdHRyaWJ1dGUoXCJmb250LXNpemVcIiwgXCIxMFwiKTtcbiAgaW9jVGV4dC5zZXRBdHRyaWJ1dGUoXCJmaWxsXCIsIFwiI2ZmZlwiKTtcbiAgaW9jVGV4dC5zZXRBdHRyaWJ1dGUoXCJmb250LXdlaWdodFwiLCBcImJvbGRcIik7XG4gIGlvY1RleHQuYXBwZW5kQ2hpbGQoZG9jdW1lbnQuY3JlYXRlVGV4dE5vZGUoaW9jTm9kZS5sYWJlbC5zbGljZSgwLCAyMCkpKTtcbiAgaW9jR3JvdXAuYXBwZW5kQ2hpbGQoaW9jVGV4dCk7XG5cbiAgc3ZnLmFwcGVuZENoaWxkKGlvY0dyb3VwKTtcblxuICBjb250YWluZXIuYXBwZW5kQ2hpbGQoc3ZnKTtcbn1cblxuLyoqXG4gKiBJbml0aWFsaXplIHRoZSBncmFwaCBtb2R1bGUuXG4gKiBGaW5kcyB0aGUgI3JlbGF0aW9uc2hpcC1ncmFwaCBlbGVtZW50IGFuZCByZW5kZXJzIHRoZSBTVkcgaWYgcHJlc2VudC5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGluaXQoKTogdm9pZCB7XG4gIGNvbnN0IGNvbnRhaW5lciA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwicmVsYXRpb25zaGlwLWdyYXBoXCIpO1xuICBpZiAoY29udGFpbmVyKSB7XG4gICAgcmVuZGVyUmVsYXRpb25zaGlwR3JhcGgoY29udGFpbmVyKTtcbiAgfVxufVxuIiwgIi8qKlxuICogU2VudGluZWxYIG1haW4gZW50cnkgcG9pbnQgXHUyMDE0IGltcG9ydHMgYW5kIGluaXRpYWxpemVzIGFsbCBmZWF0dXJlIG1vZHVsZXMuXG4gKlxuICogVGhpcyBmaWxlIGlzIHRoZSBlc2J1aWxkIGVudHJ5IHBvaW50IChKU19FTlRSWSBpbiBNYWtlZmlsZSkuXG4gKiBlc2J1aWxkIHdyYXBzIHRoZSBvdXRwdXQgaW4gYW4gSUlGRSBhdXRvbWF0aWNhbGx5ICgtLWZvcm1hdD1paWZlKS5cbiAqXG4gKiBNb2R1bGUgaW5pdCBvcmRlciBtYXRjaGVzIHRoZSBvcmlnaW5hbCBtYWluLmpzIGluaXQoKSBmdW5jdGlvblxuICogKGxpbmVzIDgxNS04MjYpIHRvIHByZXNlcnZlIGlkZW50aWNhbCBET01Db250ZW50TG9hZGVkIGJlaGF2aW9yLlxuICovXG5cbmltcG9ydCB7IGluaXQgYXMgaW5pdEZvcm0gfSBmcm9tIFwiLi9tb2R1bGVzL2Zvcm1cIjtcbmltcG9ydCB7IGluaXQgYXMgaW5pdENsaXBib2FyZCB9IGZyb20gXCIuL21vZHVsZXMvY2xpcGJvYXJkXCI7XG5pbXBvcnQgeyBpbml0IGFzIGluaXRDYXJkcyB9IGZyb20gXCIuL21vZHVsZXMvY2FyZHNcIjtcbmltcG9ydCB7IGluaXQgYXMgaW5pdEZpbHRlciB9IGZyb20gXCIuL21vZHVsZXMvZmlsdGVyXCI7XG5pbXBvcnQgeyBpbml0IGFzIGluaXRFbnJpY2htZW50IH0gZnJvbSBcIi4vbW9kdWxlcy9lbnJpY2htZW50XCI7XG5pbXBvcnQgeyBpbml0IGFzIGluaXRTZXR0aW5ncyB9IGZyb20gXCIuL21vZHVsZXMvc2V0dGluZ3NcIjtcbmltcG9ydCB7IGluaXQgYXMgaW5pdFVpIH0gZnJvbSBcIi4vbW9kdWxlcy91aVwiO1xuaW1wb3J0IHsgaW5pdCBhcyBpbml0R3JhcGggfSBmcm9tIFwiLi9tb2R1bGVzL2dyYXBoXCI7XG5cbmZ1bmN0aW9uIGluaXQoKTogdm9pZCB7XG4gIGluaXRGb3JtKCk7XG4gIGluaXRDbGlwYm9hcmQoKTtcbiAgaW5pdENhcmRzKCk7XG4gIGluaXRGaWx0ZXIoKTtcbiAgaW5pdEVucmljaG1lbnQoKTtcbiAgaW5pdFNldHRpbmdzKCk7XG4gIGluaXRVaSgpO1xuICBpbml0R3JhcGgoKTtcbn1cblxuaWYgKGRvY3VtZW50LnJlYWR5U3RhdGUgPT09IFwibG9hZGluZ1wiKSB7XG4gIGRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoXCJET01Db250ZW50TG9hZGVkXCIsIGluaXQpO1xufSBlbHNlIHtcbiAgaW5pdCgpO1xufVxuIl0sCiAgIm1hcHBpbmdzIjogIjs7O0FBU08sV0FBUyxLQUFLLElBQWEsTUFBYyxXQUFXLElBQVk7QUFDckUsV0FBTyxHQUFHLGFBQWEsSUFBSSxLQUFLO0FBQUEsRUFDbEM7OztBQ0FBLE1BQUksYUFBbUQ7QUFJdkQsV0FBUyxrQkFBa0IsV0FBeUI7QUFDbEQsVUFBTSxXQUFX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LG9CQUFvQjtBQUM5RCxRQUFJLFdBQVc7QUFDYiw4QkFBd0IsU0FBUztBQUFBLElBQ25DO0FBQUEsRUFDRjs7O0FDckxBLFdBQVNDLFFBQWE7QUFDcEIsU0FBUztBQUNULElBQUFBLE1BQWM7QUFDZCxJQUFBQSxNQUFVO0FBQ1YsSUFBQUEsTUFBVztBQUNYLElBQUFBLE1BQWU7QUFDZixJQUFBQSxNQUFhO0FBQ2IsSUFBQUEsTUFBTztBQUNQLElBQUFBLE1BQVU7QUFBQSxFQUNaO0FBRUEsTUFBSSxTQUFTLGVBQWUsV0FBVztBQUNyQyxhQUFTLGlCQUFpQixvQkFBb0JBLEtBQUk7QUFBQSxFQUNwRCxPQUFPO0FBQ0wsSUFBQUEsTUFBSztBQUFBLEVBQ1A7IiwKICAibmFtZXMiOiBbImluaXQiLCAiaW5pdCIsICJpbml0IiwgInZlcmRpY3RCdG5zIiwgInR5cGVQaWxscyIsICJzcGlubmVyV3JhcHBlciIsICJkZXRhaWxzQ29udGFpbmVyIiwgImluaXQiLCAiYnRuIiwgImluaXQiLCAiaW5pdCIsICJpbml0IiwgImluaXQiXQp9Cg==
