"use client";

import { useState } from "react";
import { useStudioStore } from "../../store/useStudioStore";
import { useCharacters } from "../../hooks/useCharacters";
import { useCharacterAutoLoad } from "../../hooks/useCharacterAutoLoad";
import PromptSetupPanel from "../setup/PromptSetupPanel";
import StyleProfileSelector from "../setup/StyleProfileSelector";

export default function ImageSettingsSection() {
  const [isExpanded, setIsExpanded] = useState(false);

  // Character auto-load (extracted from PlanTab)
  useCharacterAutoLoad();

  const {
    actorAGender,
    selectedCharacterId,
    selectedCharacterBId,
    basePromptA,
    baseNegativePromptA,
    basePromptB,
    baseNegativePromptB,
    autoComposePrompt,
    autoRewritePrompt,
    autoReplaceRiskyTags,
    hiResEnabled,
    veoEnabled,
    structure,
    setPlan,
  } = useStudioStore();

  const setMeta = useStudioStore((s) => s.setMeta);
  const currentStyleProfile = useStudioStore((s) => s.currentStyleProfile);
  const { characters } = useCharacters();

  const TOGGLES = [
    { key: "autoComposePrompt" as const, label: "Auto Compose", value: autoComposePrompt },
    { key: "autoRewritePrompt" as const, label: "Auto Rewrite", value: autoRewritePrompt },
    { key: "autoReplaceRiskyTags" as const, label: "Safe Tags", value: autoReplaceRiskyTags },
    { key: "hiResEnabled" as const, label: "Hi-Res", value: hiResEnabled },
    { key: "veoEnabled" as const, label: "Veo", value: veoEnabled },
  ];

  return (
    <section className="rounded-xl border border-zinc-200 bg-white">
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between px-5 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-800">Image Settings</span>
          {currentStyleProfile && (
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-500">
              {currentStyleProfile.display_name ?? currentStyleProfile.name}
            </span>
          )}
        </div>
        <svg
          className={`h-4 w-4 text-zinc-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Collapsible Content */}
      {isExpanded && (
        <div className="space-y-5 border-t border-zinc-100 px-5 py-4">
          <StyleProfileSelector
            currentProfileName={
              currentStyleProfile?.display_name ?? currentStyleProfile?.name ?? null
            }
          />

          <PromptSetupPanel
            actorAGender={actorAGender}
            setActorAGender={(v) => setPlan({ actorAGender: v })}
            basePromptA={basePromptA}
            setBasePromptA={(v: string) => setPlan({ basePromptA: v })}
            baseNegativePromptA={baseNegativePromptA}
            setBaseNegativePromptA={(v: string) => setPlan({ baseNegativePromptA: v })}
            onOpenPromptHelper={() => setMeta({ isHelperOpen: true })}
            characters={characters}
            selectedCharacterId={selectedCharacterId}
            onSelectCharacter={(id) => {
              const name = characters.find((c) => c.id === id)?.name ?? null;
              setPlan({ selectedCharacterId: id, selectedCharacterName: name });
            }}
            structure={structure}
            selectedCharacterBId={selectedCharacterBId}
            onSelectCharacterB={(id) => setPlan({ selectedCharacterBId: id })}
            basePromptB={basePromptB}
            setBasePromptB={(v: string) => setPlan({ basePromptB: v })}
            baseNegativePromptB={baseNegativePromptB}
            setBaseNegativePromptB={(v: string) => setPlan({ baseNegativePromptB: v })}
          />

          {/* Options Toggles */}
          <div>
            <label className="mb-1.5 block text-[10px] font-semibold tracking-wider text-zinc-500 uppercase">
              Options
            </label>
            <div className="flex flex-wrap gap-1.5">
              {TOGGLES.map((t) => (
                <label
                  key={t.key}
                  className={`flex cursor-pointer items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-medium transition ${
                    t.value
                      ? "border-zinc-900 bg-zinc-900 text-white"
                      : "border-zinc-200 bg-white text-zinc-500 hover:border-zinc-300"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={t.value}
                    onChange={(e) => setPlan({ [t.key]: e.target.checked })}
                    className="sr-only"
                  />
                  {t.label}
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
