export type DiffToken = {
  text: string;
  type: "added" | "removed" | "kept";
};

export function computeTokenDiff(current: string, edited: string): DiffToken[] {
  const currentTokens = current
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  const editedTokens = edited
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const currentSet = new Set(currentTokens.map((t) => t.toLowerCase()));
  const editedSet = new Set(editedTokens.map((t) => t.toLowerCase()));
  const diff: DiffToken[] = [];

  for (const token of currentTokens) {
    diff.push({
      text: token,
      type: editedSet.has(token.toLowerCase()) ? "kept" : "removed",
    });
  }

  for (const token of editedTokens) {
    if (!currentSet.has(token.toLowerCase())) {
      diff.push({ text: token, type: "added" });
    }
  }

  return diff;
}
