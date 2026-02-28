"use client";

import { Mic } from "lucide-react";
import { useRenderStore } from "../../store/useRenderStore";
import { useUIStore } from "../../store/useUIStore";
import StageVoiceCard from "./StageVoiceCard";
import EmptyState from "../ui/EmptyState";
import type { VoicePreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";

type Props = {
  audioPlayer: AudioPlayer;
  voicePresets: VoicePreset[];
};

export default function StageVoiceSection({ audioPlayer, voicePresets }: Props) {
  const openGroupConfig = useUIStore((s) => s.openGroupConfig);
  const voicePresetId = useRenderStore((s) => s.voicePresetId);

  const selectedPreset = voicePresets.find((p) => p.id === voicePresetId) ?? null;

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800">음성</h3>
        <button
          onClick={openGroupConfig}
          className="text-[11px] font-medium text-blue-600 hover:text-blue-700"
        >
          시리즈 설정에서 변경
        </button>
      </div>

      {!selectedPreset ? (
        <EmptyState icon={Mic} title="시리즈 설정에서 나레이터 음성을 선택하세요" variant="inline" />
      ) : (
        <StageVoiceCard preset={selectedPreset} audioPlayer={audioPlayer} />
      )}
    </section>
  );
}
