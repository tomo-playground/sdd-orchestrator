import axios from "axios";
import type { Scene, ImageGenProgress } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { getErrorMsg } from "../../utils/error";
import { generateWithProgress } from "../../utils/generateWithProgress";
import { buildScenePrompt, buildNegativePrompt } from "./promptActions";
import { resolveCharacterIdForSpeaker } from "../../utils/speakerResolver";
import { resolveSceneControlnet, resolveSceneIpAdapter } from "../../utils/sceneSettingsResolver";
import { processGeneratedImages } from "./imageProcessing";

// Re-export for external consumers
export { storeSceneImage } from "./imageProcessing";

/** Typed SD generation request payload. Mirrors backend SceneGenerateRequest. */
export interface SceneRequest {
  prompt: string;
  negative_prompt: string;
  width: number;
  height: number;
  is_hr_enabled?: boolean;
  hr_scale?: number;
  hr_upscaler?: string;
  hr_second_pass_steps?: number;
  denoising_strength?: number;
  character_id: number | null;
  character_b_id?: number;
  storyboard_id?: number;
  scene_id?: number;
  background_id?: number;
  context_tags?: Record<string, unknown>;
  style_loras: unknown[];
  is_auto_rewrite_enabled: boolean;
  is_auto_replace_risky_tags: boolean;
  client_id: string;
  is_controlnet_enabled: boolean;
  controlnet_weight: number;
  controlnet_pose?: string;
  is_ip_adapter_enabled: boolean;
  ip_adapter_reference?: string;
  ip_adapter_weight: number;
  is_reference_only_enabled: boolean;
  reference_only_weight: number;
  environment_reference_id?: number;
  environment_reference_weight: number;
}

/**
 * Build a complete SD generation request payload from scene + store state.
 * SSOT: both manual (generateSceneImageFor) and auto-run (generateBatchImages) use this.
 * Seed is intentionally excluded — callers provide it differently.
 */
export function buildSceneRequest(
  scene: Scene,
  sbState: ReturnType<typeof useStoryboardStore.getState>,
  storyboardId: number | null
): SceneRequest {
  const controlnet = resolveSceneControlnet(scene, sbState);
  const ipAdapter = resolveSceneIpAdapter(scene, sbState);
  const isNarrator = scene.speaker === "Narrator";
  // Backend SSOT: hi_res_defaults from /presets API → store.hiResDefaults
  const hrd = sbState.hiResDefaults;
  const hiResPayload = sbState.hiResEnabled
    ? {
        is_hr_enabled: true,
        hr_scale: hrd?.scale ?? 1.5,
        hr_upscaler: hrd?.upscaler ?? "R-ESRGAN 4x+ Anime6B",
        hr_second_pass_steps: hrd?.second_pass_steps ?? 10,
        denoising_strength: hrd?.denoising_strength ?? 0.35,
      }
    : {};

  return {
    prompt: buildScenePrompt(scene) || "",
    negative_prompt: buildNegativePrompt(scene),
    // Backend SSOT: /presets API image_defaults → store.imageDefaults
    width: scene.width || sbState.imageDefaults.width,
    height: scene.height || sbState.imageDefaults.height,
    ...hiResPayload,
    character_id: resolveCharacterIdForSpeaker(scene.speaker, sbState),
    character_b_id: sbState.selectedCharacterBId || undefined,
    storyboard_id: storyboardId || undefined,
    scene_id: scene.id > 0 ? scene.id : undefined,
    background_id: scene.background_id || undefined,
    context_tags: scene.context_tags || undefined,
    style_loras: sbState.characterLoras || [],
    is_auto_rewrite_enabled: sbState.autoRewritePrompt,
    is_auto_replace_risky_tags: sbState.autoReplaceRiskyTags,
    client_id: scene.client_id,
    is_controlnet_enabled: controlnet.enabled && !isNarrator,
    controlnet_weight: controlnet.weight,
    controlnet_pose: scene.controlnet_pose || undefined,
    is_ip_adapter_enabled: ipAdapter.enabled && !!ipAdapter.reference && !isNarrator,
    ip_adapter_reference: isNarrator ? undefined : ipAdapter.reference || undefined,
    // Backend SSOT: /presets API generation_defaults.ip_adapter_weight → store.ipAdapterWeight
    ip_adapter_weight: ipAdapter.weight ?? 0.35,
    // Backend SSOT: config.py (schemas.py SceneGenerateRequest.is_reference_only_enabled default=True)
    is_reference_only_enabled: scene.use_reference_only ?? true,
    // Backend SSOT: config.py DEFAULT_REFERENCE_ONLY_WEIGHT = 0.5
    reference_only_weight: scene.reference_only_weight ?? 0.5,
    environment_reference_id: scene.environment_reference_id || undefined,
    // Backend SSOT: config.py DEFAULT_ENVIRONMENT_REFERENCE_WEIGHT = 0.3
    environment_reference_weight: scene.environment_reference_weight ?? 0.3,
  };
}

/** Generate a single image for a scene via SD */
export async function generateSceneImageFor(
  scene: Scene,
  silent = false,
  overrides?: { seed?: number }
): Promise<Partial<Scene> | null> {
  const sbState = useStoryboardStore.getState();
  const { storyboardId } = useContextStore.getState();
  const { showToast } = useUIStore.getState();
  const selectedCharacterId = resolveCharacterIdForSpeaker(scene.speaker, sbState);

  // Narrator scenes don't require character selection (no_humans, scenery only)
  if (!selectedCharacterId && scene.speaker !== "Narrator") {
    if (!silent) showToast("캐릭터를 선택해야 합니다", "error");
    return null;
  }

  if (!scene.image_prompt?.trim()) {
    if (!silent) showToast("프롬프트를 입력해야 합니다", "error");
    return null;
  }

  // Multi-character scene without character B: warn user about single fallback
  if (scene.scene_mode === "multi" && !sbState.selectedCharacterBId) {
    showToast("캐릭터 B가 선택되지 않아 multi 씬이 single로 폴백됩니다.", "warning");
  }

  const base = buildSceneRequest(scene, sbState, storyboardId);
  const seed = overrides?.seed ?? Math.floor(Math.random() * 2147483647);
  const requestPayload = { ...base, seed };
  const prompt = requestPayload.prompt;

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
        sseValidation:
          sseData.match_rate != null
            ? {
                match_rate: sseData.match_rate,
                matched_tags: sseData.matched_tags,
                missing_tags: sseData.missing_tags,
              }
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
    const isTimeout =
      (axios.isAxiosError(error) && error.code === "ECONNABORTED") ||
      (error instanceof Error && error.message.includes("timeout"));
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
  payload: SceneRequest | (SceneRequest & { seed: number })
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
  requestPayload: SceneRequest | (SceneRequest & { seed: number });
  debugPayload: SceneRequest | (SceneRequest & { seed: number });
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
  const prompt = buildScenePrompt(scene);
  if (!prompt) {
    if (!silent) useUIStore.getState().showToast("프롬프트를 입력해야 합니다", "error");
    return null;
  }

  type CandidateEntry = {
    media_asset_id: number;
    match_rate?: number;
    adjusted_match_rate?: number;
    identity_score?: number;
    image_url?: string;
  };
  const candidates: CandidateEntry[] = [];
  let resolvedImagePrompt: string | undefined;

  for (let i = 0; i < 3; i += 1) {
    const result = await generateSceneImageFor(scene, true, {
      seed: Math.floor(Math.random() * 2147483647),
    });
    if (!result?.image_url || !result?.image_asset_id) continue;
    if (!resolvedImagePrompt && result.image_prompt) {
      resolvedImagePrompt = result.image_prompt;
    }
    // processGeneratedImages (SSE 경로) 내부에서 이미 validation을 실행하여
    // imageValidationResults store에 저장하고 result.candidates에 점수를 포함합니다.
    // 중복 validateImageCandidate 호출 없이 result에서 직접 점수를 읽습니다.
    const firstCandidate = result.candidates?.[0];
    candidates.push({
      media_asset_id: result.image_asset_id,
      match_rate: typeof firstCandidate?.match_rate === "number" ? firstCandidate.match_rate : 0,
      adjusted_match_rate:
        typeof firstCandidate?.adjusted_match_rate === "number"
          ? firstCandidate.adjusted_match_rate
          : undefined,
      identity_score:
        typeof firstCandidate?.identity_score === "number"
          ? firstCandidate.identity_score
          : undefined,
      image_url: result.image_url,
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

  // best 후보의 validation 결과로 store를 최종 갱신합니다.
  // (3회 반복 중 마지막 후보가 store에 남아 있을 수 있으므로 best 기준으로 덮어씁니다.)
  if (best.match_rate != null || best.adjusted_match_rate != null || best.identity_score != null) {
    useStoryboardStore.getState().set({
      imageValidationResults: {
        ...useStoryboardStore.getState().imageValidationResults,
        [scene.client_id]: {
          match_rate: best.match_rate ?? 0,
          matched: [],
          missing: [],
          extra: [],
          identity_score: best.identity_score,
          adjusted_match_rate: best.adjusted_match_rate,
        },
      },
    });
  }

  return {
    image_url: best.image_url,
    image_asset_id: best.media_asset_id,
    candidates,
    debug_prompt: prompt,
    image_prompt: resolvedImagePrompt || undefined,
  } as Partial<Scene>;
}
