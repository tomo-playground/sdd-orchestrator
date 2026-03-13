import axios from "axios";
import type { Scene } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, ADMIN_API_BASE } from "../../constants";
import { getErrorMsg } from "../../utils/error";

// --------------- Apply Missing Tags ---------------

export function applyMissingImageTags(scene: Scene, missingOverride?: string[], limit = 5) {
  const { imageValidationResults, updateScene } = useStoryboardStore.getState();
  const { showToast } = useUIStore.getState();
  const missing = missingOverride ?? imageValidationResults[scene.client_id]?.missing ?? [];
  if (!missing.length) {
    showToast("No missing tags to add", "error");
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
    showToast(`Added ${addedCount} tags to prompt`, "success");
  } else {
    showToast("All tags already in prompt", "error");
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

// --------------- Image Validation ---------------

export async function handleValidateImage(scene: Scene) {
  const { showToast } = useUIStore.getState();
  if (!scene.image_url) {
    showToast("Upload or generate an image first.", "error");
    return;
  }
  if (scene.image_url.startsWith("data:")) {
    showToast("Save the scene first (image must be stored).", "error");
    return;
  }
  useStoryboardStore.getState().set({ validatingSceneId: scene.client_id });
  const prompt = scene.debug_prompt || scene.image_prompt;
  const { storyboardId } = useContextStore.getState();

  try {
    const payload =
      scene.image_url.startsWith("http://") || scene.image_url.startsWith("https://")
        ? { image_url: scene.image_url, prompt, storyboard_id: storyboardId, scene_id: scene.id }
        : { image_b64: scene.image_url, prompt, storyboard_id: storyboardId, scene_id: scene.id };
    const res = await axios.post(`${API_BASE}/scene/validate-and-auto-edit`, payload);
    // validate-and-auto-edit returns nested { validation_result: {...}, auto_edit_triggered }
    const validation = res.data.validation_result ?? res.data;
    const prev = useStoryboardStore.getState().imageValidationResults;
    useStoryboardStore.getState().set({
      imageValidationResults: { ...prev, [scene.client_id]: validation },
    });
    const matchRate = Math.round((validation.match_rate || 0) * 100);

    const criticalFailure = validation.critical_failure;
    if (criticalFailure?.has_failure && criticalFailure.failures?.length > 0) {
      const first = criticalFailure.failures[0];
      const labels: Record<string, string> = {
        gender_swap: "성별 반전",
        no_subject: "인물 미감지",
        count_mismatch: "인물수 불일치",
      };
      const label = labels[first.failure_type] ?? first.failure_type;
      showToast(`Critical: ${label} — 재생성을 권장합니다 (${matchRate}%)`, "error");
    } else if (matchRate >= 80) {
      showToast(`Validated! Match ${matchRate}%`, "success");
    } else {
      showToast(`Match ${matchRate}% - check missing tags`, "error");
    }
  } catch (error) {
    showToast(getErrorMsg(error, "이미지 검증 실패"), "error");
  } finally {
    useStoryboardStore.getState().set({ validatingSceneId: null });
  }
}

// --------------- Mark Success / Fail ---------------

export async function handleMarkSuccess(scene: Scene) {
  const { showToast } = useUIStore.getState();
  if (!scene.activity_log_id) {
    showToast("No generation log to mark", "error");
    return;
  }
  useStoryboardStore.getState().set({
    markingStatusSceneId: scene.client_id,
  });
  try {
    await axios.patch(`${ADMIN_API_BASE}/activity-logs/${scene.activity_log_id}/status`, {
      status: "success",
    });
    showToast("Marked as success", "success");
  } catch {
    showToast("Failed to mark status", "error");
  } finally {
    useStoryboardStore.getState().set({ markingStatusSceneId: null });
  }
}

export async function handleMarkFail(scene: Scene) {
  const { showToast } = useUIStore.getState();
  if (!scene.activity_log_id) {
    showToast("No generation log to mark", "error");
    return;
  }
  useStoryboardStore.getState().set({
    markingStatusSceneId: scene.client_id,
  });
  try {
    await axios.patch(`${ADMIN_API_BASE}/activity-logs/${scene.activity_log_id}/status`, {
      status: "fail",
    });
    showToast("Marked as fail", "error");
  } catch {
    showToast("Failed to mark status", "error");
  } finally {
    useStoryboardStore.getState().set({ markingStatusSceneId: null });
  }
}

