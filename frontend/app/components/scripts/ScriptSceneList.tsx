"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, Save } from "lucide-react";
import Button from "../ui/Button";
import type { SceneItem } from "../../hooks/useScriptEditor";

type Props = {
  scenes: SceneItem[];
  storyboardId: number | null;
  isSaving: boolean;
  onUpdateScene: (index: number, patch: Partial<SceneItem>) => void;
  onSave: () => void;
};

export default function ScriptSceneList({
  scenes,
  storyboardId,
  isSaving,
  onUpdateScene,
  onSave,
}: Props) {
  const router = useRouter();

  if (scenes.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-900">Scenes ({scenes.length})</h3>
        <div className="flex items-center gap-2">
          {storyboardId && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => router.push(`/studio?id=${storyboardId}`)}
            >
              <ArrowRight className="h-3.5 w-3.5" />
              Studio
            </Button>
          )}
          <Button size="sm" loading={isSaving} onClick={onSave}>
            <Save className="h-3.5 w-3.5" />
            Save
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {scenes.map((scene, idx) => (
          <div
            key={scene.client_id ?? scene.id}
            className="rounded-xl border border-zinc-200 bg-white p-4 transition hover:shadow-sm"
          >
            <div className="mb-2 flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-900 text-[12px] font-bold text-white">
                {scene.order}
              </span>
              <span className="text-[12px] font-medium text-zinc-400">{scene.speaker}</span>
              <span className="text-[12px] text-zinc-300">{scene.duration}s</span>
              {scene.image_url && (
                <div className="ml-auto h-8 w-8 shrink-0 overflow-hidden rounded-lg border border-zinc-200">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={scene.image_url}
                    alt={`Scene ${scene.order}`}
                    className="h-full w-full object-cover"
                  />
                </div>
              )}
            </div>

            {/* Script (editable) */}
            <textarea
              value={scene.script}
              onChange={(e) => onUpdateScene(idx, { script: e.target.value })}
              rows={2}
              className="w-full rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs text-zinc-800 transition outline-none focus:border-zinc-300 focus:bg-white"
            />

            {/* Image prompt (read-only) */}
            {scene.image_prompt && (
              <p className="mt-1.5 line-clamp-2 text-[12px] leading-relaxed text-zinc-400">
                {scene.image_prompt}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
