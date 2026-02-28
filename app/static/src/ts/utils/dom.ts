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
