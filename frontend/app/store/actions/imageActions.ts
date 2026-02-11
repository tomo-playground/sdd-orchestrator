import axios from "axios";
import type { Scene, GeminiSuggestion } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE } from "../../constants";
import { buildScenePrompt } from "./promptActions";
import { resolveSceneMultiGen } from "../../utils/sceneSettingsResolver";
import { autoSaveStoryboard, saveStoryboard } from "./storyboardActions";
import {
  storeSceneImage,
  generateSceneImageFor,
  generateSceneCandidates,
} from "./imageGeneration";

// Re-export for existing consumers
export { storeSceneImage, generateSceneImageFor, generateSceneCandidates };

/** Generate image for a scene (single or multi-gen) and update store */
export async function handleGenerateImage(scene: Scene) {
  const { updateScene, scenes } = useStoryboardStore.getState();
  const { showToast } = useUIStore.getState();
  const multiGenEnabled = resolveSceneMultiGen(scene, useStoryboardStore.getState());

  // Auto-save storyboard before image generation
  // Ensures activity logs have proper storyboard_id and scene IDs are assigned
  const storyboardId = await autoSaveStoryboard();
  if (!storyboardId) {
    showToast("Failed to save storyboard before generation", "error");
    return;
  }

  // Get updated scene with DB-assigned ID
  const updatedScene = scenes.find(
    (s) => s.id === scene.id || (s.script === scene.script && s.order === scene.order)
  );
  if (!updatedScene) {
    showToast("Scene not found after save", "error");
    return;
  }

  const sceneOrder = updatedScene.order;
  updateScene(updatedScene.id, { isGenerating: true });
  try {
    const result = multiGenEnabled
      ? await generateSceneCandidates(updatedScene)
      : await generateSceneImageFor(updatedScene);
    if (result) {
      console.log("[handleGenerateImage] Image generation result:", result);
      // Scene ID may have changed during generation (concurrent save -> ID reassignment).
      // Look up by order (stable) instead of stale captured ID.
      const currentScenes = useStoryboardStore.getState().scenes;
      const currentScene = currentScenes.find((s) => s.order === sceneOrder);
      const currentId = currentScene?.id ?? updatedScene.id;
      const { updateScene: liveUpdateScene } = useStoryboardStore.getState();

      // Include isGenerating: false before saveStoryboard to survive ID reassignment
      liveUpdateScene(currentId, { ...result, isGenerating: false });

      // Auto-pin: Apply environment reference if scene has _auto_pin_previous flag
      const { applyAutoPinAfterGeneration } = await import("../../utils/applyAutoPin");
      const autoPinResult = applyAutoPinAfterGeneration(
        useStoryboardStore.getState().scenes,
        currentId,
        liveUpdateScene
      );
      if (autoPinResult?.success) {
        console.log("[AutoPin]", autoPinResult.message);
        showToast(`Auto-pin: ${autoPinResult.message}`, "success");
      }

      // image_url is already persisted by POST /image/store (Backend commits scene.image_asset_id immediately)
    } else {
      console.warn("[handleGenerateImage] No result from image generation");
    }
  } finally {
    // Scene ID may have changed after saveStoryboard (ID reassignment).
    // Look up by order (stable) instead of old ID.
    const currentScenes = useStoryboardStore.getState().scenes;
    const targetScene = currentScenes.find((s) => s.order === sceneOrder);
    if (targetScene) {
      useStoryboardStore.getState().updateScene(targetScene.id, { isGenerating: false });
    }
  }
}

/** Upload a local file as a scene image */
export function handleImageUpload(sceneId: number, file?: File) {
  if (!file) return;
  const reader = new FileReader();
  reader.onloadend = async () => {
    const dataUrl = reader.result as string;
    const { projectId, groupId, storyboardId } = useContextStore.getState();
    const { showToast } = useUIStore.getState();
    const { scenes, updateScene } = useStoryboardStore.getState();
    if (!projectId || !groupId || !storyboardId) {
      showToast("Project/Group context required", "error");
      return;
    }
    const stored = await storeSceneImage(
      dataUrl,
      projectId,
      groupId,
      storyboardId,
      sceneId,
      `upload_${sceneId}_${Date.now()}.png`
    );
    updateScene(sceneId, {
      image_url: stored.url,
      image_asset_id: stored.asset_id ?? null,
      candidates: [],
    });

    // Auto-pin: Apply environment reference if scene has _auto_pin_previous flag
    const { applyAutoPinAfterGeneration } = await import("../../utils/applyAutoPin");
    const autoPinResult = applyAutoPinAfterGeneration(scenes, sceneId, updateScene);
    if (autoPinResult?.success) {
      console.log("[AutoPin]", autoPinResult.message);
      showToast(`Auto-pin: ${autoPinResult.message}`, "success");
    }

    // Auto-save after image upload to persist to DB
    await saveStoryboard();
  };
  reader.readAsDataURL(file);
}

/** Edit scene image with Gemini */
export async function handleEditWithGemini(scene: Scene, targetChange: string) {
  const { showToast } = useUIStore.getState();
  if (!scene.image_url) {
    showToast("No image to edit. Generate one first.", "error");
    return;
  }
  if (scene.image_url.startsWith("data:")) {
    showToast("Save the scene first (image must be stored).", "error");
    return;
  }
  const sceneOrder = scene.order;
  useStoryboardStore.getState().updateScene(scene.id, { isGenerating: true });
  try {
    const prompt = await buildScenePrompt(scene);
    if (!prompt) {
      showToast("Prompt build failed", "error");
      useStoryboardStore.getState().updateScene(scene.id, { isGenerating: false });
      return;
    }
    const payload =
      scene.image_url.startsWith("http://") || scene.image_url.startsWith("https://")
        ? { image_url: scene.image_url, original_prompt: prompt, target_change: targetChange }
        : { image_b64: scene.image_url, original_prompt: prompt, target_change: targetChange };
    const res = await axios.post(`${API_BASE}/scene/edit-with-gemini`, payload);
    if (res.data.edited_image) {
      const dataUrl = `data:image/png;base64,${res.data.edited_image}`;
      const { projectId, groupId, storyboardId } = useContextStore.getState();
      if (!projectId || !groupId || !storyboardId) {
        showToast("Project/Group context required", "error");
        useStoryboardStore.getState().updateScene(scene.id, { isGenerating: false });
        return;
      }
      // Re-lookup by order: scene IDs may have changed during Gemini API call
      const currentScenes = useStoryboardStore.getState().scenes;
      const currentScene = currentScenes.find((s) => s.order === sceneOrder);
      const currentId = currentScene?.id ?? scene.id;
      const stored = await storeSceneImage(
        dataUrl,
        projectId,
        groupId,
        storyboardId,
        currentId,
        `gemini_edit_${currentId}_${Date.now()}.png`
      );
      useStoryboardStore.getState().updateScene(currentId, {
        image_url: stored.url,
        image_asset_id: stored.asset_id ?? null,
        isGenerating: false,
      });
      showToast(
        `Gemini edit done (${res.data.edit_type}) - $${res.data.cost_usd.toFixed(4)}`,
        "success"
      );

      // Auto-save after Gemini edit to persist to DB
      await saveStoryboard();
    }
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    showToast(`Gemini edit failed: ${msg}`, "error");
    // Re-lookup by order for cleanup
    const currentScenes = useStoryboardStore.getState().scenes;
    const currentScene = currentScenes.find((s) => s.order === sceneOrder);
    const currentId = currentScene?.id ?? scene.id;
    useStoryboardStore.getState().updateScene(currentId, { isGenerating: false });
  }
}

/** Ask Gemini for edit suggestions */
export async function handleSuggestEditWithGemini(scene: Scene): Promise<GeminiSuggestion[]> {
  const { showToast } = useUIStore.getState();
  if (!scene.image_url) {
    showToast("No image. Generate one first.", "error");
    return [];
  }
  if (scene.image_url.startsWith("data:")) {
    showToast("Save the scene first (image must be stored).", "error");
    return [];
  }
  try {
    const prompt = await buildScenePrompt(scene);
    if (!prompt) {
      showToast("Prompt build failed", "error");
      return [];
    }
    const payload =
      scene.image_url.startsWith("http://") || scene.image_url.startsWith("https://")
        ? { image_url: scene.image_url, original_prompt: prompt }
        : { image_b64: scene.image_url, original_prompt: prompt };
    const res = await axios.post(`${API_BASE}/scene/suggest-edit`, payload);
    if (res.data.has_mismatch && res.data.suggestions?.length > 0) {
      showToast(
        `${res.data.suggestions.length} suggestions - $${res.data.cost_usd.toFixed(4)}`,
        "success"
      );
      return res.data.suggestions;
    }
    showToast("Image matches prompt well.", "success");
    return [];
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    showToast(`Suggest failed: ${msg}`, "error");
    return [];
  }
}
