import axios from "axios";
import type { Scene, GeminiSuggestion } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { buildScenePrompt, buildNegativePrompt } from "./promptActions";
import { resolveCharacterIdForSpeaker } from "../../utils/speakerResolver";
import {
  resolveSceneControlnet,
  resolveSceneIpAdapter,
  resolveSceneMultiGen,
} from "../../utils/sceneSettingsResolver";
import { autoSaveStoryboard, saveStoryboard } from "./storyboardActions";

// Debounced save to prevent concurrent requests during batch generation
let saveTimeout: NodeJS.Timeout | null = null;
function debouncedSaveStoryboard() {
  if (saveTimeout) clearTimeout(saveTimeout);
  saveTimeout = setTimeout(async () => {
    console.log("[debouncedSave] Executing saveStoryboard...");
    const saved = await saveStoryboard();
    console.log("[debouncedSave] saveStoryboard result:", saved);
  }, 1000); // Wait 1s after last image generation
}

/** Store a base64 image on the backend and return URL + asset_id */
export async function storeSceneImage(
  dataUrl: string,
  projectId: number,
  groupId: number,
  storyboardId: number,
  sceneId: number,
  fileName?: string
): Promise<{ url: string; asset_id?: number }> {
  if (!dataUrl || !dataUrl.startsWith("data:")) return { url: dataUrl };
  try {
    const res = await fetch(`${API_BASE}/image/store`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_b64: dataUrl,
        project_id: projectId,
        group_id: groupId,
        storyboard_id: storyboardId,
        scene_id: sceneId,
        file_name: fileName,
      }),
    });
    if (!res.ok) return { url: dataUrl };
    const data = await res.json();
    return {
      url: (data?.url as string) ?? dataUrl,
      asset_id: data?.asset_id as number | undefined,
    };
  } catch {
    return { url: dataUrl };
  }
}

function buildHiResPayload() {
  const { hiResEnabled } = useStoryboardStore.getState();
  return hiResEnabled
    ? {
        enable_hr: true,
        hr_scale: 1.5,
        hr_upscaler: "R-ESRGAN 4x+ Anime6B",
        hr_second_pass_steps: 10,
        denoising_strength: 0.35,
      }
    : {};
}

/** Generate a single image for a scene via SD */
export async function generateSceneImageFor(
  scene: Scene,
  silent = false
): Promise<Partial<Scene> | null> {
  const sbState = useStoryboardStore.getState();
  const { autoComposePrompt } = sbState;
  const { storyboardId } = useContextStore.getState();
  const { showToast } = useUIStore.getState();
  const selectedCharacterId = resolveCharacterIdForSpeaker(scene.speaker, sbState);
  const controlnet = resolveSceneControlnet(scene, sbState);
  const ipAdapter = resolveSceneIpAdapter(scene, sbState);
  // Narrator scenes don't require character selection (no_humans, scenery only)
  if (!selectedCharacterId && scene.speaker !== "Narrator") {
    if (!silent) showToast("Character selection is required", "error");
    return null;
  }

  const prompt = await buildScenePrompt(scene);
  if (!prompt) {
    if (!silent) showToast("Prompt is required", "error");
    return null;
  }

  const negativePrompt = buildNegativePrompt(scene);
  // Gender enhancement is now handled by V3 backend engine

  // Pre-generation validation
  try {
    const validateRes = await axios.post(
      `${API_BASE}/prompt/validate`,
      {
        positive: prompt,
        negative: negativePrompt,
      },
      { timeout: API_TIMEOUT.DEFAULT }
    );
    const validation = validateRes.data;
    if (validation.errors?.length > 0) {
      if (!silent) showToast(validation.errors.join("; "), "error");
      return null;
    }
    if (validation.warnings?.length > 0 && !silent) {
      showToast(validation.warnings.join("; "), "error");
    }
  } catch {
    // continue
  }

  const hiResPayload = buildHiResPayload();
  // Narrator scenes: disable ControlNet (no character to pose) and IP-Adapter (no reference)
  const isNarrator = scene.speaker === "Narrator";
  const controlnetPayload =
    controlnet.enabled && !isNarrator
      ? { use_controlnet: true, controlnet_weight: controlnet.weight }
      : { use_controlnet: false };
  const ipAdapterPayload =
    ipAdapter.enabled && ipAdapter.reference && !isNarrator
      ? {
          use_ip_adapter: true,
          ip_adapter_reference: ipAdapter.reference,
          ip_adapter_weight: ipAdapter.weight,
        }
      : { use_ip_adapter: false };

  const debugPayload = {
    prompt,
    negative_prompt: negativePrompt,
    width: 512,
    height: 768,
    ...hiResPayload,
    ...controlnetPayload,
    ...ipAdapterPayload,
    character_id: selectedCharacterId,
    style_loras: sbState.characterLoras || [],
  };

  try {
    const res = await axios.post(
      `${API_BASE}/scene/generate`,
      {
        ...debugPayload,
        character_id: selectedCharacterId,
        character_b_id: sbState.selectedCharacterBId || undefined,
        storyboard_id: storyboardId,
        scene_id: scene.id > 0 ? scene.id : undefined,
        prompt_pre_composed: autoComposePrompt && !!selectedCharacterId,
      },
      { timeout: API_TIMEOUT.IMAGE_GENERATION }
    );
    const images = res.data.images || (res.data.image ? [res.data.image] : []);
    const warnings = res.data.warnings || [];

    if (!silent && warnings.length > 0) {
      warnings.forEach((msg: string) => showToast(msg, "success")); // Use success color for informational unpin
    }

    if (images.length > 0) {
      const { projectId, groupId, storyboardId: currentId } = useContextStore.getState();

      if (!projectId || !groupId || !currentId) {
        if (!silent) showToast("Project/Group context required", "error");
        return null;
      }

      // 1. Store all images in parallel
      const storedResults = await Promise.all(
        images.map((b64: string, idx: number) => {
          const dataUrl = `data:image/png;base64,${b64}`;
          return storeSceneImage(
            dataUrl,
            projectId,
            groupId,
            currentId,
            scene.id,
            `scene_${scene.id}_${Date.now()}_${idx}.png`
          );
        })
      );

      // 2. Validate all images to find the best match (Candidates creation)
      // Parallel validation for performance
      const validationResults = await Promise.all(
        storedResults.map(async (stored) => {
          const validation = await validateImageCandidate(stored.url, prompt, scene.id);
          return {
            image_url: stored.url,
            asset_id: stored.asset_id,
            match_rate: typeof validation?.match_rate === "number" ? validation.match_rate : 0,
            validation: validation, // Store full validation result for caching
          };
        })
      );

      // 3. Sort by match_rate descending (Best first)
      const sortedCandidates = validationResults.sort((a, b) => b.match_rate - a.match_rate);

      const bestCandidate = sortedCandidates[0];
      const mainImageUrl = bestCandidate.image_url;
      const bestAssetId = bestCandidate.asset_id;
      const candidates = sortedCandidates.map((c) => ({
        media_asset_id: c.asset_id!,
        match_rate: c.match_rate ?? undefined,
        image_url: c.image_url, // UI display
      }));

      // Update validation results cache in store for the best image
      if (bestCandidate.validation) {
        const { imageValidationResults } = useStoryboardStore.getState();
        useStoryboardStore.getState().set({
          imageValidationResults: {
            ...imageValidationResults,
            [scene.id]: bestCandidate.validation,
          },
        });
      }

      // Activity log (log the best image)
      let activityLogId: number | undefined;
      try {
        const currentStoryboardId = useContextStore.getState().storyboardId;

        if (!currentStoryboardId) {
          console.warn("[Activity Log] Skipping: storyboardId is required");
        } else {
          const logRes = await axios.post(`${API_BASE}/activity-logs`, {
            storyboard_id: currentStoryboardId,
            scene_id: scene.id,
            character_id: selectedCharacterId || undefined,
            prompt,
            negative_prompt: negativePrompt,
            tags: prompt.split(",").map((t: string) => t.trim()),
            sd_params: {},
            seed: -1,
            status: "pending",
            image_url: mainImageUrl?.startsWith("data:") ? null : (mainImageUrl ?? null),
            match_rate: bestCandidate.match_rate || null, // Use the best match rate
          });
          activityLogId = logRes.data.id;
        }
      } catch {
        // non-critical
      }

      return {
        image_url: mainImageUrl,
        image_asset_id: bestAssetId ?? null,
        candidates: candidates,
        image_prompt:
          autoComposePrompt && selectedCharacterId ? prompt : res.data.used_prompt || undefined,
        debug_prompt: prompt,
        debug_payload: JSON.stringify(debugPayload, null, 2),
        activity_log_id: activityLogId,
      } as Partial<Scene>;
    }
    return {
      image_prompt:
        autoComposePrompt && selectedCharacterId ? prompt : res.data.used_prompt || undefined,
      debug_prompt: prompt,
      debug_payload: JSON.stringify(debugPayload, null, 2),
    } as Partial<Scene>;
  } catch {
    if (!silent) showToast("Scene image generation failed", "error");
    return null;
  }
}

async function validateImageCandidate(imageUrl: string, prompt: string, sceneId?: number) {
  if (!imageUrl || imageUrl.startsWith("data:")) return null;
  try {
    const { storyboardId } = useContextStore.getState();
    const payload =
      imageUrl.startsWith("http://") || imageUrl.startsWith("https://")
        ? { image_url: imageUrl, prompt, storyboard_id: storyboardId, scene_id: sceneId }
        : { image_b64: imageUrl, prompt, storyboard_id: storyboardId, scene_id: sceneId };
    const res = await axios.post(`${API_BASE}/scene/validate-and-auto-edit`, payload);
    return res.data;
  } catch {
    return null;
  }
}

/** Generate 3 candidates and pick the best by match rate */
export async function generateSceneCandidates(
  scene: Scene,
  silent = false
): Promise<Partial<Scene> | null> {
  const sbState = useStoryboardStore.getState();
  const { autoComposePrompt } = sbState;
  const selectedCharacterId = resolveCharacterIdForSpeaker(scene.speaker, sbState);
  const prompt = await buildScenePrompt(scene);
  if (!prompt) {
    if (!silent) useUIStore.getState().showToast("Prompt is required", "error");
    return null;
  }

  const candidates: Array<{
    media_asset_id: number;
    match_rate?: number;
    image_url?: string;
  }> = [];
  let resolvedImagePrompt: string | undefined;
  for (let i = 0; i < 3; i += 1) {
    const result = await generateSceneImageFor(scene, true);
    if (!result?.image_url || !result?.image_asset_id) continue;
    if (!resolvedImagePrompt && result.image_prompt) {
      resolvedImagePrompt = result.image_prompt;
    }
    const validation = await validateImageCandidate(result.image_url, prompt, scene.id);
    candidates.push({
      media_asset_id: result.image_asset_id,
      match_rate: typeof validation?.match_rate === "number" ? validation.match_rate : 0,
      image_url: result.image_url, // UI display
    });
  }
  if (!candidates.length) return null;

  const best = [...candidates].sort((a, b) => (b.match_rate ?? 0) - (a.match_rate ?? 0))[0];

  if (best?.image_url) {
    const validation = await validateImageCandidate(best.image_url, prompt, scene.id);
    if (validation) {
      const { imageValidationResults } = useStoryboardStore.getState();
      useStoryboardStore.getState().set({
        imageValidationResults: {
          ...imageValidationResults,
          [scene.id]: validation,
        },
      });
    }
  }

  // best's image_asset_id
  const bestAssetId = best.media_asset_id;

  return {
    image_url: best.image_url,
    image_asset_id: bestAssetId,
    candidates,
    debug_prompt: prompt,
    image_prompt:
      resolvedImagePrompt || (autoComposePrompt && selectedCharacterId ? prompt : undefined),
  } as Partial<Scene>;
}

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

      // Auto-save after image generation to persist image_url to DB
      // Prevents image loss on page refresh
      // Debounce to prevent concurrent saves during batch generation
      console.log("[handleGenerateImage] Scheduling saveStoryboard...");
      debouncedSaveStoryboard();
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
