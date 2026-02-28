"use client";

import type { RenderProgress, RenderStage } from "../../types";
import { SIDE_PANEL_LABEL, TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";

export const STAGE_LABELS: Record<RenderStage, string> = {
  queued: "대기중",
  setup_avatars: "아바타 설정",
  process_scenes: "음성 생성",
  calculate_durations: "시간 계산",
  prepare_bgm: "BGM 준비",
  build_filters: "필터 구성",
  encode: "인코딩",
  upload: "업로드",
  completed: "완료",
  failed: "실패",
};

export type RenderSidePanelProps = {
  layoutStyle: "full" | "post";
  setLayoutStyle: (value: "full" | "post") => void;
  frameStyle: string;
  setFrameStyle: (value: string) => void;
  canRender: boolean;
  isRendering: boolean;
  scenesWithImages: number;
  totalScenes: number;
  onRender: () => void;
  onQuickRender?: () => void;
  disabledReason?: string | null;
  renderPresetName?: string | null;
  renderPresetSource?: string | null;
  renderProgress?: RenderProgress | null;
};

export function RenderSidePanel({
  layoutStyle,
  setLayoutStyle,
  frameStyle,
  setFrameStyle,
  canRender,
  isRendering,
  scenesWithImages,
  totalScenes,
  onRender,
  onQuickRender,
  disabledReason,
  renderPresetName,
  renderPresetSource,
  renderProgress,
}: RenderSidePanelProps) {
  return (
    <>
      {/* Layout */}
      <div>
        <label className={SIDE_PANEL_LABEL}>Layout</label>
        <div className="flex rounded-full border border-zinc-200 bg-zinc-50 p-0.5">
          <button
            type="button"
            onClick={() => setLayoutStyle("full")}
            className={`flex-1 rounded-full px-3 py-1.5 text-[12px] font-semibold transition ${
              layoutStyle === "full" ? TAB_ACTIVE : TAB_INACTIVE
            }`}
          >
            Full 9:16
          </button>
          <button
            type="button"
            onClick={() => setLayoutStyle("post")}
            className={`flex-1 rounded-full px-3 py-1.5 text-[12px] font-semibold transition ${
              layoutStyle === "post" ? TAB_ACTIVE : TAB_INACTIVE
            }`}
          >
            Post 1:1
          </button>
        </div>
        {layoutStyle === "full" && (
          <select
            value={frameStyle}
            onChange={(e) => setFrameStyle(e.target.value)}
            className="mt-2 w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-[12px] outline-none focus:border-zinc-400"
          >
            <option value="overlay_minimal.png">Minimal</option>
            <option value="overlay_modern.png">Modern</option>
            <option value="overlay_classic.png">Classic</option>
          </select>
        )}
      </div>

      {/* Render Action */}
      <div className="flex flex-col items-center gap-2">
        {onQuickRender && (
          <button
            onClick={onQuickRender}
            disabled={!canRender || isRendering}
            title={disabledReason || undefined}
            className="w-full rounded-full border-2 border-zinc-900 bg-white py-2.5 text-xs font-semibold text-zinc-900 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Quick Render
            <span className="mt-0.5 block text-[11px] font-normal text-zinc-400">
              기본 설정으로 즉시 렌더링
            </span>
          </button>
        )}
        <button
          onClick={onRender}
          disabled={!canRender || isRendering}
          title={disabledReason || undefined}
          className="w-full rounded-full bg-zinc-900 py-2.5 text-xs font-semibold text-white shadow-lg transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isRendering ? "Rendering..." : "Render"}
        </button>

        {/* Progress Bar */}
        {isRendering && renderProgress && (
          <div className="w-full space-y-1.5">
            <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-200">
              <div
                className="h-full rounded-full bg-zinc-900 transition-all duration-300 ease-out"
                style={{ width: `${renderProgress.percent}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[12px] text-zinc-500">
              <span>
                {STAGE_LABELS[renderProgress.stage] || renderProgress.stage}
                {renderProgress.message ? ` (${renderProgress.message})` : ""}
              </span>
              <span className="font-medium">{renderProgress.percent}%</span>
            </div>
            {renderProgress.estimated_remaining_seconds != null &&
              renderProgress.estimated_remaining_seconds > 0 && (
                <p className="text-[11px] text-zinc-400">
                  남은 시간: ~{Math.ceil(renderProgress.estimated_remaining_seconds)}초
                </p>
              )}
          </div>
        )}

        <span className="text-[12px] text-zinc-400">
          Images: {scenesWithImages}/{totalScenes}
        </span>
        {disabledReason && (
          <p className="rounded-full bg-amber-50 px-2.5 py-1 text-center text-[12px] font-medium text-amber-600">
            {disabledReason}
          </p>
        )}
      </div>

      {/* Preset */}
      {renderPresetName && (
        <div>
          <label className={SIDE_PANEL_LABEL}>Preset</label>
          <p className="text-xs font-medium text-indigo-600">{renderPresetName}</p>
          {renderPresetSource && (
            <p className="text-[11px] text-indigo-400">from {renderPresetSource}</p>
          )}
        </div>
      )}
    </>
  );
}

export default RenderSidePanel;
