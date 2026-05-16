import type { EnrichmentItem } from "../types/api";
import { copyAllIOCs, exportCSV, exportJSON } from "./export";
import { initExportButton, sortDetailRows } from "./shared-rendering";
import { readFileSync } from "node:fs";

vi.mock("./export", () => ({
  copyAllIOCs: vi.fn(),
  exportCSV: vi.fn(),
  exportJSON: vi.fn(),
}));

function appendRow(container: HTMLElement, provider: string, verdict: string): HTMLElement {
  const row = document.createElement("div");
  row.className = "provider-detail-row";
  row.setAttribute("data-verdict", verdict);
  row.textContent = provider;
  container.appendChild(row);
  return row;
}

describe("sortDetailRows", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("sorts by cached severity without rereading row verdicts in the comparator", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    appendRow(container, "Clean", "clean");
    appendRow(container, "Malicious", "malicious");
    appendRow(container, "Suspicious", "suspicious");
    appendRow(container, "Error", "error");

    const getAttributeSpy = vi.spyOn(HTMLElement.prototype, "getAttribute");

    sortDetailRows(container);

    const sortedProviders = Array.from(container.querySelectorAll(".provider-detail-row")).map(
      (row) => row.textContent
    );
    const verdictReads = getAttributeSpy.mock.calls.filter(([name]) => name === "data-verdict");

    expect(sortedProviders).toEqual(["Malicious", "Suspicious", "Clean", "Error"]);
    expect(verdictReads).toHaveLength(4);
  });

  it("decorates rows with an indexed NodeList pass", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    appendRow(container, "Clean", "clean");
    appendRow(container, "Malicious", "malicious");
    appendRow(container, "Suspicious", "suspicious");

    const originalFrom = Array.from;
    Array.from = function () {
      throw new Error("sortDetailRows should not allocate through Array.from().map()");
    } as typeof Array.from;

    try {
      sortDetailRows(container);
    } finally {
      Array.from = originalFrom;
    }

    const sortedProviders = originalFrom(
      container.querySelectorAll(".provider-detail-row"),
      (row) => row.textContent
    );
    expect(sortedProviders).toEqual(["Malicious", "Suspicious", "Clean"]);
  });

  it("re-appends sorted rows with indexed access", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    appendRow(container, "Clean", "clean");
    appendRow(container, "Malicious", "malicious");
    const source = readFileSync(
      `${process.cwd()}/app/static/src/ts/modules/shared-rendering.ts`,
      "utf8"
    );

    sortDetailRows(container);

    expect(source).not.toContain("for (const { row } of rows)");
    expect(Array.from(container.children, (row) => row.textContent)).toEqual(["Malicious", "Clean"]);
  });

  it("skips sorting and reappend work for a single detail row", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    const onlyRow = appendRow(container, "Only", "clean");
    const appendChildSpy = vi.spyOn(container, "appendChild");
    const getAttributeSpy = vi.spyOn(HTMLElement.prototype, "getAttribute");
    const source = readFileSync(
      `${process.cwd()}/app/static/src/ts/modules/shared-rendering.ts`,
      "utf8"
    );

    sortDetailRows(container);

    expect(appendChildSpy).not.toHaveBeenCalled();
    expect(getAttributeSpy).not.toHaveBeenCalledWith("data-verdict");
    expect(container.firstElementChild).toBe(onlyRow);
    expect(source).toContain("if (rowNodes.length <= 1) return;");
    expect(source).not.toContain("if (rows.length <= 1) return;");
  });

  it("orders two detail rows without invoking Array sort", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    appendRow(container, "Clean", "clean");
    appendRow(container, "Malicious", "malicious");
    const originalSort = Array.prototype.sort;
    Array.prototype.sort = function (...args) {
      if (this.length > 0 && this[0] && typeof this[0] === "object" && "row" in this[0]) {
        throw new Error("two-row severity ordering should not call Array.sort()");
      }
      return originalSort.apply(this, args);
    };

    try {
      sortDetailRows(container);
    } finally {
      Array.prototype.sort = originalSort;
    }

    expect(Array.from(container.children, (row) => row.textContent)).toEqual([
      "Malicious",
      "Clean",
    ]);
  });

  it("orders three detail rows without invoking Array sort", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    appendRow(container, "Clean", "clean");
    appendRow(container, "Malicious", "malicious");
    appendRow(container, "Suspicious", "suspicious");
    const originalSort = Array.prototype.sort;
    Array.prototype.sort = function (...args) {
      if (this.length > 0 && this[0] && typeof this[0] === "object" && "row" in this[0]) {
        throw new Error("three-row severity ordering should not call Array.sort()");
      }
      return originalSort.apply(this, args);
    };

    try {
      sortDetailRows(container);
    } finally {
      Array.prototype.sort = originalSort;
    }

    expect(Array.from(container.children, (row) => row.textContent)).toEqual([
      "Malicious",
      "Suspicious",
      "Clean",
    ]);
  });

  it("skips reappend work when detail rows are already severity sorted", () => {
    const container = document.createElement("div");
    document.body.appendChild(container);
    appendRow(container, "Malicious", "malicious");
    appendRow(container, "Suspicious", "suspicious");
    appendRow(container, "Clean", "clean");
    appendRow(container, "Error", "error");
    const appendChildSpy = vi.spyOn(container, "appendChild");

    sortDetailRows(container);

    expect(appendChildSpy).not.toHaveBeenCalled();
    expect(Array.from(container.children, (row) => row.textContent)).toEqual([
      "Malicious",
      "Suspicious",
      "Clean",
      "Error",
    ]);
  });
});

describe("initExportButton", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.mocked(copyAllIOCs).mockClear();
    vi.mocked(exportCSV).mockClear();
    vi.mocked(exportJSON).mockClear();
    document.body.innerHTML = "";
  });

  it("uses one delegated dropdown handler for export actions", () => {
    document.body.innerHTML = `
      <section class="page-results">
        <div class="export-group">
          <button id="export-btn" type="button">Export</button>
          <div id="export-dropdown" style="display: none;">
            <button data-export="json" type="button"><span>JSON</span></button>
            <button data-export="csv" type="button"><span>CSV</span></button>
            <button data-export="iocs" type="button"><span>IOCs</span></button>
          </div>
        </div>
      </section>
    `;
    const pageResults = document.querySelector<HTMLElement>(".page-results")!;
    const dropdown = document.getElementById("export-dropdown")!;
    const addEventListenerSpy = vi.spyOn(dropdown, "addEventListener");
    const querySelectorAllSpy = vi
      .spyOn(dropdown, "querySelectorAll")
      .mockImplementation(() => {
        throw new Error("export dropdown should use delegated action handling");
      });
    const results = [{ type: "error", ioc_value: "1.2.3.4" }] as EnrichmentItem[];

    initExportButton(results, pageResults);

    document.querySelector<HTMLElement>('[data-export="json"] span')?.click();
    document.querySelector<HTMLElement>('[data-export="csv"] span')?.click();
    document.querySelector<HTMLElement>('[data-export="iocs"] span')?.click();

    expect(querySelectorAllSpy).not.toHaveBeenCalled();
    expect(addEventListenerSpy.mock.calls.filter(([eventName]) => eventName === "click")).toHaveLength(1);
    expect(exportJSON).toHaveBeenCalledWith(results);
    expect(exportCSV).toHaveBeenCalledWith(results);
    expect(copyAllIOCs).toHaveBeenCalledWith(
      document.querySelector<HTMLElement>('[data-export="iocs"]'),
      results
    );
  });

  it("reuses cached export controls when callers already resolved them", () => {
    document.body.innerHTML = `
      <section class="page-results">
        <div class="export-group">
          <button id="export-btn" type="button">Export</button>
          <div id="export-dropdown" style="display: none;">
            <button data-export="json" type="button">JSON</button>
          </div>
        </div>
      </section>
    `;
    const pageResults = document.querySelector<HTMLElement>(".page-results")!;
    const exportButton = document.getElementById("export-btn")!;
    const dropdown = document.getElementById("export-dropdown")!;
    const getElementByIdSpy = vi.spyOn(document, "getElementById");
    const results = [{ type: "error", ioc_value: "1.2.3.4" }] as EnrichmentItem[];

    initExportButton(results, pageResults, { exportButton, dropdown });

    exportButton.click();
    dropdown.querySelector<HTMLElement>('[data-export="json"]')?.click();

    expect(getElementByIdSpy).not.toHaveBeenCalledWith("export-btn");
    expect(getElementByIdSpy).not.toHaveBeenCalledWith("export-dropdown");
    expect(dropdown.style.display).toBe("none");
    expect(exportJSON).toHaveBeenCalledWith(results);
  });

  it("copies IOC values from accumulated results without scanning cards", () => {
    document.body.innerHTML = `
      <section class="page-results">
        <div class="export-group">
          <button id="export-btn" type="button">Export</button>
          <div id="export-dropdown" style="display: none;">
            <button data-export="iocs" type="button"><span>IOCs</span></button>
          </div>
        </div>
        <article class="ioc-card" data-ioc-value="stale.example"></article>
      </section>
    `;
    const pageResults = document.querySelector<HTMLElement>(".page-results")!;
    const querySelectorAllSpy = vi.spyOn(document, "querySelectorAll").mockImplementation(() => {
      throw new Error("copy-all IOC export should use accumulated results");
    });
    const results = [
      { type: "error", ioc_value: "1.2.3.4" },
      { type: "result", ioc_value: "evil.example" },
    ] as EnrichmentItem[];

    initExportButton(results, pageResults);

    document.querySelector<HTMLElement>('[data-export="iocs"] span')?.click();

    expect(querySelectorAllSpy).not.toHaveBeenCalled();
    expect(copyAllIOCs).toHaveBeenCalledWith(
      document.querySelector<HTMLElement>('[data-export="iocs"]'),
      results
    );
  });
});
