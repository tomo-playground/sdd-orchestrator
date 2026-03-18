import { useCallback, useEffect } from "react";
import axios from "axios";
import { useConfirm } from "../components/ui/ConfirmDialog";
import { useStoryboardStore } from "../store/useStoryboardStore";
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
    handleRemoveScene,
    handleAddScene,
    confirm,
    dialogProps,
  };
}
