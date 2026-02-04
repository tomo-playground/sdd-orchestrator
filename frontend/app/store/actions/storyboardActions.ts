import axios from "axios";
import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";
import type { Scene } from "../../types";

/**
 * Create a draft storyboard in DB immediately (empty scenes).
 * Called when user clicks "+New Story".
 *
 * @returns storyboard_id if created successfully, undefined otherwise
 */
export async function createDraftStoryboard(title?: string): Promise<number | undefined> {
  const { storyboardId, groupId, setMeta, showToast } = useStudioStore.getState();

  // Already exists
  if (storyboardId) return storyboardId;

  if (!groupId) return undefined;

  const storyTitle = title || "Draft Storyboard";

  try {
    const res = await axios.post(`${API_BASE}/storyboards`, {
      title: storyTitle,
      group_id: groupId,
      scenes: [],
    });
    const newId = res.data.storyboard_id;
    setMeta({ storyboardId: newId, storyboardTitle: storyTitle });
    if (title) {
      useStudioStore.getState().setPlan({ topic: title });
    }
    return newId;
  } catch (error) {
    console.error("[createDraftStoryboard] Failed:", error);
    showToast("Failed to create storyboard", "error");
    return undefined;
  }
}

/**
 * Auto-save storyboard before image generation
 * Ensures all activity logs have proper storyboard_id
 *
 * @returns storyboard_id if saved successfully, undefined otherwise
 */
export async function autoSaveStoryboard(): Promise<number | undefined> {
  const { storyboardId, groupId, scenes, topic, setMeta, showToast } = useStudioStore.getState();

  // Already saved
  if (storyboardId) {
    return storyboardId;
  }

  // No scenes to save
  if (scenes.length === 0) {
    return undefined;
  }

  if (!groupId) {
    showToast("Create a group to save your storyboard", "error");
    return undefined;
  }

  try {
    const payload = {
      title: topic || "Draft Storyboard",
      description: useStudioStore.getState().description || null,
      group_id: groupId,
      scenes: scenes.map((s, i) => ({
        scene_id: i,
        script: s.script,
        speaker: s.speaker,
        duration: s.duration,
        image_prompt: s.image_prompt,
        image_prompt_ko: s.image_prompt_ko,
        image_url: s.image_url,
        description: s.description,
        width: s.width || 512,
        height: s.height || 768,
        negative_prompt: s.negative_prompt,
        context_tags: s.context_tags,
      })),
    };

    const res = await axios.post(`${API_BASE}/storyboards`, payload);
    const newStoryboardId = res.data.storyboard_id;
    const sceneIds = res.data.scene_ids || [];

    setMeta({
      storyboardId: newStoryboardId,
      storyboardTitle: topic || "Draft Storyboard",
    });

    // Update scene IDs with DB-assigned IDs
    if (sceneIds.length > 0) {
      const { scenes: currentScenes, setScenes } = useStudioStore.getState();
      const updatedScenes = currentScenes.map((scene, idx) => ({
        ...scene,
        id: sceneIds[idx] || scene.id,
      }));
      setScenes(updatedScenes);
    }

    showToast("Storyboard auto-saved", "success");

    return newStoryboardId;
  } catch (error) {
    console.error("[autoSaveStoryboard] Failed:", error);
    showToast("Auto-save failed", "error");
    return undefined;
  }
}

/**
 * Manually save or update storyboard
 * Used by PlanTab save button
 */
export async function saveStoryboard(): Promise<boolean> {
  const { storyboardId, groupId, scenes, topic, videoCaption, setMeta, showToast } =
    useStudioStore.getState();

  if (scenes.length === 0) {
    showToast("No scenes to save", "error");
    return false;
  }

  if (!groupId) {
    showToast("Create a group to save your storyboard", "error");
    return false;
  }

  try {
    const payload = {
      title: topic || "Untitled",
      description: useStudioStore.getState().description || null,
      group_id: groupId,
      caption: videoCaption || null,
      scenes: scenes.map((s, i) => ({
        scene_id: i,
        script: s.script,
        speaker: s.speaker,
        duration: s.duration,
        image_prompt: s.image_prompt,
        image_prompt_ko: s.image_prompt_ko,
        image_url: s.image_url,
        description: s.description,
        width: s.width || 512,
        height: s.height || 768,
        negative_prompt: s.negative_prompt,
        context_tags: s.context_tags,
      })),
    };

    if (storyboardId) {
      await axios.put(`${API_BASE}/storyboards/${storyboardId}`, payload);
      showToast("Storyboard updated", "success");
    } else {
      const res = await axios.post(`${API_BASE}/storyboards`, payload);
      setMeta({ storyboardId: res.data.storyboard_id, storyboardTitle: topic });
      showToast("Storyboard saved", "success");
    }

    return true;
  } catch (error) {
    console.error("[saveStoryboard] Failed:", error);
    showToast("Failed to save storyboard", "error");
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
  const { storyboardId, showToast } = useStudioStore.getState();

  if (!storyboardId) return false;

  try {
    await axios.patch(`${API_BASE}/storyboards/${storyboardId}/metadata`, updates);
    return true;
  } catch (error) {
    console.error("[updateStoryboardMetadata] Failed:", error);
    showToast("Failed to update metadata", "error");
    return false;
  }
}

/**
 * Generate storyboard via Gemini API and populate scenes.
 * Switches to Scenes tab on success and auto-saves.
 */
export async function generateStoryboard(): Promise<boolean> {
  const state = useStudioStore.getState();
  const {
    topic,
    description,
    duration,
    style,
    language,
    structure,
    actorAGender,
    selectedCharacterId,
    baseNegativePromptA,
    setScenes,
    setActiveTab,
    showToast,
  } = state;

  if (!topic.trim()) {
    showToast("Enter a topic first", "error");
    return false;
  }

  try {
    const res = await axios.post(`${API_BASE}/storyboards/create`, {
      topic,
      description: description || undefined,
      duration,
      style,
      language,
      structure,
      actor_a_gender: actorAGender,
      character_id: selectedCharacterId || undefined,
    });

    const data = res.data;
    if (!data.scenes) return false;

    const mapped: Scene[] = data.scenes.map((s: Record<string, unknown>, i: number) => {
      const sceneNegative = (s.negative_prompt as string) || "";
      const combined = [baseNegativePromptA, sceneNegative].filter(Boolean).join(", ").trim();

      return {
        id: i,
        script: (s.script as string) || "",
        speaker: (s.speaker as string) || "Narrator",
        duration: (s.duration as number) || 3,
        image_prompt: (s.image_prompt as string) || "",
        image_prompt_ko: (s.image_prompt_ko as string) || "",
        image_url: null,
        description: (s.description as string) || "",
        width: 512,
        height: 768,
        negative_prompt: combined,
        isGenerating: false,
        debug_payload: "",
      };
    });

    setScenes(mapped);
    setActiveTab("scenes");
    showToast(`Generated ${mapped.length} scenes`, "success");
    saveStoryboard();
    return true;
  } catch {
    showToast("Failed to generate storyboard", "error");
    return false;
  }
}
