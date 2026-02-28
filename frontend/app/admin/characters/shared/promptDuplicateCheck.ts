/**
 * Detect tags that appear in both the prompt text and the selected tag list.
 * Comparison normalizes underscores ↔ spaces and is case-insensitive.
 */
export function findDuplicateTokens(promptText: string, selectedTagNames: string[]): string[] {
  if (!promptText.trim() || selectedTagNames.length === 0) return [];

  const normalize = (s: string) => s.replace(/_/g, " ").toLowerCase().trim();

  const tagSet = new Set(selectedTagNames.map(normalize));
  const tokens = promptText.split(",").map((t) => normalize(t));

  const duplicates: string[] = [];
  const seen = new Set<string>();

  for (const token of tokens) {
    if (token && tagSet.has(token) && !seen.has(token)) {
      seen.add(token);
      // Return original tag name (underscore form)
      const original = selectedTagNames.find((n) => normalize(n) === token);
      if (original) duplicates.push(original);
    }
  }

  return duplicates;
}
