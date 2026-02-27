/**
 * AutoRun step check functions.
 *
 * Separated from preflight.ts to stay within the 400-line file limit.
 */

import type { Scene, DraftScene } from "../types";
import type { StepCheck } from "./preflight";

// ============================================================
// Stage Step
// ============================================================

export interface StageCheckInput {
  scenes: (Scene | DraftScene)[];
  characterName: string | null;
  characterBName: string | null;
  voiceName: string;
  bgmMode: "manual" | "auto";
  musicPresetId: number | null;
  bgmPrompt: string;
}

export function checkStageStep(input: StageCheckInput): StepCheck {
  const { scenes } = input;

  // Sub-category checks
  const withoutBg = scenes.filter((s) => !s.background_id);
  const bgReady = scenes.length > 0 && withoutBg.length === 0;
  const charReady = !!input.characterName;
  const voiceReady = !!input.voiceName;
  const bgmReady = input.bgmMode === "manual" ? !!input.musicPresetId : !!input.bgmPrompt;

  const categories = [
    {
      label: "배경",
      ready: bgReady,
      detail: scenes.length === 0 ? "씬 없음" : bgReady ? "완료" : `${withoutBg.length}/${scenes.length}`,
    },
    {
      label: "캐릭터",
      ready: charReady,
      detail: charReady
        ? [input.characterName, input.characterBName].filter(Boolean).join(", ")
        : "미선택",
    },
    { label: "음성", ready: voiceReady, detail: voiceReady ? input.voiceName : "미선택" },
    {
      label: "BGM",
      ready: bgmReady,
      detail: bgmReady ? (input.bgmMode === "manual" ? "프리셋" : "Auto") : "미설정",
    },
  ];

  const readyCount = categories.filter((c) => c.ready).length;
  const allReady = readyCount === categories.length;

  // Stage auto-run only handles backgrounds
  const needed = scenes.length > 0 && withoutBg.length > 0;

  return {
    needed,
    reason: allReady ? "모든 에셋 준비 완료" : `${readyCount}/${categories.length} 준비됨`,
    count: needed ? withoutBg.length : undefined,
    categories,
  };
}

// ============================================================
// Images Step
// ============================================================

export function checkImagesStep(scenes: (Scene | DraftScene)[]): StepCheck {
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
    reason: `${scenesWithoutImage.length}/${scenes.length} 이미지 필요`,
    sceneIds: scenesWithoutImage.map((s) => s.id),
  };
}

// ============================================================
// Render Step
// ============================================================

export function checkRenderStep(scenes: (Scene | DraftScene)[], videoUrl: string | null): StepCheck {
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

  return {
    needed: false,
    reason: "영상 존재",
  };
}
