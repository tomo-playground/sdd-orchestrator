import axios from "axios";
import type { Scene } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { buildScenePrompt, buildNegativePrompt } from "./promptActions";
import { resolveCharacterIdForSpeaker } from "../../utils/speakerResolver";
import {
  resolveSceneControlnet,
  resolveSceneIpAdapter,
} from "../../utils/sceneSettingsResolver";

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
        background_id: scene.background_id || undefined,
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

export async function validateImageCandidate(imageUrl: string, prompt: string, sceneId?: number) {
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
