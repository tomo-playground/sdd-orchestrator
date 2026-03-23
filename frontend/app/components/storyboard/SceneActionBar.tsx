"use client";

import type { Scene } from "../../types";
import Button from "../ui/Button";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";

type SceneActionBarProps = {
  scene: Scene;
  sceneIndex: number;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  sceneMenuOpen: boolean;
  isMarkingStatus?: boolean;
  onGenerateImage: () => void;
  onGeminiEditOpen: () => void;
  onClothingOpen?: () => void;
  onMarkSuccess?: () => void;
  onMarkFail?: () => void;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onRemoveScene: () => void;
  showToast: (message: string, type: "success" | "error") => void;
  compact?: boolean;
};

import { useRef } from "react";
import Popover from "../ui/Popover";

export default function SceneActionBar({
  scene,
  sceneIndex,
  qualityScore,
  sceneMenuOpen,
  isMarkingStatus = false,
  onGenerateImage,
  onGeminiEditOpen,
  onClothingOpen,
  onMarkSuccess,
  onMarkFail,
  onSceneMenuToggle,
  onSceneMenuClose,
  onUpdateScene,
  onRemoveScene,
  showToast,
  compact = false,
}: SceneActionBarProps) {
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const { confirm, dialogProps } = useConfirm();

  return (
    <div className={`flex items-center justify-between ${compact ? "flex-wrap gap-y-2" : ""}`}>
      <div className={`flex items-center gap-2 ${compact ? "flex-wrap" : ""}`}>
        {/* Generate Image button */}
        <Button
          onClick={onGenerateImage}
          disabled={scene.isGenerating}
          loading={scene.isGenerating}
          size="sm"
          className="shadow-md shadow-zinc-900/20"
        >
          {scene.isGenerating ? "Generating..." : "Generate"}
          {scene.environment_reference_id && !scene.isGenerating && (
            <span className="ml-1 animate-pulse text-[#FFD700]" title="Background Pinned">
              📌
            </span>
          )}
        </Button>

        {/* Stage background indicator */}
        {scene.background_id && !scene.isGenerating && (
          <div
            className="flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 py-1 pr-1.5 pl-2.5 text-[12px] text-emerald-600"
            title="Stage 배경이 ControlNet 참조로 사용됩니다"
          >
            <span>🎬 BG#{scene.background_id}</span>
            <button
              type="button"
              onClick={() => onUpdateScene({ background_id: null, environment_reference_id: null })}
              className="ml-1 flex h-4 w-4 items-center justify-center rounded-full text-emerald-500 transition hover:bg-emerald-200 hover:text-emerald-700"
              title="배경 매핑 해제"
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        )}

        {/* Gemini Edit button */}
        {scene.image_url && !scene.isGenerating && (
          <Button
            variant="gradient"
            size="sm"
            onClick={onGeminiEditOpen}
            className={
              qualityScore && qualityScore.match_rate < 0.7
                ? "shadow-md shadow-purple-500/20"
                : "from-purple-400/80 to-pink-400/80 shadow-md shadow-purple-400/10 hover:from-purple-500/80 hover:to-pink-500/80"
            }
            title={
              qualityScore && qualityScore.match_rate < 0.7
                ? `Match Rate ${(qualityScore.match_rate * 100).toFixed(0)}% — AI로 수정하세요.`
                : "AI로 포즈/표정/시선을 수정합니다."
            }
          >
            ✨ AI Edit
          </Button>
        )}

        {/* Mark Success / Fail buttons */}
        {scene.activity_log_id && onMarkSuccess && onMarkFail && (
          <>
            <Button
              variant="success"
              size="sm"
              icon
              onClick={onMarkSuccess}
              disabled={isMarkingStatus}
              title="Mark as Success"
            >
              👍
            </Button>
            <Button
              variant="danger"
              size="sm"
              icon
              onClick={onMarkFail}
              disabled={isMarkingStatus}
              title="Mark as Fail"
            >
              👎
            </Button>
          </>
        )}
      </div>

      {/* Menu Button & Popover */}
      <div className="relative">
        <Button ref={menuButtonRef} variant="outline" size="sm" icon onClick={onSceneMenuToggle}>
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </Button>

        <Popover
          anchorRef={menuButtonRef}
          open={sceneMenuOpen}
          onClose={onSceneMenuClose}
          align="right"
          className="w-40"
        >
          <button
            type="button"
            onClick={() => {
              navigator.clipboard
                .writeText(scene.debug_prompt || scene.image_prompt)
                .then(() => showToast("프롬프트 복사됨", "success"))
                .catch(() => showToast("클립보드 복사 실패", "error"));
              onSceneMenuClose();
            }}
            className="w-full px-3 py-2 text-left text-xs text-zinc-700 hover:bg-zinc-50"
          >
            Copy Prompt
          </button>

          {onClothingOpen && !scene.isGenerating && (
            <button
              type="button"
              onClick={() => {
                onClothingOpen();
                onSceneMenuClose();
              }}
              className="w-full px-3 py-2 text-left text-xs text-amber-600 hover:bg-amber-50"
            >
              의상 변경
            </button>
          )}

          <hr className="my-1 border-zinc-100" />

          <button
            type="button"
            onClick={async () => {
              onSceneMenuClose();
              const ok = await confirm({
                title: "Delete Scene",
                message: "이 씬을 삭제하시겠습니까?",
                confirmLabel: "Delete",
                variant: "danger",
              });
              if (ok) onRemoveScene();
            }}
            className="w-full px-3 py-2 text-left text-xs text-red-600 hover:bg-red-50"
          >
            Delete Scene
          </button>
        </Popover>
      </div>

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
