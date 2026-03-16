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

export function usePresets(skip = false) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [languages, setLanguages] = useState<LangOption[]>([]);
  const [durations, setDurations] = useState<number[]>([15, 30, 45, 60]);
  const [readingSpeed, setReadingSpeed] = useState<Record<string, ReadingSpeedConfig>>({});
  const [optionalSteps, setOptionalSteps] = useState<string[]>([]);
  const [pipelineMetadata, setPipelineMetadata] = useState<StepMetadata[]>([]);
  const [generationDefaults, setGenerationDefaults] = useState<GenerationDefaults | null>(null);
  const [fastTrackSkipStages, setFastTrackSkipStages] = useState<string[]>([]);
  // Backend SSOT fields (SSOT 위반 해소 — /presets API에서 수신)
  const [hiResDefaults, setHiResDefaults] = useState<HiResDefaults | null>(null);
  const [imageDefaults, setImageDefaults] = useState<ImageDefaults | null>(null);
  const [samplers, setSamplers] = useState<string[]>([]);
  const [ttsEngine, setTtsEngine] = useState<string | null>(null);

  useEffect(() => {
    if (skip) return;
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
        if (Array.isArray(data?.fast_track_skip_stages))
          setFastTrackSkipStages(data.fast_track_skip_stages);
        // Backend SSOT fields
        if (data?.hi_res_defaults) setHiResDefaults(data.hi_res_defaults);
        if (data?.image_defaults) setImageDefaults(data.image_defaults);
        if (Array.isArray(data?.samplers)) setSamplers(data.samplers);
        if (data?.tts_engine) setTtsEngine(data.tts_engine);
      })
      .catch((err) => console.error("[usePresets] fetch failed:", err));
  }, [skip]);

  return {
    presets,
    languages,
    durations,
    readingSpeed,
    optionalSteps,
    pipelineMetadata,
    generationDefaults,
    fastTrackSkipStages,
    hiResDefaults,
    imageDefaults,
    samplers,
    ttsEngine,
  };
}
