import axios from "axios";
import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";

/**
 * Auto-save storyboard before image generation
 * Ensures all activity logs have proper storyboard_id
 *
 * @returns storyboard_id if saved successfully, undefined otherwise
 */
export async function autoSaveStoryboard(): Promise<number | undefined> {
  const {
    storyboardId,
    scenes,
    topic,
    selectedCharacterId,
    setMeta,
    showToast,
  } = useStudioStore.getState();

  // Already saved
  if (storyboardId) {
    return storyboardId;
  }

  // No scenes to save
  if (scenes.length === 0) {
    return undefined;
  }

  try {
    const payload = {
      title: topic || "Draft Storyboard",
      description: topic || "Auto-saved before image generation",
      default_character_id: selectedCharacterId,
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
        steps: s.steps,
        cfg_scale: s.cfg_scale,
        sampler_name: s.sampler_name,
        seed: s.seed,
        clip_skip: s.clip_skip,
        context_tags: s.context_tags,
      })),
    };

    const res = await axios.post(`${API_BASE}/storyboards`, payload);
    const newStoryboardId = res.data.storyboard_id;

    setMeta({
      storyboardId: newStoryboardId,
      storyboardTitle: topic || "Draft Storyboard"
    });

    showToast("Storyboard auto-saved", "info");

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
  const {
    storyboardId,
    scenes,
    topic,
    selectedCharacterId,
    setMeta,
    showToast,
  } = useStudioStore.getState();

  if (scenes.length === 0) {
    showToast("No scenes to save", "error");
    return false;
  }

  try {
    const payload = {
      title: topic || "Untitled",
      description: topic,
      default_character_id: selectedCharacterId,
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
        steps: s.steps,
        cfg_scale: s.cfg_scale,
        sampler_name: s.sampler_name,
        seed: s.seed,
        clip_skip: s.clip_skip,
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
