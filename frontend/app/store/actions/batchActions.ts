import axios from "axios";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import type { Scene } from "../../types";
import { storeSceneImage } from "./imageActions";
import { resolveCharacterIdForSpeaker } from "../../utils/speakerResolver";
import { resolveSceneControlnet, resolveSceneIpAdapter } from "../../utils/sceneSettingsResolver";
import { buildScenePrompt, buildNegativePrompt } from "./promptActions";

interface BatchResult {
  index: number;
  status: "success" | "failed";
  data?: { image?: string; images?: string[]; used_prompt?: string; [key: string]: unknown };
  error?: string;
}

interface BatchResponse {
  results: BatchResult[];
  total: number;
  succeeded: number;
  failed: number;
}

/**
 * Generate images for multiple scenes in a single batch API call.
 * Updates each scene's state as results come back.
 */
export async function generateBatchImages(sceneClientIds: string[], signal?: AbortSignal): Promise<BatchResponse | null> {
  const sbState = useStoryboardStore.getState();
  const { scenes, updateScene } = sbState;

  // Build requests from scene data
  const targetScenes = sceneClientIds
    .map((clientId) => scenes.find((s) => s.client_id === clientId))
    .filter((s): s is Scene => s !== undefined);

  if (targetScenes.length === 0) return null;

  // Mark all as generating
  for (const scene of targetScenes) {
    updateScene(scene.client_id, { isGenerating: true });
  }

  try {
    const { storyboardId } = useContextStore.getState();
    // C-2: HiRes settings matching generateSceneImageFor
    const hiResPayload = sbState.hiResEnabled
      ? {
          enable_hr: true,
          hr_scale: 1.5,
          hr_upscaler: "R-ESRGAN 4x+ Anime6B",
          hr_second_pass_steps: 10,
          denoising_strength: 0.35,
        }
      : {};

    const sceneRequests = targetScenes.map((scene) => {
      const controlnet = resolveSceneControlnet(scene, sbState);
      const ipAdapter = resolveSceneIpAdapter(scene, sbState);
      const isNarrator = scene.speaker === "Narrator";
      // C-2: Use buildScenePrompt for consistent prompt construction
      const prompt = buildScenePrompt(scene) || "";
      return {
        prompt,
        negative_prompt: buildNegativePrompt(scene),
        seed: -1,
        width: scene.width || 512,
        height: scene.height || 768,
        ...hiResPayload,
        character_id: resolveCharacterIdForSpeaker(scene.speaker, sbState) || 0,
        character_b_id: sbState.selectedCharacterBId || undefined,
        storyboard_id: storyboardId || undefined,
        scene_id: scene.id > 0 ? scene.id : undefined, // H-6
        background_id: scene.background_id || undefined,
        context_tags: scene.context_tags || undefined,
        style_loras: sbState.characterLoras || [],
        auto_rewrite_prompt: sbState.autoRewritePrompt,
        auto_replace_risky_tags: sbState.autoReplaceRiskyTags,
        client_id: scene.client_id,
        use_controlnet: controlnet.enabled && !isNarrator,
        controlnet_weight: controlnet.weight,
        controlnet_pose: scene.controlnet_pose || undefined,
        use_ip_adapter: ipAdapter.enabled && !!ipAdapter.reference && !isNarrator,
        ip_adapter_reference: isNarrator ? undefined : ipAdapter.reference || undefined,
        ip_adapter_weight: ipAdapter.weight || 0.7,
        use_reference_only: scene.use_reference_only ?? true,
        reference_only_weight: scene.reference_only_weight ?? 0.5,
        environment_reference_id: scene.environment_reference_id || undefined,
        environment_reference_weight: scene.environment_reference_weight ?? 0.3,
      };
    });

    const res = await axios.post<BatchResponse>(
      `${API_BASE}/scene/generate-batch`,
      {
        scenes: sceneRequests,
      },
      { timeout: API_TIMEOUT.IMAGE_GENERATION * sceneRequests.length, signal }
    );

    const { results } = res.data;

    // Store images in parallel, then update scenes
    const { projectId, groupId, storyboardId: ctxStoryboardId } = useContextStore.getState();
    const canStore = projectId && groupId && ctxStoryboardId;

    await Promise.all(
      results.map(async (result) => {
        const originalScene = targetScenes[result.index];
        if (!originalScene) return;

        // Re-lookup by client_id (stable across save/ID reassignment)
        const currentScenes = useStoryboardStore.getState().scenes;
        const scene =
          currentScenes.find((s) => s.client_id === originalScene.client_id) || originalScene;

        const b64 = result.data?.image;
        if (result.status === "success" && b64 && canStore) {
          const dataUrl = `data:image/png;base64,${b64}`;
          let stored = await storeSceneImage(
            dataUrl,
            projectId,
            groupId,
            ctxStoryboardId,
            scene.id,
            `scene_${scene.id}_${Date.now()}.png`,
            scene.client_id
          );
          // Retry store once if asset_id is missing (transient storage failure)
          if (!stored.asset_id) {
            stored = await storeSceneImage(
              dataUrl,
              projectId,
              groupId,
              ctxStoryboardId,
              scene.id,
              `scene_${scene.id}_${Date.now()}_retry.png`,
              scene.client_id
            );
          }
          const candidates = stored.asset_id
            ? [{ media_asset_id: stored.asset_id, image_url: stored.url }]
            : undefined;
          useStoryboardStore.getState().updateScene(scene.client_id, {
            image_url: stored.url,
            image_asset_id: stored.asset_id ?? null,
            candidates,
            image_prompt: result.data?.used_prompt || undefined,
            isGenerating: false,
          });
        } else {
          useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: false });
        }
      })
    );

    return res.data;
  } catch (error) {
    // Mark all as not generating on error
    for (const scene of targetScenes) {
      useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: false });
    }
    console.error("Batch generation failed:", error);
    return null;
  }
}
