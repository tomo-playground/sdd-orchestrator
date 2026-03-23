import axios from "axios";
import type { Scene } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useUIStore } from "../useUIStore";
import { ADMIN_API_BASE } from "../../constants";
import { getErrorMsg } from "../../utils/error";

// --------------- Apply Missing Tags ---------------

export function applyMissingImageTags(scene: Scene, missingOverride?: string[], limit = 5) {
  const { imageValidationResults, updateScene } = useStoryboardStore.getState();
  const { showToast } = useUIStore.getState();
  const missing = missingOverride ?? imageValidationResults[scene.client_id]?.missing ?? [];
  if (!missing.length) {
    showToast("추가할 누락 태그가 없습니다", "error");
    return;
  }
  const existing = scene.image_prompt
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
  const existingSet = new Set(existing.map((t) => t.toLowerCase()));
  const next = [...existing];
  let addedCount = 0;
  missing.slice(0, limit).forEach((tok) => {
    if (!existingSet.has(tok.toLowerCase())) {
      next.push(tok);
      addedCount++;
    }
  });
  if (addedCount > 0) {
    updateScene(scene.client_id, { image_prompt: next.join(", ") });
    showToast(`${addedCount}개 태그가 프롬프트에 추가됨`, "success");
  } else {
    showToast("모든 태그가 이미 프롬프트에 있습니다", "error");
  }
}

// --------------- Speaker Change ---------------

export function handleSpeakerChange(scene: Scene, speaker: Scene["speaker"]) {
  const { baseNegativePromptA, baseNegativePromptB, updateScene } = useStoryboardStore.getState();

  // Preserve custom negative prompt: only reset to base if the scene's current
  // negative_prompt matches the old speaker's base (i.e. it was never customized)
  const oldBase = scene.speaker === "B" ? baseNegativePromptB : baseNegativePromptA;
  const isCustomized = scene.negative_prompt && scene.negative_prompt !== oldBase;

  const updates: Partial<Scene> = { speaker };
  if (!isCustomized) {
    updates.negative_prompt = speaker === "B" ? baseNegativePromptB : baseNegativePromptA;
  }

  updateScene(scene.client_id, updates);
}

// --------------- Mark Success / Fail ---------------

export async function handleMarkSuccess(scene: Scene) {
  const { showToast } = useUIStore.getState();
  if (!scene.activity_log_id) {
    showToast("표시할 생성 로그가 없습니다", "error");
    return;
  }
  useStoryboardStore.getState().set({
    markingStatusSceneId: scene.client_id,
  });
  try {
    await axios.patch(`${ADMIN_API_BASE}/activity-logs/${scene.activity_log_id}/status`, {
      status: "success",
    });
    showToast("성공으로 표시됨", "success");
  } catch {
    showToast("상태 표시에 실패했습니다", "error");
  } finally {
    useStoryboardStore.getState().set({ markingStatusSceneId: null });
  }
}

export async function handleMarkFail(scene: Scene) {
  const { showToast } = useUIStore.getState();
  if (!scene.activity_log_id) {
    showToast("표시할 생성 로그가 없습니다", "error");
    return;
  }
  useStoryboardStore.getState().set({
    markingStatusSceneId: scene.client_id,
  });
  try {
    await axios.patch(`${ADMIN_API_BASE}/activity-logs/${scene.activity_log_id}/status`, {
      status: "fail",
    });
    showToast("실패로 표시됨", "error");
  } catch {
    showToast("상태 표시에 실패했습니다", "error");
  } finally {
    useStoryboardStore.getState().set({ markingStatusSceneId: null });
  }
}
