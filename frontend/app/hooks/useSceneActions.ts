import { useCallback, useEffect } from "react";
import axios from "axios";
import { useConfirm } from "../components/ui/ConfirmDialog";
import { useStoryboardStore } from "../store/useStoryboardStore";
import { useUIStore } from "../store/useUIStore";
import { API_BASE, ADMIN_API_BASE } from "../constants";
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
  // Fetch IP-Adapter reference images on mount
  useEffect(() => {
    axios
      .get(`${ADMIN_API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        useStoryboardStore.getState().set({
          referenceImages: res.data.references || [],
        });
      })
      .catch(() => {});
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

    if (current.environment_reference_id) {
      updateScene(current.client_id, { environment_reference_id: null });
      return;
    }

    const currentIdx = scenes.findIndex((s) => s.client_id === current.client_id);
    let referenceScene = null;

    for (let i = currentIdx - 1; i >= 0; i--) {
      if (scenes[i].image_asset_id) {
        referenceScene = scenes[i];
        break;
      }
    }

    if (!referenceScene) {
      showToast("이전 씬에 고정할 배경 이미지가 없습니다.", "error");
      return;
    }

    updateScene(current.client_id, {
      environment_reference_id: referenceScene.image_asset_id,
      environment_reference_weight: 0.3,
    });
    showToast(`Scene ${referenceScene.order + 1}의 배경을 참조로 설정했습니다.`, "success");
  }, [showToast]);

  const handleRemoveScene = useCallback(
    async (clientId: string) => {
      const ok = await confirm({
        title: "Remove Scene",
        message: "Remove this scene?",
        confirmLabel: "Remove",
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
      width: 512,
      height: 768,
      negative_prompt: baseNegativePromptA,
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
