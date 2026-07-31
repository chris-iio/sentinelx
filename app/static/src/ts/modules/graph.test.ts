import { init, renderRelationshipGraph } from "./graph";
import { readFileSync } from "node:fs";

describe("renderRelationshipGraph", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("renders graph data without array filter/find/map/forEach setup", () => {
    document.body.innerHTML = `<div id="relationship-graph"></div>`;
    const container = document.getElementById("relationship-graph") as HTMLElement;
    container.setAttribute("data-graph-nodes", JSON.stringify([
      { id: "ioc", label: "1.2.3.4", verdict: "ioc", role: "ioc" },
      { id: "VirusTotal", label: "VirusTotal", verdict: "malicious", role: "provider" },
      { id: "GreyNoise", label: "GreyNoise", verdict: "clean", role: "provider" },
    ]));
    container.setAttribute("data-graph-edges", JSON.stringify([
      { from: "ioc", to: "VirusTotal", verdict: "malicious" },
      { from: "ioc", to: "GreyNoise", verdict: "clean" },
    ]));

    const filter = Array.prototype.filter;
    const find = Array.prototype.find;
    const map = Array.prototype.map;
    const forEach = Array.prototype.forEach;
    Array.prototype.filter = function () {
      throw new Error("graph renderer should not filter graph nodes");
    };
    Array.prototype.find = function () {
      throw new Error("graph renderer should not find IOC nodes with an extra pass");
    };
    Array.prototype.map = function () {
      throw new Error("graph renderer should not map provider nodes before indexing");
    };
    Array.prototype.forEach = function () {
      throw new Error("graph renderer should not use callback iteration for provider drawing");
    };

    try {
      renderRelationshipGraph(container);
    } finally {
      Array.prototype.filter = filter;
      Array.prototype.find = find;
      Array.prototype.map = map;
      Array.prototype.forEach = forEach;
    }

    expect(container.querySelector("svg")?.getAttribute("role")).toBe("img");
    expect(container.querySelectorAll(".graph-node--provider")).toHaveLength(2);
    expect(container.querySelectorAll(".graph-edges line")).toHaveLength(2);
    expect(container.textContent).toContain("VirusTotal");
    expect(container.textContent).toContain("1.2.3.4");
  });

  it("initializes real safely embedded graph data after HTML parsing", () => {
    const nodes = [
      { id: "ioc", label: "1.2.3.4", verdict: "ioc", role: "ioc" },
      {
        id: "R&D \"Intel\"",
        label: "R&D \"Intel\"",
        verdict: "suspicious",
        role: "provider",
      },
    ];
    const edges = [
      { from: "ioc", to: "R&D \"Intel\"", verdict: "suspicious" },
    ];
    const escapeAttribute = (value: unknown) =>
      JSON.stringify(value)
        .replaceAll("&", "&amp;")
        .replaceAll("\"", "&quot;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");

    document.body.innerHTML = `
      <div
        id="relationship-graph"
        data-graph-nodes="${escapeAttribute(nodes)}"
        data-graph-edges="${escapeAttribute(edges)}"
      ></div>
    `;

    init();

    const container = document.getElementById("relationship-graph")!;
    expect(container.querySelectorAll(".graph-node--provider")).toHaveLength(1);
    expect(container.querySelectorAll(".graph-edges line")).toHaveLength(1);
    expect(container.textContent).toContain("R&D \"Intel\"");
  });

  it("walks parsed graph arrays without iterator allocation", () => {
    document.body.innerHTML = `<div id="relationship-graph"></div>`;
    const container = document.getElementById("relationship-graph") as HTMLElement;
    const nodesJson = JSON.stringify([
      { id: "ioc", label: "1.2.3.4", verdict: "ioc", role: "ioc" },
      { id: "VirusTotal", label: "VirusTotal", verdict: "malicious", role: "provider" },
    ]);
    const edgesJson = JSON.stringify([
      { from: "ioc", to: "VirusTotal", verdict: "malicious" },
    ]);
    container.setAttribute("data-graph-nodes", nodesJson);
    container.setAttribute("data-graph-edges", edgesJson);

    const originalParse = JSON.parse;
    vi.spyOn(JSON, "parse").mockImplementation((text: string) => {
      const parsed = originalParse(text) as unknown;
      if (Array.isArray(parsed)) {
        Object.defineProperty(parsed, Symbol.iterator, {
          value() {
            throw new Error("graph renderer should use indexed loops for parsed arrays");
          },
        });
      }
      return parsed;
    });

    renderRelationshipGraph(container);

    expect(container.querySelector("svg")?.getAttribute("role")).toBe("img");
    expect(container.querySelectorAll(".graph-edges line")).toHaveLength(1);
  });

  it("shows an empty state for malformed graph data", () => {
    document.body.innerHTML = `<div id="relationship-graph" data-graph-nodes="{" data-graph-edges="[]"></div>`;
    const container = document.getElementById("relationship-graph") as HTMLElement;

    renderRelationshipGraph(container);

    expect(container.querySelector(".graph-empty")?.textContent).toBe("No provider data to graph");
    expect(container.querySelector(".graph-empty")?.getAttribute("role")).toBe("status");
  });

  it("skips JSON parsing when graph nodes are the literal empty payload", () => {
    document.body.innerHTML = `<div id="relationship-graph" data-graph-nodes="[]" data-graph-edges="not-json"></div>`;
    const container = document.getElementById("relationship-graph") as HTMLElement;
    const jsonParseSpy = vi.spyOn(JSON, "parse").mockImplementation(() => {
      throw new Error("empty graph node payload should skip JSON.parse");
    });

    renderRelationshipGraph(container);

    expect(jsonParseSpy).not.toHaveBeenCalled();
    expect(container.querySelector(".graph-empty")?.textContent).toBe("No provider data to graph");
  });

  it("skips edge JSON parsing when graph edges are the literal empty payload", () => {
    document.body.innerHTML = `<div id="relationship-graph"></div>`;
    const container = document.getElementById("relationship-graph") as HTMLElement;
    const nodesJson = JSON.stringify([
      { id: "ioc", label: "1.2.3.4", verdict: "ioc", role: "ioc" },
      { id: "VirusTotal", label: "VirusTotal", verdict: "malicious", role: "provider" },
    ]);
    container.setAttribute("data-graph-nodes", nodesJson);
    container.setAttribute("data-graph-edges", "[]");
    const originalParse = JSON.parse;
    const jsonParseSpy = vi.spyOn(JSON, "parse").mockImplementation((text: string) => {
      if (text === "[]") {
        throw new Error("empty graph edge payload should skip JSON.parse");
      }
      return originalParse(text) as unknown;
    });

    renderRelationshipGraph(container);

    expect(jsonParseSpy).toHaveBeenCalledTimes(1);
    expect(jsonParseSpy).toHaveBeenCalledWith(nodesJson);
    expect(container.querySelector("svg")?.getAttribute("role")).toBe("img");
    expect(container.querySelectorAll(".graph-edges line")).toHaveLength(0);
  });

  it("keeps empty graph rendering on one shared helper", () => {
    const source = readFileSync(`${process.cwd()}/app/static/src/ts/modules/graph.ts`, "utf8");

    expect(source).toContain("function appendEmptyGraphMessage");
    expect(source.match(/document\.createTextNode\("No provider data to graph"\)/g)).toHaveLength(1);
    expect(source.match(/appendEmptyGraphMessage\(container\)/g)).toHaveLength(2);
    expect(source).not.toContain("for (const node of nodes)");
    expect(source).not.toContain("for (const edge of edges)");
  });

  it("computes provider orbit coordinates once per provider", () => {
    document.body.innerHTML = `<div id="relationship-graph"></div>`;
    const container = document.getElementById("relationship-graph") as HTMLElement;
    container.setAttribute("data-graph-nodes", JSON.stringify([
      { id: "ioc", label: "1.2.3.4", verdict: "ioc", role: "ioc" },
      { id: "VirusTotal", label: "VirusTotal", verdict: "malicious", role: "provider" },
      { id: "GreyNoise", label: "GreyNoise", verdict: "clean", role: "provider" },
      { id: "Shodan", label: "Shodan", verdict: "suspicious", role: "provider" },
    ]));
    container.setAttribute("data-graph-edges", JSON.stringify([
      { from: "ioc", to: "VirusTotal", verdict: "malicious" },
      { from: "ioc", to: "GreyNoise", verdict: "clean" },
      { from: "ioc", to: "Shodan", verdict: "suspicious" },
    ]));

    const originalCos = Math.cos;
    const originalSin = Math.sin;
    const cosSpy = vi.spyOn(Math, "cos").mockImplementation((angle) => originalCos(angle));
    const sinSpy = vi.spyOn(Math, "sin").mockImplementation((angle) => originalSin(angle));

    renderRelationshipGraph(container);

    expect(cosSpy).toHaveBeenCalledTimes(3);
    expect(sinSpy).toHaveBeenCalledTimes(3);
    expect(container.querySelectorAll(".graph-node--provider")).toHaveLength(3);
    expect(container.querySelectorAll(".graph-edges line")).toHaveLength(3);
  });

  it("places two-provider orbits without trig work", () => {
    document.body.innerHTML = `<div id="relationship-graph"></div>`;
    const container = document.getElementById("relationship-graph") as HTMLElement;
    container.setAttribute("data-graph-nodes", JSON.stringify([
      { id: "ioc", label: "1.2.3.4", verdict: "ioc", role: "ioc" },
      { id: "VirusTotal", label: "VirusTotal", verdict: "malicious", role: "provider" },
      { id: "GreyNoise", label: "GreyNoise", verdict: "clean", role: "provider" },
    ]));
    container.setAttribute("data-graph-edges", JSON.stringify([
      { from: "ioc", to: "VirusTotal", verdict: "malicious" },
      { from: "ioc", to: "GreyNoise", verdict: "clean" },
    ]));

    const cosSpy = vi.spyOn(Math, "cos").mockImplementation(() => {
      throw new Error("two-provider graph should not call Math.cos");
    });
    const sinSpy = vi.spyOn(Math, "sin").mockImplementation(() => {
      throw new Error("two-provider graph should not call Math.sin");
    });

    renderRelationshipGraph(container);

    expect(cosSpy).not.toHaveBeenCalled();
    expect(sinSpy).not.toHaveBeenCalled();
    expect(container.querySelectorAll(".graph-node--provider")).toHaveLength(2);
    expect(container.querySelector("circle[cx='350'][cy='55']")).not.toBeNull();
    expect(container.querySelector("circle[cx='350'][cy='395']")).not.toBeNull();
  });
});
