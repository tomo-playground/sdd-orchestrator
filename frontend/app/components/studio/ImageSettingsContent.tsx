"use client";

import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";
import { useCharacters } from "../../hooks/useCharacters";
import { useCharacterAutoLoad } from "../../hooks/useCharacterAutoLoad";
import PromptSetupPanel from "../setup/PromptSetupPanel";
import StyleProfileSelector from "../setup/StyleProfileSelector";

export default function ImageSettingsContent() {
  const actorAGender = useStoryboardStore((s) => s.actorAGender);
  const selectedCharacterId = useStoryboardStore((s) => s.selectedCharacterId);
  const selectedCharacterBId = useStoryboardStore((s) => s.selectedCharacterBId);
  const basePromptA = useStoryboardStore((s) => s.basePromptA);
  const baseNegativePromptA = useStoryboardStore((s) => s.baseNegativePromptA);
  const basePromptB = useStoryboardStore((s) => s.basePromptB);
  const baseNegativePromptB = useStoryboardStore((s) => s.baseNegativePromptB);
  const autoRewritePrompt = useStoryboardStore((s) => s.autoRewritePrompt);
  const autoReplaceRiskyTags = useStoryboardStore((s) => s.autoReplaceRiskyTags);
  const hiResEnabled = useStoryboardStore((s) => s.hiResEnabled);
  const veoEnabled = useStoryboardStore((s) => s.veoEnabled);
  const structure = useStoryboardStore((s) => s.structure);
  const setPlan = useStoryboardStore((s) => s.set);

  const currentStyleProfile = useRenderStore((s) => s.currentStyleProfile);
  const { characters } = useCharacters();

  const TOGGLES = [
    { key: "autoRewritePrompt" as const, label: "Auto Rewrite", value: autoRewritePrompt },
    { key: "autoReplaceRiskyTags" as const, label: "Safe Tags", value: autoReplaceRiskyTags },
    { key: "hiResEnabled" as const, label: "Hi-Res", value: hiResEnabled },
    { key: "veoEnabled" as const, label: "Veo", value: veoEnabled },
  ];

  return (
    <div className="space-y-4">
      <StyleProfileSelector
        currentProfileName={currentStyleProfile?.display_name ?? currentStyleProfile?.name ?? null}
      />

      <PromptSetupPanel
        actorAGender={actorAGender}
        setActorAGender={(v) => setPlan({ actorAGender: v })}
        basePromptA={basePromptA}
        setBasePromptA={(v: string) => setPlan({ basePromptA: v })}
        baseNegativePromptA={baseNegativePromptA}
        setBaseNegativePromptA={(v: string) => setPlan({ baseNegativePromptA: v })}
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
        <label className="mb-2 block text-[12px] font-medium tracking-wider text-zinc-400 uppercase">
          Options
        </label>
        <div className="flex flex-wrap gap-1.5">
          {TOGGLES.map((t) => (
            <label
              key={t.key}
              className={`flex cursor-pointer items-center gap-1 rounded-full border px-2.5 py-1 text-[12px] font-medium transition ${t.value
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
  );
}
