"use client";

import type { Scene } from "../../types";

type GeminiSuggestion = {
  edit_type: string;
  issue: string;
  description: string;
  confidence: number;
  target_change: string;
};

type SceneGeminiModalsProps = {
  scene: Scene;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  // Gemini Edit state
  geminiEditOpen: boolean;
  setGeminiEditOpen: (open: boolean) => void;
  geminiTargetChange: string;
  setGeminiTargetChange: (value: string) => void;
  onEditWithGemini: (targetChange: string) => void;
  showToast: (message: string, type: "success" | "error") => void;
  // Gemini Suggestions state
  geminiSuggestionsOpen: boolean;
  setGeminiSuggestionsOpen: (open: boolean) => void;
  geminiSuggestions: GeminiSuggestion[];
  setGeminiSuggestions: (suggestions: GeminiSuggestion[]) => void;
  onApproveSuggestion: (suggestion: GeminiSuggestion) => void;
};

export default function SceneGeminiModals({
  scene,
  qualityScore,
  geminiEditOpen,
  setGeminiEditOpen,
  geminiTargetChange,
  setGeminiTargetChange,
  onEditWithGemini,
  showToast,
  geminiSuggestionsOpen,
  setGeminiSuggestionsOpen,
  geminiSuggestions,
  setGeminiSuggestions,
  onApproveSuggestion,
}: SceneGeminiModalsProps) {
  return (
    <>
      {/* Gemini Edit Modal */}
      {geminiEditOpen && (
        <GeminiEditModal
          scene={scene}
          qualityScore={qualityScore}
          geminiTargetChange={geminiTargetChange}
          setGeminiTargetChange={setGeminiTargetChange}
          onClose={() => {
            setGeminiEditOpen(false);
            setGeminiTargetChange("");
          }}
          onSubmit={(targetChange) => {
            onEditWithGemini(targetChange);
            setGeminiEditOpen(false);
            setGeminiTargetChange("");
          }}
          showToast={showToast}
        />
      )}

      {/* Gemini Auto-Suggest Modal */}
      {geminiSuggestionsOpen && (
        <GeminiSuggestModal
          geminiSuggestions={geminiSuggestions}
          onClose={() => {
            setGeminiSuggestionsOpen(false);
            setGeminiSuggestions([]);
          }}
          onApproveSuggestion={onApproveSuggestion}
        />
      )}
    </>
  );
}

/* ---- Gemini Edit Modal ---- */

type GeminiEditModalProps = {
  scene: Scene;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  geminiTargetChange: string;
  setGeminiTargetChange: (value: string) => void;
  onClose: () => void;
  onSubmit: (targetChange: string) => void;
  showToast: (message: string, type: "success" | "error") => void;
};

const EDIT_EXAMPLES = [
  "의자에 앉아서 무릎에 손 올리기",
  "밝게 웃으면서 정면 보기",
  "뒤돌아서 어깨 너머로 보기",
  "오른손 들어 손 흔들기",
];

function GeminiEditModal({
  scene,
  qualityScore,
  geminiTargetChange,
  setGeminiTargetChange,
  onClose,
  onSubmit,
  showToast,
}: GeminiEditModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-zinc-800">✨ Fix with Gemini Nano Banana</h3>
          <CloseButton onClick={onClose} />
        </div>

        <div className="space-y-4">
          <div>
            <p className="mb-2 text-sm text-zinc-600">
              현재 Match Rate가 낮습니다 ({(qualityScore?.match_rate ?? 0) * 100}%). 어떤 부분을 수정하시겠습니까?
            </p>
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
              <strong>Missing Tags:</strong>{" "}
              {qualityScore?.missing_tags.slice(0, 5).join(", ") || "None"}
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-zinc-700">
              어떻게 바꿀까요? (자연어로 입력하세요)
            </label>
            <div className="mb-2 flex flex-wrap gap-2">
              {EDIT_EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setGeminiTargetChange(example)}
                  className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs text-zinc-600 transition hover:border-purple-300 hover:bg-purple-50"
                >
                  {example}
                </button>
              ))}
            </div>
            <textarea
              value={geminiTargetChange}
              onChange={(e) => setGeminiTargetChange(e.target.value)}
              placeholder="예: 의자에 앉아서 무릎에 손 올리기 / 환하게 웃으면서 카메라 보기"
              className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-purple-400"
              rows={3}
            />
          </div>

          <div className="flex justify-between gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
            >
              취소
            </button>
            <button
              type="button"
              onClick={() => {
                if (!geminiTargetChange.trim()) {
                  showToast("변경 내용을 입력하세요", "error");
                  return;
                }
                onSubmit(geminiTargetChange.trim());
              }}
              disabled={!geminiTargetChange.trim() || scene.isGenerating}
              className="flex-1 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:from-purple-600 hover:to-pink-600 disabled:cursor-not-allowed disabled:from-purple-300 disabled:to-pink-300"
            >
              ✨ 편집 시작 (~$0.04)
            </button>
          </div>

          <p className="text-[10px] text-zinc-400">
            💡 Gemini가 얼굴/화풍을 유지하면서 포즈/표정/시선만 변경합니다.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ---- Gemini Suggest Modal ---- */

type GeminiSuggestModalProps = {
  geminiSuggestions: GeminiSuggestion[];
  onClose: () => void;
  onApproveSuggestion: (suggestion: GeminiSuggestion) => void;
};

function GeminiSuggestModal({
  geminiSuggestions,
  onClose,
  onApproveSuggestion,
}: GeminiSuggestModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-2xl rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-zinc-800">🤖 Gemini Auto Suggestions</h3>
          <CloseButton onClick={onClose} />
        </div>

        <div className="space-y-4">
          <p className="text-sm text-zinc-600">
            Gemini가 이미지와 프롬프트를 비교해 {geminiSuggestions.length}개의 수정 제안을 생성했습니다.
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

          <p className="text-[10px] text-zinc-400">
            💡 제안을 승인하면 Gemini Nano Banana가 이미지를 자동으로 편집합니다.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ---- Shared sub-components ---- */

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
    >
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
          clipRule="evenodd"
        />
      </svg>
    </button>
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
            <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 uppercase">
              {suggestion.edit_type}
            </span>
            <span className="text-xs font-semibold text-zinc-800">{suggestion.issue}</span>
          </div>
          <p className="text-sm text-zinc-600">{suggestion.description}</p>
        </div>
        <div className="text-xs text-zinc-500">
          {(suggestion.confidence * 100).toFixed(0)}%
        </div>
      </div>

      <div className="mb-3 rounded-lg bg-indigo-50 p-3">
        <p className="text-xs font-semibold text-indigo-900">💡 제안:</p>
        <p className="text-sm text-indigo-700">{suggestion.target_change}</p>
      </div>

      <button
        type="button"
        onClick={onApprove}
        className="w-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-2 text-sm font-semibold text-white transition hover:from-indigo-600 hover:to-purple-600"
      >
        ✅ 이 제안 승인하고 편집 (~$0.04)
      </button>
    </div>
  );
}
