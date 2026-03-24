/**
 * AutoRun Preflight — Settings check helpers.
 *
 * Separated from preflight.ts to stay within the 400-line file limit.
 */

import type { Scene, DraftScene, SettingsCheck } from "../types";
import { isMultiCharStructure } from "./structure";

export function checkTopic(topic: string): SettingsCheck {
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

export function checkCharacter(
  name: string | null,
  id: number | null,
  nameB: string | null,
  idB: number | null,
  structure: string,
  scenes: (Scene | DraftScene)[]
): SettingsCheck {
  // Narrator-only storyboards don't require a character
  const allNarrator = scenes.length > 0 && scenes.every((s) => s.speaker === "narrator");
  if (!id || !name) {
    if (allNarrator) {
      return {
        valid: true,
        value: "narrator",
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

export function checkVoice(voiceName: string, voiceBName: string, structure: string): SettingsCheck {
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

export function checkBgm(bgmFile: string | null, bgmMode: "manual" | "auto"): SettingsCheck {
  if (bgmMode === "auto") {
    return {
      valid: true,
      value: "Auto BGM",
      required: false,
    };
  }
  // Manual mode
  if (!bgmFile) {
    return {
      valid: true,
      value: null,
      required: false,
      message: "BGM 없음 (무음)",
      warning: true,
    };
  }
  const filename = bgmFile.split("/").pop() || bgmFile;
  return {
    valid: true,
    value: filename.length > 25 ? filename.slice(0, 25) + "..." : filename,
    required: false,
  };
}

export function checkControlnet(enabled: boolean, weight: number): SettingsCheck {
  if (!enabled) {
    return {
      valid: true,
      value: "비활성",
      required: false,
      message: "포즈 제어 비활성 (권장: 활성)",
      warning: true,
    };
  }
  return {
    valid: true,
    value: `활성 (${weight})`,
    required: false,
  };
}

export function checkIpAdapter(
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
