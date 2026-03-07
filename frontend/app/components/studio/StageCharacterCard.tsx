"use client";

import { ExternalLink, Mic, User } from "lucide-react";
import type { Character, CharacterFull, VoicePreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";

type Props = {
  character: Character;
  characterFull: CharacterFull | null;
  role: "A" | "B";
  basePrompt: string;
  voicePreset: VoicePreset | null;
  audioPlayer: AudioPlayer;
  onViewInLibrary: () => void;
};

export default function StageCharacterCard({
  character,
  characterFull,
  role,
  basePrompt,
  voicePreset,
  audioPlayer,
  onViewInLibrary,
}: Props) {
  const tagCount = (character.tags?.length ?? 0) + (character.loras?.length ?? 0);
  const { playingUrl, play } = audioPlayer;
  const isMe = voicePreset?.audio_url ? playingUrl === voicePreset.audio_url : false;

  return (
    <div className="flex gap-3 overflow-hidden rounded-xl border border-zinc-200 bg-white p-3 shadow-sm">
      {/* Preview image — compact thumbnail */}
      <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-zinc-100">
        {character.reference_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={character.reference_image_url}
            alt={character.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <User className="h-6 w-6 text-zinc-300" />
          </div>
        )}
        <span className="absolute top-1 left-1 rounded-full bg-black/60 px-1.5 py-px text-[11px] font-semibold text-white">
          {role}
        </span>
      </div>

      {/* Info — horizontal compact */}
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-2">
          <h4 className="truncate text-sm font-semibold text-zinc-900">{character.name}</h4>
          {character.gender && (
            <span className="shrink-0 rounded-full bg-violet-50 px-1.5 py-px text-[11px] font-medium text-violet-600">
              {character.gender}
            </span>
          )}
          {tagCount > 0 && (
            <span className="shrink-0 rounded-full bg-zinc-100 px-1.5 py-px text-[11px] text-zinc-500">
              {tagCount}개 태그
            </span>
          )}
        </div>

        {/* Voice preset */}
        {voicePreset ? (
          <div className="mb-1.5 flex items-center gap-1.5">
            <Mic className="h-3 w-3 shrink-0 text-violet-500" />
            <span className="min-w-0 truncate text-[11px] font-medium text-violet-700">
              {voicePreset.name}
            </span>
            {voicePreset.audio_url && (
              <button
                onClick={() => play(voicePreset.audio_url!)}
                className="shrink-0 rounded border border-violet-200 bg-white px-1.5 py-0.5 text-[11px] text-violet-600 transition hover:bg-violet-50"
                title={isMe ? "Stop" : "Preview voice"}
              >
                {isMe ? "\u25A0" : "\u25B6"}
              </button>
            )}
          </div>
        ) : (
          <p className="mb-1.5 flex items-center gap-1 text-[11px] text-zinc-400">
            <Mic className="h-3 w-3" />
            음성 미지정
          </p>
        )}

        {/* Group & LoRA — inline */}
        {(characterFull?.group_name || (characterFull?.loras?.length ?? 0) > 0) && (
          <div className="mb-1.5 flex flex-wrap items-center gap-1 text-[11px]">
            {characterFull?.group_name && (
              <span className="rounded bg-indigo-50 px-1.5 py-px font-medium text-indigo-700">
                {characterFull.group_name}
              </span>
            )}
            {characterFull?.loras?.map((lora, i) => (
              <span
                key={`${lora.id}-${i}`}
                className="rounded bg-indigo-50 px-1.5 py-px text-indigo-600"
              >
                {lora.display_name || lora.name} w:{Number(lora.weight.toFixed(2))}
              </span>
            ))}
          </div>
        )}

        {/* Base Prompt — single line */}
        {basePrompt && (
          <p className="mb-1.5 truncate text-[11px] text-zinc-400" title={basePrompt}>
            {basePrompt}
          </p>
        )}

        <button
          onClick={onViewInLibrary}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-zinc-500 transition hover:text-zinc-700"
        >
          <ExternalLink className="h-3 w-3" />
          라이브러리에서 보기
        </button>
      </div>
    </div>
  );
}
