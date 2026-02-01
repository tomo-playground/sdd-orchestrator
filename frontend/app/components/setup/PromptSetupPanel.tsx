"use client";

import { useState } from "react";
import type { ActorGender, Character } from "../../types";
import { SAMPLERS, API_BASE } from "../../constants";

type PromptSetupPanelProps = {
  // Tab state
  baseTab: "global" | "A";
  setBaseTab: (value: "global" | "A") => void;
  // Global settings
  autoComposePrompt: boolean;
  setAutoComposePrompt: (value: boolean) => void;
  autoRewritePrompt: boolean;
  setAutoRewritePrompt: (value: boolean) => void;
  autoReplaceRiskyTags: boolean;
  setAutoReplaceRiskyTags: (value: boolean) => void;
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
  // Prompt helper
  onOpenPromptHelper: () => void;
  // Character selection
  characters: Character[];
  selectedCharacterId: number | null;
  onSelectCharacter: (charId: number | null) => void;
};

export default function PromptSetupPanel({
  baseTab,
  setBaseTab,
  autoComposePrompt,
  setAutoComposePrompt,
  autoRewritePrompt,
  setAutoRewritePrompt,
  autoReplaceRiskyTags,
  setAutoReplaceRiskyTags,
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
  onOpenPromptHelper,
  characters,
  selectedCharacterId,
  onSelectCharacter,
}: PromptSetupPanelProps) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);

  return (
    <>
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
                className={`rounded-full px-4 py-2 text-[10px] font-semibold tracking-[0.2em] uppercase transition ${active ? "bg-zinc-900 text-white" : "bg-white/80 text-zinc-600"
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
              <div>
                <div>Auto Replace Risky Tags</div>
                <div className="text-[10px] font-normal normal-case tracking-normal text-zinc-500 mt-1">
                  Automatically replace non-Danbooru tags (e.g., "medium shot" → "cowboy shot")
                </div>
              </div>
              <input
                type="checkbox"
                checked={autoReplaceRiskyTags}
                onChange={(e) => setAutoReplaceRiskyTags(e.target.checked)}
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
              <button
                type="button"
                onClick={onOpenPromptHelper}
                className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
              >
                Prompt Helper
              </button>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              {/* Character Preset */}
              <div className="flex flex-1 flex-col gap-1 min-w-[200px]">
                <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Character
                </label>
                <select
                  value={selectedCharacterId ?? ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    const charId = val ? parseInt(val, 10) : null;
                    onSelectCharacter(charId);
                    if (charId) {
                      const char = characters.find((c) => c.id === charId);
                      if (char?.gender) setActorAGender(char.gender);
                    }
                  }}
                  className={`rounded-2xl border px-3 py-2 text-sm outline-none focus:border-zinc-400 ${!selectedCharacterId
                      ? "border-amber-300 bg-amber-50/80 text-amber-700"
                      : "border-zinc-200 bg-white/80"
                    }`}
                >
                  <option value="" disabled>Select Character...</option>
                  {(() => {
                    const female = characters.filter((c) => c.gender === "female");
                    const male = characters.filter((c) => c.gender === "male");
                    const other = characters.filter((c) => c.gender !== "female" && c.gender !== "male");
                    return (
                      <>
                        {female.length > 0 && (
                          <optgroup label="Female">
                            {female.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                          </optgroup>
                        )}
                        {male.length > 0 && (
                          <optgroup label="Male">
                            {male.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                          </optgroup>
                        )}
                        {other.length > 0 && (
                          <optgroup label="Other">
                            {other.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                          </optgroup>
                        )}
                      </>
                    );
                  })()}
                </select>
              </div>
            </div>
            {/* Character Preview Row - only show when character selected */}
            {selectedCharacterId && (() => {
              const selectedChar = characters.find((c) => c.id === selectedCharacterId);
              if (!selectedChar) return null;
              return (
                <div className="flex items-center gap-4">
                  {selectedChar.preview_image_url ? (
                    <button
                      type="button"
                      onClick={() => setPreviewModalOpen(true)}
                      className="group relative"
                    >
                      <img
                        src={selectedChar.preview_image_url.startsWith('http') ? selectedChar.preview_image_url : `${API_BASE}${selectedChar.preview_image_url}`}
                        alt={selectedChar.name}
                        className="h-20 w-20 shrink-0 rounded-2xl border border-zinc-200 object-cover object-top transition group-hover:border-zinc-400"
                      />
                      <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/0 transition group-hover:bg-black/20">
                        <span className="text-white opacity-0 transition group-hover:opacity-100">🔍</span>
                      </div>
                    </button>
                  ) : (
                    <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-zinc-50 text-zinc-400">
                      <span className="text-2xl">?</span>
                    </div>
                  )}
                  <div className="flex flex-col gap-0.5">
                    <p className="text-sm font-medium text-zinc-700">{selectedChar.name}</p>
                    {selectedChar.description && (
                      <p className="text-xs text-zinc-500">{selectedChar.description}</p>
                    )}
                  </div>
                </div>
              );
            })()}
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
      {/* Preview Modal - rendered outside section to avoid stacking context issues */}
      {previewModalOpen && (() => {
        const selectedChar = characters.find((c) => c.id === selectedCharacterId);
        if (!selectedChar?.preview_image_url) return null;
        return (
          <div
            className="fixed inset-0 z-[var(--z-preview)] flex items-center justify-center bg-black/70 backdrop-blur-sm"
            onClick={() => setPreviewModalOpen(false)}
          >
            <div className="relative" onClick={(e) => e.stopPropagation()}>
              <img
                src={selectedChar.preview_image_url.startsWith('http') ? selectedChar.preview_image_url : `${API_BASE}${selectedChar.preview_image_url}`}
                alt={selectedChar.name}
                className="max-h-[80vh] max-w-[80vw] rounded-2xl border-2 border-white/20 shadow-2xl"
              />
              <button
                type="button"
                onClick={() => setPreviewModalOpen(false)}
                className="absolute -right-3 -top-3 flex h-8 w-8 items-center justify-center rounded-full bg-white text-zinc-600 shadow-lg hover:bg-zinc-100"
              >
                ✕
              </button>
              <p className="mt-3 text-center text-sm font-medium text-white">{selectedChar.name}</p>
            </div>
          </div>
        );
      })()}
    </>
  );
}
