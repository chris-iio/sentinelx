import { readFileSync } from "node:fs";

import { applyCardVerdict, sortCardsBySeverity, updateDashboardCounts } from "./cards";

function appendCard(grid: HTMLElement, iocValue: string, verdict: string): HTMLElement {
  const card = document.createElement("div");
  card.className = "ioc-card";
  card.dataset.iocValue = iocValue;
  card.setAttribute("data-verdict", verdict);
  grid.appendChild(card);
  return card;
}

describe("sortCardsBySeverity", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("CSS", {
      escape(value: string): string {
        return value;
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  it("sorts cards by cached severity without rereading verdicts in the comparator", async () => {
    const grid = document.createElement("div");
    grid.id = "ioc-cards-grid";
    document.body.appendChild(grid);
    appendCard(grid, "clean.example", "clean");
    appendCard(grid, "bad.example", "malicious");
    appendCard(grid, "suspicious.example", "suspicious");
    appendCard(grid, "unknown.example", "no_data");

    const getAttributeSpy = vi.spyOn(HTMLElement.prototype, "getAttribute");

    sortCardsBySeverity();
    await vi.advanceTimersByTimeAsync(150);

    const sortedIocs = Array.from(grid.querySelectorAll<HTMLElement>(".ioc-card")).map(
      (card) => card.dataset.iocValue
    );
    const verdictReads = getAttributeSpy.mock.calls.filter(([name]) => name === "data-verdict");

    expect(sortedIocs).toEqual([
      "bad.example",
      "suspicious.example",
      "clean.example",
      "unknown.example",
    ]);
    expect(verdictReads).toHaveLength(4);
  });

  it("sorts every verdict with known_good below conflicts and above clean", async () => {
    const grid = document.createElement("div");
    grid.id = "ioc-cards-grid";
    document.body.appendChild(grid);
    appendCard(grid, "error.example", "error");
    appendCard(grid, "clean.example", "clean");
    appendCard(grid, "trusted.example", "known_good");
    appendCard(grid, "unknown.example", "no_data");
    appendCard(grid, "bad.example", "malicious");
    appendCard(grid, "suspicious.example", "suspicious");

    sortCardsBySeverity();
    await vi.advanceTimersByTimeAsync(150);

    expect(Array.from(grid.children, (card) => (card as HTMLElement).dataset.iocValue)).toEqual([
      "bad.example",
      "suspicious.example",
      "trusted.example",
      "clean.example",
      "unknown.example",
      "error.example",
    ]);
  });

  it("decorates cards with an indexed NodeList pass before sorting", async () => {
    const grid = document.createElement("div");
    grid.id = "ioc-cards-grid";
    document.body.appendChild(grid);
    appendCard(grid, "clean.example", "clean");
    appendCard(grid, "bad.example", "malicious");
    appendCard(grid, "suspicious.example", "suspicious");

    const originalFrom = Array.from;
    Array.from = function () {
      throw new Error("sortCardsBySeverity should not allocate through Array.from().map()");
    } as typeof Array.from;

    try {
      sortCardsBySeverity();
      await vi.advanceTimersByTimeAsync(150);
    } finally {
      Array.from = originalFrom;
    }

    const sortedIocs = originalFrom(
      grid.querySelectorAll<HTMLElement>(".ioc-card"),
      (card) => card.dataset.iocValue
    );
    expect(sortedIocs).toEqual(["bad.example", "suspicious.example", "clean.example"]);
  });

  it("skips sorting and reappend work for a single card", async () => {
    const grid = document.createElement("div");
    grid.id = "ioc-cards-grid";
    document.body.appendChild(grid);
    const onlyCard = appendCard(grid, "only.example", "clean");
    const appendChildSpy = vi.spyOn(grid, "appendChild");
    const getAttributeSpy = vi.spyOn(HTMLElement.prototype, "getAttribute");
    const source = readFileSync(`${process.cwd()}/app/static/src/ts/modules/cards.ts`, "utf8");

    sortCardsBySeverity();
    await vi.advanceTimersByTimeAsync(150);

    expect(appendChildSpy).not.toHaveBeenCalled();
    expect(getAttributeSpy).not.toHaveBeenCalledWith("data-verdict");
    expect(grid.firstElementChild).toBe(onlyCard);
    expect(source).toContain("if (cardNodes.length <= 1) return;");
    expect(source).not.toContain("if (cards.length <= 1) return;");
  });

  it("orders two cards without invoking Array sort", async () => {
    const grid = document.createElement("div");
    grid.id = "ioc-cards-grid";
    document.body.appendChild(grid);
    appendCard(grid, "clean.example", "clean");
    appendCard(grid, "bad.example", "malicious");
    const originalSort = Array.prototype.sort;
    Array.prototype.sort = function (...args) {
      if (this.length > 0 && this[0] && typeof this[0] === "object" && "card" in this[0]) {
        throw new Error("two-card severity ordering should not call Array.sort()");
      }
      return originalSort.apply(this, args);
    };

    try {
      sortCardsBySeverity();
      await vi.advanceTimersByTimeAsync(150);
    } finally {
      Array.prototype.sort = originalSort;
    }

    expect(Array.from(grid.children, (card) => (card as HTMLElement).dataset.iocValue)).toEqual([
      "bad.example",
      "clean.example",
    ]);
  });

  it("orders three cards without invoking Array sort", async () => {
    const grid = document.createElement("div");
    grid.id = "ioc-cards-grid";
    document.body.appendChild(grid);
    appendCard(grid, "clean.example", "clean");
    appendCard(grid, "bad.example", "malicious");
    appendCard(grid, "suspicious.example", "suspicious");
    const originalSort = Array.prototype.sort;
    Array.prototype.sort = function (...args) {
      if (this.length > 0 && this[0] && typeof this[0] === "object" && "card" in this[0]) {
        throw new Error("three-card severity ordering should not call Array.sort()");
      }
      return originalSort.apply(this, args);
    };

    try {
      sortCardsBySeverity();
      await vi.advanceTimersByTimeAsync(150);
    } finally {
      Array.prototype.sort = originalSort;
    }

    expect(Array.from(grid.children, (card) => (card as HTMLElement).dataset.iocValue)).toEqual([
      "bad.example",
      "suspicious.example",
      "clean.example",
    ]);
  });

  it("skips reappend work when cards are already severity sorted", async () => {
    const grid = document.createElement("div");
    grid.id = "ioc-cards-grid";
    document.body.appendChild(grid);
    appendCard(grid, "bad.example", "malicious");
    appendCard(grid, "suspicious.example", "suspicious");
    appendCard(grid, "clean.example", "clean");
    appendCard(grid, "unknown.example", "no_data");
    const appendChildSpy = vi.spyOn(grid, "appendChild");

    sortCardsBySeverity();
    await vi.advanceTimersByTimeAsync(150);

    expect(appendChildSpy).not.toHaveBeenCalled();
    expect(Array.from(grid.children, (card) => (card as HTMLElement).dataset.iocValue)).toEqual([
      "bad.example",
      "suspicious.example",
      "clean.example",
      "unknown.example",
    ]);
  });

  it("keeps card sorting source free of callback iteration", () => {
    const source = readFileSync(`${process.cwd()}/app/static/src/ts/modules/cards.ts`, "utf8");

    expect(source).not.toContain(".forEach(");
  });

  it("updates card verdict labels without rebuilding className strings", () => {
    const grid = document.createElement("div");
    grid.id = "ioc-cards-grid";
    document.body.appendChild(grid);
    const card = appendCard(grid, "bad.example", "no_data");
    const label = document.createElement("span");
    label.className = "verdict-label verdict-label--no_data extra-marker";
    label.textContent = "NO DATA";
    card.appendChild(label);
    const classListRemoveSpy = vi.spyOn(DOMTokenList.prototype, "remove");
    const classListAddSpy = vi.spyOn(DOMTokenList.prototype, "add");

    applyCardVerdict(card, "malicious");

    expect(card.getAttribute("data-verdict")).toBe("malicious");
    expect(classListRemoveSpy).toHaveBeenCalledWith(
      "verdict-label--malicious",
      "verdict-label--suspicious",
      "verdict-label--clean",
      "verdict-label--known_good",
      "verdict-label--no_data",
      "verdict-label--error"
    );
    expect(classListAddSpy).toHaveBeenCalledWith("verdict-label--malicious");
    expect(label.classList.contains("verdict-label--no_data")).toBe(false);
    expect(label.classList.contains("verdict-label--malicious")).toBe(true);
    expect(label.classList.contains("extra-marker")).toBe(true);
    expect(label.textContent).toBe("MALICIOUS");
  });

  it("updates dashboard verdict counts with one count-element query", () => {
    document.body.innerHTML = `
      <div id="verdict-dashboard">
        <span data-verdict-count="malicious">0</span>
        <span data-verdict-count="suspicious">0</span>
        <span data-verdict-count="clean">0</span>
        <span data-verdict-count="known_good">0</span>
        <span data-verdict-count="no_data">0</span>
      </div>
      <div class="ioc-card" data-verdict="malicious"></div>
      <div class="ioc-card" data-verdict="malicious"></div>
      <div class="ioc-card" data-verdict="clean"></div>
    `;
    const dashboard = document.getElementById("verdict-dashboard") as HTMLElement;
    const dashboardQueryAllSpy = vi.spyOn(dashboard, "querySelectorAll");
    const dashboardQuerySpy = vi.spyOn(dashboard, "querySelector");

    updateDashboardCounts();

    expect(dashboardQueryAllSpy).toHaveBeenCalledTimes(1);
    expect(dashboardQueryAllSpy).toHaveBeenCalledWith("[data-verdict-count]");
    expect(dashboardQuerySpy).not.toHaveBeenCalled();
    expect(document.querySelector('[data-verdict-count="malicious"]')?.textContent).toBe("2");
    expect(document.querySelector('[data-verdict-count="clean"]')?.textContent).toBe("1");
    expect(document.querySelector('[data-verdict-count="no_data"]')?.textContent).toBe("0");
  });

  it("updates dashboard counts with indexed NodeList loops", () => {
    document.body.innerHTML = `
      <div id="verdict-dashboard">
        <span data-verdict-count="malicious">0</span>
        <span data-verdict-count="suspicious">0</span>
        <span data-verdict-count="clean">0</span>
        <span data-verdict-count="known_good">0</span>
        <span data-verdict-count="no_data">0</span>
      </div>
      <div class="ioc-card" data-verdict="malicious"></div>
      <div class="ioc-card" data-verdict="suspicious"></div>
      <div class="ioc-card" data-verdict="no_data"></div>
    `;
    vi.spyOn(NodeList.prototype, "forEach").mockImplementation(() => {
      throw new Error("updateDashboardCounts should use indexed NodeList loops");
    });

    updateDashboardCounts();

    expect(document.querySelector('[data-verdict-count="malicious"]')?.textContent).toBe("1");
    expect(document.querySelector('[data-verdict-count="suspicious"]')?.textContent).toBe("1");
    expect(document.querySelector('[data-verdict-count="clean"]')?.textContent).toBe("0");
    expect(document.querySelector('[data-verdict-count="no_data"]')?.textContent).toBe("1");
  });

  it("checks dashboard count verdict membership without generic lookup helpers", () => {
    document.body.innerHTML = `
      <div id="verdict-dashboard">
      </div>
    `;
    const dashboard = document.getElementById("verdict-dashboard") as HTMLElement;
    const maliciousCount = document.createElement("span");
    maliciousCount.setAttribute("data-verdict-count", "malicious");
    maliciousCount.textContent = "0";
    const suspiciousCount = document.createElement("span");
    suspiciousCount.setAttribute("data-verdict-count", "suspicious");
    suspiciousCount.textContent = "0";
    const ignoredCount = document.createElement("span");
    ignoredCount.setAttribute("data-verdict-count", "ignored");
    ignoredCount.textContent = "unchanged";
    const maliciousCard = document.createElement("div");
    maliciousCard.setAttribute("data-verdict", "malicious");
    const suspiciousCard = document.createElement("div");
    suspiciousCard.setAttribute("data-verdict", "suspicious");
    vi.spyOn(document, "querySelectorAll").mockReturnValue([
      maliciousCard,
      suspiciousCard,
    ] as unknown as NodeListOf<HTMLElement>);
    vi.spyOn(dashboard, "querySelectorAll").mockReturnValue([
      maliciousCount,
      suspiciousCount,
      ignoredCount,
    ] as unknown as NodeListOf<HTMLElement>);
    const includes = Array.prototype.includes;
    const hasOwnPropertySpy = vi.spyOn(Object.prototype, "hasOwnProperty");
    Array.prototype.includes = function () {
      throw new Error("updateDashboardCounts should not scan dashboard verdict arrays per count element");
    };
    hasOwnPropertySpy.mockImplementation(() => {
      throw new Error("updateDashboardCounts should not call hasOwnProperty per card");
    });

    try {
      updateDashboardCounts();
    } finally {
      Array.prototype.includes = includes;
      hasOwnPropertySpy.mockRestore();
    }

    const source = readFileSync(`${process.cwd()}/app/static/src/ts/modules/cards.ts`, "utf8");
    expect(maliciousCount.textContent).toBe("1");
    expect(suspiciousCount.textContent).toBe("1");
    expect(ignoredCount.textContent).toBe("unchanged");
    expect(source).not.toContain("Object.prototype.hasOwnProperty.call(counts");
    expect(source).not.toContain("DASHBOARD_VERDICT_SET");
  });
});
