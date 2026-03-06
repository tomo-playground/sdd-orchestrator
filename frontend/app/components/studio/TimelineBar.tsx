"use client";

import { useMemo } from "react";
import type { TTSPreviewState, TimelineResponse } from "../../types";
import { formatMmSs } from "../../utils/format";

type TimelineBarProps = {
  scenes: Array<{
    client_id: string;
    script: string;
    duration: number;
  }>;
  ttsStates: Map<string, TTSPreviewState>;
  speedMultiplier?: number;
  timeline?: TimelineResponse | null;
  activeSceneIndex?: number;
  onSceneClick?: (index: number) => void;
};

export default function TimelineBar({
  scenes,
  ttsStates,
  speedMultiplier = 1.0,
  timeline,
  activeSceneIndex,
  onSceneClick,
}: TimelineBarProps) {
  // Server data or client fallback
  const segments = useMemo(() => {
    if (timeline && timeline.scenes.length === scenes.length) {
      return timeline.scenes.map((ts, i) => {
        const tts = ttsStates.get(scenes[i].client_id);
        const baseDur = scenes[i].duration / speedMultiplier;
        return {
          clientId: scenes[i].client_id,
          duration: ts.effective_duration,
          ttsStatus: tts?.status ?? "idle",
          startTime: ts.start_time,
          endTime: ts.end_time,
          ttsDuration: ts.tts_duration,
          ttsExtended: ts.has_tts && ts.effective_duration > baseDur,
        };
      });
    }
    // Client fallback
    let cumTime = 0;
    return scenes.map((scene) => {
      const tts = ttsStates.get(scene.client_id);
      const ttsDur = tts?.duration ?? null;
      const baseDur = scene.duration / speedMultiplier;
      const effectiveDur = ttsDur && ttsDur > baseDur ? ttsDur + 0.8 : baseDur;
      const start = cumTime;
      cumTime += effectiveDur;
      return {
        clientId: scene.client_id,
        duration: effectiveDur,
        ttsStatus: tts?.status ?? "idle",
        startTime: start,
        endTime: cumTime,
        ttsDuration: ttsDur,
        ttsExtended: ttsDur != null && ttsDur > baseDur,
      };
    });
  }, [scenes, ttsStates, speedMultiplier, timeline]);

  const totalDuration =
    timeline?.total_duration ?? segments.reduce((sum, s) => sum + s.duration, 0);

  if (scenes.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[11px] text-zinc-400">
        <span>Timeline</span>
        <span>{formatMmSs(totalDuration)}</span>
      </div>
      <div className="flex h-5 overflow-hidden rounded-lg bg-zinc-100">
        {segments.map((seg, i) => {
          const widthPct = totalDuration > 0 ? (seg.duration / totalDuration) * 100 : 0;
          const isActive = activeSceneIndex === i;
          const clickable = !!onSceneClick;

          return (
            <div
              key={seg.clientId}
              role={clickable ? "button" : undefined}
              tabIndex={clickable ? 0 : undefined}
              onClick={clickable ? () => onSceneClick(i) : undefined}
              onKeyDown={clickable ? (e) => e.key === "Enter" && onSceneClick(i) : undefined}
              className={[
                "relative flex items-center justify-center border-r border-white/50 text-[11px] font-medium transition-all last:border-r-0",
                getSegmentColor(seg.ttsStatus),
                isActive && "ring-2 ring-blue-400 ring-inset",
                clickable && "cursor-pointer hover:brightness-110",
                seg.ttsExtended && "ring-1 ring-amber-400 ring-inset",
              ]
                .filter(Boolean)
                .join(" ")}
              style={{ width: `${widthPct}%`, minWidth: widthPct > 0 ? "12px" : 0 }}
              title={`Scene ${i + 1}: ${seg.startTime.toFixed(1)}~${seg.endTime.toFixed(1)}s${seg.ttsDuration != null ? ` (TTS: ${seg.ttsDuration.toFixed(1)}s)` : ""}`}
            >
              {widthPct > 6 && <span className="text-white/80">{i + 1}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function getSegmentColor(ttsStatus: string): string {
  switch (ttsStatus) {
    case "cached":
      return "bg-emerald-400";
    case "loading":
      return "bg-amber-400";
    case "error":
      return "bg-red-400";
    default:
      return "bg-zinc-300";
  }
}
