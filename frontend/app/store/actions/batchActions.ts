import axios from "axios";
import { API_BASE } from "../../constants";
import { useStudioStore } from "../useStudioStore";
import type { Scene } from "../../types";

interface BatchResult {
  index: number;
  status: "success" | "failed";
  data?: { image_url: string; [key: string]: unknown };
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
export async function generateBatchImages(sceneIds: number[]): Promise<BatchResponse | null> {
  const state = useStudioStore.getState();
  const { scenes, updateScene } = state;

  // Build requests from scene data
  const targetScenes = sceneIds
    .map((id) => scenes.find((s) => s.id === id))
    .filter((s): s is Scene => s !== undefined);

  if (targetScenes.length === 0) return null;

  // Mark all as generating
  for (const scene of targetScenes) {
    updateScene(scene.id, { isGenerating: true });
  }

  try {
    const sceneRequests = targetScenes.map((scene) => ({
      prompt: scene.image_prompt || "",
      negative_prompt: scene.negative_prompt || "",
      steps: 27,
      cfg_scale: 7,
      sampler_name: "DPM++ 2M Karras",
      seed: -1,
      width: scene.width || 512,
      height: scene.height || 768,
      clip_skip: 2,
      character_id: state.selectedCharacterId || 0,
      storyboard_id: state.storyboardId || undefined,
      style_loras: state.characterLoras?.filter((l) => l.lora_type === "style") || [],
      use_controlnet: state.useControlnet || false,
      use_ip_adapter: state.useIpAdapter || false,
      ip_adapter_reference: state.ipAdapterReference || undefined,
      ip_adapter_weight: state.ipAdapterWeight || 0.7,
      use_reference_only: scene.use_reference_only ?? true,
      reference_only_weight: scene.reference_only_weight ?? 0.5,
      environment_reference_id: scene.environment_reference_id || undefined,
      environment_reference_weight: scene.environment_reference_weight ?? 0.3,
    }));

    const res = await axios.post<BatchResponse>(`${API_BASE}/scene/generate-batch`, {
      scenes: sceneRequests,
    });

    const { results } = res.data;

    // Update each scene with its result
    for (const result of results) {
      const scene = targetScenes[result.index];
      if (!scene) continue;

      if (result.status === "success" && result.data?.image_url) {
        updateScene(scene.id, {
          image_url: result.data.image_url,
          isGenerating: false,
        });
      } else {
        updateScene(scene.id, { isGenerating: false });
      }
    }

    return res.data;
  } catch (error) {
    // Mark all as not generating on error
    for (const scene of targetScenes) {
      updateScene(scene.id, { isGenerating: false });
    }
    console.error("Batch generation failed:", error);
    return null;
  }
}
