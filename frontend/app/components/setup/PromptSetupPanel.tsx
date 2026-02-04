"use client";

import type { ActorGender, Character } from "../../types";
import CharacterSelector from "./CharacterSelector";

type PromptSetupPanelProps = {
  actorAGender?: ActorGender;
  setActorAGender: (value: ActorGender) => void;
  basePromptA: string;
  setBasePromptA: (value: string) => void;
  baseNegativePromptA: string;
  setBaseNegativePromptA: (value: string) => void;
  onOpenPromptHelper: () => void;
  characters: Character[];
  selectedCharacterId: number | null;
  onSelectCharacter: (charId: number | null) => void;
};

export default function PromptSetupPanel({
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
  return (
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
  );
}
