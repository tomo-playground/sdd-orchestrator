"use client";

import type { Scene } from "../../types";
import Button from "../ui/Button";

type SceneActionBarProps = {
  scene: Scene;
  sceneIndex: number;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  sceneMenuOpen: boolean;
  isLoadingSuggestions: boolean;
  isMarkingStatus?: boolean;
  onGenerateImage: () => void;
  onGeminiEditOpen: () => void;
  onAutoSuggest: () => void;
  onPinToggle?: () => void;
  onMarkSuccess?: () => void;
  onMarkFail?: () => void;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onRemoveScene: () => void;
  onSavePrompt?: () => void;
  showToast: (message: string, type: "success" | "error") => void;
};

export default function SceneActionBar({
  scene,
  sceneIndex,
  qualityScore,
  sceneMenuOpen,
  isLoadingSuggestions,
  isMarkingStatus = false,
  onGenerateImage,
  onGeminiEditOpen,
  onAutoSuggest,
  onPinToggle,
  onMarkSuccess,
  onMarkFail,
  onSceneMenuToggle,
  onSceneMenuClose,
  onUpdateScene,
  onRemoveScene,
  onSavePrompt,
  showToast,
}: SceneActionBarProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
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
            <span className="ml-1 text-[#FFD700] animate-pulse" title="Background Pinned">📌</span>
          )}
        </Button>

        {/* Pin toggle */}
        {sceneIndex > 0 && !scene.isGenerating && onPinToggle && (
          <Button
            variant={scene.environment_reference_id ? "secondary" : "outline"}
            size="sm"
            icon
            onClick={onPinToggle}
            className={scene.environment_reference_id ? "bg-amber-100 text-amber-600 border-amber-300 hover:bg-amber-200" : ""}
            title={scene.environment_reference_id ? "배경 고정 해제" : "이전 장면의 배경을 참조합니다"}
          >
            📌
          </Button>
        )}

        {/* Auto pin indicator */}
        {scene._auto_pin_previous && !scene.environment_reference_id && !scene.image_url && (
          <div className="flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-1.5 text-[10px] text-blue-600">
            <span>💡</span>
            <span className="font-medium">자동 핀 활성</span>
          </div>
        )}

        {/* Gemini Edit button */}
        {scene.image_url && !scene.isGenerating && (
          <Button
            variant="gradient"
            size="sm"
            onClick={onGeminiEditOpen}
            className={qualityScore && qualityScore.match_rate < 0.7
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

        {/* Auto Suggest button */}
        {scene.image_url && !scene.isGenerating && (
          <Button
            variant="gradient"
            size="sm"
            onClick={onAutoSuggest}
            disabled={isLoadingSuggestions}
            loading={isLoadingSuggestions}
            className="from-indigo-500 to-purple-500 shadow-md shadow-indigo-500/20 hover:from-indigo-600 hover:to-purple-600"
            title="이미지와 프롬프트를 비교해 수정을 제안합니다"
          >
            {isLoadingSuggestions ? "분석중..." : "🤖 Auto Suggest"}
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

      {/* Dropdown menu */}
      <DropdownMenu
        scene={scene}
        sceneMenuOpen={sceneMenuOpen}
        onSceneMenuToggle={onSceneMenuToggle}
        onSceneMenuClose={onSceneMenuClose}
        onUpdateScene={onUpdateScene}
        onRemoveScene={onRemoveScene}
        onSavePrompt={onSavePrompt}
        showToast={showToast}
      />
    </div>
  );
}

/* ---- Dropdown sub-component ---- */

type DropdownMenuProps = {
  scene: Scene;
  sceneMenuOpen: boolean;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onRemoveScene: () => void;
  onSavePrompt?: () => void;
  showToast: (message: string, type: "success" | "error") => void;
};

function DropdownMenu({
  scene,
  sceneMenuOpen,
  onSceneMenuToggle,
  onSceneMenuClose,
  onUpdateScene,
  onRemoveScene,
  onSavePrompt,
  showToast,
}: DropdownMenuProps) {
  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        icon
        onClick={onSceneMenuToggle}
      >
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
        </svg>
      </Button>
      {sceneMenuOpen && (
        <div className="absolute right-0 z-10 mt-1 w-40 rounded-xl border border-zinc-200 bg-white py-1 shadow-lg">
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(scene.debug_prompt || scene.image_prompt);
              showToast("프롬프트 복사됨", "success");
              onSceneMenuClose();
            }}
            className="w-full px-3 py-2 text-left text-xs text-zinc-700 hover:bg-zinc-50"
          >
            Copy Prompt
          </button>
          <button
            type="button"
            onClick={() => {
              onUpdateScene({ seed: Math.floor(Math.random() * 999999999) });
              onSceneMenuClose();
            }}
            className="w-full px-3 py-2 text-left text-xs text-zinc-700 hover:bg-zinc-50"
          >
            Randomize Seed
          </button>
          {onSavePrompt && scene.image_url && (
            <button
              type="button"
              onClick={() => {
                onSavePrompt();
                onSceneMenuClose();
              }}
              className="w-full px-3 py-2 text-left text-xs text-emerald-600 hover:bg-emerald-50"
            >
              Save Prompt
            </button>
          )}
          <hr className="my-1 border-zinc-100" />
          <button
            type="button"
            onClick={() => {
              if (confirm("이 씬을 삭제하시겠습니까?")) {
                onRemoveScene();
              }
              onSceneMenuClose();
            }}
            className="w-full px-3 py-2 text-left text-xs text-red-600 hover:bg-red-50"
          >
            Delete Scene
          </button>
        </div>
      )}
    </div>
  );
}
