"use client";

import { useRouter } from "next/navigation";
import { Mic } from "lucide-react";
import { useRenderStore } from "../../store/useRenderStore";
import StageVoiceCard from "./StageVoiceCard";
import type { VoicePreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";

type Props = {
  audioPlayer: AudioPlayer;
  voicePresets: VoicePreset[];
};

export default function StageVoiceSection({ audioPlayer, voicePresets }: Props) {
  const router = useRouter();
  const voicePresetId = useRenderStore((s) => s.voicePresetId);

  const selectedPreset = voicePresets.find((p) => p.id === voicePresetId) ?? null;

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800">Voice</h3>
        <button
          onClick={() => router.push("/library?tab=voices")}
          className="text-[11px] font-medium text-blue-600 hover:text-blue-700"
        >
          Change Preset
        </button>
      </div>

      {!selectedPreset ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-200 py-8">
          <Mic className="mb-2 h-7 w-7 text-zinc-300" />
          <p className="text-xs font-medium text-zinc-500">No voice preset selected</p>
          <p className="mt-0.5 text-[11px] text-zinc-400">
            Choose a voice preset in Library to preview here.
          </p>
        </div>
      ) : (
        <StageVoiceCard preset={selectedPreset} audioPlayer={audioPlayer} />
      )}
    </section>
  );
}
