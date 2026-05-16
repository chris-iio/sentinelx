import { attr, pageResultsElement, resolveResultsSurfaceOwner } from "./dom";

describe("dom utils", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("returns fallback values for missing attributes", () => {
    document.body.innerHTML = `<div id="target" data-present="yes"></div>`;
    const target = document.getElementById("target")!;

    expect(attr(target, "data-present")).toBe("yes");
    expect(attr(target, "data-missing", "fallback")).toBe("fallback");
  });

  it("shares the typed page-results lookup", () => {
    document.body.innerHTML = `<main class="page-results" data-mode="online"></main>`;

    expect(pageResultsElement()?.getAttribute("data-mode")).toBe("online");
  });

  it("resolves history ownership from explicit or replay attributes", () => {
    document.body.innerHTML = `<main class="page-results" data-results-owner="history" data-mode="online"></main>`;

    expect(resolveResultsSurfaceOwner()).toBe("history");

    document.body.innerHTML = `<main class="page-results" data-history-results="[]"></main>`;

    expect(resolveResultsSurfaceOwner()).toBe("history");
  });

  it("requires a valid online job for live ownership", () => {
    document.body.innerHTML = `
      <main class="page-results" data-results-owner="live" data-mode="online" data-job-id="job-1"></main>
    `;

    expect(resolveResultsSurfaceOwner()).toBe("live");

    document.body.innerHTML = `<main class="page-results" data-results-owner="live" data-mode="online"></main>`;

    expect(resolveResultsSurfaceOwner()).toBe("static");
  });

  it("treats absent or offline results surfaces as static", () => {
    expect(resolveResultsSurfaceOwner()).toBeNull();

    document.body.innerHTML = `<main class="page-results" data-mode="offline"></main>`;

    expect(resolveResultsSurfaceOwner()).toBe("static");
  });
});
