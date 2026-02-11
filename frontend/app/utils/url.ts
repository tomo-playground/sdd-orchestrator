import { API_BASE } from "../constants";

/**
 * Resolve an image URL that may be either absolute (http/https) or
 * a relative path served by the backend API.
 *
 * - Returns the URL as-is when it already starts with "http".
 * - Prepends API_BASE for relative paths (e.g. "/uploads/...").
 * - Returns null for falsy inputs.
 */
export function resolveImageUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}
