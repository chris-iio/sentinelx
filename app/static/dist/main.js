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
  function updateContextLine(card, result) {
    const contextLine = card.querySelector(".ioc-context-line");
    if (!contextLine) return;
    const provider = result.provider;
    const stats = result.raw_stats;
    if (!stats) return;
    if (provider === "IP Context") {
      const geo = stats.geo;
      if (!geo || typeof geo !== "string") return;
      const existing = contextLine.querySelector('span[data-context-provider="IP Context"]');
      if (existing) {
        existing.textContent = geo;
        return;
      }
      const asnSpan = contextLine.querySelector('span[data-context-provider="ASN Intel"]');
      if (asnSpan) {
        contextLine.removeChild(asnSpan);
      }
      const span = document.createElement("span");
      span.className = "context-field";
      span.setAttribute("data-context-provider", "IP Context");
      span.textContent = geo;
      contextLine.appendChild(span);
    } else if (provider === "ASN Intel") {
      if (contextLine.querySelector('span[data-context-provider="IP Context"]')) return;
      const asn = stats.asn;
      const prefix = stats.prefix;
      if (!asn && !prefix) return;
      const parts = [];
      if (asn && (typeof asn === "string" || typeof asn === "number")) parts.push(String(asn));
      if (prefix && typeof prefix === "string") parts.push(prefix);
      if (parts.length === 0) return;
      const text = parts.join(" \xB7 ");
      const existing = contextLine.querySelector('span[data-context-provider="ASN Intel"]');
      if (existing) {
        existing.textContent = text;
        return;
      }
      const span = document.createElement("span");
      span.className = "context-field";
      span.setAttribute("data-context-provider", "ASN Intel");
      span.textContent = text;
      contextLine.appendChild(span);
    } else if (provider === "DNS Records") {
      const aRecords = stats.a;
      if (!Array.isArray(aRecords) || aRecords.length === 0) return;
      const ips = aRecords.slice(0, 3).filter((ip) => typeof ip === "string");
      if (ips.length === 0) return;
      const text = "A: " + ips.join(", ");
      const existing = contextLine.querySelector('span[data-context-provider="DNS Records"]');
      if (existing) {
        existing.textContent = text;
        return;
      }
      const span = document.createElement("span");
      span.className = "context-field";
      span.setAttribute("data-context-provider", "DNS Records");
      span.textContent = text;
      contextLine.appendChild(span);
    }
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
        updateContextLine(card, result);
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
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vc3JjL3RzL3V0aWxzL2RvbS50cyIsICIuLi9zcmMvdHMvbW9kdWxlcy9mb3JtLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2NsaXBib2FyZC50cyIsICIuLi9zcmMvdHMvdHlwZXMvaW9jLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2NhcmRzLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2ZpbHRlci50cyIsICIuLi9zcmMvdHMvbW9kdWxlcy9leHBvcnQudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvdmVyZGljdC1jb21wdXRlLnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL3Jvdy1mYWN0b3J5LnRzIiwgIi4uL3NyYy90cy9tb2R1bGVzL2VucmljaG1lbnQudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvc2V0dGluZ3MudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvdWkudHMiLCAiLi4vc3JjL3RzL21vZHVsZXMvZ3JhcGgudHMiLCAiLi4vc3JjL3RzL21haW4udHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbIi8qKlxuICogU2hhcmVkIERPTSB1dGlsaXRpZXMgZm9yIFNlbnRpbmVsWCBUeXBlU2NyaXB0IG1vZHVsZXMuXG4gKi9cblxuLyoqXG4gKiBUeXBlZCBnZXRBdHRyaWJ1dGUgd3JhcHBlciBcdTIwMTQgcmV0dXJucyBzdHJpbmcgaW5zdGVhZCBvZiBzdHJpbmcgfCBudWxsLlxuICogQ2FsbGVycyBwYXNzIGEgZmFsbGJhY2sgKGRlZmF1bHQ6IFwiXCIpIHRvIGF2b2lkIG51bGwgcHJvcGFnYXRpb24uXG4gKiBBdHRyaWJ1dGUgbmFtZXMgYXJlIGludGVudGlvbmFsbHkgdHlwZWQgYXMgc3RyaW5nIChub3QgYSB1bmlvbikgZm9yIGZsZXhpYmlsaXR5LlxuICovXG5leHBvcnQgZnVuY3Rpb24gYXR0cihlbDogRWxlbWVudCwgbmFtZTogc3RyaW5nLCBmYWxsYmFjayA9IFwiXCIpOiBzdHJpbmcge1xuICByZXR1cm4gZWwuZ2V0QXR0cmlidXRlKG5hbWUpID8/IGZhbGxiYWNrO1xufVxuIiwgIi8qKlxuICogRm9ybSBjb250cm9scyBtb2R1bGUgXHUyMDE0IHN1Ym1pdCBidXR0b24gc3RhdGUsIGF1dG8tZ3JvdyB0ZXh0YXJlYSxcbiAqIG1vZGUgdG9nZ2xlLCBhbmQgcGFzdGUgZmVlZGJhY2suXG4gKlxuICogRXh0cmFjdGVkIGZyb20gbWFpbi5qcyBpbml0U3VibWl0QnV0dG9uKCksIGluaXRBdXRvR3JvdygpLFxuICogaW5pdE1vZGVUb2dnbGUoKSwgdXBkYXRlU3VibWl0TGFiZWwoKSwgc2hvd1Bhc3RlRmVlZGJhY2soKSAobGluZXMgMzQtMTYyKS5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vLyBNb2R1bGUtbGV2ZWwgdGltZXIgZm9yIHBhc3RlIGZlZWRiYWNrIGFuaW1hdGlvbiBcdTIwMTQgYXZvaWRzIHN0b3Jpbmcgb24gSFRNTEVsZW1lbnRcbmxldCBwYXN0ZVRpbWVyOiBSZXR1cm5UeXBlPHR5cGVvZiBzZXRUaW1lb3V0PiB8IG51bGwgPSBudWxsO1xuXG4vLyAtLS0tIFBhc3RlIGNoYXJhY3RlciBjb3VudCBmZWVkYmFjayAoSU5QVVQtMDIpIC0tLS1cblxuZnVuY3Rpb24gc2hvd1Bhc3RlRmVlZGJhY2soY2hhckNvdW50OiBudW1iZXIpOiB2b2lkIHtcbiAgY29uc3QgZmVlZGJhY2sgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInBhc3RlLWZlZWRiYWNrXCIpO1xuICBpZiAoIWZlZWRiYWNrKSByZXR1cm47XG4gIGZlZWRiYWNrLnRleHRDb250ZW50ID0gY2hhckNvdW50ICsgXCIgY2hhcmFjdGVycyBwYXN0ZWRcIjtcbiAgZmVlZGJhY2suc3R5bGUuZGlzcGxheSA9IFwiXCI7XG4gIGZlZWRiYWNrLmNsYXNzTGlzdC5yZW1vdmUoXCJpcy1oaWRpbmdcIik7XG4gIGZlZWRiYWNrLmNsYXNzTGlzdC5hZGQoXCJpcy12aXNpYmxlXCIpO1xuICBpZiAocGFzdGVUaW1lciAhPT0gbnVsbCkgY2xlYXJUaW1lb3V0KHBhc3RlVGltZXIpO1xuICBwYXN0ZVRpbWVyID0gc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgZmVlZGJhY2suY2xhc3NMaXN0LnJlbW92ZShcImlzLXZpc2libGVcIik7XG4gICAgZmVlZGJhY2suY2xhc3NMaXN0LmFkZChcImlzLWhpZGluZ1wiKTtcbiAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcbiAgICAgIGZlZWRiYWNrLnN0eWxlLmRpc3BsYXkgPSBcIm5vbmVcIjtcbiAgICAgIGZlZWRiYWNrLmNsYXNzTGlzdC5yZW1vdmUoXCJpcy1oaWRpbmdcIik7XG4gICAgfSwgMjUwKTtcbiAgfSwgMjAwMCk7XG59XG5cbi8vIC0tLS0gU3VibWl0IGxhYmVsIChtb2RlLWF3YXJlKSAtLS0tXG5cbmZ1bmN0aW9uIHVwZGF0ZVN1Ym1pdExhYmVsKG1vZGU6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCBzdWJtaXRCdG4gPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInN1Ym1pdC1idG5cIik7XG4gIGlmICghc3VibWl0QnRuKSByZXR1cm47XG4gIHN1Ym1pdEJ0bi50ZXh0Q29udGVudCA9IFwiRXh0cmFjdFwiO1xuICAvLyBNb2RlLWF3YXJlIGJ1dHRvbiBjb2xvclxuICBzdWJtaXRCdG4uY2xhc3NMaXN0LnJlbW92ZShcIm1vZGUtb25saW5lXCIsIFwibW9kZS1vZmZsaW5lXCIpO1xuICBzdWJtaXRCdG4uY2xhc3NMaXN0LmFkZChtb2RlID09PSBcIm9ubGluZVwiID8gXCJtb2RlLW9ubGluZVwiIDogXCJtb2RlLW9mZmxpbmVcIik7XG59XG5cbi8vIC0tLS0gU3VibWl0IGJ1dHRvbjogZGlzYWJsZSB3aGVuIHRleHRhcmVhIGlzIGVtcHR5IC0tLS1cblxuZnVuY3Rpb24gaW5pdFN1Ym1pdEJ1dHRvbigpOiB2b2lkIHtcbiAgY29uc3QgZm9ybSA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiYW5hbHl6ZS1mb3JtXCIpO1xuICBpZiAoIWZvcm0pIHJldHVybjtcblxuICBjb25zdCB0ZXh0YXJlYSA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTFRleHRBcmVhRWxlbWVudD4oXCIjaW9jLXRleHRcIik7XG4gIGNvbnN0IHN1Ym1pdEJ0biA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTEJ1dHRvbkVsZW1lbnQ+KFwiI3N1Ym1pdC1idG5cIik7XG4gIGNvbnN0IGNsZWFyQnRuID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJjbGVhci1idG5cIik7XG5cbiAgaWYgKCF0ZXh0YXJlYSB8fCAhc3VibWl0QnRuKSByZXR1cm47XG5cbiAgLy8gUmUtYmluZCB0byBub24tbnVsbGFibGUgYWxpYXNlcyBzbyBjbG9zdXJlcyBiZWxvdyBkb24ndCBuZWVkIGFzc2VydGlvbnMuXG4gIC8vIFR5cGVTY3JpcHQgbmFycm93cyB0aGUgb3V0ZXIgYGNvbnN0YCBhZnRlciB0aGUgaWYtY2hlY2ssIGJ1dCBjbG9zdXJlc1xuICAvLyAoZXZlbiBub24tYXN5bmMgb25lcykgY2Fubm90IHNlZSB0aGF0IG5hcnJvd2luZyBcdTIwMTQgd2UgdGhlcmVmb3JlIGludHJvZHVjZVxuICAvLyBuZXcgYGNvbnN0YCBiaW5kaW5ncyB0aGF0IGFyZSBndWFyYW50ZWVkIG5vbi1udWxsLlxuICBjb25zdCB0YTogSFRNTFRleHRBcmVhRWxlbWVudCA9IHRleHRhcmVhO1xuICBjb25zdCBzYjogSFRNTEJ1dHRvbkVsZW1lbnQgPSBzdWJtaXRCdG47XG5cbiAgZnVuY3Rpb24gdXBkYXRlU3VibWl0U3RhdGUoKTogdm9pZCB7XG4gICAgc2IuZGlzYWJsZWQgPSB0YS52YWx1ZS50cmltKCkubGVuZ3RoID09PSAwO1xuICB9XG5cbiAgdGEuYWRkRXZlbnRMaXN0ZW5lcihcImlucHV0XCIsIHVwZGF0ZVN1Ym1pdFN0YXRlKTtcblxuICAvLyBBbHNvIGhhbmRsZSBwYXN0ZSBldmVudHMgKGJyb3dzZXIgbWF5IG5vdCBmaXJlIFwiaW5wdXRcIiBpbW1lZGlhdGVseSlcbiAgdGEuYWRkRXZlbnRMaXN0ZW5lcihcInBhc3RlXCIsIGZ1bmN0aW9uICgpIHtcbiAgICAvLyBEZWZlciB1bnRpbCBhZnRlciBwYXN0ZSBjb250ZW50IGlzIGFwcGxpZWRcbiAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uICgpIHtcbiAgICAgIHVwZGF0ZVN1Ym1pdFN0YXRlKCk7XG4gICAgICBzaG93UGFzdGVGZWVkYmFjayh0YS52YWx1ZS5sZW5ndGgpO1xuICAgIH0sIDApO1xuICB9KTtcblxuICAvLyBJbml0aWFsIHN0YXRlIChwYWdlIGxvYWQgd2l0aCBwcmUtZmlsbGVkIGNvbnRlbnQpXG4gIHVwZGF0ZVN1Ym1pdFN0YXRlKCk7XG5cbiAgLy8gLS0tLSBDbGVhciBidXR0b24gLS0tLVxuICBpZiAoY2xlYXJCdG4pIHtcbiAgICBjbGVhckJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgICAgdGEudmFsdWUgPSBcIlwiO1xuICAgICAgdXBkYXRlU3VibWl0U3RhdGUoKTtcbiAgICAgIHRhLmZvY3VzKCk7XG4gICAgfSk7XG4gIH1cbn1cblxuLy8gLS0tLSBBdXRvLWdyb3cgdGV4dGFyZWEgKElOUC0wMikgLS0tLVxuXG5mdW5jdGlvbiBpbml0QXV0b0dyb3coKTogdm9pZCB7XG4gIGNvbnN0IHRleHRhcmVhID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcjxIVE1MVGV4dEFyZWFFbGVtZW50PihcIiNpb2MtdGV4dFwiKTtcbiAgaWYgKCF0ZXh0YXJlYSkgcmV0dXJuO1xuXG4gIC8vIE5vbi1udWxsYWJsZSBhbGlhcyBmb3IgdXNlIGluc2lkZSBjbG9zdXJlcyAoVHlwZVNjcmlwdCBjYW4ndCBuYXJyb3cgdGhyb3VnaCBjbG9zdXJlcylcbiAgY29uc3QgdGE6IEhUTUxUZXh0QXJlYUVsZW1lbnQgPSB0ZXh0YXJlYTtcblxuICBmdW5jdGlvbiBncm93KCk6IHZvaWQge1xuICAgIHRhLnN0eWxlLmhlaWdodCA9IFwiYXV0b1wiO1xuICAgIHRhLnN0eWxlLmhlaWdodCA9IHRhLnNjcm9sbEhlaWdodCArIFwicHhcIjtcbiAgfVxuXG4gIHRhLmFkZEV2ZW50TGlzdGVuZXIoXCJpbnB1dFwiLCBncm93KTtcblxuICB0YS5hZGRFdmVudExpc3RlbmVyKFwicGFzdGVcIiwgZnVuY3Rpb24gKCkge1xuICAgIHNldFRpbWVvdXQoZ3JvdywgMCk7XG4gIH0pO1xuXG4gIGdyb3coKTtcbn1cblxuLy8gLS0tLSBNb2RlIHRvZ2dsZSBzd2l0Y2ggKElOUFVULTAxLCBJTlBVVC0wMykgLS0tLVxuXG5mdW5jdGlvbiBpbml0TW9kZVRvZ2dsZSgpOiB2b2lkIHtcbiAgY29uc3Qgd2lkZ2V0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJtb2RlLXRvZ2dsZS13aWRnZXRcIik7XG4gIGNvbnN0IHRvZ2dsZUJ0biA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwibW9kZS10b2dnbGUtYnRuXCIpO1xuICBjb25zdCBtb2RlSW5wdXQgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yPEhUTUxJbnB1dEVsZW1lbnQ+KFwiI21vZGUtaW5wdXRcIik7XG4gIGlmICghd2lkZ2V0IHx8ICF0b2dnbGVCdG4gfHwgIW1vZGVJbnB1dCkgcmV0dXJuO1xuXG4gIC8vIE5vbi1udWxsYWJsZSBhbGlhc2VzIGZvciBjbG9zdXJlc1xuICBjb25zdCB3OiBIVE1MRWxlbWVudCA9IHdpZGdldDtcbiAgY29uc3QgdGI6IEhUTUxFbGVtZW50ID0gdG9nZ2xlQnRuO1xuICBjb25zdCBtaTogSFRNTElucHV0RWxlbWVudCA9IG1vZGVJbnB1dDtcblxuICB0Yi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgIGNvbnN0IGN1cnJlbnQgPSBhdHRyKHcsIFwiZGF0YS1tb2RlXCIpO1xuICAgIGNvbnN0IG5leHQgPSBjdXJyZW50ID09PSBcIm9mZmxpbmVcIiA/IFwib25saW5lXCIgOiBcIm9mZmxpbmVcIjtcbiAgICB3LnNldEF0dHJpYnV0ZShcImRhdGEtbW9kZVwiLCBuZXh0KTtcbiAgICBtaS52YWx1ZSA9IG5leHQ7XG4gICAgdGIuc2V0QXR0cmlidXRlKFwiYXJpYS1wcmVzc2VkXCIsIG5leHQgPT09IFwib25saW5lXCIgPyBcInRydWVcIiA6IFwiZmFsc2VcIik7XG4gICAgdXBkYXRlU3VibWl0TGFiZWwobmV4dCk7XG4gIH0pO1xuXG4gIC8vIFNldCBpbml0aWFsIGxhYmVsIGJhc2VkIG9uIGN1cnJlbnQgbW9kZSAoZGVmZW5zaXZlKVxuICB1cGRhdGVTdWJtaXRMYWJlbChtaS52YWx1ZSk7XG59XG5cbi8vIC0tLS0gUHVibGljIEFQSSAtLS0tXG5cbi8qKlxuICogSW5pdGlhbGlzZSBhbGwgZm9ybSBjb250cm9sczogc3VibWl0IGJ1dHRvbiBzdGF0ZSwgYXV0by1ncm93LCBhbmQgbW9kZSB0b2dnbGUuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBpbml0U3VibWl0QnV0dG9uKCk7XG4gIGluaXRBdXRvR3JvdygpO1xuICBpbml0TW9kZVRvZ2dsZSgpO1xufVxuIiwgIi8qKlxuICogQ2xpcGJvYXJkIG1vZHVsZSBcdTIwMTQgY29weSBidXR0b25zLCBjb3B5LXdpdGgtZW5yaWNobWVudCwgYW5kIGZhbGxiYWNrIGNvcHkuXG4gKlxuICogRXh0cmFjdGVkIGZyb20gbWFpbi5qcyBpbml0Q29weUJ1dHRvbnMoKSwgc2hvd0NvcGllZEZlZWRiYWNrKCksXG4gKiBmYWxsYmFja0NvcHkoKSwgYW5kIHdyaXRlVG9DbGlwYm9hcmQoKSAobGluZXMgMTY2LTIyMykuXG4gKlxuICogd3JpdGVUb0NsaXBib2FyZCBpcyBleHBvcnRlZCBmb3IgdXNlIGJ5IFBoYXNlIDIyJ3MgZW5yaWNobWVudCBtb2R1bGVcbiAqIChleHBvcnQgYnV0dG9uIG5lZWRzIHRvIGNvcHkgbXVsdGktSU9DIHRleHQgdG8gY2xpcGJvYXJkKS5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vLyAtLS0tIFByaXZhdGUgaGVscGVycyAtLS0tXG5cbi8qKlxuICogVGVtcG9yYXJpbHkgcmVwbGFjZSBidXR0b24gdGV4dCB3aXRoIFwiQ29waWVkIVwiIHRoZW4gcmVzdG9yZSBhZnRlciAxNTAwbXMuXG4gKiB0ZXh0Q29udGVudCBpcyB0eXBlZCBzdHJpbmd8bnVsbCBcdTIwMTQgPz8gZW5zdXJlcyB0aGUgb3JpZ2luYWwgdmFsdWUgaXMgbmV2ZXIgbnVsbC5cbiAqL1xuZnVuY3Rpb24gc2hvd0NvcGllZEZlZWRiYWNrKGJ0bjogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgY29uc3Qgb3JpZ2luYWwgPSBidG4udGV4dENvbnRlbnQgPz8gXCJDb3B5XCI7XG4gIGJ0bi50ZXh0Q29udGVudCA9IFwiQ29waWVkIVwiO1xuICBidG4uY2xhc3NMaXN0LmFkZChcImNvcGllZFwiKTtcbiAgc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgYnRuLnRleHRDb250ZW50ID0gb3JpZ2luYWw7XG4gICAgYnRuLmNsYXNzTGlzdC5yZW1vdmUoXCJjb3BpZWRcIik7XG4gIH0sIDE1MDApO1xufVxuXG4vKipcbiAqIEZhbGxiYWNrIGNvcHkgdmlhIGEgdGVtcG9yYXJ5IG9mZi1zY3JlZW4gdGV4dGFyZWEgYW5kIGV4ZWNDb21tYW5kKFwiY29weVwiKS5cbiAqIFVzZWQgd2hlbiBuYXZpZ2F0b3IuY2xpcGJvYXJkIGlzIHVuYXZhaWxhYmxlIChub24tSFRUUFMsIG9sZGVyIGJyb3dzZXIpLlxuICovXG5mdW5jdGlvbiBmYWxsYmFja0NvcHkodGV4dDogc3RyaW5nLCBidG46IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gIC8vIENyZWF0ZSBhIHRlbXBvcmFyeSB0ZXh0YXJlYSwgc2VsZWN0IGl0cyBjb250ZW50LCBhbmQgY29weVxuICBjb25zdCB0bXAgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwidGV4dGFyZWFcIik7XG4gIHRtcC52YWx1ZSA9IHRleHQ7XG4gIHRtcC5zdHlsZS5wb3NpdGlvbiA9IFwiZml4ZWRcIjtcbiAgdG1wLnN0eWxlLnRvcCA9IFwiLTk5OTlweFwiO1xuICB0bXAuc3R5bGUubGVmdCA9IFwiLTk5OTlweFwiO1xuICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKHRtcCk7XG4gIHRtcC5mb2N1cygpO1xuICB0bXAuc2VsZWN0KCk7XG4gIHRyeSB7XG4gICAgZG9jdW1lbnQuZXhlY0NvbW1hbmQoXCJjb3B5XCIpO1xuICAgIHNob3dDb3BpZWRGZWVkYmFjayhidG4pO1xuICB9IGNhdGNoIHtcbiAgICAvLyBDb3B5IGZhaWxlZCBzaWxlbnRseSBcdTIwMTQgdXNlciBjYW4gc3RpbGwgbWFudWFsbHkgc2VsZWN0IHRoZSB2YWx1ZVxuICB9IGZpbmFsbHkge1xuICAgIGRvY3VtZW50LmJvZHkucmVtb3ZlQ2hpbGQodG1wKTtcbiAgfVxufVxuXG4vLyAtLS0tIFB1YmxpYyBBUEkgLS0tLVxuXG4vKipcbiAqIENvcHkgdGV4dCB0byB0aGUgY2xpcGJvYXJkIHVzaW5nIHRoZSBDbGlwYm9hcmQgQVBJLCBmYWxsaW5nIGJhY2sgdG9cbiAqIGV4ZWNDb21tYW5kIHdoZW4gdW5hdmFpbGFibGUuIFNob3dzIGZlZWRiYWNrIG9uIHRoZSB0cmlnZ2VyaW5nIGJ1dHRvbi5cbiAqXG4gKiBFeHBvcnRlZCBzbyBQaGFzZSAyMidzIGVucmljaG1lbnQgbW9kdWxlIGNhbiBjYWxsIGl0IGZvciB0aGUgZXhwb3J0IGJ1dHRvbi5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIHdyaXRlVG9DbGlwYm9hcmQodGV4dDogc3RyaW5nLCBidG46IEhUTUxFbGVtZW50KTogdm9pZCB7XG4gIGlmICghbmF2aWdhdG9yLmNsaXBib2FyZCkge1xuICAgIGZhbGxiYWNrQ29weSh0ZXh0LCBidG4pO1xuICAgIHJldHVybjtcbiAgfVxuICBuYXZpZ2F0b3IuY2xpcGJvYXJkLndyaXRlVGV4dCh0ZXh0KS50aGVuKGZ1bmN0aW9uICgpIHtcbiAgICBzaG93Q29waWVkRmVlZGJhY2soYnRuKTtcbiAgfSkuY2F0Y2goZnVuY3Rpb24gKCkge1xuICAgIGZhbGxiYWNrQ29weSh0ZXh0LCBidG4pO1xuICB9KTtcbn1cblxuLyoqXG4gKiBBdHRhY2ggY2xpY2sgaGFuZGxlcnMgdG8gYWxsIC5jb3B5LWJ0biBlbGVtZW50cyBwcmVzZW50IGluIHRoZSBET00uXG4gKiBFYWNoIGJ1dHRvbiByZWFkcyBkYXRhLXZhbHVlIChJT0MpIGFuZCBvcHRpb25hbGx5IGRhdGEtZW5yaWNobWVudCAod29yc3QgdmVyZGljdCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICBjb25zdCBjb3B5QnV0dG9ucyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmNvcHktYnRuXCIpO1xuXG4gIGNvcHlCdXR0b25zLmZvckVhY2goZnVuY3Rpb24gKGJ0bikge1xuICAgIGJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgICAgY29uc3QgdmFsdWUgPSBhdHRyKGJ0biwgXCJkYXRhLXZhbHVlXCIpO1xuICAgICAgaWYgKCF2YWx1ZSkgcmV0dXJuO1xuXG4gICAgICAvLyBDaGVjayBmb3IgZW5yaWNobWVudCBzdW1tYXJ5IHNldCBieSBwb2xsaW5nIGxvb3AgKHdvcnN0IHZlcmRpY3QpXG4gICAgICBjb25zdCBlbnJpY2htZW50ID0gYXR0cihidG4sIFwiZGF0YS1lbnJpY2htZW50XCIpO1xuICAgICAgLy8gYXR0cigpIHJldHVybnMgXCJcIiB3aGVuIGF0dHJpYnV0ZSBpcyBhYnNlbnQgKGZhbHN5KSBcdTIwMTQgc2FtZSB0ZXJuYXJ5IGFzIG9yaWdpbmFsXG4gICAgICBjb25zdCBjb3B5VGV4dCA9IGVucmljaG1lbnQgPyAodmFsdWUgKyBcIiB8IFwiICsgZW5yaWNobWVudCkgOiB2YWx1ZTtcblxuICAgICAgd3JpdGVUb0NsaXBib2FyZChjb3B5VGV4dCwgYnRuKTtcbiAgICB9KTtcbiAgfSk7XG59XG4iLCAiLyoqXG4gKiBEb21haW4gdHlwZXMgYW5kIGNvbnN0YW50cyBmb3IgSU9DIChJbmRpY2F0b3Igb2YgQ29tcHJvbWlzZSkgZW5yaWNobWVudC5cbiAqXG4gKiBUaGlzIG1vZHVsZSBkZWZpbmVzIHRoZSBzaGFyZWQgdHlwZSBsYXllciBmb3IgdmVyZGljdCB2YWx1ZXMgYW5kIElPQyBtZXRhZGF0YS5cbiAqIEFsbCBjb25zdGFudHMgYXJlIHNvdXJjZWQgZnJvbSBhcHAvc3RhdGljL21haW4uanMgYW5kIG11c3QgcmVtYWluIGluIHN5bmNcbiAqIHdpdGggdGhlIEZsYXNrIGJhY2tlbmQgdmVyZGljdCB2YWx1ZXMuXG4gKlxuICogU2hhcmVkIHR5cGUgZGVmaW5pdGlvbnMsIHR5cGVkIGNvbnN0YW50cywgYW5kIHZlcmRpY3QgdXRpbGl0eSBmdW5jdGlvbnMuXG4gKi9cblxuLyoqXG4gKiBUaGUgdmVyZGljdCBrZXlzIHJldHVybmVkIGJ5IHRoZSBGbGFzayBlbnJpY2htZW50IEFQSS5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgVkVSRElDVF9MQUJFTFMga2V5cyAobGluZXMgMjMxXHUyMDEzMjM3KS5cbiAqIFVzZWQgYXMgZGlzY3JpbWluYW50IHZhbHVlcyB0aHJvdWdob3V0IGVucmljaG1lbnQgcmVzdWx0IHByb2Nlc3NpbmcuXG4gKlxuICogTm90ZToga25vd25fZ29vZCBpcyBpbnRlbnRpb25hbGx5IGV4Y2x1ZGVkIGZyb20gVkVSRElDVF9TRVZFUklUWSBcdTIwMTQgaXQgaXNcbiAqIG5vdCBhIHNldmVyaXR5IGxldmVsIGJ1dCBhIGNsYXNzaWZpY2F0aW9uIG92ZXJyaWRlLiB2ZXJkaWN0U2V2ZXJpdHlJbmRleCgpXG4gKiByZXR1cm5zIC0xIGZvciBrbm93bl9nb29kLCB3aGljaCBpcyBjb3JyZWN0IGFuZCBpbnRlbnRpb25hbC5cbiAqL1xuZXhwb3J0IHR5cGUgVmVyZGljdEtleSA9XG4gIHwgXCJlcnJvclwiXG4gIHwgXCJub19kYXRhXCJcbiAgfCBcImNsZWFuXCJcbiAgfCBcInN1c3BpY2lvdXNcIlxuICB8IFwibWFsaWNpb3VzXCJcbiAgfCBcImtub3duX2dvb2RcIjtcblxuLyoqXG4gKiBUaGUgc2V2ZW4gSU9DIHR5cGVzIHN1cHBvcnRlZCBmb3IgZW5yaWNobWVudC5cbiAqXG4gKiBPbmx5IGVucmljaGFibGUgdHlwZXMgYXJlIGluY2x1ZGVkIFx1MjAxNCBOT1QgXCJjdmVcIiAoQ1ZFcyBhcmUgZXh0cmFjdGVkIGJ1dFxuICogbmV2ZXIgZW5yaWNoZWQsIGFuZCBJT0NfUFJPVklERVJfQ09VTlRTIGhhcyBubyBcImN2ZVwiIGVudHJ5KS5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgSU9DX1BST1ZJREVSX0NPVU5UUyBrZXlzIChsaW5lcyAyNDJcdTIwMTMyNTApLlxuICovXG50eXBlIElvY1R5cGUgPVxuICB8IFwiaXB2NFwiXG4gIHwgXCJpcHY2XCJcbiAgfCBcImRvbWFpblwiXG4gIHwgXCJ1cmxcIlxuICB8IFwibWQ1XCJcbiAgfCBcInNoYTFcIlxuICB8IFwic2hhMjU2XCI7XG5cbi8qKlxuICogUmFua2VkIHNldmVyaXR5IHZlcmRpY3RzIFx1MjAxNCBpbmRleCAwIGlzIGxlYXN0IHNldmVyZSwgaW5kZXggNCBpcyBtb3N0IHNldmVyZS5cbiAqXG4gKiBrbm93bl9nb29kIGlzIGludGVudGlvbmFsbHkgZXhjbHVkZWQ6IGl0IGlzIGEgY2xhc3NpZmljYXRpb24gb3ZlcnJpZGUsIG5vdFxuICogYSBzZXZlcml0eSBsZXZlbC4gdmVyZGljdFNldmVyaXR5SW5kZXggcmV0dXJucyAtMSBmb3Iga25vd25fZ29vZCwgd2hpY2ggaXNcbiAqIHRoZSBjb3JyZWN0IGFuZCBleHBlY3RlZCBiZWhhdmlvciAoaXQgYWx3YXlzIHdpbnMgdmlhIGNvbXB1dGVXb3JzdFZlcmRpY3Qnc1xuICogZWFybHktcmV0dXJuIGNoZWNrLCBub3QgYnkgc2V2ZXJpdHkgcmFua2luZykuXG4gKlxuICogU291cmNlOiBtYWluLmpzIGxpbmUgMjI4LlxuICovXG50eXBlIFJhbmtlZFZlcmRpY3QgPSBcImVycm9yXCIgfCBcIm5vX2RhdGFcIiB8IFwiY2xlYW5cIiB8IFwic3VzcGljaW91c1wiIHwgXCJtYWxpY2lvdXNcIjtcblxuY29uc3QgVkVSRElDVF9TRVZFUklUWSA9IFtcbiAgXCJlcnJvclwiLFxuICBcIm5vX2RhdGFcIixcbiAgXCJjbGVhblwiLFxuICBcInN1c3BpY2lvdXNcIixcbiAgXCJtYWxpY2lvdXNcIixcbl0gYXMgY29uc3Qgc2F0aXNmaWVzIHJlYWRvbmx5IFJhbmtlZFZlcmRpY3RbXTtcblxuLyoqXG4gKiBSZXR1cm5zIHRoZSBzZXZlcml0eSBpbmRleCBmb3IgYSB2ZXJkaWN0IGtleS5cbiAqIEhpZ2hlciBpbmRleCA9IGhpZ2hlciBzZXZlcml0eS4gUmV0dXJucyAtMSBpZiBub3QgZm91bmQgKGUuZy4ga25vd25fZ29vZCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiB2ZXJkaWN0U2V2ZXJpdHlJbmRleCh2ZXJkaWN0OiBWZXJkaWN0S2V5KTogbnVtYmVyIHtcbiAgcmV0dXJuIChWRVJESUNUX1NFVkVSSVRZIGFzIHJlYWRvbmx5IHN0cmluZ1tdKS5pbmRleE9mKHZlcmRpY3QpO1xufVxuXG4vKipcbiAqIEh1bWFuLXJlYWRhYmxlIGRpc3BsYXkgbGFiZWxzIGZvciBlYWNoIHZlcmRpY3Qga2V5LlxuICpcbiAqIFR5cGVkIGFzIGBSZWNvcmQ8VmVyZGljdEtleSwgc3RyaW5nPmAgdG8gZW5zdXJlIGFsbCBmaXZlIGtleXMgYXJlIHByZXNlbnRcbiAqIGFuZCB0aGF0IGluZGV4aW5nIHdpdGggYW4gaW52YWxpZCBrZXkgcHJvZHVjZXMgYSBjb21waWxlIGVycm9yIHVuZGVyXG4gKiBgbm9VbmNoZWNrZWRJbmRleGVkQWNjZXNzYC5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgbGluZXMgMjMxXHUyMDEzMjM3LlxuICovXG5leHBvcnQgY29uc3QgVkVSRElDVF9MQUJFTFM6IFJlY29yZDxWZXJkaWN0S2V5LCBzdHJpbmc+ID0ge1xuICBtYWxpY2lvdXM6IFwiTUFMSUNJT1VTXCIsXG4gIHN1c3BpY2lvdXM6IFwiU1VTUElDSU9VU1wiLFxuICBjbGVhbjogXCJDTEVBTlwiLFxuICBrbm93bl9nb29kOiBcIktOT1dOIEdPT0RcIixcbiAgbm9fZGF0YTogXCJOTyBEQVRBXCIsXG4gIGVycm9yOiBcIkVSUk9SXCIsXG59IGFzIGNvbnN0O1xuXG4vKipcbiAqIEhhcmRjb2RlZCBmYWxsYmFjayBwcm92aWRlciBjb3VudHMgcGVyIGVucmljaGFibGUgSU9DIHR5cGUuXG4gKlxuICogVXNlZCBhcyBhIGZhbGxiYWNrIHdoZW4gdGhlIGRhdGEtcHJvdmlkZXItY291bnRzIERPTSBhdHRyaWJ1dGUgaXMgYWJzZW50XG4gKiAob2ZmbGluZSBtb2RlIG9yIHNlcnZlciBlcnJvcikuIFJlZmxlY3RzIHRoZSBiYXNlbGluZSAzLXByb3ZpZGVyIHNldHVwOlxuICogVmlydXNUb3RhbCBzdXBwb3J0cyBhbGwgNyB0eXBlcywgTWFsd2FyZUJhemFhciBzdXBwb3J0cyBtZDUvc2hhMS9zaGEyNTYsXG4gKiBUaHJlYXRGb3ggc3VwcG9ydHMgYWxsIDcuXG4gKlxuICogUHJpdmF0ZSBcdTIwMTQgY2FsbGVycyBtdXN0IHVzZSBnZXRQcm92aWRlckNvdW50cygpIHRvIGFsbG93IHJ1bnRpbWUgb3ZlcnJpZGVcbiAqIGZyb20gdGhlIERPTSBhdHRyaWJ1dGUgcG9wdWxhdGVkIGJ5IHRoZSBGbGFzayByb3V0ZS5cbiAqL1xuY29uc3QgX2RlZmF1bHRQcm92aWRlckNvdW50czogUmVjb3JkPElvY1R5cGUsIG51bWJlcj4gPSB7XG4gIGlwdjQ6IDIsXG4gIGlwdjY6IDIsXG4gIGRvbWFpbjogMixcbiAgdXJsOiAyLFxuICBtZDU6IDMsXG4gIHNoYTE6IDMsXG4gIHNoYTI1NjogMyxcbn0gYXMgY29uc3Q7XG5cbi8qKlxuICogUmV0dXJuIHByb3ZpZGVyIGNvdW50cyBwZXIgSU9DIHR5cGUsIHJlYWRpbmcgZnJvbSB0aGUgRE9NIHdoZW4gYXZhaWxhYmxlLlxuICpcbiAqIE9uIHRoZSByZXN1bHRzIHBhZ2UgaW4gb25saW5lIG1vZGUsIEZsYXNrIGluamVjdHMgdGhlIGFjdHVhbCByZWdpc3RyeSBjb3VudHNcbiAqIHZpYSBkYXRhLXByb3ZpZGVyLWNvdW50cyBvbiAucGFnZS1yZXN1bHRzLiBUaGlzIGZ1bmN0aW9uIHJlYWRzIHRoYXQgYXR0cmlidXRlXG4gKiBzbyB0aGUgcGVuZGluZy1pbmRpY2F0b3IgbG9naWMgcmVmbGVjdHMgdGhlIHJlYWwgY29uZmlndXJlZCBwcm92aWRlciBzZXRcbiAqIChlLmcuLCA4KyBwcm92aWRlcnMgaW4gdjQuMCkgcmF0aGVyIHRoYW4gYSBzdGFsZSBoYXJkY29kZWQgdmFsdWUuXG4gKlxuICogRmFsbHMgYmFjayB0byBfZGVmYXVsdFByb3ZpZGVyQ291bnRzIHdoZW46XG4gKiAgIC0gLnBhZ2UtcmVzdWx0cyBlbGVtZW50IGlzIGFic2VudCAobm90IG9uIHJlc3VsdHMgcGFnZSlcbiAqICAgLSBkYXRhLXByb3ZpZGVyLWNvdW50cyBhdHRyaWJ1dGUgaXMgbWlzc2luZyAob2ZmbGluZSBtb2RlKVxuICogICAtIEpTT04gcGFyc2UgZmFpbHMgKG1hbGZvcm1lZCBhdHRyaWJ1dGUpXG4gKlxuICogUmV0dXJuczpcbiAqICAgUmVjb3JkIG1hcHBpbmcgSU9DIHR5cGUgc3RyaW5nIFx1MjE5MiBjb25maWd1cmVkIHByb3ZpZGVyIGNvdW50LlxuICovXG5leHBvcnQgZnVuY3Rpb24gZ2V0UHJvdmlkZXJDb3VudHMoKTogUmVjb3JkPHN0cmluZywgbnVtYmVyPiB7XG4gIGNvbnN0IGVsID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIucGFnZS1yZXN1bHRzXCIpO1xuICBpZiAoZWwgPT09IG51bGwpIHJldHVybiBfZGVmYXVsdFByb3ZpZGVyQ291bnRzO1xuICBjb25zdCByYXcgPSBlbC5nZXRBdHRyaWJ1dGUoXCJkYXRhLXByb3ZpZGVyLWNvdW50c1wiKTtcbiAgaWYgKHJhdyA9PT0gbnVsbCkgcmV0dXJuIF9kZWZhdWx0UHJvdmlkZXJDb3VudHM7XG4gIHRyeSB7XG4gICAgcmV0dXJuIEpTT04ucGFyc2UocmF3KSBhcyBSZWNvcmQ8c3RyaW5nLCBudW1iZXI+O1xuICB9IGNhdGNoIHtcbiAgICByZXR1cm4gX2RlZmF1bHRQcm92aWRlckNvdW50cztcbiAgfVxufVxuIiwgIi8qKlxuICogQ2FyZCBtYW5hZ2VtZW50IG1vZHVsZSBcdTIwMTQgdmVyZGljdCB1cGRhdGVzLCBkYXNoYm9hcmQgY291bnRzLCBzZXZlcml0eSBzb3J0aW5nLlxuICpcbiAqIEV4dHJhY3RlZCBmcm9tIG1haW4uanMgbGluZXMgMjUyLTMzNi5cbiAqIFByb3ZpZGVzIHRoZSBwdWJsaWMgQVBJIGNvbnN1bWVkIGJ5IFBoYXNlIDIyJ3MgZW5yaWNobWVudCBtb2R1bGUuXG4gKi9cblxuaW1wb3J0IHR5cGUgeyBWZXJkaWN0S2V5IH0gZnJvbSBcIi4uL3R5cGVzL2lvY1wiO1xuaW1wb3J0IHsgVkVSRElDVF9MQUJFTFMsIHZlcmRpY3RTZXZlcml0eUluZGV4IH0gZnJvbSBcIi4uL3R5cGVzL2lvY1wiO1xuaW1wb3J0IHsgYXR0ciB9IGZyb20gXCIuLi91dGlscy9kb21cIjtcblxuLyoqXG4gKiBNb2R1bGUtbGV2ZWwgZGVib3VuY2UgdGltZXIgZm9yIHNvcnRDYXJkc0J5U2V2ZXJpdHkuXG4gKiBVc2VzIFJldHVyblR5cGU8dHlwZW9mIHNldFRpbWVvdXQ+IHRvIGF2b2lkIE5vZGVKUy5UaW1lb3V0IGNvbmZsaWN0LlxuICovXG5sZXQgc29ydFRpbWVyOiBSZXR1cm5UeXBlPHR5cGVvZiBzZXRUaW1lb3V0PiB8IG51bGwgPSBudWxsO1xuXG4vKipcbiAqIEluaXRpYWxpc2UgdGhlIGNhcmRzIG1vZHVsZS5cbiAqIENhcmRzIGhhdmUgbm8gRE9NQ29udGVudExvYWRlZCBzZXR1cCBcdTIwMTQgdGhlaXIgZnVuY3Rpb25zIGFyZSBjYWxsZWQgYnkgdGhlXG4gKiBlbnJpY2htZW50IG1vZHVsZS4gRXhwb3J0ZWQgZm9yIGNvbnNpc3RlbmN5IHdpdGggdGhlIG1vZHVsZSBwYXR0ZXJuO1xuICogbWFpbi50cyB3aWxsIGNhbGwgaXQgaW4gUGhhc2UgMjIuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbml0KCk6IHZvaWQge1xuICAvLyBOby1vcCBmb3IgUGhhc2UgMjEgXHUyMDE0IGNhcmRzIG1vZHVsZSBoYXMgbm8gRE9NQ29udGVudExvYWRlZCB3aXJpbmcuXG4gIC8vIENhbGxlZCBieSBtYWluLnRzIGZvciBjb25zaXN0ZW50IG1vZHVsZSBpbml0aWFsaXNhdGlvbi5cbn1cblxuLyoqXG4gKiBGaW5kIHRoZSBJT0MgY2FyZCBlbGVtZW50IGZvciBhIGdpdmVuIElPQyB2YWx1ZSB1c2luZyBDU1MuZXNjYXBlLlxuICogUmV0dXJucyBudWxsIGlmIG5vIG1hdGNoaW5nIGNhcmQgaXMgZm91bmQuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBmaW5kQ2FyZEZvcklvYyhpb2NWYWx1ZTogc3RyaW5nKTogSFRNTEVsZW1lbnQgfCBudWxsIHtcbiAgcmV0dXJuIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFxuICAgICcuaW9jLWNhcmRbZGF0YS1pb2MtdmFsdWU9XCInICsgQ1NTLmVzY2FwZShpb2NWYWx1ZSkgKyAnXCJdJ1xuICApO1xufVxuXG4vKipcbiAqIFVwZGF0ZSBhIGNhcmQncyB2ZXJkaWN0OiBzZXRzIGRhdGEtdmVyZGljdCBhdHRyaWJ1dGUsIHZlcmRpY3QgbGFiZWwgdGV4dCxcbiAqIGFuZCB2ZXJkaWN0IGxhYmVsIENTUyBjbGFzcy5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIHVwZGF0ZUNhcmRWZXJkaWN0KFxuICBpb2NWYWx1ZTogc3RyaW5nLFxuICB3b3JzdFZlcmRpY3Q6IFZlcmRpY3RLZXlcbik6IHZvaWQge1xuICBjb25zdCBjYXJkID0gZmluZENhcmRGb3JJb2MoaW9jVmFsdWUpO1xuICBpZiAoIWNhcmQpIHJldHVybjtcblxuICAvLyBVcGRhdGUgZGF0YS12ZXJkaWN0IGF0dHJpYnV0ZSAoZHJpdmVzIENTUyBib3JkZXIgY29sb3VyKVxuICBjYXJkLnNldEF0dHJpYnV0ZShcImRhdGEtdmVyZGljdFwiLCB3b3JzdFZlcmRpY3QpO1xuXG4gIC8vIFVwZGF0ZSB2ZXJkaWN0IGxhYmVsIHRleHQgYW5kIGNsYXNzXG4gIGNvbnN0IGxhYmVsID0gY2FyZC5xdWVyeVNlbGVjdG9yKFwiLnZlcmRpY3QtbGFiZWxcIik7XG4gIGlmIChsYWJlbCkge1xuICAgIC8vIFJlbW92ZSBhbGwgdmVyZGljdC1sYWJlbC0tKiBjbGFzc2VzLCB0aGVuIGFkZCB0aGUgY29ycmVjdCBvbmVcbiAgICBjb25zdCBjbGFzc2VzID0gbGFiZWwuY2xhc3NOYW1lXG4gICAgICAuc3BsaXQoXCIgXCIpXG4gICAgICAuZmlsdGVyKChjKSA9PiAhYy5zdGFydHNXaXRoKFwidmVyZGljdC1sYWJlbC0tXCIpKTtcbiAgICBjbGFzc2VzLnB1c2goXCJ2ZXJkaWN0LWxhYmVsLS1cIiArIHdvcnN0VmVyZGljdCk7XG4gICAgbGFiZWwuY2xhc3NOYW1lID0gY2xhc3Nlcy5qb2luKFwiIFwiKTtcbiAgICBsYWJlbC50ZXh0Q29udGVudCA9IFZFUkRJQ1RfTEFCRUxTW3dvcnN0VmVyZGljdF0gfHwgd29yc3RWZXJkaWN0LnRvVXBwZXJDYXNlKCk7XG4gIH1cbn1cblxuLyoqXG4gKiBDb3VudCBjYXJkcyBieSB2ZXJkaWN0IGFuZCB1cGRhdGUgZGFzaGJvYXJkIGNvdW50IGVsZW1lbnRzLlxuICovXG5leHBvcnQgZnVuY3Rpb24gdXBkYXRlRGFzaGJvYXJkQ291bnRzKCk6IHZvaWQge1xuICBjb25zdCBkYXNoYm9hcmQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInZlcmRpY3QtZGFzaGJvYXJkXCIpO1xuICBpZiAoIWRhc2hib2FyZCkgcmV0dXJuO1xuXG4gIGNvbnN0IGNhcmRzID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuaW9jLWNhcmRcIik7XG4gIGNvbnN0IGNvdW50czogUmVjb3JkPHN0cmluZywgbnVtYmVyPiA9IHtcbiAgICBtYWxpY2lvdXM6IDAsXG4gICAgc3VzcGljaW91czogMCxcbiAgICBjbGVhbjogMCxcbiAgICBrbm93bl9nb29kOiAwLFxuICAgIG5vX2RhdGE6IDAsXG4gIH07XG5cbiAgY2FyZHMuZm9yRWFjaCgoY2FyZCkgPT4ge1xuICAgIGNvbnN0IHYgPSBhdHRyKGNhcmQsIFwiZGF0YS12ZXJkaWN0XCIpO1xuICAgIGlmIChPYmplY3QucHJvdG90eXBlLmhhc093blByb3BlcnR5LmNhbGwoY291bnRzLCB2KSkge1xuICAgICAgY291bnRzW3ZdID0gKGNvdW50c1t2XSA/PyAwKSArIDE7XG4gICAgfVxuICB9KTtcblxuICBjb25zdCB2ZXJkaWN0cyA9IFtcIm1hbGljaW91c1wiLCBcInN1c3BpY2lvdXNcIiwgXCJjbGVhblwiLCBcImtub3duX2dvb2RcIiwgXCJub19kYXRhXCJdO1xuICB2ZXJkaWN0cy5mb3JFYWNoKCh2ZXJkaWN0KSA9PiB7XG4gICAgY29uc3QgY291bnRFbCA9IGRhc2hib2FyZC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcbiAgICAgICdbZGF0YS12ZXJkaWN0LWNvdW50PVwiJyArIHZlcmRpY3QgKyAnXCJdJ1xuICAgICk7XG4gICAgaWYgKGNvdW50RWwpIHtcbiAgICAgIGNvdW50RWwudGV4dENvbnRlbnQgPSBTdHJpbmcoY291bnRzW3ZlcmRpY3RdID8/IDApO1xuICAgIH1cbiAgfSk7XG59XG5cbi8qKlxuICogRGVib3VuY2VkIGVudHJ5IHBvaW50OiBzY2hlZHVsZXMgZG9Tb3J0Q2FyZHMgd2l0aCBhIDEwMCBtcyBkZWxheS5cbiAqIENhbGxpbmcgdGhpcyBtdWx0aXBsZSB0aW1lcyBpbiBxdWljayBzdWNjZXNzaW9uIG9ubHkgdHJpZ2dlcnMgb25lIHNvcnQuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBzb3J0Q2FyZHNCeVNldmVyaXR5KCk6IHZvaWQge1xuICBpZiAoc29ydFRpbWVyICE9PSBudWxsKSBjbGVhclRpbWVvdXQoc29ydFRpbWVyKTtcbiAgc29ydFRpbWVyID0gc2V0VGltZW91dChkb1NvcnRDYXJkcywgMTAwKTtcbn1cblxuLy8gLS0tLSBQcml2YXRlIGhlbHBlcnMgLS0tLVxuXG4vKipcbiAqIFJlb3JkZXJzIC5pb2MtY2FyZCBlbGVtZW50cyBpbiAjaW9jLWNhcmRzLWdyaWQgYnkgdmVyZGljdCBzZXZlcml0eSAobW9zdFxuICogc2V2ZXJlIGZpcnN0KS4gQ2FsbGVkIGJ5IHNvcnRDYXJkc0J5U2V2ZXJpdHkgdmlhIHNldFRpbWVvdXQgZGVib3VuY2UuXG4gKi9cbmZ1bmN0aW9uIGRvU29ydENhcmRzKCk6IHZvaWQge1xuICBjb25zdCBncmlkID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJpb2MtY2FyZHMtZ3JpZFwiKTtcbiAgaWYgKCFncmlkKSByZXR1cm47XG5cbiAgY29uc3QgY2FyZHMgPSBBcnJheS5mcm9tKGdyaWQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuaW9jLWNhcmRcIikpO1xuICBpZiAoY2FyZHMubGVuZ3RoID09PSAwKSByZXR1cm47XG5cbiAgY2FyZHMuc29ydCgoYSwgYikgPT4ge1xuICAgIGNvbnN0IHZhID0gdmVyZGljdFNldmVyaXR5SW5kZXgoXG4gICAgICBhdHRyKGEsIFwiZGF0YS12ZXJkaWN0XCIsIFwibm9fZGF0YVwiKSBhcyBWZXJkaWN0S2V5XG4gICAgKTtcbiAgICBjb25zdCB2YiA9IHZlcmRpY3RTZXZlcml0eUluZGV4KFxuICAgICAgYXR0cihiLCBcImRhdGEtdmVyZGljdFwiLCBcIm5vX2RhdGFcIikgYXMgVmVyZGljdEtleVxuICAgICk7XG4gICAgLy8gSGlnaGVyIHNldmVyaXR5IGZpcnN0IChkZXNjZW5kaW5nKVxuICAgIHJldHVybiB2YiAtIHZhO1xuICB9KTtcblxuICAvLyBSZW9yZGVyIERPTSBlbGVtZW50cyB3aXRob3V0IHJlbW92aW5nIHRoZW0gZnJvbSB0aGUgZG9jdW1lbnRcbiAgY2FyZHMuZm9yRWFjaCgoY2FyZCkgPT4gZ3JpZC5hcHBlbmRDaGlsZChjYXJkKSk7XG59XG4iLCAiLyoqXG4gKiBGaWx0ZXIgYmFyIG1vZHVsZSBcdTIwMTQgdmVyZGljdC90eXBlL3NlYXJjaCBmaWx0ZXJpbmcgd2l0aCBkYXNoYm9hcmQgYmFkZ2Ugc3luYy5cbiAqXG4gKiBFeHRyYWN0ZWQgZnJvbSBtYWluLmpzIGluaXRGaWx0ZXJCYXIoKSAobGluZXMgNjc3LTc4OCkuXG4gKiBNYW5hZ2VzIGZpbHRlclN0YXRlIGFuZCB3aXJlcyB1cCBhbGwgZmlsdGVyIGV2ZW50IGxpc3RlbmVycy5cbiAqL1xuXG5pbXBvcnQgeyBhdHRyIH0gZnJvbSBcIi4uL3V0aWxzL2RvbVwiO1xuXG4vKipcbiAqIEludGVybmFsIHN0YXRlIGZvciBhbGwgYWN0aXZlIGZpbHRlciBkaW1lbnNpb25zLlxuICogTm90IGV4cG9ydGVkIFx1MjAxNCB0aGlzIGlzIHByaXZhdGUgdG8gdGhlIG1vZHVsZSBjbG9zdXJlIGluc2lkZSBpbml0KCkuXG4gKi9cbmludGVyZmFjZSBGaWx0ZXJTdGF0ZSB7XG4gIHZlcmRpY3Q6IHN0cmluZztcbiAgdHlwZTogc3RyaW5nO1xuICBzZWFyY2g6IHN0cmluZztcbn1cblxuLyoqXG4gKiBJbml0aWFsaXNlIHRoZSBmaWx0ZXIgYmFyLlxuICogV2lyZXMgdmVyZGljdCBidXR0b25zLCB0eXBlIHBpbGxzLCBzZWFyY2ggaW5wdXQsIGFuZCBkYXNoYm9hcmQgYmFkZ2UgY2xpY2tzLlxuICogQWxsIGV2ZW50IGxpc3RlbmVycyBzaGFyZSB0aGUgZmlsdGVyU3RhdGUgY2xvc3VyZS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGluaXQoKTogdm9pZCB7XG4gIGNvbnN0IGZpbHRlclJvb3RFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZmlsdGVyLXJvb3RcIik7XG4gIGlmICghZmlsdGVyUm9vdEVsKSByZXR1cm47IC8vIE5vdCBvbiByZXN1bHRzIHBhZ2VcbiAgY29uc3QgZmlsdGVyUm9vdDogSFRNTEVsZW1lbnQgPSBmaWx0ZXJSb290RWw7XG5cbiAgY29uc3QgZmlsdGVyU3RhdGU6IEZpbHRlclN0YXRlID0ge1xuICAgIHZlcmRpY3Q6IFwiYWxsXCIsXG4gICAgdHlwZTogXCJhbGxcIixcbiAgICBzZWFyY2g6IFwiXCIsXG4gIH07XG5cbiAgLy8gQXBwbHkgZmlsdGVyIHN0YXRlOiBzaG93L2hpZGUgZWFjaCBjYXJkIGFuZCB1cGRhdGUgYWN0aXZlIGJ1dHRvbiBzdHlsZXNcbiAgZnVuY3Rpb24gYXBwbHlGaWx0ZXIoKTogdm9pZCB7XG4gICAgY29uc3QgY2FyZHMgPSBmaWx0ZXJSb290LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmlvYy1jYXJkXCIpO1xuICAgIGNvbnN0IHZlcmRpY3RMQyA9IGZpbHRlclN0YXRlLnZlcmRpY3QudG9Mb3dlckNhc2UoKTtcbiAgICBjb25zdCB0eXBlTEMgPSBmaWx0ZXJTdGF0ZS50eXBlLnRvTG93ZXJDYXNlKCk7XG4gICAgY29uc3Qgc2VhcmNoTEMgPSBmaWx0ZXJTdGF0ZS5zZWFyY2gudG9Mb3dlckNhc2UoKTtcblxuICAgIGNhcmRzLmZvckVhY2goKGNhcmQpID0+IHtcbiAgICAgIGNvbnN0IGNhcmRWZXJkaWN0ID0gYXR0cihjYXJkLCBcImRhdGEtdmVyZGljdFwiKS50b0xvd2VyQ2FzZSgpO1xuICAgICAgY29uc3QgY2FyZFR5cGUgPSBhdHRyKGNhcmQsIFwiZGF0YS1pb2MtdHlwZVwiKS50b0xvd2VyQ2FzZSgpO1xuICAgICAgY29uc3QgY2FyZFZhbHVlID0gYXR0cihjYXJkLCBcImRhdGEtaW9jLXZhbHVlXCIpLnRvTG93ZXJDYXNlKCk7XG5cbiAgICAgIGNvbnN0IHZlcmRpY3RNYXRjaCA9IHZlcmRpY3RMQyA9PT0gXCJhbGxcIiB8fCBjYXJkVmVyZGljdCA9PT0gdmVyZGljdExDO1xuICAgICAgY29uc3QgdHlwZU1hdGNoID0gdHlwZUxDID09PSBcImFsbFwiIHx8IGNhcmRUeXBlID09PSB0eXBlTEM7XG4gICAgICBjb25zdCBzZWFyY2hNYXRjaCA9IHNlYXJjaExDID09PSBcIlwiIHx8IGNhcmRWYWx1ZS5pbmRleE9mKHNlYXJjaExDKSAhPT0gLTE7XG5cbiAgICAgIGNhcmQuc3R5bGUuZGlzcGxheSA9XG4gICAgICAgIHZlcmRpY3RNYXRjaCAmJiB0eXBlTWF0Y2ggJiYgc2VhcmNoTWF0Y2ggPyBcIlwiIDogXCJub25lXCI7XG4gICAgfSk7XG5cbiAgICAvLyBVcGRhdGUgYWN0aXZlIHN0YXRlIG9uIHZlcmRpY3QgYnV0dG9uc1xuICAgIGNvbnN0IHZlcmRpY3RCdG5zID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICAgIFwiW2RhdGEtZmlsdGVyLXZlcmRpY3RdXCJcbiAgICApO1xuICAgIHZlcmRpY3RCdG5zLmZvckVhY2goKGJ0bikgPT4ge1xuICAgICAgY29uc3QgYnRuVmVyZGljdCA9IGF0dHIoYnRuLCBcImRhdGEtZmlsdGVyLXZlcmRpY3RcIik7XG4gICAgICBpZiAoYnRuVmVyZGljdCA9PT0gZmlsdGVyU3RhdGUudmVyZGljdCkge1xuICAgICAgICBidG4uY2xhc3NMaXN0LmFkZChcImZpbHRlci1idG4tLWFjdGl2ZVwiKTtcbiAgICAgIH0gZWxzZSB7XG4gICAgICAgIGJ0bi5jbGFzc0xpc3QucmVtb3ZlKFwiZmlsdGVyLWJ0bi0tYWN0aXZlXCIpO1xuICAgICAgfVxuICAgIH0pO1xuXG4gICAgLy8gVXBkYXRlIGFjdGl2ZSBzdGF0ZSBvbiB0eXBlIHBpbGxzXG4gICAgY29uc3QgdHlwZVBpbGxzID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICAgIFwiW2RhdGEtZmlsdGVyLXR5cGVdXCJcbiAgICApO1xuICAgIHR5cGVQaWxscy5mb3JFYWNoKChwaWxsKSA9PiB7XG4gICAgICBjb25zdCBwaWxsVHlwZSA9IGF0dHIocGlsbCwgXCJkYXRhLWZpbHRlci10eXBlXCIpO1xuICAgICAgaWYgKHBpbGxUeXBlID09PSBmaWx0ZXJTdGF0ZS50eXBlKSB7XG4gICAgICAgIHBpbGwuY2xhc3NMaXN0LmFkZChcImZpbHRlci1waWxsLS1hY3RpdmVcIik7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBwaWxsLmNsYXNzTGlzdC5yZW1vdmUoXCJmaWx0ZXItcGlsbC0tYWN0aXZlXCIpO1xuICAgICAgfVxuICAgIH0pO1xuICB9XG5cbiAgLy8gVmVyZGljdCBidXR0b24gY2xpY2sgaGFuZGxlclxuICBjb25zdCB2ZXJkaWN0QnRucyA9IGZpbHRlclJvb3QucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXG4gICAgXCJbZGF0YS1maWx0ZXItdmVyZGljdF1cIlxuICApO1xuICB2ZXJkaWN0QnRucy5mb3JFYWNoKChidG4pID0+IHtcbiAgICBidG4uYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgIGNvbnN0IHZlcmRpY3QgPSBhdHRyKGJ0biwgXCJkYXRhLWZpbHRlci12ZXJkaWN0XCIpO1xuICAgICAgaWYgKHZlcmRpY3QgPT09IFwiYWxsXCIpIHtcbiAgICAgICAgZmlsdGVyU3RhdGUudmVyZGljdCA9IFwiYWxsXCI7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICAvLyBUb2dnbGU6IGNsaWNraW5nIGFjdGl2ZSB2ZXJkaWN0IHJlc2V0cyB0byAnYWxsJ1xuICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID0gZmlsdGVyU3RhdGUudmVyZGljdCA9PT0gdmVyZGljdCA/IFwiYWxsXCIgOiB2ZXJkaWN0O1xuICAgICAgfVxuICAgICAgYXBwbHlGaWx0ZXIoKTtcbiAgICB9KTtcbiAgfSk7XG5cbiAgLy8gVHlwZSBwaWxsIGNsaWNrIGhhbmRsZXJcbiAgY29uc3QgdHlwZVBpbGxzID0gZmlsdGVyUm9vdC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICBcIltkYXRhLWZpbHRlci10eXBlXVwiXG4gICk7XG4gIHR5cGVQaWxscy5mb3JFYWNoKChwaWxsKSA9PiB7XG4gICAgcGlsbC5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgKCkgPT4ge1xuICAgICAgY29uc3QgdHlwZSA9IGF0dHIocGlsbCwgXCJkYXRhLWZpbHRlci10eXBlXCIpO1xuICAgICAgaWYgKHR5cGUgPT09IFwiYWxsXCIpIHtcbiAgICAgICAgZmlsdGVyU3RhdGUudHlwZSA9IFwiYWxsXCI7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBmaWx0ZXJTdGF0ZS50eXBlID0gZmlsdGVyU3RhdGUudHlwZSA9PT0gdHlwZSA/IFwiYWxsXCIgOiB0eXBlO1xuICAgICAgfVxuICAgICAgYXBwbHlGaWx0ZXIoKTtcbiAgICB9KTtcbiAgfSk7XG5cbiAgLy8gU2VhcmNoIGlucHV0IGhhbmRsZXJcbiAgY29uc3Qgc2VhcmNoSW5wdXQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcbiAgICBcImZpbHRlci1zZWFyY2gtaW5wdXRcIlxuICApIGFzIEhUTUxJbnB1dEVsZW1lbnQgfCBudWxsO1xuICBpZiAoc2VhcmNoSW5wdXQpIHtcbiAgICBzZWFyY2hJbnB1dC5hZGRFdmVudExpc3RlbmVyKFwiaW5wdXRcIiwgKCkgPT4ge1xuICAgICAgZmlsdGVyU3RhdGUuc2VhcmNoID0gc2VhcmNoSW5wdXQudmFsdWU7XG4gICAgICBhcHBseUZpbHRlcigpO1xuICAgIH0pO1xuICB9XG5cbiAgLy8gVmVyZGljdCBkYXNoYm9hcmQgYmFkZ2UgY2xpY2sgaGFuZGxlciAodG9nZ2xlIGZpbHRlciBmcm9tIGRhc2hib2FyZClcbiAgY29uc3QgZGFzaGJvYXJkID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJ2ZXJkaWN0LWRhc2hib2FyZFwiKTtcbiAgaWYgKGRhc2hib2FyZCkge1xuICAgIGNvbnN0IGRhc2hCYWRnZXMgPSBkYXNoYm9hcmQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXG4gICAgICBcIi52ZXJkaWN0LWtwaS1jYXJkW2RhdGEtdmVyZGljdF1cIlxuICAgICk7XG4gICAgZGFzaEJhZGdlcy5mb3JFYWNoKChiYWRnZSkgPT4ge1xuICAgICAgYmFkZ2UuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgICAgY29uc3QgdmVyZGljdCA9IGF0dHIoYmFkZ2UsIFwiZGF0YS12ZXJkaWN0XCIpO1xuICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID1cbiAgICAgICAgICBmaWx0ZXJTdGF0ZS52ZXJkaWN0ID09PSB2ZXJkaWN0ID8gXCJhbGxcIiA6IHZlcmRpY3Q7XG4gICAgICAgIGFwcGx5RmlsdGVyKCk7XG4gICAgICB9KTtcbiAgICB9KTtcbiAgfVxuXG59XG4iLCAiLyoqXG4gKiBFeHBvcnQgbW9kdWxlIC0tIEpTT04gZG93bmxvYWQsIENTViBkb3dubG9hZCwgYW5kIGNvcHktYWxsLUlPQ3MuXG4gKlxuICogQWxsIGV4cG9ydHMgb3BlcmF0ZSBvbiB0aGUgYWNjdW11bGF0ZWQgcmVzdWx0cyBhcnJheSBidWlsdCBkdXJpbmdcbiAqIHRoZSBlbnJpY2htZW50IHBvbGxpbmcgbG9vcC4gTm8gc2VydmVyIHJvdW5kdHJpcCByZXF1aXJlZC5cbiAqL1xuXG5pbXBvcnQgdHlwZSB7IEVucmljaG1lbnRJdGVtIH0gZnJvbSBcIi4uL3R5cGVzL2FwaVwiO1xuaW1wb3J0IHsgd3JpdGVUb0NsaXBib2FyZCB9IGZyb20gXCIuL2NsaXBib2FyZFwiO1xuXG4vLyAtLS0tIEhlbHBlcnMgLS0tLVxuXG5mdW5jdGlvbiBkb3dubG9hZEJsb2IoYmxvYjogQmxvYiwgZmlsZW5hbWU6IHN0cmluZyk6IHZvaWQge1xuICBjb25zdCB1cmwgPSBVUkwuY3JlYXRlT2JqZWN0VVJMKGJsb2IpO1xuICBjb25zdCBhbmNob3IgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiYVwiKTtcbiAgYW5jaG9yLmhyZWYgPSB1cmw7XG4gIGFuY2hvci5kb3dubG9hZCA9IGZpbGVuYW1lO1xuICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKGFuY2hvcik7XG4gIGFuY2hvci5jbGljaygpO1xuICBkb2N1bWVudC5ib2R5LnJlbW92ZUNoaWxkKGFuY2hvcik7XG4gIFVSTC5yZXZva2VPYmplY3RVUkwodXJsKTtcbn1cblxuZnVuY3Rpb24gdGltZXN0YW1wKCk6IHN0cmluZyB7XG4gIHJldHVybiBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCkucmVwbGFjZSgvWzouXS9nLCBcIi1cIikuc2xpY2UoMCwgMTkpO1xufVxuXG5mdW5jdGlvbiBjc3ZFc2NhcGUodmFsdWU6IHN0cmluZyk6IHN0cmluZyB7XG4gIGlmICh2YWx1ZS5pbmRleE9mKFwiLFwiKSAhPT0gLTEgfHwgdmFsdWUuaW5kZXhPZignXCInKSAhPT0gLTEgfHwgdmFsdWUuaW5kZXhPZihcIlxcblwiKSAhPT0gLTEpIHtcbiAgICByZXR1cm4gJ1wiJyArIHZhbHVlLnJlcGxhY2UoL1wiL2csICdcIlwiJykgKyAnXCInO1xuICB9XG4gIHJldHVybiB2YWx1ZTtcbn1cblxuZnVuY3Rpb24gcmF3U3RhdEZpZWxkKHJhdzogUmVjb3JkPHN0cmluZywgdW5rbm93bj4gfCB1bmRlZmluZWQsIGtleTogc3RyaW5nKTogc3RyaW5nIHtcbiAgaWYgKCFyYXcpIHJldHVybiBcIlwiO1xuICBjb25zdCB2YWwgPSByYXdba2V5XTtcbiAgaWYgKHZhbCA9PT0gdW5kZWZpbmVkIHx8IHZhbCA9PT0gbnVsbCkgcmV0dXJuIFwiXCI7XG4gIGlmIChBcnJheS5pc0FycmF5KHZhbCkpIHJldHVybiB2YWwuam9pbihcIjsgXCIpO1xuICByZXR1cm4gU3RyaW5nKHZhbCk7XG59XG5cbi8vIC0tLS0gUHVibGljIEFQSSAtLS0tXG5cbmNvbnN0IENTVl9DT0xVTU5TID0gW1xuICBcImlvY192YWx1ZVwiLCBcImlvY190eXBlXCIsIFwicHJvdmlkZXJcIiwgXCJ2ZXJkaWN0XCIsXG4gIFwiZGV0ZWN0aW9uX2NvdW50XCIsIFwidG90YWxfZW5naW5lc1wiLCBcInNjYW5fZGF0ZVwiLFxuICBcInNpZ25hdHVyZVwiLCBcIm1hbHdhcmVfcHJpbnRhYmxlXCIsIFwidGhyZWF0X3R5cGVcIixcbiAgXCJjb3VudHJ5Q29kZVwiLCBcImlzcFwiLCBcInRvcF9kZXRlY3Rpb25zXCIsXG5dIGFzIGNvbnN0O1xuXG5leHBvcnQgZnVuY3Rpb24gZXhwb3J0SlNPTihyZXN1bHRzOiBFbnJpY2htZW50SXRlbVtdKTogdm9pZCB7XG4gIGNvbnN0IGpzb24gPSBKU09OLnN0cmluZ2lmeShyZXN1bHRzLCBudWxsLCAyKTtcbiAgY29uc3QgYmxvYiA9IG5ldyBCbG9iKFtqc29uXSwgeyB0eXBlOiBcImFwcGxpY2F0aW9uL2pzb25cIiB9KTtcbiAgZG93bmxvYWRCbG9iKGJsb2IsIFwic2VudGluZWx4LWV4cG9ydC1cIiArIHRpbWVzdGFtcCgpICsgXCIuanNvblwiKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGV4cG9ydENTVihyZXN1bHRzOiBFbnJpY2htZW50SXRlbVtdKTogdm9pZCB7XG4gIGNvbnN0IGhlYWRlciA9IENTVl9DT0xVTU5TLmpvaW4oXCIsXCIpICsgXCJcXG5cIjtcbiAgY29uc3Qgcm93czogc3RyaW5nW10gPSBbXTtcblxuICBmb3IgKGNvbnN0IHIgb2YgcmVzdWx0cykge1xuICAgIGlmIChyLnR5cGUgIT09IFwicmVzdWx0XCIpIGNvbnRpbnVlO1xuICAgIGNvbnN0IHJhdyA9IHIucmF3X3N0YXRzO1xuICAgIGNvbnN0IHJvdyA9IFtcbiAgICAgIGNzdkVzY2FwZShyLmlvY192YWx1ZSksXG4gICAgICBjc3ZFc2NhcGUoci5pb2NfdHlwZSksXG4gICAgICBjc3ZFc2NhcGUoci5wcm92aWRlciksXG4gICAgICBjc3ZFc2NhcGUoci52ZXJkaWN0KSxcbiAgICAgIFN0cmluZyhyLmRldGVjdGlvbl9jb3VudCksXG4gICAgICBTdHJpbmcoci50b3RhbF9lbmdpbmVzKSxcbiAgICAgIGNzdkVzY2FwZShyLnNjYW5fZGF0ZSA/PyBcIlwiKSxcbiAgICAgIGNzdkVzY2FwZShyYXdTdGF0RmllbGQocmF3LCBcInNpZ25hdHVyZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJtYWx3YXJlX3ByaW50YWJsZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJ0aHJlYXRfdHlwZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJjb3VudHJ5Q29kZVwiKSksXG4gICAgICBjc3ZFc2NhcGUocmF3U3RhdEZpZWxkKHJhdywgXCJpc3BcIikpLFxuICAgICAgY3N2RXNjYXBlKHJhd1N0YXRGaWVsZChyYXcsIFwidG9wX2RldGVjdGlvbnNcIikpLFxuICAgIF07XG4gICAgcm93cy5wdXNoKHJvdy5qb2luKFwiLFwiKSk7XG4gIH1cblxuICBjb25zdCBjc3YgPSBoZWFkZXIgKyByb3dzLmpvaW4oXCJcXG5cIik7XG4gIGNvbnN0IGJsb2IgPSBuZXcgQmxvYihbY3N2XSwgeyB0eXBlOiBcInRleHQvY3N2XCIgfSk7XG4gIGRvd25sb2FkQmxvYihibG9iLCBcInNlbnRpbmVseC1leHBvcnQtXCIgKyB0aW1lc3RhbXAoKSArIFwiLmNzdlwiKTtcbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGNvcHlBbGxJT0NzKGJ0bjogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgY29uc3QgY2FyZHMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcIi5pb2MtY2FyZFtkYXRhLWlvYy12YWx1ZV1cIik7XG4gIGNvbnN0IHNlZW4gPSBuZXcgU2V0PHN0cmluZz4oKTtcbiAgY29uc3QgdmFsdWVzOiBzdHJpbmdbXSA9IFtdO1xuXG4gIGNhcmRzLmZvckVhY2goKGNhcmQpID0+IHtcbiAgICBjb25zdCB2YWwgPSBjYXJkLmdldEF0dHJpYnV0ZShcImRhdGEtaW9jLXZhbHVlXCIpO1xuICAgIGlmICh2YWwgJiYgIXNlZW4uaGFzKHZhbCkpIHtcbiAgICAgIHNlZW4uYWRkKHZhbCk7XG4gICAgICB2YWx1ZXMucHVzaCh2YWwpO1xuICAgIH1cbiAgfSk7XG5cbiAgd3JpdGVUb0NsaXBib2FyZCh2YWx1ZXMuam9pbihcIlxcblwiKSwgYnRuKTtcbn1cbiIsICIvKipcbiAqIFB1cmUgdmVyZGljdCBjb21wdXRhdGlvbiBmdW5jdGlvbnMgXHUyMDE0IG5vIERPTSBhY2Nlc3MsIG5vIHNpZGUgZWZmZWN0cy5cbiAqXG4gKiBFeHRyYWN0ZWQgZnJvbSBlbnJpY2htZW50LnRzIChQaGFzZSAyKS4gVGhlc2UgZnVuY3Rpb25zIHRha2UgVmVyZGljdEVudHJ5W11cbiAqIGFycmF5cyBhbmQgcmV0dXJuIGNvbXB1dGVkIHJlc3VsdHMuIFRoZXkgYXJlIHRoZSBzaGFyZWQgY29tcHV0YXRpb24gbGF5ZXJcbiAqIHVzZWQgYnkgYm90aCByb3ctZmFjdG9yeS50cyAoc3VtbWFyeSByb3cgcmVuZGVyaW5nKSBhbmQgZW5yaWNobWVudC50c1xuICogKG9yY2hlc3RyYXRvciB2ZXJkaWN0IHRyYWNraW5nKS5cbiAqL1xuXG5pbXBvcnQgdHlwZSB7IFZlcmRpY3RLZXkgfSBmcm9tIFwiLi4vdHlwZXMvaW9jXCI7XG5pbXBvcnQgeyB2ZXJkaWN0U2V2ZXJpdHlJbmRleCB9IGZyb20gXCIuLi90eXBlcy9pb2NcIjtcblxuLyoqXG4gKiBQZXItcHJvdmlkZXIgdmVyZGljdCByZWNvcmQgYWNjdW11bGF0ZWQgZHVyaW5nIHRoZSBwb2xsaW5nIGxvb3AuXG4gKiBVc2VkIGZvciB3b3JzdC12ZXJkaWN0IGNvbXB1dGF0aW9uIGFjcm9zcyBhbGwgcHJvdmlkZXJzIGZvciBhbiBJT0MuXG4gKi9cbmV4cG9ydCBpbnRlcmZhY2UgVmVyZGljdEVudHJ5IHtcbiAgcHJvdmlkZXI6IHN0cmluZztcbiAgdmVyZGljdDogVmVyZGljdEtleTtcbiAgc3VtbWFyeVRleHQ6IHN0cmluZztcbiAgZGV0ZWN0aW9uQ291bnQ6IG51bWJlcjsgICAvLyBmcm9tIHJlc3VsdC5kZXRlY3Rpb25fY291bnQgKDAgZm9yIGVycm9ycylcbiAgdG90YWxFbmdpbmVzOiBudW1iZXI7ICAgICAvLyBmcm9tIHJlc3VsdC50b3RhbF9lbmdpbmVzICgwIGZvciBlcnJvcnMpXG4gIHN0YXRUZXh0OiBzdHJpbmc7ICAgICAgICAgLy8ga2V5IHN0YXQgc3RyaW5nIGZvciBkaXNwbGF5IChlLmcuLCBcIjQ1LzcyIGVuZ2luZXNcIilcbn1cblxuLyoqXG4gKiBDb21wdXRlIHRoZSB3b3JzdCAoaGlnaGVzdCBzZXZlcml0eSkgdmVyZGljdCBmcm9tIGEgbGlzdCBvZiBWZXJkaWN0RW50cnkgcmVjb3Jkcy5cbiAqXG4gKiBrbm93bl9nb29kIGZyb20gYW55IHByb3ZpZGVyIG92ZXJyaWRlcyBhbGwgb3RoZXIgdmVyZGljdHMgYXQgc3VtbWFyeSBsZXZlbC5cbiAqIFRoaXMgaXMgYW4gaW50ZW50aW9uYWwgZGVzaWduIGRlY2lzaW9uOiBrbm93bl9nb29kIChlLmcuIE5TUkwgbWF0Y2gpIG1lYW5zXG4gKiB0aGUgSU9DIGlzIGEgcmVjb2duaXplZCBzYWZlIGFydGlmYWN0IHJlZ2FyZGxlc3Mgb2Ygb3RoZXIgc2lnbmFscy5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgY29tcHV0ZVdvcnN0VmVyZGljdCgpIChsaW5lcyA1NDItNTUxKS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNvbXB1dGVXb3JzdFZlcmRpY3QoZW50cmllczogVmVyZGljdEVudHJ5W10pOiBWZXJkaWN0S2V5IHtcbiAgLy8ga25vd25fZ29vZCBmcm9tIGFueSBwcm92aWRlciBvdmVycmlkZXMgZXZlcnl0aGluZyBhdCBzdW1tYXJ5IGxldmVsXG4gIGlmIChlbnRyaWVzLnNvbWUoKGUpID0+IGUudmVyZGljdCA9PT0gXCJrbm93bl9nb29kXCIpKSB7XG4gICAgcmV0dXJuIFwia25vd25fZ29vZFwiO1xuICB9XG4gIGNvbnN0IHdvcnN0ID0gZmluZFdvcnN0RW50cnkoZW50cmllcyk7XG4gIHJldHVybiB3b3JzdCA/IHdvcnN0LnZlcmRpY3QgOiBcIm5vX2RhdGFcIjtcbn1cblxuLyoqXG4gKiBDb21wdXRlIGNvbnNlbnN1czogY291bnQgZmxhZ2dlZCAobWFsaWNpb3VzL3N1c3BpY2lvdXMpIGFuZCByZXNwb25kZWRcbiAqIChtYWxpY2lvdXMgKyBzdXNwaWNpb3VzICsgY2xlYW4pIHByb3ZpZGVycy5cbiAqIFBlciBkZXNpZ246IG5vX2RhdGEgYW5kIGVycm9yIGRvIE5PVCBjb3VudCBhcyB2b3Rlcy5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGNvbXB1dGVDb25zZW5zdXMoZW50cmllczogVmVyZGljdEVudHJ5W10pOiB7IGZsYWdnZWQ6IG51bWJlcjsgcmVzcG9uZGVkOiBudW1iZXIgfSB7XG4gIGxldCBmbGFnZ2VkID0gMDtcbiAgbGV0IHJlc3BvbmRlZCA9IDA7XG4gIGZvciAoY29uc3QgZW50cnkgb2YgZW50cmllcykge1xuICAgIGlmIChlbnRyeS52ZXJkaWN0ID09PSBcIm1hbGljaW91c1wiIHx8IGVudHJ5LnZlcmRpY3QgPT09IFwic3VzcGljaW91c1wiKSB7XG4gICAgICBmbGFnZ2VkKys7XG4gICAgICByZXNwb25kZWQrKztcbiAgICB9IGVsc2UgaWYgKGVudHJ5LnZlcmRpY3QgPT09IFwiY2xlYW5cIikge1xuICAgICAgcmVzcG9uZGVkKys7XG4gICAgfVxuICAgIC8vIGVycm9yIGFuZCBub19kYXRhIGRvIE5PVCBjb3VudFxuICB9XG4gIHJldHVybiB7IGZsYWdnZWQsIHJlc3BvbmRlZCB9O1xufVxuXG4vKipcbiAqIFJldHVybiB0aGUgQ1NTIG1vZGlmaWVyIGNsYXNzIGZvciB0aGUgY29uc2Vuc3VzIGJhZGdlIGJhc2VkIG9uIGZsYWdnZWQgY291bnQuXG4gKiAwIGZsYWdnZWQgXHUyMTkyIGdyZWVuLCAxLTIgXHUyMTkyIHllbGxvdywgMysgXHUyMTkyIHJlZC5cbiAqXG4gKiBQaGFzZSAzOiBObyBsb25nZXIgY29uc3VtZWQgYnkgcm93LWZhY3RvcnkgKHJlcGxhY2VkIGJ5IHZlcmRpY3QgbWljcm8tYmFyKS5cbiAqIEtlcHQgZXhwb3J0ZWQgZm9yIEFQSSBzdGFiaWxpdHkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjb25zZW5zdXNCYWRnZUNsYXNzKGZsYWdnZWQ6IG51bWJlcik6IHN0cmluZyB7XG4gIGlmIChmbGFnZ2VkID09PSAwKSByZXR1cm4gXCJjb25zZW5zdXMtYmFkZ2UtLWdyZWVuXCI7XG4gIGlmIChmbGFnZ2VkIDw9IDIpIHJldHVybiBcImNvbnNlbnN1cy1iYWRnZS0teWVsbG93XCI7XG4gIHJldHVybiBcImNvbnNlbnN1cy1iYWRnZS0tcmVkXCI7XG59XG5cbi8qKlxuICogQ29tcHV0ZSBhdHRyaWJ1dGlvbjogZmluZCB0aGUgXCJtb3N0IGRldGFpbGVkXCIgcHJvdmlkZXIgdG8gc2hvdyBpbiBzdW1tYXJ5LlxuICogSGV1cmlzdGljOiBoaWdoZXN0IHRvdGFsRW5naW5lcyB3aW5zLiBUaWVzIGJyb2tlbiBieSB2ZXJkaWN0IHNldmVyaXR5IGRlc2NlbmRpbmcuXG4gKiBQcm92aWRlcnMgd2l0aCBub19kYXRhIG9yIGVycm9yIGFyZSBleGNsdWRlZCBhcyBjYW5kaWRhdGVzLlxuICovXG5leHBvcnQgZnVuY3Rpb24gY29tcHV0ZUF0dHJpYnV0aW9uKGVudHJpZXM6IFZlcmRpY3RFbnRyeVtdKTogeyBwcm92aWRlcjogc3RyaW5nOyB0ZXh0OiBzdHJpbmcgfSB7XG4gIC8vIE9ubHkgY2FuZGlkYXRlcyB3aXRoIGFjdHVhbCBkYXRhIChub3Qgbm9fZGF0YSBvciBlcnJvcilcbiAgY29uc3QgY2FuZGlkYXRlcyA9IGVudHJpZXMuZmlsdGVyKFxuICAgIChlKSA9PiBlLnZlcmRpY3QgIT09IFwibm9fZGF0YVwiICYmIGUudmVyZGljdCAhPT0gXCJlcnJvclwiXG4gICk7XG5cbiAgaWYgKGNhbmRpZGF0ZXMubGVuZ3RoID09PSAwKSB7XG4gICAgcmV0dXJuIHsgcHJvdmlkZXI6IFwiXCIsIHRleHQ6IFwiTm8gcHJvdmlkZXJzIHJldHVybmVkIGRhdGEgZm9yIHRoaXMgSU9DXCIgfTtcbiAgfVxuXG4gIC8vIFNvcnQ6IGhpZ2hlc3QgdG90YWxFbmdpbmVzIGZpcnN0LiBUaWVzIGJyb2tlbiBieSBzZXZlcml0eSBkZXNjZW5kaW5nLlxuICBjb25zdCBzb3J0ZWQgPSBbLi4uY2FuZGlkYXRlc10uc29ydCgoYSwgYikgPT4ge1xuICAgIGlmIChiLnRvdGFsRW5naW5lcyAhPT0gYS50b3RhbEVuZ2luZXMpIHJldHVybiBiLnRvdGFsRW5naW5lcyAtIGEudG90YWxFbmdpbmVzO1xuICAgIHJldHVybiB2ZXJkaWN0U2V2ZXJpdHlJbmRleChiLnZlcmRpY3QpIC0gdmVyZGljdFNldmVyaXR5SW5kZXgoYS52ZXJkaWN0KTtcbiAgfSk7XG5cbiAgY29uc3QgYmVzdCA9IHNvcnRlZFswXTtcbiAgaWYgKCFiZXN0KSByZXR1cm4geyBwcm92aWRlcjogXCJcIiwgdGV4dDogXCJObyBwcm92aWRlcnMgcmV0dXJuZWQgZGF0YSBmb3IgdGhpcyBJT0NcIiB9O1xuXG4gIHJldHVybiB7IHByb3ZpZGVyOiBiZXN0LnByb3ZpZGVyLCB0ZXh0OiBiZXN0LnByb3ZpZGVyICsgXCI6IFwiICsgYmVzdC5zdGF0VGV4dCB9O1xufVxuXG4vKipcbiAqIEZpbmQgdGhlIHdvcnN0IChoaWdoZXN0IHNldmVyaXR5KSBWZXJkaWN0RW50cnkgZnJvbSBhIGxpc3QuXG4gKiBSZXR1cm5zIHVuZGVmaW5lZCBpZiB0aGUgbGlzdCBpcyBlbXB0eS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGZpbmRXb3JzdEVudHJ5KGVudHJpZXM6IFZlcmRpY3RFbnRyeVtdKTogVmVyZGljdEVudHJ5IHwgdW5kZWZpbmVkIHtcbiAgY29uc3QgZmlyc3QgPSBlbnRyaWVzWzBdO1xuICBpZiAoIWZpcnN0KSByZXR1cm4gdW5kZWZpbmVkO1xuXG4gIGxldCB3b3JzdCA9IGZpcnN0O1xuICBmb3IgKGxldCBpID0gMTsgaSA8IGVudHJpZXMubGVuZ3RoOyBpKyspIHtcbiAgICBjb25zdCBjdXJyZW50ID0gZW50cmllc1tpXTtcbiAgICBpZiAoIWN1cnJlbnQpIGNvbnRpbnVlO1xuICAgIGlmICh2ZXJkaWN0U2V2ZXJpdHlJbmRleChjdXJyZW50LnZlcmRpY3QpID4gdmVyZGljdFNldmVyaXR5SW5kZXgod29yc3QudmVyZGljdCkpIHtcbiAgICAgIHdvcnN0ID0gY3VycmVudDtcbiAgICB9XG4gIH1cbiAgcmV0dXJuIHdvcnN0O1xufVxuIiwgIi8qKlxuICogRE9NIHJvdyBjb25zdHJ1Y3Rpb24gZm9yIGVucmljaG1lbnQgcmVzdWx0IGRpc3BsYXkuXG4gKlxuICogRXh0cmFjdGVkIGZyb20gZW5yaWNobWVudC50cyAoUGhhc2UgMikuIE93bnMgYWxsIERPTSBlbGVtZW50IGNyZWF0aW9uXG4gKiBmb3IgcHJvdmlkZXIgcm93cywgc3VtbWFyeSByb3dzLCBhbmQgY29udGV4dCBmaWVsZHMuIFRoZSBDT05URVhUX1BST1ZJREVSU1xuICogc2V0IGxpdmVzIGhlcmUgYXMgaXQgY29udHJvbHMgcm93IHJlbmRlcmluZyBkaXNwYXRjaC5cbiAqXG4gKiBEZXBlbmRzIG9uOlxuICogICAtIHZlcmRpY3QtY29tcHV0ZS50cyBmb3IgVmVyZGljdEVudHJ5IHR5cGUgYW5kIGNvbXB1dGF0aW9uIGZ1bmN0aW9uc1xuICogICAtIHR5cGVzL2FwaS50cyAgICAgICBmb3IgRW5yaWNobWVudFJlc3VsdEl0ZW0sIEVucmljaG1lbnRJdGVtXG4gKiAgIC0gdHlwZXMvaW9jLnRzICAgICAgIGZvciBWZXJkaWN0S2V5LCBWRVJESUNUX0xBQkVMU1xuICovXG5cbmltcG9ydCB0eXBlIHsgRW5yaWNobWVudEl0ZW0sIEVucmljaG1lbnRSZXN1bHRJdGVtIH0gZnJvbSBcIi4uL3R5cGVzL2FwaVwiO1xuaW1wb3J0IHR5cGUgeyBWZXJkaWN0S2V5IH0gZnJvbSBcIi4uL3R5cGVzL2lvY1wiO1xuaW1wb3J0IHsgVkVSRElDVF9MQUJFTFMgfSBmcm9tIFwiLi4vdHlwZXMvaW9jXCI7XG5pbXBvcnQgdHlwZSB7IFZlcmRpY3RFbnRyeSB9IGZyb20gXCIuL3ZlcmRpY3QtY29tcHV0ZVwiO1xuaW1wb3J0IHsgY29tcHV0ZVdvcnN0VmVyZGljdCwgY29tcHV0ZUF0dHJpYnV0aW9uIH0gZnJvbSBcIi4vdmVyZGljdC1jb21wdXRlXCI7XG5cbi8vIC0tLS0gUHJpdmF0ZSBoZWxwZXJzIC0tLS1cblxuLyoqXG4gKiBDb21wdXRlIHZlcmRpY3QgY2F0ZWdvcnkgY291bnRzIGZyb20gZW50cmllcyBmb3IgbWljcm8tYmFyIHJlbmRlcmluZy5cbiAqL1xuZnVuY3Rpb24gY29tcHV0ZVZlcmRpY3RDb3VudHMoZW50cmllczogVmVyZGljdEVudHJ5W10pOiB7XG4gIG1hbGljaW91czogbnVtYmVyOyBzdXNwaWNpb3VzOiBudW1iZXI7IGNsZWFuOiBudW1iZXI7IG5vRGF0YTogbnVtYmVyOyB0b3RhbDogbnVtYmVyO1xufSB7XG4gIGxldCBtYWxpY2lvdXMgPSAwLCBzdXNwaWNpb3VzID0gMCwgY2xlYW4gPSAwLCBub0RhdGEgPSAwO1xuICBmb3IgKGNvbnN0IGUgb2YgZW50cmllcykge1xuICAgIGlmIChlLnZlcmRpY3QgPT09IFwibWFsaWNpb3VzXCIpIG1hbGljaW91cysrO1xuICAgIGVsc2UgaWYgKGUudmVyZGljdCA9PT0gXCJzdXNwaWNpb3VzXCIpIHN1c3BpY2lvdXMrKztcbiAgICBlbHNlIGlmIChlLnZlcmRpY3QgPT09IFwiY2xlYW5cIikgY2xlYW4rKztcbiAgICBlbHNlIG5vRGF0YSsrO1xuICB9XG4gIHJldHVybiB7IG1hbGljaW91cywgc3VzcGljaW91cywgY2xlYW4sIG5vRGF0YSwgdG90YWw6IGVudHJpZXMubGVuZ3RoIH07XG59XG5cbi8qKlxuICogRm9ybWF0IGFuIElTTyA4NjAxIGRhdGUgc3RyaW5nIGZvciBkaXNwbGF5LlxuICogUmV0dXJucyBcIlwiIGZvciBudWxsIGlucHV0IChzY2FuX2RhdGUgY2FuIGJlIG51bGwgcGVyIEFQSSBjb250cmFjdCkuXG4gKiBTb3VyY2U6IG1haW4uanMgZm9ybWF0RGF0ZSgpIChsaW5lcyA1ODEtNTg4KS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGZvcm1hdERhdGUoaXNvOiBzdHJpbmcgfCBudWxsKTogc3RyaW5nIHtcbiAgaWYgKCFpc28pIHJldHVybiBcIlwiO1xuICB0cnkge1xuICAgIHJldHVybiBuZXcgRGF0ZShpc28pLnRvTG9jYWxlRGF0ZVN0cmluZygpO1xuICB9IGNhdGNoIHtcbiAgICByZXR1cm4gaXNvO1xuICB9XG59XG5cbi8qKlxuICogRm9ybWF0IGFuIElTTyA4NjAxIHRpbWVzdGFtcCBhcyBhIHJlbGF0aXZlIHRpbWUgc3RyaW5nIChlLmcuIFwiMmggYWdvXCIpLlxuICogRmFsbHMgYmFjayB0byB0aGUgcmF3IElTTyBzdHJpbmcgaWYgcGFyc2luZyBmYWlscy5cbiAqL1xuZnVuY3Rpb24gZm9ybWF0UmVsYXRpdmVUaW1lKGlzbzogc3RyaW5nKTogc3RyaW5nIHtcbiAgdHJ5IHtcbiAgICBjb25zdCBkaWZmTXMgPSBEYXRlLm5vdygpIC0gbmV3IERhdGUoaXNvKS5nZXRUaW1lKCk7XG4gICAgY29uc3QgZGlmZk1pbiA9IE1hdGguZmxvb3IoZGlmZk1zIC8gNjAwMDApO1xuICAgIGlmIChkaWZmTWluIDwgMSkgcmV0dXJuIFwianVzdCBub3dcIjtcbiAgICBpZiAoZGlmZk1pbiA8IDYwKSByZXR1cm4gZGlmZk1pbiArIFwibSBhZ29cIjtcbiAgICBjb25zdCBkaWZmSHIgPSBNYXRoLmZsb29yKGRpZmZNaW4gLyA2MCk7XG4gICAgaWYgKGRpZmZIciA8IDI0KSByZXR1cm4gZGlmZkhyICsgXCJoIGFnb1wiO1xuICAgIGNvbnN0IGRpZmZEYXkgPSBNYXRoLmZsb29yKGRpZmZIciAvIDI0KTtcbiAgICByZXR1cm4gZGlmZkRheSArIFwiZCBhZ29cIjtcbiAgfSBjYXRjaCB7XG4gICAgcmV0dXJuIGlzbztcbiAgfVxufVxuXG4vLyAtLS0tIFByb3ZpZGVyIGNvbnRleHQgZmllbGQgZGVmaW5pdGlvbnMgLS0tLVxuXG4vKiogTWFwcGluZyBvZiBwcm92aWRlciBuYW1lIC0+IGZpZWxkcyB0byBleHRyYWN0IGZyb20gcmF3X3N0YXRzLiAqL1xuaW50ZXJmYWNlIENvbnRleHRGaWVsZERlZiB7XG4gIGtleTogc3RyaW5nO1xuICBsYWJlbDogc3RyaW5nO1xuICB0eXBlOiBcInRleHRcIiB8IFwidGFnc1wiO1xufVxuXG5jb25zdCBQUk9WSURFUl9DT05URVhUX0ZJRUxEUzogUmVjb3JkPHN0cmluZywgQ29udGV4dEZpZWxkRGVmW10+ID0ge1xuICBWaXJ1c1RvdGFsOiBbXG4gICAgeyBrZXk6IFwidG9wX2RldGVjdGlvbnNcIiwgbGFiZWw6IFwiRGV0ZWN0aW9uc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcInJlcHV0YXRpb25cIiwgbGFiZWw6IFwiUmVwdXRhdGlvblwiLCB0eXBlOiBcInRleHRcIiB9LFxuICBdLFxuICBNYWx3YXJlQmF6YWFyOiBbXG4gICAgeyBrZXk6IFwic2lnbmF0dXJlXCIsIGxhYmVsOiBcIlNpZ25hdHVyZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInRhZ3NcIiwgbGFiZWw6IFwiVGFnc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcImZpbGVfdHlwZVwiLCBsYWJlbDogXCJGaWxlIHR5cGVcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJmaXJzdF9zZWVuXCIsIGxhYmVsOiBcIkZpcnN0IHNlZW5cIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJsYXN0X3NlZW5cIiwgbGFiZWw6IFwiTGFzdCBzZWVuXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIFRocmVhdEZveDogW1xuICAgIHsga2V5OiBcIm1hbHdhcmVfcHJpbnRhYmxlXCIsIGxhYmVsOiBcIk1hbHdhcmVcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJ0aHJlYXRfdHlwZVwiLCBsYWJlbDogXCJUaHJlYXQgdHlwZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImNvbmZpZGVuY2VfbGV2ZWxcIiwgbGFiZWw6IFwiQ29uZmlkZW5jZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICBdLFxuICBBYnVzZUlQREI6IFtcbiAgICB7IGtleTogXCJhYnVzZUNvbmZpZGVuY2VTY29yZVwiLCBsYWJlbDogXCJDb25maWRlbmNlXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwidG90YWxSZXBvcnRzXCIsIGxhYmVsOiBcIlJlcG9ydHNcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJjb3VudHJ5Q29kZVwiLCBsYWJlbDogXCJDb3VudHJ5XCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwiaXNwXCIsIGxhYmVsOiBcIklTUFwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInVzYWdlVHlwZVwiLCBsYWJlbDogXCJVc2FnZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICBdLFxuICBcIlNob2RhbiBJbnRlcm5ldERCXCI6IFtcbiAgICB7IGtleTogXCJwb3J0c1wiLCBsYWJlbDogXCJQb3J0c1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcInZ1bG5zXCIsIGxhYmVsOiBcIlZ1bG5zXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwiaG9zdG5hbWVzXCIsIGxhYmVsOiBcIkhvc3RuYW1lc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcImNwZXNcIiwgbGFiZWw6IFwiQ1BFc1wiLCB0eXBlOiBcInRhZ3NcIiB9LCAgICAgIC8vIEVQUk9WLTAxXG4gICAgeyBrZXk6IFwidGFnc1wiLCBsYWJlbDogXCJUYWdzXCIsIHR5cGU6IFwidGFnc1wiIH0sICAgICAgLy8gRVBST1YtMDFcbiAgXSxcbiAgXCJDSVJDTCBIYXNobG9va3VwXCI6IFtcbiAgICB7IGtleTogXCJmaWxlX25hbWVcIiwgbGFiZWw6IFwiRmlsZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInNvdXJjZVwiLCBsYWJlbDogXCJTb3VyY2VcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgXSxcbiAgXCJHcmV5Tm9pc2UgQ29tbXVuaXR5XCI6IFtcbiAgICB7IGtleTogXCJub2lzZVwiLCBsYWJlbDogXCJOb2lzZVwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInJpb3RcIiwgbGFiZWw6IFwiUklPVFwiLCB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcImNsYXNzaWZpY2F0aW9uXCIsIGxhYmVsOiBcIkNsYXNzaWZpY2F0aW9uXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIFVSTGhhdXM6IFtcbiAgICB7IGtleTogXCJ0aHJlYXRcIiwgbGFiZWw6IFwiVGhyZWF0XCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwidXJsX3N0YXR1c1wiLCBsYWJlbDogXCJTdGF0dXNcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJ0YWdzXCIsIGxhYmVsOiBcIlRhZ3NcIiwgdHlwZTogXCJ0YWdzXCIgfSxcbiAgXSxcbiAgXCJPVFggQWxpZW5WYXVsdFwiOiBbXG4gICAgeyBrZXk6IFwicHVsc2VfY291bnRcIiwgbGFiZWw6IFwiUHVsc2VzXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwicmVwdXRhdGlvblwiLCBsYWJlbDogXCJSZXB1dGF0aW9uXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG4gIFwiSVAgQ29udGV4dFwiOiBbXG4gICAgeyBrZXk6IFwiZ2VvXCIsIGxhYmVsOiBcIkxvY2F0aW9uXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwicmV2ZXJzZVwiLCBsYWJlbDogXCJQVFJcIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJmbGFnc1wiLCBsYWJlbDogXCJGbGFnc1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICBdLFxuICBcIkROUyBSZWNvcmRzXCI6IFtcbiAgICB7IGtleTogXCJhXCIsICAgbGFiZWw6IFwiQVwiLCAgIHR5cGU6IFwidGFnc1wiIH0sXG4gICAgeyBrZXk6IFwibXhcIiwgIGxhYmVsOiBcIk1YXCIsICB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcIm5zXCIsICBsYWJlbDogXCJOU1wiLCAgdHlwZTogXCJ0YWdzXCIgfSxcbiAgICB7IGtleTogXCJ0eHRcIiwgbGFiZWw6IFwiVFhUXCIsIHR5cGU6IFwidGFnc1wiIH0sXG4gIF0sXG4gIFwiQ2VydCBIaXN0b3J5XCI6IFtcbiAgICB7IGtleTogXCJjZXJ0X2NvdW50XCIsIGxhYmVsOiBcIkNlcnRzXCIsICAgICAgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJlYXJsaWVzdFwiLCAgIGxhYmVsOiBcIkZpcnN0IHNlZW5cIiwgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJsYXRlc3RcIiwgICAgIGxhYmVsOiBcIkxhdGVzdFwiLCAgICAgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJzdWJkb21haW5zXCIsIGxhYmVsOiBcIlN1YmRvbWFpbnNcIiwgdHlwZTogXCJ0YWdzXCIgfSxcbiAgXSxcbiAgVGhyZWF0TWluZXI6IFtcbiAgICB7IGtleTogXCJwYXNzaXZlX2Ruc1wiLCBsYWJlbDogXCJQYXNzaXZlIEROU1wiLCB0eXBlOiBcInRhZ3NcIiB9LFxuICAgIHsga2V5OiBcInNhbXBsZXNcIiwgICAgIGxhYmVsOiBcIlNhbXBsZXNcIiwgICAgIHR5cGU6IFwidGFnc1wiIH0sXG4gIF0sXG4gIFwiQVNOIEludGVsXCI6IFtcbiAgICB7IGtleTogXCJhc25cIiwgICAgICAgbGFiZWw6IFwiQVNOXCIsICAgICAgIHR5cGU6IFwidGV4dFwiIH0sXG4gICAgeyBrZXk6IFwicHJlZml4XCIsICAgIGxhYmVsOiBcIlByZWZpeFwiLCAgICB0eXBlOiBcInRleHRcIiB9LFxuICAgIHsga2V5OiBcInJpclwiLCAgICAgICBsYWJlbDogXCJSSVJcIiwgICAgICAgdHlwZTogXCJ0ZXh0XCIgfSxcbiAgICB7IGtleTogXCJhbGxvY2F0ZWRcIiwgbGFiZWw6IFwiQWxsb2NhdGVkXCIsIHR5cGU6IFwidGV4dFwiIH0sXG4gIF0sXG59O1xuXG4vKipcbiAqIFByb3ZpZGVycyB0aGF0IHVzZSB0aGUgY29udGV4dCByb3cgcmVuZGVyaW5nIHBhdGggKG5vIHZlcmRpY3QgYmFkZ2UsIHBpbm5lZCB0byB0b3ApLlxuICogRXh0ZW5kIHRoaXMgc2V0IHdoZW4gYWRkaW5nIG5ldyBjb250ZXh0LW9ubHkgcHJvdmlkZXJzLlxuICovXG5leHBvcnQgY29uc3QgQ09OVEVYVF9QUk9WSURFUlMgPSBuZXcgU2V0KFtcIklQIENvbnRleHRcIiwgXCJETlMgUmVjb3Jkc1wiLCBcIkNlcnQgSGlzdG9yeVwiLCBcIlRocmVhdE1pbmVyXCIsIFwiQVNOIEludGVsXCJdKTtcblxuLyoqXG4gKiBDcmVhdGUgYSBsYWJlbGVkIGNvbnRleHQgZmllbGQgZWxlbWVudCB3aXRoIHRoZSBwcm92aWRlci1jb250ZXh0LWZpZWxkIGNsYXNzLlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmZ1bmN0aW9uIGNyZWF0ZUxhYmVsZWRGaWVsZChsYWJlbDogc3RyaW5nKTogSFRNTEVsZW1lbnQge1xuICBjb25zdCBmaWVsZEVsID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gIGZpZWxkRWwuY2xhc3NOYW1lID0gXCJwcm92aWRlci1jb250ZXh0LWZpZWxkXCI7XG5cbiAgY29uc3QgbGFiZWxFbCA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBsYWJlbEVsLmNsYXNzTmFtZSA9IFwicHJvdmlkZXItY29udGV4dC1sYWJlbFwiO1xuICBsYWJlbEVsLnRleHRDb250ZW50ID0gbGFiZWwgKyBcIjogXCI7XG4gIGZpZWxkRWwuYXBwZW5kQ2hpbGQobGFiZWxFbCk7XG5cbiAgcmV0dXJuIGZpZWxkRWw7XG59XG5cbi8qKlxuICogQ3JlYXRlIGNvbnRleHR1YWwgZmllbGRzIGZyb20gYSBwcm92aWRlciByZXN1bHQncyByYXdfc3RhdHMuXG4gKiBSZXR1cm5zIG51bGwgaWYgbm8gY29udGV4dCBmaWVsZHMgYXJlIGF2YWlsYWJsZSBmb3IgdGhpcyBwcm92aWRlci5cbiAqIEFsbCBET00gY29uc3RydWN0aW9uIHVzZXMgY3JlYXRlRWxlbWVudCArIHRleHRDb250ZW50IChTRUMtMDgpLlxuICovXG5mdW5jdGlvbiBjcmVhdGVDb250ZXh0RmllbGRzKHJlc3VsdDogRW5yaWNobWVudFJlc3VsdEl0ZW0pOiBIVE1MRWxlbWVudCB8IG51bGwge1xuICBjb25zdCBmaWVsZERlZnMgPSBQUk9WSURFUl9DT05URVhUX0ZJRUxEU1tyZXN1bHQucHJvdmlkZXJdO1xuICBpZiAoIWZpZWxkRGVmcykgcmV0dXJuIG51bGw7XG5cbiAgY29uc3Qgc3RhdHMgPSByZXN1bHQucmF3X3N0YXRzO1xuICBpZiAoIXN0YXRzKSByZXR1cm4gbnVsbDtcblxuICBjb25zdCBjb250YWluZXIgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiZGl2XCIpO1xuICBjb250YWluZXIuY2xhc3NOYW1lID0gXCJwcm92aWRlci1jb250ZXh0XCI7XG5cbiAgbGV0IGhhc0ZpZWxkcyA9IGZhbHNlO1xuXG4gIGZvciAoY29uc3QgZGVmIG9mIGZpZWxkRGVmcykge1xuICAgIGNvbnN0IHZhbHVlID0gc3RhdHNbZGVmLmtleV07XG4gICAgaWYgKHZhbHVlID09PSB1bmRlZmluZWQgfHwgdmFsdWUgPT09IG51bGwgfHwgdmFsdWUgPT09IFwiXCIpIGNvbnRpbnVlO1xuXG4gICAgaWYgKGRlZi50eXBlID09PSBcInRhZ3NcIiAmJiBBcnJheS5pc0FycmF5KHZhbHVlKSAmJiB2YWx1ZS5sZW5ndGggPiAwKSB7XG4gICAgICBjb25zdCBmaWVsZEVsID0gY3JlYXRlTGFiZWxlZEZpZWxkKGRlZi5sYWJlbCk7XG4gICAgICBmb3IgKGNvbnN0IHRhZyBvZiB2YWx1ZSkge1xuICAgICAgICBpZiAodHlwZW9mIHRhZyAhPT0gXCJzdHJpbmdcIiAmJiB0eXBlb2YgdGFnICE9PSBcIm51bWJlclwiKSBjb250aW51ZTtcbiAgICAgICAgY29uc3QgdGFnRWwgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICAgICAgdGFnRWwuY2xhc3NOYW1lID0gXCJjb250ZXh0LXRhZ1wiO1xuICAgICAgICB0YWdFbC50ZXh0Q29udGVudCA9IFN0cmluZyh0YWcpO1xuICAgICAgICBmaWVsZEVsLmFwcGVuZENoaWxkKHRhZ0VsKTtcbiAgICAgIH1cbiAgICAgIGNvbnRhaW5lci5hcHBlbmRDaGlsZChmaWVsZEVsKTtcbiAgICAgIGhhc0ZpZWxkcyA9IHRydWU7XG4gICAgfSBlbHNlIGlmIChkZWYudHlwZSA9PT0gXCJ0ZXh0XCIgJiYgKHR5cGVvZiB2YWx1ZSA9PT0gXCJzdHJpbmdcIiB8fCB0eXBlb2YgdmFsdWUgPT09IFwibnVtYmVyXCIgfHwgdHlwZW9mIHZhbHVlID09PSBcImJvb2xlYW5cIikpIHtcbiAgICAgIGNvbnN0IGZpZWxkRWwgPSBjcmVhdGVMYWJlbGVkRmllbGQoZGVmLmxhYmVsKTtcbiAgICAgIGNvbnN0IHZhbEVsID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gICAgICB2YWxFbC50ZXh0Q29udGVudCA9IFN0cmluZyh2YWx1ZSk7XG4gICAgICBmaWVsZEVsLmFwcGVuZENoaWxkKHZhbEVsKTtcbiAgICAgIGNvbnRhaW5lci5hcHBlbmRDaGlsZChmaWVsZEVsKTtcbiAgICAgIGhhc0ZpZWxkcyA9IHRydWU7XG4gICAgfVxuICB9XG5cbiAgcmV0dXJuIGhhc0ZpZWxkcyA/IGNvbnRhaW5lciA6IG51bGw7XG59XG5cbi8vIC0tLS0gRXhwb3J0ZWQgcm93IGJ1aWxkZXJzIC0tLS1cblxuLyoqXG4gKiBHZXQgb3IgY3JlYXRlIHRoZSAuaW9jLXN1bW1hcnktcm93IGVsZW1lbnQgaW5zaWRlIHRoZSBzbG90LlxuICogSW5zZXJ0cyBiZWZvcmUgLmNoZXZyb24tdG9nZ2xlIGlmIHByZXNlbnQsIG90aGVyd2lzZSBhcyBmaXJzdCBjaGlsZC5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGdldE9yQ3JlYXRlU3VtbWFyeVJvdyhzbG90OiBIVE1MRWxlbWVudCk6IEhUTUxFbGVtZW50IHtcbiAgY29uc3QgZXhpc3RpbmcgPSBzbG90LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLmlvYy1zdW1tYXJ5LXJvd1wiKTtcbiAgaWYgKGV4aXN0aW5nKSByZXR1cm4gZXhpc3Rpbmc7XG5cbiAgY29uc3Qgcm93ID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcImRpdlwiKTtcbiAgcm93LmNsYXNzTmFtZSA9IFwiaW9jLXN1bW1hcnktcm93XCI7XG5cbiAgLy8gSW5zZXJ0IGJlZm9yZSBjaGV2cm9uLXRvZ2dsZSBpZiBwcmVzZW50XG4gIGNvbnN0IGNoZXZyb24gPSBzbG90LnF1ZXJ5U2VsZWN0b3IoXCIuY2hldnJvbi10b2dnbGVcIik7XG4gIGlmIChjaGV2cm9uKSB7XG4gICAgc2xvdC5pbnNlcnRCZWZvcmUocm93LCBjaGV2cm9uKTtcbiAgfSBlbHNlIHtcbiAgICBzbG90LmFwcGVuZENoaWxkKHJvdyk7XG4gIH1cblxuICByZXR1cm4gcm93O1xufVxuXG4vKipcbiAqIFVwZGF0ZSAob3IgY3JlYXRlKSB0aGUgc3VtbWFyeSByb3cgZm9yIGFuIElPQyBpbiBpdHMgZW5yaWNobWVudCBzbG90LlxuICogU2hvd3Mgd29yc3QgdmVyZGljdCBiYWRnZSwgYXR0cmlidXRpb24gdGV4dCwgYW5kIGNvbnNlbnN1cyBiYWRnZS5cbiAqIEFsbCBET00gY29uc3RydWN0aW9uIHVzZXMgY3JlYXRlRWxlbWVudCArIHRleHRDb250ZW50IChTRUMtMDgpLlxuICovXG5leHBvcnQgZnVuY3Rpb24gdXBkYXRlU3VtbWFyeVJvdyhcbiAgc2xvdDogSFRNTEVsZW1lbnQsXG4gIGlvY1ZhbHVlOiBzdHJpbmcsXG4gIGlvY1ZlcmRpY3RzOiBSZWNvcmQ8c3RyaW5nLCBWZXJkaWN0RW50cnlbXT5cbik6IHZvaWQge1xuICBjb25zdCBlbnRyaWVzID0gaW9jVmVyZGljdHNbaW9jVmFsdWVdO1xuICBpZiAoIWVudHJpZXMgfHwgZW50cmllcy5sZW5ndGggPT09IDApIHJldHVybjtcblxuICBjb25zdCB3b3JzdFZlcmRpY3QgPSBjb21wdXRlV29yc3RWZXJkaWN0KGVudHJpZXMpO1xuICBjb25zdCBhdHRyaWJ1dGlvbiA9IGNvbXB1dGVBdHRyaWJ1dGlvbihlbnRyaWVzKTtcblxuICBjb25zdCBzdW1tYXJ5Um93ID0gZ2V0T3JDcmVhdGVTdW1tYXJ5Um93KHNsb3QpO1xuXG4gIC8vIENsZWFyIGV4aXN0aW5nIGNoaWxkcmVuIChpbW11dGFibGUgcmVidWlsZCBwYXR0ZXJuKVxuICBzdW1tYXJ5Um93LnRleHRDb250ZW50ID0gXCJcIjtcblxuICAvLyBhLiBWZXJkaWN0IGJhZGdlXG4gIGNvbnN0IHZlcmRpY3RCYWRnZSA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICB2ZXJkaWN0QmFkZ2UuY2xhc3NOYW1lID0gXCJ2ZXJkaWN0LWJhZGdlIHZlcmRpY3QtXCIgKyB3b3JzdFZlcmRpY3Q7XG4gIHZlcmRpY3RCYWRnZS50ZXh0Q29udGVudCA9IFZFUkRJQ1RfTEFCRUxTW3dvcnN0VmVyZGljdF07XG4gIHN1bW1hcnlSb3cuYXBwZW5kQ2hpbGQodmVyZGljdEJhZGdlKTtcblxuICAvLyBiLiBBdHRyaWJ1dGlvbiB0ZXh0XG4gIGNvbnN0IGF0dHJpYnV0aW9uU3BhbiA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBhdHRyaWJ1dGlvblNwYW4uY2xhc3NOYW1lID0gXCJpb2Mtc3VtbWFyeS1hdHRyaWJ1dGlvblwiO1xuICBhdHRyaWJ1dGlvblNwYW4udGV4dENvbnRlbnQgPSBhdHRyaWJ1dGlvbi50ZXh0O1xuICBzdW1tYXJ5Um93LmFwcGVuZENoaWxkKGF0dHJpYnV0aW9uU3Bhbik7XG5cbiAgLy8gYy4gVmVyZGljdCBtaWNyby1iYXIgKHJlcGxhY2VzIGNvbnNlbnN1cyBiYWRnZSlcbiAgY29uc3QgY291bnRzID0gY29tcHV0ZVZlcmRpY3RDb3VudHMoZW50cmllcyk7XG4gIGNvbnN0IHRvdGFsID0gTWF0aC5tYXgoMSwgY291bnRzLnRvdGFsKTtcbiAgY29uc3QgbWljcm9CYXIgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwiZGl2XCIpO1xuICBtaWNyb0Jhci5jbGFzc05hbWUgPSBcInZlcmRpY3QtbWljcm8tYmFyXCI7XG4gIG1pY3JvQmFyLnNldEF0dHJpYnV0ZShcInRpdGxlXCIsXG4gICAgYCR7Y291bnRzLm1hbGljaW91c30gbWFsaWNpb3VzLCAke2NvdW50cy5zdXNwaWNpb3VzfSBzdXNwaWNpb3VzLCAke2NvdW50cy5jbGVhbn0gY2xlYW4sICR7Y291bnRzLm5vRGF0YX0gbm8gZGF0YWBcbiAgKTtcbiAgY29uc3Qgc2VnbWVudHM6IEFycmF5PFtudW1iZXIsIHN0cmluZ10+ID0gW1xuICAgIFtjb3VudHMubWFsaWNpb3VzLCBcIm1hbGljaW91c1wiXSxcbiAgICBbY291bnRzLnN1c3BpY2lvdXMsIFwic3VzcGljaW91c1wiXSxcbiAgICBbY291bnRzLmNsZWFuLCBcImNsZWFuXCJdLFxuICAgIFtjb3VudHMubm9EYXRhLCBcIm5vX2RhdGFcIl0sXG4gIF07XG4gIGZvciAoY29uc3QgW2NvdW50LCB2ZXJkaWN0XSBvZiBzZWdtZW50cykge1xuICAgIGlmIChjb3VudCA9PT0gMCkgY29udGludWU7XG4gICAgY29uc3Qgc2VnID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcImRpdlwiKTtcbiAgICBzZWcuY2xhc3NOYW1lID0gXCJtaWNyby1iYXItc2VnbWVudCBtaWNyby1iYXItc2VnbWVudC0tXCIgKyB2ZXJkaWN0O1xuICAgIHNlZy5zdHlsZS53aWR0aCA9IE1hdGgucm91bmQoKGNvdW50IC8gdG90YWwpICogMTAwKSArIFwiJVwiO1xuICAgIG1pY3JvQmFyLmFwcGVuZENoaWxkKHNlZyk7XG4gIH1cbiAgc3VtbWFyeVJvdy5hcHBlbmRDaGlsZChtaWNyb0Jhcik7XG59XG5cbi8qKlxuICogQ3JlYXRlIGEgY29udGV4dCByb3cgXHUyMDE0IHB1cmVseSBpbmZvcm1hdGlvbmFsLCBubyB2ZXJkaWN0IGJhZGdlLlxuICogQ29udGV4dCBwcm92aWRlcnMgKElQIENvbnRleHQsIEROUyBSZWNvcmRzLCBDZXJ0IEhpc3RvcnkpIGNhcnJ5IG1ldGFkYXRhXG4gKiBhbmQgbXVzdCBub3QgcGFydGljaXBhdGUgaW4gY29uc2Vuc3VzL2F0dHJpYnV0aW9uIG9yIGNhcmQgdmVyZGljdCB1cGRhdGVzLlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjcmVhdGVDb250ZXh0Um93KHJlc3VsdDogRW5yaWNobWVudFJlc3VsdEl0ZW0pOiBIVE1MRWxlbWVudCB7XG4gIGNvbnN0IHJvdyA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIik7XG4gIHJvdy5jbGFzc05hbWUgPSBcInByb3ZpZGVyLWRldGFpbC1yb3cgcHJvdmlkZXItY29udGV4dC1yb3dcIjtcbiAgcm93LnNldEF0dHJpYnV0ZShcImRhdGEtdmVyZGljdFwiLCBcImNvbnRleHRcIik7IC8vIHNlbnRpbmVsIGZvciBzb3J0IHBpbm5pbmdcblxuICBjb25zdCBuYW1lU3BhbiA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBuYW1lU3Bhbi5jbGFzc05hbWUgPSBcInByb3ZpZGVyLWRldGFpbC1uYW1lXCI7XG4gIG5hbWVTcGFuLnRleHRDb250ZW50ID0gcmVzdWx0LnByb3ZpZGVyO1xuICByb3cuYXBwZW5kQ2hpbGQobmFtZVNwYW4pO1xuXG4gIC8vIE5PIHZlcmRpY3QgYmFkZ2UgXHUyMDE0IElQIENvbnRleHQgaXMgcHVyZWx5IGluZm9ybWF0aW9uYWxcblxuICAvLyBBZGQgY29udGV4dCBmaWVsZHMgKGdlbywgUFRSLCBmbGFncykgdXNpbmcgZXhpc3RpbmcgY3JlYXRlQ29udGV4dEZpZWxkcygpXG4gIGNvbnN0IGNvbnRleHRFbCA9IGNyZWF0ZUNvbnRleHRGaWVsZHMocmVzdWx0KTtcbiAgaWYgKGNvbnRleHRFbCkge1xuICAgIHJvdy5hcHBlbmRDaGlsZChjb250ZXh0RWwpO1xuICB9XG5cbiAgLy8gQ2FjaGUgYmFkZ2UgaWYgcmVzdWx0IHdhcyBzZXJ2ZWQgZnJvbSBjYWNoZVxuICBpZiAocmVzdWx0LmNhY2hlZF9hdCkge1xuICAgIGNvbnN0IGNhY2hlQmFkZ2UgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICBjYWNoZUJhZGdlLmNsYXNzTmFtZSA9IFwiY2FjaGUtYmFkZ2VcIjtcbiAgICBjYWNoZUJhZGdlLnRleHRDb250ZW50ID0gXCJjYWNoZWQgXCIgKyBmb3JtYXRSZWxhdGl2ZVRpbWUocmVzdWx0LmNhY2hlZF9hdCk7XG4gICAgcm93LmFwcGVuZENoaWxkKGNhY2hlQmFkZ2UpO1xuICB9XG5cbiAgcmV0dXJuIHJvdztcbn1cblxuLyoqXG4gKiBDcmVhdGUgYSBzaW5nbGUgcHJvdmlkZXIgZGV0YWlsIHJvdyBmb3IgdGhlIC5lbnJpY2htZW50LWRldGFpbHMgY29udGFpbmVyLlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjcmVhdGVEZXRhaWxSb3coXG4gIHByb3ZpZGVyOiBzdHJpbmcsXG4gIHZlcmRpY3Q6IFZlcmRpY3RLZXksXG4gIHN0YXRUZXh0OiBzdHJpbmcsXG4gIHJlc3VsdD86IEVucmljaG1lbnRJdGVtXG4pOiBIVE1MRWxlbWVudCB7XG4gIGNvbnN0IHJvdyA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIik7XG4gIGNvbnN0IGlzTm9EYXRhID0gdmVyZGljdCA9PT0gXCJub19kYXRhXCIgfHwgdmVyZGljdCA9PT0gXCJlcnJvclwiO1xuICByb3cuY2xhc3NOYW1lID0gXCJwcm92aWRlci1kZXRhaWwtcm93XCIgKyAoaXNOb0RhdGEgPyBcIiBwcm92aWRlci1yb3ctLW5vLWRhdGFcIiA6IFwiXCIpO1xuICByb3cuc2V0QXR0cmlidXRlKFwiZGF0YS12ZXJkaWN0XCIsIHZlcmRpY3QpO1xuXG4gIGNvbnN0IG5hbWVTcGFuID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gIG5hbWVTcGFuLmNsYXNzTmFtZSA9IFwicHJvdmlkZXItZGV0YWlsLW5hbWVcIjtcbiAgbmFtZVNwYW4udGV4dENvbnRlbnQgPSBwcm92aWRlcjtcblxuICBjb25zdCBiYWRnZSA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICBiYWRnZS5jbGFzc05hbWUgPSBcInZlcmRpY3QtYmFkZ2UgdmVyZGljdC1cIiArIHZlcmRpY3Q7XG4gIGJhZGdlLnRleHRDb250ZW50ID0gVkVSRElDVF9MQUJFTFNbdmVyZGljdF07XG5cbiAgY29uc3Qgc3RhdFNwYW4gPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgc3RhdFNwYW4uY2xhc3NOYW1lID0gXCJwcm92aWRlci1kZXRhaWwtc3RhdFwiO1xuICBzdGF0U3Bhbi50ZXh0Q29udGVudCA9IHN0YXRUZXh0O1xuXG4gIHJvdy5hcHBlbmRDaGlsZChuYW1lU3Bhbik7XG4gIHJvdy5hcHBlbmRDaGlsZChiYWRnZSk7XG4gIHJvdy5hcHBlbmRDaGlsZChzdGF0U3Bhbik7XG5cbiAgLy8gQ2FjaGUgYmFkZ2UgXHUyMDE0IHNob3cgcmVsYXRpdmUgdGltZSBpZiByZXN1bHQgd2FzIHNlcnZlZCBmcm9tIGNhY2hlXG4gIGlmIChyZXN1bHQgJiYgcmVzdWx0LnR5cGUgPT09IFwicmVzdWx0XCIgJiYgcmVzdWx0LmNhY2hlZF9hdCkge1xuICAgIGNvbnN0IGNhY2hlQmFkZ2UgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICBjYWNoZUJhZGdlLmNsYXNzTmFtZSA9IFwiY2FjaGUtYmFkZ2VcIjtcbiAgICBjb25zdCBhZ28gPSBmb3JtYXRSZWxhdGl2ZVRpbWUocmVzdWx0LmNhY2hlZF9hdCk7XG4gICAgY2FjaGVCYWRnZS50ZXh0Q29udGVudCA9IFwiY2FjaGVkIFwiICsgYWdvO1xuICAgIHJvdy5hcHBlbmRDaGlsZChjYWNoZUJhZGdlKTtcbiAgfVxuXG4gIC8vIENvbnRleHQgZmllbGRzIFx1MjAxNCBwcm92aWRlci1zcGVjaWZpYyBpbnRlbGxpZ2VuY2UgZnJvbSByYXdfc3RhdHNcbiAgaWYgKHJlc3VsdCAmJiByZXN1bHQudHlwZSA9PT0gXCJyZXN1bHRcIikge1xuICAgIGNvbnN0IGNvbnRleHRFbCA9IGNyZWF0ZUNvbnRleHRGaWVsZHMocmVzdWx0KTtcbiAgICBpZiAoY29udGV4dEVsKSB7XG4gICAgICByb3cuYXBwZW5kQ2hpbGQoY29udGV4dEVsKTtcbiAgICB9XG4gIH1cblxuICByZXR1cm4gcm93O1xufVxuXG4vKipcbiAqIFVuaWZpZWQgcm93IGNyZWF0aW9uIGRpc3BhdGNoZXIgXHUyMDE0IHJvdXRlcyB0byBjcmVhdGVDb250ZXh0Um93IG9yIGNyZWF0ZURldGFpbFJvd1xuICogYmFzZWQgb24gdGhlIGtpbmQgcGFyYW1ldGVyLiBQcm92aWRlcyBhIHN0YWJsZSBBUEkgZm9yIFBoYXNlIDMgdmlzdWFsIHdvcmsuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBjcmVhdGVQcm92aWRlclJvdyhcbiAgcmVzdWx0OiBFbnJpY2htZW50UmVzdWx0SXRlbSxcbiAga2luZDogXCJjb250ZXh0XCIgfCBcImRldGFpbFwiLFxuICBzdGF0VGV4dDogc3RyaW5nXG4pOiBIVE1MRWxlbWVudCB7XG4gIGlmIChraW5kID09PSBcImNvbnRleHRcIikge1xuICAgIHJldHVybiBjcmVhdGVDb250ZXh0Um93KHJlc3VsdCk7XG4gIH1cbiAgcmV0dXJuIGNyZWF0ZURldGFpbFJvdyhyZXN1bHQucHJvdmlkZXIsIHJlc3VsdC52ZXJkaWN0LCBzdGF0VGV4dCwgcmVzdWx0KTtcbn1cblxuLyoqXG4gKiBQb3B1bGF0ZSB0aGUgaW5saW5lIGNvbnRleHQgbGluZSBpbiB0aGUgSU9DIGNhcmQgaGVhZGVyIChDVFgtMDEpLlxuICpcbiAqIEV4dHJhY3RzIGtleSBmaWVsZHMgZnJvbSBjb250ZXh0IHByb3ZpZGVyIHJhd19zdGF0cyBhbmQgYXBwZW5kcyB0aGVtXG4gKiB0byB0aGUgLmlvYy1jb250ZXh0LWxpbmUgZWxlbWVudC4gUHJvdmlkZXJzIGhhbmRsZWQ6XG4gKiAgIC0gXCJJUCBDb250ZXh0XCIgXHUyMTkyIHJhd19zdGF0cy5nZW8gKHByZS1mb3JtYXR0ZWQgbG9jYXRpb24gc3RyaW5nKVxuICogICAtIFwiQVNOIEludGVsXCIgIFx1MjE5MiByYXdfc3RhdHMuYXNuICsgcmF3X3N0YXRzLnByZWZpeCAoc2tpcHMgaWYgSVAgQ29udGV4dCBhbHJlYWR5IHByZXNlbnQpXG4gKiAgIC0gXCJETlMgUmVjb3Jkc1wiIFx1MjE5MiByYXdfc3RhdHMuYSAoZmlyc3QgMyBBLXJlY29yZCBJUHMpXG4gKlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiB1cGRhdGVDb250ZXh0TGluZShjYXJkOiBIVE1MRWxlbWVudCwgcmVzdWx0OiBFbnJpY2htZW50UmVzdWx0SXRlbSk6IHZvaWQge1xuICBjb25zdCBjb250ZXh0TGluZSA9IGNhcmQucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIuaW9jLWNvbnRleHQtbGluZVwiKTtcbiAgaWYgKCFjb250ZXh0TGluZSkgcmV0dXJuO1xuXG4gIGNvbnN0IHByb3ZpZGVyID0gcmVzdWx0LnByb3ZpZGVyO1xuICBjb25zdCBzdGF0cyA9IHJlc3VsdC5yYXdfc3RhdHM7XG4gIGlmICghc3RhdHMpIHJldHVybjtcblxuICBpZiAocHJvdmlkZXIgPT09IFwiSVAgQ29udGV4dFwiKSB7XG4gICAgY29uc3QgZ2VvID0gc3RhdHMuZ2VvO1xuICAgIGlmICghZ2VvIHx8IHR5cGVvZiBnZW8gIT09IFwic3RyaW5nXCIpIHJldHVybjtcblxuICAgIC8vIENoZWNrIGlmIElQIENvbnRleHQgc3BhbiBhbHJlYWR5IGV4aXN0cyBcdTIwMTQgcmVwbGFjZSBpdHMgdGV4dFxuICAgIGNvbnN0IGV4aXN0aW5nID0gY29udGV4dExpbmUucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oJ3NwYW5bZGF0YS1jb250ZXh0LXByb3ZpZGVyPVwiSVAgQ29udGV4dFwiXScpO1xuICAgIGlmIChleGlzdGluZykge1xuICAgICAgZXhpc3RpbmcudGV4dENvbnRlbnQgPSBnZW87XG4gICAgICByZXR1cm47XG4gICAgfVxuXG4gICAgLy8gUmVtb3ZlIEFTTiBJbnRlbCBzcGFuIGlmIHByZXNlbnQgXHUyMDE0IElQIENvbnRleHQgaXMgbW9yZSBjb21wcmVoZW5zaXZlXG4gICAgY29uc3QgYXNuU3BhbiA9IGNvbnRleHRMaW5lLnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KCdzcGFuW2RhdGEtY29udGV4dC1wcm92aWRlcj1cIkFTTiBJbnRlbFwiXScpO1xuICAgIGlmIChhc25TcGFuKSB7XG4gICAgICBjb250ZXh0TGluZS5yZW1vdmVDaGlsZChhc25TcGFuKTtcbiAgICB9XG5cbiAgICBjb25zdCBzcGFuID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudChcInNwYW5cIik7XG4gICAgc3Bhbi5jbGFzc05hbWUgPSBcImNvbnRleHQtZmllbGRcIjtcbiAgICBzcGFuLnNldEF0dHJpYnV0ZShcImRhdGEtY29udGV4dC1wcm92aWRlclwiLCBcIklQIENvbnRleHRcIik7XG4gICAgc3Bhbi50ZXh0Q29udGVudCA9IGdlbztcbiAgICBjb250ZXh0TGluZS5hcHBlbmRDaGlsZChzcGFuKTtcbiAgfSBlbHNlIGlmIChwcm92aWRlciA9PT0gXCJBU04gSW50ZWxcIikge1xuICAgIC8vIE9ubHkgcG9wdWxhdGUgaWYgSVAgQ29udGV4dCBoYXNuJ3QgYWxyZWFkeSBwcm92aWRlZCByaWNoZXIgZGF0YVxuICAgIGlmIChjb250ZXh0TGluZS5xdWVyeVNlbGVjdG9yKCdzcGFuW2RhdGEtY29udGV4dC1wcm92aWRlcj1cIklQIENvbnRleHRcIl0nKSkgcmV0dXJuO1xuXG4gICAgY29uc3QgYXNuID0gc3RhdHMuYXNuO1xuICAgIGNvbnN0IHByZWZpeCA9IHN0YXRzLnByZWZpeDtcbiAgICBpZiAoIWFzbiAmJiAhcHJlZml4KSByZXR1cm47XG5cbiAgICBjb25zdCBwYXJ0czogc3RyaW5nW10gPSBbXTtcbiAgICBpZiAoYXNuICYmICh0eXBlb2YgYXNuID09PSBcInN0cmluZ1wiIHx8IHR5cGVvZiBhc24gPT09IFwibnVtYmVyXCIpKSBwYXJ0cy5wdXNoKFN0cmluZyhhc24pKTtcbiAgICBpZiAocHJlZml4ICYmIHR5cGVvZiBwcmVmaXggPT09IFwic3RyaW5nXCIpIHBhcnRzLnB1c2gocHJlZml4KTtcbiAgICBpZiAocGFydHMubGVuZ3RoID09PSAwKSByZXR1cm47XG5cbiAgICBjb25zdCB0ZXh0ID0gcGFydHMuam9pbihcIiBcdTAwQjcgXCIpO1xuICAgIGNvbnN0IGV4aXN0aW5nID0gY29udGV4dExpbmUucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oJ3NwYW5bZGF0YS1jb250ZXh0LXByb3ZpZGVyPVwiQVNOIEludGVsXCJdJyk7XG4gICAgaWYgKGV4aXN0aW5nKSB7XG4gICAgICBleGlzdGluZy50ZXh0Q29udGVudCA9IHRleHQ7XG4gICAgICByZXR1cm47XG4gICAgfVxuXG4gICAgY29uc3Qgc3BhbiA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICAgIHNwYW4uY2xhc3NOYW1lID0gXCJjb250ZXh0LWZpZWxkXCI7XG4gICAgc3Bhbi5zZXRBdHRyaWJ1dGUoXCJkYXRhLWNvbnRleHQtcHJvdmlkZXJcIiwgXCJBU04gSW50ZWxcIik7XG4gICAgc3Bhbi50ZXh0Q29udGVudCA9IHRleHQ7XG4gICAgY29udGV4dExpbmUuYXBwZW5kQ2hpbGQoc3Bhbik7XG4gIH0gZWxzZSBpZiAocHJvdmlkZXIgPT09IFwiRE5TIFJlY29yZHNcIikge1xuICAgIGNvbnN0IGFSZWNvcmRzID0gc3RhdHMuYTtcbiAgICBpZiAoIUFycmF5LmlzQXJyYXkoYVJlY29yZHMpIHx8IGFSZWNvcmRzLmxlbmd0aCA9PT0gMCkgcmV0dXJuO1xuXG4gICAgY29uc3QgaXBzID0gYVJlY29yZHMuc2xpY2UoMCwgMykuZmlsdGVyKChpcCk6IGlwIGlzIHN0cmluZyA9PiB0eXBlb2YgaXAgPT09IFwic3RyaW5nXCIpO1xuICAgIGlmIChpcHMubGVuZ3RoID09PSAwKSByZXR1cm47XG5cbiAgICBjb25zdCB0ZXh0ID0gXCJBOiBcIiArIGlwcy5qb2luKFwiLCBcIik7XG4gICAgY29uc3QgZXhpc3RpbmcgPSBjb250ZXh0TGluZS5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50Pignc3BhbltkYXRhLWNvbnRleHQtcHJvdmlkZXI9XCJETlMgUmVjb3Jkc1wiXScpO1xuICAgIGlmIChleGlzdGluZykge1xuICAgICAgZXhpc3RpbmcudGV4dENvbnRlbnQgPSB0ZXh0O1xuICAgICAgcmV0dXJuO1xuICAgIH1cblxuICAgIGNvbnN0IHNwYW4gPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KFwic3BhblwiKTtcbiAgICBzcGFuLmNsYXNzTmFtZSA9IFwiY29udGV4dC1maWVsZFwiO1xuICAgIHNwYW4uc2V0QXR0cmlidXRlKFwiZGF0YS1jb250ZXh0LXByb3ZpZGVyXCIsIFwiRE5TIFJlY29yZHNcIik7XG4gICAgc3Bhbi50ZXh0Q29udGVudCA9IHRleHQ7XG4gICAgY29udGV4dExpbmUuYXBwZW5kQ2hpbGQoc3Bhbik7XG4gIH1cbiAgLy8gQWxsIG90aGVyIHByb3ZpZGVycyBcdTIwMTQgZG8gbm90aGluZ1xufVxuXG4vKipcbiAqIEluamVjdCBuby1kYXRhIGNvbGxhcHNlIHN1bW1hcnkgKEdSUC0wMikgaW50byB0aGUgbm8tZGF0YSBzZWN0aW9uIG9mIGFuXG4gKiBlbnJpY2htZW50IHNsb3QuIE11c3QgYmUgY2FsbGVkIEFGVEVSIGVucmljaG1lbnQgY29tcGxldGVzIGFuZCBzb3J0RGV0YWlsUm93cygpXG4gKiBoYXMgZmluYWxpemVkIHRoZSBET00gb3JkZXIuXG4gKlxuICogU2VjdGlvbiBoZWFkZXJzIGFyZSBub3cgc2VydmVyLXJlbmRlcmVkIGluIHRoZSB0ZW1wbGF0ZSAoR1JQLTAxL1MwNCkuXG4gKiBUaGlzIGZ1bmN0aW9uIG9ubHkgaGFuZGxlcyB0aGUgbm8tZGF0YSBzdW1tYXJ5IHJvdyBhbmQgY29sbGFwc2UgdG9nZ2xlLlxuICpcbiAqIENvdW50cyAucHJvdmlkZXItcm93LS1uby1kYXRhIGVsZW1lbnRzIGluIC5lbnJpY2htZW50LXNlY3Rpb24tLW5vLWRhdGEuIElmIGFueVxuICogZXhpc3QsIGNyZWF0ZXMgYSBjbGlja2FibGUgc3VtbWFyeSByb3cgdGhhdCB0b2dnbGVzIC5uby1kYXRhLWV4cGFuZGVkIG9uIHRoZVxuICogc2VjdGlvbiBlbGVtZW50LlxuICpcbiAqIEVkZ2UgY2FzZXM6IHplcm8gbm8tZGF0YSByb3dzIGhhbmRsZWQgZ3JhY2VmdWxseSAoZWFybHkgcmV0dXJuLCBubyBjcmFzaCkuXG4gKlxuICogQWxsIERPTSBjb25zdHJ1Y3Rpb24gdXNlcyBjcmVhdGVFbGVtZW50ICsgdGV4dENvbnRlbnQgKFNFQy0wOCkuXG4gKi9cbmV4cG9ydCBmdW5jdGlvbiBpbmplY3RTZWN0aW9uSGVhZGVyc0FuZE5vRGF0YVN1bW1hcnkoc2xvdDogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgLy8gSGVhZGVycyBhcmUgbm93IGluIHRoZSB0ZW1wbGF0ZSAoR1JQLTAxKS4gT25seSBuby1kYXRhIGNvbGxhcHNlIGxvZ2ljIHJlbWFpbnMuXG4gIGNvbnN0IG5vRGF0YVNlY3Rpb24gPSBzbG90LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLmVucmljaG1lbnQtc2VjdGlvbi0tbm8tZGF0YVwiKTtcbiAgaWYgKCFub0RhdGFTZWN0aW9uKSByZXR1cm47XG5cbiAgY29uc3Qgbm9EYXRhUm93cyA9IG5vRGF0YVNlY3Rpb24ucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXG4gICAgXCIucHJvdmlkZXItcm93LS1uby1kYXRhXCJcbiAgKTtcbiAgaWYgKG5vRGF0YVJvd3MubGVuZ3RoID09PSAwKSByZXR1cm47XG5cbiAgY29uc3QgY291bnQgPSBub0RhdGFSb3dzLmxlbmd0aDtcbiAgY29uc3Qgc3VtbWFyeVJvdyA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJkaXZcIik7XG4gIHN1bW1hcnlSb3cuY2xhc3NOYW1lID0gXCJuby1kYXRhLXN1bW1hcnktcm93XCI7XG4gIHN1bW1hcnlSb3cuc2V0QXR0cmlidXRlKFwicm9sZVwiLCBcImJ1dHRvblwiKTtcbiAgc3VtbWFyeVJvdy5zZXRBdHRyaWJ1dGUoXCJ0YWJpbmRleFwiLCBcIjBcIik7XG4gIHN1bW1hcnlSb3cuc2V0QXR0cmlidXRlKFwiYXJpYS1leHBhbmRlZFwiLCBcImZhbHNlXCIpO1xuICBzdW1tYXJ5Um93LnRleHRDb250ZW50ID0gY291bnQgKyBcIiBwcm92aWRlclwiICsgKGNvdW50ICE9PSAxID8gXCJzXCIgOiBcIlwiKSArIFwiIGhhZCBubyByZWNvcmRcIjtcblxuICAvLyBJbnNlcnQgc3VtbWFyeSByb3cgYmVmb3JlIHRoZSBmaXJzdCBuby1kYXRhIHJvdyB3aXRoaW4gdGhlIG5vLWRhdGEgc2VjdGlvblxuICBjb25zdCBmaXJzdE5vRGF0YSA9IG5vRGF0YVJvd3NbMF07XG4gIGlmIChmaXJzdE5vRGF0YSkge1xuICAgIG5vRGF0YVNlY3Rpb24uaW5zZXJ0QmVmb3JlKHN1bW1hcnlSb3csIGZpcnN0Tm9EYXRhKTtcbiAgfVxuXG4gIC8vIFdpcmUgY2xpY2sgXHUyMTkyIHRvZ2dsZSAubm8tZGF0YS1leHBhbmRlZCBvbiBub0RhdGFTZWN0aW9uXG4gIHN1bW1hcnlSb3cuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICBjb25zdCBpc0V4cGFuZGVkID0gbm9EYXRhU2VjdGlvbi5jbGFzc0xpc3QudG9nZ2xlKFwibm8tZGF0YS1leHBhbmRlZFwiKTtcbiAgICBzdW1tYXJ5Um93LnNldEF0dHJpYnV0ZShcImFyaWEtZXhwYW5kZWRcIiwgU3RyaW5nKGlzRXhwYW5kZWQpKTtcbiAgfSk7XG5cbiAgLy8gV2lyZSBrZXlib2FyZCBFbnRlci9TcGFjZSBmb3IgYWNjZXNzaWJpbGl0eVxuICBzdW1tYXJ5Um93LmFkZEV2ZW50TGlzdGVuZXIoXCJrZXlkb3duXCIsIChlOiBLZXlib2FyZEV2ZW50KSA9PiB7XG4gICAgaWYgKGUua2V5ID09PSBcIkVudGVyXCIgfHwgZS5rZXkgPT09IFwiIFwiKSB7XG4gICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICBzdW1tYXJ5Um93LmNsaWNrKCk7XG4gICAgfVxuICB9KTtcbn1cbiIsICIvKipcbiAqIEVucmljaG1lbnQgcG9sbGluZyBvcmNoZXN0cmF0b3IgXHUyMDE0IHBvbGxpbmcgbG9vcCwgcHJvZ3Jlc3MgdHJhY2tpbmcsXG4gKiByZXN1bHQgZGlzcGF0Y2gsIGFuZCBtb2R1bGUgc3RhdGUuXG4gKlxuICogVmVyZGljdCBjb21wdXRhdGlvbiBsaXZlcyBpbiB2ZXJkaWN0LWNvbXB1dGUudHMuXG4gKiBET00gcm93IGNvbnN0cnVjdGlvbiBsaXZlcyBpbiByb3ctZmFjdG9yeS50cy5cbiAqIFRoaXMgbW9kdWxlIG93bnMgdGhlIHBvbGxpbmcgaW50ZXJ2YWwsIGRlZHVwIG1hcCwgcGVyLUlPQyBzdGF0ZSxcbiAqIGFuZCBjb29yZGluYXRlcyByZW5kZXJpbmcgdGhyb3VnaCBpbXBvcnRlZCBmdW5jdGlvbnMuXG4gKi9cblxuaW1wb3J0IHR5cGUgeyBFbnJpY2htZW50SXRlbSwgRW5yaWNobWVudFN0YXR1cyB9IGZyb20gXCIuLi90eXBlcy9hcGlcIjtcbmltcG9ydCB0eXBlIHsgVmVyZGljdEtleSB9IGZyb20gXCIuLi90eXBlcy9pb2NcIjtcbmltcG9ydCB7IHZlcmRpY3RTZXZlcml0eUluZGV4LCBnZXRQcm92aWRlckNvdW50cyB9IGZyb20gXCIuLi90eXBlcy9pb2NcIjtcbmltcG9ydCB7IGF0dHIgfSBmcm9tIFwiLi4vdXRpbHMvZG9tXCI7XG5pbXBvcnQge1xuICBmaW5kQ2FyZEZvcklvYyxcbiAgdXBkYXRlQ2FyZFZlcmRpY3QsXG4gIHVwZGF0ZURhc2hib2FyZENvdW50cyxcbiAgc29ydENhcmRzQnlTZXZlcml0eSxcbn0gZnJvbSBcIi4vY2FyZHNcIjtcbmltcG9ydCB7IGV4cG9ydEpTT04sIGV4cG9ydENTViwgY29weUFsbElPQ3MgfSBmcm9tIFwiLi9leHBvcnRcIjtcbmltcG9ydCB0eXBlIHsgVmVyZGljdEVudHJ5IH0gZnJvbSBcIi4vdmVyZGljdC1jb21wdXRlXCI7XG5pbXBvcnQgeyBjb21wdXRlV29yc3RWZXJkaWN0LCBmaW5kV29yc3RFbnRyeSB9IGZyb20gXCIuL3ZlcmRpY3QtY29tcHV0ZVwiO1xuaW1wb3J0IHsgQ09OVEVYVF9QUk9WSURFUlMsIGNyZWF0ZUNvbnRleHRSb3csIGNyZWF0ZURldGFpbFJvdyxcbiAgICAgICAgIHVwZGF0ZVN1bW1hcnlSb3csIGZvcm1hdERhdGUsXG4gICAgICAgICBpbmplY3RTZWN0aW9uSGVhZGVyc0FuZE5vRGF0YVN1bW1hcnksXG4gICAgICAgICB1cGRhdGVDb250ZXh0TGluZSB9IGZyb20gXCIuL3Jvdy1mYWN0b3J5XCI7XG5cbi8vIC0tLS0gTW9kdWxlLXByaXZhdGUgc3RhdGUgLS0tLVxuXG4vKiogRGVib3VuY2UgdGltZXJzIGZvciBzb3J0RGV0YWlsUm93cyBcdTIwMTQga2V5ZWQgYnkgaW9jX3ZhbHVlICovXG5jb25zdCBzb3J0VGltZXJzOiBNYXA8c3RyaW5nLCBSZXR1cm5UeXBlPHR5cGVvZiBzZXRUaW1lb3V0Pj4gPSBuZXcgTWFwKCk7XG5cbi8qKiBBY2N1bXVsYXRlZCBlbnJpY2htZW50IHJlc3VsdHMgZm9yIGV4cG9ydCAqL1xuY29uc3QgYWxsUmVzdWx0czogRW5yaWNobWVudEl0ZW1bXSA9IFtdO1xuXG4vLyAtLS0tIFByaXZhdGUgaGVscGVycyAtLS0tXG5cbi8qKlxuICogU29ydCBhbGwgLnByb3ZpZGVyLWRldGFpbC1yb3cgZWxlbWVudHMgaW4gYSBjb250YWluZXIgYnkgc2V2ZXJpdHkgZGVzY2VuZGluZy5cbiAqIG1hbGljaW91cyAoaW5kZXggNCkgZmlyc3QsIGVycm9yIChpbmRleCAwKSBsYXN0LlxuICogRGVib3VuY2VkIGF0IDEwMG1zIHBlciBJT0MgdG8gYXZvaWQgdGhyYXNoaW5nIGR1cmluZyBiYXRjaCByZXN1bHQgZGVsaXZlcnkuXG4gKi9cbmZ1bmN0aW9uIHNvcnREZXRhaWxSb3dzKGRldGFpbHNDb250YWluZXI6IEhUTUxFbGVtZW50LCBpb2NWYWx1ZTogc3RyaW5nKTogdm9pZCB7XG4gIGNvbnN0IGV4aXN0aW5nID0gc29ydFRpbWVycy5nZXQoaW9jVmFsdWUpO1xuICBpZiAoZXhpc3RpbmcgIT09IHVuZGVmaW5lZCkge1xuICAgIGNsZWFyVGltZW91dChleGlzdGluZyk7XG4gIH1cbiAgY29uc3QgdGltZXIgPSBzZXRUaW1lb3V0KCgpID0+IHtcbiAgICBzb3J0VGltZXJzLmRlbGV0ZShpb2NWYWx1ZSk7XG4gICAgY29uc3Qgcm93cyA9IEFycmF5LmZyb20oXG4gICAgICBkZXRhaWxzQ29udGFpbmVyLnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLnByb3ZpZGVyLWRldGFpbC1yb3dcIilcbiAgICApO1xuICAgIHJvd3Muc29ydCgoYSwgYikgPT4ge1xuICAgICAgY29uc3QgYVZlcmRpY3QgPSBhLmdldEF0dHJpYnV0ZShcImRhdGEtdmVyZGljdFwiKSBhcyBWZXJkaWN0S2V5IHwgbnVsbDtcbiAgICAgIGNvbnN0IGJWZXJkaWN0ID0gYi5nZXRBdHRyaWJ1dGUoXCJkYXRhLXZlcmRpY3RcIikgYXMgVmVyZGljdEtleSB8IG51bGw7XG4gICAgICBjb25zdCBhSWR4ID0gYVZlcmRpY3QgPyB2ZXJkaWN0U2V2ZXJpdHlJbmRleChhVmVyZGljdCkgOiAtMTtcbiAgICAgIGNvbnN0IGJJZHggPSBiVmVyZGljdCA/IHZlcmRpY3RTZXZlcml0eUluZGV4KGJWZXJkaWN0KSA6IC0xO1xuICAgICAgcmV0dXJuIGJJZHggLSBhSWR4OyAvLyBkZXNjZW5kaW5nOiBtYWxpY2lvdXMgZmlyc3RcbiAgICB9KTtcbiAgICBmb3IgKGNvbnN0IHJvdyBvZiByb3dzKSB7XG4gICAgICBkZXRhaWxzQ29udGFpbmVyLmFwcGVuZENoaWxkKHJvdyk7XG4gICAgfVxuICB9LCAxMDApO1xuICBzb3J0VGltZXJzLnNldChpb2NWYWx1ZSwgdGltZXIpO1xufVxuXG4vKipcbiAqIEZpbmQgdGhlIGNvcHkgYnV0dG9uIGZvciBhIGdpdmVuIElPQyB2YWx1ZSBieSBpdGVyYXRpbmcgLmNvcHktYnRuIGVsZW1lbnRzLlxuICogU291cmNlOiBtYWluLmpzIGZpbmRDb3B5QnV0dG9uRm9ySW9jKCkgKGxpbmVzIDU3MS01NzkpLlxuICovXG5mdW5jdGlvbiBmaW5kQ29weUJ1dHRvbkZvcklvYyhpb2NWYWx1ZTogc3RyaW5nKTogSFRNTEVsZW1lbnQgfCBudWxsIHtcbiAgY29uc3QgYnRucyA9IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmNvcHktYnRuXCIpO1xuICBmb3IgKGxldCBpID0gMDsgaSA8IGJ0bnMubGVuZ3RoOyBpKyspIHtcbiAgICBjb25zdCBidG4gPSBidG5zW2ldO1xuICAgIGlmIChidG4gJiYgYXR0cihidG4sIFwiZGF0YS12YWx1ZVwiKSA9PT0gaW9jVmFsdWUpIHtcbiAgICAgIHJldHVybiBidG47XG4gICAgfVxuICB9XG4gIHJldHVybiBudWxsO1xufVxuXG4vKipcbiAqIFVwZGF0ZSB0aGUgY29weSBidXR0b24ncyBkYXRhLWVucmljaG1lbnQgYXR0cmlidXRlIHdpdGggdGhlIHdvcnN0IHZlcmRpY3RcbiAqIHN1bW1hcnkgdGV4dCBhY3Jvc3MgYWxsIHByb3ZpZGVycyBmb3IgdGhlIGdpdmVuIElPQy5cbiAqIFNvdXJjZTogbWFpbi5qcyB1cGRhdGVDb3B5QnV0dG9uV29yc3RWZXJkaWN0KCkgKGxpbmVzIDU1My01NjkpLlxuICovXG5mdW5jdGlvbiB1cGRhdGVDb3B5QnV0dG9uV29yc3RWZXJkaWN0KFxuICBpb2NWYWx1ZTogc3RyaW5nLFxuICBpb2NWZXJkaWN0czogUmVjb3JkPHN0cmluZywgVmVyZGljdEVudHJ5W10+XG4pOiB2b2lkIHtcbiAgY29uc3QgY29weUJ0biA9IGZpbmRDb3B5QnV0dG9uRm9ySW9jKGlvY1ZhbHVlKTtcbiAgaWYgKCFjb3B5QnRuKSByZXR1cm47XG5cbiAgY29uc3Qgd29yc3RFbnRyeSA9IGZpbmRXb3JzdEVudHJ5KGlvY1ZlcmRpY3RzW2lvY1ZhbHVlXSA/PyBbXSk7XG4gIGlmICghd29yc3RFbnRyeSkgcmV0dXJuO1xuXG4gIGNvcHlCdG4uc2V0QXR0cmlidXRlKFwiZGF0YS1lbnJpY2htZW50XCIsIHdvcnN0RW50cnkuc3VtbWFyeVRleHQpO1xufVxuXG4vKipcbiAqIFVwZGF0ZSB0aGUgcHJvZ3Jlc3MgYmFyIGZpbGwgYW5kIHRleHQuXG4gKiBTb3VyY2U6IG1haW4uanMgdXBkYXRlUHJvZ3Jlc3NCYXIoKSAobGluZXMgMzc1LTM4MykuXG4gKi9cbmZ1bmN0aW9uIHVwZGF0ZVByb2dyZXNzQmFyKGRvbmU6IG51bWJlciwgdG90YWw6IG51bWJlcik6IHZvaWQge1xuICBjb25zdCBmaWxsID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJlbnJpY2gtcHJvZ3Jlc3MtZmlsbFwiKTtcbiAgY29uc3QgdGV4dCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZW5yaWNoLXByb2dyZXNzLXRleHRcIik7XG4gIGlmICghZmlsbCB8fCAhdGV4dCkgcmV0dXJuO1xuXG4gIGNvbnN0IHBjdCA9IHRvdGFsID4gMCA/IE1hdGgucm91bmQoKGRvbmUgLyB0b3RhbCkgKiAxMDApIDogMDtcbiAgZmlsbC5zdHlsZS53aWR0aCA9IHBjdCArIFwiJVwiO1xuICB0ZXh0LnRleHRDb250ZW50ID0gZG9uZSArIFwiL1wiICsgdG90YWwgKyBcIiBwcm92aWRlcnMgY29tcGxldGVcIjtcbn1cblxuLyoqXG4gKiBTaG93IG9yIHVwZGF0ZSB0aGUgcGVuZGluZyBwcm92aWRlciBpbmRpY2F0b3IgYWZ0ZXIgdGhlIGZpcnN0IHJlc3VsdCBmb3IgYW4gSU9DLlxuICogUmVhZHMgcHJvdmlkZXIgY291bnRzIGZyb20gdGhlIERPTSB2aWEgZ2V0UHJvdmlkZXJDb3VudHMoKSBcdTIwMTQgcmVmbGVjdHMgdGhlIGFjdHVhbFxuICogY29uZmlndXJlZCBwcm92aWRlciBzZXQgaW5qZWN0ZWQgYnkgdGhlIEZsYXNrIHJvdXRlIGludG8gZGF0YS1wcm92aWRlci1jb3VudHMuXG4gKiBTb3VyY2U6IG1haW4uanMgdXBkYXRlUGVuZGluZ0luZGljYXRvcigpIChsaW5lcyA0MTItNDQxKS5cbiAqL1xuZnVuY3Rpb24gdXBkYXRlUGVuZGluZ0luZGljYXRvcihcbiAgc2xvdDogSFRNTEVsZW1lbnQsXG4gIGNhcmQ6IEhUTUxFbGVtZW50IHwgbnVsbCxcbiAgcmVjZWl2ZWRDb3VudDogbnVtYmVyXG4pOiB2b2lkIHtcbiAgY29uc3QgaW9jVHlwZSA9IGNhcmQgPyBhdHRyKGNhcmQsIFwiZGF0YS1pb2MtdHlwZVwiKSA6IFwiXCI7XG4gIGNvbnN0IHByb3ZpZGVyQ291bnRzID0gZ2V0UHJvdmlkZXJDb3VudHMoKTtcbiAgY29uc3QgdG90YWxFeHBlY3RlZCA9IE9iamVjdC5wcm90b3R5cGUuaGFzT3duUHJvcGVydHkuY2FsbChwcm92aWRlckNvdW50cywgaW9jVHlwZSlcbiAgICA/IChwcm92aWRlckNvdW50c1tpb2NUeXBlXSA/PyAwKVxuICAgIDogMDtcbiAgY29uc3QgcmVtYWluaW5nID0gdG90YWxFeHBlY3RlZCAtIHJlY2VpdmVkQ291bnQ7XG5cbiAgaWYgKHJlbWFpbmluZyA8PSAwKSB7XG4gICAgLy8gQWxsIHByb3ZpZGVycyBhY2NvdW50ZWQgZm9yIFx1MjAxNCByZW1vdmUgd2FpdGluZyBpbmRpY2F0b3IgaWYgcHJlc2VudFxuICAgIGNvbnN0IGV4aXN0aW5nSW5kaWNhdG9yID0gc2xvdC5xdWVyeVNlbGVjdG9yKFwiLmVucmljaG1lbnQtd2FpdGluZy10ZXh0XCIpO1xuICAgIGlmIChleGlzdGluZ0luZGljYXRvcikge1xuICAgICAgc2xvdC5yZW1vdmVDaGlsZChleGlzdGluZ0luZGljYXRvcik7XG4gICAgfVxuICAgIHJldHVybjtcbiAgfVxuXG4gIC8vIEZpbmQgb3IgY3JlYXRlIHRoZSB3YWl0aW5nIGluZGljYXRvciBzcGFuXG4gIGxldCBpbmRpY2F0b3IgPSBzbG90LnF1ZXJ5U2VsZWN0b3I8SFRNTEVsZW1lbnQ+KFwiLmVucmljaG1lbnQtd2FpdGluZy10ZXh0XCIpO1xuICBpZiAoIWluZGljYXRvcikge1xuICAgIGluZGljYXRvciA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJzcGFuXCIpO1xuICAgIGluZGljYXRvci5jbGFzc05hbWUgPSBcImVucmljaG1lbnQtd2FpdGluZy10ZXh0IGVucmljaG1lbnQtcGVuZGluZy10ZXh0XCI7XG4gICAgc2xvdC5hcHBlbmRDaGlsZChpbmRpY2F0b3IpO1xuICB9XG4gIGluZGljYXRvci50ZXh0Q29udGVudCA9IHJlbWFpbmluZyArIFwiIHByb3ZpZGVyXCIgKyAocmVtYWluaW5nICE9PSAxID8gXCJzXCIgOiBcIlwiKSArIFwiIHN0aWxsIGxvYWRpbmcuLi5cIjtcbn1cblxuLyoqXG4gKiBTaG93IGEgd2FybmluZyBiYW5uZXIgZm9yIHJhdGUtbGltaXQgb3IgYXV0aGVudGljYXRpb24gZXJyb3JzLlxuICogU291cmNlOiBtYWluLmpzIHNob3dFbnJpY2hXYXJuaW5nKCkgKGxpbmVzIDYwNS02MTEpLlxuICovXG5mdW5jdGlvbiBzaG93RW5yaWNoV2FybmluZyhtZXNzYWdlOiBzdHJpbmcpOiB2b2lkIHtcbiAgY29uc3QgYmFubmVyID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJlbnJpY2gtd2FybmluZ1wiKTtcbiAgaWYgKCFiYW5uZXIpIHJldHVybjtcbiAgYmFubmVyLnN0eWxlLmRpc3BsYXkgPSBcImJsb2NrXCI7XG4gIC8vIFVzZSB0ZXh0Q29udGVudCB0byBzYWZlbHkgc2V0IHRoZSB3YXJuaW5nIG1lc3NhZ2UgKFNFQy0wOClcbiAgYmFubmVyLnRleHRDb250ZW50ID0gXCJXYXJuaW5nOiBcIiArIG1lc3NhZ2UgKyBcIiBDb25zaWRlciB1c2luZyBvZmZsaW5lIG1vZGUgb3IgY2hlY2tpbmcgeW91ciBBUEkga2V5IGluIFNldHRpbmdzLlwiO1xufVxuXG4vKipcbiAqIE1hcmsgZW5yaWNobWVudCBjb21wbGV0ZTogYWRkIC5jb21wbGV0ZSBjbGFzcyB0byBwcm9ncmVzcyBjb250YWluZXIsXG4gKiB1cGRhdGUgdGV4dCwgYW5kIGVuYWJsZSB0aGUgZXhwb3J0IGJ1dHRvbi5cbiAqIFNvdXJjZTogbWFpbi5qcyBtYXJrRW5yaWNobWVudENvbXBsZXRlKCkgKGxpbmVzIDU5MC02MDMpLlxuICovXG5mdW5jdGlvbiBtYXJrRW5yaWNobWVudENvbXBsZXRlKCk6IHZvaWQge1xuICBjb25zdCBjb250YWluZXIgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcImVucmljaC1wcm9ncmVzc1wiKTtcbiAgaWYgKGNvbnRhaW5lcikge1xuICAgIGNvbnRhaW5lci5jbGFzc0xpc3QuYWRkKFwiY29tcGxldGVcIik7XG4gIH1cbiAgY29uc3QgdGV4dCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZW5yaWNoLXByb2dyZXNzLXRleHRcIik7XG4gIGlmICh0ZXh0KSB7XG4gICAgdGV4dC50ZXh0Q29udGVudCA9IFwiRW5yaWNobWVudCBjb21wbGV0ZVwiO1xuICB9XG4gIGNvbnN0IGV4cG9ydEJ0biA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZXhwb3J0LWJ0blwiKTtcbiAgaWYgKGV4cG9ydEJ0bikge1xuICAgIGV4cG9ydEJ0bi5yZW1vdmVBdHRyaWJ1dGUoXCJkaXNhYmxlZFwiKTtcbiAgfVxuXG4gIC8vIFZJUy0wMyArIEdSUC0wMjogSW5qZWN0IHNlY3Rpb24gaGVhZGVycyBhbmQgbm8tZGF0YSBjb2xsYXBzZSBmb3IgYWxsIHNsb3RzXG4gIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGw8SFRNTEVsZW1lbnQ+KFwiLmVucmljaG1lbnQtc2xvdFwiKS5mb3JFYWNoKHNsb3QgPT4ge1xuICAgIGluamVjdFNlY3Rpb25IZWFkZXJzQW5kTm9EYXRhU3VtbWFyeShzbG90KTtcbiAgfSk7XG59XG5cbi8qKlxuICogUmVuZGVyIGEgc2luZ2xlIGVucmljaG1lbnQgcmVzdWx0IGl0ZW0gaW50byB0aGUgYXBwcm9wcmlhdGUgSU9DIGNhcmQgc2xvdC5cbiAqIEhhbmRsZXMgYm90aCBcInJlc3VsdFwiIGFuZCBcImVycm9yXCIgZGlzY3JpbWluYXRlZCB1bmlvbiBicmFuY2hlcy5cbiAqXG4gKiBOZXcgYmVoYXZpb3IgKFBsYW4gMDIpOlxuICogLSBBTEwgcmVzdWx0cyBnbyBpbnRvIC5lbnJpY2htZW50LWRldGFpbHMgY29udGFpbmVyIChubyBkaXJlY3Qgc2xvdCBhcHBlbmQpXG4gKiAtIFN1bW1hcnkgcm93IHVwZGF0ZWQgb24gZWFjaCByZXN1bHQ6IHdvcnN0IHZlcmRpY3QgYmFkZ2UgKyBhdHRyaWJ1dGlvbiArIGNvbnNlbnN1cyBiYWRnZVxuICogLSBEZXRhaWwgcm93cyBzb3J0ZWQgYnkgc2V2ZXJpdHkgZGVzY2VuZGluZyAoZGVib3VuY2VkIDEwMG1zKVxuICogLSAuZW5yaWNobWVudC1zbG90LS1sb2FkZWQgY2xhc3MgYWRkZWQgb24gZmlyc3QgcmVzdWx0IChyZXZlYWxzIGNoZXZyb24gdmlhIENTUylcbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgcmVuZGVyRW5yaWNobWVudFJlc3VsdCgpIChsaW5lcyA0NDMtNTQwKS5cbiAqL1xuZnVuY3Rpb24gcmVuZGVyRW5yaWNobWVudFJlc3VsdChcbiAgcmVzdWx0OiBFbnJpY2htZW50SXRlbSxcbiAgaW9jVmVyZGljdHM6IFJlY29yZDxzdHJpbmcsIFZlcmRpY3RFbnRyeVtdPixcbiAgaW9jUmVzdWx0Q291bnRzOiBSZWNvcmQ8c3RyaW5nLCBudW1iZXI+XG4pOiB2b2lkIHtcbiAgLy8gRmluZCB0aGUgY2FyZCBmb3IgdGhpcyBJT0MgdmFsdWVcbiAgY29uc3QgY2FyZCA9IGZpbmRDYXJkRm9ySW9jKHJlc3VsdC5pb2NfdmFsdWUpO1xuICBpZiAoIWNhcmQpIHJldHVybjtcblxuICBjb25zdCBzbG90ID0gY2FyZC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcIi5lbnJpY2htZW50LXNsb3RcIik7XG4gIGlmICghc2xvdCkgcmV0dXJuO1xuXG4gIC8vIENvbnRleHQgcHJvdmlkZXJzIChJUCBDb250ZXh0LCBETlMgUmVjb3JkcywgQ2VydCBIaXN0b3J5KSBhcmUgcHVyZWx5IGluZm9ybWF0aW9uYWwgXHUyMDE0XG4gIC8vIHNlcGFyYXRlIHJlbmRlcmluZyBwYXRoLiBObyBWZXJkaWN0RW50cnkgYWNjdW11bGF0aW9uLCBubyBjb25zZW5zdXMvYXR0cmlidXRpb24sXG4gIC8vIG5vIGNhcmQgdmVyZGljdCB1cGRhdGUuXG4gIGlmIChDT05URVhUX1BST1ZJREVSUy5oYXMocmVzdWx0LnByb3ZpZGVyKSkge1xuICAgIC8vIFJlbW92ZSBzcGlubmVyIG9uIGZpcnN0IHJlc3VsdFxuICAgIGNvbnN0IHNwaW5uZXJXcmFwcGVyID0gc2xvdC5xdWVyeVNlbGVjdG9yKFwiLnNwaW5uZXItd3JhcHBlclwiKTtcbiAgICBpZiAoc3Bpbm5lcldyYXBwZXIpIHNsb3QucmVtb3ZlQ2hpbGQoc3Bpbm5lcldyYXBwZXIpO1xuICAgIHNsb3QuY2xhc3NMaXN0LmFkZChcImVucmljaG1lbnQtc2xvdC0tbG9hZGVkXCIpO1xuXG4gICAgLy8gVHJhY2sgcmVzdWx0IGNvdW50IGZvciBwZW5kaW5nIGluZGljYXRvclxuICAgIGlvY1Jlc3VsdENvdW50c1tyZXN1bHQuaW9jX3ZhbHVlXSA9IChpb2NSZXN1bHRDb3VudHNbcmVzdWx0LmlvY192YWx1ZV0gPz8gMCkgKyAxO1xuXG4gICAgLy8gUmVuZGVyIGNvbnRleHQgcm93IGFuZCBhcHBlbmQgdG8gY29udGV4dCBzZWN0aW9uIGNvbnRhaW5lclxuICAgIGNvbnN0IGNvbnRleHRTZWN0aW9uID0gc2xvdC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcIi5lbnJpY2htZW50LXNlY3Rpb24tLWNvbnRleHRcIik7XG4gICAgaWYgKGNvbnRleHRTZWN0aW9uICYmIHJlc3VsdC50eXBlID09PSBcInJlc3VsdFwiKSB7XG4gICAgICBjb25zdCBjb250ZXh0Um93ID0gY3JlYXRlQ29udGV4dFJvdyhyZXN1bHQpO1xuICAgICAgY29udGV4dFNlY3Rpb24uYXBwZW5kQ2hpbGQoY29udGV4dFJvdyk7XG5cbiAgICAgIC8vIFBvcHVsYXRlIGlubGluZSBjb250ZXh0IGxpbmUgaW4gY2FyZCBoZWFkZXIgKENUWC0wMSlcbiAgICAgIHVwZGF0ZUNvbnRleHRMaW5lKGNhcmQsIHJlc3VsdCk7XG4gICAgfVxuXG4gICAgLy8gVXBkYXRlIHBlbmRpbmcgaW5kaWNhdG9yXG4gICAgdXBkYXRlUGVuZGluZ0luZGljYXRvcihzbG90LCBjYXJkLCBpb2NSZXN1bHRDb3VudHNbcmVzdWx0LmlvY192YWx1ZV0gPz8gMSk7XG4gICAgcmV0dXJuOyAvLyBTa2lwIGFsbCB2ZXJkaWN0L3N1bW1hcnkvc29ydC9kYXNoYm9hcmQgbG9naWNcbiAgfVxuXG4gIC8vIFJlbW92ZSBzcGlubmVyIHdyYXBwZXIgb24gZmlyc3QgcmVzdWx0IGZvciB0aGlzIElPQ1xuICBjb25zdCBzcGlubmVyV3JhcHBlciA9IHNsb3QucXVlcnlTZWxlY3RvcihcIi5zcGlubmVyLXdyYXBwZXJcIik7XG4gIGlmIChzcGlubmVyV3JhcHBlcikge1xuICAgIHNsb3QucmVtb3ZlQ2hpbGQoc3Bpbm5lcldyYXBwZXIpO1xuICB9XG5cbiAgLy8gQWRkIC5lbnJpY2htZW50LXNsb3QtLWxvYWRlZCBjbGFzcyBcdTIwMTQgdHJpZ2dlcnMgY2hldnJvbiB2aXNpYmlsaXR5IHZpYSBDU1MgZ3VhcmRcbiAgc2xvdC5jbGFzc0xpc3QuYWRkKFwiZW5yaWNobWVudC1zbG90LS1sb2FkZWRcIik7XG5cbiAgLy8gVHJhY2sgcmVjZWl2ZWQgY291bnQgZm9yIHRoaXMgSU9DXG4gIGlvY1Jlc3VsdENvdW50c1tyZXN1bHQuaW9jX3ZhbHVlXSA9IChpb2NSZXN1bHRDb3VudHNbcmVzdWx0LmlvY192YWx1ZV0gPz8gMCkgKyAxO1xuICBjb25zdCByZWNlaXZlZENvdW50ID0gaW9jUmVzdWx0Q291bnRzW3Jlc3VsdC5pb2NfdmFsdWVdID8/IDE7XG5cbiAgLy8gRGV0ZXJtaW5lIHZlcmRpY3QgYW5kIHN0YXRUZXh0XG4gIGxldCB2ZXJkaWN0OiBWZXJkaWN0S2V5O1xuICBsZXQgc3RhdFRleHQ6IHN0cmluZztcbiAgbGV0IHN1bW1hcnlUZXh0OiBzdHJpbmc7XG4gIGxldCBkZXRlY3Rpb25Db3VudCA9IDA7XG4gIGxldCB0b3RhbEVuZ2luZXMgPSAwO1xuXG4gIGlmIChyZXN1bHQudHlwZSA9PT0gXCJyZXN1bHRcIikge1xuICAgIHZlcmRpY3QgPSByZXN1bHQudmVyZGljdDtcbiAgICBkZXRlY3Rpb25Db3VudCA9IHJlc3VsdC5kZXRlY3Rpb25fY291bnQ7XG4gICAgdG90YWxFbmdpbmVzID0gcmVzdWx0LnRvdGFsX2VuZ2luZXM7XG5cbiAgICBpZiAodmVyZGljdCA9PT0gXCJtYWxpY2lvdXNcIikge1xuICAgICAgc3RhdFRleHQgPSByZXN1bHQuZGV0ZWN0aW9uX2NvdW50ICsgXCIvXCIgKyByZXN1bHQudG90YWxfZW5naW5lcyArIFwiIGVuZ2luZXNcIjtcbiAgICB9IGVsc2UgaWYgKHZlcmRpY3QgPT09IFwic3VzcGljaW91c1wiKSB7XG4gICAgICBzdGF0VGV4dCA9XG4gICAgICAgIHJlc3VsdC50b3RhbF9lbmdpbmVzID4gMVxuICAgICAgICAgID8gcmVzdWx0LmRldGVjdGlvbl9jb3VudCArIFwiL1wiICsgcmVzdWx0LnRvdGFsX2VuZ2luZXMgKyBcIiBlbmdpbmVzXCJcbiAgICAgICAgICA6IFwiU3VzcGljaW91c1wiO1xuICAgIH0gZWxzZSBpZiAodmVyZGljdCA9PT0gXCJjbGVhblwiKSB7XG4gICAgICBzdGF0VGV4dCA9IFwiQ2xlYW4sIFwiICsgcmVzdWx0LnRvdGFsX2VuZ2luZXMgKyBcIiBlbmdpbmVzXCI7XG4gICAgfSBlbHNlIGlmICh2ZXJkaWN0ID09PSBcImtub3duX2dvb2RcIikge1xuICAgICAgc3RhdFRleHQgPSBcIk5TUkwgbWF0Y2hcIjtcbiAgICB9IGVsc2Uge1xuICAgICAgLy8gbm9fZGF0YVxuICAgICAgc3RhdFRleHQgPSBcIk5vdCBpbiBkYXRhYmFzZVwiO1xuICAgIH1cblxuICAgIGNvbnN0IHNjYW5EYXRlU3RyID0gZm9ybWF0RGF0ZShyZXN1bHQuc2Nhbl9kYXRlKTtcbiAgICBzdW1tYXJ5VGV4dCA9XG4gICAgICByZXN1bHQucHJvdmlkZXIgK1xuICAgICAgXCI6IFwiICtcbiAgICAgIHZlcmRpY3QgK1xuICAgICAgXCIgKFwiICtcbiAgICAgIHN0YXRUZXh0ICtcbiAgICAgIChzY2FuRGF0ZVN0ciA/IFwiLCBzY2FubmVkIFwiICsgc2NhbkRhdGVTdHIgOiBcIlwiKSArXG4gICAgICBcIilcIjtcbiAgfSBlbHNlIHtcbiAgICAvLyBFcnJvciByZXN1bHRcbiAgICB2ZXJkaWN0ID0gXCJlcnJvclwiO1xuICAgIHN0YXRUZXh0ID0gcmVzdWx0LmVycm9yO1xuICAgIHN1bW1hcnlUZXh0ID0gcmVzdWx0LnByb3ZpZGVyICsgXCI6IGVycm9yLCBcIiArIHJlc3VsdC5lcnJvcjtcbiAgfVxuXG4gIC8vIFB1c2ggdG8gaW9jVmVyZGljdHMgd2l0aCBleHRlbmRlZCBmaWVsZHNcbiAgY29uc3QgZW50cmllcyA9IGlvY1ZlcmRpY3RzW3Jlc3VsdC5pb2NfdmFsdWVdID8/IFtdO1xuICBpb2NWZXJkaWN0c1tyZXN1bHQuaW9jX3ZhbHVlXSA9IGVudHJpZXM7XG4gIGVudHJpZXMucHVzaCh7IHByb3ZpZGVyOiByZXN1bHQucHJvdmlkZXIsIHZlcmRpY3QsIHN1bW1hcnlUZXh0LCBkZXRlY3Rpb25Db3VudCwgdG90YWxFbmdpbmVzLCBzdGF0VGV4dCB9KTtcblxuICAvLyBCdWlsZCBkZXRhaWwgcm93IGFuZCByb3V0ZSB0byBjb3JyZWN0IHNlY3Rpb24gY29udGFpbmVyXG4gIGNvbnN0IGlzTm9EYXRhID0gdmVyZGljdCA9PT0gXCJub19kYXRhXCIgfHwgdmVyZGljdCA9PT0gXCJlcnJvclwiO1xuICBjb25zdCBzZWN0aW9uU2VsZWN0b3IgPSBpc05vRGF0YVxuICAgID8gXCIuZW5yaWNobWVudC1zZWN0aW9uLS1uby1kYXRhXCJcbiAgICA6IFwiLmVucmljaG1lbnQtc2VjdGlvbi0tcmVwdXRhdGlvblwiO1xuICBjb25zdCBzZWN0aW9uQ29udGFpbmVyID0gc2xvdC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihzZWN0aW9uU2VsZWN0b3IpO1xuICBpZiAoc2VjdGlvbkNvbnRhaW5lcikge1xuICAgIGNvbnN0IGRldGFpbFJvdyA9IGNyZWF0ZURldGFpbFJvdyhyZXN1bHQucHJvdmlkZXIsIHZlcmRpY3QsIHN0YXRUZXh0LCByZXN1bHQpO1xuICAgIHNlY3Rpb25Db250YWluZXIuYXBwZW5kQ2hpbGQoZGV0YWlsUm93KTtcbiAgICAvLyBTb3J0IG9ubHkgcmVwdXRhdGlvbiByb3dzIChuby1kYXRhIHJvd3MgZG9uJ3QgbmVlZCBzZXZlcml0eSBzb3J0aW5nKVxuICAgIGlmICghaXNOb0RhdGEpIHtcbiAgICAgIHNvcnREZXRhaWxSb3dzKHNlY3Rpb25Db250YWluZXIsIHJlc3VsdC5pb2NfdmFsdWUpO1xuICAgIH1cbiAgfVxuXG4gIC8vIFVwZGF0ZSBzdW1tYXJ5IHJvdyAod29yc3QgdmVyZGljdCArIGF0dHJpYnV0aW9uICsgY29uc2Vuc3VzKVxuICB1cGRhdGVTdW1tYXJ5Um93KHNsb3QsIHJlc3VsdC5pb2NfdmFsdWUsIGlvY1ZlcmRpY3RzKTtcblxuICAvLyBVcGRhdGUgcGVuZGluZyBpbmRpY2F0b3IgZm9yIHJlbWFpbmluZyBwcm92aWRlcnNcbiAgdXBkYXRlUGVuZGluZ0luZGljYXRvcihzbG90LCBjYXJkLCByZWNlaXZlZENvdW50KTtcblxuICAvLyBDb21wdXRlIHdvcnN0IHZlcmRpY3QgZm9yIHRoaXMgSU9DXG4gIGNvbnN0IHdvcnN0VmVyZGljdCA9IGNvbXB1dGVXb3JzdFZlcmRpY3QoaW9jVmVyZGljdHNbcmVzdWx0LmlvY192YWx1ZV0gPz8gW10pO1xuXG4gIC8vIFVwZGF0ZSBjYXJkIHZlcmRpY3QsIGRhc2hib2FyZCwgYW5kIHNvcnRcbiAgdXBkYXRlQ2FyZFZlcmRpY3QocmVzdWx0LmlvY192YWx1ZSwgd29yc3RWZXJkaWN0KTtcbiAgdXBkYXRlRGFzaGJvYXJkQ291bnRzKCk7XG4gIHNvcnRDYXJkc0J5U2V2ZXJpdHkoKTtcblxuICAvLyBVcGRhdGUgY29weSBidXR0b24gd2l0aCB3b3JzdCB2ZXJkaWN0IGFjcm9zcyBhbGwgcHJvdmlkZXJzIGZvciB0aGlzIElPQ1xuICB1cGRhdGVDb3B5QnV0dG9uV29yc3RWZXJkaWN0KHJlc3VsdC5pb2NfdmFsdWUsIGlvY1ZlcmRpY3RzKTtcbn1cblxuLyoqXG4gKiBXaXJlIGV4cGFuZC9jb2xsYXBzZSB0b2dnbGUgZm9yIGFsbCAuY2hldnJvbi10b2dnbGUgYnV0dG9ucyBvbiB0aGUgcGFnZS5cbiAqIENhbGxlZCBvbmNlIGZyb20gaW5pdCgpLiBDbGljayBsaXN0ZW5lciB0b2dnbGVzIC5pcy1vcGVuIG9uIHRoZSBzaWJsaW5nXG4gKiAuZW5yaWNobWVudC1kZXRhaWxzIGNvbnRhaW5lciBhbmQgc2V0cyBhcmlhLWV4cGFuZGVkIGFjY29yZGluZ2x5LlxuICogTXVsdGlwbGUgY2FyZHMgY2FuIGJlIGluZGVwZW5kZW50bHkgb3BlbmVkIFx1MjAxNCBubyBjb2xsYXBzZS1vdGhlcnMgbG9naWMuXG4gKi9cbmZ1bmN0aW9uIHdpcmVFeHBhbmRUb2dnbGVzKCk6IHZvaWQge1xuICBjb25zdCB0b2dnbGVzID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuY2hldnJvbi10b2dnbGVcIik7XG4gIHRvZ2dsZXMuZm9yRWFjaCgodG9nZ2xlKSA9PiB7XG4gICAgdG9nZ2xlLmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCAoKSA9PiB7XG4gICAgICBjb25zdCBkZXRhaWxzID0gdG9nZ2xlLm5leHRFbGVtZW50U2libGluZyBhcyBIVE1MRWxlbWVudCB8IG51bGw7XG4gICAgICBpZiAoIWRldGFpbHMgfHwgIWRldGFpbHMuY2xhc3NMaXN0LmNvbnRhaW5zKFwiZW5yaWNobWVudC1kZXRhaWxzXCIpKSByZXR1cm47XG4gICAgICBjb25zdCBpc09wZW4gPSBkZXRhaWxzLmNsYXNzTGlzdC50b2dnbGUoXCJpcy1vcGVuXCIpO1xuICAgICAgdG9nZ2xlLmNsYXNzTGlzdC50b2dnbGUoXCJpcy1vcGVuXCIsIGlzT3Blbik7XG4gICAgICB0b2dnbGUuc2V0QXR0cmlidXRlKFwiYXJpYS1leHBhbmRlZFwiLCBTdHJpbmcoaXNPcGVuKSk7XG4gICAgfSk7XG4gIH0pO1xufVxuXG4vLyAtLS0tIFByaXZhdGUgaW5pdCBoZWxwZXJzIC0tLS1cblxuLyoqXG4gKiBXaXJlIHRoZSBleHBvcnQgZHJvcGRvd24gd2l0aCBKU09OLCBDU1YsIGFuZCBjb3B5LWFsbC1JT0NzIG9wdGlvbnMuXG4gKi9cbmZ1bmN0aW9uIGluaXRFeHBvcnRCdXR0b24oKTogdm9pZCB7XG4gIGNvbnN0IGV4cG9ydEJ0biA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwiZXhwb3J0LWJ0blwiKTtcbiAgY29uc3QgZHJvcGRvd24gPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcImV4cG9ydC1kcm9wZG93blwiKTtcbiAgaWYgKCFleHBvcnRCdG4gfHwgIWRyb3Bkb3duKSByZXR1cm47XG5cbiAgZXhwb3J0QnRuLmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCBmdW5jdGlvbiAoKSB7XG4gICAgY29uc3QgaXNWaXNpYmxlID0gZHJvcGRvd24uc3R5bGUuZGlzcGxheSAhPT0gXCJub25lXCI7XG4gICAgZHJvcGRvd24uc3R5bGUuZGlzcGxheSA9IGlzVmlzaWJsZSA/IFwibm9uZVwiIDogXCJcIjtcbiAgfSk7XG5cbiAgLy8gQ2xvc2UgZHJvcGRvd24gd2hlbiBjbGlja2luZyBvdXRzaWRlXG4gIGRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCBmdW5jdGlvbiAoZSkge1xuICAgIGNvbnN0IHRhcmdldCA9IGUudGFyZ2V0IGFzIEhUTUxFbGVtZW50O1xuICAgIGlmICghdGFyZ2V0LmNsb3Nlc3QoXCIuZXhwb3J0LWdyb3VwXCIpKSB7XG4gICAgICBkcm9wZG93bi5zdHlsZS5kaXNwbGF5ID0gXCJub25lXCI7XG4gICAgfVxuICB9KTtcblxuICBjb25zdCBidXR0b25zID0gZHJvcGRvd24ucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCJbZGF0YS1leHBvcnRdXCIpO1xuICBidXR0b25zLmZvckVhY2goZnVuY3Rpb24gKGJ0bikge1xuICAgIGJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgZnVuY3Rpb24gKCkge1xuICAgICAgY29uc3QgYWN0aW9uID0gYnRuLmdldEF0dHJpYnV0ZShcImRhdGEtZXhwb3J0XCIpO1xuICAgICAgaWYgKGFjdGlvbiA9PT0gXCJqc29uXCIpIHtcbiAgICAgICAgZXhwb3J0SlNPTihhbGxSZXN1bHRzKTtcbiAgICAgIH0gZWxzZSBpZiAoYWN0aW9uID09PSBcImNzdlwiKSB7XG4gICAgICAgIGV4cG9ydENTVihhbGxSZXN1bHRzKTtcbiAgICAgIH0gZWxzZSBpZiAoYWN0aW9uID09PSBcImlvY3NcIikge1xuICAgICAgICBjb3B5QWxsSU9DcyhidG4pO1xuICAgICAgfVxuICAgICAgZHJvcGRvd24uc3R5bGUuZGlzcGxheSA9IFwibm9uZVwiO1xuICAgIH0pO1xuICB9KTtcbn1cblxuLy8gLS0tLSBQdWJsaWMgQVBJIC0tLS1cblxuLyoqXG4gKiBJbml0aWFsaXNlIHRoZSBlbnJpY2htZW50IHBvbGxpbmcgbW9kdWxlLlxuICpcbiAqIEd1YXJkcyBvbiAucGFnZS1yZXN1bHRzIHByZXNlbmNlIGFuZCBkYXRhLW1vZGU9XCJvbmxpbmVcIiBcdTIwMTQgcmV0dXJucyBlYXJseVxuICogb24gb2ZmbGluZSBtb2RlIG9yIHdoZW4gZW5yaWNobWVudCBVSSBlbGVtZW50cyBhcmUgYWJzZW50LlxuICpcbiAqIFdpcmVzIGNoZXZyb24gZXhwYW5kL2NvbGxhcHNlIHRvZ2dsZXMgb25jZSBhdCBpbml0IHRpbWUgKGJlZm9yZSBwb2xsaW5nXG4gKiBzdGFydHMpIHNvIHRoZXkgd29yayByZWdhcmRsZXNzIG9mIHdoZW4gcmVzdWx0cyBwb3B1bGF0ZSBkZXRhaWxzLlxuICpcbiAqIFN0YXJ0cyBhIDc1MG1zIHBvbGxpbmcgaW50ZXJ2YWwgZm9yIC9lbnJpY2htZW50L3N0YXR1cy88am9iX2lkPixcbiAqIHJlbmRlcnMgaW5jcmVtZW50YWwgcmVzdWx0cywgc2hvd3Mgd2FybmluZyBiYW5uZXJzIGZvciBlcnJvcnMsIGFuZFxuICogbWFya3MgZW5yaWNobWVudCBjb21wbGV0ZSB3aGVuIGFsbCB0YXNrcyBhcmUgZG9uZS5cbiAqXG4gKiBTb3VyY2U6IG1haW4uanMgaW5pdEVucmljaG1lbnRQb2xsaW5nKCkgKGxpbmVzIDMxNi0zNzMpICtcbiAqICAgICAgICAgaW5pdEV4cG9ydEJ1dHRvbigpIChsaW5lcyA2MTUtNjQzKS5cbiAqL1xuZXhwb3J0IGZ1bmN0aW9uIGluaXQoKTogdm9pZCB7XG4gIGNvbnN0IHBhZ2VSZXN1bHRzID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcjxIVE1MRWxlbWVudD4oXCIucGFnZS1yZXN1bHRzXCIpO1xuICBpZiAoIXBhZ2VSZXN1bHRzKSByZXR1cm47XG5cbiAgY29uc3Qgam9iSWQgPSBhdHRyKHBhZ2VSZXN1bHRzLCBcImRhdGEtam9iLWlkXCIpO1xuICBjb25zdCBtb2RlID0gYXR0cihwYWdlUmVzdWx0cywgXCJkYXRhLW1vZGVcIik7XG5cbiAgaWYgKCFqb2JJZCB8fCBtb2RlICE9PSBcIm9ubGluZVwiKSByZXR1cm47XG5cbiAgLy8gV2lyZSBleHBhbmQvY29sbGFwc2UgdG9nZ2xlcyBvbmNlIGF0IGluaXQgKGJlZm9yZSBwb2xsaW5nIHN0YXJ0cylcbiAgd2lyZUV4cGFuZFRvZ2dsZXMoKTtcblxuICAvLyBEZWR1cCBrZXk6IFwiaW9jX3ZhbHVlfHByb3ZpZGVyXCIgXHUyMDE0IGVhY2ggcHJvdmlkZXIgcmVzdWx0IHBlciBJT0MgcmVuZGVyZWQgb25jZVxuICBjb25zdCByZW5kZXJlZDogUmVjb3JkPHN0cmluZywgYm9vbGVhbj4gPSB7fTtcblxuICAvLyBQZXItSU9DIHZlcmRpY3QgdHJhY2tpbmcgZm9yIHdvcnN0LXZlcmRpY3QgY29weS9leHBvcnQgY29tcHV0YXRpb25cbiAgLy8gaW9jVmVyZGljdHNbaW9jX3ZhbHVlXSA9IFt7cHJvdmlkZXIsIHZlcmRpY3QsIHN1bW1hcnlUZXh0LCBkZXRlY3Rpb25Db3VudCwgdG90YWxFbmdpbmVzLCBzdGF0VGV4dH1dXG4gIGNvbnN0IGlvY1ZlcmRpY3RzOiBSZWNvcmQ8c3RyaW5nLCBWZXJkaWN0RW50cnlbXT4gPSB7fTtcblxuICAvLyBQZXItSU9DIHJlc3VsdCBjb3VudCB0cmFja2luZyBmb3IgcGVuZGluZyBpbmRpY2F0b3JcbiAgY29uc3QgaW9jUmVzdWx0Q291bnRzOiBSZWNvcmQ8c3RyaW5nLCBudW1iZXI+ID0ge307XG5cbiAgLy8gVXNlIFJldHVyblR5cGU8dHlwZW9mIHNldEludGVydmFsPiB0byBhdm9pZCBOb2RlSlMuVGltZW91dCBjb25mbGljdFxuICBjb25zdCBpbnRlcnZhbElkOiBSZXR1cm5UeXBlPHR5cGVvZiBzZXRJbnRlcnZhbD4gPSBzZXRJbnRlcnZhbChmdW5jdGlvbiAoKSB7XG4gICAgZmV0Y2goXCIvZW5yaWNobWVudC9zdGF0dXMvXCIgKyBqb2JJZClcbiAgICAgIC50aGVuKGZ1bmN0aW9uIChyZXNwKSB7XG4gICAgICAgIGlmICghcmVzcC5vaykgcmV0dXJuIG51bGw7XG4gICAgICAgIHJldHVybiByZXNwLmpzb24oKSBhcyBQcm9taXNlPEVucmljaG1lbnRTdGF0dXM+O1xuICAgICAgfSlcbiAgICAgIC50aGVuKGZ1bmN0aW9uIChkYXRhKSB7XG4gICAgICAgIGlmICghZGF0YSkgcmV0dXJuO1xuXG4gICAgICAgIHVwZGF0ZVByb2dyZXNzQmFyKGRhdGEuZG9uZSwgZGF0YS50b3RhbCk7XG5cbiAgICAgICAgLy8gUmVuZGVyIGFueSBuZXcgcmVzdWx0cyBub3QgeWV0IGRpc3BsYXllZCwgYW5kIGNoZWNrIGZvciB3YXJuaW5nc1xuICAgICAgICBjb25zdCByZXN1bHRzID0gZGF0YS5yZXN1bHRzO1xuICAgICAgICBmb3IgKGxldCBpID0gMDsgaSA8IHJlc3VsdHMubGVuZ3RoOyBpKyspIHtcbiAgICAgICAgICBjb25zdCByZXN1bHQgPSByZXN1bHRzW2ldO1xuICAgICAgICAgIGlmICghcmVzdWx0KSBjb250aW51ZTtcbiAgICAgICAgICBjb25zdCBkZWR1cEtleSA9IHJlc3VsdC5pb2NfdmFsdWUgKyBcInxcIiArIHJlc3VsdC5wcm92aWRlcjtcbiAgICAgICAgICBpZiAoIXJlbmRlcmVkW2RlZHVwS2V5XSkge1xuICAgICAgICAgICAgcmVuZGVyZWRbZGVkdXBLZXldID0gdHJ1ZTtcbiAgICAgICAgICAgIGFsbFJlc3VsdHMucHVzaChyZXN1bHQpO1xuICAgICAgICAgICAgcmVuZGVyRW5yaWNobWVudFJlc3VsdChyZXN1bHQsIGlvY1ZlcmRpY3RzLCBpb2NSZXN1bHRDb3VudHMpO1xuICAgICAgICAgIH1cblxuICAgICAgICAgIC8vIFNob3cgd2FybmluZyBiYW5uZXIgZm9yIHJhdGUtbGltaXQgb3IgYXV0aCBlcnJvcnNcbiAgICAgICAgICBpZiAocmVzdWx0LnR5cGUgPT09IFwiZXJyb3JcIiAmJiByZXN1bHQuZXJyb3IpIHtcbiAgICAgICAgICAgIGNvbnN0IGVyckxvd2VyID0gcmVzdWx0LmVycm9yLnRvTG93ZXJDYXNlKCk7XG4gICAgICAgICAgICBpZiAoXG4gICAgICAgICAgICAgIGVyckxvd2VyLmluZGV4T2YoXCJyYXRlIGxpbWl0XCIpICE9PSAtMSB8fFxuICAgICAgICAgICAgICBlcnJMb3dlci5pbmRleE9mKFwiNDI5XCIpICE9PSAtMVxuICAgICAgICAgICAgKSB7XG4gICAgICAgICAgICAgIHNob3dFbnJpY2hXYXJuaW5nKFwiUmF0ZSBsaW1pdCByZWFjaGVkIGZvciBcIiArIHJlc3VsdC5wcm92aWRlciArIFwiLlwiKTtcbiAgICAgICAgICAgIH0gZWxzZSBpZiAoXG4gICAgICAgICAgICAgIGVyckxvd2VyLmluZGV4T2YoXCJhdXRoZW50aWNhdGlvblwiKSAhPT0gLTEgfHxcbiAgICAgICAgICAgICAgZXJyTG93ZXIuaW5kZXhPZihcIjQwMVwiKSAhPT0gLTEgfHxcbiAgICAgICAgICAgICAgZXJyTG93ZXIuaW5kZXhPZihcIjQwM1wiKSAhPT0gLTFcbiAgICAgICAgICAgICkge1xuICAgICAgICAgICAgICBzaG93RW5yaWNoV2FybmluZyhcbiAgICAgICAgICAgICAgICBcIkF1dGhlbnRpY2F0aW9uIGVycm9yIGZvciBcIiArXG4gICAgICAgICAgICAgICAgICByZXN1bHQucHJvdmlkZXIgK1xuICAgICAgICAgICAgICAgICAgXCIuIFBsZWFzZSBjaGVjayB5b3VyIEFQSSBrZXkgaW4gU2V0dGluZ3MuXCJcbiAgICAgICAgICAgICAgKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9XG4gICAgICAgIH1cblxuICAgICAgICBpZiAoZGF0YS5jb21wbGV0ZSkge1xuICAgICAgICAgIGNsZWFySW50ZXJ2YWwoaW50ZXJ2YWxJZCk7XG4gICAgICAgICAgbWFya0VucmljaG1lbnRDb21wbGV0ZSgpO1xuICAgICAgICB9XG4gICAgICB9KVxuICAgICAgLmNhdGNoKGZ1bmN0aW9uICgpIHtcbiAgICAgICAgLy8gRmV0Y2ggZXJyb3IgXHUyMDE0IHNpbGVudGx5IGNvbnRpbnVlOyByZXRyeSBvbiBuZXh0IGludGVydmFsIHRpY2tcbiAgICAgIH0pO1xuICB9LCA3NTApO1xuXG4gIC8vIFdpcmUgdGhlIGV4cG9ydCBidXR0b25cbiAgaW5pdEV4cG9ydEJ1dHRvbigpO1xufVxuIiwgIi8qKlxuICogU2V0dGluZ3MgcGFnZSBtb2R1bGUgXHUyMDE0IGFjY29yZGlvbiBhbmQgQVBJIGtleSB0b2dnbGVzLlxuICovXG5cbi8qKiBXaXJlIHVwIGFjY29yZGlvbiBzZWN0aW9ucyBcdTIwMTQgb25lIG9wZW4gYXQgYSB0aW1lLiAqL1xuZnVuY3Rpb24gaW5pdEFjY29yZGlvbigpOiB2b2lkIHtcbiAgY29uc3Qgc2VjdGlvbnMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsPEhUTUxFbGVtZW50PihcbiAgICBcIi5zZXR0aW5ncy1zZWN0aW9uW2RhdGEtcHJvdmlkZXJdXCJcbiAgKTtcbiAgaWYgKHNlY3Rpb25zLmxlbmd0aCA9PT0gMCkgcmV0dXJuO1xuXG4gIGZ1bmN0aW9uIGV4cGFuZFNlY3Rpb24oc2VjdGlvbjogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgICBzZWN0aW9ucy5mb3JFYWNoKChzKSA9PiB7XG4gICAgICBpZiAocyAhPT0gc2VjdGlvbikge1xuICAgICAgICBzLnJlbW92ZUF0dHJpYnV0ZShcImRhdGEtZXhwYW5kZWRcIik7XG4gICAgICAgIGNvbnN0IGJ0biA9IHMucXVlcnlTZWxlY3RvcihcIi5hY2NvcmRpb24taGVhZGVyXCIpO1xuICAgICAgICBpZiAoYnRuKSBidG4uc2V0QXR0cmlidXRlKFwiYXJpYS1leHBhbmRlZFwiLCBcImZhbHNlXCIpO1xuICAgICAgfVxuICAgIH0pO1xuICAgIHNlY3Rpb24uc2V0QXR0cmlidXRlKFwiZGF0YS1leHBhbmRlZFwiLCBcIlwiKTtcbiAgICBjb25zdCBidG4gPSBzZWN0aW9uLnF1ZXJ5U2VsZWN0b3IoXCIuYWNjb3JkaW9uLWhlYWRlclwiKTtcbiAgICBpZiAoYnRuKSBidG4uc2V0QXR0cmlidXRlKFwiYXJpYS1leHBhbmRlZFwiLCBcInRydWVcIik7XG4gIH1cblxuICBzZWN0aW9ucy5mb3JFYWNoKChzZWN0aW9uKSA9PiB7XG4gICAgY29uc3QgaGVhZGVyID0gc2VjdGlvbi5xdWVyeVNlbGVjdG9yKFwiLmFjY29yZGlvbi1oZWFkZXJcIik7XG4gICAgaWYgKCFoZWFkZXIpIHJldHVybjtcbiAgICBoZWFkZXIuYWRkRXZlbnRMaXN0ZW5lcihcImNsaWNrXCIsICgpID0+IHtcbiAgICAgIGlmIChzZWN0aW9uLmhhc0F0dHJpYnV0ZShcImRhdGEtZXhwYW5kZWRcIikpIHtcbiAgICAgICAgc2VjdGlvbi5yZW1vdmVBdHRyaWJ1dGUoXCJkYXRhLWV4cGFuZGVkXCIpO1xuICAgICAgICBoZWFkZXIuc2V0QXR0cmlidXRlKFwiYXJpYS1leHBhbmRlZFwiLCBcImZhbHNlXCIpO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgZXhwYW5kU2VjdGlvbihzZWN0aW9uKTtcbiAgICAgIH1cbiAgICB9KTtcbiAgfSk7XG5cbn1cblxuLyoqIFdpcmUgdXAgcGVyLXByb3ZpZGVyIEFQSSBrZXkgc2hvdy9oaWRlIHRvZ2dsZXMuICovXG5mdW5jdGlvbiBpbml0S2V5VG9nZ2xlcygpOiB2b2lkIHtcbiAgY29uc3Qgc2VjdGlvbnMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKFwiLnNldHRpbmdzLXNlY3Rpb25cIik7XG4gIHNlY3Rpb25zLmZvckVhY2goKHNlY3Rpb24pID0+IHtcbiAgICBjb25zdCBidG4gPSBzZWN0aW9uLnF1ZXJ5U2VsZWN0b3IoXG4gICAgICBcIltkYXRhLXJvbGU9J3RvZ2dsZS1rZXknXVwiXG4gICAgKSBhcyBIVE1MQnV0dG9uRWxlbWVudCB8IG51bGw7XG4gICAgY29uc3QgaW5wdXQgPSBzZWN0aW9uLnF1ZXJ5U2VsZWN0b3IoXG4gICAgICBcImlucHV0W3R5cGU9J3Bhc3N3b3JkJ10sIGlucHV0W3R5cGU9J3RleHQnXVwiXG4gICAgKSBhcyBIVE1MSW5wdXRFbGVtZW50IHwgbnVsbDtcbiAgICBpZiAoIWJ0biB8fCAhaW5wdXQpIHJldHVybjtcblxuICAgIGJ0bi5hZGRFdmVudExpc3RlbmVyKFwiY2xpY2tcIiwgKCkgPT4ge1xuICAgICAgaWYgKGlucHV0LnR5cGUgPT09IFwicGFzc3dvcmRcIikge1xuICAgICAgICBpbnB1dC50eXBlID0gXCJ0ZXh0XCI7XG4gICAgICAgIGJ0bi50ZXh0Q29udGVudCA9IFwiSGlkZVwiO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgaW5wdXQudHlwZSA9IFwicGFzc3dvcmRcIjtcbiAgICAgICAgYnRuLnRleHRDb250ZW50ID0gXCJTaG93XCI7XG4gICAgICB9XG4gICAgfSk7XG4gIH0pO1xufVxuXG5leHBvcnQgZnVuY3Rpb24gaW5pdCgpOiB2b2lkIHtcbiAgaW5pdEFjY29yZGlvbigpO1xuICBpbml0S2V5VG9nZ2xlcygpO1xufVxuIiwgIi8qKlxuICogVUkgdXRpbGl0aWVzIG1vZHVsZSBcdTIwMTQgc2Nyb2xsLWF3YXJlIGZpbHRlciBiYXIgYW5kIGNhcmQgc3RhZ2dlciBhbmltYXRpb24uXG4gKlxuICogRXh0cmFjdGVkIGZyb20gbWFpbi5qcyBpbml0U2Nyb2xsQXdhcmVGaWx0ZXJCYXIoKSAobGluZXMgODExLTgyNilcbiAqIGFuZCBpbml0Q2FyZFN0YWdnZXIoKSAobGluZXMgODMwLTgzNSkuXG4gKi9cblxuLyoqXG4gKiBBZGQgc2Nyb2xsIGxpc3RlbmVyIHRoYXQgdG9nZ2xlcyBcImlzLXNjcm9sbGVkXCIgY2xhc3Mgb24gLmZpbHRlci1iYXItd3JhcHBlclxuICogb25jZSB0aGUgcGFnZSBzY3JvbGxzIHBhc3QgNDBweC5cbiAqL1xuZnVuY3Rpb24gaW5pdFNjcm9sbEF3YXJlRmlsdGVyQmFyKCk6IHZvaWQge1xuICBjb25zdCBmaWx0ZXJCYXIgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yPEhUTUxFbGVtZW50PihcIi5maWx0ZXItYmFyLXdyYXBwZXJcIik7XG4gIGlmICghZmlsdGVyQmFyKSByZXR1cm47XG5cbiAgbGV0IHNjcm9sbGVkID0gZmFsc2U7XG4gIHdpbmRvdy5hZGRFdmVudExpc3RlbmVyKFxuICAgIFwic2Nyb2xsXCIsXG4gICAgZnVuY3Rpb24gKCkge1xuICAgICAgY29uc3QgaXNTY3JvbGxlZCA9IHdpbmRvdy5zY3JvbGxZID4gNDA7XG4gICAgICBpZiAoaXNTY3JvbGxlZCAhPT0gc2Nyb2xsZWQpIHtcbiAgICAgICAgc2Nyb2xsZWQgPSBpc1Njcm9sbGVkO1xuICAgICAgICBmaWx0ZXJCYXIuY2xhc3NMaXN0LnRvZ2dsZShcImlzLXNjcm9sbGVkXCIsIHNjcm9sbGVkKTtcbiAgICAgIH1cbiAgICB9LFxuICAgIHsgcGFzc2l2ZTogdHJ1ZSB9XG4gICk7XG59XG5cbi8qKlxuICogU2V0IC0tY2FyZC1pbmRleCBDU1MgY3VzdG9tIHByb3BlcnR5IG9uIGVhY2ggLmlvYy1jYXJkIGVsZW1lbnQsXG4gKiBjYXBwZWQgYXQgMTUgdG8gbGltaXQgc3RhZ2dlciBkZWxheSBvbiBsb25nIGxpc3RzLlxuICovXG5mdW5jdGlvbiBpbml0Q2FyZFN0YWdnZXIoKTogdm9pZCB7XG4gIGNvbnN0IGNhcmRzID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbDxIVE1MRWxlbWVudD4oXCIuaW9jLWNhcmRcIik7XG4gIGNhcmRzLmZvckVhY2goKGNhcmQsIGkpID0+IHtcbiAgICBjYXJkLnN0eWxlLnNldFByb3BlcnR5KFwiLS1jYXJkLWluZGV4XCIsIFN0cmluZyhNYXRoLm1pbihpLCAxNSkpKTtcbiAgfSk7XG59XG5cbi8qKlxuICogSW5pdGlhbGlzZSBhbGwgVUkgZW5oYW5jZW1lbnRzOiBzY3JvbGwtYXdhcmUgZmlsdGVyIGJhciBhbmQgY2FyZCBzdGFnZ2VyLlxuICovXG5leHBvcnQgZnVuY3Rpb24gaW5pdCgpOiB2b2lkIHtcbiAgaW5pdFNjcm9sbEF3YXJlRmlsdGVyQmFyKCk7XG4gIGluaXRDYXJkU3RhZ2dlcigpO1xufVxuIiwgIi8qKlxuICogU1ZHIHJlbGF0aW9uc2hpcCBncmFwaCByZW5kZXJlciBmb3IgdGhlIElPQyBkZXRhaWwgcGFnZS5cbiAqXG4gKiBSZWFkcyBncmFwaF9ub2RlcyBhbmQgZ3JhcGhfZWRnZXMgZnJvbSBkYXRhIGF0dHJpYnV0ZXMgb24gdGhlXG4gKiAjcmVsYXRpb25zaGlwLWdyYXBoIGNvbnRhaW5lciwgdGhlbiBkcmF3cyBhIGh1Yi1hbmQtc3Bva2UgU1ZHIGRpYWdyYW1cbiAqIHdpdGggdGhlIElPQyBhdCB0aGUgY2VudGVyIGFuZCBwcm92aWRlciBub2RlcyBhcnJhbmdlZCBpbiBhIGNpcmNsZSBhcm91bmQgaXQuXG4gKlxuICogTm9kZXMgYXJlIGNvbG9yZWQgYnkgdmVyZGljdCB0byBnaXZlIGluc3RhbnQgdmlzdWFsIHRyaWFnZSBjb250ZXh0LlxuICpcbiAqIFNFQy0wODogQWxsIHRleHQgY29udGVudCB1c2VzIGRvY3VtZW50LmNyZWF0ZVRleHROb2RlKCkgXHUyMDE0IG5ldmVyIGlubmVySFRNTFxuICogb3IgdGV4dENvbnRlbnQgb24gZWxlbWVudHMgd2l0aCBjaGlsZHJlbi4gSU9DIHZhbHVlcyBhbmQgcHJvdmlkZXIgbmFtZXNcbiAqIGFyZSBwYXNzZWQgdGhyb3VnaCBjcmVhdGVUZXh0Tm9kZSBvbmx5IHRvIHByZXZlbnQgWFNTLlxuICovXG5cbmludGVyZmFjZSBHcmFwaE5vZGUge1xuICBpZDogc3RyaW5nO1xuICBsYWJlbDogc3RyaW5nO1xuICB2ZXJkaWN0OiBzdHJpbmc7XG4gIHJvbGU6IFwiaW9jXCIgfCBcInByb3ZpZGVyXCI7XG59XG5cbmludGVyZmFjZSBHcmFwaEVkZ2Uge1xuICBmcm9tOiBzdHJpbmc7XG4gIHRvOiBzdHJpbmc7XG4gIHZlcmRpY3Q6IHN0cmluZztcbn1cblxuLyoqIFZlcmRpY3QtdG8tZmlsbC1jb2xvciBtYXBwaW5nIChtYXRjaGVzIENTUyB2ZXJkaWN0IHZhcmlhYmxlcykuICovXG5jb25zdCBWRVJESUNUX0NPTE9SUzogUmVjb3JkPHN0cmluZywgc3RyaW5nPiA9IHtcbiAgbWFsaWNpb3VzOiAgXCIjZWY0NDQ0XCIsXG4gIHN1c3BpY2lvdXM6IFwiI2Y5NzMxNlwiLFxuICBjbGVhbjogICAgICBcIiMyMmM1NWVcIixcbiAga25vd25fZ29vZDogXCIjM2I4MmY2XCIsXG4gIG5vX2RhdGE6ICAgIFwiIzZiNzI4MFwiLFxuICBlcnJvcjogICAgICBcIiM2YjcyODBcIixcbiAgaW9jOiAgICAgICAgXCIjOGI1Y2Y2XCIsXG59O1xuXG5jb25zdCBTVkdfTlMgPSBcImh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnXCI7XG5cbmZ1bmN0aW9uIHZlcmRpY3RDb2xvcih2ZXJkaWN0OiBzdHJpbmcpOiBzdHJpbmcge1xuICByZXR1cm4gVkVSRElDVF9DT0xPUlNbdmVyZGljdF0gPz8gXCIjNmI3MjgwXCI7XG59XG5cbi8qKlxuICogQ3JlYXRlIGFuIFNWRyBlbGVtZW50IGluIHRoZSBTVkcgbmFtZXNwYWNlLlxuICovXG5mdW5jdGlvbiBzdmdFbCh0YWc6IHN0cmluZyk6IFNWR0VsZW1lbnQge1xuICByZXR1cm4gZG9jdW1lbnQuY3JlYXRlRWxlbWVudE5TKFNWR19OUywgdGFnKSBhcyBTVkdFbGVtZW50O1xufVxuXG4vKipcbiAqIFJlbmRlciB0aGUgaHViLWFuZC1zcG9rZSByZWxhdGlvbnNoaXAgZ3JhcGggaW50byB0aGUgZ2l2ZW4gY29udGFpbmVyLlxuICogU2FmZSB0byBjYWxsIHdoZW4gbm8gcHJvdmlkZXIgZGF0YSBpcyBwcmVzZW50IFx1MjAxNCBzaG93cyBhIGZhbGxiYWNrIG1lc3NhZ2UuXG4gKi9cbmZ1bmN0aW9uIHJlbmRlclJlbGF0aW9uc2hpcEdyYXBoKGNvbnRhaW5lcjogSFRNTEVsZW1lbnQpOiB2b2lkIHtcbiAgY29uc3Qgbm9kZXNBdHRyID0gY29udGFpbmVyLmdldEF0dHJpYnV0ZShcImRhdGEtZ3JhcGgtbm9kZXNcIik7XG4gIGNvbnN0IGVkZ2VzQXR0ciA9IGNvbnRhaW5lci5nZXRBdHRyaWJ1dGUoXCJkYXRhLWdyYXBoLWVkZ2VzXCIpO1xuXG4gIGxldCBub2RlczogR3JhcGhOb2RlW10gPSBbXTtcbiAgbGV0IGVkZ2VzOiBHcmFwaEVkZ2VbXSA9IFtdO1xuXG4gIHRyeSB7XG4gICAgbm9kZXMgPSBub2Rlc0F0dHIgPyAoSlNPTi5wYXJzZShub2Rlc0F0dHIpIGFzIEdyYXBoTm9kZVtdKSA6IFtdO1xuICAgIGVkZ2VzID0gZWRnZXNBdHRyID8gKEpTT04ucGFyc2UoZWRnZXNBdHRyKSBhcyBHcmFwaEVkZ2VbXSkgOiBbXTtcbiAgfSBjYXRjaCB7XG4gICAgLy8gTWFsZm9ybWVkIEpTT04gXHUyMDE0IHNob3cgZW1wdHkgc3RhdGVcbiAgICBub2RlcyA9IFtdO1xuICAgIGVkZ2VzID0gW107XG4gIH1cblxuICBjb25zdCBwcm92aWRlck5vZGVzID0gbm9kZXMuZmlsdGVyKChuKSA9PiBuLnJvbGUgPT09IFwicHJvdmlkZXJcIik7XG4gIGNvbnN0IGlvY05vZGUgPSBub2Rlcy5maW5kKChuKSA9PiBuLnJvbGUgPT09IFwiaW9jXCIpO1xuXG4gIGlmICghaW9jTm9kZSB8fCBwcm92aWRlck5vZGVzLmxlbmd0aCA9PT0gMCkge1xuICAgIGNvbnN0IG1zZyA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoXCJwXCIpO1xuICAgIG1zZy5jbGFzc05hbWUgPSBcImdyYXBoLWVtcHR5XCI7XG4gICAgbXNnLmFwcGVuZENoaWxkKGRvY3VtZW50LmNyZWF0ZVRleHROb2RlKFwiTm8gcHJvdmlkZXIgZGF0YSB0byBncmFwaFwiKSk7XG4gICAgY29udGFpbmVyLmFwcGVuZENoaWxkKG1zZyk7XG4gICAgcmV0dXJuO1xuICB9XG5cbiAgLy8gLS0tLSBTVkcgY2FudmFzIC0tLS1cbiAgY29uc3Qgc3ZnID0gc3ZnRWwoXCJzdmdcIik7XG4gIHN2Zy5zZXRBdHRyaWJ1dGUoXCJ2aWV3Qm94XCIsIFwiMCAwIDYwMCA0MDBcIik7XG4gIHN2Zy5zZXRBdHRyaWJ1dGUoXCJ3aWR0aFwiLCBcIjEwMCVcIik7XG4gIHN2Zy5zZXRBdHRyaWJ1dGUoXCJyb2xlXCIsIFwiaW1nXCIpO1xuICBzdmcuc2V0QXR0cmlidXRlKFwiYXJpYS1sYWJlbFwiLCBcIlByb3ZpZGVyIHJlbGF0aW9uc2hpcCBncmFwaFwiKTtcblxuICBjb25zdCBjeCA9IDMwMDsgIC8vIGNlbnRlciB4XG4gIGNvbnN0IGN5ID0gMjAwOyAgLy8gY2VudGVyIHlcbiAgY29uc3Qgb3JiaXRSYWRpdXMgPSAxNTA7XG4gIGNvbnN0IGlvY3JyID0gMzA7ICAvLyBJT0Mgbm9kZSByYWRpdXNcbiAgY29uc3QgcHJyciA9IDIwOyAgIC8vIHByb3ZpZGVyIG5vZGUgcmFkaXVzXG5cbiAgLy8gLS0tLSBEcmF3IGVkZ2VzIGZpcnN0IChiZWhpbmQgbm9kZXMpIC0tLS1cbiAgY29uc3QgZWRnZUdyb3VwID0gc3ZnRWwoXCJnXCIpO1xuICBlZGdlR3JvdXAuc2V0QXR0cmlidXRlKFwiY2xhc3NcIiwgXCJncmFwaC1lZGdlc1wiKTtcblxuICBmb3IgKGNvbnN0IGVkZ2Ugb2YgZWRnZXMpIHtcbiAgICBjb25zdCB0YXJnZXROb2RlID0gcHJvdmlkZXJOb2Rlcy5maW5kKChuKSA9PiBuLmlkID09PSBlZGdlLnRvKTtcbiAgICBpZiAoIXRhcmdldE5vZGUpIGNvbnRpbnVlO1xuXG4gICAgY29uc3QgaWR4ID0gcHJvdmlkZXJOb2Rlcy5pbmRleE9mKHRhcmdldE5vZGUpO1xuICAgIGNvbnN0IGFuZ2xlID0gKDIgKiBNYXRoLlBJICogaWR4KSAvIHByb3ZpZGVyTm9kZXMubGVuZ3RoIC0gTWF0aC5QSSAvIDI7XG4gICAgY29uc3QgcHggPSBjeCArIG9yYml0UmFkaXVzICogTWF0aC5jb3MoYW5nbGUpO1xuICAgIGNvbnN0IHB5ID0gY3kgKyBvcmJpdFJhZGl1cyAqIE1hdGguc2luKGFuZ2xlKTtcblxuICAgIGNvbnN0IGxpbmUgPSBzdmdFbChcImxpbmVcIik7XG4gICAgbGluZS5zZXRBdHRyaWJ1dGUoXCJ4MVwiLCBTdHJpbmcoY3gpKTtcbiAgICBsaW5lLnNldEF0dHJpYnV0ZShcInkxXCIsIFN0cmluZyhjeSkpO1xuICAgIGxpbmUuc2V0QXR0cmlidXRlKFwieDJcIiwgU3RyaW5nKE1hdGgucm91bmQocHgpKSk7XG4gICAgbGluZS5zZXRBdHRyaWJ1dGUoXCJ5MlwiLCBTdHJpbmcoTWF0aC5yb3VuZChweSkpKTtcbiAgICBsaW5lLnNldEF0dHJpYnV0ZShcInN0cm9rZVwiLCB2ZXJkaWN0Q29sb3IoZWRnZS52ZXJkaWN0KSk7XG4gICAgbGluZS5zZXRBdHRyaWJ1dGUoXCJzdHJva2Utd2lkdGhcIiwgXCIyXCIpO1xuICAgIGxpbmUuc2V0QXR0cmlidXRlKFwib3BhY2l0eVwiLCBcIjAuNlwiKTtcbiAgICBlZGdlR3JvdXAuYXBwZW5kQ2hpbGQobGluZSk7XG4gIH1cblxuICBzdmcuYXBwZW5kQ2hpbGQoZWRnZUdyb3VwKTtcblxuICAvLyAtLS0tIERyYXcgcHJvdmlkZXIgbm9kZXMgLS0tLVxuICBjb25zdCBub2RlR3JvdXAgPSBzdmdFbChcImdcIik7XG4gIG5vZGVHcm91cC5zZXRBdHRyaWJ1dGUoXCJjbGFzc1wiLCBcImdyYXBoLW5vZGVzXCIpO1xuXG4gIHByb3ZpZGVyTm9kZXMuZm9yRWFjaCgobm9kZSwgaWR4KSA9PiB7XG4gICAgY29uc3QgYW5nbGUgPSAoMiAqIE1hdGguUEkgKiBpZHgpIC8gcHJvdmlkZXJOb2Rlcy5sZW5ndGggLSBNYXRoLlBJIC8gMjtcbiAgICBjb25zdCBweCA9IGN4ICsgb3JiaXRSYWRpdXMgKiBNYXRoLmNvcyhhbmdsZSk7XG4gICAgY29uc3QgcHkgPSBjeSArIG9yYml0UmFkaXVzICogTWF0aC5zaW4oYW5nbGUpO1xuXG4gICAgY29uc3QgZ3JvdXAgPSBzdmdFbChcImdcIik7XG4gICAgZ3JvdXAuc2V0QXR0cmlidXRlKFwiY2xhc3NcIiwgXCJncmFwaC1ub2RlIGdyYXBoLW5vZGUtLXByb3ZpZGVyXCIpO1xuXG4gICAgLy8gQWNjZXNzaWJsZSB0b29sdGlwXG4gICAgY29uc3QgdGl0bGUgPSBzdmdFbChcInRpdGxlXCIpO1xuICAgIHRpdGxlLmFwcGVuZENoaWxkKGRvY3VtZW50LmNyZWF0ZVRleHROb2RlKG5vZGUuaWQpKTtcbiAgICBncm91cC5hcHBlbmRDaGlsZCh0aXRsZSk7XG5cbiAgICAvLyBDaXJjbGVcbiAgICBjb25zdCBjaXJjbGUgPSBzdmdFbChcImNpcmNsZVwiKTtcbiAgICBjaXJjbGUuc2V0QXR0cmlidXRlKFwiY3hcIiwgU3RyaW5nKE1hdGgucm91bmQocHgpKSk7XG4gICAgY2lyY2xlLnNldEF0dHJpYnV0ZShcImN5XCIsIFN0cmluZyhNYXRoLnJvdW5kKHB5KSkpO1xuICAgIGNpcmNsZS5zZXRBdHRyaWJ1dGUoXCJyXCIsIFN0cmluZyhwcnJyKSk7XG4gICAgY2lyY2xlLnNldEF0dHJpYnV0ZShcImZpbGxcIiwgdmVyZGljdENvbG9yKG5vZGUudmVyZGljdCkpO1xuICAgIGdyb3VwLmFwcGVuZENoaWxkKGNpcmNsZSk7XG5cbiAgICAvLyBMYWJlbCBiZWxvdyBjaXJjbGUgKFNFQy0wODogY3JlYXRlVGV4dE5vZGUpXG4gICAgY29uc3QgdGV4dCA9IHN2Z0VsKFwidGV4dFwiKTtcbiAgICB0ZXh0LnNldEF0dHJpYnV0ZShcInhcIiwgU3RyaW5nKE1hdGgucm91bmQocHgpKSk7XG4gICAgdGV4dC5zZXRBdHRyaWJ1dGUoXCJ5XCIsIFN0cmluZyhNYXRoLnJvdW5kKHB5ICsgcHJyciArIDE0KSkpO1xuICAgIHRleHQuc2V0QXR0cmlidXRlKFwidGV4dC1hbmNob3JcIiwgXCJtaWRkbGVcIik7XG4gICAgdGV4dC5zZXRBdHRyaWJ1dGUoXCJmb250LXNpemVcIiwgXCIxMVwiKTtcbiAgICB0ZXh0LnNldEF0dHJpYnV0ZShcImZpbGxcIiwgXCIjZTVlN2ViXCIpO1xuICAgIHRleHQuYXBwZW5kQ2hpbGQoZG9jdW1lbnQuY3JlYXRlVGV4dE5vZGUobm9kZS5sYWJlbC5zbGljZSgwLCAxMikpKTtcbiAgICBncm91cC5hcHBlbmRDaGlsZCh0ZXh0KTtcblxuICAgIG5vZGVHcm91cC5hcHBlbmRDaGlsZChncm91cCk7XG4gIH0pO1xuXG4gIHN2Zy5hcHBlbmRDaGlsZChub2RlR3JvdXApO1xuXG4gIC8vIC0tLS0gRHJhdyBJT0MgY2VudGVyIG5vZGUgKG9uIHRvcCkgLS0tLVxuICBjb25zdCBpb2NHcm91cCA9IHN2Z0VsKFwiZ1wiKTtcbiAgaW9jR3JvdXAuc2V0QXR0cmlidXRlKFwiY2xhc3NcIiwgXCJncmFwaC1ub2RlIGdyYXBoLW5vZGUtLWlvY1wiKTtcblxuICBjb25zdCBpb2NUaXRsZSA9IHN2Z0VsKFwidGl0bGVcIik7XG4gIGlvY1RpdGxlLmFwcGVuZENoaWxkKGRvY3VtZW50LmNyZWF0ZVRleHROb2RlKGlvY05vZGUuaWQpKTtcbiAgaW9jR3JvdXAuYXBwZW5kQ2hpbGQoaW9jVGl0bGUpO1xuXG4gIGNvbnN0IGlvY0NpcmNsZSA9IHN2Z0VsKFwiY2lyY2xlXCIpO1xuICBpb2NDaXJjbGUuc2V0QXR0cmlidXRlKFwiY3hcIiwgU3RyaW5nKGN4KSk7XG4gIGlvY0NpcmNsZS5zZXRBdHRyaWJ1dGUoXCJjeVwiLCBTdHJpbmcoY3kpKTtcbiAgaW9jQ2lyY2xlLnNldEF0dHJpYnV0ZShcInJcIiwgU3RyaW5nKGlvY3JyKSk7XG4gIGlvY0NpcmNsZS5zZXRBdHRyaWJ1dGUoXCJmaWxsXCIsIHZlcmRpY3RDb2xvcihcImlvY1wiKSk7XG4gIGlvY0dyb3VwLmFwcGVuZENoaWxkKGlvY0NpcmNsZSk7XG5cbiAgY29uc3QgaW9jVGV4dCA9IHN2Z0VsKFwidGV4dFwiKTtcbiAgaW9jVGV4dC5zZXRBdHRyaWJ1dGUoXCJ4XCIsIFN0cmluZyhjeCkpO1xuICBpb2NUZXh0LnNldEF0dHJpYnV0ZShcInlcIiwgU3RyaW5nKGN5ICsgNCkpO1xuICBpb2NUZXh0LnNldEF0dHJpYnV0ZShcInRleHQtYW5jaG9yXCIsIFwibWlkZGxlXCIpO1xuICBpb2NUZXh0LnNldEF0dHJpYnV0ZShcImZvbnQtc2l6ZVwiLCBcIjEwXCIpO1xuICBpb2NUZXh0LnNldEF0dHJpYnV0ZShcImZpbGxcIiwgXCIjZmZmXCIpO1xuICBpb2NUZXh0LnNldEF0dHJpYnV0ZShcImZvbnQtd2VpZ2h0XCIsIFwiYm9sZFwiKTtcbiAgaW9jVGV4dC5hcHBlbmRDaGlsZChkb2N1bWVudC5jcmVhdGVUZXh0Tm9kZShpb2NOb2RlLmxhYmVsLnNsaWNlKDAsIDIwKSkpO1xuICBpb2NHcm91cC5hcHBlbmRDaGlsZChpb2NUZXh0KTtcblxuICBzdmcuYXBwZW5kQ2hpbGQoaW9jR3JvdXApO1xuXG4gIGNvbnRhaW5lci5hcHBlbmRDaGlsZChzdmcpO1xufVxuXG4vKipcbiAqIEluaXRpYWxpemUgdGhlIGdyYXBoIG1vZHVsZS5cbiAqIEZpbmRzIHRoZSAjcmVsYXRpb25zaGlwLWdyYXBoIGVsZW1lbnQgYW5kIHJlbmRlcnMgdGhlIFNWRyBpZiBwcmVzZW50LlxuICovXG5leHBvcnQgZnVuY3Rpb24gaW5pdCgpOiB2b2lkIHtcbiAgY29uc3QgY29udGFpbmVyID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXCJyZWxhdGlvbnNoaXAtZ3JhcGhcIik7XG4gIGlmIChjb250YWluZXIpIHtcbiAgICByZW5kZXJSZWxhdGlvbnNoaXBHcmFwaChjb250YWluZXIpO1xuICB9XG59XG4iLCAiLyoqXG4gKiBTZW50aW5lbFggbWFpbiBlbnRyeSBwb2ludCBcdTIwMTQgaW1wb3J0cyBhbmQgaW5pdGlhbGl6ZXMgYWxsIGZlYXR1cmUgbW9kdWxlcy5cbiAqXG4gKiBUaGlzIGZpbGUgaXMgdGhlIGVzYnVpbGQgZW50cnkgcG9pbnQgKEpTX0VOVFJZIGluIE1ha2VmaWxlKS5cbiAqIGVzYnVpbGQgd3JhcHMgdGhlIG91dHB1dCBpbiBhbiBJSUZFIGF1dG9tYXRpY2FsbHkgKC0tZm9ybWF0PWlpZmUpLlxuICpcbiAqIE1vZHVsZSBpbml0IG9yZGVyIG1hdGNoZXMgdGhlIG9yaWdpbmFsIG1haW4uanMgaW5pdCgpIGZ1bmN0aW9uXG4gKiAobGluZXMgODE1LTgyNikgdG8gcHJlc2VydmUgaWRlbnRpY2FsIERPTUNvbnRlbnRMb2FkZWQgYmVoYXZpb3IuXG4gKi9cblxuaW1wb3J0IHsgaW5pdCBhcyBpbml0Rm9ybSB9IGZyb20gXCIuL21vZHVsZXMvZm9ybVwiO1xuaW1wb3J0IHsgaW5pdCBhcyBpbml0Q2xpcGJvYXJkIH0gZnJvbSBcIi4vbW9kdWxlcy9jbGlwYm9hcmRcIjtcbmltcG9ydCB7IGluaXQgYXMgaW5pdENhcmRzIH0gZnJvbSBcIi4vbW9kdWxlcy9jYXJkc1wiO1xuaW1wb3J0IHsgaW5pdCBhcyBpbml0RmlsdGVyIH0gZnJvbSBcIi4vbW9kdWxlcy9maWx0ZXJcIjtcbmltcG9ydCB7IGluaXQgYXMgaW5pdEVucmljaG1lbnQgfSBmcm9tIFwiLi9tb2R1bGVzL2VucmljaG1lbnRcIjtcbmltcG9ydCB7IGluaXQgYXMgaW5pdFNldHRpbmdzIH0gZnJvbSBcIi4vbW9kdWxlcy9zZXR0aW5nc1wiO1xuaW1wb3J0IHsgaW5pdCBhcyBpbml0VWkgfSBmcm9tIFwiLi9tb2R1bGVzL3VpXCI7XG5pbXBvcnQgeyBpbml0IGFzIGluaXRHcmFwaCB9IGZyb20gXCIuL21vZHVsZXMvZ3JhcGhcIjtcblxuZnVuY3Rpb24gaW5pdCgpOiB2b2lkIHtcbiAgaW5pdEZvcm0oKTtcbiAgaW5pdENsaXBib2FyZCgpO1xuICBpbml0Q2FyZHMoKTtcbiAgaW5pdEZpbHRlcigpO1xuICBpbml0RW5yaWNobWVudCgpO1xuICBpbml0U2V0dGluZ3MoKTtcbiAgaW5pdFVpKCk7XG4gIGluaXRHcmFwaCgpO1xufVxuXG5pZiAoZG9jdW1lbnQucmVhZHlTdGF0ZSA9PT0gXCJsb2FkaW5nXCIpIHtcbiAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcihcIkRPTUNvbnRlbnRMb2FkZWRcIiwgaW5pdCk7XG59IGVsc2Uge1xuICBpbml0KCk7XG59XG4iXSwKICAibWFwcGluZ3MiOiAiOzs7QUFTTyxXQUFTLEtBQUssSUFBYSxNQUFjLFdBQVcsSUFBWTtBQUNyRSxXQUFPLEdBQUcsYUFBYSxJQUFJLEtBQUs7QUFBQSxFQUNsQzs7O0FDQUEsTUFBSSxhQUFtRDtBQUl2RCxXQUFTLGtCQUFrQixXQUF5QjtBQUNsRCxVQUFNLFdBQVcsU0FBUyxlQUFlLGdCQUFnQjtBQUN6RCxRQUFJLENBQUMsU0FBVTtBQUNmLGFBQVMsY0FBYyxZQUFZO0FBQ25DLGFBQVMsTUFBTSxVQUFVO0FBQ3pCLGFBQVMsVUFBVSxPQUFPLFdBQVc7QUFDckMsYUFBUyxVQUFVLElBQUksWUFBWTtBQUNuQyxRQUFJLGVBQWUsS0FBTSxjQUFhLFVBQVU7QUFDaEQsaUJBQWEsV0FBVyxXQUFZO0FBQ2xDLGVBQVMsVUFBVSxPQUFPLFlBQVk7QUFDdEMsZUFBUyxVQUFVLElBQUksV0FBVztBQUNsQyxpQkFBVyxXQUFZO0FBQ3JCLGlCQUFTLE1BQU0sVUFBVTtBQUN6QixpQkFBUyxVQUFVLE9BQU8sV0FBVztBQUFBLE1BQ3ZDLEdBQUcsR0FBRztBQUFBLElBQ1IsR0FBRyxHQUFJO0FBQUEsRUFDVDtBQUlBLFdBQVMsa0JBQWtCLE1BQW9CO0FBQzdDLFVBQU0sWUFBWSxTQUFTLGVBQWUsWUFBWTtBQUN0RCxRQUFJLENBQUMsVUFBVztBQUNoQixjQUFVLGNBQWM7QUFFeEIsY0FBVSxVQUFVLE9BQU8sZUFBZSxjQUFjO0FBQ3hELGNBQVUsVUFBVSxJQUFJLFNBQVMsV0FBVyxnQkFBZ0IsY0FBYztBQUFBLEVBQzVFO0FBSUEsV0FBUyxtQkFBeUI7QUFDaEMsVUFBTSxPQUFPLFNBQVMsZUFBZSxjQUFjO0FBQ25ELFFBQUksQ0FBQyxLQUFNO0FBRVgsVUFBTSxXQUFXLFNBQVMsY0FBbUMsV0FBVztBQUN4RSxVQUFNLFlBQVks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TUFBTSxHQUFHLEVBQUUsQ0FBQyxDQUFDO0FBQ3ZFLGFBQVMsWUFBWSxPQUFPO0FBRTVCLFFBQUksWUFBWSxRQUFRO0FBRXhCLGNBQVUsWUFBWSxHQUFHO0FBQUEsRUFDM0I7QUFNTyxXQUFTQyxRQUFhO0FBQzNCLFVBQU0sWUFBWSxTQUFTLGVBQWUsb0JBQW9CO0FBQzlELFFBQUksV0FBVztBQUNiLDhCQUF3QixTQUFTO0FBQUEsSUFDbkM7QUFBQSxFQUNGOzs7QUNyTEEsV0FBU0MsUUFBYTtBQUNwQixTQUFTO0FBQ1QsSUFBQUEsTUFBYztBQUNkLElBQUFBLE1BQVU7QUFDVixJQUFBQSxNQUFXO0FBQ1gsSUFBQUEsTUFBZTtBQUNmLElBQUFBLE1BQWE7QUFDYixJQUFBQSxNQUFPO0FBQ1AsSUFBQUEsTUFBVTtBQUFBLEVBQ1o7QUFFQSxNQUFJLFNBQVMsZUFBZSxXQUFXO0FBQ3JDLGFBQVMsaUJBQWlCLG9CQUFvQkEsS0FBSTtBQUFBLEVBQ3BELE9BQU87QUFDTCxJQUFBQSxNQUFLO0FBQUEsRUFDUDsiLAogICJuYW1lcyI6IFsiaW5pdCIsICJpbml0IiwgImluaXQiLCAidmVyZGljdEJ0bnMiLCAidHlwZVBpbGxzIiwgInNwaW5uZXJXcmFwcGVyIiwgImluaXQiLCAiYnRuIiwgImluaXQiLCAiaW5pdCIsICJpbml0IiwgImluaXQiXQp9Cg==
