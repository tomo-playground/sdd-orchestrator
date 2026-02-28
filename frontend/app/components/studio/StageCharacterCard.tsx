"use client";

import { ExternalLink, Mic, User } from "lucide-react";
import type { Character, CharacterFull, VoicePreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";
import InfoTooltip from "../ui/InfoTooltip";

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
    <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
      {/* Preview image */}
      <div className="relative aspect-square bg-zinc-100">
        {character.preview_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={character.preview_image_url}
            alt={character.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <User className="h-10 w-10 text-zinc-300" />
          </div>
        )}
        <span className="absolute top-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-semibold text-white">
          {role}
        </span>
      </div>

      {/* Info */}
      <div className="p-3">
        <h4 className="mb-0.5 text-sm font-semibold text-zinc-900">{character.name}</h4>
        <div className="mb-2 flex flex-wrap gap-1">
          {character.gender && (
            <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-600">
              {character.gender}
            </span>
          )}
          {tagCount > 0 && (
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-500">
              {tagCount} tags
            </span>
          )}
        </div>

        {/* Voice preset */}
        {voicePreset ? (
          <div className="mb-2 flex items-center gap-2 rounded-lg bg-violet-50/50 px-2.5 py-1.5">
            <Mic className="h-3.5 w-3.5 shrink-0 text-violet-500" />
            <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-violet-700">
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
          <p className="mb-2 flex items-center gap-1.5 text-[11px] text-zinc-400">
            <Mic className="h-3 w-3" />
            No voice assigned
          </p>
        )}

        {/* Style & LoRA Dependencies */}
        {(characterFull?.style_profile_name || (characterFull?.loras?.length ?? 0) > 0) && (
          <div className="mb-2 space-y-1 rounded-lg bg-indigo-50/50 px-2.5 py-2">
            {characterFull?.style_profile_name && (
              <p className="text-[11px] font-semibold text-indigo-700">
                Style: {characterFull.style_profile_name}
              </p>
            )}
            {characterFull?.loras?.map((lora, i) => (
              <div
                key={`${lora.id}-${i}`}
                className="flex items-center gap-1.5 text-[11px] text-indigo-600"
              >
                <span className="inline-flex items-center gap-0.5 text-indigo-400">
                  LoRA <InfoTooltip term="lora" position="right" />
                </span>
                <span className="min-w-0 flex-1 truncate font-medium">
                  {lora.display_name || lora.name}
                </span>
                <span className="shrink-0 text-indigo-400">w:{Number(lora.weight.toFixed(2))}</span>
              </div>
            ))}
          </div>
        )}

        {/* Base Prompt */}
        {basePrompt && (
          <div className="mb-2 rounded-lg bg-zinc-50 px-2.5 py-2">
            <p className="mb-0.5 text-[11px] font-semibold text-zinc-400">Base Prompt</p>
            <p
              className="line-clamp-2 text-[11px] leading-relaxed text-zinc-500"
              title={basePrompt}
            >
              {basePrompt}
            </p>
          </div>
        )}

        <button
          onClick={onViewInLibrary}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 transition hover:bg-zinc-50"
        >
          <ExternalLink className="h-3 w-3" />
          View in Library
        </button>
      </div>
    </div>
  );
}
