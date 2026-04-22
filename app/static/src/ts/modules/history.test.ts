/**
 * Focused tests for history.ts replay ownership and one-time wiring.
 */

function installCssEscape(): void {
  vi.stubGlobal("CSS", {
    escape(value: string): string {
      return value;
    },
  });
}

function buildHistoryDom(historyResults: string): void {
  document.body.innerHTML = `
    <div class="page-results"
         data-results-owner="history"
         data-job-id="history"
         data-mode="online"
         data-provider-counts='{"ipv4":1}'
         data-history-results='${historyResults}'>
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

  it("replays stored results without leaking live polling and wires listeners once", async () => {
    buildHistoryDom(
      JSON.stringify([
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
      ])
    );

    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { init } = await import("./history");
    init();
    init();

    const root = document.querySelector<HTMLElement>(".page-results");
    const exportBtn = document.getElementById("export-btn") as HTMLButtonElement;
    const dropdown = document.getElementById("export-dropdown") as HTMLElement;
    const summaryRow = document.querySelector<HTMLElement>(".ioc-summary-row");
    const details = document.querySelector<HTMLElement>(".enrichment-details");
    const progress = document.getElementById("enrich-progress");
    const progressText = document.getElementById("enrich-progress-text");

    expect(fetchMock).not.toHaveBeenCalled();
    expect(root?.getAttribute("data-results-runtime")).toBe("history");
    expect(root?.getAttribute("data-results-expand-wired")).toBe("true");
    expect(root?.getAttribute("data-results-export-wired")).toBe("true");
    expect(progress?.classList.contains("complete")).toBe(true);
    expect(progressText?.textContent).toBe("Enrichment complete");
    expect(exportBtn.hasAttribute("disabled")).toBe(false);

    exportBtn.click();
    expect(dropdown.style.display).toBe("");

    summaryRow?.click();
    expect(details?.classList.contains("is-open")).toBe(true);
  });

  it("treats an empty history payload as complete without enabling export", async () => {
    buildHistoryDom("[]");

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
});
