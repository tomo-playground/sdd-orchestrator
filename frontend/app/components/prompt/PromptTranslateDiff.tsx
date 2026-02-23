"use client";

import { useCallback, useState } from "react";
import { API_BASE } from "../../constants";
import { computeTokenDiff } from "../../utils/promptDiff";

type PromptTranslateDiffProps = {
  koText: string;
  currentPrompt: string;
  characterId?: number | null;
  onApply: (translatedPrompt: string) => void;
};

export default function PromptTranslateDiff({
  koText,
  currentPrompt,
  characterId,
  onApply,
}: PromptTranslateDiffProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [translatedPrompt, setTranslatedPrompt] = useState<string | null>(null);

  const handleTranslate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setTranslatedPrompt(null);

    try {
      const res = await fetch(`${API_BASE}/prompt/translate-ko`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ko_text: koText,
          current_prompt: currentPrompt || undefined,
          character_id: characterId || undefined,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setTranslatedPrompt(data.translated_prompt);
    } catch (err) {
      setError(err instanceof Error ? err.message : "변환 실패");
    } finally {
      setLoading(false);
    }
  }, [koText, currentPrompt, characterId]);

  const handleApply = useCallback(() => {
    if (translatedPrompt) {
      onApply(translatedPrompt);
      setTranslatedPrompt(null);
    }
  }, [translatedPrompt, onApply]);

  const handleCancel = useCallback(() => {
    setTranslatedPrompt(null);
    setError(null);
  }, []);

  // Diff tokens
  const diffTokens = translatedPrompt ? computeTokenDiff(currentPrompt, translatedPrompt) : [];

  return (
    <div className="flex flex-col gap-2">
      {/* Translate button */}
      {!translatedPrompt && (
        <button
          type="button"
          onClick={handleTranslate}
          disabled={loading}
          className="self-start rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100 disabled:opacity-50"
        >
          {loading ? "변환 중..." : "KO → EN 변환"}
        </button>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          <span>{error}</span>
          <button
            type="button"
            onClick={handleTranslate}
            className="ml-auto text-xs font-medium text-red-600 underline hover:text-red-800"
          >
            다시 시도
          </button>
        </div>
      )}

      {/* Diff view */}
      {translatedPrompt && (
        <div className="rounded-xl border border-zinc-200 bg-zinc-50/80 p-3">
          <p className="mb-2 text-[11px] font-semibold tracking-wide text-zinc-500 uppercase">
            변환 결과 Diff
          </p>
          <div className="flex flex-wrap gap-1">
            {diffTokens.map((token, i) => (
              <span
                key={`${token.text}-${token.type}-${i}`}
                className={`inline-block rounded px-1.5 py-0.5 text-xs ${
                  token.type === "added"
                    ? "bg-green-100 text-green-800"
                    : token.type === "removed"
                      ? "bg-red-100 text-red-800 line-through"
                      : "bg-zinc-100 text-zinc-600"
                }`}
              >
                {token.text}
              </span>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={handleApply}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700"
            >
              적용
            </button>
            <button
              type="button"
              onClick={handleCancel}
              className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-zinc-50"
            >
              취소
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
