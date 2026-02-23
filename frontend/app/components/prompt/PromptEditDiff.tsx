"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../../constants";
import { computeTokenDiff } from "../../utils/promptDiff";

type PromptEditDiffProps = {
  currentPrompt: string;
  instruction: string;
  characterId?: number | null;
  onApply: (editedPrompt: string) => void;
  onCancel: () => void;
};

async function fetchEditPrompt(
  currentPrompt: string,
  instruction: string,
  characterId?: number | null,
): Promise<string> {
  const res = await fetch(`${API_BASE}/prompt/edit-prompt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_prompt: currentPrompt,
      instruction,
      character_id: characterId || undefined,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || `Error ${res.status}`);
  }
  const data = await res.json();
  return data.edited_prompt;
}

export default function PromptEditDiff({
  currentPrompt,
  instruction,
  characterId,
  onApply,
  onCancel,
}: PromptEditDiffProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editedPrompt, setEditedPrompt] = useState<string | null>(null);
  const didFetch = useRef(false);

  useEffect(() => {
    if (didFetch.current || !instruction) return;
    didFetch.current = true;

    void (async () => {
      try {
        const result = await fetchEditPrompt(currentPrompt, instruction, characterId);
        setEditedPrompt(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "편집 실패");
      } finally {
        setLoading(false);
      }
    })();
  }, [instruction, currentPrompt, characterId]);

  const handleRetry = async () => {
    setLoading(true);
    setError(null);
    setEditedPrompt(null);
    try {
      const result = await fetchEditPrompt(currentPrompt, instruction, characterId);
      setEditedPrompt(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "편집 실패");
    } finally {
      setLoading(false);
    }
  };

  const diffTokens = editedPrompt ? computeTokenDiff(currentPrompt, editedPrompt) : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
        <span className="ml-3 text-sm text-zinc-500">프롬프트 편집 중...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4">
        <p className="mb-2 text-sm text-red-700">{error}</p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void handleRetry()}
            className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
          >
            다시 시도
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50"
          >
            취소
          </button>
        </div>
      </div>
    );
  }

  if (!editedPrompt) return null;

  return (
    <div className="rounded-xl border border-zinc-200 bg-zinc-50/80 p-4">
      <p className="mb-1 text-[11px] font-semibold tracking-wide text-zinc-500 uppercase">
        편집 Diff
      </p>
      <p className="mb-3 text-[12px] text-zinc-400">지시: {instruction}</p>
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
          onClick={() => onApply(editedPrompt)}
          className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700"
        >
          적용
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-zinc-50"
        >
          취소
        </button>
      </div>
    </div>
  );
}
