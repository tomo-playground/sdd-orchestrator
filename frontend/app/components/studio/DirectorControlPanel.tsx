"use client";

import { useShallow } from "zustand/react/shallow";
import { Mic, Music, Loader2 } from "lucide-react";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { useRenderStore } from "../../store/useRenderStore";

// ── Presets ──────────────────────────────────────────────
// TODO: Backend /presets API로 이동 예정 (SSOT)
// emotion 값은 Backend EMOTION_VOCAB 키와 일치해야 함 (_context_tag_utils.py)
const EMOTION_PRESETS = [
  { id: "excited", label: "밝게", emotion: "excited" },
  { id: "calm", label: "차분", emotion: "calm" },
  { id: "tense", label: "긴장", emotion: "tense" },
  { id: "nostalgic", label: "감성", emotion: "nostalgic" },
] as const;

const BGM_MOOD_PRESETS = [
  {
    id: "upbeat",
    label: "경쾌",
    mood: "upbeat",
    prompt: "bright upbeat cheerful background music",
  },
  { id: "calm", label: "잔잔", mood: "calm", prompt: "calm peaceful relaxing ambient music" },
  {
    id: "tense",
    label: "긴박",
    mood: "tense",
    prompt: "tense dramatic suspenseful cinematic music",
  },
  {
    id: "romantic",
    label: "로맨틱",
    mood: "romantic",
    prompt: "romantic warm emotional piano background music",
  },
] as const;

type Props = {
  onApplyAll?: () => void;
  showToast?: (msg: string, type: "success" | "error" | "warning") => void;
  isApplying?: boolean;
};

// ── Component ────────────────────────────────────────────
export default function DirectorControlPanel({ onApplyAll, showToast, isApplying }: Props) {
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

  const handleEmotionClick = (preset: (typeof EMOTION_PRESETS)[number]) => {
    if (selectedEmotionPreset === preset.id) return;
    setGlobalEmotion(preset.emotion);
    showToast?.(`음성 톤: ${preset.label} 적용`, "success");
  };

  const handleBgmClick = (preset: (typeof BGM_MOOD_PRESETS)[number]) => {
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
          {EMOTION_PRESETS.map((p) => (
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
          {BGM_MOOD_PRESETS.map((p) => (
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
