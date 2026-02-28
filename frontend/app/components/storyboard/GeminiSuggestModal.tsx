"use client";

import type { GeminiSuggestion } from "../../types";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import CloseButton from "./CloseButton";

type GeminiSuggestModalProps = {
  geminiSuggestions: GeminiSuggestion[];
  onClose: () => void;
  onApproveSuggestion: (suggestion: GeminiSuggestion) => void;
};

export default function GeminiSuggestModal({
  geminiSuggestions,
  onClose,
  onApproveSuggestion,
}: GeminiSuggestModalProps) {
  const trapRef = useFocusTrap(true);

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="gemini-suggest-title"
    >
      <div
        ref={trapRef}
        tabIndex={-1}
        className="w-full max-w-2xl rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl outline-none"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 id="gemini-suggest-title" className="text-lg font-semibold text-zinc-800">
            Gemini Auto Suggestions
          </h3>
          <CloseButton onClick={onClose} />
        </div>

        <div className="space-y-4">
          <p className="text-sm text-zinc-600">
            Gemini가 이미지와 프롬프트를 비교해 {geminiSuggestions.length}개의 수정 제안을
            생성했습니다.
          </p>

          <div className="space-y-3">
            {geminiSuggestions.map((suggestion, idx) => (
              <SuggestionCard
                key={idx}
                suggestion={suggestion}
                onApprove={() => onApproveSuggestion(suggestion)}
              />
            ))}
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
          >
            모든 제안 무시
          </button>

          <p className="text-[12px] text-zinc-400">
            제안을 승인하면 Gemini가 이미지를 자동으로 편집합니다.
          </p>
        </div>
      </div>
    </div>
  );
}

function SuggestionCard({
  suggestion,
  onApprove,
}: {
  suggestion: GeminiSuggestion;
  onApprove: () => void;
}) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-gradient-to-br from-white to-zinc-50 p-4 transition hover:border-indigo-300 hover:shadow-md">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[12px] font-semibold text-indigo-700 uppercase">
              {suggestion.edit_type}
            </span>
            <span className="text-xs font-semibold text-zinc-800">{suggestion.issue}</span>
          </div>
          <p className="text-sm text-zinc-600">{suggestion.description}</p>
        </div>
        <div className="text-xs text-zinc-500">{(suggestion.confidence * 100).toFixed(0)}%</div>
      </div>

      <div className="mb-3 rounded-lg bg-indigo-50 p-3">
        <p className="text-xs font-semibold text-indigo-900">Suggestion:</p>
        <p className="text-sm text-indigo-700">{suggestion.target_change}</p>
      </div>

      <button
        type="button"
        onClick={onApprove}
        className="w-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-2 text-sm font-semibold text-white transition hover:from-indigo-600 hover:to-purple-600"
      >
        Approve & Edit (~$0.04)
      </button>
    </div>
  );
}
