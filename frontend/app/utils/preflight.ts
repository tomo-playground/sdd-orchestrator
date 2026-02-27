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
import { useContextStore } from "../store/useContextStore";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useRenderStore } from "../store/useRenderStore";

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
  characterName: string | null;
  characterId: number | null;
  voiceName: string;
  bgmFile: string | null;
  controlnetEnabled: boolean;
  controlnetWeight: number;
  ipAdapterEnabled: boolean;
  ipAdapterReference: string | null;

  // SD Params
  steps: number;
  cfgScale: number;
  sampler: string;
  seed?: number;
  clipSkip: number;

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

function checkCharacter(name: string | null, id: number | null): SettingsCheck {
  if (!id || !name) {
    return {
      valid: false,
      value: null,
      required: true,
      message: "Character Preset을 선택하세요",
    };
  }
  return {
    valid: true,
    value: name,
    required: true,
  };
}

function checkVoice(voiceName: string): SettingsCheck {
  if (!voiceName) {
    return {
      valid: true, // Not required
      value: "기본값",
      required: false,
      message: "기본 음성 사용",
    };
  }
  return {
    valid: true,
    value: voiceName,
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

function checkIpAdapter(enabled: boolean, reference: string | null): SettingsCheck {
  if (!enabled) {
    return {
      valid: true,
      value: "비활성",
      required: false,
    };
  }
  if (!reference) {
    return {
      valid: false,
      value: null,
      required: false,
      message: "IP-Adapter 참조 이미지 필요",
    };
  }
  const refName = reference.split("/").pop() || reference;
  return {
    valid: true,
    value: refName.length > 20 ? refName.slice(0, 20) + "..." : refName,
    required: false,
  };
}

// ============================================================
// Step Checks
// ============================================================

function checkStageStep(scenes: (Scene | DraftScene)[]): StepCheck {
  if (scenes.length === 0) {
    return { needed: false, reason: "씬 없음" };
  }
  const withoutBg = scenes.filter((s) => !s.background_id);
  if (withoutBg.length === 0) {
    return { needed: false, reason: "모든 씬에 배경 있음" };
  }
  return {
    needed: true,
    reason: `${withoutBg.length}/${scenes.length} 배경 필요`,
    count: withoutBg.length,
  };
}

function checkImagesStep(scenes: (Scene | DraftScene)[]): StepCheck {
  if (scenes.length === 0) {
    return {
      needed: true,
      reason: "전체 생성 필요",
    };
  }

  const scenesWithoutImage = scenes.filter((s) => !s.image_url);
  if (scenesWithoutImage.length === 0) {
    return {
      needed: false,
      reason: "모든 씬 이미지 있음",
    };
  }

  return {
    needed: true,
    reason: `${scenesWithoutImage.length}/${scenes.length} 필요`,
    count: scenesWithoutImage.length,
    sceneIds: scenesWithoutImage.map((s) => s.id),
  };
}

function checkRenderStep(scenes: (Scene | DraftScene)[], videoUrl: string | null): StepCheck {
  if (scenes.length === 0) {
    return {
      needed: true,
      reason: "스토리보드 후 실행",
    };
  }

  const hasAllImages = scenes.every((s) => s.image_url);
  if (!hasAllImages) {
    return {
      needed: true,
      reason: "이미지 생성 후 실행",
    };
  }

  if (!videoUrl) {
    return {
      needed: true,
      reason: "영상 없음",
    };
  }

  // Render check
  return {
    needed: false,
    reason: "영상 존재",
  };
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
    character: checkCharacter(input.characterName, input.characterId),
    voice: checkVoice(input.voiceName),
    bgm: checkBgm(input.bgmFile),
    controlnet: checkControlnet(input.controlnetEnabled, input.controlnetWeight),
    ipAdapter: checkIpAdapter(input.ipAdapterEnabled, input.ipAdapterReference),
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

  // Check steps
  const steps = {
    stage: checkStageStep(input.scenes),
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
  const ctx = useContextStore.getState();
  const sb = useStoryboardStore.getState();
  const render = useRenderStore.getState();
  const voiceName = render.voicePresetId ? `Preset #${render.voicePresetId}` : "";
  return {
    topic: sb.topic,
    characterName: sb.selectedCharacterName,
    characterId: sb.selectedCharacterId,
    voiceName,
    bgmFile: render.bgmFile,
    controlnetEnabled: sb.useControlnet,
    controlnetWeight: sb.controlnetWeight,
    ipAdapterEnabled: sb.useIpAdapter,
    ipAdapterReference: sb.ipAdapterReference || null,
    steps: ctx.effectiveSdSteps ?? 0,
    cfgScale: ctx.effectiveSdCfgScale ?? 0,
    sampler: ctx.effectiveSdSamplerName ?? "",
    clipSkip: ctx.effectiveSdClipSkip ?? 0,
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
