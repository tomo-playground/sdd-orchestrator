import type { Scene } from "../types";
import { shouldAutoPin, findPreviousSceneWithImage } from "./autoPin";

type UpdateSceneFn = (clientId: string, updates: Partial<Scene>) => void;

type AutoPinResult = {
  success: boolean;
  message: string;
} | null;

/**
 * Apply auto-pin after image generation if scene has _auto_pin_previous flag
 * @param scenes - All scenes
 * @param currentClientId - The scene's client_id that just got its image generated
 * @param updateScene - Function to update scene state
 * @returns Result with success message, or null if no action taken
 */
export function applyAutoPinAfterGeneration(
  scenes: Scene[],
  currentClientId: string,
  updateScene: UpdateSceneFn
): AutoPinResult {
  const currentScene = scenes.find((s) => s.client_id === currentClientId);
  if (!currentScene) return null;

  // Check if auto-pin should be applied
  if (!shouldAutoPin(currentScene)) return null;

  // Find previous scene with image
  const referenceScene = findPreviousSceneWithImage(scenes, currentClientId);
  if (!referenceScene || !referenceScene.image_asset_id) return null;

  // Apply pin
  updateScene(currentClientId, {
    environment_reference_id: referenceScene.image_asset_id,
    environment_reference_weight: 0.3,
  });

  return {
    success: true,
    message: `Scene ${referenceScene.order}의 배경을 참조로 설정했습니다`,
  };
}
