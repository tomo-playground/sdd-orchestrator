/**
 * Migrate legacy draft data from "shorts-producer:draft:v1"
 * to the new Zustand store key "shorts-producer:studio:v1".
 *
 * Runs once on first load; deletes the old key after migration.
 */

import { DEFAULT_STRUCTURE } from "../../constants";

const OLD_KEY = "shorts-producer:draft:v1";
const NEW_KEY = "shorts-producer:studio:v1";

let migrated = false;

export function migrateDraft(): void {
  if (migrated) return;
  migrated = true;

  if (typeof window === "undefined") return;

  try {
    const existing = window.localStorage.getItem(NEW_KEY);
    if (existing) return; // Already has new data, skip

    const raw = window.localStorage.getItem(OLD_KEY);
    if (!raw) return;

    const draft = JSON.parse(raw);
    if (!draft || typeof draft !== "object") return;

    // Map old DraftData fields → new store shape
    const newState: Record<string, unknown> = {
      state: {
        // Plan fields
        topic: draft.topic ?? "",
        description: draft.description ?? "",
        duration: draft.duration ?? 30,
        style: draft.style ?? "Anime",
        language: draft.language ?? "Korean",
        structure: draft.structure ?? DEFAULT_STRUCTURE,
        actorAGender: draft.actorAGender ?? "female",
        selectedCharacterId: draft.selectedCharacterId ?? null,
        selectedCharacterBId: null,
        basePromptA: draft.basePromptA ?? "",
        baseNegativePromptA: draft.baseNegativePromptA ?? "",
        basePromptB: "",
        baseNegativePromptB: "",
        baseStepsA: draft.baseStepsA ?? 27,
        baseCfgScaleA: draft.baseCfgScaleA ?? 7,
        baseSamplerA: draft.baseSamplerA ?? "DPM++ 2M Karras",
        baseSeedA: draft.baseSeedA ?? -1,
        baseClipSkipA: draft.baseClipSkipA ?? 2,
        hiResEnabled: draft.hiResEnabled ?? false,
        veoEnabled: draft.veoEnabled ?? false,
        useControlnet: draft.useControlnet ?? true,
        controlnetWeight: draft.controlnetWeight ?? 0.8,
        useIpAdapter: draft.useIpAdapter ?? false,
        ipAdapterReference: draft.ipAdapterReference ?? "",
        ipAdapterWeight: draft.ipAdapterWeight ?? 0.7,

        // Scenes (convert DraftScene[] → Scene[])
        scenes: (draft.scenes || []).map((s: Record<string, unknown>) => ({
          ...s,
          isGenerating: false,
          debug_payload: "",
        })),
        currentSceneIndex: 0,

        // Output
        layoutStyle: draft.layoutStyle ?? "post",
        kenBurnsPreset: draft.kenBurnsPreset ?? "random",
        kenBurnsIntensity: draft.kenBurnsIntensity ?? 1.0,
        includeSceneText: draft.includeSceneText ?? true,
        bgmFile: draft.bgmFile ?? "random",
        audioDucking: draft.audioDucking ?? true,
        bgmVolume: draft.bgmVolume ?? 0.25,
        speedMultiplier: draft.speedMultiplier ?? 1.3,
        sceneTextFont: draft.sceneTextFont ?? draft.subtitleFont ?? "",
        ttsEngine: "qwen",
        voiceDesignPrompt: draft.voiceDesignPrompt ?? "",
        voicePresetId: null,
        videoUrl: draft.videoUrl ?? null,
        videoUrlFull: draft.videoUrlFull ?? null,
        videoUrlPost: draft.videoUrlPost ?? null,
        recentVideos: draft.recentVideos ?? [],

        // Meta
        activeTab: "plan",
      },
      version: 0,
    };

    window.localStorage.setItem(NEW_KEY, JSON.stringify(newState));
    window.localStorage.removeItem(OLD_KEY);
  } catch {
    // Migration failed - not critical, user starts fresh
  }
}
