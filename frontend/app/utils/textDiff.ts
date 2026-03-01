export type TextDiffToken = {
  text: string;
  type: "added" | "removed" | "equal";
};

/**
 * Word-level LCS diff for natural language sentences.
 * Splits on whitespace and computes longest common subsequence.
 */
export function computeWordDiff(before: string, after: string): TextDiffToken[] {
  const a = before.split(/\s+/).filter(Boolean);
  const b = after.split(/\s+/).filter(Boolean);

  // LCS table
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1] ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }

  // Backtrack to produce diff tokens
  const tokens: TextDiffToken[] = [];
  let i = m;
  let j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      tokens.push({ text: a[i - 1], type: "equal" });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      tokens.push({ text: b[j - 1], type: "added" });
      j--;
    } else {
      tokens.push({ text: a[i - 1], type: "removed" });
      i--;
    }
  }

  return tokens.reverse();
}
