import axios from "axios";
import type { Scene, ImageGenProgress, ImageValidation } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { getErrorMsg } from "../../utils/error";
import { generateWithProgress } from "../../utils/generateWithProgress";
import { buildScenePrompt, buildNegativePrompt } from "./promptActions";
import { resolveCharacterIdForSpeaker } from "../../utils/speakerResolver";
import { resolveSceneControlnet, resolveSceneIpAdapter } from "../../utils/sceneSettingsResolver";
import { validateImageCandidate, processGeneratedImages } from "./imageProcessing";

// Re-export for external consumers
export { storeSceneImage } from "./imageProcessing";

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

  const prompt = buildScenePrompt(scene);
  if (!prompt) {
    if (!silent) showToast("Prompt is required", "error");
    return null;
  }

  const negativePrompt = buildNegativePrompt(scene);

  const hiResPayload = buildHiResPayload();
  // Narrator scenes: disable ControlNet (no character to pose) and IP-Adapter (no reference)
  const isNarrator = scene.speaker === "Narrator";
  const controlnetPayload =
    controlnet.enabled && !isNarrator
      ? {
          use_controlnet: true,
          controlnet_weight: controlnet.weight,
          controlnet_pose: scene.controlnet_pose || undefined,
        }
      : { use_controlnet: false };
  const ipAdapterPayload =
    ipAdapter.enabled && ipAdapter.reference && !isNarrator
      ? {
          use_ip_adapter: true,
          ip_adapter_reference: ipAdapter.reference,
          ip_adapter_weight: ipAdapter.weight,
        }
      : { use_ip_adapter: false };

  const requestPayload = {
    prompt,
    negative_prompt: negativePrompt,
    width: 512,
    height: 768,
    ...hiResPayload,
    ...controlnetPayload,
    ...ipAdapterPayload,
    character_id: selectedCharacterId,
    character_b_id: sbState.selectedCharacterBId || undefined,
    storyboard_id: storyboardId,
    scene_id: scene.id > 0 ? scene.id : undefined,
    background_id: scene.background_id || undefined,
    context_tags: scene.context_tags || undefined,
    style_loras: sbState.characterLoras || [],
    auto_rewrite_prompt: sbState.autoRewritePrompt,
    auto_replace_risky_tags: sbState.autoReplaceRiskyTags,
    client_id: scene.client_id,
  };

  const debugPayload = { ...requestPayload };

  // Try async SSE first, fallback to sync on any SSE failure
  try {
    const sseData = await generateWithSSE(scene.client_id, requestPayload);
    if (sseData?.image) {
      const result = await processGeneratedImages({
        images: [sseData.image],
        scene,
        prompt,
        usedPrompt: sseData.used_prompt,
        warnings: sseData.warnings || [],
        selectedCharacterId,
        silent,
        controlnet_pose: sseData.controlnet_pose,
        ip_adapter_reference: sseData.ip_adapter_reference,
        preStored:
          sseData.image_url && sseData.image_asset_id
            ? { url: sseData.image_url, asset_id: sseData.image_asset_id }
            : undefined,
      });
      if (result) {
        return {
          ...result,
          debug_prompt: prompt,
          debug_payload: JSON.stringify(
            {
              request: debugPayload,
              actual: {
                prompt: sseData.used_prompt,
                negative_prompt: sseData.used_negative_prompt,
                steps: sseData.used_steps,
                cfg_scale: sseData.used_cfg_scale,
                sampler: sseData.used_sampler,
                seed: sseData.seed,
              },
            },
            null,
            2
          ),
        };
      }
    }
  } catch (error) {
    // Timeout: task is still running on server, don't create duplicate via sync
    const isTimeout = error instanceof Error && error.message.includes("timeout");
    if (isTimeout) {
      if (!silent) showToast("이미지 생성 시간이 초과되었습니다. 다시 시도해 주세요.", "error");
      return null;
    }
    // Other SSE failures (connection refused, stream lost): fall through to sync fallback
    console.warn("[generateSceneImageFor] SSE failed, falling back to sync");
  }

  return generateSync({
    scene,
    requestPayload,
    debugPayload,
    prompt,
    selectedCharacterId,
    silent,
  });
}

/** Clear SSE progress for a scene */
function clearImageGenProgress(sceneClientId: string) {
  const { imageGenProgress } = useStoryboardStore.getState();
  const next = { ...imageGenProgress };
  delete next[sceneClientId];
  useStoryboardStore.getState().set({ imageGenProgress: next });
}

/** SSE-based async image generation — returns raw SSE data for caller to process */
async function generateWithSSE(
  sceneClientId: string,
  payload: Record<string, unknown>
): Promise<ImageGenProgress | null> {
  const updateProgress = (p: ImageGenProgress) => {
    const { imageGenProgress } = useStoryboardStore.getState();
    useStoryboardStore.getState().set({
      imageGenProgress: { ...imageGenProgress, [sceneClientId]: p },
    });
  };

  try {
    const final = await generateWithProgress(payload, updateProgress);
    clearImageGenProgress(sceneClientId);
    if (!final.image) return null;
    return final;
  } catch (error) {
    clearImageGenProgress(sceneClientId);
    // Don't show toast here — caller falls back to sync which has its own error handling.
    throw error;
  }
}

type GenerateOpts = {
  scene: Scene;
  requestPayload: Record<string, unknown>;
  debugPayload: Record<string, unknown>;
  prompt: string;
  selectedCharacterId: number | null;
  silent: boolean;
};

/** Sync fallback: POST /scene/generate */
async function generateSync(opts: GenerateOpts): Promise<Partial<Scene> | null> {
  const { scene, requestPayload, debugPayload, prompt, selectedCharacterId, silent } = opts;
  const { showToast } = useUIStore.getState();

  try {
    const res = await axios.post(`${API_BASE}/scene/generate`, requestPayload, {
      timeout: API_TIMEOUT.IMAGE_GENERATION,
    });
    const images = res.data.images || (res.data.image ? [res.data.image] : []);

    if (images.length > 0) {
      const result = await processGeneratedImages({
        images,
        scene,
        prompt,
        usedPrompt: res.data.used_prompt,
        warnings: res.data.warnings,
        selectedCharacterId,
        silent,
        controlnet_pose: res.data.controlnet_pose,
        ip_adapter_reference: res.data.ip_adapter_reference,
      });
      if (result) {
        return {
          ...result,
          debug_prompt: prompt,
          debug_payload: JSON.stringify(
            {
              request: debugPayload,
              actual: {
                prompt: res.data.used_prompt,
                negative_prompt: res.data.used_negative_prompt,
                steps: res.data.used_steps,
                cfg_scale: res.data.used_cfg_scale,
                sampler: res.data.used_sampler,
                seed: res.data.seed,
              },
            },
            null,
            2
          ),
        };
      }
    }

    return {
      image_prompt: res.data.used_prompt || undefined,
      debug_prompt: prompt,
      debug_payload: JSON.stringify(
        {
          request: debugPayload,
          actual: {
            prompt: res.data.used_prompt,
            negative_prompt: res.data.used_negative_prompt,
            steps: res.data.used_steps,
            cfg_scale: res.data.used_cfg_scale,
            sampler: res.data.used_sampler,
            seed: res.data.seed,
          },
        },
        null,
        2
      ),
    } as Partial<Scene>;
  } catch (error) {
    if (!silent) showToast(getErrorMsg(error, "이미지 생성 실패"), "error");
    return null;
  }
}

/** Generate 3 candidates and pick the best by match rate */
export async function generateSceneCandidates(
  scene: Scene,
  silent = false
): Promise<Partial<Scene> | null> {
  const sbState = useStoryboardStore.getState();
  const selectedCharacterId = resolveCharacterIdForSpeaker(scene.speaker, sbState);
  const prompt = buildScenePrompt(scene);
  if (!prompt) {
    if (!silent) useUIStore.getState().showToast("Prompt is required", "error");
    return null;
  }

  type CandidateEntry = {
    media_asset_id: number;
    match_rate?: number;
    adjusted_match_rate?: number;
    identity_score?: number;
    image_url?: string;
    _validation?: ImageValidation;
  };
  const candidates: CandidateEntry[] = [];
  let resolvedImagePrompt: string | undefined;
  for (let i = 0; i < 3; i += 1) {
    const result = await generateSceneImageFor(scene, true);
    if (!result?.image_url || !result?.image_asset_id) continue;
    if (!resolvedImagePrompt && result.image_prompt) {
      resolvedImagePrompt = result.image_prompt;
    }
    const validation = await validateImageCandidate(
      result.image_url,
      prompt,
      scene.id,
      selectedCharacterId
    );
    const vResult = validation?.validation_result ?? validation;
    candidates.push({
      media_asset_id: result.image_asset_id,
      match_rate: typeof vResult?.match_rate === "number" ? vResult.match_rate : 0,
      adjusted_match_rate:
        typeof vResult?.adjusted_match_rate === "number" ? vResult.adjusted_match_rate : undefined,
      identity_score:
        typeof vResult?.identity_score === "number" ? vResult.identity_score : undefined,
      image_url: result.image_url,
      _validation: vResult ?? undefined,
    });
  }
  if (!candidates.length) {
    if (!silent) {
      useUIStore
        .getState()
        .showToast("3회 시도 모두 실패했습니다. 프롬프트를 확인해 주세요.", "error");
    }
    return null;
  }

  const best = [...candidates].sort((a, b) => {
    const idA = a.identity_score ?? -1;
    const idB = b.identity_score ?? -1;
    if (idA !== idB) return idB - idA;
    return (
      (b.adjusted_match_rate ?? b.match_rate ?? 0) - (a.adjusted_match_rate ?? a.match_rate ?? 0)
    );
  })[0];

  // Re-use the validation result already obtained during candidate generation.
  // No redundant API call needed: best._validation was already fetched in the loop.
  if (best?._validation) {
    const { imageValidationResults } = useStoryboardStore.getState();
    useStoryboardStore.getState().set({
      imageValidationResults: {
        ...imageValidationResults,
        [scene.client_id]: best._validation,
      },
    });
  }

  const bestAssetId = best.media_asset_id;

  return {
    image_url: best.image_url,
    image_asset_id: bestAssetId,
    candidates,
    debug_prompt: prompt,
    image_prompt: resolvedImagePrompt || undefined,
  } as Partial<Scene>;
}
