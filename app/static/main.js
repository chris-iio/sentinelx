/**
 * SentinelX — main.js
 *
 * Minimal, CSP-compliant JavaScript for the IOC extractor UI.
 * No inline event handlers — all listeners are attached from this external file.
 *
 * Features:
 * - Disable submit button when textarea is empty
 * - Clear button resets textarea and re-disables submit
 * - Clipboard copy for IOC values via navigator.clipboard API
 * - Enrichment polling loop: fetches /enrichment/status/{job_id} every 750ms
 * - Incremental result rendering with verdict badges (XSS-safe DOM methods)
 * - Multi-provider display: multiple provider results stacked vertically per IOC
 * - Copy-with-enrichment: worst verdict across all providers for that IOC
 * - Export button: copies all IOCs + worst-verdict enrichment summaries to clipboard
 *
 * XSS safety (SEC-08): All API response data is rendered via .textContent or
 * .setAttribute only. No .innerHTML concatenation of external strings.
 */

(function () {
    "use strict";

    // ---- Submit button: disable when textarea is empty ----

    function initSubmitButton() {
        var form = document.getElementById("analyze-form");
        if (!form) return;

        var textarea = document.getElementById("ioc-text");
        var submitBtn = document.getElementById("submit-btn");
        var clearBtn = document.getElementById("clear-btn");

        if (!textarea || !submitBtn) return;

        function updateSubmitState() {
            submitBtn.disabled = textarea.value.trim().length === 0;
        }

        textarea.addEventListener("input", updateSubmitState);

        // Also handle paste events (browser may not fire "input" immediately)
        textarea.addEventListener("paste", function () {
            // Defer until after paste content is applied
            setTimeout(updateSubmitState, 0);
        });

        // Initial state (page load with pre-filled content)
        updateSubmitState();

        // ---- Clear button ----
        if (clearBtn) {
            clearBtn.addEventListener("click", function () {
                textarea.value = "";
                updateSubmitState();
                textarea.focus();
            });
        }
    }

    // ---- Clipboard copy for IOC values ----

    function initCopyButtons() {
        var copyButtons = document.querySelectorAll(".copy-btn");

        copyButtons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var value = btn.getAttribute("data-value");
                if (!value) return;

                // Check for enrichment summary set by polling loop (worst verdict)
                var enrichment = btn.getAttribute("data-enrichment");
                var copyText = enrichment ? (value + " | " + enrichment) : value;

                if (!navigator.clipboard) {
                    // Fallback for non-HTTPS or older browsers
                    fallbackCopy(copyText, btn);
                    return;
                }

                navigator.clipboard.writeText(copyText).then(function () {
                    showCopiedFeedback(btn);
                }).catch(function () {
                    fallbackCopy(copyText, btn);
                });
            });
        });
    }

    function showCopiedFeedback(btn) {
        var original = btn.textContent;
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(function () {
            btn.textContent = original;
            btn.classList.remove("copied");
        }, 1500);
    }

    function fallbackCopy(text, btn) {
        // Create a temporary textarea, select its content, and copy
        var tmp = document.createElement("textarea");
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
        } catch (e) {
            // Copy failed silently — user can still manually select the value
        } finally {
            document.body.removeChild(tmp);
        }
    }

    // ---- Enrichment polling loop ----

    // Verdict severity order for worst-verdict computation (highest index = most severe)
    var VERDICT_SEVERITY = ["error", "no_data", "clean", "suspicious", "malicious"];

    // Human-readable display labels for verdict strings (UI-06)
    var VERDICT_LABELS = {
        "malicious":  "MALICIOUS",
        "suspicious": "SUSPICIOUS",
        "clean":      "CLEAN",
        "no_data":    "NO RECORD",
        "error":      "ERROR"
    };

    // Expected provider counts per IOC type
    // VT supports all 7 enrichable types, MB supports md5/sha1/sha256, TF supports all 7
    // => hashes get 3 providers, others (ipv4/ipv6/domain/url) get 2 providers
    var IOC_PROVIDER_COUNTS = {
        "ipv4":   2,
        "ipv6":   2,
        "domain": 2,
        "url":    2,
        "md5":    3,
        "sha1":   3,
        "sha256": 3
    };

    function verdictSeverity(verdict) {
        var idx = VERDICT_SEVERITY.indexOf(verdict);
        return idx === -1 ? -1 : idx;
    }

    function initEnrichmentPolling() {
        var pageResults = document.querySelector(".page-results");
        if (!pageResults) return;

        var jobId = pageResults.getAttribute("data-job-id");
        var mode = pageResults.getAttribute("data-mode");

        if (!jobId || mode !== "online") return;

        // Dedup key: "ioc_value|provider" — each provider result per IOC rendered once
        var rendered = {};

        // Per-IOC verdict tracking for worst-verdict copy/export computation
        // iocVerdicts[ioc_value] = [{provider, verdict, summaryText}]
        var iocVerdicts = {};

        // Per-IOC result count tracking for pending indicator
        var iocResultCounts = {};

        var intervalId = setInterval(function () {
            fetch("/enrichment/status/" + jobId).then(function (resp) {
                if (!resp.ok) return null;
                return resp.json();
            }).then(function (data) {
                if (!data) return;

                updateProgressBar(data.done, data.total);

                // Render any new results not yet displayed
                var results = data.results || [];
                for (var i = 0; i < results.length; i++) {
                    var result = results[i];
                    var dedupKey = result.ioc_value + "|" + result.provider;
                    if (!rendered[dedupKey]) {
                        rendered[dedupKey] = true;
                        renderEnrichmentResult(result, iocVerdicts, iocResultCounts);
                    }
                }

                // Check for rate-limit or auth errors to show warning banner
                for (var j = 0; j < results.length; j++) {
                    var r = results[j];
                    if (r.type === "error" && r.error) {
                        var errLower = r.error.toLowerCase();
                        if (errLower.indexOf("rate limit") !== -1 || errLower.indexOf("429") !== -1) {
                            showEnrichWarning("Rate limit reached for " + r.provider + ".");
                        } else if (errLower.indexOf("authentication") !== -1 || errLower.indexOf("401") !== -1 || errLower.indexOf("403") !== -1) {
                            showEnrichWarning("Authentication error for " + r.provider + ". Please check your API key in Settings.");
                        }
                    }
                }

                if (data.complete) {
                    clearInterval(intervalId);
                    markEnrichmentComplete(data.done, data.total);
                }
            }).catch(function () {
                // Fetch error — silently continue; retry on next interval tick
            });
        }, 750);
    }

    function updateProgressBar(done, total) {
        var fill = document.getElementById("enrich-progress-fill");
        var text = document.getElementById("enrich-progress-text");
        if (!fill || !text) return;

        var pct = total > 0 ? Math.round((done / total) * 100) : 0;
        fill.style.width = pct + "%";
        text.textContent = done + "/" + total + " providers complete";
    }

    // Get or create the collapsed no-data section inside an enrichment slot
    function getOrCreateNodataSection(slot) {
        var existing = slot.querySelector(".enrichment-nodata-section");
        if (existing) return existing;

        var details = document.createElement("details");
        details.className = "enrichment-nodata-section";
        // Collapsed by default — no open attribute

        var summary = document.createElement("summary");
        summary.className = "enrichment-nodata-summary";
        summary.textContent = "1 provider: no record";

        details.appendChild(summary);
        slot.appendChild(details);
        return details;
    }

    // Update the summary count text after appending a no_data result row
    function updateNodataSummary(detailsEl) {
        var rows = detailsEl.querySelectorAll(".provider-result-row");
        var count = rows.length;
        var summary = detailsEl.querySelector("summary");
        if (!summary) return;
        summary.textContent = count + " provider" + (count !== 1 ? "s" : "") + ": no record";
    }

    // Show or update the pending provider indicator after first result for an IOC
    function updatePendingIndicator(slot, targetRow, receivedCount) {
        var iocType = targetRow ? targetRow.getAttribute("data-ioc-type") : "";
        var totalExpected = IOC_PROVIDER_COUNTS[iocType] || 0;
        var remaining = totalExpected - receivedCount;

        if (remaining <= 0) {
            // All providers accounted for — remove waiting indicator if present
            var existingIndicator = slot.querySelector(".enrichment-waiting-text");
            if (existingIndicator) {
                slot.removeChild(existingIndicator);
            }
            return;
        }

        // Find or create the waiting indicator span
        var indicator = slot.querySelector(".enrichment-waiting-text");
        if (!indicator) {
            indicator = document.createElement("span");
            indicator.className = "enrichment-waiting-text enrichment-pending-text";
            // Insert before nodata section if present, otherwise append
            var nodataSection = slot.querySelector(".enrichment-nodata-section");
            if (nodataSection) {
                slot.insertBefore(indicator, nodataSection);
            } else {
                slot.appendChild(indicator);
            }
        }
        indicator.textContent = remaining + " provider" + (remaining !== 1 ? "s" : "") + " still loading...";
    }

    function renderEnrichmentResult(result, iocVerdicts, iocResultCounts) {
        // Find the enrichment row for this IOC value
        var rows = document.querySelectorAll(".ioc-enrichment-row");
        var targetRow = null;
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].getAttribute("data-ioc-value") === result.ioc_value) {
                targetRow = rows[i];
                break;
            }
        }
        if (!targetRow) return;

        var slot = targetRow.querySelector(".enrichment-slot");
        if (!slot) return;

        // Remove spinner wrapper on first result for this IOC (slot still has spinner-wrapper)
        var spinnerWrapper = slot.querySelector(".spinner-wrapper");
        if (spinnerWrapper) {
            slot.removeChild(spinnerWrapper);
        }

        // Track received count for this IOC before rendering
        iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] || 0) + 1;
        var receivedCount = iocResultCounts[result.ioc_value];

        // Build provider result row div (appended, not replacing)
        var providerRow = document.createElement("div");
        providerRow.className = "provider-result-row";

        var badge = document.createElement("span");
        var detail = document.createElement("span");
        detail.className = "enrichment-detail";

        var summaryText = "";
        var verdict = "";

        if (result.type === "result") {
            verdict = result.verdict || "no_data";
            badge.className = "verdict-badge verdict-" + verdict;
            // Use VERDICT_LABELS for display — never raw verdict strings (UI-06)
            badge.textContent = VERDICT_LABELS[verdict] || verdict.toUpperCase();

            var verdictText = "";
            if (verdict === "malicious") {
                verdictText = result.detection_count + "/" + result.total_engines + " malicious";
            } else if (verdict === "suspicious") {
                verdictText = "Suspicious";
            } else if (verdict === "clean") {
                // Explicitly mention engine count to distinguish from no_data (UI-06)
                verdictText = "Clean — scanned by " + result.total_engines + " engines";
            } else {
                // no_data: analyst-friendly phrasing (UI-06)
                verdictText = "Not in " + result.provider + " database";
            }

            var scanDateStr = formatDate(result.scan_date);
            detail.textContent = result.provider + ": " + verdictText + (scanDateStr ? " — Scanned " + scanDateStr : "");

            summaryText = result.provider + ": " + verdict + " (" + verdictText + ")";
        } else {
            // Error result
            verdict = "error";
            badge.className = "verdict-badge verdict-error";
            badge.textContent = VERDICT_LABELS["error"] || "ERROR";
            detail.textContent = result.provider + ": " + result.error;
            summaryText = result.provider + ": error — " + result.error;
        }

        providerRow.appendChild(badge);
        providerRow.appendChild(detail);

        if (verdict === "no_data") {
            // Route no_data results into the collapsed details section (UI-06)
            var nodataSection = getOrCreateNodataSection(slot);
            nodataSection.appendChild(providerRow);
            updateNodataSummary(nodataSection);
        } else {
            // Active results go directly into the slot
            slot.appendChild(providerRow);
        }

        // Update pending indicator for remaining providers
        updatePendingIndicator(slot, targetRow, receivedCount);

        // Track per-IOC verdicts for worst-verdict computation
        if (!iocVerdicts[result.ioc_value]) {
            iocVerdicts[result.ioc_value] = [];
        }
        iocVerdicts[result.ioc_value].push({
            provider: result.provider,
            verdict: verdict,
            summaryText: summaryText
        });

        // Update copy button with worst verdict across all providers for this IOC
        updateCopyButtonWorstVerdict(result.ioc_value, iocVerdicts);
    }

    function updateCopyButtonWorstVerdict(iocValue, iocVerdicts) {
        var copyBtn = findCopyButtonForIoc(iocValue);
        if (!copyBtn) return;

        var verdicts = iocVerdicts[iocValue] || [];
        if (verdicts.length === 0) return;

        // Find the entry with the highest severity verdict
        var worst = verdicts[0];
        for (var i = 1; i < verdicts.length; i++) {
            if (verdictSeverity(verdicts[i].verdict) > verdictSeverity(worst.verdict)) {
                worst = verdicts[i];
            }
        }

        copyBtn.setAttribute("data-enrichment", worst.summaryText);
    }

    function findCopyButtonForIoc(iocValue) {
        var btns = document.querySelectorAll(".copy-btn");
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].getAttribute("data-value") === iocValue) {
                return btns[i];
            }
        }
        return null;
    }

    function formatDate(iso) {
        if (!iso) return "";
        try {
            return new Date(iso).toLocaleDateString();
        } catch (e) {
            return iso;
        }
    }

    function markEnrichmentComplete(done, total) {
        var container = document.getElementById("enrich-progress");
        if (container) {
            container.classList.add("complete");
        }
        var text = document.getElementById("enrich-progress-text");
        if (text) {
            text.textContent = "Enrichment complete";
        }
        var exportBtn = document.getElementById("export-btn");
        if (exportBtn) {
            exportBtn.removeAttribute("disabled");
        }
    }

    function showEnrichWarning(message) {
        var banner = document.getElementById("enrich-warning");
        if (!banner) return;
        banner.style.display = "block";
        // Use textContent to safely set the warning message (SEC-08)
        banner.textContent = "Warning: " + message + " Consider using offline mode or checking your API key in Settings.";
    }

    // ---- Export button: copy all IOCs + worst-verdict enrichment to clipboard ----

    function initExportButton() {
        var exportBtn = document.getElementById("export-btn");
        if (!exportBtn) return;

        exportBtn.addEventListener("click", function () {
            var lines = [];
            var iocRows = document.querySelectorAll(".ioc-row");

            iocRows.forEach(function (row) {
                var valueEl = row.querySelector(".ioc-value");
                if (!valueEl) return;

                var iocValue = valueEl.textContent.trim();
                var copyBtn = findCopyButtonForIoc(iocValue);
                // data-enrichment holds the worst verdict summary (set by polling loop)
                var enrichment = copyBtn ? copyBtn.getAttribute("data-enrichment") : null;

                if (enrichment) {
                    lines.push(iocValue + " | " + enrichment);
                } else {
                    lines.push(iocValue);
                }
            });

            var exportText = lines.join("\n");

            if (!navigator.clipboard) {
                fallbackCopy(exportText, exportBtn);
                return;
            }

            navigator.clipboard.writeText(exportText).then(function () {
                showCopiedFeedback(exportBtn);
            }).catch(function () {
                fallbackCopy(exportText, exportBtn);
            });
        });
    }

    // ---- Settings page: show/hide API key toggle ----

    function initSettingsPage() {
        var btn = document.getElementById('toggle-key-btn');
        var input = document.getElementById('api-key');
        if (!btn || !input) return;
        btn.addEventListener('click', function () {
            if (input.type === 'password') {
                input.type = 'text';
                btn.textContent = 'Hide';
            } else {
                input.type = 'password';
                btn.textContent = 'Show';
            }
        });
    }

    // ---- Initialise on DOM ready ----

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            initSubmitButton();
            initCopyButtons();
            initEnrichmentPolling();
            initExportButton();
            initSettingsPage();
        });
    } else {
        // DOM already ready (script is deferred or loaded late)
        initSubmitButton();
        initCopyButtons();
        initEnrichmentPolling();
        initExportButton();
        initSettingsPage();
    }

}());
