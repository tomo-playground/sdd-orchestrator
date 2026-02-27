"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Music } from "lucide-react";
import axios from "axios";
import { useRenderStore } from "../../store/useRenderStore";
import { useUIStore } from "../../store/useUIStore";
import { API_BASE } from "../../constants";
import { getErrorMsg } from "../../utils/error";
import StageBgmCard from "./StageBgmCard";
import type { MusicPreset } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";

type Props = {
  audioPlayer: AudioPlayer;
};

export default function StageBgmSection({ audioPlayer }: Props) {
  const router = useRouter();
  const showToast = useUIStore((s) => s.showToast);
  const bgmMode = useRenderStore((s) => s.bgmMode);
  const musicPresetId = useRenderStore((s) => s.musicPresetId);
  const bgmPrompt = useRenderStore((s) => s.bgmPrompt);
  const bgmMood = useRenderStore((s) => s.bgmMood);
  const bgmVolume = useRenderStore((s) => s.bgmVolume);
  const autoPreviewUrl = useRenderStore((s) => s.bgmPreviewUrl);

  const [presets, setPresets] = useState<MusicPreset[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    if (bgmMode !== "manual") return;
    axios
      .get<MusicPreset[]>(`${API_BASE}/music-presets`)
      .then((r) => setPresets(r.data))
      .catch(() => {});
  }, [bgmMode]);

  // Reset preview when prompt changes
  useEffect(() => {
    useRenderStore.getState().set({ bgmPreviewUrl: null });
  }, [bgmPrompt]);

  const handleGeneratePreview = useCallback(async () => {
    if (!bgmPrompt.trim()) return;
    setIsGenerating(true);
    try {
      const res = await axios.post<{ audio_url: string; temp_asset_id: number; seed: number }>(
        `${API_BASE}/music-presets/preview`,
        { prompt: bgmPrompt, duration: 10.0, seed: -1 },
      );
      useRenderStore.getState().set({ bgmPreviewUrl: res.data.audio_url });
    } catch (error) {
      showToast(getErrorMsg(error, "BGM preview generation failed"), "error");
    } finally {
      setIsGenerating(false);
    }
  }, [bgmPrompt, showToast]);

  const selectedPreset = presets.find((p) => p.id === musicPresetId) ?? null;
  const isEmpty = bgmMode === "manual" ? !selectedPreset : !bgmPrompt;

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800">BGM</h3>
        <button
          onClick={() => router.push("/library?tab=music")}
          className="text-[11px] font-medium text-blue-600 hover:text-blue-700"
        >
          Change
        </button>
      </div>

      {isEmpty ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-200 py-8">
          <Music className="mb-2 h-7 w-7 text-zinc-300" />
          <p className="text-xs font-medium text-zinc-500">No BGM configured</p>
          <p className="mt-0.5 text-[11px] text-zinc-400">
            Set up background music in Library to preview here.
          </p>
        </div>
      ) : bgmMode === "manual" && selectedPreset ? (
        <StageBgmCard
          mode="manual"
          preset={selectedPreset}
          volume={bgmVolume}
          audioPlayer={audioPlayer}
        />
      ) : bgmMode === "auto" ? (
        <StageBgmCard
          mode="auto"
          bgmPrompt={bgmPrompt}
          bgmMood={bgmMood}
          volume={bgmVolume}
          audioPlayer={audioPlayer}
          previewUrl={autoPreviewUrl}
          isGenerating={isGenerating}
          onGeneratePreview={handleGeneratePreview}
        />
      ) : null}
    </section>
  );
}
