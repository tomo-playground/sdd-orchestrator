"use client";

import { useState } from "react";
import type { ActorGender } from "../types";
import { PROMPT_SAMPLES, SAMPLERS } from "../constants";

type PromptSetupPanelProps = {
  // Tab state
  baseTab: "global" | "A";
  setBaseTab: (value: "global" | "A") => void;
  // Global settings
  autoComposePrompt: boolean;
  setAutoComposePrompt: (value: boolean) => void;
  autoRewritePrompt: boolean;
  setAutoRewritePrompt: (value: boolean) => void;
  hiResEnabled: boolean;
  setHiResEnabled: (value: boolean) => void;
  veoEnabled: boolean;
  setVeoEnabled: (value: boolean) => void;
  // Actor A settings
  actorAGender: ActorGender;
  setActorAGender: (value: ActorGender) => void;
  basePromptA: string;
  setBasePromptA: (value: string) => void;
  baseNegativePromptA: string;
  setBaseNegativePromptA: (value: string) => void;
  baseStepsA: number;
  setBaseStepsA: (value: number) => void;
  baseCfgScaleA: number;
  setBaseCfgScaleA: (value: number) => void;
  baseSamplerA: string;
  setBaseSamplerA: (value: string) => void;
  baseSeedA: number;
  setBaseSeedA: (value: number) => void;
  baseClipSkipA: number;
  setBaseClipSkipA: (value: number) => void;
  // Sample selection
  selectedSampleId: string;
  setSelectedSampleId: (value: string) => void;
  onOpenPromptHelper: () => void;
};

export default function PromptSetupPanel({
  baseTab,
  setBaseTab,
  autoComposePrompt,
  setAutoComposePrompt,
  autoRewritePrompt,
  setAutoRewritePrompt,
  hiResEnabled,
  setHiResEnabled,
  veoEnabled,
  setVeoEnabled,
  actorAGender,
  setActorAGender,
  basePromptA,
  setBasePromptA,
  baseNegativePromptA,
  setBaseNegativePromptA,
  baseStepsA,
  setBaseStepsA,
  baseCfgScaleA,
  setBaseCfgScaleA,
  baseSamplerA,
  setBaseSamplerA,
  baseSeedA,
  setBaseSeedA,
  baseClipSkipA,
  setBaseClipSkipA,
  selectedSampleId,
  setSelectedSampleId,
  onOpenPromptHelper,
}: PromptSetupPanelProps) {
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const handleInsertSample = () => {
    const sample = PROMPT_SAMPLES.find((item) => item.id === selectedSampleId);
    if (!sample) return;
    setBasePromptA(sample.basePrompt);
    setBaseNegativePromptA(sample.baseNegative);
  };

  return (
    <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">Prompt Setup</h2>
          <p className="text-xs text-zinc-500">Define global prompt rules and actor setup.</p>
          <p className="text-[10px] text-zinc-400">
            Tip: Base Prompt is identity/style. Scene prompts handle action, camera, and
            background.
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {[
          { id: "global", label: "Global" },
          { id: "A", label: "Actor A" },
        ].map((tab) => {
          const active = baseTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setBaseTab(tab.id as "global" | "A")}
              className={`rounded-full px-4 py-2 text-[10px] font-semibold tracking-[0.2em] uppercase transition ${
                active ? "bg-zinc-900 text-white" : "bg-white/80 text-zinc-600"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {baseTab === "global" && (
        <div className="grid gap-3">
          <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
            Auto Compose Prompt
            <input
              type="checkbox"
              checked={autoComposePrompt}
              onChange={(e) => setAutoComposePrompt(e.target.checked)}
              className="h-4 w-4 accent-zinc-900"
            />
          </label>
          <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
            Auto Rewrite Prompt (Gemini)
            <input
              type="checkbox"
              checked={autoRewritePrompt}
              onChange={(e) => setAutoRewritePrompt(e.target.checked)}
              className="h-4 w-4 accent-zinc-900"
            />
          </label>
          <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
            Hi-Res Fix (1.5x)
            <input
              type="checkbox"
              checked={hiResEnabled}
              onChange={(e) => setHiResEnabled(e.target.checked)}
              className="h-4 w-4 accent-zinc-900"
            />
          </label>
          <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-zinc-100/50 px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-400 uppercase cursor-not-allowed">
            <span>VEO Clip <span className="text-[9px] text-zinc-400 normal-case">(Coming Soon)</span></span>
            <input
              type="checkbox"
              checked={veoEnabled}
              onChange={(e) => setVeoEnabled(e.target.checked)}
              className="h-4 w-4 accent-zinc-900"
              disabled
            />
          </label>
        </div>
      )}

      {baseTab === "A" && (
        <div className="grid gap-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Actor A Setup
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={selectedSampleId}
                onChange={(e) => setSelectedSampleId(e.target.value)}
                className="rounded-full border border-zinc-200 bg-white/80 px-3 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
              >
                {PROMPT_SAMPLES.map((sample) => (
                  <option key={sample.id} value={sample.id}>
                    {sample.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleInsertSample}
                className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
              >
                Insert Sample
              </button>
              <button
                type="button"
                onClick={onOpenPromptHelper}
                className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
              >
                Prompt Helper
              </button>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Actor A Gender
            </label>
            <select
              value={actorAGender}
              onChange={(e) => setActorAGender(e.target.value as ActorGender)}
              className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
            >
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Base Prompt (Actor A)
            </label>
            <textarea
              value={basePromptA}
              onChange={(e) => setBasePromptA(e.target.value)}
              rows={2}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
              placeholder="1girl, eureka, (black t-shirt:1.2), ... <lora:...:1.0>"
            />
            <p className="text-[10px] text-zinc-500">
              Model tags like &lt;model:...&gt; are ignored. Use the SD Model selector
              instead.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Base Negative (Actor A)
            </label>
            <textarea
              value={baseNegativePromptA}
              onChange={(e) => setBaseNegativePromptA(e.target.value)}
              rows={2}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
              placeholder="verybadimagenegative_v1.3"
            />
          </div>
          {/* Advanced Settings Toggle */}
          <div className="border-t border-zinc-200 pt-4">
            <button
              type="button"
              onClick={() => setAdvancedOpen(!advancedOpen)}
              className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase hover:text-zinc-700"
            >
              <span className={`transition-transform ${advancedOpen ? "rotate-90" : ""}`}>▶</span>
              Advanced Settings (SD Parameters)
            </button>
            {advancedOpen && (
              <div className="mt-4 grid gap-3 md:grid-cols-5">
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Steps
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={80}
                    value={baseStepsA}
                    onChange={(e) => setBaseStepsA(Number(e.target.value))}
                    className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    CFG Scale
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    step={0.5}
                    value={baseCfgScaleA}
                    onChange={(e) => setBaseCfgScaleA(Number(e.target.value))}
                    className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Sampler
                  </label>
                  <select
                    value={baseSamplerA}
                    onChange={(e) => setBaseSamplerA(e.target.value)}
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
                    value={baseSeedA}
                    onChange={(e) => setBaseSeedA(Number(e.target.value))}
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
                    value={baseClipSkipA}
                    onChange={(e) => setBaseClipSkipA(Number(e.target.value))}
                    className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
