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
  function computeVerdictCounts(entries) {
    let malicious = 0, suspicious = 0, clean = 0, noData = 0;
    for (const e of entries) {
      if (e.verdict === "malicious") malicious++;
      else if (e.verdict === "suspicious") suspicious++;
      else if (e.verdict === "clean") clean++;
      else noData++;
    }
    return { malicious, suspicious, clean, noData, total: entries.length };
  }
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
    const counts = computeVerdictCounts(entries);
    const total = Math.max(1, counts.total);
    const microBar = document.createElement("div");
    microBar.className = "verdict-micro-bar";
    microBar.setAttribute(
      "title",
      `${counts.malicious} malicious, ${counts.suspicious} suspicious, ${counts.clean} clean, ${counts.noData} no data`
    );
    const segments = [
      [counts.malicious, "malicious"],
      [counts.suspicious, "suspicious"],
      [counts.clean, "clean"],
      [counts.noData, "no_data"]
    ];
    for (const [count, verdict] of segments) {
      if (count === 0) continue;
      const seg = document.createElement("div");
      seg.className = "micro-bar-segment micro-bar-segment--" + verdict;
      seg.style.width = Math.round(count / total * 100) + "%";
      microBar.appendChild(seg);
    }
    summaryRow.appendChild(microBar);
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
    const isNoData = verdict === "no_data" || verdict === "error";
    row.className = "provider-detail-row" + (isNoData ? " provider-row--no-data" : "");
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
  function injectSectionHeadersAndNoDataSummary(slot) {
    const noDataSection = slot.querySelector(".enrichment-section--no-data");
    if (!noDataSection) return;
    const noDataRows = noDataSection.querySelectorAll(
      ".provider-row--no-data"
    );
    if (noDataRows.length === 0) return;
    const count = noDataRows.length;
    const summaryRow = document.createElement("div");
    summaryRow.className = "no-data-summary-row";
    summaryRow.setAttribute("role", "button");
    summaryRow.setAttribute("tabindex", "0");
    summaryRow.setAttribute("aria-expanded", "false");
    summaryRow.textContent = count + " provider" + (count !== 1 ? "s" : "") + " had no record";
    const firstNoData = noDataRows[0];
    if (firstNoData) {
      noDataSection.insertBefore(summaryRow, firstNoData);
    }
    summaryRow.addEventListener("click", () => {
      const isExpanded = noDataSection.classList.toggle("no-data-expanded");
      summaryRow.setAttribute("aria-expanded", String(isExpanded));
    });
    summaryRow.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        summaryRow.click();
      }
    });
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
    document.querySelectorAll(".enrichment-slot").forEach((slot) => {
      injectSectionHeadersAndNoDataSummary(slot);
    });
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
      const contextSection = slot.querySelector(".enrichment-section--context");
      if (contextSection && result.type === "result") {
        const contextRow = createContextRow(result);
        contextSection.appendChild(contextRow);
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
    const isNoData = verdict === "no_data" || verdict === "error";
    const sectionSelector = isNoData ? ".enrichment-section--no-data" : ".enrichment-section--reputation";
    const sectionContainer = slot.querySelector(sectionSelector);
    if (sectionContainer) {
      const detailRow = createDetailRow(result.provider, verdict, statText, result);
      sectionContainer.appendChild(detailRow);
      if (!isNoData) {
        sortDetailRows(sectionContainer, result.ioc_value);
      }
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
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vc3JjL3RzL3V0aWxzL2RvbS50cyIsICIuLi9zcmMvdHMvbW9kdWxlcy9mb3JtLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2NsaXBib2FyZC50cyIsICIuLi9zcmMvdHMvdHlwZXMvaW9jLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2NhcmRzLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2ZpbHRlci50cyIsICIuLi9zcmMvdHMvbW9kdWxlcy9leHBvcnQudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvdmVyZGljdC1jb21wdXRlLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL3Jvdy1mYWN0b3J5LnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2VucmljaG1lbnQudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvc2V0dGluZ3MudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvdWkudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvZ3JhcGgudHMiLCAiLi4vc3JjL3RzL21haW4udHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbIi8qKlxuICogU2hhcmVkIERPTSB1dGlsaXRpZXMgZm9yIFNlbnRpbmVsWCBUeXBlU2NyaXB0IG1vZHVsZXMuXG4gKi9cblxuLyoqXG4gKiBUeXBlZCBnZXRBdHRyaWJ1dGUgd3JhcHBlciBcdTIwMTQgcmV0dXJucyBzdHJpbmcgaW5zdGVhZCBvZiBzdHJpbmcgfCBudWxsLlxuICogQ2FsbGVycyBwYXNzIGEgZmFsbGJhY2sgKGRlZmF1bHQ6IFwiXCIpIHRvIGF2b2lkIG51bGwgcHJvcGFnYXRpb24uXG4gKiBBdHRyaWJ1dGUgbmFtZXMgYXJlIGludGVudGlvbmFsbHkgdHlwZWQgYXMgc3RyaW5nIChub3QgYSB1bmlvbikgZm9yIGZsZXhpYmlsaXR5LlxuICovXG5leHBvcnQgZnVuY3Rpb24gYXR0cihlbDogRWxlbWVudCwgbmFtZTogc3RyaW5nLCBmYWxsYmFjayA9IFwiXCIpOiBzdHJpbmcge1xuICByZXR1cm4gZWwuZ2V0QXR0cmlidXRlKG5hbWUpID8/IGZhbGxiYWNrO1xufVxuIiwgIi8qKlxuICogRm9ybSBjb250cm9scyBtb2R1bGUgXHUyMDE0IHN1Ym1pdCBidXR0b24gc3RhdGUsIGF1dG8tZ3JvdyB0ZXh0YXJlYSxcbiAqIG1vZGUgdG9nZ2xlLCBhbmQgcGFzdGUgZmVlZGJhY2suXG4gKlxuICogRXh0cmFjdGVkIGZyb20gbWFpbi5qcyBpbml0U3VibWl0QnV0dG9uKCksIGluaXRBdXRvR3JvdygpLFxuICogaW5pdE1vZGVUb2dnbGUoKSwgdXBkYXRlU3VibWl0TGFiZWwoKSwgc2hvd1Bhc3RlRmVlZGJhY2soKSAobGluZXMgMzQtMTYyKS5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vLyBNb2R1bGUtbGV2ZWwgdGltZXIgZm9yIHBhc3RlIGZlZWRiYWNrIGFuaW1hdGlvbiBcdTIwMTQgYXZvaWRzIHN0b3Jpbmcgb24gSFRNTEVsZW1lbnRcbmxldCBwYXN0ZVRpbWVyOiBSZXR1cm5UeXBlPHR5cGVvZiBzZXRUaW1lb3V0PiB8IG51bGwgPSBudWxsO1xuXG4vLyAtLS0tIFBhc3RlIGNoYXJhY3RlciBjb3VudCBmZWVkYmFjayAoSU5QVVQtMDIpIC0tLS1cblxuZnVuY3Rpb24gc2hvd1Bhc3RlRmVlZGJhY2soY2hhckNvdW50OiBudW1iZXIpOiB2b2lkIHtcbiAgY29uc3QgZmVlZGJhY2sgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInBhc3RlLWZlZWRiYWNrXCIpO1xuICBpZiAoIWZlZWRiYWNrKSByZXR1cm47XG4gIGZlZWRiYWNrLnRleHRDb250ZW50ID0gY2hhckNvdW50ICsgXCIgY2hhcmFjdGVycyBwYXN0ZWRcIjtcbiAgZmVlZGJhY2suc3R5bGUuZGlzcGxheSA9IFwiXCI7XG4gIGZlZWRiYWNrLmNsYXNzTGlzdC5yZW1vdmUoXCJpcy1oaWRpbmdcIik7XG4gIGZlZWRiYWNrLmNsYXNzTGlzdC5hZGQoXCJpcy12aXNpYmxlXCIpO1xuICBpZiAocGFzdGVUaW1lciAhPT0gbnVsbCkgY2xlYXJUaW1lb3V0KHBhc3RlVGltZXIpO1xuICBwYXN0ZVRpbWVyID0gc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgZmVlZGJhY2suY2xhc3NMaXN0LnJlbW92ZShcImlzLXZpc2libGVcIik7XG4gICAgZmVlZGJhY2suY2xhc3NMaXN0LmFkZChcImlzLWhpZGluZ1wiKTtcbiAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcbiAgICAgIGZlZWRiYWNrLnN0eWxlLmRpc3BsYXkgPSBcIm5vbmVcIjtcbiAgICAgIGZlZWRiYWNrLmNsYXNzTGlzdC5yZW1vdmUoXCJpcy1oaWRpbmdcIik7XG4gICAgfSwgMjUwKTtcbiAgfSwgMjAwMCk7XG59XG5cbi8vIC0tLS0gU3VibWl0IGxhYmVsIChtb2RlLWF3YXJlKSAtLS0tXG5cbmZ1bmN0aW9uIHVwZGF0ZVN1Ym1pdExhYmVsKG1vZGU6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCBzdWJtaXRCdG4gPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInN1Ym1pdC1idG5cIik7XG4gIGlmICghc3VibWl0QnRuKSByZXR1cm47XG4gIHN1Ym1pdEJ0bi50ZXh0Q29udGVudCA9IFwiRXh0cmFjdFwiO1xuICAvLyBNb2RlLWF3YXJlIGJ1dHRvbiBjb2xvclxuICBzdWJtaXRCdG4uY2xhc3NMaXN0LnJlbW92ZShcIm1vZGUtb25saW5lXCIsIFwibW9kZS1vZmZsaW5lXCIpO1xuICBzdWJtaXRCdG4uY2xhc3NMaXN0LmFkZChtb2RlID09PSBcIm9ubGluZVwiID8gXCJtb2RlLW9ubGluZVwiIDogXCJtb2RlLW9mZmxpbmVcIik7XG59XG5cbi8vIC0tLS0gU3VibWl0IGJ1dHRvbjogZGlzYWJsZSB3aGVuIHRleHRhcmVhIGlzIGVtcHR5IC0tLS1cblxuZnVuY3Rpb24gaW5pdFN1Ym1pdEJ1dHRvbigpOiB2b2lkIHtcbiAgY29uc3QgZm9ybSA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiYW5hbHl6ZS1mb3JtXCIpO1xuICBpZiAoIWZvcm0pIHJldHVybjtcblxuICBjb25zdCB0ZXh0YXJlYSA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTFRleHRBcmVhRWxlbWVudD4oXCIjaW9jLXRleHRcIik7XG4gIGNvbnN0IHN1Ym1pdEJ0biA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTEJ1dHRvbkVsZW1lbnQ+KFwiI3N1Ym1pdC1idG5cIik7XG4gIGNvbnN0IGNsZWFyQnRuID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJjbGVhci1idG5cIik7XG5cbiAgaWYgKCF0ZXh0YXJlYSB8fCAhc3VibWl0QnRuKSByZXR1cm47XG5cbiAgLy8gUmUtYmluZCB0byBub24tbnVsbGFibGUgYWxpYXNlcyBzbyBjbG9zdXJlcyBiZWxvdyBkb24ndCBuZWVkIGFzc2VydGlvbnMuXG4gIC8vIFR5cGVTY3JpcHQgbmFycm93cyB0aGUgb3V0ZXIgYGNvbnN0YCBhZnRlciB0aGUgaWYtY2hlY2ssIGJ1dCBjbG9zdXJlc1xuICAvLyAoZXZlbiBub24tYXN5bmMgb25lcykgY2Fubm90IHNlZSB0aGF0IG5hcnJvd2luZyBcdTIwMTQgd2UgdGhlcmVmb3JlIGludHJvZHVjZVxuICAvLyBuZXcgYGNvbnN0YCBiaW5kaW5ncyB0aGF0IGFyZSBndWFyYW50ZWVkIG5vbi1udWxsLlxuICBjb25zdCB0YTogSFRNTFRleHRBcmVhRWxlbWVudCA9IHRleHRhcmVhO1xuICBjb25zdCBzYjogSFRNTEJ1dHRvbkVsZW1lbnQgPSBzdWJtaXRCdG47XG5cbiAgZnVuY3Rpb24gdXBkYXRlU3VibWl0U3RhdGUoKTogdm9pZCB7XG4gICAgc2IuZGlzYWJsZWQgPSB0YS52YWx1ZS50cmltKCkubGVuZ3RoID09PSAwO1xuICB9XG5cbiAgdGEuYWRkRXZlbnRMaXN0ZW5lcihcImlucHV0XCIsIHVwZGF0ZVN1Ym1pdFN0YXRlKTtcblxuICAvLyBBbHNvIGhhbmRsZSBwYXN0ZSBldmVudHMgKGJyb3dzZXIgbWF5IG5vdCBmaXJlIFwiaW5wdXRcIiBpbW1lZGlhdGVseSlcbiAgdGEuYWRkRXZlbnRMaXN0ZW5lcihcInBhc3RlXCIsIGZ1bmN0aW9uICgpIHtcbiAgICAvLyBEZWZlciB1bnRpbCBhZnRlciBwYXN0ZSBjb250ZW50IGlzIGFwcGxpZWRcbiAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcbiAgICAgIHVwZGF0ZVN1Ym1pdFN0YXRlKCk7XG4gICAgICBzaG93UGFzdGVGZWVkYmFjayh0YS52YWx1ZS5sZW5ndGgpO1xuICAgIH0sIDApO1xuICB9KTtcblxuICAvLyBJbml0aWFsIHN0YXRlIChwYWdlIGxvYWQgd2l0aCBwcmUtZmlsbGVkIGNvbnRlbnQpXG4gIHVwZGF0ZVN1Ym1pdFN0YXRlKCk7XG5cbiAgLy8gLS0tLSBDbGVhciBidXR0b24gLS0tLVxuICBpZiAoY2xlYXJCdG4pIHtcbiAgICBjbGVhckJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgICAgdGEudmFsdWUgPSBcIlwiO1xuICAgICAgdXBkYXRlU3VibWl0U3RhdGUoKTtcbiAgICAgIHRhLmZvY3VzKCk7XG4gICAgfSk7XG4gIH1cbn1cblxuLy8gLS0tLSBBdXRvLWdyb3cgdGV4dGFyZWEgKElOUC0wMikgLS0tLVxuXG5mdW5jdGlvbiBpbml0QXV0b0dyb3coKTogdm9pZCB7XG4gIGNvbnN0IHRleHRhcmVhID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcjxIVE1MVGV4dEFyZWFFbGVtZW50PihcIiNpb2MtdGV4dFwiKTtcbiAgaWYgKCF0ZXh0YXJlYSkgcmV0dXJuO1xuXG4gIC8vIE5vbi1udWxsYWJsZSBhbGlhcyBmb3IgdXNlIGluc2lkZSBjbG9zdXJlcyAoVHlwZVNjcmlwdCBjYW4ndCBuYXJyb3cgdGhyb3VnaCBjbG9zdXJlcylcbiAgY29uc3QgdGE6IEhUTUxUZXh0QXJlYUVsZW1lbnQgPSB0ZXh0YXJlYTtcblxuICBmdW5jdGlvbiBncm93KCk6IHZvaWQge1xuICAgIHRhLnN0eWxlLmhlaWdodCA9IFwiYXV0b1wiO1xuICAgIHRhLnN0eWxlLmhlaWdodCA9IHRhLnNjcm9sbEhlaWdodCArIFwicHhcIjtcbiAgfVxuXG4gIHRhLmFkZEV2ZW50TGlzdGVuZXIoXCJpbnB1dFwiLCBncm93KTtcblxuICB0YS5hZGRFdmVudExpc3RlbmVyKFwicGFzdGVcIiwgZnVuY3Rpb24gKCkge1xuICAgIHNldFRpbWVvdXQoZ3JvdywgMCk7XG4gIH0pO1xuXG4gIGdyb3coKTtcbn1cblxuLy8gLS0tLSBNb2RlIHRvZ2dsZSBzd2l0Y2ggKElOUFVULTAxLCBJTlBVVC0wMykgLS0tLVxuXG5mdW5jdGlvbiBpbml0TW9kZVRvZ2dsZSgpOiB2b2lkIHtcbiAgY29uc3Qgd2lkZ2V0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJtb2RlLXRvZ2dsZS13aWRnZXRcIik7XG4gIGNvbnN0IHRvZ2dsZUJ0biA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwibW9kZS10b2dnbGUtYnRuXCIpO1xuICBjb25zdCBtb2RlSW5wdXQgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yPEhUTUxJbnB1dEVsZW1lbnQ+KFwiI21vZGUtaW5wdXRcIik7XG4gIGlmICghd2lkZ2V0IHx8ICF0b2dnbGVCdG4gfHwgIW1vZGVJbnB1dCkgcmV0dXJuO1xuXG4gIC8vIE5vbi1udWxsYWJsZSBhbGlhc2VzIGZvciBjbG9zdXJlc1xuICBjb25zdCB3OiBIVE1MRWxlbWVudCA9IHdpZGdldDtcbiAgY29uc3QgdGI6IEhUTUxFbGVtZW50ID0gdG9nZ2xlQnRuO1xuICBjb25zdCBtaTogSFRNTElucHV0RWxlbWVudCA9IG1vZGVJbnB1dDtcblxuICB0Yi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgIGNvbnN0IGN1cnJlbnQgPSBhdHRyKHcsIFwiZGF0YS1tb2RlXCIpO1xuICAgIGNvbnN0IG5leHQgPSBjdXJyZW50ID09PSBcIm9mZmxpbmVcIiA/IFwib25saW5lXCIgOiBcIm9mZmxpbmVcIjtcbiAgICB3LnNldEF0dHJpYnV0ZShcImRhdGEtbW9kZVwiLCBuZXh0KTtcbiAgICBtaS52YWx1ZSA9IG5leHQ7XG4gICAgdGIuc2V0QXR0cmlidXRlKFwiYXJpYS1wcmVzc2VkXCIsIG5leHQgPT09IFwib25saW5lXCIgPyBcInRydWVcIiA6IFwiZmFsc2VcIik7XG4gICAgdXBkYXRlU3VibWl0TGFiZWwobmV4dCk7XG4gIH0pO1xuXG4gIC8vIFNldCBpbml0aWFsIGxhYmVsIGJhc2VkIG9uIGN1cnJlbnQgbW9kZSAoZGVmZW5zaXZlKVxuICB1cGRhdGVTdWJtaXRMYWJlbChtaS52YWx1ZSk7XG59XG5cbi8vIC0tLS0gUHVibGljIEFQSSAtLS0tXG5cbi8qKlxuICogSW5pdGlhbGlzZSBhbGwgZm9ybSBjb250cm9sczogc3VibWl0IGJ1dHRvbiBzdGF0ZSwgYXV0by1ncm93LCBhbmQgbW9kZSB0b2dnbGUuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBpbml0U3VibWl0QnV0dG9uKCk7XG4gIGluaXRBdXRvR3JvdygpO1xuICBpbml0TW9kZVRvZ2dsZSgpO1xufVxuIiwgIi8qKlxuICogQ2xpcGJvYXJkIG1vZHVsZSBcdTIwMTQgY29weSBidXR0b25zLCBjb3B5LXdpdGgtZW5yaWNobWVudCwgYW5kIGZhbGxiYWNrIGNvcHkuXG4gKlxuICogRXh0cmFjdGVkIGZyb20gbWFpbi5qcyBpbml0Q29weUJ1dHRvbnMoKSwgc2hvd0NvcGllZEZlZWRiYWNrKCksXG4gKiBmYWxsYmFja0NvcHkoKSwgYW5kIHdyaXRlVG9DbGlwYm9hcmQoKSAobGluZXMgMTY2LTIyMykuXG4gKlxuICogd3JpdGVUb0NsaXBib2FyZCBpcyBleHBvcnRlZCBmb3IgdXNlIGJ5IFBoYXNlIDIyJ3MgZW5yaWNobWVudCBtb2R1bGVcbiAqIChleHBvcnQgYnV0dG9uIG5lZWRzIHRvIGNvcHkgbXVsdGktSU9DIHRleHQgdG8gY2xpcGJvYXJkKS5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vLyAtLS0tIFByaXZhdGUgaGVscGVycyAtLS0tXG5cbi8qKlxuICogVGVtcG9yYXJpbHkgcmVwbGFjZSBidXR0b24gdGV4dCB3aXRoIFwiQ29waWVkIVwiIHRoZW4gcmVzdG9yZSBhZnRlciAxNTAwbXMuXG4gKiB0ZXh0Q29udGVudCBpcyB0eXBlZCBzdHJpbmd8bnVsbCBcdTIwMTQgPz8gZW5zdXJlcyB0aGUgb3JpZ2luYWwgdmFsdWUgaXMgbmV2ZXIgbnVsbC5cbiAqL1xuZnVuY3Rpb24gc2hvd0NvcGllZEZlZWRiYWNrKGJ0bjogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgY29uc3Qgb3JpZ2luYWwgPSBidG4udGV4dENvbnRlbnQgPz8gXCJDb3B5XCI7XG4gIGJ0bi50ZXh0Q29udGVudCA9IFwiQ29waWVkIVwiO1xuICBidG4uY2xhc3NMaXN0LmFkZChcImNvcGllZFwiKTtcbiAgc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgYnRuLnRleHRDb250ZW50ID0gb3JpZ2luYWw7XG4gICAgYnRuLmNsYXNzTGlzdC5yZW1vdmUoXCJjb3BpZWRcIik7XG4gIH0sIDE1MDApO1xufVxuXG4vKipcbiAqIEZhbGxiYWNrIGNvcHkgdmlhIGEgdGVtcG9yYXJ5IG9mZi1zY3JlZW4gdGV4dGFyZWEgYW5kIGV4ZWNDb21tYW5kKFwiY29weVwiKS5cbiAqIFVzZWQgd2hlbiBuYXZpZ2F0b3IuY2xpcGJvYXJkIGlzIHVuYXZhaWxhYmxlIChub24tSFRUUFMsIG9sZGVyIGJyb3dzZXIpLlxuICovXG5mdW5jdGlvbiBmYWxsYmFja0NvcHkodGV4dDogc3RyaW5nLCBidG46IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gIC8vIENyZWF0ZSBhIHRlbXBvcmFyeSB0ZXh0YXJlYSwgc2VsZWN0IGl0cyBjb250ZW50LCBhbmQgY29weVxuICBjb25zdCB0bXAgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwidGV4dGFyZWFcIik7XG4gIHRtcC52YWx1ZSA9IHRleHQ7XG4gIHRtcC5zdHlsZS5wb3NpdGlvbiA9IFwiZml4ZWRcIjtcbiAgdG1wLnN0eWxlLnRvcCA9IFwiLTk5OTlweFwiO1xuICB0bXAuc3R5bGUubGVmdCA9IFwiLTk5OTlweFwiO1xuICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKHRtcCk7XG4gIHRtcC5mb2N1cygpO1xuICB0bXAuc2VsZWN0KCk7XG4gIHRyeSB7XG4gICAgZG9jdW1lbnQuZXhlY0NvbW1hbmQoXCJjb3B5XCIpO1xuICAgIHNob3dDb3BpZWRGZWVkYmFjayhidG4pO1xuICB9IGNhdGNoIHtcbiAgICAvLyBDb3B5IGZhaWxlZCBzaWxlbnRseSBcdTIwMTQgdXNlciBjYW4gc3RpbGwgbWFudWFsbHkgc2VsZWN0IHRoZSB2YWx1ZVxuICB9IGZpbmFsbHkge1xuICAgIGRvY3VtZW50LmJvZHkucmVtb3ZlQ2hpbGQodG1wKTtcbiAgfVxufVxuXG4vLyAtLS0tIFB1YmxpYyBBUEkgLS0tLVxuXG4vKipcbiAqIENvcHkgdGV4dCB0byB0aGUgY2xpcGJvYXJkIHVzaW5nIHRoZSBDbGlwYm9hcmQgQVBJLCBmYWxsaW5nIGJhY2sgdG9cbiAqIGV4ZWNDb21tYW5kIHdoZW4gdW5hdmFpbGFibGUuIFNob3dzIGZlZWRiYWNrIG9uIHRoZSB0cmlnZ2VyaW5nIGJ1dHRvbi5cbiAqXG4gKiBFeHBvcnRlZCBzbyBQaGFzZSAyMidzIGVucmljaG1lbnQgbW9kdWxlIGNhbiBjYWxsIGl0IGZvciB0aGUgZXhwb3J0IGJ1dHRvbi5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIHdyaXRlVG9DbGlwYm9hcmQodGV4dDogc3RyaW5nLCBidG46IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gIGlmICghbmF2aWdhdG9yLmNsaXBib2FyZCkge1xuICAgIGZhbGxiYWNrQ29weSh0ZXh0LCBidG4pO1xuICAgIHJldHVybjtcbiAgfVxuICBuYXZpZ2F0b3IuY2xpcGJvYXJkLndyaXRlVGV4dCh0ZXh0KS50aGVuKGZ1bmN0aW9uICgpIHtcbiAgICBzaG93Q29waWVkRmVlZGJhY2soYnRuKTtcbiAgfSkuY2F0Y2goZnVuY3Rpb24gKCkge1xuICAgIGZhbGxiYWNrQ29weSh0ZXh0LCBidG4pO1xuICB9KTtcbn1cblxuLyoqXG4gKiBBdHRhY2ggY2xpY2sgaGFuZGxlcnMgdG8gYWxsIC5jb3B5LWJ0biBlbGVtZW50cyBwcmVzZW50IGluIHRoZSBET00uXG4gKiBFYWNoIGJ1dHRvbiByZWFkcyBkYXRhLXZhbHVlIChJT0MpIGFuZCBvcHRpb25hbGx5IGRhdGEtZW5yaWNobWVudCAod29yc3QgdmVyZGljdCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBjb25zdCBjb3B5QnV0dG9ucyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmNvcHktYnRuXCIpO1xuXG4gIGNvcHlCdXR0b25zLmZvckVhY2goZnVuY3Rpb24gKGJ0bikge1xuICAgIGJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgICAgY29uc3QgdmFsdWUgPSBhdHRyKGJ0biwgXCJkYXRhLXZhbHVlXCIpO1xuICAgICAgaWYgKCF2YWx1ZSkgcmV0dXJuO1xuXG4gICAgICAvLyBDaGVjayBmb3IgZW5yaWNobWVudCBzdW1tYXJ5IHNldCBieSBwb2xsaW5nIGxvb3AgKHdvcnN0IHZlcmRpY3QpXG4gICAgICBjb25zdCBlbnJpY2htZW50ID0gYXR0cihidG4sIFwiZGF0YS1lbnJpY2htZW50XCIpO1xuICAgICAgLy8gYXR0cigpIHJldHVybnMgXCJcIiB3aGVuIGF0dHJpYnV0ZSBpcyBhYnNlbnQgKGZhbHN5KSBcdTIwMTQgc2FtZSB0ZXJuYXJ5IGFzIG9yaWdpbmFsXG4gICAgICBjb25zdCBjb3B5VGV4dCA9IGVucmljaG1lbnQgPyAodmFsdWUgKyBcIiB8IFwiICsgZW5yaWNobWVudCkgOiB2YWx1ZTtcblxuICAgICAgd3JpdGVUb0NsaXBib2FyZChjb3B5VGV4dCwgYnRuKTtcbiAgICB9KTtcbiAgfSk7XG59XG4iLCAiLyoqXG4gKiBEb21haW4gdHlwZXMgYW5kIGNvbnN0YW50cyBmb3IgSU9DIChJbmRpY2F0b3Igb2YgQ29tcHJvbWlzZSkgZW5yaWNobWVudC5cbiAqXG4gKiBUaGlzIG1vZHVsZSBkZWZpbmVzIHRoZSBzaGFyZWQgdHlwZSBsYXllciBmb3IgdmVyZGljdCB2YWx1ZXMgYW5kIElPQyBtZXRhZGF0YS5cbiAqIEFsbCBjb25zdGFudHMgYXJlIHNvdXJjZWQgZnJvbSBhcHAvc3RhdGljL21haW4uanMgYW5kIG11c3QgcmVtYWluIGluIHN5bmNcbiAqIHdpdGggdGhlIEZsYXNrIGJhY2tlbmQgdmVyZGljdCB2YWx1ZXMuXG4gKlxuICogU2hhcmVkIHR5cGUgZGVmaW5pdGlvbnMsIHR5cGVkIGNvbnN0YW50cywgYW5kIHZlcmRpY3QgdXRpbGl0eSBmdW5jdGlvbnMuXG4gKi9cblxuLyoqXG4gKiBUaGUgdmVyZGljdCBrZXlzIHJldHVybmVkIGJ5IHRoZSBGbGFzayBlbnJpY2htZW50IEFQSS5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgVkVSRElDVF9MQUJFTFMga2V5cyAobGluZXMgMjMxXHUyMDEzMjM3KS5cbiAqIFVzZWQgYXMgZGlzY3JpbWluYW50IHZhbHVlcyB0aHJvdWdob3V0IGVucmljaG1lbnQgcmVzdWx0IHByb2Nlc3NpbmcuXG4gKlxuICogTm90ZToga25vd25fZ29vZCBpcyBpbnRlbnRpb25hbGx5IGV4Y2x1ZGVkIGZyb20gVkVSRElDVF9TRVZFUklUWSBcdTIwMTQgaXQgaXNcbiAqIG5vdCBhIHNldmVyaXR5IGxldmVsIGJ1dCBhIGNsYXNzaWZpY2F0aW9uIG92ZXJyaWRlLiB2ZXJkaWN0U2V2ZXJpdHlJbmRleCgpXG4gKiByZXR1cm5zIC0xIGZvciBrbm93bl9nb29kLCB3aGljaCBpcyBjb3JyZWN0IGFuZCBpbnRlbnRpb25hbC5cbiAqL1xuZXhwb3J0IHR5cGUgVmVyZGljdEtleSA9XG4gIHwgXCJlcnJvclwiXG4gIHwgXCJub19kYXRhXCJcbiAgfCBcImNsZWFuXCJcbiAgfCBcInN1c3BpY2lvdXNcIlxuICB8IFwibWFsaWNpb3VzXCJcbiAgfCBcImtub3duX2dvb2RcIjtcblxuLyoqXG4gKiBUaGUgc2V2ZW4gSU9DIHR5cGVzIHN1cHBvcnRlZCBmb3IgZW5yaWNobWVudC5cbiAqXG4gKiBPbmx5IGVucmljaGFibGUgdHlwZXMgYXJlIGluY2x1ZGVkIFx1MjAxNCBOT1QgXCJjdmVcIiAoQ1ZFcyBhcmUgZXh0cmFjdGVkIGJ1dFxuICogbmV2ZXIgZW5yaWNoZWQsIGFuZCBJT0NfUFJPVklERVJfQ09VTlRTIGhhcyBubyBcImN2ZVwiIGVudHJ5KS5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgSU9DX1BST1ZJREVSX0NPVU5UUyBrZXlzIChsaW5lcyAyNDJcdTIwMTMyNTApLlxuICovXG50eXBlIElvY1R5cGUgPVxuICB8IFwiaXB2NFwiXG4gIHwgXCJpcHY2XCJcbiAgfCBcImRvbWFpblwiXG4gIHwgXCJ1cmxcIlxuICB8IFwibWQ1XCJcbiAgfCBcInNoYTFcIlxuICB8IFwic2hhMjU2XCI7XG5cbi8qKlxuICogUmFua2VkIHNldmVyaXR5IHZlcmRpY3RzIFx1MjAxNCBpbmRleCAwIGlzIGxlYXN0IHNldmVyZSwgaW5kZXggNCBpcyBtb3N0IHNldmVyZS5cbiAqXG4gKiBrbm93bl9nb29kIGlzIGludGVudGlvbmFsbHkgZXhjbHVkZWQ6IGl0IGlzIGEgY2xhc3NpZmljYXRpb24gb3ZlcnJpZGUsIG5vdFxuICogYSBzZXZlcml0eSBsZXZlbC4gdmVyZGljdFNldmVyaXR5SW5kZXggcmV0dXJucyAtMSBmb3Iga25vd25fZ29vZCwgd2hpY2ggaXNcbiAqIHRoZSBjb3JyZWN0IGFuZCBleHBlY3RlZCBiZWhhdmlvciAoaXQgYWx3YXlzIHdpbnMgdmlhIGNvbXB1dGVXb3JzdFZlcmRpY3Qnc1xuICogZWFybHktcmV0dXJuIGNoZWNrLCBub3QgYnkgc2V2ZXJpdHkgcmFua2luZykuXG4gKlxuICogU291cmNlOiBtYWluLmpzIGxpbmUgMjI4LlxuICovXG50eXBlIFJhbmtlZFZlcmRpY3QgPSBcImVycm9yXCIgfCBcIm5vX2RhdGFcIiB8IFwiY2xlYW5cIiB8IFwic3VzcGljaW91c1wiIHwgXCJtYWxpY2lvdXNcIjtcblxuY29uc3QgVkVSRElDVF9TRVZFUklUWSA9IFtcbiAgXCJlcnJvclwiLFxuICBcIm5vX2RhdGFcIixcbiAgXCJjbGVhblwiLFxuICBcInN1c3BpY2lvdXNcIixcbiAgXCJtYWxpY2lvdXNcIixcbl0gYXMgY29uc3Qgc2F0aXNmaWVzIHJlYWRvbmx5IFJhbmtlZFZlcmRpY3RbXTtcblxuLyoqXG4gKiBSZXR1cm5zIHRoZSBzZXZlcml0eSBpbmRleCBmb3IgYSB2ZXJkaWN0IGtleS5cbiAqIEhpZ2hlciBpbmRleCA9IGhpZ2hlciBzZXZlcml0eS4gUmV0dXJucyAtMSBpZiBub3QgZm91bmQgKGUuZy4ga25vd25fZ29vZCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiB2ZXJkaWN0U2V2ZXJpdHlJbmRleCh2ZXJkaWN0OiBWZXJkaWN0S2V5KTogbnVtYmVyIHtcbiAgcmV0dXJuIChWRVJESUNUX1NFVkVSSVRZIGFzIHJlYWRvbmx5IHN0cmluZ1tdKS5pbmRleE9mKHZlcmRpY3QpO1xufVxuXG4vKipcbiAqIEh1bWFuLXJlYWRhYmxlIGRpc3BsYXkgbGFiZWxzIGZvciBlYWNoIHZlcmRpY3Qga2V5LlxuICpcbiAqIFR5cGVkIGFzIGBSZWNvcmQ8VmVyZGljdEtleSwgc3RyaW5nPmAgdG8gZW5zdXJlIGFsbCBmaXZlIGtleXMgYXJlIHByZXNlbnRcbiAqIGFuZCB0aGF0IGluZGV4aW5nIHdpdGggYW4gaW52YWxpZCBrZXkgcHJvZHVjZXMgYSBjb21waWxlIGVycm9yIHVuZGVyXG4gKiBgbm9VbmNoZWNrZWRJbmRleGVkQWNjZXNzYC5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgbGluZXMgMjMxXHUyMDEzMjM3LlxuICovXG5leHBvcnQgY29uc3QgVkVSRElDVF9MQUJFTFM6IFJlY29yZDxWZXJkaWN0S2V5LCBzdHJpbmc+ID0ge1xuICBtYWxpY2lvdXM6IFwiTUFMSUNJT1VTXCIsXG4gIHN1c3BpY2lvdXM6IFwiU1VTUElDSU9VU1wiLFxuICBjbGVhbjogXCJDTEVBTlwiLFxuICBrbm93bl9nb29kOiBcIktOT1dOIEdPT0RcIixcbiAgbm9fZGF0YTogXCJOTyBEQVRBXCIsXG4gIGVycm9yOiBcIkVSUk9SXCIsXG59IGFzIGNvbnN0O1xuXG4vKipcbiAqIEhhcmRjb2RlZCBmYWxsYmFjayBwcm92aWRlciBjb3VudHMgcGVyIGVucmljaGFibGUgSU9DIHR5cGUuXG4gKlxuICogVXNlZCBhcyBhIGZhbGxiYWNrIHdoZW4gdGhlIGRhdGEtcHJvdmlkZXItY291bnRzIERPTSBhdHRyaWJ1dGUgaXMgYWJzZW50XG4gKiAob2ZmbGluZSBtb2RlIG9yIHNlcnZlciBlcnJvcikuIFJlZmxlY3RzIHRoZSBiYXNlbGluZSAzLXByb3ZpZGVyIHNldHVwOlxuICogVmlydXNUb3RhbCBzdXBwb3J0cyBhbGwgNyB0eXBlcywgTWFsd2FyZUJhemFhciBzdXBwb3J0cyBtZDUvc2hhMS9zaGEyNTYsXG4gKiBUaHJlYXRGb3ggc3VwcG9ydHMgYWxsIDcuXG4gKlxuICogUHJpdmF0ZSBcdTIwMTQgY2FsbGVycyBtdXN0IHVzZSBnZXRQcm92aWRlckNvdW50cygpIHRvIGFsbG93IHJ1bnRpbWUgb3ZlcnJpZGVcbiAqIGZyb20gdGhlIERPTSBhdHRyaWJ1dGUgcG9wdWxhdGVkIGJ5IHRoZSBGbGFzayByb3V0ZS5cbiAqL1xuY29uc3QgX2RlZmF1bHRQcm92aWRlckNvdW50czogUmVjb3JkPElvY1R5cGUsIG51bWJlcj4gPSB7XG4gIGlwdjQ6IDIsXG4gIGlwdjY6IDIsXG4gIGRvbWFpbjogMixcbiAgdXJsOiAyLFxuICBtZDU6IDMsXG4gIHNoYTE6IDMsXG4gIHNoYTI1NjogMyxcbn0gYXMgY29uc3Q7XG5cbi8qKlxuICogUmV0dXJuIHByb3ZpZGVyIGNvdW50cyBwZXIgSU9DIHR5cGUsIHJlYWRpbmcgZnJvbSB0aGUgRE9NIHdoZW4gYXZhaWxhYmxlLlxuICpcbiAqIE9uIHRoZSByZXN1bHRzIHBhZ2UgaW4gb25saW5lIG1vZGUsIEZsYXNrIGluamVjdHMgdGhlIGFjdHVhbCByZWdpc3RyeSBjb3VudHNcbiAqIHZpYSBkYXRhLXByb3ZpZGVyLWNvdW50cyBvbiAucGFnZS1yZXN1bHRzLiBUaGlzIGZ1bmN0aW9uIHJlYWRzIHRoYXQgYXR0cmlidXRlXG4gKiBzbyB0aGUgcGVuZGluZy1pbmRpY2F0b3IgbG9naWMgcmVmbGVjdHMgdGhlIHJlYWwgY29uZmlndXJlZCBwcm92aWRlciBzZXRcbiAqIChlLmcuLCA4KyBwcm92aWRlcnMgaW4gdjQuMCkgcmF0aGVyIHRoYW4gYSBzdGFsZSBoYXJkY29kZWQgdmFsdWUuXG4gKlxuICogRmFsbHMgYmFjayB0byBfZGVmYXVsdFByb3ZpZGVyQ291bnRzIHdoZW46XG4gKiAgIC0gLnBhZ2UtcmVzdWx0cyBlbGVtZW50IGlzIGFic2VudCAobm90IG9uIHJlc3VsdHMgcGFnZSlcbiAqICAgLSBkYXRhLXByb3ZpZGVyLWNvdW50cyBhdHRyaWJ1dGUgaXMgbWlzc2luZyAob2ZmbGluZSBtb2RlKVxuICogICAtIEpTT04gcGFyc2UgZmFpbHMgKG1hbGZvcm1lZCBhdHRyaWJ1dGUpXG4gKlxuICogUmV0dXJuczpcbiAqICAgUmVjb3JkIG1hcHBpbmcgSU9DIHR5cGUgc3RyaW5nIFx1MjE5MiBjb25maWd1cmVkIHByb3ZpZGVyIGNvdW50LlxuICovXG5leHBvcnQgZnVuY3Rpb24gZ2V0UHJvdmlkZXJDb3VudHMoKTogUmVjb3JkPHN0cmluZywgbnVtYmVyPiB7XG4gIGNvbnN0IGVsID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIucGFnZS1yZXN1bHRzXCIpO1xuICBpZiAoZWwgPT09IG51bGwpIHJldHVybiBfZGVmYXVsdFByb3ZpZGVyQ291bnRzO1xuICBjb25zdCByYXcgPSBlbC5nZXRBdHRyaWJ1dGUoXCJkYXRhLXByb3ZpZGVyLWNvdW50c1wiKTtcbiAgaWYgKHJhdyA9PT0gbnVsbCkgcmV0dXJuIF9kZWZhdWx0UHJvdmlkZXJDb3VudHM7XG4gIHRyeSB7XG4gICAgcmV0dXJuIEpTT04ucGFyc2UocmF3KSBhcyBSZWNvcmQ8c3RyaW5nLCBudW1iZXI+O1xuICB9IGNhdGNoIHtcbiAgICByZXR1cm4gX2RlZmF1bHRQcm92aWRlckNvdW50cztcbiAgfVxufVxuIiwgIi8qKlxuICogQ2FyZCBtYW5hZ2VtZW50IG1vZHVsZSBcdTIwMTQgdmVyZGljdCB1cGRhdGVzLCBkYXNoYm9hcmQgY291bnRzLCBzZXZlcml0eSBzb3J0aW5nLlxuICpcbiAqIEV4dHJhY3RlZCBmcm9tIG1haW4uanMgbGluZXMgMjUyLTMzNi5cbiAqIFByb3ZpZGVzIHRoZSBwdWJsaWMgQVBJIGNvbnN1bWVkIGJ5IFBoYXNlIDIyJ3MgZW5yaWNobWVudCBtb2R1bGUuXG4gKi9cblxuaW1wb3J0IHR5cGUgeyBWZXJkaWN0S2V5IH0gZnJvbSBcIi4uL3R5cGVzL2lvY1wiO1xuaW1wb3J0IHsgVkVSRElDVF9MQUJFTFMsIHZlcmRpY3RTZXZlcml0eUluZGV4IH0gZnJvbSBcIi4uL3R5cGVzL2lvY1wiO1xuaW1wb3J0IHsgYXR0ciB9IGZyb20gXCIuLi91dGlscy9kb21cIjtcblxuLyoqXG4gKiBNb2R1bGUtbGV2ZWwgZGVib3VuY2UgdGltZXIgZm9yIHNvcnRDYXJkc0J5U2V2ZXJpdHkuXG4gKiBVc2VzIFJldHVyblR5cGU8dHlwZW9mIHNldFRpbWVvdXQ+IHRvIGF2b2lkIE5vZGVKUy5UaW1lb3V0IGNvbmZsaWN0LlxuICovXG5sZXQgc29ydFRpbWVyOiBSZXR1cm5UeXBlPHR5cGVvZiBzZXRUaW1lb3V0PiB8IG51bGwgPSBudWxsO1xuXG4vKipcbiAqIEluaXRpYWxpc2UgdGhlIGNhcmRzIG1vZHVsZS5cbiAqIENhcmRzIGhhdmUgbm8gRE9NQ29udGVudExvYWRlZCBzZXR1cCBcdTIwMTQgdGhlaXIgZnVuY3Rpb25zIGFyZSBjYWxsZWQgYnkgdGhlXG4gKiBlbnJpY2htZW50IG1vZHVsZS4gRXhwb3J0ZWQgZm9yIGNvbnNpc3RlbmN5IHdpdGggdGhlIG1vZHVsZSBwYXR0ZXJuO1xuICogbWFpbi50cyB3aWxsIGNhbGwgaXQgaW4gUGhhc2UgMjIuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICAvLyBOby1vcCBmb3IgUGhhc2UgMjEgXHUyMDE0IGNhcmRzIG1vZHVsZSBoYXMgbm8gRE9NQ29udGVudExvYWRlZCB3aXJpbmcuXG4gIC8vIENhbGxlZCBieSBtYWluLnRzIGZvciBjb25zaXN0ZW50IG1vZHVsZSBpbml0aWFsaXNhdGlvbi5cbn1cblxuLyoqXG4gKiBGaW5kIHRoZSBJT0MgY2FyZCBlbGVtZW50IGZvciBhIGdpdmVuIElPQyB2YWx1ZSB1c2luZyBDU1MuZXNjYXBlLlxuICogUmV0dXJucyBudWxsIGlmIG5vIG1hdGNoaW5nIGNhcmQgaXMgZm91bmQuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBmaW5kQ2FyZEZvcklvYyhpb2NWYWx1ZTogc3RyaW5nKTogSFRNTEVsZW1lbnQgfCBudWxsIHtcbiAgcmV0dXJuIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFxuICAgICcuaW9jLWNhcmRbZGF0YS1pb2MtdmFsdWU9XCInICsgQ1NTLmVzY2FwZShpb2NWYWx1ZSkgKyAnXCJdJ1xuICApO1xufVxuXG4vKipcbiAqIFVwZGF0ZSBhIGNhcmQncyB2ZXJkaWN0OiBzZXRzIGRhdGEtdmVyZGljdCBhdHRyaWJ1dGUsIHZlcmRpY3QgbGFiZWwgdGV4dCxcbiAqIGFuZCB2ZXJkaWN0IGxhYmVsIENTUyBjbGFzcy5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIHVwZGF0ZUNhcmRWZXJkaWN0KFxuICBpb2NWYWx1ZTogc3RyaW5nLFxuICB3b3JzdFZlcmRpY3Q6IFZlcmRpY3RLZXlcbik6IHZvaWQge1xuICBjb25zdCBjYXJkID0gZmluZENhcmRGb3JJb2MoaW9jVmFsdWUpO1xuICBpZiAoIWNhcmQpIHJldHVybjtcblxuICAvLyBVcGRhdGUgZGF0YS12ZXJkaWN0IGF0dHJpYnV0ZSAoZHJpdmVzIENTUyBib3JkZXIgY29sb3VyKVxuICBjYXJkLnNldEF0dHJpYnV0ZShcImRhdGEtdmVyZGljdFwiLCB3b3JzdFZlcmRpY3QpO1xuXG4gIC8vIFVwZGF0ZSB2ZXJkaWN0IGxhYmVsIHRleHQgYW5kIGNsYXNzXG4gIGNvbnN0IGxhYmVsID0gY2FyZC5xdWVyeVNlbGVjdG9yKFwiLnZlcmRpY3QtbGFiZWxcIik7XG4gIGlmIChsYWJlbCkge1xuICAgIC8vIFJlbW92ZSBhbGwgdmVyZGljdC1sYWJlbC0tKiBjbGFzc2VzLCB0aGVuIGFkZCB0aGUgY29ycmVjdCBvbmVcbiAgICBjb25zdCBjbGFzc2VzID0gbGFiZWwuY2xhc3NOYW1lXG4gICAgICAuc3BsaXQoXCIgXCIpXG4gICAgICAuZmlsdGVyKChjKSA9PiAhYy5zdGFydHNXaXRoKFwidmVyZGljdC1sYWJlbC0tXCIpKTtcbiAgICBjbGFzc2VzLnB1c2goXCJ2ZXJkaWN0LWxhYmVsLS1cIiArIHdvcnN0VmVyZGljdCk7XG4gICAgbGFiZWwuY2xhc3NOYW1lID0gY2xhc3Nlcy5qb2luKFwiIFwiKTtcbiAgICBsYWJlbC50ZXh0Q29udGVudCA9IFZFUkRJQ1RfTEFCRUxTW3dvcnN0VmVyZGljdF0gfHwgd29yc3RWZXJkaWN0LnRvVXBwZXJDYXNlKCk7XG4gIH1cbn1cblxuLyoqXG4gKiBDb3VudCBjYXJkcyBieSB2ZXJkaWN0IGFuZCB1cGRhdGUgZGFzaGJvYXJkIGNvdW50IGVsZW1lbnRzLlxuICovXG5leHBvcnQgZnVuY3Rpb24gdXBkYXRlRGFzaGJvYXJkQ291bnRzKCk6IHZvaWQge1xuICBjb25zdCBkYXNoYm9hcmQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInZlcmRpY3QtZGFzaGJvYXJkXCIpO1xuICBpZiAoIWRhc2hib2FyZCkgcmV0dXJuO1xuXG4gIGNvbnN0IGNhcmRzID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuaW9jLWNhcmRcIik7XG4gIGNvbnN0IGNvdW50czogUmVjb3JkPHN0cmluZywgbnVtYmVyPiA9IHtcbiAgICBtYWxpY2lvdXM6IDAsXG4gICAgc3VzcGljaW91czogMCxcbiAgICBjbGVhbjogMCxcbiAgICBrbm93bl9nb29kOiAwLFxuICAgIG5vX2RhdGE6IDAsXG4gIH07XG5cbiAgY2FyZHMuZm9yRWFjaCgoY2FyZCkgPT4ge1xuICAgIGNvbnN0IHYgPSBhdHRyKGNhcmQsIFwiZGF0YS12ZXJkaWN0XCIpO1xuICAgIGlmIChPYmplY3QucHJvdG90eXBlLmhhc093blByb3BlcnR5LmNhbGwoY291bnRzLCB2KSkge1xuICAgICAgY291bnRzW3ZdID0gKGNvdW50c1t2XSA/PyAwKSArIDE7XG4gICAgfVxuICB9KTtcblxuICBjb25zdCB2ZXJkaWN0cyA9IFtcIm1hbGljaW91c1wiLCBcInN1c3BpY2lvdXNcIiwgXCJjbGVhblwiLCBcImtub3duX2dvb2RcIiwgXCJub19kYXRhXCJdO1xuICB2ZXJkaWN0cy5mb3JFYWNoKCh2ZXJkaWN0KSA9PiB7XG4gICAgY29uc3QgY291bnRFbCA9IGRhc2hib2FyZC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcbiAgICAgICdbZGF0YS12ZXJkaWN0LWNvdW50PVwiJyArIHZlcmRpY3QgKyAnXCJdJ1xuICAgICk7XG4gICAgaWYgKGNvdW50RWwpIHtcbiAgICAgIGNvdW50RWwudGV4dENvbnRlbnQgPSBTdHJpbmcoY291bnRzW3ZlcmRpY3RdID8/IDApO1xuICAgIH1cbiAgfSk7XG59XG5cbi8qKlxuICogRGVib3VuY2VkIGVudHJ5IHBvaW50OiBzY2hlZHVsZXMgZG9Tb3J0Q2FyZHMgd2l0aCBhIDEwMCBtcyBkZWxheS5cbiAqIENhbGxpbmcgdGhpcyBtdWx0aXBsZSB0aW1lcyBpbiBxdWljayBzdWNjZXNzaW9uIG9ubHkgdHJpZ2dlcnMgb25lIHNvcnQuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBzb3J0Q2FyZHNCeVNldmVyaXR5KCk6IHZvaWQge1xuICBpZiAoc29ydFRpbWVyICE9PSBudWxsKSBjbGVhclRpbWVvdXQoc29ydFRpbWVyKTtcbiAgc29ydFRpbWVyID0gc2V0VGltZW91dChkb1NvcnRDYXJkcywgMTAwKTtcbn1cblxuLy8gLS0tLSBQcml2YXRlIGhlbHBlcnMgLS0tLVxuXG4vKipcbiAqIFJlb3JkZXJzIC5pb2MtY2FyZCBlbGVtZW50cyBpbiAjaW9jLWNhcmRzLWdyaWQgYnkgdmVyZGljdCBzZXZlcml0eSAobW9zdFxuICogc2V2ZXJlIGZpcnN0KS4gQ2FsbGVkIGJ5IHNvcnRDYXJkc0J5U2V2ZXJpdHkgdmlhIHNldFRpbWVvdXQgZGVib3VuY2UuXG4gKi9cbmZ1bmN0aW9uIGRvU29ydENhcmRzKCk6IHZvaWQge1xuICBjb25zdCBncmlkID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJpb2MtY2FyZHMtZ3JpZFwiKTtcbiAgaWYgKCFncmlkKSByZXR1cm47XG5cbiAgY29uc3QgY2FyZHMgPSBBcnJheS5mcm9tKGdyaWQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuaW9jLWNhcmRcIikpO1xuICBpZiAoY2FyZHMubGVuZ3RoID09PSAwKSByZXR1cm47XG5cbiAgY2FyZHMuc29ydCgoYSwgYikgPT4ge1xuICAgIGNvbnN0IHZhID0gdmVyZGljdFNldmVyaXR5SW5kZXgoXG4gICAgICBhdHRyKGEsIFwiZGF0YS12ZXJkaWN0XCIsIFwibm9fZGF0YVwiKSBhcyBWZXJkaWN0S2V5XG4gICAgKTtcbiAgICBjb25zdCB2YiA9IHZlcmRpY3RTZXZlcml0eUluZGV4KFxuICAgICAgYXR0cihiLCBcImRhdGEtdmVyZGljdFwiLCBcIm5vX2RhdGFcIikgYXMgVmVyZGljdEtleVxuICAgICk7XG4gICAgLy8gSGlnaGVyIHNldmVyaXR5IGZpcnN0IChkZXNjZW5kaW5nKVxuICAgIHJldHVybiB2YiAtIHZhO1xuICB9KTtcblxuICAvLyBSZW9yZGVyIERPTSBlbGVtZW50cyB3aXRob3V0IHJlbW92aW5nIHRoZW0gZnJvbSB0aGUgZG9jdW1lbnRcbiAgY2FyZHMuZm9yRWFjaCgoY2FyZCkgPT4gZ3JpZC5hcHBlbmRDaGlsZChjYXJkKSk7XG59XG4iLCAiLyoqXG4gKiBGaWx0ZXIgYmFyIG1vZHVsZSBcdTIwMTQgdmVyZGljdC90eXBlL3NlYXJjaCBmaWx0ZXJpbmcgd2l0aCBkYXNoYm9hcmQgYmFkZ2Ugc3luYy5cbiAqXG4gKiBFeHRyYWN0ZWQgZnJvbSBtYWluLmpzIGluaXRGaWx0ZXJCYXIoKSAobGluZXMgNjc3LTc4OCkuXG4gKiBNYW5hZ2VzIGZpbHRlclN0YXRlIGFuZCB3aXJlcyB1cCBhbGwgZmlsdGVyIGV2ZW50IGxpc3RlbmVycy5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vKipcbiAqIEludGVybmFsIHN0YXRlIGZvciBhbGwgYWN0aXZlIGZpbHRlciBkaW1lbnNpb25zLlxuICogTm90IGV4cG9ydGVkIFx1MjAxNCB0aGlzIGlzIHByaXZhdGUgdG8gdGhlIG1vZHVsZSBjbG9zdXJlIGluc2lkZSBpbml0KCkuXG4gKi9cbmludGVyZmFjZSBGaWx0ZXJTdGF0ZSB7XG4gIHZlcmRpY3Q6IHN0cmluZztcbiAgdHlwZTogc3RyaW5nO1xuICBzZWFyY2g6IHN0cmluZztcbn1cblxuLyoqXG4gKiBJbml0aWFsaXNlIHRoZSBmaWx0ZXIgYmFyLlxuICogV2lyZXMgdmVyZGljdCBidXR0b25zLCB0eXBlIHBpbGxzLCBzZWFyY2ggaW5wdXQsIGFuZCBkYXNoYm9hcmQgYmFkZ2UgY2xpY2tzLlxuICogQWxsIGV2ZW50IGxpc3RlbmVycyBzaGFyZSB0aGUgZmlsdGVyU3RhdGUgY2xvc3VyZS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGluaXQoKTogdm9pZCB7XG4gIGNvbnN0IGZpbHRlclJvb3RFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZmlsdGVyLXJvb3RcIik7XG4gIGlmICghZmlsdGVyUm9vdEVsKSByZXR1cm47IC8vIE5vdCBvbiByZXN1bHRzIHBhZ2VcbiAgY29uc3QgZmlsdGVyUm9vdDogSFRNTEVsZW1lbnQgPSBmaWx0ZXJSb290RWw7XG5cbiAgY29uc3QgZmlsdGVyU3RhdGU6IEZpbHRlclN0YXRlID0ge1xuICAgIHZlcmRpY3Q6IFwiYWxsXCIsXG4gICAgdHlwZTogXCJhbGxcIixcbiAgICBzZWFyY2g6IFwiXCIsXG4gIH07XG5cbiAgLy8gQXBwbHkgZmlsdGVyIHN0YXRlOiBzaG93L2hpZGUgZWFjaCBjYXJkIGFuZCB1cGRhdGUgYWN0aXZlIGJ1dHRvbiBzdHlsZXNcbiAgZnVuY3Rpb24gYXBwbHlGaWx0ZXIoKTogdm9pZCB7XG4gICAgY29uc3QgY2FyZHMgPSBmaWx0ZXJSb290LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmlvYy1jYXJkXCIpO1xuICAgIGNvbnN0IHZlcmRpY3RMQyA9IGZpbHRlclN0YXRlLnZlcmRpY3QudG9Mb3dlckNhc2UoKTtcbiAgICBjb25zdCB0eXBlTEMgPSBmaWx0ZXJTdGF0ZS50eXBlLnRvTG93ZXJDYXNlKCk7XG4gICAgY29uc3Qgc2VhcmNoTEMgPSBmaWx0ZXJTdGF0ZS5zZWFyY2gudG9Mb3dlckNhc2UoKTtcblxuICAgIGNhcmRzLmZvckVhY2goKGNhcmQpID0+IHtcbiAgICAgIGNvbnN0IGNhcmRWZXJkaWN0ID0gYXR0cihjYXJkLCBcImRhdGEtdmVyZGljdFwiKS50b0xvd2VyQ2FzZSgpO1xuICAgICAgY29uc3QgY2FyZFR5cGUgPSBhdHRyKGNhcmQsIFwiZGF0YS1pb2MtdHlwZVwiKS50b0xvd2VyQ2FzZSgpO1xuICAgICAgY29uc3QgY2FyZFZhbHVlID0gYXR0cihjYXJkLCBcImRhdGEtaW9jLXZhbHVlXCIpLnRvTG93ZXJDYXNlKCk7XG5cbiAgICAgIGNvbnN0IHZlcmRpY3RNYXRjaCA9IHZlcmRpY3RMQyA9PT0gXCJhbGxcIiB8fCBjYXJkVmVyZGljdCA9PT0gdmVyZGljdExDO1xuICAgICAgY29uc3QgdHlwZU1hdGNoID0gdHlwZUxDID09PSBcImFsbFwiIHx8IGNhcmRUeXBlID09PSB0eXBlTEM7XG4gICAgICBjb25zdCBzZWFyY2hNYXRjaCA9IHNlYXJjaExDID09PSBcIlwiIHx8IGNhcmRWYWx1ZS5pbmRleE9mKHNlYXJjaExDKSAhPT0gLTE7XG5cbiAgICAgIGNhcmQuc3R5bGUuZGlzcGxheSA9XG4gICAgICAgIHZlcmRpY3RNYXRjaCAmJiB0eXBlTWF0Y2ggJiYgc2VhcmNoTWF0Y2ggPyBcIlwiIDogXCJub25lXCI7XG4gICAgfSk7XG5cbiAgICAvLyBVcGRhdGUgYWN0aXZlIHN0YXRlIG9uIHZlcmRpY3QgYnV0dG9uc1xuICAgIGNvbnN0IHZlcmRpY3RCdG5zID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICAgIFwiW2RhdGEtZmlsdGVyLXZlcmRpY3RdXCJcbiAgICApO1xuICAgIHZlcmRpY3RCdG5zLmZvckVhY2goKGJ0bikgPT4ge1xuICAgICAgY29uc3QgYnRuVmVyZGljdCA9IGF0dHIoYnRuLCBcImRhdGEtZmlsdGVyLXZlcmRpY3RcIik7XG4gICAgICBpZiAoYnRuVmVyZGljdCA9PT0gZmlsdGVyU3RhdGUudmVyZGljdCkge1xuICAgICAgICBidG4uY2xhc3NMaXN0LmFkZChcImZpbHRlci1idG4tLWFjdGl2ZVwiKTtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIGJ0bi5jbGFzc0xpc3QucmVtb3ZlKFwiZmlsdGVyLWJ0bi0tYWN0aXZlXCIpO1xuICAgICAgfVxuICAgIH0pO1xuXG4gICAgLy8gVXBkYXRlIGFjdGl2ZSBzdGF0ZSBvbiB0eXBlIHBpbGxzXG4gICAgY29uc3QgdHlwZVBpbGxzID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICAgIFwiW2RhdGEtZmlsdGVyLXR5cGVdXCJcbiAgICApO1xuICAgIHR5cGVQaWxscy5mb3JFYWNoKChwaWxsKSA9PiB7XG4gICAgICBjb25zdCBwaWxsVHlwZSA9IGF0dHIocGlsbCwgXCJkYXRhLWZpbHRlci10eXBlXCIpO1xuICAgICAgaWYgKHBpbGxUeXBlID09PSBmaWx0ZXJTdGF0ZS50eXBlKSB7XG4gICAgICAgIHBpbGwuY2xhc3NMaXN0LmFkZChcImZpbHRlci1waWxsLS1hY3RpdmVcIik7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwaWxsLmNsYXNzTGlzdC5yZW1vdmUoXCJmaWx0ZXItcGlsbC0tYWN0aXZlXCIpO1xuICAgICAgfVxuICAgIH0pO1xuICB9XG5cbiAgLy8gVmVyZGljdCBidXR0b24gY2xpY2sgaGFuZGxlclxuICBjb25zdCB2ZXJkaWN0QnRucyA9IGZpbHRlclJvb3QucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXG4gICAgXCJbZGF0YS1maWx0ZXItdmVyZGljdF1cIlxuICApO1xuICB2ZXJkaWN0QnRucy5mb3JFYWNoKChidG4pID0+IHtcbiAgICBidG4uYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgIGNvbnN0IHZlcmRpY3QgPSBhdHRyKGJ0biwgXCJkYXRhLWZpbHRlci12ZXJkaWN0XCIpO1xuICAgICAgaWYgKHZlcmRpY3QgPT09IFwiYWxsXCIpIHtcbiAgICAgICAgZmlsdGVyU3RhdGUudmVyZGljdCA9IFwiYWxsXCI7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICAvLyBUb2dnbGU6IGNsaWNraW5nIGFjdGl2ZSB2ZXJkaWN0IHJlc2V0cyB0byAnYWxsJ1xuICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID0gZmlsdGVyU3RhdGUudmVyZGljdCA9PT0gdmVyZGljdCA/IFwiYWxsXCIgOiB2ZXJkaWN0O1xuICAgICAgfVxuICAgICAgYXBwbHlGaWx0ZXIoKTtcbiAgICB9KTtcbiAgfSk7XG5cbiAgLy8gVHlwZSBwaWxsIGNsaWNrIGhhbmRsZXJcbiAgY29uc3QgdHlwZVBpbGxzID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICBcIltkYXRhLWZpbHRlci10eXBlXVwiXG4gICk7XG4gIHR5cGVQaWxscy5mb3JFYWNoKChwaWxsKSA9PiB7XG4gICAgcGlsbC5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgKCkgPT4ge1xuICAgICAgY29uc3QgdHlwZSA9IGF0dHIocGlsbCwgXCJkYXRhLWZpbHRlci10eXBlXCIpO1xuICAgICAgaWYgKHR5cGUgPT09IFwiYWxsXCIpIHtcbiAgICAgICAgZmlsdGVyU3RhdGUudHlwZSA9IFwiYWxsXCI7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBmaWx0ZXJTdGF0ZS50eXBlID0gZmlsdGVyU3RhdGUudHlwZSA9PT0gdHlwZSA/IFwiYWxsXCIgOiB0eXBlO1xuICAgICAgfVxuICAgICAgYXBwbHlGaWx0ZXIoKTtcbiAgICB9KTtcbiAgfSk7XG5cbiAgLy8gU2VhcmNoIGlucHV0IGhhbmRsZXJcbiAgY29uc3Qgc2VhcmNoSW5wdXQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcbiAgICBcImZpbHRlci1zZWFyY2gtaW5wdXRcIlxuICApIGFzIEhUTUxJbnB1dEVsZW1lbnQgfCBudWxsO1xuICBpZiAoc2VhcmNoSW5wdXQpIHtcbiAgICBzZWFyY2hJbnB1dC5hZGRFdmVudExpc3RlbmVyKFwiaW5wdXRcIiwgKCkgPT4ge1xuICAgICAgZmlsdGVyU3RhdGUuc2VhcmNoID0gc2VhcmNoSW5wdXQudmFsdWU7XG4gICAgICBhcHBseUZpbHRlcigpO1xuICAgIH0pO1xuICB9XG5cbiAgLy8gVmVyZGljdCBkYXNoYm9hcmQgYmFkZ2UgY2xpY2sgaGFuZGxlciAodG9nZ2xlIGZpbHRlciBmcm9tIGRhc2hib2FyZClcbiAgY29uc3QgZGFzaGJvYXJkID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJ2ZXJkaWN0LWRhc2hib2FyZFwiKTtcbiAgaWYgKGRhc2hib2FyZCkge1xuICAgIGNvbnN0IGRhc2hCYWRnZXMgPSBkYXNoYm9hcmQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXG4gICAgICBcIi52ZXJkaWN0LWtwaS1jYXJkW2RhdGEtdmVyZGljdF1cIlxuICAgICk7XG4gICAgZGFzaEJhZGdlcy5mb3JFYWNoKChiYWRnZSkgPT4ge1xuICAgICAgYmFkZ2UuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgICAgY29uc3QgdmVyZGljdCA9IGF0dHIoYmFkZ2UsIFwiZGF0YS12ZXJkaWN0XCIpO1xuICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID1cbiAgICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID09PSB2ZXJkaWN0ID8gXCJhbGxcIiA6IHZlcmRpY3Q7XG4gICAgICAgIGFwcGx5RmlsdGVyKCk7XG4gICAgICB9KTtcbiAgICB9KTtcbiAgfVxuXG59XG4iLCAiLyoqXG4gKiBFeHBvcnQgbW9kdWxlIC0tIEpTT04gZG93bmxvYWQsIENTViBkb3dubG9hZCwgYW5kIGNvcHktYWxsLUlPQ3MuXG4gKlxuICogQWxsIGV4cG9ydHMgb3BlcmF0ZSBvbiB0aGUgYWNjdW11bGF0ZWQgcmVzdWx0cyBhcnJheSBidWlsdCBkdXJpbmdcbiAqIHRoZSBlbnJpY2htZW50IHBvbGxpbmcgbG9vcC4gTm8gc2VydmVyIHJvdW5kdHJpcCByZXF1aXJlZC5cbiAqL1xuXG5pbXBvcnQgdHlwZSB7IEVucmljaG1lbnRJdGVtIH0gZnJvbSBcIi4uL3R5cGVzL2FwaVwiO1xuaW1wb3J0IHsgd3JpdGVUb0NsaXBib2FyZCB9IGZyb20gXCIuL2NsaXBib2FyZFwiO1xuXG4vLyAtLS0tIEhlbHBlcnMgLS0tLVxuXG5mdW5jdGlvbiBkb3dubG9hZEJsb2IoYmxvYjogQmxvYiwgZmlsZW5hbWU6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCB1cmwgPSBVUkwuY3JlYXRlT2JqZWN0VVJMKGJsb2IpO1xuICBjb25zdCBhbmNob3IgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiYVwiKTtcbiAgYW5jaG9yLmhyZWYgPSB1cmw7XG4gIGFuY2hvci5kb3dubG9hZCA9IGZpbGVuYW1lO1xuICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKGFuY2hvcik7XG4gIGFuY2hvci5jbGljaygpO1xuICBkb2N1bWVudC5ib2R5LnJlbW92ZUNoaWxkKGFuY2hvcik7XG4gIFVSTC5yZXZva2VPYmplY3RVUkwodXJsKTtcbn1cblxuZnVuY3Rpb24gdGltZXN0YW1wKCk6IHN0cmluZyB7XG4gIHJldHVybiBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCkucmVwbGFjZSgvWzouXS9nLCBcIi1cIikuc2xpY2UoMCwgMTkpO1xufVxuXG5mdW5jdGlvbiBjc3ZFc2NhcGUodmFsdWU6IHN0cmluZyk6IHN0cmluZyB7XG4gIGlmICh2YWx1ZS5pbmRleE9mKFwiLFwiKSAhPT0gLTEgfHwgdmFsdWUuaW5kZXhPZignXCInKSAhPT0gLTEgfHwgdmFsdWUuaW5kZXhPZihcIlxcblwiKSAhPT0gLTEpIHtcbiAgICByZXR1cm4gJ1wiJyArIHZhbHVlLnJlcGxhY2UoL1wiL2csICdcIlwiJykgKyAnXCInO1xuICB9XG4gIHJldHVybiB2YWx1ZTtcbn1cblxuZnVuY3Rpb24gcmF3U3RhdEZpZWxkKHJhdzogUmVjb3JkPHN0cmluZywgdW5rbm93bj4gfCB1bmRlZmluZWQsIGtleTogc3RyaW5nKTogc3RyaW5nIHtcbiAgaWYgKCFyYXcpIHJldHVybiBcIlwiO1xuICBjb25zdCB2YWwgPSByYXdba2V5XTtcbiAgaWYgKHZhbCA9PT0gdW5kZWZpbmVkIHx8IHZhbCA9PT0gbnVsbCkgcmV0dXJuIFwiXCI7XG4gIGlmIChBcnJheS5pc0FycmF5KHZhbCkpIHJldHVybiB2YWwuam9pbihcIjsgXCIpO1xuICByZXR1cm4gU3RyaW5nKHZhbCk7XG59XG5cbi8vIC0tLS0gUHVibGljIEFQSSAtLS0tXG5cbmNvbnN0IENTVl9DT0xVTU5TID0gW1xuICBcImlvY192YWx1ZVwiLCBcImlvY190eXBlXCIsIFwicHJvdmlkZXJcIiwgXCJ2ZXJkaWN0XCIsXG4gIFwiZGV0ZWN0aW9uX2NvdW50XCIsIFwidG90YWxfZW5naW5lc1wiLCBcInNjYW5fZGF0ZVwiLFxuICBcInNpZ25hdHVyZVwiLCBcIm1hbHdhcmVfcHJpbnRhYmxlXCIsIFwidGhyZWF0X3R5cGVcIixcbiAgXCJjb3VudHJ5Q29kZVwiLCBcImlzcFwiLCBcInRvcF9kZXRlY3Rpb25zXCIsXG5dIGFzIGNvbnN0O1xuXG5leHBvcnQgZnVuY3Rpb24gZXhwb3J0SlNPTihyZXN1bHRzOiBFbnJpY2htZW50SXRlbVtdKTogdm9pZCB7XG4gIGNvbnN0IGpzb24gPSBKU09OLnN0cmluZ2lmeShyZXN1bHRzLCBudWxsLCAyKTtcbiAgY29uc3QgYmxvYiA9IG5ldyBCbG9iKFtqc29uXSwgeyB0eXBlOiBcImFwcGxpY2F0aW9uL2pzb25cIiB9KTtcbiAgZG93bmxvYWRCbG9iKGJsb2IsIFwic2VudGluZWx4LWV4cG9ydC1cIiArIHRpbWVzdGFtcCgpICsgXCIuanNvblwiKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGV4cG9ydENTVihyZXN1bHRzOiBFbnJpY2htZW50SXRlbVtdKTogdm9pZCB7XG4gIGNvbnN0IGhlYWRlciA9IENTVl9DT0xVTU5TLmpvaW4oXCIsXCIpICsgXCJcXG5cIjtcbiAgY29uc3Qgcm93czogc3RyaW5nW10gPSBbXTtcblxuICBmb3IgKGNvbnN0IHIgb2YgcmVzdWx0cykge1xuICAgIGlmIChyLnR5cGUgIT09IFwicmVzdWx0XCIpIGNvbnRpbnVlO1xuICAgIGNvbnN0IHJhdyA9IHIucmF3X3N0YXRzO1xuICAgIGNvbnN0IHJvdyA9IFtcbiAgICAgIGNzdkVzY2FwZShyLmlvY192YWx1ZSksXG4gICAgICBjc3ZFc2NhcGUoci5pb2NfdHlwZSksXG4gICAgICBjc3ZFc2NhcGUoci5wcm92aWRlciksXG4gICAgICBjc3ZFc2NhcGUoci52ZXJkaWN0KSxcbiAgICAgIFN0cmluZyhyLmRldGVjdGlvbl9jb3VudCksXG4gICAgICBTdHJpbmcoci50b3RhbF9lbmdpbmVzKSxcbiAgICAgIGNzdkVzY2FwZShyLnNjYW5fZGF0ZSA/PyBcIlwiKSxcbiAgICAgIGNzdkVzY2FwZShyYXdTdGF0RmllbGQocmF3LCBcInNpZ25hdHVyZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJtYWx3YXJlX3ByaW50YWJsZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJ0aHJlYXRfdHlwZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJjb3VudHJ5Q29kZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJpc3BcIikpLFxuICAgICAgY3N2RXNjYXBlKHJhd1N0YXRGaWVsZChyYXcsIFwidG9wX2RldGVjdGlvbnNcIikpLFxuICAgIF07XG4gICAgcm93cy5wdXNoKHJvdy5qb2luKFwiLFwiKSk7XG4gIH1cblxuICBjb25zdCBjc3YgPSBoZWFkZXIgKyByb3dzLmpvaW4oXCJcXG5cIik7XG4gIGNvbnN0IGJsb2IgPSBuZXcgQmxvYihbY3N2XSwgeyB0eXBlOiBcInRleHQvY3N2XCIgfSk7XG4gIGRvd25sb2FkQmxvYihibG9iLCBcInNlbnRpbmVseC1leHBvcnQtXCIgKyB0aW1lc3RhbXAoKSArIFwiLmNzdlwiKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGNvcHlBbGxJT0NzKGJ0bjogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgY29uc3QgY2FyZHMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcIi5pb2MtY2FyZFtkYXRhLWlvYy12YWx1ZV1cIik7XG4gIGNvbnN0IHNlZW4gPSBuZXcgU2V0PHN0cmluZz4oKTtcbiAgY29uc3QgdmFsdWVzOiBzdHJpbmdbXSA9IFtdO1xuXG4gIGNhcmRzLmZvckVhY2goKGNhcmQpID0+IHtcbiAgICBjb25zdCB2YWwgPSBjYXJkLmdldEF0dHJpYnV0ZShcImRhdGEtaW9jLXZhbHVlXCIpO1xuICAgIGlmICh2YWwgJiYgIXNlZW4uaGFzKHZhbCkpIHtcbiAgICAgIHNlZW4uYWRkKHZhbCk7XG4gICAgICB2YWx1ZXMucHVzaCh2YWwpO1xuICAgIH1cbiAgfSk7XG5cbiAgd3JpdGVUb0NsaXBib2FyZCh2YWx1ZXMuam9pbihcIlxcblwiKSwgYnRuKTtcbn1cbiIsICIvKipcbiAqIFB1cmUgdmVyZGljdCBjb21wdXRhdGlvbiBmdW5jdGlvbnMgXHUyMDE0IG5vIERPTSBhY2Nlc3MsIG5vIHNpZGUgZWZmZWN0cy5cbiAqXG4gKiBFeHRyYWN0ZWQgZnJvbSBlbnJpY2htZW50LnRzIChQaGFzZSAyKS4gVGhlc2UgZnVuY3Rpb25zIHRha2UgVmVyZGljdEVudHJ5W11cbiAqIGFycmF5cyBhbmQgcmV0dXJuIGNvbXB1dGVkIHJlc3VsdHMuIFRoZXkgYXJlIHRoZSBzaGFyZWQgY29tcHV0YXRpb24gbGF5ZXJcbiAqIHVzZWQgYnkgYm90aCByb3ctZmFjdG9yeS50cyAoc3VtbWFyeSByb3cgcmVuZGVyaW5nKSBhbmQgZW5yaWNobWVudC50c1xuICogKG9yY2hlc3RyYXRvciB2ZXJkaWN0IHRyYWNraW5nKS5cbiAqL1xuXG5pbXBvcnQgdHlwZSB7IFZlcmRpY3RLZXkgfSBmcm9tIFwiLi4vdHlwZXMvaW9jXCI7XG5pbXBvcnQgeyB2ZXJkaWN0U2V2ZXJpdHlJbmRleCB9IGZyb20gXCIuLi90eXBlcy9pb2NcIjtcblxuLyoqXG4gKiBQZXItcHJvdmlkZXIgdmVyZGljdCByZWNvcmQgYWNjdW11bGF0ZWQgZHVyaW5nIHRoZSBwb2xsaW5nIGxvb3AuXG4gKiBVc2VkIGZvciB3b3JzdC12ZXJkaWN0IGNvbXB1dGF0aW9uIGFjcm9zcyBhbGwgcHJvdmlkZXJzIGZvciBhbiBJT0MuXG4gKi9cbmV4cG9ydCBpbnRlcmZhY2UgVmVyZGljdEVudHJ5IHtcbiAgcHJvdmlkZXI6IHN0cmluZztcbiAgdmVyZGljdDogVmVyZGljdEtleTtcbiAgc3VtbWFyeVRleHQ6IHN0cmluZztcbiAgZGV0ZWN0aW9uQ291bnQ6IG51bWJlcjsgICAvLyBmcm9tIHJlc3VsdC5kZXRlY3Rpb25fY291bnQgKDAgZm9yIGVycm9ycylcbiAgdG90YWxFbmdpbmVzOiBudW1iZXI7ICAgICAvLyBmcm9tIHJlc3VsdC50b3RhbF9lbmdpbmVzICgwIGZvciBlcnJvcnMpXG4gIHN0YXRUZXh0OiBzdHJpbmc7ICAgICAgICAgLy8ga2V5IHN0YXQgc3RyaW5nIGZvciBkaXNwbGF5IChlLmcuLCBcIjQ1LzcyIGVuZ2luZXNcIilcbn1cblxuLyoqXG4gKiBDb21wdXRlIHRoZSB3b3JzdCAoaGlnaGVzdCBzZXZlcml0eSkgdmVyZGljdCBmcm9tIGEgbGlzdCBvZiBWZXJkaWN0RW50cnkgcmVjb3Jkcy5cbiAqXG4gKiBrbm93bl9nb29kIGZyb20gYW55IHByb3ZpZGVyIG92ZXJyaWRlcyBhbGwgb3RoZXIgdmVyZGljdHMgYXQgc3VtbWFyeSBsZXZlbC5cbiAqIFRoaXMgaXMgYW4gaW50ZW50aW9uYWwgZGVzaWduIGRlY2lzaW9uOiBrbm93bl9nb29kIChlLmcuIE5TUkwgbWF0Y2gpIG1lYW5zXG4gKiB0aGUgSU9DIGlzIGEgcmVjb2duaXplZCBzYWZlIGFydGlmYWN0IHJlZ2FyZGxlc3Mgb2Ygb3RoZXIgc2lnbmFscy5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgY29tcHV0ZVdvcnN0VmVyZGljdCgpIChsaW5lcyA1NDItNTUxKS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNvbXB1dGVXb3JzdFZlcmRpY3QoZW50cmllczogVmVyZGljdEVudHJ5W10pOiBWZXJkaWN0S2V5IHtcbiAgLy8ga25vd25fZ29vZCBmcm9tIGFueSBwcm92aWRlciBvdmVycmlkZXMgZXZlcnl0aGluZyBhdCBzdW1tYXJ5IGxldmVsXG4gIGlmIChlbnRyaWVzLnNvbWUoKGUpID0+IGUudmVyZGljdCA9PT0gXCJrbm93bl9nb29kXCIpKSB7XG4gICAgcmV0dXJuIFwia25vd25fZ29vZFwiO1xuICB9XG4gIGNvbnN0IHdvcnN0ID0gZmluZFdvcnN0RW50cnkoZW50cmllcyk7XG4gIHJldHVybiB3b3JzdCA/IHdvcnN0LnZlcmRpY3QgOiBcIm5vX2RhdGFcIjtcbn1cblxuLyoqXG4gKiBDb21wdXRlIGNvbnNlbnN1czogY291bnQgZmxhZ2dlZCAobWFsaWNpb3VzL3N1c3BpY2lvdXMpIGFuZCByZXNwb25kZWRcbiAqIChtYWxpY2lvdXMgKyBzdXNwaWNpb3VzICsgY2xlYW4pIHByb3ZpZGVycy5cbiAqIFBlciBkZXNpZ246IG5vX2RhdGEgYW5kIGVycm9yIGRvIE5PVCBjb3VudCBhcyB2b3Rlcy5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNvbXB1dGVDb25zZW5zdXMoZW50cmllczogVmVyZGljdEVudHJ5W10pOiB7IGZsYWdnZWQ6IG51bWJlcjsgcmVzcG9uZGVkOiBudW1iZXIgfSB7XG4gIGxldCBmbGFnZ2VkID0gMDtcbiAgbGV0IHJlc3BvbmRlZCA9IDA7XG4gIGZvciAoY29uc3QgZW50cnkgb2YgZW50cmllcykge1xuICAgIGlmIChlbnRyeS52ZXJkaWN0ID09PSBcIm1hbGljaW91c1wiIHx8IGVudHJ5LnZlcmRpY3QgPT09IFwic3VzcGljaW91c1wiKSB7XG4gICAgICBmbGFnZ2VkKys7XG4gICAgICByZXNwb25kZWQrKztcbiAgICB9IGVsc2UgaWYgKGVudHJ5LnZlcmRpY3QgPT09IFwiY2xlYW5cIikge1xuICAgICAgcmVzcG9uZGVkKys7XG4gICAgfVxuICAgIC8vIGVycm9yIGFuZCBub19kYXRhIGRvIE5PVCBjb3VudFxuICB9XG4gIHJldHVybiB7IGZsYWdnZWQsIHJlc3BvbmRlZCB9O1xufVxuXG4vKipcbiAqIFJldHVybiB0aGUgQ1NTIG1vZGlmaWVyIGNsYXNzIGZvciB0aGUgY29uc2Vuc3VzIGJhZGdlIGJhc2VkIG9uIGZsYWdnZWQgY291bnQuXG4gKiAwIGZsYWdnZWQgXHUyMTkyIGdyZWVuLCAxLTIgXHUyMTkyIHllbGxvdywgMysgXHUyMTkyIHJlZC5cbiAqXG4gKiBQaGFzZSAzOiBObyBsb25nZXIgY29uc3VtZWQgYnkgcm93LWZhY3RvcnkgKHJlcGxhY2VkIGJ5IHZlcmRpY3QgbWljcm8tYmFyKS5cbiAqIEtlcHQgZXhwb3J0ZWQgZm9yIEFQSSBzdGFiaWxpdHkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjb25zZW5zdXNCYWRnZUNsYXNzKGZsYWdnZWQ6IG51bWJlcik6IHN0cmluZyB7XG4gIGlmIChmbGFnZ2VkID09PSAwKSByZXR1cm4gXCJjb25zZW5zdXMtYmFkZ2UtLWdyZWVuXCI7XG4gIGlmIChmbGFnZ2VkIDw9IDIpIHJldHVybiBcImNvbnNlbnN1cy1iYWRnZS0teWVsbG93XCI7XG4gIHJldHVybiBcImNvbnNlbnN1cy1iYWRnZS0tcmVkXCI7XG59XG5cbi8qKlxuICogQ29tcHV0ZSBhdHRyaWJ1dGlvbjogZmluZCB0aGUgXCJtb3N0IGRldGFpbGVkXCIgcHJvdmlkZXIgdG8gc2hvdyBpbiBzdW1tYXJ5LlxuICogSGV1cmlzdGljOiBoaWdoZXN0IHRvdGFsRW5naW5lcyB3aW5zLiBUaWVzIGJyb2tlbiBieSB2ZXJkaWN0IHNldmVyaXR5IGRlc2NlbmRpbmcuXG4gKiBQcm92aWRlcnMgd2l0aCBub19kYXRhIG9yIGVycm9yIGFyZSBleGNsdWRlZCBhcyBjYW5kaWRhdGVzLlxuICovXG5leHBvcnQgZnVuY3Rpb24gY29tcHV0ZUF0dHJpYnV0aW9uKGVudHJpZXM6IFZlcmRpY3RFbnRyeVtdKTogeyBwcm92aWRlcjogc3RyaW5nOyB0ZXh0OiBzdHJpbmcgfSB7XG4gIC8vIE9ubHkgY2FuZGlkYXRlcyB3aXRoIGFjdHVhbCBkYXRhIChub3Qgbm9fZGF0YSBvciBlcnJvcilcbiAgY29uc3QgY2FuZGlkYXRlcyA9IGVudHJpZXMuZmlsdGVyKFxuICAgIChlKSA9PiBlLnZlcmRpY3QgIT09IFwibm9fZGF0YVwiICYmIGUudmVyZGljdCAhPT0gXCJlcnJvclwiXG4gICk7XG5cbiAgaWYgKGNhbmRpZGF0ZXMubGVuZ3RoID09PSAwKSB7XG4gICAgcmV0dXJuIHsgcHJvdmlkZXI6IFwiXCIsIHRleHQ6IFwiTm8gcHJvdmlkZXJzIHJldHVybmVkIGRhdGEgZm9yIHRoaXMgSU9DXCIgfTtcbiAgfVxuXG4gIC8vIFNvcnQ6IGhpZ2hlc3QgdG90YWxFbmdpbmVzIGZpcnN0LiBUaWVzIGJyb2tlbiBieSBzZXZlcml0eSBkZXNjZW5kaW5nLlxuICBjb25zdCBzb3J0ZWQgPSBbLi4uY2FuZGlkYXRlc10uc29ydCgoYSwgYikgPT4ge1xuICAgIGlmIChiLnRvdGFsRW5naW5lcyAhPT0gYS50b3RhbEVuZ2luZXMpIHJldHVybiBiLnRvdGFsRW5naW5lcyAtIGEudG90YWxFbmdpbmVzO1xuICAgIHJldHVybiB2ZXJkaWN0U2V2ZXJpdHlJbmRleChiLnZlcmRpY3QpIC0gdmVyZGljdFNldmVyaXR5SW5kZXgoYS52ZXJkaWN0KTtcbiAgfSk7XG5cbiAgY29uc3QgYmVzdCA9IHNvcnRlZFswXTtcbiAgaWYgKCFiZXN0KSByZXR1cm4geyBwcm92aWRlcjogXCJcIiwgdGV4dDogXCJObyBwcm92aWRlcnMgcmV0dXJuZWQgZGF0YSBmb3IgdGhpcyBJT0NcIiB9O1xuXG4gIHJldHVybiB7IHByb3ZpZGVyOiBiZXN0LnByb3ZpZGVyLCB0ZXh0OiBiZXN0LnByb3ZpZGVyICsgXCI6IFwiICsgYmVzdC5zdGF0VGV4dCB9O1xufVxuXG4vKipcbiAqIEZpbmQgdGhlIHdvcnN0IChoaWdoZXN0IHNldmVyaXR5KSBWZXJkaWN0RW50cnkgZnJvbSBhIGxpc3QuXG4gKiBSZXR1cm5zIHVuZGVmaW5lZCBpZiB0aGUgbGlzdCBpcyBlbXB0eS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGZpbmRXb3JzdEVudHJ5KGVudHJpZXM6IFZlcmRpY3RFbnRyeVtdKTogVmVyZGljdEVudHJ5IHwgdW5kZWZpbmVkIHtcbiAgY29uc3QgZmlyc3QgPSBlbnRyaWVzWzBdO1xuICBpZiAoIWZpcnN0KSByZXR1cm4gdW5kZWZpbmVkO1xuXG4gIGxldCB3b3JzdCA9IGZpcnN0O1xuICBmb3IgKGxldCBpID0gMTsgaSA8IGVudHJpZXMubGVuZ3RoOyBpKyspIHtcbiAgICBjb25zdCBjdXJyZW50ID0gZW50cmllc1tpXTtcbiAgICBpZiAoIWN1cnJlbnQpIGNvbnRpbnVlO1xuICAgIGlmICh2ZXJkaWN0U2V2ZXJpdHlJbmRleChjdXJyZW50LnZlcmRpY3QpID4gdmVyZGljdFNldmVyaXR5SW5kZXgod29yc3QudmVyZGljdCkpIHtcbiAgICAgIHdvcnN0ID0gY3VycmVudDtcbiAgICB9XG4gIH1cbiAgcmV0dXJuIHdvcnN0O1xufVxuIiwgIi8qKlxuICogRE9NIHJvdyBjb25zdHJ1Y3Rpb24gZm9yIGVucmljaG1lbnQgcmVzdWx0IGRpc3BsYXkuXG4gKlxuICogRXh0cmFjdGVkIGZyb20gZW5yaWNobWVudC50cyAoUGhhc2UgMikuIE93bnMgYWxsIERPTSBlbGVtZW50IGNyZWF0aW9uXG4gKiBmb3IgcHJvdmlkZXIgcm93cywgc3VtbWFyeSByb3dzLCBhbmQgY29udGV4dCBmaWVsZHMuIFRoZSBDT05URVhUX1BST1ZJREVSU1xuICogc2V0IGxpdmVzIGhlcmUgYXMgaXQgY29udHJvbHMgcm93IHJlbmRlcmluZyBkaXNwYXRjaC5cbiAqXG4gKiBEZXBlbmRzIG9uOlxuICogICAtIHZlcmRpY3QtY29tcHV0ZS50cyBmb3IgVmVyZGljdEVudHJ5IHR5cGUgYW5kIGNvbXB1dGF0aW9uIGZ1bmN0aW9uc1xuICogICAtIHR5cGVzL2FwaS50cyAgICAgICBmb3IgRW5yaWNobWVudFJlc3VsdEl0ZW0sIEVucmljaG1lbnRJdGVtXG4gKiAgIC0gdHlwZXMvaW9jLnRzICAgICAgIGZvciBWZXJkaWN0S2V5LCBWRVJESUNUX0xBQkVMU1xuICovXG5cbmltcG9ydCB0eXBlIHsgRW5yaWNobWVudEl0ZW0sIEVucmljaG1lbnRSZXN1bHRJdGVtIH0gZnJvbSBcIi4uL3R5cGVzL2FwaVwiO1xuaW1wb3J0IHR5cGUgeyBWZXJkaWN0S2V5IH0gZnJvbSBcIi4uL3R5cGVzL2lvY1wiO1xuaW1wb3J0IHsgVkVSRElDVF9MQUJFTFMgfSBmcm9tIFwiLi4vdHlwZXMvaW9jXCI7XG5pbXBvcnQgdHlwZSB7IFZlcmRpY3RFbnRyeSB9IGZyb20gXCIuL3ZlcmRpY3QtY29tcHV0ZVwiO1xuaW1wb3J0IHsgY29tcHV0ZVdvcnN0VmVyZGljdCwgY29tcHV0ZUF0dHJpYnV0aW9uIH0gZnJvbSBcIi4vdmVyZGljdC1jb21wdXRlXCI7XG5cbi8vIC0tLS0gUHJpdmF0ZSBoZWxwZXJzIC0tLS1cblxuLyoqXG4gKiBDb21wdXRlIHZlcmRpY3QgY2F0ZWdvcnkgY291bnRzIGZyb20gZW50cmllcyBmb3IgbWljcm8tYmFyIHJlbmRlcmluZy5cbiAqL1xuZnVuY3Rpb24gY29tcHV0ZVZlcmRpY3RDb3VudHMoZW50cmllczogVmVyZGljdEVudHJ5W10pOiB7XG4gIG1hbGljaW91czogbnVtYmVyOyBzdXNwaWNpb3VzOiBudW1iZXI7IGNsZWFuOiBudW1iZXI7IG5vRGF0YTogbnVtYmVyOyB0b3RhbDogbnVtYmVyO1xufSB7XG4gIGxldCBtYWxpY2lvdXMgPSAwLCBzdXNwaWNpb3VzID0gMCwgY2xlYW4gPSAwLCBub0RhdGEgPSAwO1xuICBmb3IgKGNvbnN0IGUgb2YgZW50cmllcykge1xuICAgIGlmIChlLnZlcmRpY3QgPT09IFwibWFsaWNpb3VzXCIpIG1hbGljaW91cysrO1xuICAgIGVsc2UgaWYgKGUudmVyZGljdCA9PT0gXCJzdXNwaWNpb3VzXCIpIHN1c3BpY2lvdXMrKztcbiAgICBlbHNlIGlmIChlLnZlcmRpY3QgPT09IFwiY2xlYW5cIikgY2xlYW4rKztcbiAgICBlbHNlIG5vRGF0YSsrO1xuICB9XG4gIHJldHVybiB7IG1hbGljaW91cywgc3VzcGljaW91cywgY2xlYW4sIG5vRGF0YSwgdG90YWw6IGVudHJpZXMubGVuZ3RoIH07XG59XG5cbi8qKlxuICogRm9ybWF0IGFuIElTTyA4NjAxIGRhdGUgc3RyaW5nIGZvciBkaXNwbGF5LlxuICogUmV0dXJucyBcIlwiIGZvciBudWxsIGlucHV0IChzY2FuX2RhdGUgY2FuIGJlIG51bGwgcGVyIEFQSSBjb250cmFjdCkuXG4gKiBTb3VyY2U6IG1haW4uanMgZm9ybWF0RGF0ZSgpIChsaW5lcyA1ODEtNTg4KS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGZvcm1hdERhdGUoaXNvOiBzdHJpbmcgfCBudWxsKTogc3RyaW5nIHtcbiAgaWYgKCFpc28pIHJldHVybiBcIlwiO1xuICB0cnkge1xuICAgIHJldHVybiBuZXcgRGF0ZShpc28pLnRvTG9jYWxlRGF0ZVN0cmluZygpO1xuICB9IGNhdGNoIHtcbiAgICByZXR1cm4gaXNvO1xuICB9XG59XG5cbi8qKlxuICogRm9ybWF0IGFuIElTTyA4NjAxIHRpbWVzdGFtcCBhcyBhIHJlbGF0aXZlIHRpbWUgc3RyaW5nIChlLmcuIFwiMmggYWdvXCIpLlxuICogRmFsbHMgYmFjayB0byB0aGUgcmF3IElTTyBzdHJpbmcgaWYgcGFyc2luZyBmYWlscy5cbiAqL1xuZnVuY3Rpb24gZm9ybWF0UmVsYXRpdmVUaW1lKGlzbzogc3RyaW5nKTogc3RyaW5nIHtcbiAgdHJ5IHtcbiAgICBjb25zdCBkaWZmTXMgPSBEYXRlLm5vdygpIC0gbmV3IERhdGUoaXNvKS5nZXRUaW1lKCk7XG4gICAgY29uc3QgZGlmZk1pbiA9IE1hdGguZmxvb3IoZGlmZk1zIC8gNjAwMDApO1xuICAgIGlmIChkaWZmTWluIDwgMSkgcmV0dXJuIFwianVzdCBub3dcIjtcbiAgICBpZiAoZGlmZk1pbiA8IDYwKSByZXR1cm4gZGlmZk1pbiArIFwibSBhZ29cIjtcbiAgICBjb25zdCBkaWZmSHIgPSBNYXRoLmZsb29yKGRpZmZNaW4gLyA2MCk7XG4gICAgaWYgKGRpZmZIciA8IDI0KSByZXR1cm4gZGlmZkhyICsgXCJoIGFnb1wiO1xuICAgIGNvbnN0IGRpZmZEYXkgPSBNYXRoLmZsb29yKGRpZmZIciAvIDI0KTtcbiAgICByZXR1cm4gZGlmZkRheSArIFwiZCBhZ29cIjtcbiAgfSBjYXRjaCB7XG4gICAgcmV0dXJuIGlzbztcbiAgfVxufVxuXG4vLyAtLS0tIFByb3ZpZGVyIGNvbnRleHQgZmllbGQgZGVmaW5pdGlvbnMgLS0tLVxuXG4vKiogTWFwcGluZyBvZiBwcm92aWRlciBuYW1lIC0+IGZpZWxkcyB0byBleHRyYWN0IGZyb20gcmF3X3N0YXRzLiAqL1xuaW50ZXJmYWNlIENvbnRleHRGaWVsZERlZiB7XG4gIGtleTogc3RyaW5nO1xuICBsYWJlbDogc3RyaW5nO1xuICB0eXBlOiBcInRleHRcIiB8IFwidGFnc1wiO1xufVxuXG5jb25zdCBQUk9WSURFUl9DT05URVhUX0ZJRUxEUzogUmVjb3JkPHN0cmluZywgQ29udGV4dEZpZWxkRGVmW10+ID0ge1xuICBWaXJ1c1RvdGFsOiBbXG4gICAgeyBrZXk6IFwidG9wX2RldGVjdGlvbnNcIiwgbGFiZWw6IFwiRGV0ZWN0aW9uc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcInJlcHV0YXRpb25cIiwgbGFiZWw6IFwiUmVwdXRhdGlvblwiLCB0eXBlOiBcInRleHRcIiB9LFxuICBdLFxuICBNYWx3YXJlQmF6YWFyOiBbXG4gICAgeyBrZXk6IFwic2lnbmF0dXJlXCIsIGxhYmVsOiBcIlNpZ25hdHVyZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInRhZ3NcIiwgbGFiZWw6IFwiVGFnc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcImZpbGVfdHlwZVwiLCBsYWJlbDogXCJGaWxlIHR5cGVcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJmaXJzdF9zZWVuXCIsIGxhYmVsOiBcIkZpcnN0IHNlZW5cIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJsYXN0X3NlZW5cIiwgbGFiZWw6IFwiTGFzdCBzZWVuXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIFRocmVhdEZveDogW1xuICAgIHsga2V5OiBcIm1hbHdhcmVfcHJpbnRhYmxlXCIsIGxhYmVsOiBcIk1hbHdhcmVcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJ0aHJlYXRfdHlwZVwiLCBsYWJlbDogXCJUaHJlYXQgdHlwZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImNvbmZpZGVuY2VfbGV2ZWxcIiwgbGFiZWw6IFwiQ29uZmlkZW5jZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICBdLFxuICBBYnVzZUlQREI6IFtcbiAgICB7IGtleTogXCJhYnVzZUNvbmZpZGVuY2VTY29yZVwiLCBsYWJlbDogXCJDb25maWRlbmNlXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwidG90YWxSZXBvcnRzXCIsIGxhYmVsOiBcIlJlcG9ydHNcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJjb3VudHJ5Q29kZVwiLCBsYWJlbDogXCJDb3VudHJ5XCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwiaXNwXCIsIGxhYmVsOiBcIklTUFwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInVzYWdlVHlwZVwiLCBsYWJlbDogXCJVc2FnZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICBdLFxuICBcIlNob2RhbiBJbnRlcm5ldERCXCI6IFtcbiAgICB7IGtleTogXCJwb3J0c1wiLCBsYWJlbDogXCJQb3J0c1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcInZ1bG5zXCIsIGxhYmVsOiBcIlZ1bG5zXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwiaG9zdG5hbWVzXCIsIGxhYmVsOiBcIkhvc3RuYW1lc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcImNwZXNcIiwgbGFiZWw6IFwiQ1BFc1wiLCB0eXBlOiBcInRhZ3NcIiB9LCAgICAgIC8vIEVQUk9WLTAxXG4gICAgeyBrZXk6IFwidGFnc1wiLCBsYWJlbDogXCJUYWdzXCIsIHR5cGU6IFwidGFnc1wiIH0sICAgICAgLy8gRVBST1YtMDFcbiAgXSxcbiAgXCJDSVJDTCBIYXNobG9va3VwXCI6IFtcbiAgICB7IGtleTogXCJmaWxlX25hbWVcIiwgbGFiZWw6IFwiRmlsZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInNvdXJjZVwiLCBsYWJlbDogXCJTb3VyY2VcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgXSxcbiAgXCJHcmV5Tm9pc2UgQ29tbXVuaXR5XCI6IFtcbiAgICB7IGtleTogXCJub2lzZVwiLCBsYWJlbDogXCJOb2lzZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInJpb3RcIiwgbGFiZWw6IFwiUklPVFwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImNsYXNzaWZpY2F0aW9uXCIsIGxhYmVsOiBcIkNsYXNzaWZpY2F0aW9uXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIFVSTGhhdXM6IFtcbiAgICB7IGtleTogXCJ0aHJlYXRcIiwgbGFiZWw6IFwiVGhyZWF0XCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwidXJsX3N0YXR1c1wiLCBsYWJlbDogXCJTdGF0dXNcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJ0YWdzXCIsIGxhYmVsOiBcIlRhZ3NcIiwgdHlwZTogXCJ0YWdzXCIgfSxcbiAgXSxcbiAgXCJPVFggQWxpZW5WYXVsdFwiOiBbXG4gICAgeyBrZXk6IFwicHVsc2VfY291bnRcIiwgbGFiZWw6IFwiUHVsc2VzXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwicmVwdXRhdGlvblwiLCBsYWJlbDogXCJSZXB1dGF0aW9uXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIFwiSVAgQ29udGV4dFwiOiBbXG4gICAgeyBrZXk6IFwiZ2VvXCIsIGxhYmVsOiBcIkxvY2F0aW9uXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwicmV2ZXJzZVwiLCBsYWJlbDogXCJQVFJcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJmbGFnc1wiLCBsYWJlbDogXCJGbGFnc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICBdLFxuICBcIkROUyBSZWNvcmRzXCI6IFtcbiAgICB7IGtleTogXCJhXCIsICAgbGFiZWw6IFwiQVwiLCAgIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwibXhcIiwgIGxhYmVsOiBcIk1YXCIsICB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcIm5zXCIsICBsYWJlbDogXCJOU1wiLCAgdHlwZTogXCJ0YWdzXCIgfSxcbiAgICB7IGtleTogXCJ0eHRcIiwgbGFiZWw6IFwiVFhUXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gIF0sXG4gIFwiQ2VydCBIaXN0b3J5XCI6IFtcbiAgICB7IGtleTogXCJjZXJ0X2NvdW50XCIsIGxhYmVsOiBcIkNlcnRzXCIsICAgICAgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJlYXJsaWVzdFwiLCAgIGxhYmVsOiBcIkZpcnN0IHNlZW5cIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJsYXRlc3RcIiwgICAgIGxhYmVsOiBcIkxhdGVzdFwiLCAgICAgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJzdWJkb21haW5zXCIsIGxhYmVsOiBcIlN1YmRvbWFpbnNcIiwgdHlwZTogXCJ0YWdzXCIgfSxcbiAgXSxcbiAgVGhyZWF0TWluZXI6IFtcbiAgICB7IGtleTogXCJwYXNzaXZlX2Ruc1wiLCBsYWJlbDogXCJQYXNzaXZlIEROU1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcInNhbXBsZXNcIiwgICAgIGxhYmVsOiBcIlNhbXBsZXNcIiwgICAgIHR5cGU6IFwidGFnc1wiIH0sXG4gIF0sXG4gIFwiQVNOIEludGVsXCI6IFtcbiAgICB7IGtleTogXCJhc25cIiwgICAgICAgbGFiZWw6IFwiQVNOXCIsICAgICAgIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwicHJlZml4XCIsICAgIGxhYmVsOiBcIlByZWZpeFwiLCAgICB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInJpclwiLCAgICAgICBsYWJlbDogXCJSSVJcIiwgICAgICAgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJhbGxvY2F0ZWRcIiwgbGFiZWw6IFwiQWxsb2NhdGVkXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG59O1xuXG4vKipcbiAqIFByb3ZpZGVycyB0aGF0IHVzZSB0aGUgY29udGV4dCByb3cgcmVuZGVyaW5nIHBhdGggKG5vIHZlcmRpY3QgYmFkZ2UsIHBpbm5lZCB0byB0b3ApLlxuICogRXh0ZW5kIHRoaXMgc2V0IHdoZW4gYWRkaW5nIG5ldyBjb250ZXh0LW9ubHkgcHJvdmlkZXJzLlxuICovXG5leHBvcnQgY29uc3QgQ09OVEVYVF9QUk9WSURFUlMgPSBuZXcgU2V0KFtcIklQIENvbnRleHRcIiwgXCJETlMgUmVjb3Jkc1wiLCBcIkNlcnQgSGlzdG9yeVwiLCBcIlRocmVhdE1pbmVyXCIsIFwiQVNOIEludGVsXCJdKTtcblxuLyoqXG4gKiBDcmVhdGUgYSBsYWJlbGVkIGNvbnRleHQgZmllbGQgZWxlbWVudCB3aXRoIHRoZSBwcm92aWRlci1jb250ZXh0LWZpZWxkIGNsYXNzLlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmZ1bmN0aW9uIGNyZWF0ZUxhYmVsZWRGaWVsZChsYWJlbDogc3RyaW5nKTogSFRNTEVsZW1lbnQge1xuICBjb25zdCBmaWVsZEVsID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gIGZpZWxkRWwuY2xhc3NOYW1lID0gXCJwcm92aWRlci1jb250ZXh0LWZpZWxkXCI7XG5cbiAgY29uc3QgbGFiZWxFbCA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBsYWJlbEVsLmNsYXNzTmFtZSA9IFwicHJvdmlkZXItY29udGV4dC1sYWJlbFwiO1xuICBsYWJlbEVsLnRleHRDb250ZW50ID0gbGFiZWwgKyBcIjogXCI7XG4gIGZpZWxkRWwuYXBwZW5kQ2hpbGQobGFiZWxFbCk7XG5cbiAgcmV0dXJuIGZpZWxkRWw7XG59XG5cbi8qKlxuICogQ3JlYXRlIGNvbnRleHR1YWwgZmllbGRzIGZyb20gYSBwcm92aWRlciByZXN1bHQncyByYXdfc3RhdHMuXG4gKiBSZXR1cm5zIG51bGwgaWYgbm8gY29udGV4dCBmaWVsZHMgYXJlIGF2YWlsYWJsZSBmb3IgdGhpcyBwcm92aWRlci5cbiAqIEFsbCBET00gY29uc3RydWN0aW9uIHVzZXMgY3JlYXRlRWxlbWVudCArIHRleHRDb250ZW50IChTRUMtMDgpLlxuICovXG5mdW5jdGlvbiBjcmVhdGVDb250ZXh0RmllbGRzKHJlc3VsdDogRW5yaWNobWVudFJlc3VsdEl0ZW0pOiBIVE1MRWxlbWVudCB8IG51bGwge1xuICBjb25zdCBmaWVsZERlZnMgPSBQUk9WSURFUl9DT05URVhUX0ZJRUxEU1tyZXN1bHQucHJvdmlkZXJdO1xuICBpZiAoIWZpZWxkRGVmcykgcmV0dXJuIG51bGw7XG5cbiAgY29uc3Qgc3RhdHMgPSByZXN1bHQucmF3X3N0YXRzO1xuICBpZiAoIXN0YXRzKSByZXR1cm4gbnVsbDtcblxuICBjb25zdCBjb250YWluZXIgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiZGl2XCIpO1xuICBjb250YWluZXIuY2xhc3NOYW1lID0gXCJwcm92aWRlci1jb250ZXh0XCI7XG5cbiAgbGV0IGhhc0ZpZWxkcyA9IGZhbHNlO1xuXG4gIGZvciAoY29uc3QgZGVmIG9mIGZpZWxkRGVmcykge1xuICAgIGNvbnN0IHZhbHVlID0gc3RhdHNbZGVmLmtleV07XG4gICAgaWYgKHZhbHVlID09PSB1bmRlZmluZWQgfHwgdmFsdWUgPT09IG51bGwgfHwgdmFsdWUgPT09IFwiXCIpIGNvbnRpbnVlO1xuXG4gICAgaWYgKGRlZi50eXBlID09PSBcInRhZ3NcIiAmJiBBcnJheS5pc0FycmF5KHZhbHVlKSAmJiB2YWx1ZS5sZW5ndGggPiAwKSB7XG4gICAgICBjb25zdCBmaWVsZEVsID0gY3JlYXRlTGFiZWxlZEZpZWxkKGRlZi5sYWJlbCk7XG4gICAgICBmb3IgKGNvbnN0IHRhZyBvZiB2YWx1ZSkge1xuICAgICAgICBpZiAodHlwZW9mIHRhZyAhPT0gXCJzdHJpbmdcIiAmJiB0eXBlb2YgdGFnICE9PSBcIm51bWJlclwiKSBjb250aW51ZTtcbiAgICAgICAgY29uc3QgdGFnRWwgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICAgICAgdGFnRWwuY2xhc3NOYW1lID0gXCJjb250ZXh0LXRhZ1wiO1xuICAgICAgICB0YWdFbC50ZXh0Q29udGVudCA9IFN0cmluZyh0YWcpO1xuICAgICAgICBmaWVsZEVsLmFwcGVuZENoaWxkKHRhZ0VsKTtcbiAgICAgIH1cbiAgICAgIGNvbnRhaW5lci5hcHBlbmRDaGlsZChmaWVsZEVsKTtcbiAgICAgIGhhc0ZpZWxkcyA9IHRydWU7XG4gICAgfSBlbHNlIGlmIChkZWYudHlwZSA9PT0gXCJ0ZXh0XCIgJiYgKHR5cGVvZiB2YWx1ZSA9PT0gXCJzdHJpbmdcIiB8fCB0eXBlb2YgdmFsdWUgPT09IFwibnVtYmVyXCIgfHwgdHlwZW9mIHZhbHVlID09PSBcImJvb2xlYW5cIikpIHtcbiAgICAgIGNvbnN0IGZpZWxkRWwgPSBjcmVhdGVMYWJlbGVkRmllbGQoZGVmLmxhYmVsKTtcbiAgICAgIGNvbnN0IHZhbEVsID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gICAgICB2YWxFbC50ZXh0Q29udGVudCA9IFN0cmluZyh2YWx1ZSk7XG4gICAgICBmaWVsZEVsLmFwcGVuZENoaWxkKHZhbEVsKTtcbiAgICAgIGNvbnRhaW5lci5hcHBlbmRDaGlsZChmaWVsZEVsKTtcbiAgICAgIGhhc0ZpZWxkcyA9IHRydWU7XG4gICAgfVxuICB9XG5cbiAgcmV0dXJuIGhhc0ZpZWxkcyA/IGNvbnRhaW5lciA6IG51bGw7XG59XG5cbi8vIC0tLS0gRXhwb3J0ZWQgcm93IGJ1aWxkZXJzIC0tLS1cblxuLyoqXG4gKiBHZXQgb3IgY3JlYXRlIHRoZSAuaW9jLXN1bW1hcnktcm93IGVsZW1lbnQgaW5zaWRlIHRoZSBzbG90LlxuICogSW5zZXJ0cyBiZWZvcmUgLmNoZXZyb24tdG9nZ2xlIGlmIHByZXNlbnQsIG90aGVyd2lzZSBhcyBmaXJzdCBjaGlsZC5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGdldE9yQ3JlYXRlU3VtbWFyeVJvdyhzbG90OiBIVE1MRWxlbWVudCk6IEhUTUxFbGVtZW50IHtcbiAgY29uc3QgZXhpc3RpbmcgPSBzbG90LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLmlvYy1zdW1tYXJ5LXJvd1wiKTtcbiAgaWYgKGV4aXN0aW5nKSByZXR1cm4gZXhpc3Rpbmc7XG5cbiAgY29uc3Qgcm93ID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcImRpdlwiKTtcbiAgcm93LmNsYXNzTmFtZSA9IFwiaW9jLXN1bW1hcnktcm93XCI7XG5cbiAgLy8gSW5zZXJ0IGJlZm9yZSBjaGV2cm9uLXRvZ2dsZSBpZiBwcmVzZW50XG4gIGNvbnN0IGNoZXZyb24gPSBzbG90LnF1ZXJ5U2VsZWN0b3IoXCIuY2hldnJvbi10b2dnbGVcIik7XG4gIGlmIChjaGV2cm9uKSB7XG4gICAgc2xvdC5pbnNlcnRCZWZvcmUocm93LCBjaGV2cm9uKTtcbiAgfSBlbHNlIHtcbiAgICBzbG90LmFwcGVuZENoaWxkKHJvdyk7XG4gIH1cblxuICByZXR1cm4gcm93O1xufVxuXG4vKipcbiAqIFVwZGF0ZSAob3IgY3JlYXRlKSB0aGUgc3VtbWFyeSByb3cgZm9yIGFuIElPQyBpbiBpdHMgZW5yaWNobWVudCBzbG90LlxuICogU2hvd3Mgd29yc3QgdmVyZGljdCBiYWRnZSwgYXR0cmlidXRpb24gdGV4dCwgYW5kIGNvbnNlbnN1cyBiYWRnZS5cbiAqIEFsbCBET00gY29uc3RydWN0aW9uIHVzZXMgY3JlYXRlRWxlbWVudCArIHRleHRDb250ZW50IChTRUMtMDgpLlxuICovXG5leHBvcnQgZnVuY3Rpb24gdXBkYXRlU3VtbWFyeVJvdyhcbiAgc2xvdDogSFRNTEVsZW1lbnQsXG4gIGlvY1ZhbHVlOiBzdHJpbmcsXG4gIGlvY1ZlcmRpY3RzOiBSZWNvcmQ8c3RyaW5nLCBWZXJkaWN0RW50cnlbXT5cbik6IHZvaWQge1xuICBjb25zdCBlbnRyaWVzID0gaW9jVmVyZGljdHNbaW9jVmFsdWVdO1xuICBpZiAoIWVudHJpZXMgfHwgZW50cmllcy5sZW5ndGggPT09IDApIHJldHVybjtcblxuICBjb25zdCB3b3JzdFZlcmRpY3QgPSBjb21wdXRlV29yc3RWZXJkaWN0KGVudHJpZXMpO1xuICBjb25zdCBhdHRyaWJ1dGlvbiA9IGNvbXB1dGVBdHRyaWJ1dGlvbihlbnRyaWVzKTtcblxuICBjb25zdCBzdW1tYXJ5Um93ID0gZ2V0T3JDcmVhdGVTdW1tYXJ5Um93KHNsb3QpO1xuXG4gIC8vIENsZWFyIGV4aXN0aW5nIGNoaWxkcmVuIChpbW11dGFibGUgcmVidWlsZCBwYXR0ZXJuKVxuICBzdW1tYXJ5Um93LnRleHRDb250ZW50ID0gXCJcIjtcblxuICAvLyBhLiBWZXJkaWN0IGJhZGdlXG4gIGNvbnN0IHZlcmRpY3RCYWRnZSA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICB2ZXJkaWN0QmFkZ2UuY2xhc3NOYW1lID0gXCJ2ZXJkaWN0LWJhZGdlIHZlcmRpY3QtXCIgKyB3b3JzdFZlcmRpY3Q7XG4gIHZlcmRpY3RCYWRnZS50ZXh0Q29udGVudCA9IFZFUkRJQ1RfTEFCRUxTW3dvcnN0VmVyZGljdF07XG4gIHN1bW1hcnlSb3cuYXBwZW5kQ2hpbGQodmVyZGljdEJhZGdlKTtcblxuICAvLyBiLiBBdHRyaWJ1dGlvbiB0ZXh0XG4gIGNvbnN0IGF0dHJpYnV0aW9uU3BhbiA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBhdHRyaWJ1dGlvblNwYW4uY2xhc3NOYW1lID0gXCJpb2Mtc3VtbWFyeS1hdHRyaWJ1dGlvblwiO1xuICBhdHRyaWJ1dGlvblNwYW4udGV4dENvbnRlbnQgPSBhdHRyaWJ1dGlvbi50ZXh0O1xuICBzdW1tYXJ5Um93LmFwcGVuZENoaWxkKGF0dHJpYnV0aW9uU3Bhbik7XG5cbiAgLy8gYy4gVmVyZGljdCBtaWNyby1iYXIgKHJlcGxhY2VzIGNvbnNlbnN1cyBiYWRnZSlcbiAgY29uc3QgY291bnRzID0gY29tcHV0ZVZlcmRpY3RDb3VudHMoZW50cmllcyk7XG4gIGNvbnN0IHRvdGFsID0gTWF0aC5tYXgoMSwgY291bnRzLnRvdGFsKTtcbiAgY29uc3QgbWljcm9CYXIgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiZGl2XCIpO1xuICBtaWNyb0Jhci5jbGFzc05hbWUgPSBcInZlcmRpY3QtbWljcm8tYmFyXCI7XG4gIG1pY3JvQmFyLnNldEF0dHJpYnV0ZShcInRpdGxlXCIsXG4gICAgYCR7Y291bnRzLm1hbGljaW91c30gbWFsaWNpb3VzLCAke2NvdW50cy5zdXNwaWNpb3VzfSBzdXNwaWNpb3VzLCAke2NvdW50cy5jbGVhbn0gY2xlYW4sICR7Y291bnRzLm5vRGF0YX0gbm8gZGF0YWBcbiAgKTtcbiAgY29uc3Qgc2VnbWVudHM6IEFycmF5PFtudW1iZXIsIHN0cmluZ10+ID0gW1xuICAgIFtjb3VudHMubWFsaWNpb3VzLCBcIm1hbGljaW91c1wiXSxcbiAgICBbY291bnRzLnN1c3BpY2lvdXMsIFwic3VzcGljaW91c1wiXSxcbiAgICBbY291bnRzLmNsZWFuLCBcImNsZWFuXCJdLFxuICAgIFtjb3VudHMubm9EYXRhLCBcIm5vX2RhdGFcIl0sXG4gIF07XG4gIGZvciAoY29uc3QgW2NvdW50LCB2ZXJkaWN0XSBvZiBzZWdtZW50cykge1xuICAgIGlmIChjb3VudCA9PT0gMCkgY29udGludWU7XG4gICAgY29uc3Qgc2VnID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcImRpdlwiKTtcbiAgICBzZWcuY2xhc3NOYW1lID0gXCJtaWNyby1iYXItc2VnbWVudCBtaWNyby1iYXItc2VnbWVudC0tXCIgKyB2ZXJkaWN0O1xuICAgIHNlZy5zdHlsZS53aWR0aCA9IE1hdGgucm91bmQoKGNvdW50IC8gdG90YWwpICogMTAwKSArIFwiJVwiO1xuICAgIG1pY3JvQmFyLmFwcGVuZENoaWxkKHNlZyk7XG4gIH1cbiAgc3VtbWFyeVJvdy5hcHBlbmRDaGlsZChtaWNyb0Jhcik7XG59XG5cbi8qKlxuICogQ3JlYXRlIGEgY29udGV4dCByb3cgXHUyMDE0IHB1cmVseSBpbmZvcm1hdGlvbmFsLCBubyB2ZXJkaWN0IGJhZGdlLlxuICogQ29udGV4dCBwcm92aWRlcnMgKElQIENvbnRleHQsIEROUyBSZWNvcmRzLCBDZXJ0IEhpc3RvcnkpIGNhcnJ5IG1ldGFkYXRhXG4gKiBhbmQgbXVzdCBub3QgcGFydGljaXBhdGUgaW4gY29uc2Vuc3VzL2F0dHJpYnV0aW9uIG9yIGNhcmQgdmVyZGljdCB1cGRhdGVzLlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjcmVhdGVDb250ZXh0Um93KHJlc3VsdDogRW5yaWNobWVudFJlc3VsdEl0ZW0pOiBIVE1MRWxlbWVudCB7XG4gIGNvbnN0IHJvdyA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIik7XG4gIHJvdy5jbGFzc05hbWUgPSBcInByb3ZpZGVyLWRldGFpbC1yb3cgcHJvdmlkZXItY29udGV4dC1yb3dcIjtcbiAgcm93LnNldEF0dHJpYnV0ZShcImRhdGEtdmVyZGljdFwiLCBcImNvbnRleHRcIik7IC8vIHNlbnRpbmVsIGZvciBzb3J0IHBpbm5pbmdcblxuICBjb25zdCBuYW1lU3BhbiA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBuYW1lU3Bhbi5jbGFzc05hbWUgPSBcInByb3ZpZGVyLWRldGFpbC1uYW1lXCI7XG4gIG5hbWVTcGFuLnRleHRDb250ZW50ID0gcmVzdWx0LnByb3ZpZGVyO1xuICByb3cuYXBwZW5kQ2hpbGQobmFtZVNwYW4pO1xuXG4gIC8vIE5PIHZlcmRpY3QgYmFkZ2UgXHUyMDE0IElQIENvbnRleHQgaXMgcHVyZWx5IGluZm9ybWF0aW9uYWxcblxuICAvLyBBZGQgY29udGV4dCBmaWVsZHMgKGdlbywgUFRSLCBmbGFncykgdXNpbmcgZXhpc3RpbmcgY3JlYXRlQ29udGV4dEZpZWxkcygpXG4gIGNvbnN0IGNvbnRleHRFbCA9IGNyZWF0ZUNvbnRleHRGaWVsZHMocmVzdWx0KTtcbiAgaWYgKGNvbnRleHRFbCkge1xuICAgIHJvdy5hcHBlbmRDaGlsZChjb250ZXh0RWwpO1xuICB9XG5cbiAgLy8gQ2FjaGUgYmFkZ2UgaWYgcmVzdWx0IHdhcyBzZXJ2ZWQgZnJvbSBjYWNoZVxuICBpZiAocmVzdWx0LmNhY2hlZF9hdCkge1xuICAgIGNvbnN0IGNhY2hlQmFkZ2UgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICBjYWNoZUJhZGdlLmNsYXNzTmFtZSA9IFwiY2FjaGUtYmFkZ2VcIjtcbiAgICBjYWNoZUJhZGdlLnRleHRDb250ZW50ID0gXCJjYWNoZWQgXCIgKyBmb3JtYXRSZWxhdGl2ZVRpbWUocmVzdWx0LmNhY2hlZF9hdCk7XG4gICAgcm93LmFwcGVuZENoaWxkKGNhY2hlQmFkZ2UpO1xuICB9XG5cbiAgcmV0dXJuIHJvdztcbn1cblxuLyoqXG4gKiBDcmVhdGUgYSBzaW5nbGUgcHJvdmlkZXIgZGV0YWlsIHJvdyBmb3IgdGhlIC5lbnJpY2htZW50LWRldGFpbHMgY29udGFpbmVyLlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjcmVhdGVEZXRhaWxSb3coXG4gIHByb3ZpZGVyOiBzdHJpbmcsXG4gIHZlcmRpY3Q6IFZlcmRpY3RLZXksXG4gIHN0YXRUZXh0OiBzdHJpbmcsXG4gIHJlc3VsdD86IEVucmljaG1lbnRJdGVtXG4pOiBIVE1MRWxlbWVudCB7XG4gIGNvbnN0IHJvdyA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIik7XG4gIGNvbnN0IGlzTm9EYXRhID0gdmVyZGljdCA9PT0gXCJub19kYXRhXCIgfHwgdmVyZGljdCA9PT0gXCJlcnJvclwiO1xuICByb3cuY2xhc3NOYW1lID0gXCJwcm92aWRlci1kZXRhaWwtcm93XCIgKyAoaXNOb0RhdGEgPyBcIiBwcm92aWRlci1yb3ctLW5vLWRhdGFcIiA6IFwiXCIpO1xuICByb3cuc2V0QXR0cmlidXRlKFwiZGF0YS12ZXJkaWN0XCIsIHZlcmRpY3QpO1xuXG4gIGNvbnN0IG5hbWVTcGFuID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gIG5hbWVTcGFuLmNsYXNzTmFtZSA9IFwicHJvdmlkZXItZGV0YWlsLW5hbWVcIjtcbiAgbmFtZVNwYW4udGV4dENvbnRlbnQgPSBwcm92aWRlcjtcblxuICBjb25zdCBiYWRnZSA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBiYWRnZS5jbGFzc05hbWUgPSBcInZlcmRpY3QtYmFkZ2UgdmVyZGljdC1cIiArIHZlcmRpY3Q7XG4gIGJhZGdlLnRleHRDb250ZW50ID0gVkVSRElDVF9MQUJFTFNbdmVyZGljdF07XG5cbiAgY29uc3Qgc3RhdFNwYW4gPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgc3RhdFNwYW4uY2xhc3NOYW1lID0gXCJwcm92aWRlci1kZXRhaWwtc3RhdFwiO1xuICBzdGF0U3Bhbi50ZXh0Q29udGVudCA9IHN0YXRUZXh0O1xuXG4gIHJvdy5hcHBlbmRDaGlsZChuYW1lU3Bhbik7XG4gIHJvdy5hcHBlbmRDaGlsZChiYWRnZSk7XG4gIHJvdy5hcHBlbmRDaGlsZChzdGF0U3Bhbik7XG5cbiAgLy8gQ2FjaGUgYmFkZ2UgXHUyMDE0IHNob3cgcmVsYXRpdmUgdGltZSBpZiByZXN1bHQgd2FzIHNlcnZlZCBmcm9tIGNhY2hlXG4gIGlmIChyZXN1bHQgJiYgcmVzdWx0LnR5cGUgPT09IFwicmVzdWx0XCIgJiYgcmVzdWx0LmNhY2hlZF9hdCkge1xuICAgIGNvbnN0IGNhY2hlQmFkZ2UgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICBjYWNoZUJhZGdlLmNsYXNzTmFtZSA9IFwiY2FjaGUtYmFkZ2VcIjtcbiAgICBjb25zdCBhZ28gPSBmb3JtYXRSZWxhdGl2ZVRpbWUocmVzdWx0LmNhY2hlZF9hdCk7XG4gICAgY2FjaGVCYWRnZS50ZXh0Q29udGVudCA9IFwiY2FjaGVkIFwiICsgYWdvO1xuICAgIHJvdy5hcHBlbmRDaGlsZChjYWNoZUJhZGdlKTtcbiAgfVxuXG4gIC8vIENvbnRleHQgZmllbGRzIFx1MjAxNCBwcm92aWRlci1zcGVjaWZpYyBpbnRlbGxpZ2VuY2UgZnJvbSByYXdfc3RhdHNcbiAgaWYgKHJlc3VsdCAmJiByZXN1bHQudHlwZSA9PT0gXCJyZXN1bHRcIikge1xuICAgIGNvbnN0IGNvbnRleHRFbCA9IGNyZWF0ZUNvbnRleHRGaWVsZHMocmVzdWx0KTtcbiAgICBpZiAoY29udGV4dEVsKSB7XG4gICAgICByb3cuYXBwZW5kQ2hpbGQoY29udGV4dEVsKTtcbiAgICB9XG4gIH1cblxuICByZXR1cm4gcm93O1xufVxuXG4vKipcbiAqIFVuaWZpZWQgcm93IGNyZWF0aW9uIGRpc3BhdGNoZXIgXHUyMDE0IHJvdXRlcyB0byBjcmVhdGVDb250ZXh0Um93IG9yIGNyZWF0ZURldGFpbFJvd1xuICogYmFzZWQgb24gdGhlIGtpbmQgcGFyYW1ldGVyLiBQcm92aWRlcyBhIHN0YWJsZSBBUEkgZm9yIFBoYXNlIDMgdmlzdWFsIHdvcmsuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjcmVhdGVQcm92aWRlclJvdyhcbiAgcmVzdWx0OiBFbnJpY2htZW50UmVzdWx0SXRlbSxcbiAga2luZDogXCJjb250ZXh0XCIgfCBcImRldGFpbFwiLFxuICBzdGF0VGV4dDogc3RyaW5nXG4pOiBIVE1MRWxlbWVudCB7XG4gIGlmIChraW5kID09PSBcImNvbnRleHRcIikge1xuICAgIHJldHVybiBjcmVhdGVDb250ZXh0Um93KHJlc3VsdCk7XG4gIH1cbiAgcmV0dXJuIGNyZWF0ZURldGFpbFJvdyhyZXN1bHQucHJvdmlkZXIsIHJlc3VsdC52ZXJkaWN0LCBzdGF0VGV4dCwgcmVzdWx0KTtcbn1cblxuLyoqXG4gKiBJbmplY3Qgbm8tZGF0YSBjb2xsYXBzZSBzdW1tYXJ5IChHUlAtMDIpIGludG8gdGhlIG5vLWRhdGEgc2VjdGlvbiBvZiBhblxuICogZW5yaWNobWVudCBzbG90LiBNdXN0IGJlIGNhbGxlZCBBRlRFUiBlbnJpY2htZW50IGNvbXBsZXRlcyBhbmQgc29ydERldGFpbFJvd3MoKVxuICogaGFzIGZpbmFsaXplZCB0aGUgRE9NIG9yZGVyLlxuICpcbiAqIFNlY3Rpb24gaGVhZGVycyBhcmUgbm93IHNlcnZlci1yZW5kZXJlZCBpbiB0aGUgdGVtcGxhdGUgKEdSUC0wMS9TMDQpLlxuICogVGhpcyBmdW5jdGlvbiBvbmx5IGhhbmRsZXMgdGhlIG5vLWRhdGEgc3VtbWFyeSByb3cgYW5kIGNvbGxhcHNlIHRvZ2dsZS5cbiAqXG4gKiBDb3VudHMgLnByb3ZpZGVyLXJvdy0tbm8tZGF0YSBlbGVtZW50cyBpbiAuZW5yaWNobWVudC1zZWN0aW9uLS1uby1kYXRhLiBJZiBhbnlcbiAqIGV4aXN0LCBjcmVhdGVzIGEgY2xpY2thYmxlIHN1bW1hcnkgcm93IHRoYXQgdG9nZ2xlcyAubm8tZGF0YS1leHBhbmRlZCBvbiB0aGVcbiAqIHNlY3Rpb24gZWxlbWVudC5cbiAqXG4gKiBFZGdlIGNhc2VzOiB6ZXJvIG5vLWRhdGEgcm93cyBoYW5kbGVkIGdyYWNlZnVsbHkgKGVhcmx5IHJldHVybiwgbm8gY3Jhc2gpLlxuICpcbiAqIEFsbCBET00gY29uc3RydWN0aW9uIHVzZXMgY3JlYXRlRWxlbWVudCArIHRleHRDb250ZW50IChTRUMtMDgpLlxuICovXG5leHBvcnQgZnVuY3Rpb24gaW5qZWN0U2VjdGlvbkhlYWRlcnNBbmROb0RhdGFTdW1tYXJ5KHNsb3Q6IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gIC8vIEhlYWRlcnMgYXJlIG5vdyBpbiB0aGUgdGVtcGxhdGUgKEdSUC0wMSkuIE9ubHkgbm8tZGF0YSBjb2xsYXBzZSBsb2dpYyByZW1haW5zLlxuICBjb25zdCBub0RhdGFTZWN0aW9uID0gc2xvdC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcIi5lbnJpY2htZW50LXNlY3Rpb24tLW5vLWRhdGFcIik7XG4gIGlmICghbm9EYXRhU2VjdGlvbikgcmV0dXJuO1xuXG4gIGNvbnN0IG5vRGF0YVJvd3MgPSBub0RhdGFTZWN0aW9uLnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFxuICAgIFwiLnByb3ZpZGVyLXJvdy0tbm8tZGF0YVwiXG4gICk7XG4gIGlmIChub0RhdGFSb3dzLmxlbmd0aCA9PT0gMCkgcmV0dXJuO1xuXG4gIGNvbnN0IGNvdW50ID0gbm9EYXRhUm93cy5sZW5ndGg7XG4gIGNvbnN0IHN1bW1hcnlSb3cgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiZGl2XCIpO1xuICBzdW1tYXJ5Um93LmNsYXNzTmFtZSA9IFwibm8tZGF0YS1zdW1tYXJ5LXJvd1wiO1xuICBzdW1tYXJ5Um93LnNldEF0dHJpYnV0ZShcInJvbGVcIiwgXCJidXR0b25cIik7XG4gIHN1bW1hcnlSb3cuc2V0QXR0cmlidXRlKFwidGFiaW5kZXhcIiwgXCIwXCIpO1xuICBzdW1tYXJ5Um93LnNldEF0dHJpYnV0ZShcImFyaWEtZXhwYW5kZWRcIiwgXCJmYWxzZVwiKTtcbiAgc3VtbWFyeVJvdy50ZXh0Q29udGVudCA9IGNvdW50ICsgXCIgcHJvdmlkZXJcIiArIChjb3VudCAhPT0gMSA/IFwic1wiIDogXCJcIikgKyBcIiBoYWQgbm8gcmVjb3JkXCI7XG5cbiAgLy8gSW5zZXJ0IHN1bW1hcnkgcm93IGJlZm9yZSB0aGUgZmlyc3Qgbm8tZGF0YSByb3cgd2l0aGluIHRoZSBuby1kYXRhIHNlY3Rpb25cbiAgY29uc3QgZmlyc3ROb0RhdGEgPSBub0RhdGFSb3dzWzBdO1xuICBpZiAoZmlyc3ROb0RhdGEpIHtcbiAgICBub0RhdGFTZWN0aW9uLmluc2VydEJlZm9yZShzdW1tYXJ5Um93LCBmaXJzdE5vRGF0YSk7XG4gIH1cblxuICAvLyBXaXJlIGNsaWNrIFx1MjE5MiB0b2dnbGUgLm5vLWRhdGEtZXhwYW5kZWQgb24gbm9EYXRhU2VjdGlvblxuICBzdW1tYXJ5Um93LmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCAoKSA9PiB7XG4gICAgY29uc3QgaXNFeHBhbmRlZCA9IG5vRGF0YVNlY3Rpb24uY2xhc3NMaXN0LnRvZ2dsZShcIm5vLWRhdGEtZXhwYW5kZWRcIik7XG4gICAgc3VtbWFyeVJvdy5zZXRBdHRyaWJ1dGUoXCJhcmlhLWV4cGFuZGVkXCIsIFN0cmluZyhpc0V4cGFuZGVkKSk7XG4gIH0pO1xuXG4gIC8vIFdpcmUga2V5Ym9hcmQgRW50ZXIvU3BhY2UgZm9yIGFjY2Vzc2liaWxpdHlcbiAgc3VtbWFyeVJvdy5hZGRFdmVudExpc3RlbmVyKFwia2V5ZG93blwiLCAoZTogS2V5Ym9hcmRFdmVudCkgPT4ge1xuICAgIGlmIChlLmtleSA9PT0gXCJFbnRlclwiIHx8IGUua2V5ID09PSBcIiBcIikge1xuICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgc3VtbWFyeVJvdy5jbGljaygpO1xuICAgIH1cbiAgfSk7XG59XG4iLCAiLyoqXG4gKiBFbnJpY2htZW50IHBvbGxpbmcgb3JjaGVzdHJhdG9yIFx1MjAxNCBwb2xsaW5nIGxvb3AsIHByb2dyZXNzIHRyYWNraW5nLFxuICogcmVzdWx0IGRpc3BhdGNoLCBhbmQgbW9kdWxlIHN0YXRlLlxuICpcbiAqIFZlcmRpY3QgY29tcHV0YXRpb24gbGl2ZXMgaW4gdmVyZGljdC1jb21wdXRlLnRzLlxuICogRE9NIHJvdyBjb25zdHJ1Y3Rpb24gbGl2ZXMgaW4gcm93LWZhY3RvcnkudHMuXG4gKiBUaGlzIG1vZHVsZSBvd25zIHRoZSBwb2xsaW5nIGludGVydmFsLCBkZWR1cCBtYXAsIHBlci1JT0Mgc3RhdGUsXG4gKiBhbmQgY29vcmRpbmF0ZXMgcmVuZGVyaW5nIHRocm91Z2ggaW1wb3J0ZWQgZnVuY3Rpb25zLlxuICovXG5cbmltcG9ydCB0eXBlIHsgRW5yaWNobWVudEl0ZW0sIEVucmljaG1lbnRTdGF0dXMgfSBmcm9tIFwiLi4vdHlwZXMvYXBpXCI7XG5pbXBvcnQgdHlwZSB7IFZlcmRpY3RLZXkgfSBmcm9tIFwiLi4vdHlwZXMvaW9jXCI7XG5pbXBvcnQgeyB2ZXJkaWN0U2V2ZXJpdHlJbmRleCwgZ2V0UHJvdmlkZXJDb3VudHMgfSBmcm9tIFwiLi4vdHlwZXMvaW9jXCI7XG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuaW1wb3J0IHtcbiAgZmluZENhcmRGb3JJb2MsXG4gIHVwZGF0ZUNhcmRWZXJkaWN0LFxuICB1cGRhdGVEYXNoYm9hcmRDb3VudHMsXG4gIHNvcnRDYXJkc0J5U2V2ZXJpdHksXG59IGZyb20gXCIuL2NhcmRzXCI7XG5pbXBvcnQgeyBleHBvcnRKU09OLCBleHBvcnRDU1YsIGNvcHlBbGxJT0NzIH0gZnJvbSBcIi4vZXhwb3J0XCI7XG5pbXBvcnQgdHlwZSB7IFZlcmRpY3RFbnRyeSB9IGZyb20gXCIuL3ZlcmRpY3QtY29tcHV0ZVwiO1xuaW1wb3J0IHsgY29tcHV0ZVdvcnN0VmVyZGljdCwgZmluZFdvcnN0RW50cnkgfSBmcm9tIFwiLi92ZXJkaWN0LWNvbXB1dGVcIjtcbmltcG9ydCB7IENPTlRFWFRfUFJPVklERVJTLCBjcmVhdGVDb250ZXh0Um93LCBjcmVhdGVEZXRhaWxSb3csXG4gICAgICAgICB1cGRhdGVTdW1tYXJ5Um93LCBmb3JtYXREYXRlLFxuICAgICAgICAgaW5qZWN0U2VjdGlvbkhlYWRlcnNBbmROb0RhdGFTdW1tYXJ5IH0gZnJvbSBcIi4vcm93LWZhY3RvcnlcIjtcblxuLy8gLS0tLSBNb2R1bGUtcHJpdmF0ZSBzdGF0ZSAtLS0tXG5cbi8qKiBEZWJvdW5jZSB0aW1lcnMgZm9yIHNvcnREZXRhaWxSb3dzIFx1MjAxNCBrZXllZCBieSBpb2NfdmFsdWUgKi9cbmNvbnN0IHNvcnRUaW1lcnM6IE1hcDxzdHJpbmcsIFJldHVyblR5cGU8dHlwZW9mIHNldFRpbWVvdXQ+PiA9IG5ldyBNYXAoKTtcblxuLyoqIEFjY3VtdWxhdGVkIGVucmljaG1lbnQgcmVzdWx0cyBmb3IgZXhwb3J0ICovXG5jb25zdCBhbGxSZXN1bHRzOiBFbnJpY2htZW50SXRlbVtdID0gW107XG5cbi8vIC0tLS0gUHJpdmF0ZSBoZWxwZXJzIC0tLS1cblxuLyoqXG4gKiBTb3J0IGFsbCAucHJvdmlkZXItZGV0YWlsLXJvdyBlbGVtZW50cyBpbiBhIGNvbnRhaW5lciBieSBzZXZlcml0eSBkZXNjZW5kaW5nLlxuICogbWFsaWNpb3VzIChpbmRleCA0KSBmaXJzdCwgZXJyb3IgKGluZGV4IDApIGxhc3QuXG4gKiBEZWJvdW5jZWQgYXQgMTAwbXMgcGVyIElPQyB0byBhdm9pZCB0aHJhc2hpbmcgZHVyaW5nIGJhdGNoIHJlc3VsdCBkZWxpdmVyeS5cbiAqL1xuZnVuY3Rpb24gc29ydERldGFpbFJvd3MoZGV0YWlsc0NvbnRhaW5lcjogSFRNTEVsZW1lbnQsIGlvY1ZhbHVlOiBzdHJpbmcpOiB2b2lkIHtcbiAgY29uc3QgZXhpc3RpbmcgPSBzb3J0VGltZXJzLmdldChpb2NWYWx1ZSk7XG4gIGlmIChleGlzdGluZyAhPT0gdW5kZWZpbmVkKSB7XG4gICAgY2xlYXJUaW1lb3V0KGV4aXN0aW5nKTtcbiAgfVxuICBjb25zdCB0aW1lciA9IHNldFRpbWVvdXQoKCkgPT4ge1xuICAgIHNvcnRUaW1lcnMuZGVsZXRlKGlvY1ZhbHVlKTtcbiAgICBjb25zdCByb3dzID0gQXJyYXkuZnJvbShcbiAgICAgIGRldGFpbHNDb250YWluZXIucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIucHJvdmlkZXItZGV0YWlsLXJvd1wiKVxuICAgICk7XG4gICAgcm93cy5zb3J0KChhLCBiKSA9PiB7XG4gICAgICBjb25zdCBhVmVyZGljdCA9IGEuZ2V0QXR0cmlidXRlKFwiZGF0YS12ZXJkaWN0XCIpIGFzIFZlcmRpY3RLZXkgfCBudWxsO1xuICAgICAgY29uc3QgYlZlcmRpY3QgPSBiLmdldEF0dHJpYnV0ZShcImRhdGEtdmVyZGljdFwiKSBhcyBWZXJkaWN0S2V5IHwgbnVsbDtcbiAgICAgIGNvbnN0IGFJZHggPSBhVmVyZGljdCA/IHZlcmRpY3RTZXZlcml0eUluZGV4KGFWZXJkaWN0KSA6IC0xO1xuICAgICAgY29uc3QgYklkeCA9IGJWZXJkaWN0ID8gdmVyZGljdFNldmVyaXR5SW5kZXgoYlZlcmRpY3QpIDogLTE7XG4gICAgICByZXR1cm4gYklkeCAtIGFJZHg7IC8vIGRlc2NlbmRpbmc6IG1hbGljaW91cyBmaXJzdFxuICAgIH0pO1xuICAgIGZvciAoY29uc3Qgcm93IG9mIHJvd3MpIHtcbiAgICAgIGRldGFpbHNDb250YWluZXIuYXBwZW5kQ2hpbGQocm93KTtcbiAgICB9XG4gIH0sIDEwMCk7XG4gIHNvcnRUaW1lcnMuc2V0KGlvY1ZhbHVlLCB0aW1lcik7XG59XG5cbi8qKlxuICogRmluZCB0aGUgY29weSBidXR0b24gZm9yIGEgZ2l2ZW4gSU9DIHZhbHVlIGJ5IGl0ZXJhdGluZyAuY29weS1idG4gZWxlbWVudHMuXG4gKiBTb3VyY2U6IG1haW4uanMgZmluZENvcHlCdXR0b25Gb3JJb2MoKSAobGluZXMgNTcxLTU3OSkuXG4gKi9cbmZ1bmN0aW9uIGZpbmRDb3B5QnV0dG9uRm9ySW9jKGlvY1ZhbHVlOiBzdHJpbmcpOiBIVE1MRWxlbWVudCB8IG51bGwge1xuICBjb25zdCBidG5zID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuY29weS1idG5cIik7XG4gIGZvciAobGV0IGkgPSAwOyBpIDwgYnRucy5sZW5ndGg7IGkrKykge1xuICAgIGNvbnN0IGJ0biA9IGJ0bnNbaV07XG4gICAgaWYgKGJ0biAmJiBhdHRyKGJ0biwgXCJkYXRhLXZhbHVlXCIpID09PSBpb2NWYWx1ZSkge1xuICAgICAgcmV0dXJuIGJ0bjtcbiAgICB9XG4gIH1cbiAgcmV0dXJuIG51bGw7XG59XG5cbi8qKlxuICogVXBkYXRlIHRoZSBjb3B5IGJ1dHRvbidzIGRhdGEtZW5yaWNobWVudCBhdHRyaWJ1dGUgd2l0aCB0aGUgd29yc3QgdmVyZGljdFxuICogc3VtbWFyeSB0ZXh0IGFjcm9zcyBhbGwgcHJvdmlkZXJzIGZvciB0aGUgZ2l2ZW4gSU9DLlxuICogU291cmNlOiBtYWluLmpzIHVwZGF0ZUNvcHlCdXR0b25Xb3JzdFZlcmRpY3QoKSAobGluZXMgNTUzLTU2OSkuXG4gKi9cbmZ1bmN0aW9uIHVwZGF0ZUNvcHlCdXR0b25Xb3JzdFZlcmRpY3QoXG4gIGlvY1ZhbHVlOiBzdHJpbmcsXG4gIGlvY1ZlcmRpY3RzOiBSZWNvcmQ8c3RyaW5nLCBWZXJkaWN0RW50cnlbXT5cbik6IHZvaWQge1xuICBjb25zdCBjb3B5QnRuID0gZmluZENvcHlCdXR0b25Gb3JJb2MoaW9jVmFsdWUpO1xuICBpZiAoIWNvcHlCdG4pIHJldHVybjtcblxuICBjb25zdCB3b3JzdEVudHJ5ID0gZmluZFdvcnN0RW50cnkoaW9jVmVyZGljdHNbaW9jVmFsdWVdID8/IFtdKTtcbiAgaWYgKCF3b3JzdEVudHJ5KSByZXR1cm47XG5cbiAgY29weUJ0bi5zZXRBdHRyaWJ1dGUoXCJkYXRhLWVucmljaG1lbnRcIiwgd29yc3RFbnRyeS5zdW1tYXJ5VGV4dCk7XG59XG5cbi8qKlxuICogVXBkYXRlIHRoZSBwcm9ncmVzcyBiYXIgZmlsbCBhbmQgdGV4dC5cbiAqIFNvdXJjZTogbWFpbi5qcyB1cGRhdGVQcm9ncmVzc0JhcigpIChsaW5lcyAzNzUtMzgzKS5cbiAqL1xuZnVuY3Rpb24gdXBkYXRlUHJvZ3Jlc3NCYXIoZG9uZTogbnVtYmVyLCB0b3RhbDogbnVtYmVyKTogdm9pZCB7XG4gIGNvbnN0IGZpbGwgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcImVucmljaC1wcm9ncmVzcy1maWxsXCIpO1xuICBjb25zdCB0ZXh0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJlbnJpY2gtcHJvZ3Jlc3MtdGV4dFwiKTtcbiAgaWYgKCFmaWxsIHx8ICF0ZXh0KSByZXR1cm47XG5cbiAgY29uc3QgcGN0ID0gdG90YWwgPiAwID8gTWF0aC5yb3VuZCgoZG9uZSAvIHRvdGFsKSAqIDEwMCkgOiAwO1xuICBmaWxsLnN0eWxlLndpZHRoID0gcGN0ICsgXCIlXCI7XG4gIHRleHQudGV4dENvbnRlbnQgPSBkb25lICsgXCIvXCIgKyB0b3RhbCArIFwiIHByb3ZpZGVycyBjb21wbGV0ZVwiO1xufVxuXG4vKipcbiAqIFNob3cgb3IgdXBkYXRlIHRoZSBwZW5kaW5nIHByb3ZpZGVyIGluZGljYXRvciBhZnRlciB0aGUgZmlyc3QgcmVzdWx0IGZvciBhbiBJT0MuXG4gKiBSZWFkcyBwcm92aWRlciBjb3VudHMgZnJvbSB0aGUgRE9NIHZpYSBnZXRQcm92aWRlckNvdW50cygpIFx1MjAxNCByZWZsZWN0cyB0aGUgYWN0dWFsXG4gKiBjb25maWd1cmVkIHByb3ZpZGVyIHNldCBpbmplY3RlZCBieSB0aGUgRmxhc2sgcm91dGUgaW50byBkYXRhLXByb3ZpZGVyLWNvdW50cy5cbiAqIFNvdXJjZTogbWFpbi5qcyB1cGRhdGVQZW5kaW5nSW5kaWNhdG9yKCkgKGxpbmVzIDQxMi00NDEpLlxuICovXG5mdW5jdGlvbiB1cGRhdGVQZW5kaW5nSW5kaWNhdG9yKFxuICBzbG90OiBIVE1MRWxlbWVudCxcbiAgY2FyZDogSFRNTEVsZW1lbnQgfCBudWxsLFxuICByZWNlaXZlZENvdW50OiBudW1iZXJcbik6IHZvaWQge1xuICBjb25zdCBpb2NUeXBlID0gY2FyZCA/IGF0dHIoY2FyZCwgXCJkYXRhLWlvYy10eXBlXCIpIDogXCJcIjtcbiAgY29uc3QgcHJvdmlkZXJDb3VudHMgPSBnZXRQcm92aWRlckNvdW50cygpO1xuICBjb25zdCB0b3RhbEV4cGVjdGVkID0gT2JqZWN0LnByb3RvdHlwZS5oYXNPd25Qcm9wZXJ0eS5jYWxsKHByb3ZpZGVyQ291bnRzLCBpb2NUeXBlKVxuICAgID8gKHByb3ZpZGVyQ291bnRzW2lvY1R5cGVdID8/IDApXG4gICAgOiAwO1xuICBjb25zdCByZW1haW5pbmcgPSB0b3RhbEV4cGVjdGVkIC0gcmVjZWl2ZWRDb3VudDtcblxuICBpZiAocmVtYWluaW5nIDw9IDApIHtcbiAgICAvLyBBbGwgcHJvdmlkZXJzIGFjY291bnRlZCBmb3IgXHUyMDE0IHJlbW92ZSB3YWl0aW5nIGluZGljYXRvciBpZiBwcmVzZW50XG4gICAgY29uc3QgZXhpc3RpbmdJbmRpY2F0b3IgPSBzbG90LnF1ZXJ5U2VsZWN0b3IoXCIuZW5yaWNobWVudC13YWl0aW5nLXRleHRcIik7XG4gICAgaWYgKGV4aXN0aW5nSW5kaWNhdG9yKSB7XG4gICAgICBzbG90LnJlbW92ZUNoaWxkKGV4aXN0aW5nSW5kaWNhdG9yKTtcbiAgICB9XG4gICAgcmV0dXJuO1xuICB9XG5cbiAgLy8gRmluZCBvciBjcmVhdGUgdGhlIHdhaXRpbmcgaW5kaWNhdG9yIHNwYW5cbiAgbGV0IGluZGljYXRvciA9IHNsb3QucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIuZW5yaWNobWVudC13YWl0aW5nLXRleHRcIik7XG4gIGlmICghaW5kaWNhdG9yKSB7XG4gICAgaW5kaWNhdG9yID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gICAgaW5kaWNhdG9yLmNsYXNzTmFtZSA9IFwiZW5yaWNobWVudC13YWl0aW5nLXRleHQgZW5yaWNobWVudC1wZW5kaW5nLXRleHRcIjtcbiAgICBzbG90LmFwcGVuZENoaWxkKGluZGljYXRvcik7XG4gIH1cbiAgaW5kaWNhdG9yLnRleHRDb250ZW50ID0gcmVtYWluaW5nICsgXCIgcHJvdmlkZXJcIiArIChyZW1haW5pbmcgIT09IDEgPyBcInNcIiA6IFwiXCIpICsgXCIgc3RpbGwgbG9hZGluZy4uLlwiO1xufVxuXG4vKipcbiAqIFNob3cgYSB3YXJuaW5nIGJhbm5lciBmb3IgcmF0ZS1saW1pdCBvciBhdXRoZW50aWNhdGlvbiBlcnJvcnMuXG4gKiBTb3VyY2U6IG1haW4uanMgc2hvd0VucmljaFdhcm5pbmcoKSAobGluZXMgNjA1LTYxMSkuXG4gKi9cbmZ1bmN0aW9uIHNob3dFbnJpY2hXYXJuaW5nKG1lc3NhZ2U6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCBiYW5uZXIgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcImVucmljaC13YXJuaW5nXCIpO1xuICBpZiAoIWJhbm5lcikgcmV0dXJuO1xuICBiYW5uZXIuc3R5bGUuZGlzcGxheSA9IFwiYmxvY2tcIjtcbiAgLy8gVXNlIHRleHRDb250ZW50IHRvIHNhZmVseSBzZXQgdGhlIHdhcm5pbmcgbWVzc2FnZSAoU0VDLTA4KVxuICBiYW5uZXIudGV4dENvbnRlbnQgPSBcIldhcm5pbmc6IFwiICsgbWVzc2FnZSArIFwiIENvbnNpZGVyIHVzaW5nIG9mZmxpbmUgbW9kZSBvciBjaGVja2luZyB5b3VyIEFQSSBrZXkgaW4gU2V0dGluZ3MuXCI7XG59XG5cbi8qKlxuICogTWFyayBlbnJpY2htZW50IGNvbXBsZXRlOiBhZGQgLmNvbXBsZXRlIGNsYXNzIHRvIHByb2dyZXNzIGNvbnRhaW5lcixcbiAqIHVwZGF0ZSB0ZXh0LCBhbmQgZW5hYmxlIHRoZSBleHBvcnQgYnV0dG9uLlxuICogU291cmNlOiBtYWluLmpzIG1hcmtFbnJpY2htZW50Q29tcGxldGUoKSAobGluZXMgNTkwLTYwMykuXG4gKi9cbmZ1bmN0aW9uIG1hcmtFbnJpY2htZW50Q29tcGxldGUoKTogdm9pZCB7XG4gIGNvbnN0IGNvbnRhaW5lciA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZW5yaWNoLXByb2dyZXNzXCIpO1xuICBpZiAoY29udGFpbmVyKSB7XG4gICAgY29udGFpbmVyLmNsYXNzTGlzdC5hZGQoXCJjb21wbGV0ZVwiKTtcbiAgfVxuICBjb25zdCB0ZXh0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJlbnJpY2gtcHJvZ3Jlc3MtdGV4dFwiKTtcbiAgaWYgKHRleHQpIHtcbiAgICB0ZXh0LnRleHRDb250ZW50ID0gXCJFbnJpY2htZW50IGNvbXBsZXRlXCI7XG4gIH1cbiAgY29uc3QgZXhwb3J0QnRuID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJleHBvcnQtYnRuXCIpO1xuICBpZiAoZXhwb3J0QnRuKSB7XG4gICAgZXhwb3J0QnRuLnJlbW92ZUF0dHJpYnV0ZShcImRpc2FibGVkXCIpO1xuICB9XG5cbiAgLy8gVklTLTAzICsgR1JQLTAyOiBJbmplY3Qgc2VjdGlvbiBoZWFkZXJzIGFuZCBuby1kYXRhIGNvbGxhcHNlIGZvciBhbGwgc2xvdHNcbiAgZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuZW5yaWNobWVudC1zbG90XCIpLmZvckVhY2goc2xvdCA9PiB7XG4gICAgaW5qZWN0U2VjdGlvbkhlYWRlcnNBbmROb0RhdGFTdW1tYXJ5KHNsb3QpO1xuICB9KTtcbn1cblxuLyoqXG4gKiBSZW5kZXIgYSBzaW5nbGUgZW5yaWNobWVudCByZXN1bHQgaXRlbSBpbnRvIHRoZSBhcHByb3ByaWF0ZSBJT0MgY2FyZCBzbG90LlxuICogSGFuZGxlcyBib3RoIFwicmVzdWx0XCIgYW5kIFwiZXJyb3JcIiBkaXNjcmltaW5hdGVkIHVuaW9uIGJyYW5jaGVzLlxuICpcbiAqIE5ldyBiZWhhdmlvciAoUGxhbiAwMik6XG4gKiAtIEFMTCByZXN1bHRzIGdvIGludG8gLmVucmljaG1lbnQtZGV0YWlscyBjb250YWluZXIgKG5vIGRpcmVjdCBzbG90IGFwcGVuZClcbiAqIC0gU3VtbWFyeSByb3cgdXBkYXRlZCBvbiBlYWNoIHJlc3VsdDogd29yc3QgdmVyZGljdCBiYWRnZSArIGF0dHJpYnV0aW9uICsgY29uc2Vuc3VzIGJhZGdlXG4gKiAtIERldGFpbCByb3dzIHNvcnRlZCBieSBzZXZlcml0eSBkZXNjZW5kaW5nIChkZWJvdW5jZWQgMTAwbXMpXG4gKiAtIC5lbnJpY2htZW50LXNsb3QtLWxvYWRlZCBjbGFzcyBhZGRlZCBvbiBmaXJzdCByZXN1bHQgKHJldmVhbHMgY2hldnJvbiB2aWEgQ1NTKVxuICpcbiAqIFNvdXJjZTogbWFpbi5qcyByZW5kZXJFbnJpY2htZW50UmVzdWx0KCkgKGxpbmVzIDQ0My01NDApLlxuICovXG5mdW5jdGlvbiByZW5kZXJFbnJpY2htZW50UmVzdWx0KFxuICByZXN1bHQ6IEVucmljaG1lbnRJdGVtLFxuICBpb2NWZXJkaWN0czogUmVjb3JkPHN0cmluZywgVmVyZGljdEVudHJ5W10+LFxuICBpb2NSZXN1bHRDb3VudHM6IFJlY29yZDxzdHJpbmcsIG51bWJlcj5cbik6IHZvaWQge1xuICAvLyBGaW5kIHRoZSBjYXJkIGZvciB0aGlzIElPQyB2YWx1ZVxuICBjb25zdCBjYXJkID0gZmluZENhcmRGb3JJb2MocmVzdWx0LmlvY192YWx1ZSk7XG4gIGlmICghY2FyZCkgcmV0dXJuO1xuXG4gIGNvbnN0IHNsb3QgPSBjYXJkLnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLmVucmljaG1lbnQtc2xvdFwiKTtcbiAgaWYgKCFzbG90KSByZXR1cm47XG5cbiAgLy8gQ29udGV4dCBwcm92aWRlcnMgKElQIENvbnRleHQsIEROUyBSZWNvcmRzLCBDZXJ0IEhpc3RvcnkpIGFyZSBwdXJlbHkgaW5mb3JtYXRpb25hbCBcdTIwMTRcbiAgLy8gc2VwYXJhdGUgcmVuZGVyaW5nIHBhdGguIE5vIFZlcmRpY3RFbnRyeSBhY2N1bXVsYXRpb24sIG5vIGNvbnNlbnN1cy9hdHRyaWJ1dGlvbixcbiAgLy8gbm8gY2FyZCB2ZXJkaWN0IHVwZGF0ZS5cbiAgaWYgKENPTlRFWFRfUFJPVklERVJTLmhhcyhyZXN1bHQucHJvdmlkZXIpKSB7XG4gICAgLy8gUmVtb3ZlIHNwaW5uZXIgb24gZmlyc3QgcmVzdWx0XG4gICAgY29uc3Qgc3Bpbm5lcldyYXBwZXIgPSBzbG90LnF1ZXJ5U2VsZWN0b3IoXCIuc3Bpbm5lci13cmFwcGVyXCIpO1xuICAgIGlmIChzcGlubmVyV3JhcHBlcikgc2xvdC5yZW1vdmVDaGlsZChzcGlubmVyV3JhcHBlcik7XG4gICAgc2xvdC5jbGFzc0xpc3QuYWRkKFwiZW5yaWNobWVudC1zbG90LS1sb2FkZWRcIik7XG5cbiAgICAvLyBUcmFjayByZXN1bHQgY291bnQgZm9yIHBlbmRpbmcgaW5kaWNhdG9yXG4gICAgaW9jUmVzdWx0Q291bnRzW3Jlc3VsdC5pb2NfdmFsdWVdID0gKGlvY1Jlc3VsdENvdW50c1tyZXN1bHQuaW9jX3ZhbHVlXSA/PyAwKSArIDE7XG5cbiAgICAvLyBSZW5kZXIgY29udGV4dCByb3cgYW5kIGFwcGVuZCB0byBjb250ZXh0IHNlY3Rpb24gY29udGFpbmVyXG4gICAgY29uc3QgY29udGV4dFNlY3Rpb24gPSBzbG90LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLmVucmljaG1lbnQtc2VjdGlvbi0tY29udGV4dFwiKTtcbiAgICBpZiAoY29udGV4dFNlY3Rpb24gJiYgcmVzdWx0LnR5cGUgPT09IFwicmVzdWx0XCIpIHtcbiAgICAgIGNvbnN0IGNvbnRleHRSb3cgPSBjcmVhdGVDb250ZXh0Um93KHJlc3VsdCk7XG4gICAgICBjb250ZXh0U2VjdGlvbi5hcHBlbmRDaGlsZChjb250ZXh0Um93KTtcbiAgICB9XG5cbiAgICAvLyBVcGRhdGUgcGVuZGluZyBpbmRpY2F0b3JcbiAgICB1cGRhdGVQZW5kaW5nSW5kaWNhdG9yKHNsb3QsIGNhcmQsIGlvY1Jlc3VsdENvdW50c1tyZXN1bHQuaW9jX3ZhbHVlXSA/PyAxKTtcbiAgICByZXR1cm47IC8vIFNraXAgYWxsIHZlcmRpY3Qvc3VtbWFyeS9zb3J0L2Rhc2hib2FyZCBsb2dpY1xuICB9XG5cbiAgLy8gUmVtb3ZlIHNwaW5uZXIgd3JhcHBlciBvbiBmaXJzdCByZXN1bHQgZm9yIHRoaXMgSU9DXG4gIGNvbnN0IHNwaW5uZXJXcmFwcGVyID0gc2xvdC5xdWVyeVNlbGVjdG9yKFwiLnNwaW5uZXItd3JhcHBlclwiKTtcbiAgaWYgKHNwaW5uZXJXcmFwcGVyKSB7XG4gICAgc2xvdC5yZW1vdmVDaGlsZChzcGlubmVyV3JhcHBlcik7XG4gIH1cblxuICAvLyBBZGQgLmVucmljaG1lbnQtc2xvdC0tbG9hZGVkIGNsYXNzIFx1MjAxNCB0cmlnZ2VycyBjaGV2cm9uIHZpc2liaWxpdHkgdmlhIENTUyBndWFyZFxuICBzbG90LmNsYXNzTGlzdC5hZGQoXCJlbnJpY2htZW50LXNsb3QtLWxvYWRlZFwiKTtcblxuICAvLyBUcmFjayByZWNlaXZlZCBjb3VudCBmb3IgdGhpcyBJT0NcbiAgaW9jUmVzdWx0Q291bnRzW3Jlc3VsdC5pb2NfdmFsdWVdID0gKGlvY1Jlc3VsdENvdW50c1tyZXN1bHQuaW9jX3ZhbHVlXSA/PyAwKSArIDE7XG4gIGNvbnN0IHJlY2VpdmVkQ291bnQgPSBpb2NSZXN1bHRDb3VudHNbcmVzdWx0LmlvY192YWx1ZV0gPz8gMTtcblxuICAvLyBEZXRlcm1pbmUgdmVyZGljdCBhbmQgc3RhdFRleHRcbiAgbGV0IHZlcmRpY3Q6IFZlcmRpY3RLZXk7XG4gIGxldCBzdGF0VGV4dDogc3RyaW5nO1xuICBsZXQgc3VtbWFyeVRleHQ6IHN0cmluZztcbiAgbGV0IGRldGVjdGlvbkNvdW50ID0gMDtcbiAgbGV0IHRvdGFsRW5naW5lcyA9IDA7XG5cbiAgaWYgKHJlc3VsdC50eXBlID09PSBcInJlc3VsdFwiKSB7XG4gICAgdmVyZGljdCA9IHJlc3VsdC52ZXJkaWN0O1xuICAgIGRldGVjdGlvbkNvdW50ID0gcmVzdWx0LmRldGVjdGlvbl9jb3VudDtcbiAgICB0b3RhbEVuZ2luZXMgPSByZXN1bHQudG90YWxfZW5naW5lcztcblxuICAgIGlmICh2ZXJkaWN0ID09PSBcIm1hbGljaW91c1wiKSB7XG4gICAgICBzdGF0VGV4dCA9IHJlc3VsdC5kZXRlY3Rpb25fY291bnQgKyBcIi9cIiArIHJlc3VsdC50b3RhbF9lbmdpbmVzICsgXCIgZW5naW5lc1wiO1xuICAgIH0gZWxzZSBpZiAodmVyZGljdCA9PT0gXCJzdXNwaWNpb3VzXCIpIHtcbiAgICAgIHN0YXRUZXh0ID1cbiAgICAgICAgcmVzdWx0LnRvdGFsX2VuZ2luZXMgPiAxXG4gICAgICAgICAgPyByZXN1bHQuZGV0ZWN0aW9uX2NvdW50ICsgXCIvXCIgKyByZXN1bHQudG90YWxfZW5naW5lcyArIFwiIGVuZ2luZXNcIlxuICAgICAgICAgIDogXCJTdXNwaWNpb3VzXCI7XG4gICAgfSBlbHNlIGlmICh2ZXJkaWN0ID09PSBcImNsZWFuXCIpIHtcbiAgICAgIHN0YXRUZXh0ID0gXCJDbGVhbiwgXCIgKyByZXN1bHQudG90YWxfZW5naW5lcyArIFwiIGVuZ2luZXNcIjtcbiAgICB9IGVsc2UgaWYgKHZlcmRpY3QgPT09IFwia25vd25fZ29vZFwiKSB7XG4gICAgICBzdGF0VGV4dCA9IFwiTlNSTCBtYXRjaFwiO1xuICAgIH0gZWxzZSB7XG4gICAgICAvLyBub19kYXRhXG4gICAgICBzdGF0VGV4dCA9IFwiTm90IGluIGRhdGFiYXNlXCI7XG4gICAgfVxuXG4gICAgY29uc3Qgc2NhbkRhdGVTdHIgPSBmb3JtYXREYXRlKHJlc3VsdC5zY2FuX2RhdGUpO1xuICAgIHN1bW1hcnlUZXh0ID1cbiAgICAgIHJlc3VsdC5wcm92aWRlciArXG4gICAgICBcIjogXCIgK1xuICAgICAgdmVyZGljdCArXG4gICAgICBcIiAoXCIgK1xuICAgICAgc3RhdFRleHQgK1xuICAgICAgKHNjYW5EYXRlU3RyID8gXCIsIHNjYW5uZWQgXCIgKyBzY2FuRGF0ZVN0ciA6IFwiXCIpICtcbiAgICAgIFwiKVwiO1xuICB9IGVsc2Uge1xuICAgIC8vIEVycm9yIHJlc3VsdFxuICAgIHZlcmRpY3QgPSBcImVycm9yXCI7XG4gICAgc3RhdFRleHQgPSByZXN1bHQuZXJyb3I7XG4gICAgc3VtbWFyeVRleHQgPSByZXN1bHQucHJvdmlkZXIgKyBcIjogZXJyb3IsIFwiICsgcmVzdWx0LmVycm9yO1xuICB9XG5cbiAgLy8gUHVzaCB0byBpb2NWZXJkaWN0cyB3aXRoIGV4dGVuZGVkIGZpZWxkc1xuICBjb25zdCBlbnRyaWVzID0gaW9jVmVyZGljdHNbcmVzdWx0LmlvY192YWx1ZV0gPz8gW107XG4gIGlvY1ZlcmRpY3RzW3Jlc3VsdC5pb2NfdmFsdWVdID0gZW50cmllcztcbiAgZW50cmllcy5wdXNoKHsgcHJvdmlkZXI6IHJlc3VsdC5wcm92aWRlciwgdmVyZGljdCwgc3VtbWFyeVRleHQsIGRldGVjdGlvbkNvdW50LCB0b3RhbEVuZ2luZXMsIHN0YXRUZXh0IH0pO1xuXG4gIC8vIEJ1aWxkIGRldGFpbCByb3cgYW5kIHJvdXRlIHRvIGNvcnJlY3Qgc2VjdGlvbiBjb250YWluZXJcbiAgY29uc3QgaXNOb0RhdGEgPSB2ZXJkaWN0ID09PSBcIm5vX2RhdGFcIiB8fCB2ZXJkaWN0ID09PSBcImVycm9yXCI7XG4gIGNvbnN0IHNlY3Rpb25TZWxlY3RvciA9IGlzTm9EYXRhXG4gICAgPyBcIi5lbnJpY2htZW50LXNlY3Rpb24tLW5vLWRhdGFcIlxuICAgIDogXCIuZW5yaWNobWVudC1zZWN0aW9uLS1yZXB1dGF0aW9uXCI7XG4gIGNvbnN0IHNlY3Rpb25Db250YWluZXIgPSBzbG90LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KHNlY3Rpb25TZWxlY3Rvcik7XG4gIGlmIChzZWN0aW9uQ29udGFpbmVyKSB7XG4gICAgY29uc3QgZGV0YWlsUm93ID0gY3JlYXRlRGV0YWlsUm93KHJlc3VsdC5wcm92aWRlciwgdmVyZGljdCwgc3RhdFRleHQsIHJlc3VsdCk7XG4gICAgc2VjdGlvbkNvbnRhaW5lci5hcHBlbmRDaGlsZChkZXRhaWxSb3cpO1xuICAgIC8vIFNvcnQgb25seSByZXB1dGF0aW9uIHJvd3MgKG5vLWRhdGEgcm93cyBkb24ndCBuZWVkIHNldmVyaXR5IHNvcnRpbmcpXG4gICAgaWYgKCFpc05vRGF0YSkge1xuICAgICAgc29ydERldGFpbFJvd3Moc2VjdGlvbkNvbnRhaW5lciwgcmVzdWx0LmlvY192YWx1ZSk7XG4gICAgfVxuICB9XG5cbiAgLy8gVXBkYXRlIHN1bW1hcnkgcm93ICh3b3JzdCB2ZXJkaWN0ICsgYXR0cmlidXRpb24gKyBjb25zZW5zdXMpXG4gIHVwZGF0ZVN1bW1hcnlSb3coc2xvdCwgcmVzdWx0LmlvY192YWx1ZSwgaW9jVmVyZGljdHMpO1xuXG4gIC8vIFVwZGF0ZSBwZW5kaW5nIGluZGljYXRvciBmb3IgcmVtYWluaW5nIHByb3ZpZGVyc1xuICB1cGRhdGVQZW5kaW5nSW5kaWNhdG9yKHNsb3QsIGNhcmQsIHJlY2VpdmVkQ291bnQpO1xuXG4gIC8vIENvbXB1dGUgd29yc3QgdmVyZGljdCBmb3IgdGhpcyBJT0NcbiAgY29uc3Qgd29yc3RWZXJkaWN0ID0gY29tcHV0ZVdvcnN0VmVyZGljdChpb2NWZXJkaWN0c1tyZXN1bHQuaW9jX3ZhbHVlXSA/PyBbXSk7XG5cbiAgLy8gVXBkYXRlIGNhcmQgdmVyZGljdCwgZGFzaGJvYXJkLCBhbmQgc29ydFxuICB1cGRhdGVDYXJkVmVyZGljdChyZXN1bHQuaW9jX3ZhbHVlLCB3b3JzdFZlcmRpY3QpO1xuICB1cGRhdGVEYXNoYm9hcmRDb3VudHMoKTtcbiAgc29ydENhcmRzQnlTZXZlcml0eSgpO1xuXG4gIC8vIFVwZGF0ZSBjb3B5IGJ1dHRvbiB3aXRoIHdvcnN0IHZlcmRpY3QgYWNyb3NzIGFsbCBwcm92aWRlcnMgZm9yIHRoaXMgSU9DXG4gIHVwZGF0ZUNvcHlCdXR0b25Xb3JzdFZlcmRpY3QocmVzdWx0LmlvY192YWx1ZSwgaW9jVmVyZGljdHMpO1xufVxuXG4vKipcbiAqIFdpcmUgZXhwYW5kL2NvbGxhcHNlIHRvZ2dsZSBmb3IgYWxsIC5jaGV2cm9uLXRvZ2dsZSBidXR0b25zIG9uIHRoZSBwYWdlLlxuICogQ2FsbGVkIG9uY2UgZnJvbSBpbml0KCkuIENsaWNrIGxpc3RlbmVyIHRvZ2dsZXMgLmlzLW9wZW4gb24gdGhlIHNpYmxpbmdcbiAqIC5lbnJpY2htZW50LWRldGFpbHMgY29udGFpbmVyIGFuZCBzZXRzIGFyaWEtZXhwYW5kZWQgYWNjb3JkaW5nbHkuXG4gKiBNdWx0aXBsZSBjYXJkcyBjYW4gYmUgaW5kZXBlbmRlbnRseSBvcGVuZWQgXHUyMDE0IG5vIGNvbGxhcHNlLW90aGVycyBsb2dpYy5cbiAqL1xuZnVuY3Rpb24gd2lyZUV4cGFuZFRvZ2dsZXMoKTogdm9pZCB7XG4gIGNvbnN0IHRvZ2dsZXMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcIi5jaGV2cm9uLXRvZ2dsZVwiKTtcbiAgdG9nZ2xlcy5mb3JFYWNoKCh0b2dnbGUpID0+IHtcbiAgICB0b2dnbGUuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgIGNvbnN0IGRldGFpbHMgPSB0b2dnbGUubmV4dEVsZW1lbnRTaWJsaW5nIGFzIEhUTUxFbGVtZW50IHwgbnVsbDtcbiAgICAgIGlmICghZGV0YWlscyB8fCAhZGV0YWlscy5jbGFzc0xpc3QuY29udGFpbnMoXCJlbnJpY2htZW50LWRldGFpbHNcIikpIHJldHVybjtcbiAgICAgIGNvbnN0IGlzT3BlbiA9IGRldGFpbHMuY2xhc3NMaXN0LnRvZ2dsZShcImlzLW9wZW5cIik7XG4gICAgICB0b2dnbGUuY2xhc3NMaXN0LnRvZ2dsZShcImlzLW9wZW5cIiwgaXNPcGVuKTtcbiAgICAgIHRvZ2dsZS5zZXRBdHRyaWJ1dGUoXCJhcmlhLWV4cGFuZGVkXCIsIFN0cmluZyhpc09wZW4pKTtcbiAgICB9KTtcbiAgfSk7XG59XG5cbi8vIC0tLS0gUHJpdmF0ZSBpbml0IGhlbHBlcnMgLS0tLVxuXG4vKipcbiAqIFdpcmUgdGhlIGV4cG9ydCBkcm9wZG93biB3aXRoIEpTT04sIENTViwgYW5kIGNvcHktYWxsLUlPQ3Mgb3B0aW9ucy5cbiAqL1xuZnVuY3Rpb24gaW5pdEV4cG9ydEJ1dHRvbigpOiB2b2lkIHtcbiAgY29uc3QgZXhwb3J0QnRuID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJleHBvcnQtYnRuXCIpO1xuICBjb25zdCBkcm9wZG93biA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZXhwb3J0LWRyb3Bkb3duXCIpO1xuICBpZiAoIWV4cG9ydEJ0biB8fCAhZHJvcGRvd24pIHJldHVybjtcblxuICBleHBvcnRCdG4uYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsIGZ1bmN0aW9uICgpIHtcbiAgICBjb25zdCBpc1Zpc2libGUgPSBkcm9wZG93bi5zdHlsZS5kaXNwbGF5ICE9PSBcIm5vbmVcIjtcbiAgICBkcm9wZG93bi5zdHlsZS5kaXNwbGF5ID0gaXNWaXNpYmxlID8gXCJub25lXCIgOiBcIlwiO1xuICB9KTtcblxuICAvLyBDbG9zZSBkcm9wZG93biB3aGVuIGNsaWNraW5nIG91dHNpZGVcbiAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsIGZ1bmN0aW9uIChlKSB7XG4gICAgY29uc3QgdGFyZ2V0ID0gZS50YXJnZXQgYXMgSFRNTEVsZW1lbnQ7XG4gICAgaWYgKCF0YXJnZXQuY2xvc2VzdChcIi5leHBvcnQtZ3JvdXBcIikpIHtcbiAgICAgIGRyb3Bkb3duLnN0eWxlLmRpc3BsYXkgPSBcIm5vbmVcIjtcbiAgICB9XG4gIH0pO1xuXG4gIGNvbnN0IGJ1dHRvbnMgPSBkcm9wZG93bi5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcIltkYXRhLWV4cG9ydF1cIik7XG4gIGJ1dHRvbnMuZm9yRWFjaChmdW5jdGlvbiAoYnRuKSB7XG4gICAgYnRuLmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCBmdW5jdGlvbiAoKSB7XG4gICAgICBjb25zdCBhY3Rpb24gPSBidG4uZ2V0QXR0cmlidXRlKFwiZGF0YS1leHBvcnRcIik7XG4gICAgICBpZiAoYWN0aW9uID09PSBcImpzb25cIikge1xuICAgICAgICBleHBvcnRKU09OKGFsbFJlc3VsdHMpO1xuICAgICAgfSBlbHNlIGlmIChhY3Rpb24gPT09IFwiY3N2XCIpIHtcbiAgICAgICAgZXhwb3J0Q1NWKGFsbFJlc3VsdHMpO1xuICAgICAgfSBlbHNlIGlmIChhY3Rpb24gPT09IFwiaW9jc1wiKSB7XG4gICAgICAgIGNvcHlBbGxJT0NzKGJ0bik7XG4gICAgICB9XG4gICAgICBkcm9wZG93bi5zdHlsZS5kaXNwbGF5ID0gXCJub25lXCI7XG4gICAgfSk7XG4gIH0pO1xufVxuXG4vLyAtLS0tIFB1YmxpYyBBUEkgLS0tLVxuXG4vKipcbiAqIEluaXRpYWxpc2UgdGhlIGVucmljaG1lbnQgcG9sbGluZyBtb2R1bGUuXG4gKlxuICogR3VhcmRzIG9uIC5wYWdlLXJlc3VsdHMgcHJlc2VuY2UgYW5kIGRhdGEtbW9kZT1cIm9ubGluZVwiIFx1MjAxNCByZXR1cm5zIGVhcmx5XG4gKiBvbiBvZmZsaW5lIG1vZGUgb3Igd2hlbiBlbnJpY2htZW50IFVJIGVsZW1lbnRzIGFyZSBhYnNlbnQuXG4gKlxuICogV2lyZXMgY2hldnJvbiBleHBhbmQvY29sbGFwc2UgdG9nZ2xlcyBvbmNlIGF0IGluaXQgdGltZSAoYmVmb3JlIHBvbGxpbmdcbiAqIHN0YXJ0cykgc28gdGhleSB3b3JrIHJlZ2FyZGxlc3Mgb2Ygd2hlbiByZXN1bHRzIHBvcHVsYXRlIGRldGFpbHMuXG4gKlxuICogU3RhcnRzIGEgNzUwbXMgcG9sbGluZyBpbnRlcnZhbCBmb3IgL2VucmljaG1lbnQvc3RhdHVzLzxqb2JfaWQ+LFxuICogcmVuZGVycyBpbmNyZW1lbnRhbCByZXN1bHRzLCBzaG93cyB3YXJuaW5nIGJhbm5lcnMgZm9yIGVycm9ycywgYW5kXG4gKiBtYXJrcyBlbnJpY2htZW50IGNvbXBsZXRlIHdoZW4gYWxsIHRhc2tzIGFyZSBkb25lLlxuICpcbiAqIFNvdXJjZTogbWFpbi5qcyBpbml0RW5yaWNobWVudFBvbGxpbmcoKSAobGluZXMgMzE2LTM3MykgK1xuICogICAgICAgICBpbml0RXhwb3J0QnV0dG9uKCkgKGxpbmVzIDYxNS02NDMpLlxuICovXG5leHBvcnQgZnVuY3Rpb24gaW5pdCgpOiB2b2lkIHtcbiAgY29uc3QgcGFnZVJlc3VsdHMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcIi5wYWdlLXJlc3VsdHNcIik7XG4gIGlmICghcGFnZVJlc3VsdHMpIHJldHVybjtcblxuICBjb25zdCBqb2JJZCA9IGF0dHIocGFnZVJlc3VsdHMsIFwiZGF0YS1qb2ItaWRcIik7XG4gIGNvbnN0IG1vZGUgPSBhdHRyKHBhZ2VSZXN1bHRzLCBcImRhdGEtbW9kZVwiKTtcblxuICBpZiAoIWpvYklkIHx8IG1vZGUgIT09IFwib25saW5lXCIpIHJldHVybjtcblxuICAvLyBXaXJlIGV4cGFuZC9jb2xsYXBzZSB0b2dnbGVzIG9uY2UgYXQgaW5pdCAoYmVmb3JlIHBvbGxpbmcgc3RhcnRzKVxuICB3aXJlRXhwYW5kVG9nZ2xlcygpO1xuXG4gIC8vIERlZHVwIGtleTogXCJpb2NfdmFsdWV8cHJvdmlkZXJcIiBcdTIwMTQgZWFjaCBwcm92aWRlciByZXN1bHQgcGVyIElPQyByZW5kZXJlZCBvbmNlXG4gIGNvbnN0IHJlbmRlcmVkOiBSZWNvcmQ8c3RyaW5nLCBib29sZWFuPiA9IHt9O1xuXG4gIC8vIFBlci1JT0MgdmVyZGljdCB0cmFja2luZyBmb3Igd29yc3QtdmVyZGljdCBjb3B5L2V4cG9ydCBjb21wdXRhdGlvblxuICAvLyBpb2NWZXJkaWN0c1tpb2NfdmFsdWVdID0gW3twcm92aWRlciwgdmVyZGljdCwgc3VtbWFyeVRleHQsIGRldGVjdGlvbkNvdW50LCB0b3RhbEVuZ2luZXMsIHN0YXRUZXh0fV1cbiAgY29uc3QgaW9jVmVyZGljdHM6IFJlY29yZDxzdHJpbmcsIFZlcmRpY3RFbnRyeVtdPiA9IHt9O1xuXG4gIC8vIFBlci1JT0MgcmVzdWx0IGNvdW50IHRyYWNraW5nIGZvciBwZW5kaW5nIGluZGljYXRvclxuICBjb25zdCBpb2NSZXN1bHRDb3VudHM6IFJlY29yZDxzdHJpbmcsIG51bWJlcj4gPSB7fTtcblxuICAvLyBVc2UgUmV0dXJuVHlwZTx0eXBlb2Ygc2V0SW50ZXJ2YWw+IHRvIGF2b2lkIE5vZGVKUy5UaW1lb3V0IGNvbmZsaWN0XG4gIGNvbnN0IGludGVydmFsSWQ6IFJldHVyblR5cGU8dHlwZW9mIHNldEludGVydmFsPiA9IHNldEludGVydmFsKGZ1bmN0aW9uICgpIHtcbiAgICBmZXRjaChcIi9lbnJpY2htZW50L3N0YXR1cy9cIiArIGpvYklkKVxuICAgICAgLnRoZW4oZnVuY3Rpb24gKHJlc3ApIHtcbiAgICAgICAgaWYgKCFyZXNwLm9rKSByZXR1cm4gbnVsbDtcbiAgICAgICAgcmV0dXJuIHJlc3AuanNvbigpIGFzIFByb21pc2U8RW5yaWNobWVudFN0YXR1cz47XG4gICAgICB9KVxuICAgICAgLnRoZW4oZnVuY3Rpb24gKGRhdGEpIHtcbiAgICAgICAgaWYgKCFkYXRhKSByZXR1cm47XG5cbiAgICAgICAgdXBkYXRlUHJvZ3Jlc3NCYXIoZGF0YS5kb25lLCBkYXRhLnRvdGFsKTtcblxuICAgICAgICAvLyBSZW5kZXIgYW55IG5ldyByZXN1bHRzIG5vdCB5ZXQgZGlzcGxheWVkLCBhbmQgY2hlY2sgZm9yIHdhcm5pbmdzXG4gICAgICAgIGNvbnN0IHJlc3VsdHMgPSBkYXRhLnJlc3VsdHM7XG4gICAgICAgIGZvciAobGV0IGkgPSAwOyBpIDwgcmVzdWx0cy5sZW5ndGg7IGkrKykge1xuICAgICAgICAgIGNvbnN0IHJlc3VsdCA9IHJlc3VsdHNbaV07XG4gICAgICAgICAgaWYgKCFyZXN1bHQpIGNvbnRpbnVlO1xuICAgICAgICAgIGNvbnN0IGRlZHVwS2V5ID0gcmVzdWx0LmlvY192YWx1ZSArIFwifFwiICsgcmVzdWx0LnByb3ZpZGVyO1xuICAgICAgICAgIGlmICghcmVuZGVyZWRbZGVkdXBLZXldKSB7XG4gICAgICAgICAgICByZW5kZXJlZFtkZWR1cEtleV0gPSB0cnVlO1xuICAgICAgICAgICAgYWxsUmVzdWx0cy5wdXNoKHJlc3VsdCk7XG4gICAgICAgICAgICByZW5kZXJFbnJpY2htZW50UmVzdWx0KHJlc3VsdCwgaW9jVmVyZGljdHMsIGlvY1Jlc3VsdENvdW50cyk7XG4gICAgICAgICAgfVxuXG4gICAgICAgICAgLy8gU2hvdyB3YXJuaW5nIGJhbm5lciBmb3IgcmF0ZS1saW1pdCBvciBhdXRoIGVycm9yc1xuICAgICAgICAgIGlmIChyZXN1bHQudHlwZSA9PT0gXCJlcnJvclwiICYmIHJlc3VsdC5lcnJvcikge1xuICAgICAgICAgICAgY29uc3QgZXJyTG93ZXIgPSByZXN1bHQuZXJyb3IudG9Mb3dlckNhc2UoKTtcbiAgICAgICAgICAgIGlmIChcbiAgICAgICAgICAgICAgZXJyTG93ZXIuaW5kZXhPZihcInJhdGUgbGltaXRcIikgIT09IC0xIHx8XG4gICAgICAgICAgICAgIGVyckxvd2VyLmluZGV4T2YoXCI0MjlcIikgIT09IC0xXG4gICAgICAgICAgICApIHtcbiAgICAgICAgICAgICAgc2hvd0VucmljaFdhcm5pbmcoXCJSYXRlIGxpbWl0IHJlYWNoZWQgZm9yIFwiICsgcmVzdWx0LnByb3ZpZGVyICsgXCIuXCIpO1xuICAgICAgICAgICAgfSBlbHNlIGlmIChcbiAgICAgICAgICAgICAgZXJyTG93ZXIuaW5kZXhPZihcImF1dGhlbnRpY2F0aW9uXCIpICE9PSAtMSB8fFxuICAgICAgICAgICAgICBlcnJMb3dlci5pbmRleE9mKFwiNDAxXCIpICE9PSAtMSB8fFxuICAgICAgICAgICAgICBlcnJMb3dlci5pbmRleE9mKFwiNDAzXCIpICE9PSAtMVxuICAgICAgICAgICAgKSB7XG4gICAgICAgICAgICAgIHNob3dFbnJpY2hXYXJuaW5nKFxuICAgICAgICAgICAgICAgIFwiQXV0aGVudGljYXRpb24gZXJyb3IgZm9yIFwiICtcbiAgICAgICAgICAgICAgICAgIHJlc3VsdC5wcm92aWRlciArXG4gICAgICAgICAgICAgICAgICBcIi4gUGxlYXNlIGNoZWNrIHlvdXIgQVBJIGtleSBpbiBTZXR0aW5ncy5cIlxuICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgfVxuICAgICAgICAgIH1cbiAgICAgICAgfVxuXG4gICAgICAgIGlmIChkYXRhLmNvbXBsZXRlKSB7XG4gICAgICAgICAgY2xlYXJJbnRlcnZhbChpbnRlcnZhbElkKTtcbiAgICAgICAgICBtYXJrRW5yaWNobWVudENvbXBsZXRlKCk7XG4gICAgICAgIH1cbiAgICAgIH0pXG4gICAgICAuY2F0Y2goZnVuY3Rpb24gKCkge1xuICAgICAgICAvLyBGZXRjaCBlcnJvciBcdTIwMTQgc2lsZW50bHkgY29udGludWU7IHJldHJ5IG9uIG5leHQgaW50ZXJ2YWwgdGlja1xuICAgICAgfSk7XG4gIH0sIDc1MCk7XG5cbiAgLy8gV2lyZSB0aGUgZXhwb3J0IGJ1dHRvblxuICBpbml0RXhwb3J0QnV0dG9uKCk7XG59XG4iLCAiLyoqXG4gKiBTZXR0aW5ncyBwYWdlIG1vZHVsZSBcdTIwMTQgYWNjb3JkaW9uIGFuZCBBUEkga2V5IHRvZ2dsZXMuXG4gKi9cblxuLyoqIFdpcmUgdXAgYWNjb3JkaW9uIHNlY3Rpb25zIFx1MjAxNCBvbmUgb3BlbiBhdCBhIHRpbWUuICovXG5mdW5jdGlvbiBpbml0QWNjb3JkaW9uKCk6IHZvaWQge1xuICBjb25zdCBzZWN0aW9ucyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFxuICAgIFwiLnNldHRpbmdzLXNlY3Rpb25bZGF0YS1wcm92aWRlcl1cIlxuICApO1xuICBpZiAoc2VjdGlvbnMubGVuZ3RoID09PSAwKSByZXR1cm47XG5cbiAgZnVuY3Rpb24gZXhwYW5kU2VjdGlvbihzZWN0aW9uOiBIVE1MRWxlbWVudCk6IHZvaWQge1xuICAgIHNlY3Rpb25zLmZvckVhY2goKHMpID0+IHtcbiAgICAgIGlmIChzICE9PSBzZWN0aW9uKSB7XG4gICAgICAgIHMucmVtb3ZlQXR0cmlidXRlKFwiZGF0YS1leHBhbmRlZFwiKTtcbiAgICAgICAgY29uc3QgYnRuID0gcy5xdWVyeVNlbGVjdG9yKFwiLmFjY29yZGlvbi1oZWFkZXJcIik7XG4gICAgICAgIGlmIChidG4pIGJ0bi5zZXRBdHRyaWJ1dGUoXCJhcmlhLWV4cGFuZGVkXCIsIFwiZmFsc2VcIik7XG4gICAgICB9XG4gICAgfSk7XG4gICAgc2VjdGlvbi5zZXRBdHRyaWJ1dGUoXCJkYXRhLWV4cGFuZGVkXCIsIFwiXCIpO1xuICAgIGNvbnN0IGJ0biA9IHNlY3Rpb24ucXVlcnlTZWxlY3RvcihcIi5hY2NvcmRpb24taGVhZGVyXCIpO1xuICAgIGlmIChidG4pIGJ0bi5zZXRBdHRyaWJ1dGUoXCJhcmlhLWV4cGFuZGVkXCIsIFwidHJ1ZVwiKTtcbiAgfVxuXG4gIHNlY3Rpb25zLmZvckVhY2goKHNlY3Rpb24pID0+IHtcbiAgICBjb25zdCBoZWFkZXIgPSBzZWN0aW9uLnF1ZXJ5U2VsZWN0b3IoXCIuYWNjb3JkaW9uLWhlYWRlclwiKTtcbiAgICBpZiAoIWhlYWRlcikgcmV0dXJuO1xuICAgIGhlYWRlci5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgKCkgPT4ge1xuICAgICAgaWYgKHNlY3Rpb24uaGFzQXR0cmlidXRlKFwiZGF0YS1leHBhbmRlZFwiKSkge1xuICAgICAgICBzZWN0aW9uLnJlbW92ZUF0dHJpYnV0ZShcImRhdGEtZXhwYW5kZWRcIik7XG4gICAgICAgIGhlYWRlci5zZXRBdHRyaWJ1dGUoXCJhcmlhLWV4cGFuZGVkXCIsIFwiZmFsc2VcIik7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBleHBhbmRTZWN0aW9uKHNlY3Rpb24pO1xuICAgICAgfVxuICAgIH0pO1xuICB9KTtcblxufVxuXG4vKiogV2lyZSB1cCBwZXItcHJvdmlkZXIgQVBJIGtleSBzaG93L2hpZGUgdG9nZ2xlcy4gKi9cbmZ1bmN0aW9uIGluaXRLZXlUb2dnbGVzKCk6IHZvaWQge1xuICBjb25zdCBzZWN0aW9ucyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoXCIuc2V0dGluZ3Mtc2VjdGlvblwiKTtcbiAgc2VjdGlvbnMuZm9yRWFjaCgoc2VjdGlvbikgPT4ge1xuICAgIGNvbnN0IGJ0biA9IHNlY3Rpb24ucXVlcnlTZWxlY3RvcihcbiAgICAgIFwiW2RhdGEtcm9sZT0ndG9nZ2xlLWtleSddXCJcbiAgICApIGFzIEhUTUxCdXR0b25FbGVtZW50IHwgbnVsbDtcbiAgICBjb25zdCBpbnB1dCA9IHNlY3Rpb24ucXVlcnlTZWxlY3RvcihcbiAgICAgIFwiaW5wdXRbdHlwZT0ncGFzc3dvcmQnXSwgaW5wdXRbdHlwZT0ndGV4dCddXCJcbiAgICApIGFzIEhUTUxJbnB1dEVsZW1lbnQgfCBudWxsO1xuICAgIGlmICghYnRuIHx8ICFpbnB1dCkgcmV0dXJuO1xuXG4gICAgYnRuLmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCAoKSA9PiB7XG4gICAgICBpZiAoaW5wdXQudHlwZSA9PT0gXCJwYXNzd29yZFwiKSB7XG4gICAgICAgIGlucHV0LnR5cGUgPSBcInRleHRcIjtcbiAgICAgICAgYnRuLnRleHRDb250ZW50ID0gXCJIaWRlXCI7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBpbnB1dC50eXBlID0gXCJwYXNzd29yZFwiO1xuICAgICAgICBidG4udGV4dENvbnRlbnQgPSBcIlNob3dcIjtcbiAgICAgIH1cbiAgICB9KTtcbiAgfSk7XG59XG5cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBpbml0QWNjb3JkaW9uKCk7XG4gIGluaXRLZXlUb2dnbGVzKCk7XG59XG4iLCAiLyoqXG4gKiBVSSB1dGlsaXRpZXMgbW9kdWxlIFx1MjAxNCBzY3JvbGwtYXdhcmUgZmlsdGVyIGJhciBhbmQgY2FyZCBzdGFnZ2VyIGFuaW1hdGlvbi5cbiAqXG4gKiBFeHRyYWN0ZWQgZnJvbSBtYWluLmpzIGluaXRTY3JvbGxBd2FyZUZpbHRlckJhcigpIChsaW5lcyA4MTEtODI2KVxuICogYW5kIGluaXRDYXJkU3RhZ2dlcigpIChsaW5lcyA4MzAtODM1KS5cbiAqL1xuXG4vKipcbiAqIEFkZCBzY3JvbGwgbGlzdGVuZXIgdGhhdCB0b2dnbGVzIFwiaXMtc2Nyb2xsZWRcIiBjbGFzcyBvbiAuZmlsdGVyLWJhci13cmFwcGVyXG4gKiBvbmNlIHRoZSBwYWdlIHNjcm9sbHMgcGFzdCA0MHB4LlxuICovXG5mdW5jdGlvbiBpbml0U2Nyb2xsQXdhcmVGaWx0ZXJCYXIoKTogdm9pZCB7XG4gIGNvbnN0IGZpbHRlckJhciA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLmZpbHRlci1iYXItd3JhcHBlclwiKTtcbiAgaWYgKCFmaWx0ZXJCYXIpIHJldHVybjtcblxuICBsZXQgc2Nyb2xsZWQgPSBmYWxzZTtcbiAgd2luZG93LmFkZEV2ZW50TGlzdGVuZXIoXG4gICAgXCJzY3JvbGxcIixcbiAgICBmdW5jdGlvbiAoKSB7XG4gICAgICBjb25zdCBpc1Njcm9sbGVkID0gd2luZG93LnNjcm9sbFkgPiA0MDtcbiAgICAgIGlmIChpc1Njcm9sbGVkICE9PSBzY3JvbGxlZCkge1xuICAgICAgICBzY3JvbGxlZCA9IGlzU2Nyb2xsZWQ7XG4gICAgICAgIGZpbHRlckJhci5jbGFzc0xpc3QudG9nZ2xlKFwiaXMtc2Nyb2xsZWRcIiwgc2Nyb2xsZWQpO1xuICAgICAgfVxuICAgIH0sXG4gICAgeyBwYXNzaXZlOiB0cnVlIH1cbiAgKTtcbn1cblxuLyoqXG4gKiBTZXQgLS1jYXJkLWluZGV4IENTUyBjdXN0b20gcHJvcGVydHkgb24gZWFjaCAuaW9jLWNhcmQgZWxlbWVudCxcbiAqIGNhcHBlZCBhdCAxNSB0byBsaW1pdCBzdGFnZ2VyIGRlbGF5IG9uIGxvbmcgbGlzdHMuXG4gKi9cbmZ1bmN0aW9uIGluaXRDYXJkU3RhZ2dlcigpOiB2b2lkIHtcbiAgY29uc3QgY2FyZHMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcIi5pb2MtY2FyZFwiKTtcbiAgY2FyZHMuZm9yRWFjaCgoY2FyZCwgaSkgPT4ge1xuICAgIGNhcmQuc3R5bGUuc2V0UHJvcGVydHkoXCItLWNhcmQtaW5kZXhcIiwgU3RyaW5nKE1hdGgubWluKGksIDE1KSkpO1xuICB9KTtcbn1cblxuLyoqXG4gKiBJbml0aWFsaXNlIGFsbCBVSSBlbmhhbmNlbWVudHM6IHNjcm9sbC1hd2FyZSBmaWx0ZXIgYmFyIGFuZCBjYXJkIHN0YWdnZXIuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBpbml0U2Nyb2xsQXdhcmVGaWx0ZXJCYXIoKTtcbiAgaW5pdENhcmRTdGFnZ2VyKCk7XG59XG4iLCAiLyoqXG4gKiBTVkcgcmVsYXRpb25zaGlwIGdyYXBoIHJlbmRlcmVyIGZvciB0aGUgSU9DIGRldGFpbCBwYWdlLlxuICpcbiAqIFJlYWRzIGdyYXBoX25vZGVzIGFuZCBncmFwaF9lZGdlcyBmcm9tIGRhdGEgYXR0cmlidXRlcyBvbiB0aGVcbiAqICNyZWxhdGlvbnNoaXAtZ3JhcGggY29udGFpbmVyLCB0aGVuIGRyYXdzIGEgaHViLWFuZC1zcG9rZSBTVkcgZGlhZ3JhbVxuICogd2l0aCB0aGUgSU9DIGF0IHRoZSBjZW50ZXIgYW5kIHByb3ZpZGVyIG5vZGVzIGFycmFuZ2VkIGluIGEgY2lyY2xlIGFyb3VuZCBpdC5cbiAqXG4gKiBOb2RlcyBhcmUgY29sb3JlZCBieSB2ZXJkaWN0IHRvIGdpdmUgaW5zdGFudCB2aXN1YWwgdHJpYWdlIGNvbnRleHQuXG4gKlxuICogU0VDLTA4OiBBbGwgdGV4dCBjb250ZW50IHVzZXMgZG9jdW1lbnQuY3JlYXRlVGV4dE5vZGUoKSBcdTIwMTQgbmV2ZXIgaW5uZXJIVE1MXG4gKiBvciB0ZXh0Q29udGVudCBvbiBlbGVtZW50cyB3aXRoIGNoaWxkcmVuLiBJT0MgdmFsdWVzIGFuZCBwcm92aWRlciBuYW1lc1xuICogYXJlIHBhc3NlZCB0aHJvdWdoIGNyZWF0ZVRleHROb2RlIG9ubHkgdG8gcHJldmVudCBYU1MuXG4gKi9cblxuaW50ZXJmYWNlIEdyYXBoTm9kZSB7XG4gIGlkOiBzdHJpbmc7XG4gIGxhYmVsOiBzdHJpbmc7XG4gIHZlcmRpY3Q6IHN0cmluZztcbiAgcm9sZTogXCJpb2NcIiB8IFwicHJvdmlkZXJcIjtcbn1cblxuaW50ZXJmYWNlIEdyYXBoRWRnZSB7XG4gIGZyb206IHN0cmluZztcbiAgdG86IHN0cmluZztcbiAgdmVyZGljdDogc3RyaW5nO1xufVxuXG4vKiogVmVyZGljdC10by1maWxsLWNvbG9yIG1hcHBpbmcgKG1hdGNoZXMgQ1NTIHZlcmRpY3QgdmFyaWFibGVzKS4gKi9cbmNvbnN0IFZFUkRJQ1RfQ09MT1JTOiBSZWNvcmQ8c3RyaW5nLCBzdHJpbmc+ID0ge1xuICBtYWxpY2lvdXM6ICBcIiNlZjQ0NDRcIixcbiAgc3VzcGljaW91czogXCIjZjk3MzE2XCIsXG4gIGNsZWFuOiAgICAgIFwiIzIyYzU1ZVwiLFxuICBrbm93bl9nb29kOiBcIiMzYjgyZjZcIixcbiAgbm9fZGF0YTogICAgXCIjNmI3MjgwXCIsXG4gIGVycm9yOiAgICAgIFwiIzZiNzI4MFwiLFxuICBpb2M6ICAgICAgICBcIiM4YjVjZjZcIixcbn07XG5cbmNvbnN0IFNWR19OUyA9IFwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIjtcblxuZnVuY3Rpb24gdmVyZGljdENvbG9yKHZlcmRpY3Q6IHN0cmluZyk6IHN0cmluZyB7XG4gIHJldHVybiBWRVJESUNUX0NPTE9SU1t2ZXJkaWN0XSA/PyBcIiM2YjcyODBcIjtcbn1cblxuLyoqXG4gKiBDcmVhdGUgYW4gU1ZHIGVsZW1lbnQgaW4gdGhlIFNWRyBuYW1lc3BhY2UuXG4gKi9cbmZ1bmN0aW9uIHN2Z0VsKHRhZzogc3RyaW5nKTogU1ZHRWxlbWVudCB7XG4gIHJldHVybiBkb2N1bWVudC5jcmVhdGVFbGVtZW50TlMoU1ZHX05TLCB0YWcpIGFzIFNWR0VsZW1lbnQ7XG59XG5cbi8qKlxuICogUmVuZGVyIHRoZSBodWItYW5kLXNwb2tlIHJlbGF0aW9uc2hpcCBncmFwaCBpbnRvIHRoZSBnaXZlbiBjb250YWluZXIuXG4gKiBTYWZlIHRvIGNhbGwgd2hlbiBubyBwcm92aWRlciBkYXRhIGlzIHByZXNlbnQgXHUyMDE0IHNob3dzIGEgZmFsbGJhY2sgbWVzc2FnZS5cbiAqL1xuZnVuY3Rpb24gcmVuZGVyUmVsYXRpb25zaGlwR3JhcGgoY29udGFpbmVyOiBIVE1MRWxlbWVudCk6IHZvaWQge1xuICBjb25zdCBub2Rlc0F0dHIgPSBjb250YWluZXIuZ2V0QXR0cmlidXRlKFwiZGF0YS1ncmFwaC1ub2Rlc1wiKTtcbiAgY29uc3QgZWRnZXNBdHRyID0gY29udGFpbmVyLmdldEF0dHJpYnV0ZShcImRhdGEtZ3JhcGgtZWRnZXNcIik7XG5cbiAgbGV0IG5vZGVzOiBHcmFwaE5vZGVbXSA9IFtdO1xuICBsZXQgZWRnZXM6IEdyYXBoRWRnZVtdID0gW107XG5cbiAgdHJ5IHtcbiAgICBub2RlcyA9IG5vZGVzQXR0ciA/IChKU09OLnBhcnNlKG5vZGVzQXR0cikgYXMgR3JhcGhOb2RlW10pIDogW107XG4gICAgZWRnZXMgPSBlZGdlc0F0dHIgPyAoSlNPTi5wYXJzZShlZGdlc0F0dHIpIGFzIEdyYXBoRWRnZVtdKSA6IFtdO1xuICB9IGNhdGNoIHtcbiAgICAvLyBNYWxmb3JtZWQgSlNPTiBcdTIwMTQgc2hvdyBlbXB0eSBzdGF0ZVxuICAgIG5vZGVzID0gW107XG4gICAgZWRnZXMgPSBbXTtcbiAgfVxuXG4gIGNvbnN0IHByb3ZpZGVyTm9kZXMgPSBub2Rlcy5maWx0ZXIoKG4pID0+IG4ucm9sZSA9PT0gXCJwcm92aWRlclwiKTtcbiAgY29uc3QgaW9jTm9kZSA9IG5vZGVzLmZpbmQoKG4pID0+IG4ucm9sZSA9PT0gXCJpb2NcIik7XG5cbiAgaWYgKCFpb2NOb2RlIHx8IHByb3ZpZGVyTm9kZXMubGVuZ3RoID09PSAwKSB7XG4gICAgY29uc3QgbXNnID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInBcIik7XG4gICAgbXNnLmNsYXNzTmFtZSA9IFwiZ3JhcGgtZW1wdHlcIjtcbiAgICBtc2cuYXBwZW5kQ2hpbGQoZG9jdW1lbnQuY3JlYXRlVGV4dE5vZGUoXCJObyBwcm92aWRlciBkYXRhIHRvIGdyYXBoXCIpKTtcbiAgICBjb250YWluZXIuYXBwZW5kQ2hpbGQobXNnKTtcbiAgICByZXR1cm47XG4gIH1cblxuICAvLyAtLS0tIFNWRyBjYW52YXMgLS0tLVxuICBjb25zdCBzdmcgPSBzdmdFbChcInN2Z1wiKTtcbiAgc3ZnLnNldEF0dHJpYnV0ZShcInZpZXdCb3hcIiwgXCIwIDAgNjAwIDQwMFwiKTtcbiAgc3ZnLnNldEF0dHJpYnV0ZShcIndpZHRoXCIsIFwiMTAwJVwiKTtcbiAgc3ZnLnNldEF0dHJpYnV0ZShcInJvbGVcIiwgXCJpbWdcIik7XG4gIHN2Zy5zZXRBdHRyaWJ1dGUoXCJhcmlhLWxhYmVsXCIsIFwiUHJvdmlkZXIgcmVsYXRpb25zaGlwIGdyYXBoXCIpO1xuXG4gIGNvbnN0IGN4ID0gMzAwOyAgLy8gY2VudGVyIHhcbiAgY29uc3QgY3kgPSAyMDA7ICAvLyBjZW50ZXIgeVxuICBjb25zdCBvcmJpdFJhZGl1cyA9IDE1MDtcbiAgY29uc3QgaW9jcnIgPSAzMDsgIC8vIElPQyBub2RlIHJhZGl1c1xuICBjb25zdCBwcnJyID0gMjA7ICAgLy8gcHJvdmlkZXIgbm9kZSByYWRpdXNcblxuICAvLyAtLS0tIERyYXcgZWRnZXMgZmlyc3QgKGJlaGluZCBub2RlcykgLS0tLVxuICBjb25zdCBlZGdlR3JvdXAgPSBzdmdFbChcImdcIik7XG4gIGVkZ2VHcm91cC5zZXRBdHRyaWJ1dGUoXCJjbGFzc1wiLCBcImdyYXBoLWVkZ2VzXCIpO1xuXG4gIGZvciAoY29uc3QgZWRnZSBvZiBlZGdlcykge1xuICAgIGNvbnN0IHRhcmdldE5vZGUgPSBwcm92aWRlck5vZGVzLmZpbmQoKG4pID0+IG4uaWQgPT09IGVkZ2UudG8pO1xuICAgIGlmICghdGFyZ2V0Tm9kZSkgY29udGludWU7XG5cbiAgICBjb25zdCBpZHggPSBwcm92aWRlck5vZGVzLmluZGV4T2YodGFyZ2V0Tm9kZSk7XG4gICAgY29uc3QgYW5nbGUgPSAoMiAqIE1hdGguUEkgKiBpZHgpIC8gcHJvdmlkZXJOb2Rlcy5sZW5ndGggLSBNYXRoLlBJIC8gMjtcbiAgICBjb25zdCBweCA9IGN4ICsgb3JiaXRSYWRpdXMgKiBNYXRoLmNvcyhhbmdsZSk7XG4gICAgY29uc3QgcHkgPSBjeSArIG9yYml0UmFkaXVzICogTWF0aC5zaW4oYW5nbGUpO1xuXG4gICAgY29uc3QgbGluZSA9IHN2Z0VsKFwibGluZVwiKTtcbiAgICBsaW5lLnNldEF0dHJpYnV0ZShcIngxXCIsIFN0cmluZyhjeCkpO1xuICAgIGxpbmUuc2V0QXR0cmlidXRlKFwieTFcIiwgU3RyaW5nKGN5KSk7XG4gICAgbGluZS5zZXRBdHRyaWJ1dGUoXCJ4MlwiLCBTdHJpbmcoTWF0aC5yb3VuZChweCkpKTtcbiAgICBsaW5lLnNldEF0dHJpYnV0ZShcInkyXCIsIFN0cmluZyhNYXRoLnJvdW5kKHB5KSkpO1xuICAgIGxpbmUuc2V0QXR0cmlidXRlKFwic3Ryb2tlXCIsIHZlcmRpY3RDb2xvcihlZGdlLnZlcmRpY3QpKTtcbiAgICBsaW5lLnNldEF0dHJpYnV0ZShcInN0cm9rZS13aWR0aFwiLCBcIjJcIik7XG4gICAgbGluZS5zZXRBdHRyaWJ1dGUoXCJvcGFjaXR5XCIsIFwiMC42XCIpO1xuICAgIGVkZ2VHcm91cC5hcHBlbmRDaGlsZChsaW5lKTtcbiAgfVxuXG4gIHN2Zy5hcHBlbmRDaGlsZChlZGdlR3JvdXApO1xuXG4gIC8vIC0tLS0gRHJhdyBwcm92aWRlciBub2RlcyAtLS0tXG4gIGNvbnN0IG5vZGVHcm91cCA9IHN2Z0VsKFwiZ1wiKTtcbiAgbm9kZUdyb3VwLnNldEF0dHJpYnV0ZShcImNsYXNzXCIsIFwiZ3JhcGgtbm9kZXNcIik7XG5cbiAgcHJvdmlkZXJOb2Rlcy5mb3JFYWNoKChub2RlLCBpZHgpID0+IHtcbiAgICBjb25zdCBhbmdsZSA9ICgyICogTWF0aC5QSSAqIGlkeCkgLyBwcm92aWRlck5vZGVzLmxlbmd0aCAtIE1hdGguUEkgLyAyO1xuICAgIGNvbnN0IHB4ID0gY3ggKyBvcmJpdFJhZGl1cyAqIE1hdGguY29zKGFuZ2xlKTtcbiAgICBjb25zdCBweSA9IGN5ICsgb3JiaXRSYWRpdXMgKiBNYXRoLnNpbihhbmdsZSk7XG5cbiAgICBjb25zdCBncm91cCA9IHN2Z0VsKFwiZ1wiKTtcbiAgICBncm91cC5zZXRBdHRyaWJ1dGUoXCJjbGFzc1wiLCBcImdyYXBoLW5vZGUgZ3JhcGgtbm9kZS0tcHJvdmlkZXJcIik7XG5cbiAgICAvLyBBY2Nlc3NpYmxlIHRvb2x0aXBcbiAgICBjb25zdCB0aXRsZSA9IHN2Z0VsKFwidGl0bGVcIik7XG4gICAgdGl0bGUuYXBwZW5kQ2hpbGQoZG9jdW1lbnQuY3JlYXRlVGV4dE5vZGUobm9kZS5pZCkpO1xuICAgIGdyb3VwLmFwcGVuZENoaWxkKHRpdGxlKTtcblxuICAgIC8vIENpcmNsZVxuICAgIGNvbnN0IGNpcmNsZSA9IHN2Z0VsKFwiY2lyY2xlXCIpO1xuICAgIGNpcmNsZS5zZXRBdHRyaWJ1dGUoXCJjeFwiLCBTdHJpbmcoTWF0aC5yb3VuZChweCkpKTtcbiAgICBjaXJjbGUuc2V0QXR0cmlidXRlKFwiY3lcIiwgU3RyaW5nKE1hdGgucm91bmQocHkpKSk7XG4gICAgY2lyY2xlLnNldEF0dHJpYnV0ZShcInJcIiwgU3RyaW5nKHBycnIpKTtcbiAgICBjaXJjbGUuc2V0QXR0cmlidXRlKFwiZmlsbFwiLCB2ZXJkaWN0Q29sb3Iobm9kZS52ZXJkaWN0KSk7XG4gICAgZ3JvdXAuYXBwZW5kQ2hpbGQoY2lyY2xlKTtcblxuICAgIC8vIExhYmVsIGJlbG93IGNpcmNsZSAoU0VDLTA4OiBjcmVhdGVUZXh0Tm9kZSlcbiAgICBjb25zdCB0ZXh0ID0gc3ZnRWwoXCJ0ZXh0XCIpO1xuICAgIHRleHQuc2V0QXR0cmlidXRlKFwieFwiLCBTdHJpbmcoTWF0aC5yb3VuZChweCkpKTtcbiAgICB0ZXh0LnNldEF0dHJpYnV0ZShcInlcIiwgU3RyaW5nKE1hdGgucm91bmQocHkgKyBwcnJyICsgMTQpKSk7XG4gICAgdGV4dC5zZXRBdHRyaWJ1dGUoXCJ0ZXh0LWFuY2hvclwiLCBcIm1pZGRsZVwiKTtcbiAgICB0ZXh0LnNldEF0dHJpYnV0ZShcImZvbnQtc2l6ZVwiLCBcIjExXCIpO1xuICAgIHRleHQuc2V0QXR0cmlidXRlKFwiZmlsbFwiLCBcIiNlNWU3ZWJcIik7XG4gICAgdGV4dC5hcHBlbmRDaGlsZChkb2N1bWVudC5jcmVhdGVUZXh0Tm9kZShub2RlLmxhYmVsLnNsaWNlKDAsIDEyKSkpO1xuICAgIGdyb3VwLmFwcGVuZENoaWxkKHRleHQpO1xuXG4gICAgbm9kZUdyb3VwLmFwcGVuZENoaWxkKGdyb3VwKTtcbiAgfSk7XG5cbiAgc3ZnLmFwcGVuZENoaWxkKG5vZGVHcm91cCk7XG5cbiAgLy8gLS0tLSBEcmF3IElPQyBjZW50ZXIgbm9kZSAob24gdG9wKSAtLS0tXG4gIGNvbnN0IGlvY0dyb3VwID0gc3ZnRWwoXCJnXCIpO1xuICBpb2NHcm91cC5zZXRBdHRyaWJ1dGUoXCJjbGFzc1wiLCBcImdyYXBoLW5vZGUgZ3JhcGgtbm9kZS0taW9jXCIpO1xuXG4gIGNvbnN0IGlvY1RpdGxlID0gc3ZnRWwoXCJ0aXRsZVwiKTtcbiAgaW9jVGl0bGUuYXBwZW5kQ2hpbGQoZG9jdW1lbnQuY3JlYXRlVGV4dE5vZGUoaW9jTm9kZS5pZCkpO1xuICBpb2NHcm91cC5hcHBlbmRDaGlsZChpb2NUaXRsZSk7XG5cbiAgY29uc3QgaW9jQ2lyY2xlID0gc3ZnRWwoXCJjaXJjbGVcIik7XG4gIGlvY0NpcmNsZS5zZXRBdHRyaWJ1dGUoXCJjeFwiLCBTdHJpbmcoY3gpKTtcbiAgaW9jQ2lyY2xlLnNldEF0dHJpYnV0ZShcImN5XCIsIFN0cmluZyhjeSkpO1xuICBpb2NDaXJjbGUuc2V0QXR0cmlidXRlKFwiclwiLCBTdHJpbmcoaW9jcnIpKTtcbiAgaW9jQ2lyY2xlLnNldEF0dHJpYnV0ZShcImZpbGxcIiwgdmVyZGljdENvbG9yKFwiaW9jXCIpKTtcbiAgaW9jR3JvdXAuYXBwZW5kQ2hpbGQoaW9jQ2lyY2xlKTtcblxuICBjb25zdCBpb2NUZXh0ID0gc3ZnRWwoXCJ0ZXh0XCIpO1xuICBpb2NUZXh0LnNldEF0dHJpYnV0ZShcInhcIiwgU3RyaW5nKGN4KSk7XG4gIGlvY1RleHQuc2V0QXR0cmlidXRlKFwieVwiLCBTdHJpbmcoY3kgKyA0KSk7XG4gIGlvY1RleHQuc2V0QXR0cmlidXRlKFwidGV4dC1hbmNob3JcIiwgXCJtaWRkbGVcIik7XG4gIGlvY1RleHQuc2V0QXR0cmlidXRlKFwiZm9udC1zaXplXCIsIFwiMTBcIik7XG4gIGlvY1RleHQuc2V0QXR0cmlidXRlKFwiZmlsbFwiLCBcIiNmZmZcIik7XG4gIGlvY1RleHQuc2V0QXR0cmlidXRlKFwiZm9udC13ZWlnaHRcIiwgXCJib2xkXCIpO1xuICBpb2NUZXh0LmFwcGVuZENoaWxkKGRvY3VtZW50LmNyZWF0ZVRleHROb2RlKGlvY05vZGUubGFiZWwuc2xpY2UoMCwgMjApKSk7XG4gIGlvY0dyb3VwLmFwcGVuZENoaWxkKGlvY1RleHQpO1xuXG4gIHN2Zy5hcHBlbmRDaGlsZChpb2NHcm91cCk7XG5cbiAgY29udGFpbmVyLmFwcGVuZENoaWxkKHN2Zyk7XG59XG5cbi8qKlxuICogSW5pdGlhbGl6ZSB0aGUgZ3JhcGggbW9kdWxlLlxuICogRmluZHMgdGhlICNyZWxhdGlvbnNoaXAtZ3JhcGggZWxlbWVudCBhbmQgcmVuZGVycyB0aGUgU1ZHIGlmIHByZXNlbnQuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBjb25zdCBjb250YWluZXIgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInJlbGF0aW9uc2hpcC1ncmFwaFwiKTtcbiAgaWYgKGNvbnRhaW5lcikge1xuICAgIHJlbmRlclJlbGF0aW9uc2hpcEdyYXBoKGNvbnRhaW5lcik7XG4gIH1cbn1cbiIsICIvKipcbiAqIFNlbnRpbmVsWCBtYWluIGVudHJ5IHBvaW50IFx1MjAxNCBpbXBvcnRzIGFuZCBpbml0aWFsaXplcyBhbGwgZmVhdHVyZSBtb2R1bGVzLlxuICpcbiAqIFRoaXMgZmlsZSBpcyB0aGUgZXNidWlsZCBlbnRyeSBwb2ludCAoSlNfRU5UUlkgaW4gTWFrZWZpbGUpLlxuICogZXNidWlsZCB3cmFwcyB0aGUgb3V0cHV0IGluIGFuIElJRkUgYXV0b21hdGljYWxseSAoLS1mb3JtYXQ9aWlmZSkuXG4gKlxuICogTW9kdWxlIGluaXQgb3JkZXIgbWF0Y2hlcyB0aGUgb3JpZ2luYWwgbWFpbi5qcyBpbml0KCkgZnVuY3Rpb25cbiAqIChsaW5lcyA4MTUtODI2KSB0byBwcmVzZXJ2ZSBpZGVudGljYWwgRE9NQ29udGVudExvYWRlZCBiZWhhdmlvci5cbiAqL1xuXG5pbXBvcnQgeyBpbml0IGFzIGluaXRGb3JtIH0gZnJvbSBcIi4vbW9kdWxlcy9mb3JtXCI7XG5pbXBvcnQgeyBpbml0IGFzIGluaXRDbGlwYm9hcmQgfSBmcm9tIFwiLi9tb2R1bGVzL2NsaXBib2FyZFwiO1xuaW1wb3J0IHsgaW5pdCBhcyBpbml0Q2FyZHMgfSBmcm9tIFwiLi9tb2R1bGVzL2NhcmRzXCI7XG5pbXBvcnQgeyBpbml0IGFzIGluaXRGaWx0ZXIgfSBmcm9tIFwiLi9tb2R1bGVzL2ZpbHRlclwiO1xuaW1wb3J0IHsgaW5pdCBhcyBpbml0RW5yaWNobWVudCB9IGZyb20gXCIuL21vZHVsZXMvZW5yaWNobWVudFwiO1xuaW1wb3J0IHsgaW5pdCBhcyBpbml0U2V0dGluZ3MgfSBmcm9tIFwiLi9tb2R1bGVzL3NldHRpbmdzXCI7XG5pbXBvcnQgeyBpbml0IGFzIGluaXRVaSB9IGZyb20gXCIuL21vZHVsZXMvdWlcIjtcbmltcG9ydCB7IGluaXQgYXMgaW5pdEdyYXBoIH0gZnJvbSBcIi4vbW9kdWxlcy9ncmFwaFwiO1xuXG5mdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBpbml0Rm9ybSgpO1xuICBpbml0Q2xpcGJvYXJkKCk7XG4gIGluaXRDYXJkcygpO1xuICBpbml0RmlsdGVyKCk7XG4gIGluaXRFbnJpY2htZW50KCk7XG4gIGluaXRTZXR0aW5ncygpO1xuICBpbml0VWkoKTtcbiAgaW5pdEdyYXBoKCk7XG59XG5cbmlmIChkb2N1bWVudC5yZWFkeVN0YXRlID09PSBcImxvYWRpbmdcIikge1xuICBkb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKFwiRE9NQ29udGVudExvYWRlZFwiLCBpbml0KTtcbn0gZWxzZSB7XG4gIGluaXQoKTtcbn1cbiJdLAogICJtYXBwaW5ncyI6ICI7OztBQVNPLFdBQVMsS0FBSyxJQUFhLE1BQWMsV0FBVyxJQUFZO0FBQ3JFLFdBQU8sR0FBRyxhQUFhLElBQUksS0FBSztBQUFBLEVBQ2xDOzs7QUNBQSxNQUFJLGFBQW1EO0FBSXZELFdBQVMsa0JBQWtCLFdBQXlCO0FBQ2xELFVBQU0sV0FBVyxTQUFTLGVBQWUsZ0JBQWdCO0FBQ3pELFFBQUksQ0FBQyxTQUFVO0FBQ2YsYUFBUyxjQUFjLFlBQVk7QUFDbkMsYUFBUyxNQUFNLFVBQVU7QUFDekIsYUFBUyxVQUFVLE9BQU8sV0FBVztBQUNyQyxhQUFTLFVBQVUsSUFBSSxZQUFZO0FBQ25DLFFBQUksZUFBZSxLQUFNLGNBQWEsVUFBVTtBQUNoRCxpQkFBYSxXQUFXLFdBQVk7QUFDbEMsZUFBUyxVQUFVLE9BQU8sWUFBWTtBQUN0QyxlQUFTLFVBQVUsSUFBSSxXQUFXO0FBQ2xDLGlCQUFXLFdBQVk7QUFDckIsaUJBQVMsTUFBTSxVQUFVO0FBQ3pCLGlCQUFTLFVBQVUsT0FBTyxXQUFXO0FBQUEsTUFDdkMsR0FBRyxHQUFHO0FBQUEsSUFDUixHQUFHLEdBQUk7QUFBQSxFQUNUO0FBSUEsV0FBUyxrQkFBa0IsTUFBb0I7QUFDN0MsVUFBTSxZQUFZLFNBQVMsZUFBZSxZQUFZO0FBQ3RELFFBQUksQ0FBQyxVQUFXO0FBQ2hCLGNBQVUsY0FBYztBQUV4QixjQUFVLFVBQVUsT0FBTyxlQUFlLGNBQWM7QUFDeEQsY0FBVSxVQUFVLElBQUksU0FBUyxXQUFXLGdCQUFnQixjQUFjO0FBQUEsRUFDNUU7QUFJQSxXQUFTLG1CQUF5QjtBQUNoQyxVQUFNLE9BQU8sU0FBUyxlQUFlLGNBQWM7QUFDbkQsUUFBSSxDQUFDLEtBQU07QUFFWCxVQUFNLFdBQVcsU0FBUyxjQUFtQyxXQUFXO0FBQ3hFLFVBQU0sWUFBWSxTQUFTLGNBQWlDLGFBQWE7QUFDekUs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LFFBQVEsYUFBYSxLQUFLLENBQUM7QUFDbEQsYUFBUyxZQUFZLFNBQVM7QUFFOUIsVUFBTSxVQUFVLE1BQU0sTUFBTTtBQUM1QixZQUFRLGFBQWEsS0FBSyxPQUFPLEVBQUUsQ0FBQztBQUNwQyxZQUFRLGFBQWEsS0FBSyxPQUFPLEtBQUssQ0FBQyxDQUFDO0FBQ3hDLFlBQVEsYUFBYSxlQUFlLFFBQVE7QUFDNUMsWUFBUSxhQUFhLGFBQWEsSUFBSTtBQUN0QyxZQUFRLGFBQWEsUUFBUSxNQUFNO0FBQ25DLFlBQVEsYUFBYSxlQUFlLE1BQU07QUFDMUMsWUFBUSxZQUFZLFNBQVMsZUFBZSxRQUFRLE1BQU0sTUFBTSxHQUFHLEVBQUUsQ0FBQyxDQUFDO0FBQ3ZFLGFBQVMsWUFBWSxPQUFPO0FBRTVCLFFBQUksWUFBWSxRQUFRO0FBRXhCLGNBQVUsWUFBWSxHQUFHO0FBQUEsRUFDM0I7QUFNTyxXQUFTQyxRQUFhO0FBQzNCLFVBQU0sWUFBWSxTQUFTLGVBQWUsb0JBQW9CO0FBQzlELFFBQUksV0FBVztBQUNiLDhCQUF3QixTQUFTO0FBQUEsSUFDbkM7QUFBQSxFQUNGOzs7QUNyTEEsV0FBU0MsUUFBYTtBQUNwQixTQUFTO0FBQ1QsSUFBQUEsTUFBYztBQUNkLElBQUFBLE1BQVU7QUFDVixJQUFBQSxNQUFXO0FBQ1gsSUFBQUEsTUFBZTtBQUNmLElBQUFBLE1BQWE7QUFDYixJQUFBQSxNQUFPO0FBQ1AsSUFBQUEsTUFBVTtBQUFBLEVBQ1o7QUFFQSxNQUFJLFNBQVMsZUFBZSxXQUFXO0FBQ3JDLGFBQVMsaUJBQWlCLG9CQUFvQkEsS0FBSTtBQUFBLEVBQ3BELE9BQU87QUFDTCxJQUFBQSxNQUFLO0FBQUEsRUFDUDsiLAogICJuYW1lcyI6IFsiaW5pdCIsICJpbml0IiwgImluaXQiLCAidmVyZGljdEJ0bnMiLCAidHlwZVBpbGxzIiwgInNwaW5uZXJXcmFwcGVyIiwgImluaXQiLCAiYnRuIiwgImluaXQiLCAiaW5pdCIsICJpbml0IiwgImluaXQiXQp9Cg==
