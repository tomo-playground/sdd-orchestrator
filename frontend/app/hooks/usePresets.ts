"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "../constants";
import type { HiResDefaults, ImageDefaults } from "../types";

export type Preset = {
  id: string;
  name: string;
  name_ko: string;
  structure: string;
  sample_topics: string[];
  default_duration: number;
  default_language: string;
};

export type LangOption = { value: string; label: string };
export type StepMetadata = { key: string; label: string; desc: string };
export type ReadingSpeedConfig = { cps?: number; wps?: number; unit: string };
export type GenerationDefaults = {
  use_controlnet: boolean;
  controlnet_weight: number;
  use_ip_adapter: boolean;
  ip_adapter_weight: number;
  multi_gen_enabled: boolean;
  enable_hr: boolean;
};

export type EmotionPreset = { id: string; label: string; emotion: string };
export type BgmMoodPreset = { id: string; label: string; mood: string; prompt: string };
export type IdLabelOption = { id: string; label: string };

export function usePresets(skip = false) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [languages, setLanguages] = useState<LangOption[]>([]);
  const [durations, setDurations] = useState<number[]>([15, 30, 45, 60]);
  const [readingSpeed, setReadingSpeed] = useState<Record<string, ReadingSpeedConfig>>({});
  const [optionalSteps, setOptionalSteps] = useState<string[]>([]);
  const [pipelineMetadata, setPipelineMetadata] = useState<StepMetadata[]>([]);
  const [generationDefaults, setGenerationDefaults] = useState<GenerationDefaults | null>(null);
  // Backend SSOT fields (SSOT 위반 해소 — /presets API에서 수신)
  const [hiResDefaults, setHiResDefaults] = useState<HiResDefaults | null>(null);
  const [imageDefaults, setImageDefaults] = useState<ImageDefaults | null>(null);
  const [samplers, setSamplers] = useState<string[]>([]);
  const [ttsEngine, setTtsEngine] = useState<string | null>(null);
  const [emotionPresets, setEmotionPresets] = useState<EmotionPreset[]>([]);
  const [bgmMoodPresets, setBgmMoodPresets] = useState<BgmMoodPreset[]>([]);
  const [ipAdapterModels, setIpAdapterModels] = useState<string[]>([]);
  const [overlayStyles, setOverlayStyles] = useState<IdLabelOption[]>([]);
  const [isLoading, setIsLoading] = useState(!skip);

  useEffect(() => {
    if (skip) return;
    setIsLoading(true);
    fetch(`${API_BASE}/presets`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data?.presets)) setPresets(data.presets);
        if (Array.isArray(data?.languages)) setLanguages(data.languages);
        if (Array.isArray(data?.durations)) setDurations(data.durations);
        if (data?.reading_speed) setReadingSpeed(data.reading_speed);
        if (Array.isArray(data?.optional_steps)) setOptionalSteps(data.optional_steps);
        if (Array.isArray(data?.pipeline_metadata)) setPipelineMetadata(data.pipeline_metadata);
        if (data?.generation_defaults) setGenerationDefaults(data.generation_defaults);
        // Backend SSOT fields
        if (data?.hi_res_defaults) setHiResDefaults(data.hi_res_defaults);
        if (data?.image_defaults) setImageDefaults(data.image_defaults);
        if (Array.isArray(data?.samplers)) setSamplers(data.samplers);
        if (data?.tts_engine) setTtsEngine(data.tts_engine);
        if (Array.isArray(data?.emotion_presets)) setEmotionPresets(data.emotion_presets);
        if (Array.isArray(data?.bgm_mood_presets)) setBgmMoodPresets(data.bgm_mood_presets);
        if (Array.isArray(data?.ip_adapter_models)) setIpAdapterModels(data.ip_adapter_models);
        if (Array.isArray(data?.overlay_styles)) setOverlayStyles(data.overlay_styles);
      })
      .catch((err) => console.error("[usePresets] fetch failed:", err))
      .finally(() => setIsLoading(false));
  }, [skip]);

  return {
    presets,
    languages,
    durations,
    readingSpeed,
    optionalSteps,
    pipelineMetadata,
    generationDefaults,
    hiResDefaults,
    imageDefaults,
    samplers,
    ttsEngine,
    emotionPresets,
    bgmMoodPresets,
    ipAdapterModels,
    overlayStyles,
    isLoading,
  };
}
