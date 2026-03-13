import { API_ROOT } from "../constants";

/**
 * Resolve an image URL that may be either absolute (http/https) or
 * a relative path served by the backend API.
 *
 * - Returns the URL as-is when it already starts with "http".
 * - Prepends API_ROOT for relative paths (e.g. "/uploads/...").
 * - Returns null for falsy inputs.
 */
export function resolveImageUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("http") ? url : `${API_ROOT}${url}`;
}

/**
 * Clear studio URL params (?id, ?new) to prevent stale storyboard loading after context switch.
 * Uses window.history.replaceState instead of Next.js router to avoid hook dependency
 * (this runs inside useCallback, not a component render cycle).
 */
export function clearStudioUrlParams() {
  const url = new URL(window.location.href);
  if (url.searchParams.has("id") || url.searchParams.has("new")) {
    url.searchParams.delete("id");
    url.searchParams.delete("new");
    window.history.replaceState({}, "", url.toString());
  }
}
