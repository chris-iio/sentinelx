/**
 * Shared DOM utilities for SentinelX TypeScript modules.
 */

/**
 * Typed getAttribute wrapper — returns string instead of string | null.
 * Callers pass a fallback (default: "") to avoid null propagation.
 * Attribute names are intentionally typed as string (not a union) for flexibility.
 */
export function attr(el: Element, name: string, fallback = ""): string {
  return el.getAttribute(name) ?? fallback;
}

export type ResultsSurfaceOwner = "live" | "history" | "static";

export function pageResultsElement(): HTMLElement | null {
  return document.querySelector<HTMLElement>(".page-results");
}

export function resolveResultsSurfaceOwner(
  pageResults: HTMLElement | null = pageResultsElement()
): ResultsSurfaceOwner | null {
  if (!pageResults) return null;

  const explicitOwner = attr(pageResults, "data-results-owner");
  const mode = attr(pageResults, "data-mode");
  const jobId = attr(pageResults, "data-job-id");
  const hasHistoryResults = pageResults.hasAttribute("data-history-results");

  if (explicitOwner === "history") {
    return "history";
  }

  if (explicitOwner === "live") {
    return mode === "online" && jobId ? "live" : "static";
  }

  if (hasHistoryResults) {
    return "history";
  }

  if (mode === "online" && jobId) {
    return "live";
  }

  return "static";
}
