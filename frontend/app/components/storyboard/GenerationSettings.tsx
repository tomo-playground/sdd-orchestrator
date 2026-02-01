"use client";

import type { Scene } from "../../types";
import { SAMPLERS } from "../../constants";

type GenerationSettingsProps = {
  scene: Scene;
  autoComposePrompt: boolean;
  onUpdateScene: (updates: Partial<Scene>) => void;
};

export default function GenerationSettings({
  scene,
  autoComposePrompt,
  onUpdateScene,
}: GenerationSettingsProps) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <div className="flex flex-col gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Steps
        </label>
        <input
          type="number"
          min={1}
          max={80}
          value={scene.steps}
          onChange={(e) => onUpdateScene({ steps: Number(e.target.value) })}
          disabled={autoComposePrompt}
          className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          CFG
        </label>
        <input
          type="number"
          min={1}
          max={20}
          step={0.5}
          value={scene.cfg_scale}
          onChange={(e) => onUpdateScene({ cfg_scale: Number(e.target.value) })}
          disabled={autoComposePrompt}
          className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Sampler
        </label>
        <select
          value={scene.sampler_name}
          onChange={(e) => onUpdateScene({ sampler_name: e.target.value })}
          disabled={autoComposePrompt}
          className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
        >
          {SAMPLERS.map((sampler) => (
            <option key={sampler} value={sampler}>
              {sampler}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Seed
        </label>
        <input
          type="number"
          value={scene.seed}
          onChange={(e) => onUpdateScene({ seed: Number(e.target.value) })}
          disabled={autoComposePrompt}
          className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Clip Skip
        </label>
        <input
          type="number"
          min={1}
          max={12}
          value={scene.clip_skip}
          onChange={(e) => onUpdateScene({ clip_skip: Number(e.target.value) })}
          disabled={autoComposePrompt}
          className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </div>
    </div>
  );
}
