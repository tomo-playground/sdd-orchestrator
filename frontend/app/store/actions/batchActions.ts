import axios from "axios";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import type { Scene } from "../../types";
import { storeSceneImage } from "./imageActions";
import { resolveCharacterIdForSpeaker } from "../../utils/speakerResolver";
import { resolveSceneControlnet, resolveSceneIpAdapter } from "../../utils/sceneSettingsResolver";
import { buildNegativePrompt } from "./promptActions";

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
export async function generateBatchImages(sceneClientIds: string[]): Promise<BatchResponse | null> {
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
    const sceneRequests = targetScenes.map((scene) => {
      const controlnet = resolveSceneControlnet(scene, sbState);
      const ipAdapter = resolveSceneIpAdapter(scene, sbState);
      // Narrator scenes: disable ControlNet (no character to pose) and IP-Adapter (no reference)
      const isNarrator = scene.speaker === "Narrator";
      return {
        prompt: scene.image_prompt || "",
        negative_prompt: buildNegativePrompt(scene),
        steps: 27,
        cfg_scale: 7,
        sampler_name: "DPM++ 2M Karras",
        seed: -1,
        width: scene.width || 512,
        height: scene.height || 768,
        clip_skip: 2,
        character_id: resolveCharacterIdForSpeaker(scene.speaker, sbState) || 0,
        storyboard_id: useContextStore.getState().storyboardId || undefined,
        use_controlnet: controlnet.enabled && !isNarrator,
        controlnet_weight: controlnet.weight,
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
      { timeout: API_TIMEOUT.IMAGE_GENERATION * sceneRequests.length }
    );

    const { results } = res.data;

    // Store images in parallel, then update scenes
    const { projectId, groupId, storyboardId } = useContextStore.getState();
    const canStore = projectId && groupId && storyboardId;

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
            storyboardId,
            scene.id,
            `scene_${scene.id}_${Date.now()}.png`
          );
          // Retry store once if asset_id is missing (transient storage failure)
          if (!stored.asset_id) {
            stored = await storeSceneImage(
              dataUrl,
              projectId,
              groupId,
              storyboardId,
              scene.id,
              `scene_${scene.id}_${Date.now()}_retry.png`
            );
          }
          useStoryboardStore.getState().updateScene(scene.client_id, {
            image_url: stored.url,
            image_asset_id: stored.asset_id ?? null,
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
