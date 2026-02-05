"use client";

import type { ActorGender, Character } from "../../types";
import CharacterSelector from "./CharacterSelector";
import { cx, SECTION_CLASSES } from "../ui/variants";

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
  // Dialogue (Character B)
  structure: string;
  selectedCharacterBId: number | null;
  onSelectCharacterB: (charId: number | null) => void;
  basePromptB: string;
  setBasePromptB: (value: string) => void;
  baseNegativePromptB: string;
  setBaseNegativePromptB: (value: string) => void;
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
  structure,
  selectedCharacterBId,
  onSelectCharacterB,
  basePromptB,
  setBasePromptB,
  baseNegativePromptB,
  setBaseNegativePromptB,
}: PromptSetupPanelProps) {
  const isDialogue = structure.toLowerCase() === "dialogue";
  const sameCharacterWarning =
    isDialogue &&
    selectedCharacterId &&
    selectedCharacterBId &&
    selectedCharacterId === selectedCharacterBId;

  return (
    <section className={cx(SECTION_CLASSES, "grid gap-4")}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">
            {isDialogue ? "Characters" : "Character"}
          </h2>
          <p className="text-[10px] text-zinc-400">
            Identity and style prompts. Scene prompts handle action, camera, and background.
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
          label={isDialogue ? "Speaker A" : "Character"}
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
        {isDialogue && (
          <CharacterSelector
            label="Speaker B"
            characters={characters}
            selectedCharacterId={selectedCharacterBId}
            onSelect={onSelectCharacterB}
          />
        )}
      </div>
      {sameCharacterWarning && (
        <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-700">
          Speaker A and B must be different characters.
        </p>
      )}
      <div className="flex flex-col gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          {isDialogue ? "Base Prompt (A)" : "Base Prompt"}
        </label>
        <textarea
          value={basePromptA}
          onChange={(e) => setBasePromptA(e.target.value)}
          rows={2}
          className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
          placeholder="1girl, eureka, (black t-shirt:1.2), ... <lora:...:1.0>"
        />
        <p className="text-[10px] text-zinc-500">
          Model tags like &lt;model:...&gt; are ignored. Use the SD Model selector instead.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          {isDialogue ? "Negative Prompt (A)" : "Negative Prompt"}
        </label>
        <textarea
          value={baseNegativePromptA}
          onChange={(e) => setBaseNegativePromptA(e.target.value)}
          rows={2}
          className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
          placeholder="verybadimagenegative_v1.3"
        />
      </div>
      {isDialogue && (
        <>
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Base Prompt (B)
            </label>
            <textarea
              value={basePromptB}
              onChange={(e) => setBasePromptB(e.target.value)}
              rows={2}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
              placeholder="1boy, character_b tags..."
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Negative Prompt (B)
            </label>
            <textarea
              value={baseNegativePromptB}
              onChange={(e) => setBaseNegativePromptB(e.target.value)}
              rows={2}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
              placeholder="verybadimagenegative_v1.3"
            />
          </div>
        </>
      )}
    </section>
  );
}
