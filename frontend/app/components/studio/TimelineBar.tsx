"use client";

import { useMemo } from "react";
import type { TTSPreviewState } from "../../types";

type TimelineBarProps = {
  scenes: Array<{
    client_id: string;
    script: string;
    duration: number;
  }>;
  ttsStates: Map<string, TTSPreviewState>;
  speedMultiplier?: number;
};

export default function TimelineBar({
  scenes,
  ttsStates,
  speedMultiplier = 1.0,
}: TimelineBarProps) {
  const segments = useMemo(() => {
    return scenes.map((scene) => {
      const tts = ttsStates.get(scene.client_id);
      const ttsDur = tts?.duration ?? null;
      const baseDur = scene.duration / speedMultiplier;
      const effectiveDur = ttsDur && ttsDur > baseDur ? ttsDur + 0.8 : baseDur;
      return {
        clientId: scene.client_id,
        duration: effectiveDur,
        ttsStatus: tts?.status ?? "idle",
      };
    });
  }, [scenes, ttsStates, speedMultiplier]);

  const totalDuration = segments.reduce((sum, s) => sum + s.duration, 0);

  if (scenes.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[11px] text-zinc-400">
        <span>Timeline</span>
        <span>{totalDuration.toFixed(1)}s</span>
      </div>
      <div className="flex h-5 overflow-hidden rounded-lg bg-zinc-100">
        {segments.map((seg, i) => {
          const widthPct = totalDuration > 0 ? (seg.duration / totalDuration) * 100 : 0;
          return (
            <div
              key={seg.clientId}
              className={`relative flex items-center justify-center border-r border-white/50 text-[11px] font-medium transition-all last:border-r-0 ${getSegmentColor(seg.ttsStatus)}`}
              style={{ width: `${widthPct}%`, minWidth: widthPct > 0 ? "12px" : 0 }}
              title={`Scene ${i + 1}: ${seg.duration.toFixed(1)}s (TTS: ${seg.ttsStatus})`}
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
