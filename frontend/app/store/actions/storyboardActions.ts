import axios from "axios";
import { useContextStore } from "../useContextStore";
import { useStoryboardStore } from "../useStoryboardStore";
import { useRenderStore } from "../useRenderStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, API_TIMEOUT, DEFAULT_STRUCTURE } from "../../constants";
import { getErrorMsg } from "../../utils/error";
import type { Scene } from "../../types";
import { generateSceneClientId } from "../../utils/uuid";
import { buildScenesPayload } from "../../utils/buildScenesPayload";

/**
 * Sync storyboard version from server after 409 Conflict.
 * Fetches latest version so next save attempt uses correct version.
 */
async function syncVersionAfterConflict(): Promise<void> {
  const { storyboardId } = useContextStore.getState();
  if (!storyboardId) return;
  try {
    const res = await axios.get(`${API_BASE}/storyboards/${storyboardId}`);
    useStoryboardStore.getState().set({ storyboardVersion: res.data.version ?? null });
  } catch {
    // Silently fail — user already sees conflict toast
  }
}

// Re-export sanitizeCandidatesForDb for backward compatibility (canonical source: utils/buildScenesPayload)
export { sanitizeCandidatesForDb } from "../../utils/buildScenesPayload";

/**
 * Auto-save storyboard before image generation
 * Ensures all activity logs have proper storyboard_id
 *
 * @returns storyboard_id if saved successfully, undefined otherwise
 */
export async function autoSaveStoryboard(): Promise<number | undefined> {
  const ctxState = useContextStore.getState();
  const { showToast } = useUIStore.getState();
  const { storyboardId, groupId } = ctxState;

  // Already saved
  if (storyboardId) {
    return storyboardId;
  }

  // No scenes to save
  if (useStoryboardStore.getState().scenes.length === 0) {
    return undefined;
  }

  if (!groupId) {
    showToast("Create a group to save your storyboard", "error");
    return undefined;
  }

  try {
    const sbState = useStoryboardStore.getState();
    const { topic, scenes } = sbState;
    const {
      selectedCharacterId,
      selectedCharacterBId,
      structure,
      duration,
      language,
      description,
    } = sbState;
    const payload = {
      title: topic || "Draft Storyboard",
      description: description || null,
      group_id: groupId,
      structure: structure || DEFAULT_STRUCTURE,
      duration: duration || undefined,
      language: language || undefined,
      character_id: selectedCharacterId || undefined,
      character_b_id: selectedCharacterBId || undefined,
      casting_recommendation: sbState.castingRecommendation ?? undefined,
      scenes: buildScenesPayload(scenes),
    };

    const res = await axios.post(`${API_BASE}/storyboards`, payload, {
      timeout: API_TIMEOUT.STORYBOARD_SAVE,
    });
    const newStoryboardId = res.data.storyboard_id;
    const sceneIds = res.data.scene_ids || [];

    useContextStore.getState().setContext({
      storyboardId: newStoryboardId,
      storyboardTitle: topic || "Draft Storyboard",
    });

    // Atomic update: scenes + version + isDirty in one set() to avoid isDirty re-trigger
    const currentScenes = useStoryboardStore.getState().scenes;
    useStoryboardStore.getState().set({
      scenes:
        sceneIds.length > 0
          ? currentScenes.map((scene, idx) => ({ ...scene, id: sceneIds[idx] ?? scene.id }))
          : currentScenes,
      storyboardVersion: res.data.version ?? 1,
      isDirty: false,
    });

    // Sync URL with newly created storyboard ID & clear new mode
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("new");
      url.searchParams.set("id", String(newStoryboardId));
      window.history.replaceState({}, "", url.toString());
    }
    useUIStore.getState().set({ isNewStoryboardMode: false });

    showToast("Storyboard auto-saved", "success");

    return newStoryboardId;
  } catch (error) {
    console.error("[autoSaveStoryboard] Failed:", error);
    showToast("Auto-save failed", "error");
    return undefined;
  }
}

/**
 * Manually save or update storyboard (with toast feedback).
 * Used by Studio save button.
 */
export async function saveStoryboard(): Promise<boolean> {
  const { scenes } = useStoryboardStore.getState();
  const { groupId, storyboardId } = useContextStore.getState();
  const { showToast } = useUIStore.getState();

  if (scenes.length === 0) {
    showToast("No scenes to save", "error");
    return false;
  }
  if (!groupId) {
    showToast("Create a group to save your storyboard", "error");
    return false;
  }

  const ok = await persistStoryboard();
  if (ok) {
    showToast(storyboardId ? "Storyboard updated" : "Storyboard saved", "success");
  } else {
    showToast("Failed to save storyboard", "error");
  }
  return ok;
}

/**
 * Map raw Gemini API scene response to typed Scene array.
 * Single source of truth for Gemini -> Scene mapping.
 */
export function mapGeminiScenes(
  rawScenes: Record<string, unknown>[],
  baseNegative: string
): Scene[] {
  return rawScenes.map((s, i) => {
    const sceneNegative = (s.negative_prompt as string) || "";
    const combined = [baseNegative, sceneNegative].filter(Boolean).join(", ").trim();

    return {
      id: 0,
      client_id: generateSceneClientId(),
      order: i,
      script: (s.script as string) || "",
      speaker: ((s.speaker as string) || "Narrator") as Scene["speaker"],
      duration: (s.duration as number) || 3,
      image_prompt: (s.image_prompt as string) || "",
      image_prompt_ko: (s.image_prompt_ko as string) || "",
      image_url: null,
      width: 512,
      height: 768,
      negative_prompt: combined,
      context_tags: (s.context_tags as Scene["context_tags"]) || undefined,
      character_actions: (s.character_actions as Scene["character_actions"]) || undefined,
      use_controlnet: (s.use_controlnet as boolean) ?? undefined,
      controlnet_weight: (s.controlnet_weight as number) ?? undefined,
      controlnet_pose: (s.controlnet_pose as string) ?? undefined,
      use_ip_adapter: (s.use_ip_adapter as boolean) ?? undefined,
      ip_adapter_weight: (s.ip_adapter_weight as number) ?? undefined,
      multi_gen_enabled: (s.multi_gen_enabled as boolean) ?? undefined,
      voice_design_prompt: (s.voice_design_prompt as string) ?? undefined,
      head_padding: (s.head_padding as number) ?? undefined,
      tail_padding: (s.tail_padding as number) ?? undefined,
      ken_burns_preset: (s.ken_burns_preset as string) ?? undefined,
      isGenerating: false,
      debug_payload: "",
      _auto_pin_previous: (s._auto_pin_previous as boolean) ?? false,
    };
  });
}

/**
 * Detect whether scene data changed between two snapshots.
 * Used to keep isDirty = true when image generation completes during a save.
 */
function didScenesChangeDuringSave(before: Scene[], after: Scene[]): boolean {
  if (before.length !== after.length) return true;
  return after.some((scene, idx) => {
    const prev = before[idx];
    if (!prev || scene.client_id !== prev.client_id) return true;
    return (
      scene.image_asset_id !== prev.image_asset_id ||
      scene.image_url !== prev.image_url ||
      scene.image_prompt !== prev.image_prompt ||
      scene.script !== prev.script ||
      scene.negative_prompt !== prev.negative_prompt ||
      scene.candidates !== prev.candidates
    );
  });
}

/**
 * Silently persist storyboard to DB (no toast).
 * Used by autopilot and internal flows.
 * PUT if storyboardId exists, POST otherwise (with scene ID reassignment).
 */
export async function persistStoryboard(): Promise<boolean> {
  const ctxState = useContextStore.getState();
  const { storyboardId, groupId } = ctxState;

  if (useStoryboardStore.getState().scenes.length === 0 || !groupId) return false;

  try {
    const sbState = useStoryboardStore.getState();
    const { videoCaption, bgmPrompt, bgmMood } = useRenderStore.getState();
    const {
      scenes,
      topic,
      selectedCharacterId,
      selectedCharacterBId,
      structure,
      duration,
      language,
      description,
    } = sbState;

    // Snapshot before save — compare after PUT to detect changes during flight
    const scenesBeforeSave = scenes;

    const payload = {
      title: topic || "Untitled",
      description: description || null,
      group_id: groupId,
      structure: structure || DEFAULT_STRUCTURE,
      duration: duration || undefined,
      language: language || undefined,
      caption: videoCaption || null,
      character_id: selectedCharacterId || undefined,
      character_b_id: selectedCharacterBId || undefined,
      version: sbState.storyboardVersion ?? undefined,
      bgm_prompt: bgmPrompt || undefined,
      bgm_mood: bgmMood || undefined,
      casting_recommendation: sbState.castingRecommendation ?? undefined,
      scenes: buildScenesPayload(scenes),
    };

    if (storyboardId) {
      // PUT also returns scene_ids since scenes are deleted and recreated
      const res = await axios.put(`${API_BASE}/storyboards/${storyboardId}`, payload, {
        timeout: API_TIMEOUT.STORYBOARD_SAVE,
      });
      const sceneIds: number[] = res.data.scene_ids || [];
      const scenesAfterSave = useStoryboardStore.getState().scenes;
      const changedDuringSave = didScenesChangeDuringSave(scenesBeforeSave, scenesAfterSave);
      useStoryboardStore.getState().set({
        scenes:
          sceneIds.length > 0
            ? scenesAfterSave.map((scene, idx) => ({ ...scene, id: sceneIds[idx] ?? scene.id }))
            : scenesAfterSave,
        storyboardVersion: res.data.version,
        isDirty: changedDuringSave,
      });
    } else {
      const res = await axios.post(`${API_BASE}/storyboards`, payload, {
        timeout: API_TIMEOUT.STORYBOARD_SAVE,
      });
      const newId = res.data.storyboard_id;
      const sceneIds: number[] = res.data.scene_ids || [];
      useContextStore.getState().setContext({ storyboardId: newId, storyboardTitle: topic });
      const scenesAfterSave = useStoryboardStore.getState().scenes;
      const changedDuringSave = didScenesChangeDuringSave(scenesBeforeSave, scenesAfterSave);
      useStoryboardStore.getState().set({
        scenes:
          sceneIds.length > 0
            ? scenesAfterSave.map((scene, idx) => ({ ...scene, id: sceneIds[idx] ?? scene.id }))
            : scenesAfterSave,
        storyboardVersion: res.data.version ?? 1,
        isDirty: changedDuringSave,
      });
      // Sync URL with newly created storyboard ID & clear new mode
      if (typeof window !== "undefined") {
        const url = new URL(window.location.href);
        url.searchParams.delete("new");
        url.searchParams.set("id", String(newId));
        window.history.replaceState({}, "", url.toString());
      }
      useUIStore.getState().set({ isNewStoryboardMode: false });
    }
    return true;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      useUIStore.getState().showToast("다른 탭에서 수정되었습니다. 다시 저장해주세요.", "error");
      await syncVersionAfterConflict();
      return false;
    }
    console.error("[persistStoryboard] Failed:", error);
    return false;
  }
}

/**
 * Partially update storyboard metadata (title, caption, etc) in DB.
 */
export async function updateStoryboardMetadata(updates: {
  title?: string;
  description?: string;
  caption?: string | null;
}): Promise<boolean> {
  const { storyboardId } = useContextStore.getState();
  const { showToast } = useUIStore.getState();
  const { storyboardVersion } = useStoryboardStore.getState();

  if (!storyboardId) return false;

  try {
    const res = await axios.patch(`${API_BASE}/storyboards/${storyboardId}/metadata`, {
      ...updates,
      version: storyboardVersion ?? undefined,
    });
    // Update version from response
    if (res.data?.version != null) {
      useStoryboardStore.getState().set({ storyboardVersion: res.data.version });
    }
    return true;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      showToast("다른 탭에서 수정되었습니다. 다시 저장해주세요.", "error");
      await syncVersionAfterConflict();
      return false;
    }
    console.error("[updateStoryboardMetadata] Failed:", error);
    showToast("Failed to update metadata", "error");
    return false;
  }
}

/**
 * Generate storyboard via Gemini API and populate scenes.
 * Returns "needs_confirm" if existing scenes would be replaced (caller should confirm).
 * Pass force=true to skip the check.
 */
export async function generateStoryboard(force = false): Promise<boolean | "needs_confirm"> {
  const sbState = useStoryboardStore.getState();
  const { showToast, setActiveTab } = useUIStore.getState();
  const {
    scenes: existingScenes,
    topic,
    description,
    duration,
    style,
    language,
    structure,
    actorAGender,
    selectedCharacterId,
    selectedCharacterBId,
    baseNegativePromptA,
    setScenes,
  } = sbState;

  if (!topic.trim()) {
    showToast("Enter a topic first", "error");
    return false;
  }

  if (!force && existingScenes.length > 0) {
    return "needs_confirm";
  }

  try {
    const structureLower = structure.toLowerCase();
    const hasCharacterB = structureLower === "dialogue" || structureLower === "narrated dialogue";
    const res = await axios.post(`${API_BASE}/storyboards/create`, {
      topic,
      description: description || undefined,
      duration,
      style,
      language,
      structure,
      actor_a_gender: actorAGender,
      character_id: selectedCharacterId || undefined,
      character_b_id: hasCharacterB ? selectedCharacterBId || undefined : undefined,
    });

    const data = res.data;
    if (!data.scenes) return false;

    const mapped = mapGeminiScenes(data.scenes, baseNegativePromptA);

    setScenes(mapped);
    useStoryboardStore.getState().set({ currentSceneIndex: 0 });
    setActiveTab("direct");
    showToast(`Generated ${mapped.length} scenes`, "success");
    await saveStoryboard();
    return true;
  } catch (error) {
    showToast(getErrorMsg(error, "스토리보드 생성 실패"), "error");
    return false;
  }
}
