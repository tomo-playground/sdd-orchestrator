"use client";

import { useState } from "react";
import { ArrowRight, Save } from "lucide-react";
import Button from "../ui/Button";
import SceneReasoningPanel from "./SceneReasoningPanel";
import type { SceneItem } from "../../hooks/useScriptEditor";
import type { SceneReasoning } from "../../types";

type Props = {
  scenes: SceneItem[];
  isSaving: boolean;
  approveLabel?: string;
  onApprove: () => void;
  compact?: boolean;
  reasonings?: Record<number, SceneReasoning>;
};

export default function ScriptSceneList({
  scenes,
  isSaving,
  approveLabel = "Save",
  onApprove,
  compact = false,
  reasonings,
}: Props) {
  const [openReasoningId, setOpenReasoningId] = useState<number | null>(null);

  if (scenes.length === 0) return null;

  const totalDuration = scenes.reduce((sum, s) => sum + (s.duration ?? 0), 0);

  return (
    <div className="space-y-3">
      <div
        className={`flex items-center justify-between ${compact ? "flex-col items-start gap-2" : ""}`}
      >
        <div className="flex items-baseline gap-2">
          <h3 className="text-sm font-semibold text-zinc-900">Scenes ({scenes.length})</h3>
          <span className="text-[12px] text-zinc-400">{totalDuration}s</span>
        </div>
        <Button
          size="sm"
          loading={isSaving}
          onClick={onApprove}
          className={compact ? "w-full" : ""}
        >
          {approveLabel === "Save" ? (
            <Save className="h-3.5 w-3.5" />
          ) : (
            <ArrowRight className="h-3.5 w-3.5" />
          )}
          {approveLabel}
        </Button>
      </div>

      <div className="space-y-2">
        {scenes.map((scene) => {
          const reasoning = reasonings?.[scene.id];
          const isOpen = openReasoningId === scene.id;

          return (
            <div
              key={scene.client_id ?? scene.id}
              className="rounded-xl border border-zinc-200 bg-white px-4 py-3"
            >
              <div className="flex items-start gap-2">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-[12px] font-bold text-white">
                  {scene.order}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-[12px] font-medium text-zinc-400">{scene.speaker}</span>
                    <span className="text-[12px] text-zinc-300">{scene.duration}s</span>
                    {reasoning && (
                      <button
                        className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] font-medium text-zinc-500 hover:bg-zinc-200 hover:text-zinc-700"
                        onClick={() => setOpenReasoningId(isOpen ? null : scene.id)}
                      >
                        왜?
                      </button>
                    )}
                  </div>
                  <p className="text-xs leading-relaxed text-zinc-800">{scene.script}</p>
                </div>
                {scene.image_url && (
                  <div className="h-8 w-8 shrink-0 overflow-hidden rounded-lg border border-zinc-200">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={scene.image_url}
                      alt={`Scene ${scene.order}`}
                      className="h-full w-full object-cover"
                    />
                  </div>
                )}
              </div>

              {/* Image prompt (read-only) */}
              {scene.image_prompt && (
                <p className="mt-1.5 line-clamp-2 pl-7 text-[12px] leading-relaxed text-zinc-400">
                  {scene.image_prompt}
                </p>
              )}

              {/* Scene reasoning panel */}
              {reasoning && isOpen && (
                <SceneReasoningPanel
                  reasoning={reasoning}
                  onClose={() => setOpenReasoningId(null)}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
