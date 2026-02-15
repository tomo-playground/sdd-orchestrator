"use client";

import { forwardRef, useEffect, useRef, useState } from "react";
import type { Scene, ImageValidation } from "../../types";
import { hasSceneImage } from "../../utils/sceneCompletion";
import {
  LEFT_PANEL_CLASSES, cx,
  SUCCESS_BG,
  WARNING_BG,
  ERROR_BG
} from "../ui/variants";
import Button from "../ui/Button";

type SceneListPanelProps = {
  scenes: Scene[];
  currentSceneIndex: number;
  onSceneSelect: (index: number) => void;
  onAddScene: () => void;
  onRemoveScene: (index: number) => void;
  onReorderScene: (from: number, to: number) => void;
  imageValidationResults?: Record<string, ImageValidation>;
};

export default function SceneListPanel({
  scenes,
  currentSceneIndex,
  onSceneSelect,
  onAddScene,
  onRemoveScene,
  onReorderScene,
  imageValidationResults,
}: SceneListPanelProps) {
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const el = itemRefs.current[currentSceneIndex];
    if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [currentSceneIndex]);

  const totalDuration = scenes.reduce((sum, s) => sum + (s.duration ?? 0), 0);

  return (
    <aside className={LEFT_PANEL_CLASSES}>
      {/* Header */}
      <div className="border-b border-zinc-200 px-4 py-3">
        <h2 className="text-sm font-bold text-zinc-800">Scenes</h2>
        <p className="text-xs text-zinc-400">
          {scenes.length}개 씬 &middot; 총 {totalDuration}초
        </p>
      </div>

      {/* Scene Cards */}
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {scenes.length === 0 ? (
          <div className="py-12 text-center text-xs text-zinc-400">
            씬이 없습니다.
            <br />
            아래 버튼으로 추가하세요.
          </div>
        ) : (
          scenes.map((scene, idx) => (
            <SceneListItem
              key={scene.client_id}
              ref={(el) => {
                itemRefs.current[idx] = el;
              }}
              scene={scene}
              index={idx}
              isActive={idx === currentSceneIndex}
              imageValidationResults={imageValidationResults}
              onSelect={() => onSceneSelect(idx)}
              onRemove={() => onRemoveScene(idx)}
              onReorder={onReorderScene}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-zinc-200 p-3">
        <Button variant="secondary" size="sm" onClick={onAddScene} className="w-full">
          + 씬 추가
        </Button>
      </div>
    </aside>
  );
}

/* ---- SceneListItem ---- */

type SceneListItemProps = {
  scene: Scene;
  index: number;
  isActive: boolean;
  imageValidationResults?: Record<string, ImageValidation>;
  onSelect: () => void;
  onRemove: () => void;
  onReorder: (from: number, to: number) => void;
};

const SceneListItem = forwardRef<HTMLDivElement, SceneListItemProps>(function SceneListItem(
  { scene, index, isActive, imageValidationResults, onSelect, onRemove, onReorder },
  ref
) {
  const [isDragOver, setIsDragOver] = useState(false);

  const scriptPreview = scene.script?.trim() ? scene.script.trim().slice(0, 40) : "스크립트 없음";

  return (
    <div
      ref={ref}
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
      draggable
      onDragStart={(e) => e.dataTransfer.setData("application/x-scene-index", String(index))}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragOver(false);
        const from = parseInt(e.dataTransfer.getData("application/x-scene-index"), 10);
        if (!isNaN(from) && from !== index) onReorder(from, index);
      }}
      onDragEnd={() => setIsDragOver(false)}
      className={cx(
        "group flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 transition-colors",
        isActive ? "border-l-2 border-purple-500 bg-white shadow-sm" : "hover:bg-white/60",
        isDragOver && "ring-2 ring-blue-400"
      )}
    >
      {/* Drag Handle */}
      <span className="cursor-grab text-zinc-300 group-hover:text-zinc-400">
        <GripIcon />
      </span>

      {/* Scene Number */}
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-zinc-100 text-[11px] font-bold text-zinc-500">
        {index + 1}
      </span>

      {/* Thumbnail */}
      {scene.image_url ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={scene.image_url}
          alt={`Scene ${index + 1}`}
          className="h-9 w-9 flex-shrink-0 rounded-md bg-zinc-100 object-cover"
        />
      ) : null}

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-zinc-700">{scriptPreview}</p>
        <p className="text-[11px] text-zinc-400">{scene.duration ?? 3}초</p>
      </div>

      {/* Completion Dots */}
      <CompletionDots scene={scene} imageValidationResults={imageValidationResults} />

      {/* Remove */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        className="shrink-0 rounded p-0.5 text-zinc-300 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-600"
        title="삭제"
      >
        <TrashIcon />
      </button>
    </div>
  );
});

/* ---- CompletionDots (ported from SceneFilmstrip) ---- */

const DOT_COLORS = {
  green: SUCCESS_BG,
  amber: WARNING_BG,
  red: ERROR_BG,
  gray: "bg-zinc-300",
} as const;

function CompletionDots({
  scene,
  imageValidationResults,
}: {
  scene: Scene;
  imageValidationResults?: Record<string, ImageValidation>;
}) {
  const hasScript = scene.script.trim().length > 0;
  const hasImage = hasSceneImage(scene);
  const matchResult = imageValidationResults?.[scene.client_id];
  const rate = matchResult?.match_rate;
  const hasActions = (scene.character_actions?.length ?? 0) > 0;

  const scriptColor = hasScript ? "green" : "red";
  const imageColor = hasImage ? "green" : "red";
  const validationColor =
    rate == null ? "gray" : rate >= 70 ? "green" : rate >= 50 ? "amber" : "red";
  const actionColor = hasActions ? "green" : "gray";

  const dots: Array<{ color: keyof typeof DOT_COLORS; label: string }> = [
    { color: scriptColor, label: `대본: ${hasScript ? "있음" : "없음"}` },
    { color: imageColor, label: `이미지: ${hasImage ? "있음" : "없음"}` },
    { color: validationColor, label: rate != null ? `검증: ${Math.round(rate)}%` : "검증: 미실행" },
    { color: actionColor, label: `액션: ${hasActions ? "있음" : "N/A"}` },
  ];

  return (
    <div className="flex gap-0.5">
      {dots.map((d) => (
        <span
          key={d.label}
          title={d.label}
          className={`h-1.5 w-1.5 rounded-full ${DOT_COLORS[d.color]} ring-1 ring-black/20`}
        />
      ))}
    </div>
  );
}

/* ---- Icons ---- */

function GripIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
      <circle cx="4" cy="2" r="1" />
      <circle cx="8" cy="2" r="1" />
      <circle cx="4" cy="6" r="1" />
      <circle cx="8" cy="6" r="1" />
      <circle cx="4" cy="10" r="1" />
      <circle cx="8" cy="10" r="1" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14" />
    </svg>
  );
}
