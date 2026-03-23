"use client";

import { useState } from "react";
import type { Scene } from "../../types";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import PromptEditDiff from "../prompt/PromptEditDiff";

type SceneGeminiModalsProps = {
  scene: Scene;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  geminiEditOpen: boolean;
  setGeminiEditOpen: (open: boolean) => void;
  geminiTargetChange: string;
  setGeminiTargetChange: (value: string) => void;
  onApplyPromptEdit: (editedPrompt: string) => void;
  showToast: (message: string, type: "success" | "error") => void;
  selectedCharacterId?: number | null;
};

export default function SceneGeminiModals({
  scene,
  qualityScore,
  geminiEditOpen,
  setGeminiEditOpen,
  geminiTargetChange,
  setGeminiTargetChange,
  onApplyPromptEdit,
  showToast,
  selectedCharacterId,
}: SceneGeminiModalsProps) {
  return (
    <>
      {/* Gemini Edit Modal (프롬프트 편집 전용) */}
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
          onApplyPromptEdit={(edited) => {
            onApplyPromptEdit(edited);
            setGeminiEditOpen(false);
            setGeminiTargetChange("");
          }}
          showToast={showToast}
          selectedCharacterId={selectedCharacterId}
        />
      )}
    </>
  );
}

/* ---- Gemini Edit Modal (2-phase: input → diff) ---- */

type GeminiEditModalProps = {
  scene: Scene;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  geminiTargetChange: string;
  setGeminiTargetChange: (value: string) => void;
  onClose: () => void;
  onApplyPromptEdit: (editedPrompt: string) => void;
  showToast: (message: string, type: "success" | "error") => void;
  selectedCharacterId?: number | null;
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
  onApplyPromptEdit,
  showToast,
  selectedCharacterId,
}: GeminiEditModalProps) {
  const trapRef = useFocusTrap(true);
  const [phase, setPhase] = useState<"input" | "diff">("input");
  const [diffInstruction, setDiffInstruction] = useState("");

  const handlePromptPreview = () => {
    if (!geminiTargetChange.trim()) {
      showToast("변경 내용을 입력하세요", "error");
      return;
    }
    setDiffInstruction(geminiTargetChange.trim());
    setPhase("diff");
  };

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="gemini-edit-title"
    >
      <div
        ref={trapRef}
        tabIndex={-1}
        className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl outline-none"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 id="gemini-edit-title" className="text-lg font-semibold text-zinc-800">
            ✨ 프롬프트 편집
          </h3>
          <CloseButton onClick={onClose} />
        </div>

        {phase === "input" && (
          <div className="space-y-4">
            <div>
              <p className="mb-2 text-sm text-zinc-600">
                현재 Match Rate: {((qualityScore?.match_rate ?? 0) * 100).toFixed(0)}%
              </p>
              {qualityScore?.missing_tags && qualityScore.missing_tags.length > 0 && (
                <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
                  <strong>Missing Tags:</strong> {qualityScore.missing_tags.slice(0, 5).join(", ")}
                </div>
              )}
            </div>

            <div>
              <label
                htmlFor="gemini-edit-instruction"
                className="mb-2 block text-sm font-semibold text-zinc-700"
              >
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
                id="gemini-edit-instruction"
                value={geminiTargetChange}
                onChange={(e) => setGeminiTargetChange(e.target.value)}
                placeholder="예: 의자에 앉아서 무릎에 손 올리기 / 환하게 웃으면서 카메라 보기"
                className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-purple-400"
                rows={3}
              />
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handlePromptPreview}
                disabled={!geminiTargetChange.trim()}
                className="flex-1 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:from-purple-600 hover:to-pink-600 disabled:cursor-not-allowed disabled:from-purple-300 disabled:to-pink-300"
              >
                ✨ 프롬프트 미리보기
              </button>
            </div>
          </div>
        )}

        {phase === "diff" && (
          <PromptEditDiff
            currentPrompt={scene.image_prompt}
            instruction={diffInstruction}
            characterId={selectedCharacterId}
            onApply={onApplyPromptEdit}
            onCancel={() => setPhase("input")}
          />
        )}
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
      aria-label="Close dialog"
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
