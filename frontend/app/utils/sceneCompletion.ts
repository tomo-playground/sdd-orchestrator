/**
 * Scene completion utilities.
 * Shared between SceneFilmstrip (dots) and SceneSidePanel (insights).
 */

/** Checks whether a scene has at least one generated/uploaded image. */
export function hasSceneImage(scene: {
  image_url: string | null;
  candidates?: Array<{ media_asset_id: number }>;
}): boolean {
  return !!scene.image_url || (Array.isArray(scene.candidates) && scene.candidates.length > 0);
}
