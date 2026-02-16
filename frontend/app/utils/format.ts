/**
 * Format a timestamp (ISO string or epoch ms) as a relative time string.
 * e.g. "just now", "5m ago", "3h ago", "2d ago"
 */
export function formatRelativeTime(value: string | number): string {
  const timestamp = typeof value === "string" ? new Date(value).getTime() : value;
  const diff = Date.now() - timestamp;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
