/**
 * Focused unit tests for result-application.ts shared live/history coordinator.
 */

import type { EnrichmentItem, EnrichmentResultItem } from "../types/api";

function installCssEscape(): void {
  vi.stubGlobal("CSS", {
    escape(value: string): string {
      return value;
    },
  });
}

function buildCard(iocValue: string, iocType = "ipv4"): string {
  return `
    <div class="ioc-card" data-ioc-value="${iocValue}" data-ioc-type="${iocType}" data-verdict="no_data">
      <div class="ioc-card-header">
        <div class="ioc-row-left">
          <span class="verdict-label verdict-label--no_data">NO DATA</span>
          <span class="ioc-type-badge">${iocType}</span>
          <code class="ioc-value">${iocValue}</code>
        </div>
        <div class="ioc-card-actions">
          <button class="btn btn-copy copy-btn" data-value="${iocValue}" type="button">Copy</button>
        </div>
      </div>
      <div class="ioc-context-line"></div>
      <div class="enrichment-slot">
        <div class="spinner-wrapper shimmer-wrapper"></div>
        <div class="enrichment-details">
          <div class="enrichment-section enrichment-section--context">
            <div class="provider-section-header">Infrastructure Context</div>
          </div>
          <div class="enrichment-section enrichment-section--reputation">
            <div class="provider-section-header">Reputation</div>
          </div>
          <div class="enrichment-section enrichment-section--no-data">
            <div class="provider-section-header">No Data</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function buildDom(cards: string, providerCounts = '{"ipv4":4}'): void {
  document.body.innerHTML = `
    <div class="page-results" data-provider-counts='${providerCounts}'>
      <div class="verdict-dashboard" id="verdict-dashboard">
        <span data-verdict-count="malicious">0</span>
        <span data-verdict-count="suspicious">0</span>
        <span data-verdict-count="clean">0</span>
        <span data-verdict-count="known_good">0</span>
        <span data-verdict-count="no_data">0</span>
      </div>
      <div class="ioc-cards-grid" id="ioc-cards-grid">${cards}</div>
    </div>
  `;
}

function resultItem(
  overrides: Partial<EnrichmentResultItem> & Pick<EnrichmentResultItem, "provider">
): EnrichmentResultItem {
  return {
    type: "result",
    ioc_value: "1.2.3.4",
    ioc_type: "ipv4",
    provider: overrides.provider,
    verdict: "clean",
    detection_count: 0,
    total_engines: 95,
    scan_date: null,
    raw_stats: {},
    ...overrides,
  };
}

function errorItem(overrides: Partial<EnrichmentItem> & { provider: string; error: string }): EnrichmentItem {
  return {
    type: "error",
    ioc_value: "1.2.3.4",
    ioc_type: "ipv4",
    provider: overrides.provider,
    error: overrides.error,
    ...overrides,
  } as EnrichmentItem;
}

describe("result-application coordinator", () => {
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

  it("renders mixed context, reputation, and error rows through one shared finalize path", async () => {
    buildDom(buildCard("1.2.3.4"));
    const { createResultApplicationCoordinator } = await import("./result-application");
    const coordinator = createResultApplicationCoordinator();

    const parityResults: EnrichmentItem[] = [
      resultItem({
        provider: "IP Context",
        verdict: "no_data",
        detection_count: 0,
        total_engines: 0,
        raw_stats: {
          geo: "Tokyo, JP",
          reverse: "edge.example.net",
          flags: ["hosting"],
        },
      }),
      resultItem({
        provider: "VirusTotal",
        verdict: "malicious",
        detection_count: 2,
        total_engines: 70,
      }),
      resultItem({
        provider: "GreyNoise",
        verdict: "clean",
        detection_count: 0,
        total_engines: 1,
        raw_stats: {
          classification: "benign",
        },
      }),
      errorItem({ provider: "AbuseIPDB", error: "Timeout" }),
    ];

    for (const result of parityResults) {
      coordinator.apply(result);
    }

    coordinator.finalize();
    await vi.advanceTimersByTimeAsync(150);

    const card = document.querySelector<HTMLElement>('.ioc-card[data-ioc-value="1.2.3.4"]');
    const summary = document.querySelector<HTMLElement>(".ioc-summary-row");
    const detailLink = document.querySelector<HTMLAnchorElement>(".detail-link");
    const repRows = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".enrichment-section--reputation .provider-detail-row"
      )
    );
    const noDataRows = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".enrichment-section--no-data .provider-detail-row"
      )
    );
    const contextRows = document.querySelectorAll(
      ".enrichment-section--context .provider-context-row"
    );
    const copyBtn = document.querySelector<HTMLElement>(".copy-btn");
    const noDataSummary = document.querySelector<HTMLElement>(".no-data-summary-row");
    const maliciousCount = document.querySelector('[data-verdict-count="malicious"]');
    const noDataCount = document.querySelector('[data-verdict-count="no_data"]');

    expect(card?.getAttribute("data-verdict")).toBe("malicious");
    expect(summary).not.toBeNull();
    expect(summary?.textContent).toContain("MALICIOUS");
    expect(detailLink?.getAttribute("href")).toBe("/ioc/ipv4/1.2.3.4");
    expect(repRows.map((row) => row.querySelector(".provider-detail-name")?.textContent)).toEqual([
      "VirusTotal",
      "GreyNoise",
    ]);
    expect(noDataRows.map((row) => row.querySelector(".provider-detail-name")?.textContent)).toEqual([
      "AbuseIPDB",
    ]);
    expect(contextRows).toHaveLength(1);
    expect(copyBtn?.getAttribute("data-enrichment")).toBe(
      "VirusTotal: malicious (2/70 engines)"
    );
    expect(noDataSummary?.textContent).toBe("1 provider had no record");
    expect(maliciousCount?.textContent).toBe("1");
    expect(noDataCount?.textContent).toBe("0");
  });

  it("keeps context-only providers on the shared path without forcing summary state", async () => {
    buildDom(buildCard("1.2.3.4"), '{"ipv4":2}');
    const { createResultApplicationCoordinator } = await import("./result-application");
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(
      resultItem({
        provider: "IP Context",
        raw_stats: {},
      })
    );
    coordinator.flush();

    const card = document.querySelector<HTMLElement>('.ioc-card[data-ioc-value="1.2.3.4"]');
    const slot = card?.querySelector<HTMLElement>(".enrichment-slot");
    const contextRows = document.querySelectorAll(
      ".enrichment-section--context .provider-context-row"
    );
    const summary = document.querySelector(".ioc-summary-row");
    const waiting = document.querySelector(".enrichment-waiting-text");

    expect(slot?.classList.contains("enrichment-slot--loaded")).toBe(true);
    expect(contextRows).toHaveLength(1);
    expect(summary).toBeNull();
    expect(card?.getAttribute("data-verdict")).toBe("no_data");
    expect(waiting?.textContent).toBe("1 provider still loading...");
  });

  it("ignores missing cards without breaking valid IOC application", async () => {
    buildDom(buildCard("1.2.3.4") + buildCard("5.6.7.8"));
    const { createResultApplicationCoordinator } = await import("./result-application");
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(
      resultItem({
        ioc_value: "9.9.9.9",
        provider: "VirusTotal",
        verdict: "malicious",
        detection_count: 1,
        total_engines: 10,
      })
    );
    coordinator.apply(
      resultItem({
        ioc_value: "5.6.7.8",
        provider: "VirusTotal",
        verdict: "clean",
      })
    );

    coordinator.finalize();
    await vi.advanceTimersByTimeAsync(150);

    const validCard = document.querySelector<HTMLElement>('.ioc-card[data-ioc-value="5.6.7.8"]');
    const missingCard = document.querySelector<HTMLElement>('.ioc-card[data-ioc-value="9.9.9.9"]');
    const detailLink = validCard?.querySelector(".detail-link");

    expect(missingCard).toBeNull();
    expect(validCard?.getAttribute("data-verdict")).toBe("clean");
    expect(detailLink).not.toBeNull();
  });

  it("finalize flushes repeated results and updates copy-button worst verdict before link injection", async () => {
    buildDom(buildCard("1.2.3.4"), '{"ipv4":2}');
    const { createResultApplicationCoordinator } = await import("./result-application");
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(
      resultItem({
        provider: "VirusTotal",
        verdict: "clean",
        detection_count: 0,
        total_engines: 95,
      })
    );
    coordinator.apply(
      resultItem({
        provider: "ThreatFox",
        verdict: "malicious",
        detection_count: 1,
        total_engines: 1,
      })
    );

    coordinator.finalize();
    await vi.advanceTimersByTimeAsync(150);

    const copyBtn = document.querySelector<HTMLElement>(".copy-btn");
    const summary = document.querySelector(".ioc-summary-row");
    const detailLink = document.querySelector(".detail-link");
    const waiting = document.querySelector(".enrichment-waiting-text");

    expect(copyBtn?.getAttribute("data-enrichment")).toBe(
      "ThreatFox: malicious (1/1 engines)"
    );
    expect(summary?.textContent).toContain("MALICIOUS");
    expect(detailLink).not.toBeNull();
    expect(waiting).toBeNull();
  });
});
