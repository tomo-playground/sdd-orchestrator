"use client";

import { useRouter } from "next/navigation";
import { Users } from "lucide-react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useCharacters } from "../../hooks/useCharacters";
import StageCharacterCard from "./StageCharacterCard";
import type { VoicePreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";

type Props = {
  audioPlayer: AudioPlayer;
  voicePresets: VoicePreset[];
};

export default function StageCharactersSection({ audioPlayer, voicePresets }: Props) {
  const router = useRouter();
  const selectedCharacterId = useStoryboardStore((s) => s.selectedCharacterId);
  const selectedCharacterBId = useStoryboardStore((s) => s.selectedCharacterBId);
  const { characters } = useCharacters();

  const charA = characters.find((c) => c.id === selectedCharacterId) ?? null;
  const charB = characters.find((c) => c.id === selectedCharacterBId) ?? null;
  const hasAny = charA || charB;

  const getVoicePreset = (id: number | null) =>
    id ? voicePresets.find((p) => p.id === id) ?? null : null;

  return (
    <section>
      <h3 className="mb-3 text-sm font-semibold text-zinc-800">Characters</h3>

      {!hasAny ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-200 py-8">
          <Users className="mb-2 h-7 w-7 text-zinc-300" />
          <p className="text-xs font-medium text-zinc-500">No characters selected</p>
          <p className="mt-0.5 text-[11px] text-zinc-400">
            Select characters in the Script tab to see them here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {charA && (
            <StageCharacterCard
              character={charA}
              role="A"
              voicePreset={getVoicePreset(charA.voice_preset_id)}
              audioPlayer={audioPlayer}
              onViewInLibrary={() => router.push(`/library?tab=characters&id=${charA.id}`)}
            />
          )}
          {charB && (
            <StageCharacterCard
              character={charB}
              role="B"
              voicePreset={getVoicePreset(charB.voice_preset_id)}
              audioPlayer={audioPlayer}
              onViewInLibrary={() => router.push(`/library?tab=characters&id=${charB.id}`)}
            />
          )}
        </div>
      )}
    </section>
  );
}
