"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Users } from "lucide-react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useCharacters } from "../../hooks/useCharacters";
import { isMultiCharStructure } from "../../utils/structure";
import CharacterSelector from "../setup/CharacterSelector";
import EmptyState from "../ui/EmptyState";
import StageCastingCompareCard from "./StageCastingCompareCard";
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
  const basePromptA = useStoryboardStore((s) => s.basePromptA);
  const basePromptB = useStoryboardStore((s) => s.basePromptB);
  const setPlan = useStoryboardStore((s) => s.set);
  const casting = useStoryboardStore((s) => s.castingRecommendation);
  const { characters, getCharacterFull } = useCharacters();

  const isDialogue = isMultiCharStructure(structure);
  const recommendedIds = [casting?.character_a_id, casting?.character_b_id].filter(
    (id): id is number => id != null
  );

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

  const handleAcceptCasting = () => {
    if (!casting) return;
    if (casting.character_a_id != null) {
      const char = characters.find((c) => c.id === casting.character_a_id);
      setPlan({
        selectedCharacterId: casting.character_a_id,
        selectedCharacterName: char?.name ?? casting.character_a_name,
      });
      if (char?.gender) setPlan({ actorAGender: char.gender });
    }
    if (casting.character_b_id != null) {
      const name =
        characters.find((c) => c.id === casting.character_b_id)?.name ?? casting.character_b_name;
      setPlan({ selectedCharacterBId: casting.character_b_id, selectedCharacterBName: name });
    }
    setPlan({ castingRecommendation: null, isDirty: true });
  };

  const handleDismissCasting = () => {
    setPlan({ castingRecommendation: null, isDirty: true });
  };

  return (
    <section>
      <h3 className="mb-3 text-sm font-semibold text-zinc-800">캐릭터</h3>

      {/* Casting comparison card */}
      {casting && (
        <StageCastingCompareCard
          casting={casting}
          currentChar={charA}
          onAccept={handleAcceptCasting}
          onDismiss={handleDismissCasting}
        />
      )}

      {/* Character Selectors */}
      <div className="mb-4 flex flex-wrap gap-3">
        <CharacterSelector
          label={isDialogue ? "화자 A" : "캐릭터"}
          characters={characters}
          selectedCharacterId={selectedCharacterId}
          onSelect={(charId) => {
            const char = characters.find((c) => c.id === charId);
            setPlan({ selectedCharacterId: charId, selectedCharacterName: char?.name ?? null });
            if (char?.gender) setPlan({ actorAGender: char.gender });
          }}
          recommendedCharacterIds={recommendedIds}
        />
        {isDialogue && (
          <CharacterSelector
            label="화자 B"
            characters={characters}
            selectedCharacterId={selectedCharacterBId}
            onSelect={(charId) => {
              const name = characters.find((c) => c.id === charId)?.name ?? null;
              setPlan({ selectedCharacterBId: charId, selectedCharacterBName: name });
            }}
            recommendedCharacterIds={recommendedIds}
          />
        )}
      </div>

      {sameWarning && (
        <div className="mb-3 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          화자 A와 B가 같은 캐릭터입니다.
        </div>
      )}

      {/* Character Cards */}
      {!hasAny ? (
        <EmptyState icon={Users} title="위에서 캐릭터를 선택하세요" variant="inline" />
      ) : (
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
          {charA && (
            <StageCharacterCard
              key={charA.id}
              character={charA}
              characterFull={charAFull}
              role="A"
              basePrompt={basePromptA}
              voicePreset={getVoicePreset(charA.voice_preset_id)}
              audioPlayer={audioPlayer}
              onViewInLibrary={() => router.push(`/library/characters/${charA.id}`)}
            />
          )}
          {charB && (
            <StageCharacterCard
              key={charB.id}
              character={charB}
              characterFull={charBFull}
              role="B"
              basePrompt={basePromptB}
              voicePreset={getVoicePreset(charB.voice_preset_id)}
              audioPlayer={audioPlayer}
              onViewInLibrary={() => router.push(`/library/characters/${charB.id}`)}
            />
          )}
        </div>
      )}
    </section>
  );
}
