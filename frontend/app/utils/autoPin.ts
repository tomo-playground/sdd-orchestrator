import type { Scene } from '../types';

/**
 * Check if a scene should have auto-pin applied
 * @param scene - The scene to check
 * @returns true if scene has _auto_pin_previous flag and is not already pinned
 */
export function shouldAutoPin(scene: Scene): boolean {
  if (!scene._auto_pin_previous) return false;
  if (scene.environment_reference_id) return false;
  return true;
}

/**
 * Find the previous scene with an image_asset_id
 * @param scenes - All scenes in order
 * @param currentSceneId - The current scene's id
 * @returns The previous scene with image, or null if none found
 */
export function findPreviousSceneWithImage(
  scenes: Scene[],
  currentSceneId: number
): Scene | null {
  const currentIndex = scenes.findIndex((s) => s.id === currentSceneId);

  if (currentIndex <= 0) return null; // No previous scenes or not found

  // Search backwards from current scene
  for (let i = currentIndex - 1; i >= 0; i--) {
    if (scenes[i].image_asset_id) {
      return scenes[i];
    }
  }

  return null;
}
