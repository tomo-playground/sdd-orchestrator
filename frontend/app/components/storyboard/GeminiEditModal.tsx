"use client";

import { useState } from "react";
import type { Scene } from "../../types";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import PromptEditDiff from "../prompt/PromptEditDiff";
import CloseButton from "./CloseButton";

type GeminiEditModalProps = {
  scene: Scene;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  geminiTargetChange: string;
  setGeminiTargetChange: (value: string) => void;
  onClose: () => void;
  onSubmitImageEdit: (targetChange: string) => void;
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

export default function GeminiEditModal({
  scene,
  qualityScore,
  geminiTargetChange,
  setGeminiTargetChange,
  onClose,
  onSubmitImageEdit,
  onApplyPromptEdit,
  showToast,
  selectedCharacterId,
}: GeminiEditModalProps) {
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
    <Modal open onClose={onClose} size="lg" ariaLabelledBy="gemini-edit-title">
      <Modal.Header>
        <h3 id="gemini-edit-title" className="text-lg font-semibold text-zinc-800">
          프롬프트 편집
        </h3>
        <CloseButton onClick={onClose} />
      </Modal.Header>

      <div className="p-6">
        {phase === "input" && (
          <GeminiEditInputPhase
            qualityScore={qualityScore}
            geminiTargetChange={geminiTargetChange}
            setGeminiTargetChange={setGeminiTargetChange}
            isGenerating={!!scene.isGenerating}
            onClose={onClose}
            onPromptPreview={handlePromptPreview}
            onSubmitImageEdit={onSubmitImageEdit}
            showToast={showToast}
          />
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
    </Modal>
  );
}

/** Input phase sub-component for GeminiEditModal */
function GeminiEditInputPhase({
  qualityScore,
  geminiTargetChange,
  setGeminiTargetChange,
  isGenerating,
  onClose,
  onPromptPreview,
  onSubmitImageEdit,
  showToast,
}: {
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  geminiTargetChange: string;
  setGeminiTargetChange: (value: string) => void;
  isGenerating: boolean;
  onClose: () => void;
  onPromptPreview: () => void;
  onSubmitImageEdit: (targetChange: string) => void;
  showToast: (message: string, type: "success" | "error") => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <p className="mb-2 text-sm text-zinc-600">
          일치율: {((qualityScore?.match_rate ?? 0) * 100).toFixed(0)}%
        </p>
        {qualityScore?.missing_tags && qualityScore.missing_tags.length > 0 && (
          <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
            <strong>누락 태그:</strong> {qualityScore.missing_tags.slice(0, 5).join(", ")}
          </div>
        )}
      </div>

      <div>
        <label
          htmlFor="gemini-edit-instruction"
          className="mb-2 block text-sm font-semibold text-zinc-700"
        >
          어떻게 변경할까요? (자연어 입력)
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

      <div className="flex flex-col gap-2">
        <Button
          variant="primary"
          className="w-full"
          onClick={onPromptPreview}
          disabled={!geminiTargetChange.trim()}
        >
          프롬프트 미리보기
        </Button>
        <div className="flex justify-between gap-3">
          <Button variant="secondary" size="sm" className="flex-1" onClick={onClose}>
            취소
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="flex-1"
            onClick={() => {
              if (!geminiTargetChange.trim()) {
                showToast("변경 내용을 입력하세요", "error");
                return;
              }
              onSubmitImageEdit(geminiTargetChange.trim());
            }}
            disabled={!geminiTargetChange.trim() || isGenerating}
          >
            이미지 직접 편집 (~$0.04)
          </Button>
        </div>
      </div>

      <p className="text-[12px] text-zinc-400">
        프롬프트 미리보기: 태그 변경을 확인 후 적용합니다. 이미지 편집: Gemini가 이미지를 직접
        수정합니다.
      </p>
    </div>
  );
}
