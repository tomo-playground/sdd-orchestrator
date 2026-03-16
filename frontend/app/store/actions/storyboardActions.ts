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

/** Sync storyboard version from server after 409 Conflict. */
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

export { sanitizeCandidatesForDb } from "../../utils/buildScenesPayload";

/** Sync URL and new mode flag after storyboard creation. */
function syncUrlAfterCreate(newId: number): void {
  if (typeof window !== "undefined") {
    const url = new URL(window.location.href);
    url.searchParams.delete("new");
    url.searchParams.set("id", String(newId));
    window.history.replaceState({}, "", url.toString());
  }
  useUIStore.getState().set({ isNewStoryboardMode: false });
}

/** Apply save response: update scene IDs, version, and dirty flag in one atomic set(). */
function applySaveResult(
  scenesBeforeSave: Scene[],
  data: { scene_ids?: number[]; version?: number },
  forceClean = false
): void {
  const sceneIds: number[] = data.scene_ids || [];
  const scenesAfterSave = useStoryboardStore.getState().scenes;
  useStoryboardStore.getState().set({
    scenes:
      sceneIds.length > 0
        ? scenesAfterSave.map((scene, idx) => ({ ...scene, id: sceneIds[idx] ?? scene.id }))
        : scenesAfterSave,
    storyboardVersion: data.version ?? 1,
    isDirty: forceClean ? false : didScenesChangeDuringSave(scenesBeforeSave, scenesAfterSave),
  });
}

/** Detect scene changes during save flight to preserve isDirty accurately. */
function didScenesChangeDuringSave(before: Scene[], after: Scene[]): boolean {
  if (before === after) return false;
  if (before.length !== after.length) return true;
  return after.some((scene, idx) => {
    const prev = before[idx];
    if (scene === prev) return false;
    if (!prev || scene.client_id !== prev.client_id) return true;
    return (
      scene.image_asset_id !== prev.image_asset_id ||
      scene.image_url !== prev.image_url ||
      scene.image_prompt !== prev.image_prompt ||
      scene.script !== prev.script ||
      scene.negative_prompt !== prev.negative_prompt ||
      scene.environment_reference_id !== prev.environment_reference_id ||
      scene.background_id !== prev.background_id ||
      scene.voice_design_prompt !== prev.voice_design_prompt ||
      scene.ken_burns_preset !== prev.ken_burns_preset ||
      scene.head_padding !== prev.head_padding ||
      scene.tail_padding !== prev.tail_padding ||
      // Object/array fields: reference check + deep fallback (prevent false positives)
      (scene.context_tags !== prev.context_tags &&
        JSON.stringify(scene.context_tags) !== JSON.stringify(prev.context_tags)) ||
      (scene.candidates !== prev.candidates &&
        JSON.stringify(scene.candidates) !== JSON.stringify(prev.candidates))
    );
  });
}

/**
 * Auto-save storyboard before image generation.
 * Returns storyboard_id if saved, undefined otherwise.
 */
export async function autoSaveStoryboard(): Promise<number | undefined> {
  const { storyboardId, groupId } = useContextStore.getState();
  const { showToast } = useUIStore.getState();

  if (storyboardId) return storyboardId;
  if (useStoryboardStore.getState().scenes.length === 0) return undefined;
  if (!groupId) {
    showToast("Create a group to save your storyboard", "error");
    return undefined;
  }

  try {
    const sbState = useStoryboardStore.getState();
    const {
      topic,
      scenes,
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
      casting_recommendation: sbState.castingRecommendation ?? null,
      scenes: buildScenesPayload(scenes),
    };

    const res = await axios.post(`${API_BASE}/storyboards`, payload, {
      timeout: API_TIMEOUT.STORYBOARD_SAVE,
    });
    const newStoryboardId = res.data.storyboard_id;
    useContextStore.getState().setContext({
      storyboardId: newStoryboardId,
      storyboardTitle: topic || "Draft Storyboard",
    });
    applySaveResult(scenes, res.data, true);
    syncUrlAfterCreate(newStoryboardId);
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
 * Spread passthrough: Gemini 출력 필드를 그대로 전달하고, 고정값/합성값만 오버라이드.
 */
export function mapGeminiScenes(
  rawScenes: Record<string, unknown>[],
  baseNegative: string
): Scene[] {
  return rawScenes.map((s, i) => {
    const sceneNegative = (s.negative_prompt as string) || "";
    const combined = [baseNegative, sceneNegative].filter(Boolean).join(", ").trim();

    return {
      ...(s as unknown as Scene),
      id: 0,
      client_id: generateSceneClientId(),
      order: i,
      image_url: null,
      // Backend SSOT: config.py SD_DEFAULT_WIDTH=832, SD_DEFAULT_HEIGHT=1216
      width: 832,
      height: 1216,
      script: (s.script as string) || "",
      speaker: ((s.speaker as string) || "Narrator") as Scene["speaker"],
      duration: (s.duration as number) || 3,
      image_prompt: (s.image_prompt as string) || "",
      image_prompt_ko: (s.image_prompt_ko as string) || "",
      negative_prompt: combined,
      isGenerating: false,
      debug_payload: "",
      _auto_pin_previous: (s._auto_pin_previous as boolean) ?? false,
    };
  });
}

/**
 * Silently persist storyboard to DB (no toast).
 * PUT if storyboardId exists, POST otherwise.
 */
export async function persistStoryboard(retrying = false): Promise<boolean> {
  const { storyboardId, groupId } = useContextStore.getState();
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
      casting_recommendation: sbState.castingRecommendation ?? null,
      scenes: buildScenesPayload(scenes),
    };

    if (storyboardId) {
      const res = await axios.put(`${API_BASE}/storyboards/${storyboardId}`, payload, {
        timeout: API_TIMEOUT.STORYBOARD_SAVE,
      });
      applySaveResult(scenesBeforeSave, res.data);
    } else {
      const res = await axios.post(`${API_BASE}/storyboards`, payload, {
        timeout: API_TIMEOUT.STORYBOARD_SAVE,
      });
      const newId = res.data.storyboard_id;
      useContextStore.getState().setContext({ storyboardId: newId, storyboardTitle: topic });
      applySaveResult(scenesBeforeSave, res.data);
      syncUrlAfterCreate(newId);
    }
    return true;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 409) {
      useUIStore.getState().showToast("다른 탭에서 수정되었습니다. 다시 저장해주세요.", "error");
      await syncVersionAfterConflict();
      return false;
    }
    if (axios.isAxiosError(error) && error.response?.status === 404 && !retrying) {
      console.warn("[persistStoryboard] 404 — stale storyboardId, retrying as new");
      useContextStore.getState().setContext({ storyboardId: null });
      if (typeof window !== "undefined") {
        const url = new URL(window.location.href);
        url.searchParams.delete("id");
        window.history.replaceState({}, "", url.toString());
      }
      return persistStoryboard(true);
    }
    console.error("[persistStoryboard] Failed:", error);
    useUIStore.getState().showToast("저장에 실패했습니다. 다시 시도해 주세요.", "error");
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
