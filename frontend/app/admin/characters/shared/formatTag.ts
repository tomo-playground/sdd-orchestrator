/** Display a Danbooru-style tag name with spaces instead of underscores. */
export function formatTagName(name: string): string {
  return name.replace(/_/g, " ");
}
