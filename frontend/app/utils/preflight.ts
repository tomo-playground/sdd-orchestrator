/**
 * Smart AutoRun Pre-flight Check
 *
 * Analyzes current state and settings to determine:
 * 1. Which settings are valid/missing
 * 2. Which steps need to be executed
 * 3. Whether autorun can proceed
 */

import type { Scene, DraftScene } from "../types";
import { useStudioStore } from "../store/useStudioStore";

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
    images: StepCheck;
    validate: StepCheck;
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

function checkValidateStep(scenes: (Scene | DraftScene)[]): StepCheck {
  // Count scenes that have images but need validation
  const scenesNeedingValidation = scenes.filter(
    (s) => s.image_url && !("candidates" in s && s.candidates?.length)
  );

  if (scenesNeedingValidation.length === 0) {
    return {
      needed: false,
      reason: "검증 완료",
    };
  }

  return {
    needed: true,
    reason: `${scenesNeedingValidation.length}개 검증 필요`,
    count: scenesNeedingValidation.length,
    sceneIds: scenesNeedingValidation.map((s) => s.id),
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

  // TODO: Add content hash comparison to detect changes
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
    images: checkImagesStep(input.scenes),
    validate: checkValidateStep(input.scenes),
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

export type AutoRunStepId = "images" | "validate" | "render";

export function getStepsToExecute(
  preflight: PreflightResult,
  userOverrides?: Partial<Record<AutoRunStepId, boolean>>
): AutoRunStepId[] {
  const stepOrder: AutoRunStepId[] = ["images", "validate", "render"];

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
  const s = useStudioStore.getState();
  const voiceName = s.voicePresetId ? `Preset #${s.voicePresetId}` : "";
  return {
    topic: s.topic,
    characterName: s.selectedCharacterName,
    characterId: s.selectedCharacterId,
    voiceName,
    bgmFile: s.bgmFile,
    controlnetEnabled: s.useControlnet,
    controlnetWeight: s.controlnetWeight,
    ipAdapterEnabled: s.useIpAdapter,
    ipAdapterReference: s.ipAdapterReference || null,
    steps: s.effectiveSdSteps ?? 0,
    cfgScale: s.effectiveSdCfgScale ?? 0,
    sampler: s.effectiveSdSamplerName ?? "",
    clipSkip: s.effectiveSdClipSkip ?? 0,
    scenes: s.scenes,
    videoUrl: s.videoUrl,
  };
}

// ============================================================
// Utility: Estimate time
// ============================================================

export function estimateTime(preflight: PreflightResult): string {
  let seconds = 0;

  if (preflight.steps.images.needed) {
    const count = preflight.steps.images.count || 6;
    seconds += count * 15; // ~15s per image
  }
  if (preflight.steps.validate.needed) {
    const count = preflight.steps.validate.count || 6;
    seconds += count * 3; // ~3s per validation
  }
  if (preflight.steps.render.needed) seconds += 30;

  if (seconds < 60) {
    return `~${seconds}초`;
  }
  const minutes = Math.ceil(seconds / 60);
  return `~${minutes}분`;
}
