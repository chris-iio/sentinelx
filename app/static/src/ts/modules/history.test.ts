import type { EnrichmentItem, EnrichmentStatus } from "../types/api";

/**
 * Focused tests for history.ts replay ownership and parity with live results.
 */

function installCssEscape(): void {
  vi.stubGlobal("CSS", {
    escape(value: string): string {
      return value;
    },
  });
}

const PARITY_RESULTS: EnrichmentItem[] = [
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

function buildResultsDom(options: {
  owner?: "history" | "live";
  jobId?: string;
  providerCounts?: string;
  historyResults?: string;
} = {}): void {
  const {
    owner = "history",
    jobId = owner === "history" ? "history" : "job-123",
    providerCounts = '{"ipv4":4}',
    historyResults,
  } = options;

  const historyAttr = historyResults
    ? ` data-history-results='${historyResults}'`
    : "";

  document.body.innerHTML = `
    <div class="page-results"
         data-results-owner="${owner}"
         data-job-id="${jobId}"
         data-mode="online"
         data-provider-counts='${providerCounts}'${historyAttr}>
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

function normalizeText(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

function readDetailRows(selector: string): Array<{ provider: string; verdict: string; stat: string }> {
  return Array.from(document.querySelectorAll<HTMLElement>(selector)).map((row) => ({
    provider: normalizeText(row.querySelector(".provider-detail-name")?.textContent),
    verdict: normalizeText(row.querySelector(".verdict-badge")?.textContent),
    stat: normalizeText(row.querySelector(".provider-detail-stat")?.textContent),
  }));
}

function readContextRows(): Array<{ provider: string; text: string }> {
  return Array.from(
    document.querySelectorAll<HTMLElement>(
      ".enrichment-section--context .provider-context-row"
    )
  ).map((row) => ({
    provider: normalizeText(row.querySelector(".provider-detail-name")?.textContent),
    text: normalizeText(row.textContent),
  }));
}

function readVisibleState() {
  const root = document.querySelector<HTMLElement>(".page-results");
  const card = document.querySelector<HTMLElement>('.ioc-card[data-ioc-value="1.2.3.4"]');
  const warning = document.getElementById("enrich-warning");
  const progress = document.getElementById("enrich-progress");
  const progressText = document.getElementById("enrich-progress-text");
  const exportBtn = document.getElementById("export-btn") as HTMLButtonElement | null;
  const copyBtn = document.querySelector<HTMLElement>(".copy-btn");
  const summaryRow = document.querySelector<HTMLElement>(".ioc-summary-row");
  const detailLink = document.querySelector<HTMLAnchorElement>(".detail-link");
  const noDataSummary = document.querySelector<HTMLElement>(".no-data-summary-row");

  return {
    runtime: root?.getAttribute("data-results-runtime"),
    progressComplete: progress?.classList.contains("complete") ?? false,
    progressText: normalizeText(progressText?.textContent),
    warningDisplay: warning?.style.display ?? "",
    warningText: normalizeText(warning?.textContent),
    exportEnabled: exportBtn ? !exportBtn.hasAttribute("disabled") : false,
    cardVerdict: card?.getAttribute("data-verdict"),
    verdictLabel: normalizeText(card?.querySelector(".verdict-label")?.textContent),
    copyEnrichment: copyBtn?.getAttribute("data-enrichment"),
    summaryText: normalizeText(summaryRow?.textContent),
    detailLinkHref: detailLink?.getAttribute("href"),
    detailLinkText: normalizeText(detailLink?.textContent),
    noDataSummaryText: normalizeText(noDataSummary?.textContent),
    dashboard: {
      malicious: normalizeText(
        document.querySelector('[data-verdict-count="malicious"]')?.textContent
      ),
      suspicious: normalizeText(
        document.querySelector('[data-verdict-count="suspicious"]')?.textContent
      ),
      clean: normalizeText(
        document.querySelector('[data-verdict-count="clean"]')?.textContent
      ),
      knownGood: normalizeText(
        document.querySelector('[data-verdict-count="known_good"]')?.textContent
      ),
      noData: normalizeText(
        document.querySelector('[data-verdict-count="no_data"]')?.textContent
      ),
    },
    reputationRows: readDetailRows(
      ".enrichment-section--reputation .provider-detail-row"
    ),
    noDataRows: readDetailRows(
      ".enrichment-section--no-data .provider-detail-row"
    ),
    contextRows: readContextRows(),
  };
}

function comparableParityState(state: ReturnType<typeof readVisibleState>) {
  const { runtime: _runtime, ...comparable } = state;
  return comparable;
}

describe("history replay", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.useFakeTimers();
    installCssEscape();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  it("matches the live results surface for equivalent stored results and never polls history status", async () => {
    buildResultsDom({ historyResults: JSON.stringify(PARITY_RESULTS) });

    const historyFetch = vi.fn();
    vi.stubGlobal("fetch", historyFetch);

    const { init: initHistory } = await import("./history");
    initHistory();
    await vi.advanceTimersByTimeAsync(1500);

    const historyState = readVisibleState();

    expect(historyFetch).not.toHaveBeenCalled();
    expect(historyState.runtime).toBe("history");
    expect(historyState.warningDisplay).toBe("none");
    expect(historyState.warningText).toBe("");

    buildResultsDom({ owner: "live", jobId: "job-123" });

    const liveFetch = mockFetchSequence({
      ok: true,
      data: {
        total: PARITY_RESULTS.length,
        done: PARITY_RESULTS.length,
        complete: true,
        results: PARITY_RESULTS,
        next_since: PARITY_RESULTS.length,
        status: "complete",
        terminal: false,
        terminal_reason: null,
        error: null,
      },
    });

    const { init: initEnrichment } = await import("./enrichment");
    initEnrichment();
    await vi.advanceTimersByTimeAsync(750);
    await vi.advanceTimersByTimeAsync(150);

    const liveState = readVisibleState();

    expect(liveFetch).toHaveBeenCalledTimes(1);
    expect(String(liveFetch.mock.calls[0]?.[0] ?? "")).toContain(
      "/enrichment/status/job-123?since=0"
    );
    expect(liveState.runtime).toBe("live");
    expect(liveState.warningDisplay).toBe("none");
    expect(liveState.warningText).toBe("");
    expect(comparableParityState(historyState)).toEqual(comparableParityState(liveState));
  });

  it("treats an empty history payload as complete without enabling export", async () => {
    buildResultsDom({ historyResults: "[]", providerCounts: '{"ipv4":1}' });

    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { init } = await import("./history");
    init();

    const root = document.querySelector<HTMLElement>(".page-results");
    const exportBtn = document.getElementById("export-btn");
    const progress = document.getElementById("enrich-progress");
    const progressText = document.getElementById("enrich-progress-text");
    const summaryRow = document.querySelector(".ioc-summary-row");

    expect(fetchMock).not.toHaveBeenCalled();
    expect(root?.getAttribute("data-results-runtime")).toBe("history");
    expect(progress?.classList.contains("complete")).toBe(true);
    expect(progressText?.textContent).toBe("Enrichment complete");
    expect(exportBtn?.hasAttribute("disabled")).toBe(true);
    expect(summaryRow).toBeNull();
  });

  it("fails loudly on malformed history JSON instead of polling or showing a false terminal banner", async () => {
    buildResultsDom({ historyResults: "not-json" });

    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { init } = await import("./history");
    init();
    await vi.advanceTimersByTimeAsync(1500);

    const root = document.querySelector<HTMLElement>(".page-results");
    const warning = document.getElementById("enrich-warning");
    const progress = document.getElementById("enrich-progress");
    const exportBtn = document.getElementById("export-btn");

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      "[history] Failed to parse data-history-results JSON"
    );
    expect(fetchMock).not.toHaveBeenCalled();
    expect(root?.getAttribute("data-results-runtime")).toBeNull();
    expect(progress?.classList.contains("complete")).toBe(false);
    expect(warning?.style.display).toBe("none");
    expect(warning?.textContent).toBe("");
    expect(exportBtn?.hasAttribute("disabled")).toBe(true);
  });
});
