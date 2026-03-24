import { describe, it, expect } from "vitest";
import type { Scene } from "../../types";

/**
 * Tests for resolving pinned scene order from environment_reference_id.
 * The environment_reference_id stores a media_asset_id, not scene_id.
 * We need to find the scene whose image_asset_id matches to display the order.
 */

const createScene = (overrides: Partial<Scene> = {}): Scene => ({
  id: overrides.id ?? 1,
  client_id: overrides.client_id ?? `scene-${overrides.id ?? 1}`,
  order: overrides.order ?? 1,
  script: "Test",
  speaker: "speaker_1",
  duration: 5,
  image_prompt: "test",
  image_prompt_ko: "",
  image_url: null,
  negative_prompt: "",
  isGenerating: false,
  debug_payload: "",
  ...overrides,
});

/** Mirrors the logic in ScenesTab.tsx */
function resolvePinnedSceneOrder(
  scenes: Scene[],
  environmentReferenceId: number | null | undefined
): number | undefined {
  if (!environmentReferenceId) return undefined;
  return scenes.find((s) => s.image_asset_id === environmentReferenceId)?.order;
}

describe("resolvePinnedSceneOrder", () => {
  const scenes = [
    createScene({ id: 10, order: 1, image_asset_id: 100 }),
    createScene({ id: 11, order: 2, image_asset_id: 101 }),
    createScene({ id: 12, order: 3, image_asset_id: 102, environment_reference_id: 100 }),
    createScene({ id: 13, order: 4, image_asset_id: 103, environment_reference_id: 101 }),
  ];

  it("returns order of referenced scene", () => {
    expect(resolvePinnedSceneOrder(scenes, 100)).toBe(1);
  });

  it("returns order of second referenced scene", () => {
    expect(resolvePinnedSceneOrder(scenes, 101)).toBe(2);
  });

  it("returns undefined when no environment_reference_id", () => {
    expect(resolvePinnedSceneOrder(scenes, null)).toBeUndefined();
    expect(resolvePinnedSceneOrder(scenes, undefined)).toBeUndefined();
  });

  it("returns undefined when referenced asset not found", () => {
    expect(resolvePinnedSceneOrder(scenes, 999)).toBeUndefined();
  });

  it("handles empty scenes array", () => {
    expect(resolvePinnedSceneOrder([], 100)).toBeUndefined();
  });

  it("finds correct scene when multiple have images", () => {
    const manyScenes = [
      createScene({ id: 1, order: 1, image_asset_id: 200 }),
      createScene({ id: 2, order: 2, image_asset_id: 201 }),
      createScene({ id: 3, order: 3, image_asset_id: 202 }),
      createScene({ id: 4, order: 4, environment_reference_id: 201 }),
    ];
    expect(resolvePinnedSceneOrder(manyScenes, 201)).toBe(2);
  });
});
