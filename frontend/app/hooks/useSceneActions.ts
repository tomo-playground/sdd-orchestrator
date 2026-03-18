import { useCallback, useEffect } from "react";
import axios from "axios";
import { useConfirm } from "../components/ui/ConfirmDialog";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useUIStore } from "../store/useUIStore";
import { API_BASE, DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT } from "../constants";
import type { Scene } from "../types";
import { generateSceneClientId } from "../utils/uuid";

/**
 * Extracted scene handlers and fetch effects from ScenesTab.
 * Keeps the tab component under the 400-line guideline.
 */
export function useSceneActions() {
  const { confirm, dialogProps } = useConfirm();
  const sbSet = useStoryboardStore((s) => s.set);
  const setScenes = useStoryboardStore((s) => s.setScenes);
  const showToast = useUIStore((s) => s.showToast);
  // Fetch IP-Adapter reference images on mount (skip if already loaded by useCharacterAutoLoad)
  useEffect(() => {
    if (useStoryboardStore.getState().referenceImages.length > 0) return;
    axios
      .get(`${API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        useStoryboardStore.getState().set({
          referenceImages: res.data.references || [],
        });
      })
      .catch((err) => console.warn("[useSceneActions] IP-Adapter references fetch failed:", err));
  }, []);

  const setCurrentSceneIndex = useCallback(
    (idx: number) => sbSet({ currentSceneIndex: idx }),
    [sbSet]
  );

  const handleUpdateScene = useCallback((updates: Partial<Scene>) => {
    const { scenes, currentSceneIndex, updateScene } = useStoryboardStore.getState();
    const current = scenes[currentSceneIndex];
    if (current) updateScene(current.client_id, updates);
  }, []);

  const handlePinToggle = useCallback(async () => {
    const { scenes, currentSceneIndex, updateScene } = useStoryboardStore.getState();
    const current = scenes[currentSceneIndex];
    if (!current) return;

    // 토글 OFF
    if (current.environment_reference_id) {
      updateScene(current.client_id, { environment_reference_id: null });
      return;
    }

    // Stage 배경 참조 설정 (현재 또는 제거된 background_id)
    const bgId =
      current.background_id || (current as Record<string, unknown>)._cleared_background_id;
    if (!bgId) {
      showToast("Stage 배경이 없습니다. Stage에서 배경을 먼저 생성하세요.", "error");
      return;
    }

    try {
      const res = await axios.get(`${API_BASE}/storyboards/backgrounds/${bgId}/asset-id`);
      const assetId = res.data?.image_asset_id;
      if (!assetId) {
        showToast("배경 이미지가 아직 생성되지 않았습니다.", "error");
        return;
      }
      updateScene(current.client_id, {
        environment_reference_id: assetId,
        environment_reference_weight: 0.3,
      });
      showToast("Stage 배경을 참조로 설정했습니다.", "success");
    } catch {
      showToast("배경 정보를 조회할 수 없습니다.", "error");
    }
  }, [showToast]);

  const handleRemoveScene = useCallback(
    async (clientId: string) => {
      const ok = await confirm({
        title: "씬 삭제",
        message: "이 씬을 삭제하시겠습니까?",
        confirmLabel: "삭제",
        variant: "danger",
      });
      if (ok) useStoryboardStore.getState().removeScene(clientId);
    },
    [confirm]
  );

  const handleAddScene = useCallback(() => {
    const { scenes, baseNegativePromptA } = useStoryboardStore.getState();
    const newScene = {
      id: 0,
      client_id: generateSceneClientId(),
      order: scenes.length,
      script: "",
      speaker: "Narrator" as const,
      duration: 3,
      image_prompt: "",
      image_prompt_ko: "",
      image_url: null,
      // Backend SSOT fallback: /presets API image_defaults
      width: DEFAULT_IMAGE_WIDTH,
      height: DEFAULT_IMAGE_HEIGHT,
      negative_prompt: baseNegativePromptA,
      scene_mode: "single" as const,
      isGenerating: false,
      debug_payload: "",
    };
    setScenes([...scenes, newScene]);
    sbSet({ currentSceneIndex: scenes.length });
  }, [setScenes, sbSet]);

  return {
    setCurrentSceneIndex,
    handleUpdateScene,
    handlePinToggle,
    handleRemoveScene,
    handleAddScene,
    confirm,
    dialogProps,
  };
}
