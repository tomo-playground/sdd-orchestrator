import axios from "axios";
import type { Scene, GeminiSuggestion } from "../../types";
import { useStoryboardStore } from "../useStoryboardStore";
import { useContextStore } from "../useContextStore";
import { useUIStore } from "../useUIStore";
import { API_BASE } from "../../constants";
import { buildScenePrompt } from "./promptActions";
import { resolveSceneMultiGen } from "../../utils/sceneSettingsResolver";
import { autoSaveStoryboard, saveStoryboard } from "./storyboardActions";
import { storeSceneImage, generateSceneImageFor, generateSceneCandidates } from "./imageGeneration";

// Re-export for existing consumers
export { storeSceneImage, generateSceneImageFor, generateSceneCandidates };

/** Generate image for a scene (single or multi-gen) and update store */
export async function handleGenerateImage(scene: Scene) {
  const { updateScene } = useStoryboardStore.getState();
  const { showToast } = useUIStore.getState();
  const multiGenEnabled = resolveSceneMultiGen(scene, useStoryboardStore.getState());

  // Auto-save storyboard before image generation
  // Ensures activity logs have proper storyboard_id and scene IDs are assigned
  const storyboardId = await autoSaveStoryboard();
  if (!storyboardId) {
    showToast("이미지 생성 전 영상 저장에 실패했습니다", "error");
    return;
  }

  // Get updated scene with DB-assigned ID (client_id is stable across saves)
  const updatedScene = useStoryboardStore
    .getState()
    .scenes.find((s) => s.client_id === scene.client_id);
  if (!updatedScene) {
    showToast("저장 후 씬을 찾을 수 없습니다", "error");
    return;
  }

  updateScene(scene.client_id, { isGenerating: true });
  try {
    const result = multiGenEnabled
      ? await generateSceneCandidates(updatedScene)
      : await generateSceneImageFor(updatedScene);
    if (result) {
      const { updateScene: liveUpdateScene } = useStoryboardStore.getState();

      // Include isGenerating: false before saveStoryboard to survive ID reassignment
      liveUpdateScene(scene.client_id, { ...result, isGenerating: false });

      // Auto-pin: Apply environment reference if scene has _auto_pin_previous flag
      const { applyAutoPinAfterGeneration } = await import("../../utils/applyAutoPin");
      const autoPinResult = applyAutoPinAfterGeneration(
        useStoryboardStore.getState().scenes,
        scene.client_id,
        liveUpdateScene
      );
      if (autoPinResult?.success) {
        console.log("[AutoPin]", autoPinResult.message);
        showToast(`자동 핀: ${autoPinResult.message}`, "success");
      }

      // image_url/image_asset_id are persisted by POST /image/store immediately.
      // Other fields (use_controlnet, ip_adapter_reference, candidates, etc.) auto-saved via isDirty subscribe.
    } else {
      console.warn("[handleGenerateImage] No result from image generation");
    }
  } finally {
    useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: false });
  }
}

/** Upload a local file as a scene image */
export function handleImageUpload(clientId: string, file?: File) {
  if (!file) return;
  const reader = new FileReader();
  reader.onerror = () => {
    console.error("FileReader error:", reader.error);
    useUIStore.getState().showToast("이미지 파일을 읽을 수 없습니다", "error");
  };
  reader.onloadend = async () => {
    const dataUrl = reader.result as string;
    const { projectId, groupId, storyboardId } = useContextStore.getState();
    const { showToast } = useUIStore.getState();
    const { updateScene } = useStoryboardStore.getState();
    if (!projectId || !groupId || !storyboardId) {
      showToast("채널/시리즈를 먼저 선택하세요", "error");
      return;
    }
    const scene = useStoryboardStore.getState().scenes.find((s) => s.client_id === clientId);
    const dbSceneId = scene?.id ?? 0;
    const stored = await storeSceneImage(
      dataUrl,
      projectId,
      groupId,
      storyboardId,
      dbSceneId,
      `upload_${dbSceneId}_${Date.now()}.png`,
      clientId
    );
    updateScene(clientId, {
      image_url: stored.url,
      image_asset_id: stored.asset_id ?? null,
      candidates: [],
    });

    // Auto-pin: Apply environment reference if scene has _auto_pin_previous flag
    const { applyAutoPinAfterGeneration } = await import("../../utils/applyAutoPin");
    const autoPinResult = applyAutoPinAfterGeneration(
      useStoryboardStore.getState().scenes,
      clientId,
      updateScene
    );
    if (autoPinResult?.success) {
      console.log("[AutoPin]", autoPinResult.message);
      showToast(`자동 핀: ${autoPinResult.message}`, "success");
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
    showToast("편집할 이미지가 없습니다. 먼저 생성하세요.", "error");
    return;
  }
  if (scene.image_url.startsWith("data:")) {
    showToast("씬을 먼저 저장하세요 (이미지가 저장되어야 합니다)", "error");
    return;
  }
  useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: true });
  try {
    const prompt = buildScenePrompt(scene);
    if (!prompt) {
      showToast("프롬프트 구성에 실패했습니다", "error");
      useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: false });
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
        showToast("채널/시리즈를 먼저 선택하세요", "error");
        useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: false });
        return;
      }
      // Use client_id for stable scene lookup (DB id may change during API call)
      const currentScene = useStoryboardStore
        .getState()
        .scenes.find((s) => s.client_id === scene.client_id);
      const dbId = currentScene?.id ?? scene.id;
      const stored = await storeSceneImage(
        dataUrl,
        projectId,
        groupId,
        storyboardId,
        dbId,
        `gemini_edit_${dbId}_${Date.now()}.png`,
        scene.client_id
      );
      useStoryboardStore.getState().updateScene(scene.client_id, {
        image_url: stored.url,
        image_asset_id: stored.asset_id ?? null,
        isGenerating: false,
      });
      showToast(
        `Gemini 편집 완료 (${res.data.edit_type}) - $${(res.data.cost_usd ?? 0).toFixed(4)}`,
        "success"
      );

      // Auto-save after Gemini edit to persist to DB
      await saveStoryboard();
    }
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    showToast(`Gemini 편집 실패: ${msg}`, "error");
    useStoryboardStore.getState().updateScene(scene.client_id, { isGenerating: false });
  }
}

/** Ask Gemini for edit suggestions */
export async function handleSuggestEditWithGemini(scene: Scene): Promise<GeminiSuggestion[]> {
  const { showToast } = useUIStore.getState();
  if (!scene.image_url) {
    showToast("이미지가 없습니다. 먼저 생성하세요.", "error");
    return [];
  }
  if (scene.image_url.startsWith("data:")) {
    showToast("씬을 먼저 저장하세요 (이미지가 저장되어야 합니다)", "error");
    return [];
  }
  try {
    const prompt = buildScenePrompt(scene);
    if (!prompt) {
      showToast("프롬프트 구성에 실패했습니다", "error");
      return [];
    }
    const payload =
      scene.image_url.startsWith("http://") || scene.image_url.startsWith("https://")
        ? { image_url: scene.image_url, original_prompt: prompt }
        : { image_b64: scene.image_url, original_prompt: prompt };
    const res = await axios.post(`${API_BASE}/scene/suggest-edit`, payload);
    if (res.data.has_mismatch && res.data.suggestions?.length > 0) {
      showToast(
        `${res.data.suggestions.length}개 제안 - $${(res.data.cost_usd ?? 0).toFixed(4)}`,
        "success"
      );
      return res.data.suggestions;
    }
    showToast("이미지가 프롬프트와 잘 일치합니다", "success");
    return [];
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    showToast(`제안 실패: ${msg}`, "error");
    return [];
  }
}
