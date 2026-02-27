"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Users } from "lucide-react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useCharacters } from "../../hooks/useCharacters";
import { isMultiCharStructure } from "../../utils/structure";
import CharacterSelector from "../setup/CharacterSelector";
import StageCharacterCard from "./StageCharacterCard";
import type { CharacterFull, VoicePreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";

type FetchedChar = { id: number; data: CharacterFull | null };

function useCharacterFull(
  charId: number | null | undefined,
  getCharacterFull: (id: number) => Promise<CharacterFull | null>
): CharacterFull | null {
  const [fetched, setFetched] = useState<FetchedChar | null>(null);

  useEffect(() => {
    if (!charId) return;
    let stale = false;
    getCharacterFull(charId)
      .then((d) => {
        if (!stale) setFetched({ id: charId, data: d });
      })
      .catch(() => {});
    return () => {
      stale = true;
    };
  }, [charId, getCharacterFull]);

  if (!charId || fetched?.id !== charId) return null;
  return fetched.data;
}

type Props = {
  audioPlayer: AudioPlayer;
  voicePresets: VoicePreset[];
};

export default function StageCharactersSection({ audioPlayer, voicePresets }: Props) {
  const router = useRouter();
  const selectedCharacterId = useStoryboardStore((s) => s.selectedCharacterId);
  const selectedCharacterBId = useStoryboardStore((s) => s.selectedCharacterBId);
  const structure = useStoryboardStore((s) => s.structure);
  const setPlan = useStoryboardStore((s) => s.set);
  const { characters, getCharacterFull } = useCharacters();

  const isDialogue = isMultiCharStructure(structure);

  const charA = characters.find((c) => c.id === selectedCharacterId) ?? null;
  const charB = characters.find((c) => c.id === selectedCharacterBId) ?? null;
  const hasAny = charA || charB;
  const sameWarning =
    isDialogue &&
    selectedCharacterId != null &&
    selectedCharacterBId != null &&
    selectedCharacterId === selectedCharacterBId;

  const charAFull = useCharacterFull(charA?.id, getCharacterFull);
  const charBFull = useCharacterFull(charB?.id, getCharacterFull);

  const getVoicePreset = (id: number | null) =>
    id ? (voicePresets.find((p) => p.id === id) ?? null) : null;

  return (
    <section>
      <h3 className="mb-3 text-sm font-semibold text-zinc-800">Characters</h3>

      {/* Character Selectors */}
      <div className="mb-4 flex flex-wrap gap-3">
        <CharacterSelector
          label={isDialogue ? "Speaker A" : "Character"}
          characters={characters}
          selectedCharacterId={selectedCharacterId}
          onSelect={(charId) => {
            const char = characters.find((c) => c.id === charId);
            setPlan({ selectedCharacterId: charId, selectedCharacterName: char?.name ?? null });
            if (char?.gender) setPlan({ actorAGender: char.gender });
          }}
        />
        {isDialogue && (
          <CharacterSelector
            label="Speaker B"
            characters={characters}
            selectedCharacterId={selectedCharacterBId}
            onSelect={(charId) => {
              const name = characters.find((c) => c.id === charId)?.name ?? null;
              setPlan({ selectedCharacterBId: charId, selectedCharacterBName: name });
            }}
          />
        )}
      </div>

      {sameWarning && (
        <div className="mb-3 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          Speaker A and B are the same character.
        </div>
      )}

      {/* Character Cards */}
      {!hasAny ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-200 py-8">
          <Users className="mb-2 h-7 w-7 text-zinc-300" />
          <p className="text-xs font-medium text-zinc-500">No characters selected</p>
          <p className="mt-0.5 text-[11px] text-zinc-400">
            Select a character above to see preview
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {charA && (
            <StageCharacterCard
              key={charA.id}
              character={charA}
              characterFull={charAFull}
              role="A"
              voicePreset={getVoicePreset(charA.voice_preset_id)}
              audioPlayer={audioPlayer}
              onViewInLibrary={() => router.push(`/characters/${charA.id}`)}
            />
          )}
          {charB && (
            <StageCharacterCard
              key={charB.id}
              character={charB}
              characterFull={charBFull}
              role="B"
              voicePreset={getVoicePreset(charB.voice_preset_id)}
              audioPlayer={audioPlayer}
              onViewInLibrary={() => router.push(`/characters/${charB.id}`)}
            />
          )}
        </div>
      )}
    </section>
  );
}
