"use client";

import { useEffect, useState } from "react";
import type { Scene, TTSPreviewState } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";
import { isMultiCharStructure } from "../../utils/structure";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { Input, Textarea } from "../ui";
import { API_BASE } from "../../constants";
import type { ReadingSpeedConfig } from "../../hooks/usePresets";

type SceneEssentialFieldsProps = {
  scene: Scene;
  structure?: string;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
  onImageUpload: (file: File | undefined) => void;
  ttsState?: TTSPreviewState;
  onTTSPreview?: () => void;
  onTTSRegenerate?: () => void;
  audioPlayer?: AudioPlayer;
};

export default function SceneEssentialFields({
  scene,
  structure,
  onUpdateScene,
  onSpeakerChange,
  onImageUpload,
  ttsState,
  onTTSPreview,
  onTTSRegenerate,
  audioPlayer,
}: SceneEssentialFieldsProps) {
  const hasMultipleSpeakers = isMultiCharStructure(structure ?? "");
  const isNarratedDialogue = structure?.toLowerCase() === "narrated dialogue";

  return (
    <>
      {/* Script */}
      <div className="grid gap-2">
        <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Script
        </label>
        <Textarea
          value={scene.script}
          onChange={(e) => onUpdateScene({ script: e.target.value })}
          rows={3}
          className="text-sm"
        />
        <div className="flex items-center gap-2">
          <ScriptMeta script={scene.script} />
          {onTTSPreview && scene.script.trim() && (
            <TTSPreviewButton
              state={ttsState}
              isPlaying={audioPlayer?.playingUrl === ttsState?.audioUrl && !!ttsState?.audioUrl}
              onPreview={onTTSPreview}
              onRegenerate={onTTSRegenerate}
            />
          )}
        </div>
      </div>

      {/* Speaker, Duration, Upload - 3 Column Grid */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Speaker
          </label>
          <select
            value={scene.speaker}
            onChange={(e) => onSpeakerChange(e.target.value as Scene["speaker"])}
            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            {isNarratedDialogue && <option value="Narrator">Narrator</option>}
            <option value="A">Actor A</option>
            {hasMultipleSpeakers && <option value="B">Actor B</option>}
          </select>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Duration
          </label>
          <Input
            type="number"
            min={1}
            max={10}
            value={scene.duration}
            onChange={(e) => {
              const num = Number(e.target.value);
              if (Number.isNaN(num)) return;
              onUpdateScene({ duration: Math.min(10, Math.max(1, Math.round(num))) });
            }}
            onBlur={(e) => {
              if (!e.target.value.trim()) onUpdateScene({ duration: 3 });
            }}
            className="text-sm"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Image
          </label>
          <label className="flex h-10 cursor-pointer items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white/80 text-[12px] font-semibold tracking-[0.2em] text-zinc-600 uppercase hover:bg-zinc-50">
            Upload
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => onImageUpload(e.target.files?.[0])}
            />
          </label>
        </div>
      </div>
    </>
  );
}

/* ---- Script Meta (character count + reading time) ---- */

// Module-level cache for reading speed from /presets API (fetched once)
let _cachedReadingSpeed: Record<string, ReadingSpeedConfig> | null = null;
let _fetchPromise: Promise<void> | null = null;

function useReadingSpeed(): Record<string, ReadingSpeedConfig> {
  const [speed, setSpeed] = useState<Record<string, ReadingSpeedConfig>>(_cachedReadingSpeed ?? {});

  useEffect(() => {
    if (_cachedReadingSpeed) {
      setSpeed(_cachedReadingSpeed);
      return;
    }
    if (!_fetchPromise) {
      _fetchPromise = fetch(`${API_BASE}/presets`)
        .then((res) => res.json())
        .then((data) => {
          if (data?.reading_speed) {
            _cachedReadingSpeed = data.reading_speed;
          }
        })
        .catch(() => {});
    }
    _fetchPromise.then(() => {
      if (_cachedReadingSpeed) setSpeed(_cachedReadingSpeed);
    });
  }, []);

  return speed;
}

function ScriptMeta({ script }: { script: string }) {
  const language = useStoryboardStore((s) => s.language);
  const readingSpeed = useReadingSpeed();
  const text = script.trim();
  if (!text) return null;

  const cfg = readingSpeed[language];
  const charCount = text.replace(/\s/g, "").length;
  const wordCount = text.split(/\s+/).length;
  const isWordBased = cfg?.unit === "words";
  const count = isWordBased ? wordCount : charCount;
  const rate = isWordBased ? (cfg?.wps ?? 2.5) : (cfg?.cps ?? 4);
  const readTime = count / rate;
  const unit = isWordBased ? "words" : language === "Japanese" ? "字" : "자";

  return (
    <div className="flex items-center gap-2 text-[11px] text-zinc-400">
      <span>
        {count}
        {unit}
      </span>
      <span>·</span>
      <span>읽기 {readTime.toFixed(1)}초</span>
    </div>
  );
}

/* ---- Audio Waveform Animation (TTS playing indicator) ---- */

function AudioWaveform() {
  return (
    <span className="inline-flex items-end gap-px" style={{ width: 12, height: 12 }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="inline-block w-[3px] rounded-sm bg-blue-500"
          style={{
            animation: `tts-bar 0.8s ease-in-out ${i * 0.15}s infinite alternate`,
          }}
        />
      ))}
      <style>{`
        @keyframes tts-bar {
          0% { height: 3px; }
          100% { height: 11px; }
        }
      `}</style>
    </span>
  );
}

/* ---- TTS Preview Button ---- */

function TTSPreviewButton({
  state,
  isPlaying,
  onPreview,
  onRegenerate,
}: {
  state?: TTSPreviewState;
  isPlaying: boolean;
  onPreview: () => void;
  onRegenerate?: () => void;
}) {
  const isLoading = state?.status === "loading";
  const hasAudio = !!state?.audioUrl;
  const isError = state?.status === "error";
  const isCached = state?.status === "cached";

  if (isLoading) {
    return (
      <span className="ml-auto flex items-center gap-1">
        <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-500">
          생성 중...
        </span>
      </span>
    );
  }

  if (isError) {
    return (
      <span className="ml-auto flex items-center gap-1.5">
        <button
          onClick={onPreview}
          className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-500 hover:bg-red-100"
          title={state?.error || "TTS error"}
        >
          재시도
        </button>
      </span>
    );
  }

  if (!hasAudio) {
    return (
      <span className="ml-auto">
        <button
          onClick={onPreview}
          className="rounded-full bg-zinc-50 px-2.5 py-0.5 text-xs font-medium text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
          title="TTS 미리듣기"
        >
          미리듣기
        </button>
      </span>
    );
  }

  // Has audio: show play + duration + regenerate
  return (
    <span className="ml-auto flex items-center gap-1.5">
      <button
        onClick={onPreview}
        className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition ${
          isPlaying
            ? "bg-blue-100 text-blue-700"
            : isCached
              ? "bg-emerald-50 text-emerald-600 hover:bg-emerald-100"
              : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
        }`}
        title={isPlaying ? "정지" : isCached ? "캐시된 TTS 재생" : "TTS 재생"}
      >
        {isPlaying ? "■ 정지" : "▶ 재생"}
      </button>
      {isPlaying && <AudioWaveform />}
      <span className="text-[11px] text-zinc-400">{state?.duration?.toFixed(1)}s</span>
      {onRegenerate && (
        <button
          onClick={onRegenerate}
          className="rounded-full bg-zinc-50 px-2 py-0.5 text-xs text-zinc-400 hover:bg-amber-50 hover:text-amber-600"
          title="캐시 삭제 후 새로 생성"
        >
          재생성
        </button>
      )}
    </span>
  );
}
