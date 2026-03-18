"use client";

import type { GeminiSuggestion } from "../../types";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
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
  return (
    <Modal open onClose={onClose} size="xl" ariaLabelledBy="gemini-suggest-title">
      <Modal.Header>
        <h3 id="gemini-suggest-title" className="text-lg font-semibold text-zinc-800">
          Gemini Auto Suggestions
        </h3>
        <CloseButton onClick={onClose} />
      </Modal.Header>

      <div className="p-6 space-y-4">
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

        <Button variant="secondary" className="w-full" onClick={onClose}>
          모든 제안 무시
        </Button>

        <p className="text-[12px] text-zinc-400">
          제안을 승인하면 Gemini가 이미지를 자동으로 편집합니다.
        </p>
      </div>
    </Modal>
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

      <Button variant="primary" className="w-full" onClick={onApprove}>
        Approve &amp; Edit (~$0.04)
      </Button>
    </div>
  );
}
