"use client";

import { useState } from "react";
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
  const structureLower = structure.toLowerCase();
  const isDialogue = structureLower === "dialogue" || structureLower === "narrated dialogue";
  const sameCharacterWarning =
    isDialogue &&
    selectedCharacterId &&
    selectedCharacterBId &&
    selectedCharacterId === selectedCharacterBId;

  const [promptOpen, setPromptOpen] = useState(false);
  const hasPrompt = !!(basePromptA || baseNegativePromptA || basePromptB || baseNegativePromptB);

  return (
    <section className={cx(SECTION_CLASSES, "grid gap-4")}>
      <h2 className="text-lg font-semibold text-zinc-900">
        {isDialogue ? "Characters" : "Character"}
      </h2>
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

      {/* Collapsible prompt section */}
      <button
        type="button"
        onClick={() => setPromptOpen((v) => !v)}
        className="flex items-center gap-2 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase transition hover:text-zinc-600"
      >
        <svg
          className={cx("h-3 w-3 transition-transform", promptOpen && "rotate-90")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        Prompts
        {hasPrompt && !promptOpen && <span className="ml-1 h-1.5 w-1.5 rounded-full bg-zinc-400" />}
      </button>

      {promptOpen && (
        <div className="grid gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              {isDialogue ? "Base Prompt (A)" : "Base Prompt"}
            </label>
            <textarea
              value={basePromptA}
              onChange={(e) => setBasePromptA(e.target.value)}
              rows={2}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
              placeholder="1girl, eureka, (black t-shirt:1.2), ... <lora:...:1.0>"
            />
            <p className="text-[12px] text-zinc-500">
              Model tags like &lt;model:...&gt; are ignored. Use the SD Model selector instead.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
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
                <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
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
                <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
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
          <button
            type="button"
            onClick={onOpenPromptHelper}
            className="w-fit rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[12px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
          >
            Prompt Helper
          </button>
        </div>
      )}
    </section>
  );
}
