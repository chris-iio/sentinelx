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

function buildCardWithoutSlot(iocValue: string, iocType = "ipv4"): string {
  return `
    <div class="ioc-card" data-ioc-value="${iocValue}" data-ioc-type="${iocType}" data-verdict="no_data">
      <div class="ioc-card-header">
        <div class="ioc-row-left">
          <span class="verdict-label verdict-label--no_data">NO DATA</span>
          <code class="ioc-value">${iocValue}</code>
        </div>
      </div>
      <div class="ioc-context-line"></div>
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

async function importCoordinatorWithCardSpies(): Promise<{
  createResultApplicationCoordinator: typeof import("./result-application").createResultApplicationCoordinator;
  updateDashboardCountsSpy: ReturnType<typeof vi.fn>;
  sortCardsBySeveritySpy: ReturnType<typeof vi.fn>;
}> {
  const actualCards = await vi.importActual<typeof import("./cards")>("./cards");
  const updateDashboardCountsSpy = vi.fn(actualCards.updateDashboardCounts);
  const sortCardsBySeveritySpy = vi.fn(actualCards.sortCardsBySeverity);

  vi.doMock("./cards", () => ({
    ...actualCards,
    updateDashboardCounts: updateDashboardCountsSpy,
    sortCardsBySeverity: sortCardsBySeveritySpy,
  }));

  const { createResultApplicationCoordinator } = await import("./result-application");
  return { createResultApplicationCoordinator, updateDashboardCountsSpy, sortCardsBySeveritySpy };
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

  it("caches stable IOC handles and provider counts across repeated apply, flush, and finalize calls", async () => {
    buildDom(buildCard("1.2.3.4") + buildCard("5.6.7.8"), '{"ipv4":2}');
    const { createResultApplicationCoordinator } = await import("./result-application");
    const querySelectorSpy = vi.spyOn(Document.prototype, "querySelector");
    const jsonParseSpy = vi.spyOn(JSON, "parse");
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(
      resultItem({
        provider: "VirusTotal",
        verdict: "clean",
        ioc_value: "1.2.3.4",
      })
    );
    coordinator.flush();
    coordinator.apply(
      resultItem({
        provider: "ThreatFox",
        verdict: "malicious",
        detection_count: 1,
        total_engines: 1,
        ioc_value: "1.2.3.4",
      })
    );
    coordinator.apply(
      resultItem({
        provider: "VirusTotal",
        verdict: "clean",
        ioc_value: "5.6.7.8",
      })
    );

    coordinator.finalize();
    await vi.advanceTimersByTimeAsync(150);

    const cardLookupCalls = querySelectorSpy.mock.calls.filter(([selector]) =>
      selector === '.ioc-card[data-ioc-value="1.2.3.4"]' ||
      selector === '.ioc-card[data-ioc-value="5.6.7.8"]'
    );

    expect(jsonParseSpy).toHaveBeenCalledTimes(1);
    expect(cardLookupCalls).toHaveLength(2);
    expect(
      document.querySelector('.ioc-card[data-ioc-value="1.2.3.4"]')?.getAttribute("data-verdict")
    ).toBe("malicious");
    expect(
      document.querySelector('.ioc-card[data-ioc-value="5.6.7.8"] .detail-link')
    ).not.toBeNull();
  });

  it.each([
    { label: "missing", providerCounts: null },
    { label: "malformed", providerCounts: "not-json" },
  ])(
    "falls back to default provider counts when page metadata is $label",
    async ({ providerCounts }) => {
      buildDom(buildCard("1.2.3.4"));
      const pageResults = document.querySelector<HTMLElement>(".page-results");
      if (providerCounts === null) {
        pageResults?.removeAttribute("data-provider-counts");
      } else {
        pageResults?.setAttribute("data-provider-counts", providerCounts);
      }

      const { createResultApplicationCoordinator } = await import("./result-application");
      const jsonParseSpy = vi.spyOn(JSON, "parse");
      const coordinator = createResultApplicationCoordinator();

      coordinator.apply(
        resultItem({
          provider: "IP Context",
          raw_stats: {
            geo: "Tokyo, JP",
          },
        })
      );
      coordinator.flush();

      expect(document.querySelector(".enrichment-waiting-text")?.textContent).toBe(
        "1 provider still loading..."
      );
      expect(jsonParseSpy).toHaveBeenCalledTimes(providerCounts === null ? 0 : 1);
    }
  );

  it("ignores missing cards and malformed slot structure without breaking valid IOC application", async () => {
    buildDom(buildCardWithoutSlot("1.2.3.4") + buildCard("5.6.7.8"));
    const { createResultApplicationCoordinator } = await import("./result-application");
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(
      resultItem({
        ioc_value: "1.2.3.4",
        provider: "VirusTotal",
        verdict: "malicious",
        detection_count: 1,
        total_engines: 10,
      })
    );
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

    const malformedCard = document.querySelector<HTMLElement>('.ioc-card[data-ioc-value="1.2.3.4"]');
    const validCard = document.querySelector<HTMLElement>('.ioc-card[data-ioc-value="5.6.7.8"]');

    expect(malformedCard?.querySelector(".detail-link")).toBeNull();
    expect(validCard?.getAttribute("data-verdict")).toBe("clean");
    expect(validCard?.querySelector(".detail-link")).not.toBeNull();
  });

  it("renders EmailRep through the shared result application path for email cards", async () => {
    const email = "analyst@example.com";
    const scriptLike = '<script data-provider="emailrep">alert(1)</script>';
    buildDom(buildCard(email, "email"), '{"email":1}');
    const { createResultApplicationCoordinator } = await import("./result-application");
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(
      resultItem({
        ioc_value: email,
        ioc_type: "email",
        provider: "EmailRep",
        verdict: "suspicious",
        detection_count: 1,
        total_engines: 1,
        raw_stats: {
          reputation: "medium",
          references: 7,
          risk_flags: ["credentials_leaked", "spoofable", scriptLike],
          domain_reputation: "low",
          profiles: ["github", "twitter"],
          first_seen: "2023-01-01",
          last_seen: "2024-06-15",
          deliverable: true,
          valid_mx: false,
          spoofable: true,
          spf_strict: false,
          dmarc_enforced: true,
          unknown_nested: { should: "not render" },
          nested_reputation: { reputation: "raw object must stay hidden" },
        },
      })
    );
    coordinator.flush();
    coordinator.finalize();
    await vi.advanceTimersByTimeAsync(150);

    const card = document.querySelector<HTMLElement>(`.ioc-card[data-ioc-value="${email}"]`);
    const verdictLabel = card?.querySelector<HTMLElement>(".verdict-label");
    const summary = card?.querySelector<HTMLElement>(".ioc-summary-row");
    const repRows = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".enrichment-section--reputation .provider-detail-row"
      )
    );
    const contextRows = document.querySelectorAll(
      ".enrichment-section--context .provider-detail-row"
    );
    const noDataRows = document.querySelectorAll(
      ".enrichment-section--no-data .provider-detail-row"
    );
    const emailRepRow = repRows.find(
      (row) => row.querySelector(".provider-detail-name")?.textContent === "EmailRep"
    );
    const fieldText = Array.from(
      emailRepRow?.querySelectorAll<HTMLElement>(".provider-context-field") ?? []
    ).map((field) => field.textContent);
    const renderedText = document.body.textContent ?? "";

    expect(card?.getAttribute("data-verdict")).toBe("suspicious");
    expect(verdictLabel?.textContent).toBe("SUSPICIOUS");
    expect(verdictLabel?.classList.contains("verdict-label--suspicious")).toBe(true);
    expect(summary?.textContent).toContain("SUSPICIOUS");
    expect(summary?.textContent).toContain("EmailRep: Suspicious");
    expect(repRows).toHaveLength(1);
    expect(emailRepRow).not.toBeUndefined();
    expect(emailRepRow?.getAttribute("data-verdict")).toBe("suspicious");
    expect(contextRows).toHaveLength(0);
    expect(noDataRows).toHaveLength(0);
    expect(fieldText).toEqual([
      "Reputation: medium",
      "Refs: 7",
      "Risks: credentials_leakedspoofable" + scriptLike,
      "Domain: low",
      "Profiles: githubtwitter",
      "First seen: 2023-01-01",
      "Last seen: 2024-06-15",
      "Deliverable: true",
      "MX: false",
      "Spoofable: true",
      "SPF: false",
      "DMARC: true",
    ]);
    expect(emailRepRow?.querySelector("script")).toBeNull();
    expect(emailRepRow?.innerHTML).not.toContain("<script");
    expect(renderedText).not.toContain("[object Object]");
    expect(renderedText).not.toContain("unknown_nested");
    expect(renderedText).not.toContain("raw object must stay hidden");
    expect(document.querySelector(".enrichment-waiting-text")).toBeNull();
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

  it("does not run global dashboard recount or card reorder for provider-only deltas with unchanged severity", async () => {
    buildDom(buildCard("1.2.3.4"), '{"ipv4":2}');
    const { createResultApplicationCoordinator, updateDashboardCountsSpy, sortCardsBySeveritySpy } =
      await importCoordinatorWithCardSpies();
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(
      resultItem({
        provider: "ThreatFox",
        verdict: "malicious",
        detection_count: 1,
        total_engines: 1,
      })
    );
    coordinator.flush();

    expect(updateDashboardCountsSpy).toHaveBeenCalled();
    expect(sortCardsBySeveritySpy).toHaveBeenCalled();
    updateDashboardCountsSpy.mockClear();
    sortCardsBySeveritySpy.mockClear();

    coordinator.apply(
      resultItem({
        provider: "GreyNoise",
        verdict: "clean",
        detection_count: 0,
        total_engines: 1,
      })
    );
    coordinator.flush();

    const summary = document.querySelector<HTMLElement>(".ioc-summary-row");
    const providerNames = Array.from(
      document.querySelectorAll<HTMLElement>(".provider-detail-name")
    ).map((node) => node.textContent);

    expect(document.querySelector('[data-verdict-count="malicious"]')?.textContent).toBe("1");
    expect(document.querySelector('[data-verdict-count="clean"]')?.textContent).toBe("0");
    expect(document.querySelector('.ioc-card')?.getAttribute("data-verdict")).toBe("malicious");
    expect(summary?.textContent).toContain("ThreatFox: 1/1 engines");
    expect(providerNames).toEqual(["ThreatFox", "GreyNoise"]);
  });

  it("runs global recount and reorder when a delta changes card severity/order state", async () => {
    buildDom(buildCard("1.2.3.4") + buildCard("5.6.7.8"), '{"ipv4":1}');
    const { createResultApplicationCoordinator, updateDashboardCountsSpy, sortCardsBySeveritySpy } =
      await importCoordinatorWithCardSpies();
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(resultItem({ provider: "VirusTotal", verdict: "clean", ioc_value: "1.2.3.4" }));
    coordinator.apply(resultItem({ provider: "VirusTotal", verdict: "clean", ioc_value: "5.6.7.8" }));
    coordinator.flush();
    await vi.advanceTimersByTimeAsync(150);

    expect(updateDashboardCountsSpy).toHaveBeenCalled();
    expect(sortCardsBySeveritySpy).toHaveBeenCalled();
    updateDashboardCountsSpy.mockClear();
    sortCardsBySeveritySpy.mockClear();

    coordinator.apply(
      resultItem({
        provider: "ThreatFox",
        verdict: "malicious",
        detection_count: 1,
        total_engines: 1,
        ioc_value: "5.6.7.8",
      })
    );
    coordinator.flush();
    await vi.advanceTimersByTimeAsync(150);

    const orderedIocs = Array.from(document.querySelectorAll<HTMLElement>(".ioc-card")).map((card) =>
      card.getAttribute("data-ioc-value")
    );

    expect(updateDashboardCountsSpy).toHaveBeenCalledTimes(1);
    expect(sortCardsBySeveritySpy).toHaveBeenCalledTimes(1);
    expect(orderedIocs).toEqual(["5.6.7.8", "1.2.3.4"]);
    expect(document.querySelector('[data-verdict-count="malicious"]')?.textContent).toBe("1");
    expect(document.querySelector('[data-verdict-count="clean"]')?.textContent).toBe("1");
  });

  it("preserves history-replay copy, export, and detail-link affordances without extra global work on unchanged severity", async () => {
    buildDom(buildCard("1.2.3.4"), '{"ipv4":2}');
    const { createResultApplicationCoordinator, updateDashboardCountsSpy, sortCardsBySeveritySpy } =
      await importCoordinatorWithCardSpies();
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(
      resultItem({
        provider: "ThreatFox",
        verdict: "malicious",
        detection_count: 1,
        total_engines: 1,
      })
    );
    coordinator.flush();
    expect(updateDashboardCountsSpy).toHaveBeenCalled();
    expect(sortCardsBySeveritySpy).toHaveBeenCalled();
    updateDashboardCountsSpy.mockClear();
    sortCardsBySeveritySpy.mockClear();
    coordinator.apply(
      resultItem({
        provider: "VirusTotal",
        verdict: "clean",
        detection_count: 0,
        total_engines: 70,
      })
    );
    coordinator.finalize();
    await vi.advanceTimersByTimeAsync(150);

    const copyBtn = document.querySelector<HTMLElement>(".copy-btn");
    const detailLink = document.querySelector<HTMLAnchorElement>(".detail-link");
    const noDataSummary = document.querySelector(".no-data-summary-row");

    expect(document.querySelector('[data-verdict-count="malicious"]')?.textContent).toBe("1");
    expect(document.querySelector('[data-verdict-count="clean"]')?.textContent).toBe("0");
    expect(copyBtn?.textContent).toBe("Copy");
    expect(copyBtn?.getAttribute("data-value")).toBe("1.2.3.4");
    expect(copyBtn?.getAttribute("data-enrichment")).toBe("ThreatFox: malicious (1/1 engines)");
    expect(detailLink?.getAttribute("href")).toBe("/ioc/ipv4/1.2.3.4");
    expect(detailLink?.textContent).toContain("View full detail");
    expect(noDataSummary).toBeNull();
  });

  it("renders malicious-looking provider text as inert text on the real detail row path", async () => {
    const provider = '<img src=x onerror="alert(1)">Provider';
    buildDom(buildCard("1.2.3.4"), '{"ipv4":1}');
    const { createResultApplicationCoordinator } = await import("./result-application");
    const coordinator = createResultApplicationCoordinator();

    coordinator.apply(resultItem({ provider, verdict: "clean" }));
    coordinator.finalize();

    const providerName = document.querySelector<HTMLElement>(".provider-detail-name");

    expect(providerName?.textContent).toBe(provider);
    expect(providerName?.querySelector("img")).toBeNull();
    expect(document.querySelector("img")).toBeNull();
    expect(providerName?.innerHTML).not.toContain("<img");
    expect(document.body.innerHTML).not.toContain('<img src=x onerror="alert(1)">');
  });
});
