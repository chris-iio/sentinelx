/**
 * Unit tests for enrichment.ts polling behavior.
 *
 * Covers explicit terminal failure handling from the hardened backend contract,
 * continuity of the existing success-path rendering/completion flow, and the
 * exclusive live-owner guard that prevents history pages from polling.
 */

import type { EnrichmentItem, EnrichmentStatus } from "../types/api";

function installCssEscape(): void {
  vi.stubGlobal("CSS", {
    escape(value: string): string {
      return value;
    },
  });
}

const STREAMED_RESULTS: EnrichmentItem[] = [
  {
    type: "result",
    ioc_value: "1.2.3.4",
    ioc_type: "ipv4",
    provider: "IP Context",
    verdict: "no_data",
    detection_count: 0,
    total_engines: 0,
    scan_date: null,
    raw_stats: {
      geo: "Tokyo, JP",
      reverse: "edge.example.net",
      flags: ["hosting"],
    },
  },
  {
    type: "result",
    ioc_value: "1.2.3.4",
    ioc_type: "ipv4",
    provider: "VirusTotal",
    verdict: "malicious",
    detection_count: 2,
    total_engines: 70,
    scan_date: null,
    raw_stats: {},
  },
  {
    type: "result",
    ioc_value: "1.2.3.4",
    ioc_type: "ipv4",
    provider: "GreyNoise",
    verdict: "clean",
    detection_count: 0,
    total_engines: 1,
    scan_date: null,
    raw_stats: {
      classification: "benign",
    },
  },
  {
    type: "error",
    ioc_value: "1.2.3.4",
    ioc_type: "ipv4",
    provider: "AbuseIPDB",
    error: "Timeout",
  },
];

function buildResultsDom(owner = "live", providerCounts = '{"ipv4":4}'): void {
  document.body.innerHTML = `
    <div class="page-results" data-results-owner="${owner}" data-job-id="job-123" data-mode="online" data-provider-counts='${providerCounts}'>
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
        <span class="enrich-progress-text" id="enrich-progress-text">0/4 providers complete</span>
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
    buildResultsDom("history", '{"ipv4":1}');
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

  it("preserves next_since continuity while rendering shared-path parity state across multiple polls", async () => {
    const fetchMock = mockFetchSequence(
      {
        ok: true,
        data: {
          total: STREAMED_RESULTS.length,
          done: 1,
          complete: false,
          results: [STREAMED_RESULTS[0]!],
          next_since: 1,
          status: "running",
          terminal: false,
          terminal_reason: null,
          error: null,
        },
      },
      {
        ok: true,
        data: {
          total: STREAMED_RESULTS.length,
          done: STREAMED_RESULTS.length,
          complete: true,
          results: STREAMED_RESULTS.slice(1),
          next_since: STREAMED_RESULTS.length,
          status: "complete",
          terminal: false,
          terminal_reason: null,
          error: null,
        },
      }
    );

    const { init } = await import("./enrichment");
    init();

    await vi.advanceTimersByTimeAsync(750);

    const firstProgressText = document.getElementById("enrich-progress-text");
    const firstContextRow = document.querySelector(".provider-context-row");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]?.[0] ?? "")).toContain(
      "/enrichment/status/job-123?since=0"
    );
    expect(firstProgressText?.textContent).toBe(`1/${STREAMED_RESULTS.length} providers complete`);
    expect(firstContextRow).not.toBeNull();

    await vi.advanceTimersByTimeAsync(750);
    await vi.advanceTimersByTimeAsync(150);

    const warning = document.getElementById("enrich-warning");
    const progress = document.getElementById("enrich-progress");
    const progressText = document.getElementById("enrich-progress-text");
    const exportBtn = document.getElementById("export-btn");
    const copyBtn = document.querySelector<HTMLElement>(".copy-btn");
    const summaryRow = document.querySelector<HTMLElement>(".ioc-summary-row");
    const detailLink = document.querySelector<HTMLAnchorElement>(".detail-link");
    const reputationRows = document.querySelectorAll(
      ".enrichment-section--reputation .provider-detail-row"
    );
    const noDataRows = document.querySelectorAll(
      ".enrichment-section--no-data .provider-detail-row"
    );
    const root = document.querySelector<HTMLElement>(".page-results");

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[1]?.[0] ?? "")).toContain(
      "/enrichment/status/job-123?since=1"
    );
    expect(warning?.style.display).toBe("none");
    expect(warning?.textContent).toBe("");
    expect(progress?.classList.contains("complete")).toBe(true);
    expect(progressText?.textContent).toBe("Enrichment complete");
    expect(exportBtn?.hasAttribute("disabled")).toBe(false);
    expect(copyBtn?.getAttribute("data-enrichment")).toBe(
      "VirusTotal: malicious (2/70 engines)"
    );
    expect(summaryRow?.textContent).toContain("MALICIOUS");
    expect(detailLink?.getAttribute("href")).toBe("/ioc/ipv4/1.2.3.4");
    expect(reputationRows).toHaveLength(2);
    expect(noDataRows).toHaveLength(1);
    expect(root?.getAttribute("data-results-runtime")).toBe("live");
    expect(root?.getAttribute("data-results-expand-wired")).toBe("true");
    expect(root?.getAttribute("data-results-export-wired")).toBe("true");

    await vi.advanceTimersByTimeAsync(1500);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
