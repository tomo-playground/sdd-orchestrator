"use client";

import type { Scene } from "../../types";

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
        <button
          type="button"
          onClick={onGenerateImage}
          disabled={scene.isGenerating}
          className="rounded-full bg-zinc-900 px-5 py-2.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400 flex items-center gap-2"
        >
          {scene.isGenerating ? "Generating..." : "Generate Image"}
          {scene.environment_reference_id && !scene.isGenerating && (
            <span className="ml-1 text-[#FFD700] animate-pulse" title="Background Pinned">📌</span>
          )}
        </button>

        {/* Pin toggle */}
        {sceneIndex > 0 && !scene.isGenerating && onPinToggle && (
          <button
            type="button"
            onClick={onPinToggle}
            className={`rounded-full p-2.5 text-[10px] shadow-md transition ${scene.environment_reference_id ? 'bg-amber-100 text-amber-600 border border-amber-300' : 'bg-white text-zinc-400 border border-zinc-200 hover:bg-zinc-50'}`}
            title={scene.environment_reference_id ? "배경 고정 해제" : "이전 장면의 배경을 참조합니다"}
          >
            📌
          </button>
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
          <button
            type="button"
            onClick={onGeminiEditOpen}
            className={`rounded-full px-4 py-2.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md transition ${qualityScore && qualityScore.match_rate < 0.7
              ? "bg-gradient-to-r from-purple-500 to-pink-500 shadow-purple-500/20 hover:from-purple-600 hover:to-pink-600"
              : "bg-gradient-to-r from-purple-400/80 to-pink-400/80 shadow-purple-400/10 hover:from-purple-500/80 hover:to-pink-500/80"
              }`}
            title={
              qualityScore && qualityScore.match_rate < 0.7
                ? `Match Rate가 낮습니다 (${(qualityScore.match_rate * 100).toFixed(0)}%). Gemini로 수정하세요.`
                : "Gemini로 포즈/표정/시선을 수정할 수 있습니다."
            }
          >
            ✨ Edit with Gemini
          </button>
        )}

        {/* Auto Suggest button */}
        {scene.image_url && !scene.isGenerating && (
          <button
            type="button"
            onClick={onAutoSuggest}
            disabled={isLoadingSuggestions}
            className="rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-2.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md shadow-indigo-500/20 transition hover:from-indigo-600 hover:to-purple-600 disabled:cursor-not-allowed disabled:opacity-50"
            title="Gemini가 이미지와 프롬프트를 비교해 자동으로 수정 제안을 생성합니다"
          >
            {isLoadingSuggestions ? "분석중..." : "🤖 Auto Suggest"}
          </button>
        )}

        {/* Mark Success / Fail buttons */}
        {scene.activity_log_id && onMarkSuccess && onMarkFail && (
          <>
            <button
              type="button"
              onClick={onMarkSuccess}
              disabled={isMarkingStatus}
              title="Mark as Success"
              className="rounded-full bg-emerald-500 px-3 py-2 text-[10px] font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-emerald-300"
            >
              👍
            </button>
            <button
              type="button"
              onClick={onMarkFail}
              disabled={isMarkingStatus}
              title="Mark as Fail"
              className="rounded-full bg-rose-500 px-3 py-2 text-[10px] font-semibold text-white transition hover:bg-rose-600 disabled:cursor-not-allowed disabled:bg-rose-300"
            >
              👎
            </button>
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
      <button
        type="button"
        onClick={onSceneMenuToggle}
        className="rounded-full border border-zinc-200 bg-white p-2 text-zinc-500 transition hover:bg-zinc-50"
      >
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
        </svg>
      </button>
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
