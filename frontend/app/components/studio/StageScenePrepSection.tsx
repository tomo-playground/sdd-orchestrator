"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import type { Scene } from "../../types";

const SPEAKER_COLORS: Record<string, string> = {
  Narrator: "bg-zinc-100 text-zinc-500",
  A: "bg-violet-100 text-violet-700",
  B: "bg-sky-100 text-sky-700",
};

function SceneRow({ scene }: { scene: Scene }) {
  const [open, setOpen] = useState(false);
  const emotion = scene.context_tags?.emotion;
  const camera = scene.context_tags?.camera;
  const mood = scene.context_tags?.mood;
  const hasVoice = !!scene.voice_design_prompt;
  const hasPacing = scene.head_padding != null || scene.tail_padding != null;
  const hasDetail = !!scene.image_prompt_ko || hasVoice || hasPacing;

  return (
    <div className="border-b border-zinc-100 last:border-0">
      {/* Row header */}
      <button
        type="button"
        onClick={() => hasDetail && setOpen((v) => !v)}
        className={`flex w-full items-start gap-2 px-3 py-2 text-left transition ${hasDetail ? "hover:bg-zinc-50" : ""}`}
      >
        {/* Scene number */}
        <span className="mt-0.5 w-6 shrink-0 text-[11px] font-medium text-zinc-400">
          #{scene.order}
        </span>

        {/* Speaker badge */}
        <span
          className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium ${SPEAKER_COLORS[scene.speaker] ?? SPEAKER_COLORS.Narrator}`}
        >
          {scene.speaker}
        </span>

        {/* Inline tags */}
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
          {emotion && (
            <span className="rounded bg-rose-50 px-1.5 py-0.5 text-[11px] text-rose-600">
              {emotion}
            </span>
          )}
          {camera && (
            <span className="rounded bg-violet-50 px-1.5 py-0.5 text-[11px] text-violet-600">
              {camera}
            </span>
          )}
          {mood && mood.length > 0 && (
            <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] text-amber-600">
              {Array.isArray(mood) ? mood[0] : mood}
            </span>
          )}
          {hasVoice && (
            <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[11px] text-emerald-600">
              음성 설계
            </span>
          )}
          {/* Script excerpt */}
          <span className="min-w-0 truncate text-[11px] text-zinc-400">{scene.script}</span>
        </div>

        {/* Expand icon */}
        {hasDetail && (
          <span className="mt-0.5 shrink-0 text-zinc-300">
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
        )}
      </button>

      {/* Expanded detail */}
      {open && hasDetail && (
        <div className="space-y-2 bg-zinc-50 px-3 pb-3 pt-1">
          {scene.image_prompt_ko && (
            <div>
              <p className="text-[11px] font-medium text-zinc-400">시각 설계</p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-zinc-600">
                {scene.image_prompt_ko}
              </p>
            </div>
          )}
          {hasVoice && (
            <div>
              <p className="text-[11px] font-medium text-zinc-400">음성 디자인</p>
              <p className="mt-0.5 text-[11px] leading-relaxed text-zinc-600">
                {scene.voice_design_prompt}
              </p>
            </div>
          )}
          {hasPacing && (
            <div className="flex gap-3">
              {scene.head_padding != null && (
                <p className="text-[11px] text-zinc-400">
                  앞 여백 <span className="text-zinc-600">{scene.head_padding}s</span>
                </p>
              )}
              {scene.tail_padding != null && (
                <p className="text-[11px] text-zinc-400">
                  뒤 여백 <span className="text-zinc-600">{scene.tail_padding}s</span>
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function StageScenePrepSection() {
  const scenes = useStoryboardStore((s) => s.scenes);
  const [expanded, setExpanded] = useState(false);

  const preparedCount = scenes.filter(
    (s) => s.context_tags?.emotion || s.voice_design_prompt || s.image_prompt_ko
  ).length;

  if (preparedCount === 0) return null;

  return (
    <section>
      {/* Section header */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mb-2 flex w-full items-center justify-between"
      >
        <h3 className="text-sm font-semibold text-zinc-800">씬별 AI 준비 현황</h3>
        <span className="flex items-center gap-1.5 text-[11px] text-zinc-400">
          {preparedCount}/{scenes.length}개 준비됨
          {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </span>
      </button>

      {expanded && (
        <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
          {scenes.map((scene) => (
            <SceneRow key={scene.id} scene={scene} />
          ))}
        </div>
      )}
    </section>
  );
}
