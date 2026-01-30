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

/** Store a base64 image on the backend and return a URL */
export async function storeSceneImage(dataUrl: string): Promise<string> {
  if (!dataUrl || !dataUrl.startsWith("data:")) return dataUrl;
  try {
    const res = await fetch(`${API_BASE}/image/store`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_b64: dataUrl }),
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
        hr_upscaler: "Latent",
        hr_second_pass_steps: 10,
        denoising_strength: 0.25,
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
  };

  try {
    const res = await axios.post(`${API_BASE}/scene/generate`, {
      ...debugPayload,
      character_id: selectedCharacterId,
    });
    if (res.data.image) {
      const dataUrl = `data:image/png;base64,${res.data.image}`;
      const storedUrl = await storeSceneImage(dataUrl);

      // Activity log
      let activityLogId: number | undefined;
      try {
        const logRes = await axios.post(`${API_BASE}/activity-logs`, {
          scene_id: scene.id,
          character_id: selectedCharacterId || undefined,
          prompt,
          tags: prompt.split(",").map((t: string) => t.trim()),
          sd_params: {
            steps: scene.steps,
            cfg_scale: scene.cfg_scale,
            sampler_name: scene.sampler_name,
            clip_skip: scene.clip_skip,
          },
          seed: scene.seed,
          status: "pending",
          image_url: storedUrl,
        });
        activityLogId = logRes.data.id;
      } catch {
        // non-critical
      }

      return {
        image_url: storedUrl,
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

async function validateImageCandidate(imageUrl: string, prompt: string) {
  try {
    const res = await axios.post(`${API_BASE}/scene/validate_image`, {
      image_b64: imageUrl,
      prompt,
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
    const validation = await validateImageCandidate(result.image_url, prompt);
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
    const validation = await validateImageCandidate(best.image_url, prompt);
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
  const { multiGenEnabled, updateScene } = useStudioStore.getState();
  updateScene(scene.id, { isGenerating: true });
  try {
    const result = multiGenEnabled
      ? await generateSceneCandidates(scene)
      : await generateSceneImageFor(scene);
    if (result) updateScene(scene.id, result);
  } finally {
    updateScene(scene.id, { isGenerating: false });
  }
}

/** Upload a local file as a scene image */
export function handleImageUpload(sceneId: number, file?: File) {
  if (!file) return;
  const reader = new FileReader();
  reader.onloadend = async () => {
    const dataUrl = reader.result as string;
    const storedUrl = await storeSceneImage(dataUrl);
    useStudioStore.getState().updateScene(sceneId, {
      image_url: storedUrl,
      candidates: [],
    });
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
      const storedUrl = await storeSceneImage(dataUrl);
      updateScene(scene.id, { image_url: storedUrl, isGenerating: false });
      showToast(
        `Gemini edit done (${res.data.edit_type}) - $${res.data.cost_usd.toFixed(4)}`,
        "success"
      );
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
