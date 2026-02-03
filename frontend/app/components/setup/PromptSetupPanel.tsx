"use client";

import { useState } from "react";
import type { ActorGender, Character } from "../../types";
import CharacterSelector from "./CharacterSelector";

type PromptSetupPanelProps = {
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
  // Prompt helper
  onOpenPromptHelper: () => void;
  // Character selection
  characters: Character[];
  selectedCharacterId: number | null;
  onSelectCharacter: (charId: number | null) => void;
};

export default function PromptSetupPanel({
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
  actorAGender: _actorAGender, // eslint-disable-line @typescript-eslint/no-unused-vars
  setActorAGender,
  basePromptA,
  setBasePromptA,
  baseNegativePromptA,
  setBaseNegativePromptA,
  onOpenPromptHelper,
  characters,
  selectedCharacterId,
  onSelectCharacter,
}: PromptSetupPanelProps) {
  const [isGlobalOpen, setIsGlobalOpen] = useState(false);

  return (
    <>
      {/* Global Settings (Collapsible) */}
      <section className="rounded-3xl border border-white/60 bg-white/70 shadow-xl shadow-slate-200/40 backdrop-blur overflow-hidden">
        <button
          type="button"
          onClick={() => setIsGlobalOpen((v) => !v)}
          className="flex w-full items-center justify-between px-6 py-4"
        >
          <h2 className="text-lg font-semibold text-zinc-900">Global</h2>
          <svg
            className={`h-4 w-4 text-zinc-400 transition-transform ${isGlobalOpen ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {isGlobalOpen && (
          <div className="grid gap-2 px-6 pb-5">
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
                  Automatically replace non-Danbooru tags (e.g., &quot;medium shot&quot; → &quot;cowboy shot&quot;)
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
      </section>

      {/* Actor A Settings */}
      <section className="grid gap-4 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-zinc-900">Actor A</h2>
            <p className="text-[10px] text-zinc-400">
              Base Prompt is identity/style. Scene prompts handle action, camera, and background.
            </p>
          </div>
          <button
            type="button"
            onClick={onOpenPromptHelper}
            className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
          >
            Prompt Helper
          </button>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <CharacterSelector
            characters={characters}
            selectedCharacterId={selectedCharacterId}
            onSelect={(charId) => {
              onSelectCharacter(charId);
              if (charId) {
                const char = characters.find((c) => c.id === charId);
                if (char?.gender) setActorAGender(char.gender);
              }
            }}
          />
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
      </section>
    </>
  );
}
