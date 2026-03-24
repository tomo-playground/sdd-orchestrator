import { describe, it, expect } from "vitest";
import { shouldAutoPin, findPreviousSceneWithImage } from "../autoPin";
import type { Scene } from "../../types";

// Helper to create a scene
const createScene = (overrides: Partial<Scene> = {}): Scene => ({
  id: overrides.id ?? 1,
  client_id: overrides.client_id ?? `scene-${overrides.id ?? 1}`,
  order: overrides.order ?? 0,
  script: "Test script",
  speaker: "speaker_1",
  duration: 5,
  image_prompt: "1girl, standing",
  image_prompt_ko: "테스트",
  image_url: overrides.image_url ?? null,
  image_asset_id: overrides.image_asset_id ?? undefined,
  negative_prompt: "bad quality",
  isGenerating: false,
  debug_payload: "",
  environment_reference_id: overrides.environment_reference_id ?? null,
  environment_reference_weight: overrides.environment_reference_weight ?? 0.3,
  _auto_pin_previous: overrides._auto_pin_previous ?? false,
  ...overrides,
});

describe("autoPin utilities", () => {
  describe("shouldAutoPin", () => {
    it("should return false for scene without _auto_pin_previous flag", () => {
      const scene = createScene({ _auto_pin_previous: false });
      expect(shouldAutoPin(scene)).toBe(false);
    });

    it("should return false for scene already pinned", () => {
      const scene = createScene({
        _auto_pin_previous: true,
        environment_reference_id: 123,
      });
      expect(shouldAutoPin(scene)).toBe(false);
    });

    it("should return true for scene with flag and not pinned", () => {
      const scene = createScene({
        _auto_pin_previous: true,
        environment_reference_id: null,
      });
      expect(shouldAutoPin(scene)).toBe(true);
    });

    it("should return false if scene has background_id (Stage BG)", () => {
      const scene = createScene({
        _auto_pin_previous: true,
        environment_reference_id: null,
        background_id: 10,
      });
      expect(shouldAutoPin(scene)).toBe(false);
    });

    it("should return false if _auto_pin_previous is undefined", () => {
      const scene = createScene({ _auto_pin_previous: undefined });
      expect(shouldAutoPin(scene)).toBe(false);
    });
  });

  describe("findPreviousSceneWithImage", () => {
    it("should find previous scene with image_asset_id", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100, image_url: "http://test.com/0.png" }),
        createScene({ id: 1, order: 1, image_asset_id: undefined, image_url: null }),
        createScene({ id: 2, order: 2, image_asset_id: undefined, image_url: null }),
      ];

      const result = findPreviousSceneWithImage(scenes, "scene-2");
      expect(result).toEqual(scenes[0]);
      expect(result?.image_asset_id).toBe(100);
    });

    it("should find immediately previous scene with image", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100, image_url: "http://test.com/0.png" }),
        createScene({ id: 1, order: 1, image_asset_id: 101, image_url: "http://test.com/1.png" }),
        createScene({ id: 2, order: 2, image_asset_id: undefined, image_url: null }),
      ];

      const result = findPreviousSceneWithImage(scenes, "scene-2");
      expect(result).toEqual(scenes[1]);
      expect(result?.image_asset_id).toBe(101);
    });

    it("should return null if no previous scenes", () => {
      const scenes = [createScene({ id: 0, order: 0, image_asset_id: undefined, image_url: null })];

      const result = findPreviousSceneWithImage(scenes, "scene-0");
      expect(result).toBeNull();
    });

    it("should return null if no previous scenes have images", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: undefined, image_url: null }),
        createScene({ id: 1, order: 1, image_asset_id: undefined, image_url: null }),
        createScene({ id: 2, order: 2, image_asset_id: undefined, image_url: null }),
      ];

      const result = findPreviousSceneWithImage(scenes, "scene-2");
      expect(result).toBeNull();
    });

    it("should skip scenes without image_asset_id", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100, image_url: "http://test.com/0.png" }),
        createScene({
          id: 1,
          order: 1,
          image_asset_id: undefined,
          image_url: "http://test.com/1.png",
        }), // has URL but no asset_id
        createScene({ id: 2, order: 2, image_asset_id: undefined, image_url: null }),
      ];

      const result = findPreviousSceneWithImage(scenes, "scene-2");
      expect(result).toEqual(scenes[0]); // Skip scene 1, return scene 0
      expect(result?.image_asset_id).toBe(100);
    });

    it("should handle invalid sceneId gracefully", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100, image_url: "http://test.com/0.png" }),
      ];

      const result = findPreviousSceneWithImage(scenes, "scene-999");
      expect(result).toBeNull();
    });

    it("should handle empty scenes array", () => {
      const result = findPreviousSceneWithImage([], "scene-0");
      expect(result).toBeNull();
    });
  });
});
