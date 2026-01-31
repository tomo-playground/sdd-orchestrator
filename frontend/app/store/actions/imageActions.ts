import axios from "axios";
import type { Scene } from "../../types";
import { useStudioStore } from "../useStudioStore";
import { API_BASE } from "../../constants";
import {
  splitPromptTokens,
  getGenderEnhancements,
} from "../../utils";
import {
  buildScenePrompt,
  buildNegativePrompt,
  getBasePromptForScene,
  buildPositivePrompt,
} from "./promptActions";
import { autoSaveStoryboard, saveStoryboard } from "./storyboardActions";

/** Store a base64 image on the backend and return a URL */
export async function storeSceneImage(
  dataUrl: string,
  projectId: number,
  groupId: number,
  storyboardId: number,
  sceneId: number,
  fileName?: string
): Promise<string> {
  if (!dataUrl || !dataUrl.startsWith("data:")) return dataUrl;
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
    if (!res.ok) return dataUrl;
    const data = await res.json();
    return (data?.url as string) ?? dataUrl;
  } catch {
    return dataUrl;
  }
}

function buildHiResPayload() {
  const { hiResEnabled } = useStudioStore.getState();
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
  const {
    autoComposePrompt,
    useControlnet,
    controlnetWeight,
    useIpAdapter,
    ipAdapterReference,
    ipAdapterWeight,
    selectedCharacterId,
    storyboardId,
    showToast,
  } = useStudioStore.getState();

  const prompt = await buildScenePrompt(scene);
  if (!prompt) {
    if (!silent) showToast("Prompt is required", "error");
    return null;
  }

  let negativePrompt = buildNegativePrompt(scene);

  // Gender enhancement negative tags
  const basePrompt = getBasePromptForScene(scene);
  const baseTokens = basePrompt ? splitPromptTokens(basePrompt) : [];
  const genderEnhancements = getGenderEnhancements(baseTokens);
  if (genderEnhancements.negative.length > 0) {
    const extra = genderEnhancements.negative.join(", ");
    negativePrompt = negativePrompt ? `${negativePrompt}, ${extra}` : extra;
  }

  // Pre-generation validation
  try {
    const validateRes = await axios.post(`${API_BASE}/prompt/validate`, {
      positive: prompt,
      negative: negativePrompt,
    });
    const validation = validateRes.data;
    if (validation.errors?.length > 0) {
      if (!silent) showToast(`Blocked: ${validation.errors.join("; ")}`, "error");
      return null;
    }
    if (validation.warnings?.length > 0 && !silent) {
      showToast(`Warning: ${validation.warnings.join("; ")}`, "error");
    }
  } catch {
    // continue
  }

  const hiResPayload = buildHiResPayload();
  const controlnetPayload = useControlnet
    ? { use_controlnet: true, controlnet_weight: controlnetWeight }
    : { use_controlnet: false };
  const ipAdapterPayload =
    useIpAdapter && ipAdapterReference
      ? {
        use_ip_adapter: true,
        ip_adapter_reference: ipAdapterReference,
        ip_adapter_weight: ipAdapterWeight,
      }
      : { use_ip_adapter: false };

  const debugPayload = {
    prompt,
    negative_prompt: negativePrompt,
    steps: scene.steps,
    cfg_scale: scene.cfg_scale,
    sampler_name: scene.sampler_name,
    seed: scene.seed,
    clip_skip: scene.clip_skip,
    width: 512,
    height: 768,
    ...hiResPayload,
    ...controlnetPayload,
    ...ipAdapterPayload,
    ...(selectedCharacterId ? { character_id: selectedCharacterId } : {}),
  };

  try {
    const res = await axios.post(`${API_BASE}/scene/generate`, {
      ...debugPayload,
      character_id: selectedCharacterId,
      storyboard_id: storyboardId,
    });
    const images = res.data.images || (res.data.image ? [res.data.image] : []);
    const warnings = res.data.warnings || [];

    if (!silent && warnings.length > 0) {
      warnings.forEach((msg: string) => showToast(msg, "success")); // Use success color for informational unpin
    }

    if (images.length > 0) {
      const { projectId, groupId, storyboardId: currentId } = useStudioStore.getState();

      // 1. Store all images in parallel
      const storedUrls = await Promise.all(
        images.map((b64: string, idx: number) => {
          const dataUrl = `data:image/png;base64,${b64}`;
          return storeSceneImage(
            dataUrl,
            projectId || 1,
            groupId || 1,
            currentId || 1,
            scene.id,
            `scene_${scene.id}_${Date.now()}_${idx}.png`
          );
        })
      );

      // 2. Validate all images to find the best match (Candidates creation)
      // Parallel validation for performance
      const validationResults = await Promise.all(
        storedUrls.map(async (url) => {
          const validation = await validateImageCandidate(url, prompt, scene.id);
          return {
            image_url: url,
            match_rate: typeof validation?.match_rate === "number" ? validation.match_rate : 0,
            validation: validation, // Store full validation result for caching
          };
        })
      );

      // 3. Sort by match_rate descending (Best first)
      const sortedCandidates = validationResults.sort(
        (a, b) => b.match_rate - a.match_rate
      );

      const bestCandidate = sortedCandidates[0];
      const mainImageUrl = bestCandidate.image_url;
      const candidates = sortedCandidates.map(c => ({ image_url: c.image_url }));

      // Update validation results cache in store for the best image
      if (bestCandidate.validation) {
        const { imageValidationResults } = useStudioStore.getState();
        useStudioStore.getState().setScenesState({
          imageValidationResults: {
            ...imageValidationResults,
            [scene.id]: bestCandidate.validation,
          },
        });
      }

      // Activity log (log the best image)
      let activityLogId: number | undefined;
      try {
        const currentStoryboardId = useStudioStore.getState().storyboardId;

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
            sd_params: {
              steps: scene.steps,
              cfg_scale: scene.cfg_scale,
              sampler_name: scene.sampler_name,
              clip_skip: scene.clip_skip,
            },
            seed: scene.seed,
            status: "pending",
            image_url: mainImageUrl, // Use the best image
            match_rate: bestCandidate.match_rate || null, // Use the best match rate
          });
          activityLogId = logRes.data.id;
        }
      } catch {
        // non-critical
      }

      return {
        image_url: mainImageUrl,
        candidates: candidates,
        image_prompt: autoComposePrompt ? prompt : undefined,
        debug_prompt: prompt,
        debug_payload: JSON.stringify(debugPayload, null, 2),
        activity_log_id: activityLogId,
      } as Partial<Scene>;
    }
    return {
      image_prompt: autoComposePrompt ? prompt : undefined,
      debug_prompt: prompt,
      debug_payload: JSON.stringify(debugPayload, null, 2),
    } as Partial<Scene>;
  } catch {
    if (!silent) showToast("Scene image generation failed", "error");
    return null;
  }
}

async function validateImageCandidate(imageUrl: string, prompt: string, sceneId?: number) {
  try {
    const { storyboardId } = useStudioStore.getState();
    const res = await axios.post(`${API_BASE}/scene/validate_image`, {
      image_b64: imageUrl,
      prompt,
      storyboard_id: storyboardId,
      scene_id: sceneId,
    });
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
  const { autoComposePrompt } = useStudioStore.getState();
  const prompt = await buildScenePrompt(scene);
  if (!prompt) {
    if (!silent) useStudioStore.getState().showToast("Prompt is required", "error");
    return null;
  }

  const candidates: Array<{ image_url: string; match_rate?: number }> = [];
  for (let i = 0; i < 3; i += 1) {
    const result = await generateSceneImageFor(scene, true);
    if (!result?.image_url) continue;
    const validation = await validateImageCandidate(result.image_url, prompt, scene.id);
    candidates.push({
      image_url: result.image_url,
      match_rate:
        typeof validation?.match_rate === "number" ? validation.match_rate : 0,
    });
  }
  if (!candidates.length) return null;

  const best = [...candidates].sort(
    (a, b) => (b.match_rate ?? 0) - (a.match_rate ?? 0)
  )[0];

  if (best?.image_url) {
    const validation = await validateImageCandidate(best.image_url, prompt, scene.id);
    if (validation) {
      const { imageValidationResults } = useStudioStore.getState();
      useStudioStore.getState().setScenesState({
        imageValidationResults: {
          ...imageValidationResults,
          [scene.id]: validation,
        },
      });
    }
  }

  return {
    image_url: best.image_url,
    candidates,
    debug_prompt: prompt,
    image_prompt: autoComposePrompt ? prompt : undefined,
  } as Partial<Scene>;
}

/** Generate image for a scene (single or multi-gen) and update store */
export async function handleGenerateImage(scene: Scene) {
  const { multiGenEnabled, updateScene, showToast, scenes } = useStudioStore.getState();

  // Auto-save storyboard before image generation
  // Ensures activity logs have proper storyboard_id and scene IDs are assigned
  const storyboardId = await autoSaveStoryboard();
  if (!storyboardId) {
    showToast("Failed to save storyboard before generation", "error");
    return;
  }

  // Get updated scene with DB-assigned ID
  const updatedScene = scenes.find(s => s.id === scene.id || (s.script === scene.script && s.order === scene.order));
  if (!updatedScene) {
    showToast("Scene not found after save", "error");
    return;
  }

  updateScene(updatedScene.id, { isGenerating: true });
  try {
    const result = multiGenEnabled
      ? await generateSceneCandidates(updatedScene)
      : await generateSceneImageFor(updatedScene);
    if (result) {
      console.log("[handleGenerateImage] Image generation result:", result);
      updateScene(updatedScene.id, result);

      // Auto-save after image generation to persist image_url to DB
      // Prevents image loss on page refresh
      console.log("[handleGenerateImage] Calling saveStoryboard...");
      const saved = await saveStoryboard();
      console.log("[handleGenerateImage] saveStoryboard result:", saved);
    } else {
      console.warn("[handleGenerateImage] No result from image generation");
    }
  } finally {
    updateScene(updatedScene.id, { isGenerating: false });
  }
}

/** Upload a local file as a scene image */
export function handleImageUpload(sceneId: number, file?: File) {
  if (!file) return;
  const reader = new FileReader();
  reader.onloadend = async () => {
    const dataUrl = reader.result as string;
    const { projectId, groupId, storyboardId } = useStudioStore.getState();
    const storedUrl = await storeSceneImage(
      dataUrl,
      projectId || 1,
      groupId || 1,
      storyboardId || 1,
      sceneId,
      `upload_${sceneId}_${Date.now()}.png`
    );
    useStudioStore.getState().updateScene(sceneId, {
      image_url: storedUrl,
      candidates: [],
    });

    // Auto-save after image upload to persist to DB
    await saveStoryboard();
  };
  reader.readAsDataURL(file);
}

/** Edit scene image with Gemini */
export async function handleEditWithGemini(
  scene: Scene,
  targetChange: string
) {
  const { updateScene, showToast } = useStudioStore.getState();
  if (!scene.image_url) {
    showToast("No image to edit. Generate one first.", "error");
    return;
  }
  updateScene(scene.id, { isGenerating: true });
  try {
    const prompt = await buildScenePrompt(scene);
    if (!prompt) {
      showToast("Prompt build failed", "error");
      updateScene(scene.id, { isGenerating: false });
      return;
    }
    const res = await axios.post(`${API_BASE}/scene/edit-with-gemini`, {
      image_url: scene.image_url,
      original_prompt: prompt,
      target_change: targetChange,
    });
    if (res.data.edited_image) {
      const dataUrl = `data:image/png;base64,${res.data.edited_image}`;
      const { projectId, groupId, storyboardId } = useStudioStore.getState();
      const storedUrl = await storeSceneImage(
        dataUrl,
        projectId || 1,
        groupId || 1,
        storyboardId || 1,
        scene.id,
        `gemini_edit_${scene.id}_${Date.now()}.png`
      );
      updateScene(scene.id, { image_url: storedUrl, isGenerating: false });
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
    updateScene(scene.id, { isGenerating: false });
  }
}

/** Ask Gemini for edit suggestions */
export async function handleSuggestEditWithGemini(
  scene: Scene
): Promise<unknown[]> {
  const { showToast } = useStudioStore.getState();
  if (!scene.image_url) {
    showToast("No image. Generate one first.", "error");
    return [];
  }
  try {
    const prompt = await buildScenePrompt(scene);
    if (!prompt) {
      showToast("Prompt build failed", "error");
      return [];
    }
    const res = await axios.post(`${API_BASE}/scene/suggest-edit`, {
      image_url: scene.image_url,
      original_prompt: prompt,
    });
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
