/**
 * Smart AutoRun Pre-flight Check
 *
 * Analyzes current state and settings to determine:
 * 1. Which settings are valid/missing
 * 2. Which steps need to be executed
 * 3. Whether autorun can proceed
 */

import type { Scene, DraftScene, AutoRunStepId } from "../types";
export type { AutoRunStepId } from "../types";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";
import { useContextStore } from "../store/useContextStore";
import { checkStageStep, checkImagesStep, checkRenderStep } from "./preflight-steps";
import { isMultiCharStructure } from "./structure";
export type { StageCheckInput } from "./preflight-steps";

// ============================================================
// Types
// ============================================================

export interface SettingsCheck {
  valid: boolean;
  value: string | null;
  required: boolean;
  message?: string;
}

export interface StepCheck {
  needed: boolean;
  reason: string;
  count?: number;
  sceneIds?: number[];
  /** Stage step sub-category readiness (locations/characters/voice/bgm) */
  categories?: { label: string; ready: boolean; detail: string }[];
}

export interface PreflightResult {
  // Settings validation
  settings: {
    topic: SettingsCheck;
    character: SettingsCheck;
    voice: SettingsCheck;
    bgm: SettingsCheck;
    controlnet: SettingsCheck;
    ipAdapter: SettingsCheck;
  };

  // SD Parameters (info display)
  sdParams: {
    steps: number;
    cfgScale: number;
    sampler: string;
    seed?: number;
    clipSkip: number;
  };

  // Execution steps
  steps: {
    stage: StepCheck;
    images: StepCheck;
    render: StepCheck;
  };

  // Overall status
  canRun: boolean;
  errors: string[];
  warnings: string[];
}

export interface PreflightInput {
  // Settings
  topic: string;
  structure: string;
  characterName: string | null;
  characterId: number | null;
  characterBName: string | null;
  characterBId: number | null;
  voiceName: string;
  voiceBName: string;
  bgmMode: "manual" | "auto";
  bgmFile: string | null;
  bgmPrompt: string;
  musicPresetId: number | null;
  controlnetEnabled: boolean;
  controlnetWeight: number;
  ipAdapterEnabled: boolean;
  ipAdapterReference: string | null;
  ipAdapterReferenceB: string | null;

  // SD Params
  steps: number;
  cfgScale: number;
  sampler: string;
  seed?: number;
  clipSkip: number;

  // Context
  storyboardId: number | null;

  // State
  scenes: (Scene | DraftScene)[];
  videoUrl: string | null;
  lastRenderHash?: string;
}

// ============================================================
// Helper Functions
// ============================================================

function checkTopic(topic: string): SettingsCheck {
  const trimmed = topic.trim();
  if (!trimmed) {
    return {
      valid: false,
      value: null,
      required: true,
      message: "토픽을 입력하세요",
    };
  }
  return {
    valid: true,
    value: trimmed.length > 30 ? trimmed.slice(0, 30) + "..." : trimmed,
    required: true,
  };
}

function checkCharacter(
  name: string | null,
  id: number | null,
  nameB: string | null,
  idB: number | null,
  structure: string,
  scenes: (Scene | DraftScene)[]
): SettingsCheck {
  // Narrator-only storyboards don't require a character
  const allNarrator = scenes.length > 0 && scenes.every((s) => s.speaker === "Narrator");
  if (!id || !name) {
    if (allNarrator) {
      return {
        valid: true,
        value: "Narrator",
        required: false,
        message: "나레이터 구조 (캐릭터 불필요)",
      };
    }
    return {
      valid: false,
      value: null,
      required: true,
      message: "Character Preset을 선택하세요",
    };
  }
  const isMulti = isMultiCharStructure(structure);
  if (isMulti && idB && nameB) {
    return { valid: true, value: `${name} & ${nameB}`, required: true };
  }
  if (isMulti && (!idB || !nameB)) {
    return {
      valid: false,
      value: null,
      required: true,
      message: `${name} 선택됨 — Character B 필요`,
    };
  }
  return {
    valid: true,
    value: name,
    required: !allNarrator,
  };
}

function checkVoice(voiceName: string, voiceBName: string, structure: string): SettingsCheck {
  const isMulti = isMultiCharStructure(structure);
  if (!voiceName && !voiceBName) {
    return {
      valid: true,
      value: "기본값",
      required: false,
      message: "기본 음성 사용",
    };
  }
  if (isMulti && voiceName && voiceBName) {
    return { valid: true, value: `${voiceName} / ${voiceBName}`, required: false };
  }
  return {
    valid: true,
    value: voiceName || voiceBName || "기본값",
    required: false,
  };
}

function checkBgm(bgmFile: string | null): SettingsCheck {
  if (!bgmFile) {
    return {
      valid: true, // Not required
      value: null,
      required: false,
      message: "BGM 없음 (무음)",
    };
  }
  // Extract filename from path
  const filename = bgmFile.split("/").pop() || bgmFile;
  return {
    valid: true,
    value: filename.length > 25 ? filename.slice(0, 25) + "..." : filename,
    required: false,
  };
}

function checkControlnet(enabled: boolean, weight: number): SettingsCheck {
  if (!enabled) {
    return {
      valid: true,
      value: "비활성",
      required: false,
      message: "포즈 제어 비활성 (권장: 활성)",
    };
  }
  return {
    valid: true,
    value: `활성 (${weight})`,
    required: false,
  };
}

function checkIpAdapter(
  enabled: boolean,
  reference: string | null,
  referenceB: string | null,
  structure: string
): SettingsCheck {
  if (!enabled) {
    return { valid: true, value: "비활성", required: false };
  }
  if (!reference) {
    return { valid: false, value: null, required: false, message: "IP-Adapter 참조 이미지 필요" };
  }
  const nameA = reference.split("/").pop() || reference;
  const shortA = nameA.length > 20 ? nameA.slice(0, 20) + "..." : nameA;
  const isMulti = isMultiCharStructure(structure);
  if (isMulti && referenceB) {
    const nameB = referenceB.split("/").pop() || referenceB;
    const shortB = nameB.length > 20 ? nameB.slice(0, 20) + "..." : nameB;
    return { valid: true, value: `${shortA} & ${shortB}`, required: false };
  }
  return { valid: true, value: shortA, required: false };
}

// ============================================================
// Main Function
// ============================================================

export function runPreflight(input: PreflightInput): PreflightResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check settings
  const settings = {
    topic: checkTopic(input.topic),
    character: checkCharacter(
      input.characterName,
      input.characterId,
      input.characterBName,
      input.characterBId,
      input.structure,
      input.scenes
    ),
    voice: checkVoice(input.voiceName, input.voiceBName, input.structure),
    bgm: checkBgm(input.bgmFile),
    controlnet: checkControlnet(input.controlnetEnabled, input.controlnetWeight),
    ipAdapter: checkIpAdapter(
      input.ipAdapterEnabled,
      input.ipAdapterReference,
      input.ipAdapterReferenceB,
      input.structure
    ),
  };

  // Collect errors and warnings from settings
  if (!settings.topic.valid) {
    errors.push(settings.topic.message || "토픽 필요");
  }
  if (!settings.character.valid) {
    errors.push(settings.character.message || "캐릭터 필요");
  }
  if (!settings.ipAdapter.valid) {
    // Demote to warning if any scene has per-scene IP-Adapter override
    const hasSceneIpOverride = input.scenes.some(
      (s) => "use_ip_adapter" in s && (s as Scene).use_ip_adapter != null
    );
    if (hasSceneIpOverride) {
      warnings.push(settings.ipAdapter.message || "IP-Adapter: 글로벌 참조 없음 (씬별 설정 사용)");
    } else {
      errors.push(settings.ipAdapter.message || "IP-Adapter 설정 오류");
    }
  }
  if (settings.controlnet.message?.includes("권장")) {
    warnings.push(settings.controlnet.message);
  }
  if (settings.bgm.message?.includes("무음")) {
    warnings.push(settings.bgm.message);
  }

  // SD Parameters (info only)
  const sdParams = {
    steps: input.steps,
    cfgScale: input.cfgScale,
    sampler: input.sampler,
    ...(input.seed != null && { seed: input.seed }),
    clipSkip: input.clipSkip,
  };

  // Scenes must exist (script should be created before autopilot)
  if (input.scenes.length === 0) {
    errors.push("씬이 없습니다. 먼저 스크립트를 생성하세요.");
  }

  // Storyboard must be saved before autorun
  if (!input.storyboardId) {
    errors.push("스토리보드가 저장되지 않았습니다. 먼저 저장해주세요.");
  }

  // Check steps
  const steps = {
    stage: checkStageStep({
      scenes: input.scenes,
      characterName: input.characterName,
      characterBName: input.characterBName,
      voiceName: input.voiceName,
      bgmMode: input.bgmMode,
      musicPresetId: input.musicPresetId,
      bgmPrompt: input.bgmPrompt,
    }),
    images: checkImagesStep(input.scenes),
    render: checkRenderStep(input.scenes, input.videoUrl),
  };

  // Determine if we can run
  const canRun = errors.length === 0;

  return {
    settings,
    sdParams,
    steps,
    canRun,
    errors,
    warnings,
  };
}

// ============================================================
// Utility: Get steps to execute
// ============================================================

export function getStepsToExecute(
  preflight: PreflightResult,
  userOverrides?: Partial<Record<AutoRunStepId, boolean>>
): AutoRunStepId[] {
  const stepOrder: AutoRunStepId[] = ["stage", "images", "render"];

  return stepOrder.filter((stepId) => {
    // User can force enable/disable
    if (userOverrides && stepId in userOverrides) {
      return userOverrides[stepId];
    }
    // Otherwise use preflight result
    return preflight.steps[stepId].needed;
  });
}

// ============================================================
// Utility: Build PreflightInput from store
// ============================================================

export function buildPreflightInput(): PreflightInput {
  const sb = useStoryboardStore.getState();
  const render = useRenderStore.getState();
  const ctx = useContextStore.getState();
  const sp = render.currentStyleProfile;
  // Dialogue: show character names as voice labels (each character owns its voice_preset)
  // Narrator-only: show group narrator preset
  const isMulti = isMultiCharStructure(sb.structure);
  const voiceName = isMulti
    ? (sb.selectedCharacterName ?? "")
    : render.voicePresetId
      ? `Preset #${render.voicePresetId}`
      : "";
  const voiceBName = isMulti ? (sb.selectedCharacterBName ?? "") : "";
  return {
    topic: sb.topic,
    structure: sb.structure,
    characterName: sb.selectedCharacterName,
    characterId: sb.selectedCharacterId,
    characterBName: sb.selectedCharacterBName ?? null,
    characterBId: sb.selectedCharacterBId ?? null,
    voiceName,
    voiceBName,
    bgmMode: render.bgmMode,
    bgmFile: render.bgmFile,
    bgmPrompt: render.bgmPrompt,
    musicPresetId: render.musicPresetId,
    controlnetEnabled: sb.useControlnet,
    controlnetWeight: sb.controlnetWeight,
    ipAdapterEnabled: sb.useIpAdapter,
    ipAdapterReference: sb.ipAdapterReference || null,
    ipAdapterReferenceB: sb.ipAdapterReferenceB || null,
    steps: sp?.default_steps ?? 27,
    cfgScale: sp?.default_cfg_scale ?? 7.0,
    sampler: sp?.default_sampler_name ?? "DPM++ 2M Karras",
    clipSkip: sp?.default_clip_skip ?? 2,
    storyboardId: ctx.storyboardId,
    scenes: sb.scenes,
    videoUrl: render.videoUrl,
  };
}

// ============================================================
// Utility: Estimate time
// ============================================================

export function estimateTime(preflight: PreflightResult): string {
  let seconds = 0;

  if (preflight.steps.stage.needed) {
    const count = preflight.steps.stage.count || 3;
    seconds += count * 20; // ~20s per location
  }
  if (preflight.steps.images.needed) {
    const count = preflight.steps.images.count || 6;
    seconds += count * 15; // ~15s per image
  }
  if (preflight.steps.render.needed) seconds += 30;

  if (seconds < 60) {
    return `~${seconds}초`;
  }
  const minutes = Math.ceil(seconds / 60);
  return `~${minutes}분`;
}
