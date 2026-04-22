/**
 * Unit tests for enrichment.ts polling behavior.
 *
 * Covers explicit terminal failure handling from the hardened backend contract,
 * continuity of the existing success-path rendering/completion flow, and the
 * exclusive live-owner guard that prevents history pages from polling.
 */

import type { EnrichmentStatus } from "../types/api";

function installCssEscape(): void {
  vi.stubGlobal("CSS", {
    escape(value: string): string {
      return value;
    },
  });
}

function buildResultsDom(owner = "live"): void {
  document.body.innerHTML = `
    <div class="page-results" data-results-owner="${owner}" data-job-id="job-123" data-mode="online" data-provider-counts='{"ipv4":1}'>
      <div class="export-group">
        <button class="btn btn-export" id="export-btn" type="button" disabled>Export</button>
        <div class="export-dropdown" id="export-dropdown" style="display:none;">
          <button data-export="json" type="button">JSON</button>
          <button data-export="csv" type="button">CSV</button>
          <button data-export="iocs" type="button">IOCs</button>
        </div>
      </div>

      <div class="enrich-warning" id="enrich-warning" style="display:none;"></div>

      <div class="enrich-progress" id="enrich-progress">
        <div class="enrich-progress-bar">
          <div class="enrich-progress-fill" id="enrich-progress-fill" style="width:0%;"></div>
        </div>
        <span class="enrich-progress-text" id="enrich-progress-text">0/1 providers complete</span>
      </div>

      <div class="verdict-dashboard" id="verdict-dashboard">
        <span data-verdict-count="malicious">0</span>
        <span data-verdict-count="suspicious">0</span>
        <span data-verdict-count="clean">0</span>
        <span data-verdict-count="known_good">0</span>
        <span data-verdict-count="no_data">1</span>
      </div>

      <div class="ioc-cards-grid" id="ioc-cards-grid">
        <div class="ioc-card" data-ioc-value="1.2.3.4" data-ioc-type="ipv4" data-verdict="no_data">
          <div class="ioc-card-header">
            <div class="ioc-row-left">
              <span class="ioc-value">1.2.3.4</span>
              <span class="verdict-label verdict-label--no_data">NO DATA</span>
            </div>
            <div class="ioc-card-actions">
              <button class="btn btn-copy copy-btn" data-value="1.2.3.4" type="button">Copy</button>
            </div>
          </div>
          <div class="ioc-context-line"></div>
          <div class="enrichment-slot">
            <div class="spinner-wrapper shimmer-wrapper"></div>
            <div class="enrichment-details">
              <div class="enrichment-section enrichment-section--reputation"></div>
              <div class="enrichment-section enrichment-section--context"></div>
              <div class="enrichment-section enrichment-section--no-data"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function mockFetchSequence(...responses: Array<{ ok: boolean; data: EnrichmentStatus }>) {
  const fetchMock = vi.fn();
  for (const response of responses) {
    fetchMock.mockResolvedValueOnce({
      ok: response.ok,
      json: vi.fn().mockResolvedValue(response.data),
    });
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("enrichment polling", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.useFakeTimers();
    installCssEscape();
    buildResultsDom();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  it("does not poll when the results surface is owned by history", async () => {
    buildResultsDom("history");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { init } = await import("./enrichment");
    init();

    await vi.advanceTimersByTimeAsync(1500);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(document.querySelector(".page-results")?.getAttribute("data-results-runtime")).toBeNull();
  });

  it("surfaces terminal 404 polling failures and stops retrying", async () => {
    const fetchMock = mockFetchSequence({
      ok: false,
      data: {
        total: 0,
        done: 0,
        complete: true,
        results: [],
        next_since: 0,
        status: "failed",
        terminal: true,
        terminal_reason: "evicted",
        error: "Enrichment job status was evicted from memory.",
      },
    });

    const { init } = await import("./enrichment");
    init();

    await vi.advanceTimersByTimeAsync(750);

    const warning = document.getElementById("enrich-warning");
    const progressText = document.getElementById("enrich-progress-text");
    const exportBtn = document.getElementById("export-btn");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(warning?.style.display).toBe("block");
    expect(warning?.textContent).toBe("Enrichment job status was evicted from memory.");
    expect(progressText?.textContent).toBe("Enrichment job status was evicted from memory.");
    expect(exportBtn?.hasAttribute("disabled")).toBe(true);

    await vi.advanceTimersByTimeAsync(1500);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("preserves the existing success-path rendering and completion flow", async () => {
    const fetchMock = mockFetchSequence({
      ok: true,
      data: {
        total: 1,
        done: 1,
        complete: true,
        results: [
          {
            type: "result",
            ioc_value: "1.2.3.4",
            ioc_type: "ipv4",
            provider: "VirusTotal",
            verdict: "clean",
            detection_count: 0,
            total_engines: 95,
            scan_date: null,
            raw_stats: {},
          },
        ],
        next_since: 1,
        status: "complete",
        terminal: false,
        terminal_reason: null,
        error: null,
      },
    });

    const { init } = await import("./enrichment");
    init();

    await vi.advanceTimersByTimeAsync(750);
    await vi.advanceTimersByTimeAsync(150);

    const warning = document.getElementById("enrich-warning");
    const progress = document.getElementById("enrich-progress");
    const progressText = document.getElementById("enrich-progress-text");
    const exportBtn = document.getElementById("export-btn");
    const slot = document.querySelector<HTMLElement>(".enrichment-slot");
    const detailRow = document.querySelector(".provider-detail-row");
    const detailLink = document.querySelector(".detail-link");
    const verdictLabel = document.querySelector(".verdict-label");
    const root = document.querySelector<HTMLElement>(".page-results");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(warning?.style.display).toBe("none");
    expect(progress?.classList.contains("complete")).toBe(true);
    expect(progressText?.textContent).toBe("Enrichment complete");
    expect(exportBtn?.hasAttribute("disabled")).toBe(false);
    expect(slot?.classList.contains("enrichment-slot--loaded")).toBe(true);
    expect(detailRow).not.toBeNull();
    expect(detailLink).not.toBeNull();
    expect(verdictLabel?.textContent).toBe("CLEAN");
    expect(root?.getAttribute("data-results-runtime")).toBe("live");
    expect(root?.getAttribute("data-results-expand-wired")).toBe("true");
    expect(root?.getAttribute("data-results-export-wired")).toBe("true");

    await vi.advanceTimersByTimeAsync(1500);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
