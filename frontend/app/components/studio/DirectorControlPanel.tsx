"use client";

import { useShallow } from "zustand/react/shallow";
import { Mic, Music, Loader2 } from "lucide-react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";
import { usePresets, type EmotionPreset, type BgmMoodPreset } from "../../hooks/usePresets";

type Props = {
  onApplyAll?: () => void;
  showToast?: (msg: string, type: "success" | "error" | "warning") => void;
  isApplying?: boolean;
};

// ── Component ────────────────────────────────────────────
export default function DirectorControlPanel({ onApplyAll, showToast, isApplying }: Props) {
  const { emotionPresets, bgmMoodPresets, isLoading: presetsLoading } = usePresets();

  const { scenes, selectedEmotionPreset, setGlobalEmotion } = useStoryboardStore(
    useShallow((s) => ({
      scenes: s.scenes,
      selectedEmotionPreset: s.selectedEmotionPreset,
      setGlobalEmotion: s.setGlobalEmotion,
    }))
  );

  const selectedBgmPreset = useRenderStore((s) => s.selectedBgmPreset);

  const setRender = useRenderStore.getState().set;
  const sceneCount = scenes.length;

  const handleEmotionClick = (preset: EmotionPreset) => {
    if (selectedEmotionPreset === preset.id) return;
    setGlobalEmotion(preset.emotion);
    showToast?.(`음성 톤: ${preset.label} 적용`, "success");
  };

  const handleBgmClick = (preset: BgmMoodPreset) => {
    if (selectedBgmPreset === preset.id) return;
    setRender({
      bgmMood: preset.mood,
      bgmPrompt: preset.prompt,
      bgmMode: "auto",
      selectedBgmPreset: preset.id,
    });
    showToast?.(`BGM: ${preset.label} 적용`, "success");
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      {/* Voice Tone */}
      <div className="mb-3">
        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-zinc-500">
          <Mic className="h-3.5 w-3.5" />
          음성 톤
        </div>
        <div className="flex flex-wrap gap-2">
          {presetsLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-7 w-14 animate-pulse rounded-lg bg-zinc-100" />
              ))
            : emotionPresets.map((p) => (
                <button
                  key={p.id}
                  data-preset-id={`emotion-${p.id}`}
                  onClick={() => handleEmotionClick(p)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    selectedEmotionPreset === p.id
                      ? "bg-zinc-900 text-white ring-2 ring-zinc-900/20"
                      : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                  }`}
                >
                  {p.label}
                </button>
              ))}
        </div>
      </div>

      {/* BGM Mood */}
      <div className="mb-3">
        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-zinc-500">
          <Music className="h-3.5 w-3.5" />
          BGM 분위기
        </div>
        <div className="flex flex-wrap gap-2">
          {presetsLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-7 w-14 animate-pulse rounded-lg bg-zinc-100" />
              ))
            : bgmMoodPresets.map((p) => (
                <button
                  key={p.id}
                  data-preset-id={`bgm-${p.id}`}
                  onClick={() => handleBgmClick(p)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    selectedBgmPreset === p.id
                      ? "bg-zinc-900 text-white ring-2 ring-zinc-900/20"
                      : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                  }`}
                >
                  {p.label}
                </button>
              ))}
        </div>
      </div>

      {/* Apply All — TTS 재생성 */}
      {sceneCount > 0 && (
        <button
          onClick={onApplyAll}
          disabled={isApplying}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isApplying ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              재생성 중...
            </>
          ) : (
            `TTS 전체 재생성 (${sceneCount}씬)`
          )}
        </button>
      )}
    </div>
  );
}
