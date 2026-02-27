"use client";

import { Loader2, Music } from "lucide-react";
import type { MusicPreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";

type BaseProps = {
  volume: number;
  audioPlayer: AudioPlayer;
};

type ManualProps = BaseProps & {
  mode: "manual";
  preset: MusicPreset;
};

type AutoProps = BaseProps & {
  mode: "auto";
  bgmPrompt: string;
  bgmMood: string;
  previewUrl: string | null;
  isGenerating: boolean;
  onGeneratePreview: () => void;
};

type Props = ManualProps | AutoProps;

export default function StageBgmCard(props: Props) {
  const { playingUrl, play } = props.audioPlayer;

  const audioUrl = props.mode === "manual" ? props.preset.audio_url : props.previewUrl;
  const isMe = audioUrl ? playingUrl === audioUrl : false;

  return (
    <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white p-3 shadow-sm">
      {/* Icon */}
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-50">
        <Music className="h-5 w-5 text-amber-500" />
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        {props.mode === "manual" ? (
          <>
            <p className="text-sm font-semibold text-zinc-900">{props.preset.name}</p>
            {props.preset.description && (
              <p className="mt-0.5 truncate text-[11px] text-zinc-400">
                {props.preset.description}
              </p>
            )}
          </>
        ) : (
          <>
            <p className="text-sm font-semibold text-zinc-900">AI Generated</p>
            {props.bgmPrompt && (
              <p className="mt-0.5 truncate text-[11px] text-zinc-400">{props.bgmPrompt}</p>
            )}
          </>
        )}
        <div className="mt-1 flex flex-wrap gap-1">
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
              props.mode === "manual" ? "bg-zinc-100 text-zinc-500" : "bg-amber-50 text-amber-600"
            }`}
          >
            {props.mode === "manual" ? "Manual" : "Auto"}
          </span>
          {props.mode === "auto" && props.bgmMood && (
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-500">
              {props.bgmMood}
            </span>
          )}
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-500">
            Vol {Math.round(props.volume * 100)}%
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex shrink-0 items-center gap-1.5">
        {/* Generate Preview (auto mode only, no preview yet) */}
        {props.mode === "auto" && !props.previewUrl && (
          <button
            onClick={props.onGeneratePreview}
            disabled={props.isGenerating}
            className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[11px] font-medium text-amber-700 transition hover:bg-amber-100 disabled:opacity-50"
            title="Generate 10s BGM preview"
          >
            {props.isGenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Preview"}
          </button>
        )}

        {/* Play/Stop button */}
        {audioUrl && (
          <button
            onClick={() => play(audioUrl)}
            className="rounded-lg border border-zinc-200 bg-white px-2.5 py-2 text-xs text-zinc-600 transition hover:bg-zinc-50"
            title={isMe ? "Stop" : "Preview"}
          >
            {isMe ? "\u25A0" : "\u25B6"}
          </button>
        )}
      </div>
    </div>
  );
}
