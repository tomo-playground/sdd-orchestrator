import axios from "axios";
import { API_BASE, API_TIMEOUT } from "../../constants";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import type { Scene } from "../../types";
import { storeSceneImage } from "./imageActions";
import { buildSceneRequest } from "./imageGeneration";

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

    const sceneRequests = targetScenes.map((scene) => ({
      ...buildSceneRequest(scene, sbState, storyboardId || null),
      seed: -1,
    }));

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
