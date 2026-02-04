import { describe, it, expect, vi } from "vitest";
import { applyAutoPinAfterGeneration } from "../applyAutoPin";
import type { Scene } from "../../types";

const createScene = (overrides: Partial<Scene> = {}): Scene => ({
  id: overrides.id ?? 1,
  order: overrides.order ?? 0,
  script: "Test",
  speaker: "A",
  duration: 5,
  image_prompt: "test",
  image_prompt_ko: "test",
  image_url: overrides.image_url ?? null,
  image_asset_id: overrides.image_asset_id ?? undefined,
  negative_prompt: "bad",
  isGenerating: false,
  debug_payload: "",
  environment_reference_id: overrides.environment_reference_id ?? null,
  environment_reference_weight: 0.3,
  _auto_pin_previous: overrides._auto_pin_previous ?? false,
  ...overrides,
});

describe("Pin Integration Tests", () => {
  describe("Auto-pin + Manual pin interaction", () => {
    it("should not override manual pin with auto-pin", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({ id: 1, order: 1, image_asset_id: 101 }),
        createScene({
          id: 2,
          order: 2,
          image_asset_id: 102,
          _auto_pin_previous: true,
          environment_reference_id: 100, // Manually pinned to scene 0
        }),
      ];
      const updateScene = vi.fn();

      applyAutoPinAfterGeneration(scenes, 2, updateScene);

      // Should NOT update because already pinned
      expect(updateScene).not.toHaveBeenCalled();
    });

    it("should apply auto-pin when manual pin is removed", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({ id: 1, order: 1, image_asset_id: 101 }),
        createScene({
          id: 2,
          order: 2,
          image_asset_id: 102,
          _auto_pin_previous: true,
          environment_reference_id: null, // Manual pin removed
        }),
      ];
      const updateScene = vi.fn();

      applyAutoPinAfterGeneration(scenes, 2, updateScene);

      // Should apply auto-pin to scene 1
      expect(updateScene).toHaveBeenCalledWith(2, {
        environment_reference_id: 101,
        environment_reference_weight: 0.3,
      });
    });

    it("should respect manual pin to earlier scene over auto-pin suggestion", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({ id: 1, order: 1, image_asset_id: 101 }),
        createScene({ id: 2, order: 2, image_asset_id: 102 }),
        createScene({
          id: 3,
          order: 3,
          image_asset_id: 103,
          _auto_pin_previous: true, // Would auto-pin to scene 2
          environment_reference_id: 100, // But manually pinned to scene 0
        }),
      ];
      const updateScene = vi.fn();

      applyAutoPinAfterGeneration(scenes, 3, updateScene);

      expect(updateScene).not.toHaveBeenCalled();
      expect(scenes[3].environment_reference_id).toBe(100); // Manual pin preserved
    });
  });

  describe("Sequential auto-pin chain", () => {
    it("should create chain: 0 → 1 → 2 → 3", () => {
      const updateScene = vi.fn();

      // Scene 0: no pin (first scene)
      const scenes0 = [createScene({ id: 0, order: 0, image_asset_id: 100 })];
      applyAutoPinAfterGeneration(scenes0, 0, updateScene);
      expect(updateScene).not.toHaveBeenCalled(); // No previous scene

      // Scene 1: auto-pin to Scene 0
      const scenes1 = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({ id: 1, order: 1, image_asset_id: 101, _auto_pin_previous: true }),
      ];
      updateScene.mockClear();
      applyAutoPinAfterGeneration(scenes1, 1, updateScene);
      expect(updateScene).toHaveBeenCalledWith(1, {
        environment_reference_id: 100,
        environment_reference_weight: 0.3,
      });

      // Scene 2: auto-pin to Scene 1
      const scenes2 = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({ id: 1, order: 1, image_asset_id: 101, environment_reference_id: 100 }),
        createScene({ id: 2, order: 2, image_asset_id: 102, _auto_pin_previous: true }),
      ];
      updateScene.mockClear();
      applyAutoPinAfterGeneration(scenes2, 2, updateScene);
      expect(updateScene).toHaveBeenCalledWith(2, {
        environment_reference_id: 101,
        environment_reference_weight: 0.3,
      });

      // Scene 3: auto-pin to Scene 2
      const scenes3 = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({ id: 1, order: 1, image_asset_id: 101, environment_reference_id: 100 }),
        createScene({ id: 2, order: 2, image_asset_id: 102, environment_reference_id: 101 }),
        createScene({ id: 3, order: 3, image_asset_id: 103, _auto_pin_previous: true }),
      ];
      updateScene.mockClear();
      applyAutoPinAfterGeneration(scenes3, 3, updateScene);
      expect(updateScene).toHaveBeenCalledWith(3, {
        environment_reference_id: 102,
        environment_reference_weight: 0.3,
      });
    });

    it("should break chain when _auto_pin_previous is false", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({ id: 1, order: 1, image_asset_id: 101, environment_reference_id: 100 }),
        createScene({ id: 2, order: 2, image_asset_id: 102, _auto_pin_previous: false }), // Location changed
        createScene({ id: 3, order: 3, image_asset_id: 103, _auto_pin_previous: true }),
      ];
      const updateScene = vi.fn();

      // Scene 2: no auto-pin (location changed)
      applyAutoPinAfterGeneration(scenes, 2, updateScene);
      expect(updateScene).not.toHaveBeenCalled();

      // Scene 3: auto-pin to Scene 2 (new location chain starts)
      updateScene.mockClear();
      applyAutoPinAfterGeneration(scenes, 3, updateScene);
      expect(updateScene).toHaveBeenCalledWith(3, {
        environment_reference_id: 102,
        environment_reference_weight: 0.3,
      });
    });
  });

  describe("Edge cases", () => {
    it("should handle missing image_asset_id in chain", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({
          id: 1,
          order: 1,
          image_url: "http://test.com/1.png",
          image_asset_id: undefined,
        }), // Image URL but no asset_id
        createScene({ id: 2, order: 2, image_asset_id: 102, _auto_pin_previous: true }),
      ];
      const updateScene = vi.fn();

      applyAutoPinAfterGeneration(scenes, 2, updateScene);

      // Should skip scene 1 and pin to scene 0
      expect(updateScene).toHaveBeenCalledWith(2, {
        environment_reference_id: 100,
        environment_reference_weight: 0.3,
      });
    });

    it("should handle all scenes without image_asset_id", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: undefined }),
        createScene({ id: 1, order: 1, image_asset_id: undefined }),
        createScene({ id: 2, order: 2, image_asset_id: 102, _auto_pin_previous: true }),
      ];
      const updateScene = vi.fn();

      applyAutoPinAfterGeneration(scenes, 2, updateScene);

      // No previous scene with asset_id
      expect(updateScene).not.toHaveBeenCalled();
    });

    it("should handle scene regeneration (same scene ID)", () => {
      const scenes = [
        createScene({ id: 0, order: 0, image_asset_id: 100 }),
        createScene({
          id: 1,
          order: 1,
          image_asset_id: 101,
          _auto_pin_previous: true,
          environment_reference_id: 100, // Already pinned from first generation
        }),
      ];
      const updateScene = vi.fn();

      // Regenerate scene 1
      applyAutoPinAfterGeneration(scenes, 1, updateScene);

      // Should not re-pin (already pinned)
      expect(updateScene).not.toHaveBeenCalled();
    });
  });
});
