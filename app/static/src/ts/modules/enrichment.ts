/**
 * Enrichment polling orchestrator — polling loop, progress tracking,
 * result dispatch, and module state.
 *
 * Verdict computation lives in verdict-compute.ts.
 * DOM row construction lives in row-factory.ts.
 * Shared result application lives in result-application.ts.
 * This module owns the polling interval, transport/runtime warnings,
 * terminal-state handling, and live-mode debounced flush timing.
 */

import type { EnrichmentItem, EnrichmentStatus } from "../types/api";
import { attr } from "../utils/dom";
import { initExportButton as sharedInitExportButton } from "./shared-rendering";
import { createResultApplicationCoordinator } from "./result-application";

// ---- Module-private state ----

/** Accumulated enrichment results for export */
const allResults: EnrichmentItem[] = [];

const POLL_BASE_DELAY_MS = 750;
const POLL_MAX_DELAY_MS = 5000;
const POLL_MAX_CONSECUTIVE_FAILURES = 5;

type PollFailureReason = "network_error" | "malformed_json" | "http_error" | "runtime_error";

type PollPayload = {
  ok: boolean;
  status: number;
  data: EnrichmentStatus;
};

function recordPollingState(
  pageResults: HTMLElement,
  state: "running" | "retrying" | "failed" | "complete",
  failures = 0,
  reason?: PollFailureReason
): void {
  pageResults.setAttribute("data-enrichment-poll-state", state);
  pageResults.setAttribute("data-enrichment-poll-failures", String(failures));
  if (reason) {
    pageResults.setAttribute("data-enrichment-poll-last-error", reason);
  } else {
    pageResults.removeAttribute("data-enrichment-poll-last-error");
  }
}

function warnPollingDecision(
  event: string,
  jobId: string,
  details: Record<string, string | number | boolean | null>
): void {
  console.warn({ event, jobId, ...details });
}

function getPollFailureReason(error: unknown): PollFailureReason {
  if (error instanceof Error) {
    const reason = error.message;
    if (reason === "malformed_json") return "malformed_json";
    if (reason === "http_error") return "http_error";
    if (reason === "runtime_error") return "runtime_error";
  }
  return "network_error";
}

function getPollFailureMessage(reason: PollFailureReason): string {
  if (reason === "malformed_json") {
    return "Enrichment polling returned an unreadable status response.";
  }
  if (reason === "http_error") {
    return "Enrichment polling returned an unexpected server response.";
  }
  return "Enrichment polling failed after repeated attempts. Please retry the analysis.";
}

async function readPollPayload(resp: Response): Promise<PollPayload> {
  let data: EnrichmentStatus;
  try {
    data = (await resp.json()) as EnrichmentStatus;
  } catch {
    throw new Error("malformed_json");
  }

  return {
    ok: resp.ok,
    status: resp.status,
    data,
  };
}

// ---- Private helpers ----

function isLiveResultsPage(pageResults: HTMLElement): boolean {
  const explicitOwner = attr(pageResults, "data-results-owner");
  const mode = attr(pageResults, "data-mode");
  const jobId = attr(pageResults, "data-job-id");

  if (explicitOwner) {
    return explicitOwner === "live" && mode === "online" && Boolean(jobId);
  }

  if (pageResults.hasAttribute("data-history-results")) {
    return false;
  }

  return mode === "online" && Boolean(jobId);
}

/**
 * Update the progress bar fill and text.
 * Source: main.js updateProgressBar() (lines 375-383).
 */
function updateProgressBar(done: number, total: number): void {
  const fill = document.getElementById("enrich-progress-fill");
  const text = document.getElementById("enrich-progress-text");
  if (!fill || !text) return;

  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  fill.style.width = pct + "%";
  text.textContent = done + "/" + total + " providers complete";
}

/**
 * Show a warning banner for rate-limit or authentication errors.
 * Source: main.js showEnrichWarning() (lines 605-611).
 */
function showEnrichWarning(message: string): void {
  const banner = document.getElementById("enrich-warning");
  if (!banner) return;
  banner.style.display = "block";
  banner.textContent =
    "Warning: " +
    message +
    " Consider using offline mode or checking your API key in Settings.";
}

/**
 * Show a terminal enrichment failure banner for analyst-visible polling failures.
 */
function showTerminalFailure(message: string): void {
  const banner = document.getElementById("enrich-warning");
  if (!banner) return;
  banner.style.display = "block";
  banner.textContent = message;
}

/**
 * Mark enrichment complete: add .complete class to progress container,
 * update text, and enable the export button.
 */
function markEnrichmentComplete(
  coordinator: ReturnType<typeof createResultApplicationCoordinator>
): void {
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

  coordinator.finalize();
}

/**
 * Mark enrichment as terminally failed so the analyst sees a stable stop state
 * instead of endless polling.
 */
function markEnrichmentTerminalFailure(
  message: string,
  coordinator: ReturnType<typeof createResultApplicationCoordinator>
): void {
  const container = document.getElementById("enrich-progress");
  if (container) {
    container.classList.remove("complete");
  }
  const text = document.getElementById("enrich-progress-text");
  if (text) {
    text.textContent = message;
  }
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn && allResults.length > 0) {
    exportBtn.removeAttribute("disabled");
  }

  coordinator.finalize();
}

/**
 * Convert terminal polling payloads into analyst-visible copy.
 */
function getTerminalFailureMessage(data: EnrichmentStatus): string {
  if (data.terminal_reason === "evicted") {
    return data.error ?? "Enrichment status was evicted from memory. Please rerun the analysis.";
  }
  if (data.terminal_reason === "unknown") {
    return data.error ?? "Enrichment job was not found. Please rerun the analysis.";
  }
  if (data.error) {
    return "Enrichment failed: " + data.error;
  }
  return "Enrichment failed before completion.";
}

/**
 * Wire expand/collapse toggle using event delegation on .page-results.
 * Called once from init(). Handles clicks and keyboard Enter/Space on any
 * .ioc-summary-row that appears in the page — including ones created after
 * init() (summary rows are built during polling/replay).
 */
export function wireExpandToggles(
  pageResults: HTMLElement | null = document.querySelector<HTMLElement>(".page-results")
): void {
  if (!pageResults) return;
  if (pageResults.getAttribute("data-results-expand-wired") === "true") return;

  function handleToggle(target: HTMLElement): void {
    const summaryRow = target.closest<HTMLElement>(".ioc-summary-row");
    if (!summaryRow) return;

    const slot = summaryRow.closest<HTMLElement>(".enrichment-slot");
    const details = slot ? slot.querySelector<HTMLElement>(".enrichment-details") : null;
    if (!details) return;

    const isOpen = details.classList.toggle("is-open");
    summaryRow.classList.toggle("is-open", isOpen);
    summaryRow.setAttribute("aria-expanded", String(isOpen));
  }

  pageResults.addEventListener("click", (event: MouseEvent) => {
    handleToggle(event.target as HTMLElement);
  });

  pageResults.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      const target = event.target as HTMLElement;
      if (target.closest(".ioc-summary-row")) {
        event.preventDefault();
        handleToggle(target);
      }
    }
  });

  pageResults.setAttribute("data-results-expand-wired", "true");
}

// ---- Public API ----

export function init(): void {
  const pageResults = document.querySelector<HTMLElement>(".page-results");
  if (!pageResults || !isLiveResultsPage(pageResults)) return;

  const jobId = attr(pageResults, "data-job-id");
  if (!jobId) return;
  const livePageResults: HTMLElement = pageResults;
  allResults.length = 0;
  wireExpandToggles(livePageResults);

  let since = 0;
  const coordinator = createResultApplicationCoordinator();
  let flushTimer: ReturnType<typeof setTimeout> | null = null;

  function scheduleFlush(): void {
    if (flushTimer !== null) {
      clearTimeout(flushTimer);
    }
    flushTimer = setTimeout(() => {
      flushTimer = null;
      coordinator.flush();
    }, 100);
  }

  function clearPendingFlush(): void {
    if (flushTimer !== null) {
      clearTimeout(flushTimer);
      flushTimer = null;
    }
  }

  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;
  let consecutiveFailures = 0;

  function stopPolling(): void {
    stopped = true;
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function scheduleNextPoll(delayMs: number): void {
    if (stopped) return;
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
    }
    pollTimer = setTimeout(() => {
      pollTimer = null;
      void pollOnce();
    }, delayMs);
  }

  function handleRepeatedPollingFailure(reason: PollFailureReason): void {
    consecutiveFailures += 1;
    recordPollingState(livePageResults, "retrying", consecutiveFailures, reason);

    if (consecutiveFailures >= POLL_MAX_CONSECUTIVE_FAILURES) {
      stopPolling();
      clearPendingFlush();
      const message = getPollFailureMessage(reason);
      warnPollingDecision("enrichment-poll-terminal-failure", jobId, {
        reason,
        consecutiveFailures,
      });
      showTerminalFailure(message);
      markEnrichmentTerminalFailure(message, coordinator);
      recordPollingState(livePageResults, "failed", consecutiveFailures, reason);
      return;
    }

    const nextDelay = Math.min(
      POLL_BASE_DELAY_MS * Math.pow(2, consecutiveFailures),
      POLL_MAX_DELAY_MS
    );
    warnPollingDecision("enrichment-poll-retry-scheduled", jobId, {
      reason,
      consecutiveFailures,
      nextDelayMs: nextDelay,
    });
    scheduleNextPoll(nextDelay);
  }

  function applyStatusPayload(payload: PollPayload): void {
    const data = payload.data;
    updateProgressBar(data.done, data.total);

    const results = data.results;
    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      if (!result) continue;
      allResults.push(result);
      coordinator.apply(result);

      if (result.type === "error" && result.error) {
        const errLower = result.error.toLowerCase();
        if (errLower.indexOf("rate limit") !== -1 || errLower.indexOf("429") !== -1) {
          showEnrichWarning("Rate limit reached for " + result.provider + ".");
        } else if (
          errLower.indexOf("authentication") !== -1 ||
          errLower.indexOf("401") !== -1 ||
          errLower.indexOf("403") !== -1
        ) {
          showEnrichWarning(
            "Authentication error for " +
              result.provider +
              ". Please check your API key in Settings."
          );
        }
      }
    }

    if (results.length > 0) {
      scheduleFlush();
    }

    since = data.next_since;
    consecutiveFailures = 0;
    recordPollingState(livePageResults, "running");

    if (data.terminal) {
      stopPolling();
      clearPendingFlush();
      const terminalMessage = getTerminalFailureMessage(data);
      showTerminalFailure(terminalMessage);
      markEnrichmentTerminalFailure(terminalMessage, coordinator);
      recordPollingState(livePageResults, "failed", 0, "http_error");
      return;
    }

    if (!payload.ok) {
      throw new Error("http_error");
    }

    if (data.complete) {
      stopPolling();
      clearPendingFlush();
      markEnrichmentComplete(coordinator);
      recordPollingState(livePageResults, "complete");
    }
  }

  async function pollOnce(): Promise<void> {
    if (stopped) return;

    try {
      const resp = await fetch("/enrichment/status/" + jobId + "?since=" + since);
      const payload = await readPollPayload(resp);
      applyStatusPayload(payload);
      if (!stopped) {
        scheduleNextPoll(POLL_BASE_DELAY_MS);
      }
    } catch (error) {
      handleRepeatedPollingFailure(getPollFailureReason(error));
    }
  }

  scheduleNextPoll(POLL_BASE_DELAY_MS);

  livePageResults.setAttribute("data-results-runtime", "live");
  sharedInitExportButton(allResults, livePageResults);
}
