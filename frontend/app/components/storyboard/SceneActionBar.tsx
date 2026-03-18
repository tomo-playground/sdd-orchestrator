"use client";

import type { Scene } from "../../types";
import Button from "../ui/Button";
import ConfirmDialog, { useConfirm } from "../ui/ConfirmDialog";

type SceneActionBarProps = {
  scene: Scene;
  sceneIndex: number;
  sceneMenuOpen: boolean;
  isLoadingSuggestions: boolean;
  onGeminiEditOpen: () => void;
  onEditImageOpen?: () => void;
  onClothingOpen?: () => void;
  onAutoSuggest: () => void;
  compact?: boolean;
};

import { useRef, useState } from "react";
import Popover from "../ui/Popover";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useSceneContext } from "./SceneContext";

type BgInfo = { image_url: string | null; tags: string[]; location_key: string } | null;

function BgBadge({ backgroundId, bgInfo, onClear }: { backgroundId: number; bgInfo: BgInfo; onClear: () => void }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="flex cursor-default items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 py-1 pr-1.5 pl-2.5 text-[12px] text-emerald-600">
        <span>🎬 BG#{backgroundId}</span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onClear();
          }}
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

      {hovered && (
        <div className="absolute bottom-full left-0 z-50 mb-1.5 w-56 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-lg">
          <div className="flex h-16 w-full items-center justify-center overflow-hidden bg-zinc-100">
            {bgInfo?.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={bgInfo.image_url}
                alt={`BG#${backgroundId}`}
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="text-[11px] text-zinc-400">이미지 없음</span>
            )}
          </div>

          <div className="px-2.5 py-2">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[12px] font-semibold text-zinc-700">BG#{backgroundId}</span>
              {bgInfo?.location_key && (
                <span
                  className="ml-2 max-w-[100px] truncate text-[11px] text-zinc-400"
                  title={bgInfo.location_key}
                >
                  {bgInfo.location_key}
                </span>
              )}
            </div>
            {bgInfo?.tags && bgInfo.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {bgInfo.tags.slice(0, 4).map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] text-zinc-500"
                  >
                    {tag}
                  </span>
                ))}
                {bgInfo.tags.length > 4 && (
                  <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] text-zinc-400">
                    +{bgInfo.tags.length - 4}
                  </span>
                )}
              </div>
            )}
            {!bgInfo && <span className="text-[11px] text-zinc-400">배경 정보 로딩 전</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export default function SceneActionBar({
  scene,
  sceneIndex,
  sceneMenuOpen,
  isLoadingSuggestions,
  onGeminiEditOpen,
  onEditImageOpen,
  onClothingOpen,
  onAutoSuggest,
  compact = false,
}: SceneActionBarProps) {
  const { data, callbacks } = useSceneContext();
  const {
    qualityScore,
    pinnedSceneOrder,
    isMarkingStatus,
  } = data;
  const {
    onGenerateImage,
    onUpdateScene,
    onRemoveScene,
    showToast,
    onPinToggle,
    onMarkSuccess,
    onMarkFail,
    onSceneMenuToggle,
    onSceneMenuClose,
  } = callbacks;
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const { confirm, dialogProps } = useConfirm();
  const stageLocations = useStoryboardStore((s) => s.stageLocations);
  const bgInfo = scene.background_id
    ? (stageLocations.find((loc) => loc.background_id === scene.background_id) ?? null)
    : null;

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
          <BgBadge
            backgroundId={scene.background_id}
            bgInfo={bgInfo}
            onClear={() =>
              onUpdateScene({
                background_id: null,
                environment_reference_id: null,
                _cleared_background_id: scene.background_id,
              })
            }
          />
        )}

        {/* Pin toggle — only when no Stage background */}
        {!scene.background_id && sceneIndex > 0 && !scene.isGenerating && onPinToggle && (
          <Button
            variant={scene.environment_reference_id ? "secondary" : "outline"}
            size="sm"
            icon={!scene.environment_reference_id}
            onClick={onPinToggle}
            className={
              scene.environment_reference_id
                ? "border-amber-300 bg-amber-100 text-amber-600 hover:bg-amber-200"
                : ""
            }
            title={
              scene.environment_reference_id
                ? `S${sceneIndex + 1}→S${pinnedSceneOrder != null ? pinnedSceneOrder + 1 : "?"} 배경 참조 중 (클릭하여 해제)`
                : "이전 장면의 배경을 참조합니다"
            }
          >
            📌
            {scene.environment_reference_id ? (
              <span className="ml-0.5 text-[12px]">
                S{sceneIndex + 1}
                {pinnedSceneOrder != null ? `→S${pinnedSceneOrder + 1}` : ""}
              </span>
            ) : null}
          </Button>
        )}

        {/* Auto pin indicator — only when no Stage background */}
        {!scene.background_id &&
          scene._auto_pin_previous &&
          !scene.environment_reference_id &&
          !scene.image_url && (
            <div className="flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-[12px] text-blue-600">
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

          {onEditImageOpen && scene.image_url && !scene.isGenerating && (
            <button
              type="button"
              onClick={() => {
                onEditImageOpen();
                onSceneMenuClose();
              }}
              className="w-full px-3 py-2 text-left text-xs text-indigo-600 hover:bg-indigo-50"
            >
              이미지 편집
            </button>
          )}

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
                title: "씬 삭제",
                message: "이 씬을 삭제하시겠습니까?",
                confirmLabel: "삭제",
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
