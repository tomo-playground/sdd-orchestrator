import { describe, it, expect, vi } from 'vitest';
import { applyAutoPinAfterGeneration } from '../applyAutoPin';
import type { Scene } from '../../types';

const createScene = (overrides: Partial<Scene> = {}): Scene => ({
  id: overrides.id ?? 1,
  order: overrides.order ?? 0,
  script: 'Test',
  speaker: 'A',
  duration: 5,
  image_prompt: 'test',
  image_prompt_ko: 'test',
  image_url: overrides.image_url ?? null,
  image_asset_id: overrides.image_asset_id ?? undefined,
  negative_prompt: 'bad',
  steps: 25,
  cfg_scale: 7,
  sampler_name: 'DPM++ 2M Karras',
  seed: -1,
  clip_skip: 2,
  isGenerating: false,
  debug_payload: '',
  environment_reference_id: overrides.environment_reference_id ?? null,
  environment_reference_weight: 0.3,
  _auto_pin_previous: overrides._auto_pin_previous ?? false,
  ...overrides,
});

describe('applyAutoPinAfterGeneration', () => {
  it('should not pin if _auto_pin_previous is false', () => {
    const scenes = [
      createScene({ id: 0, order: 0, image_asset_id: 100 }),
      createScene({ id: 1, order: 1, image_asset_id: 101, _auto_pin_previous: false }),
    ];
    const updateScene = vi.fn();

    applyAutoPinAfterGeneration(scenes, 1, updateScene);

    expect(updateScene).not.toHaveBeenCalled();
  });

  it('should not pin if already pinned', () => {
    const scenes = [
      createScene({ id: 0, order: 0, image_asset_id: 100 }),
      createScene({
        id: 1,
        order: 1,
        image_asset_id: 101,
        _auto_pin_previous: true,
        environment_reference_id: 100,
      }),
    ];
    const updateScene = vi.fn();

    applyAutoPinAfterGeneration(scenes, 1, updateScene);

    expect(updateScene).not.toHaveBeenCalled();
  });

  it('should pin to previous scene with image', () => {
    const scenes = [
      createScene({ id: 0, order: 0, image_asset_id: 100 }),
      createScene({ id: 1, order: 1, image_asset_id: 101, _auto_pin_previous: true }),
    ];
    const updateScene = vi.fn();

    applyAutoPinAfterGeneration(scenes, 1, updateScene);

    expect(updateScene).toHaveBeenCalledWith(1, {
      environment_reference_id: 100,
      environment_reference_weight: 0.3,
    });
  });

  it('should not pin if no previous scene with image', () => {
    const scenes = [
      createScene({ id: 0, order: 0, image_asset_id: undefined }),
      createScene({ id: 1, order: 1, image_asset_id: 101, _auto_pin_previous: true }),
    ];
    const updateScene = vi.fn();

    applyAutoPinAfterGeneration(scenes, 1, updateScene);

    expect(updateScene).not.toHaveBeenCalled();
  });

  it('should skip scenes without image_asset_id when finding reference', () => {
    const scenes = [
      createScene({ id: 0, order: 0, image_asset_id: 100 }),
      createScene({ id: 1, order: 1, image_asset_id: undefined }), // No asset
      createScene({ id: 2, order: 2, image_asset_id: 102, _auto_pin_previous: true }),
    ];
    const updateScene = vi.fn();

    applyAutoPinAfterGeneration(scenes, 2, updateScene);

    expect(updateScene).toHaveBeenCalledWith(2, {
      environment_reference_id: 100, // Skip scene 1, use scene 0
      environment_reference_weight: 0.3,
    });
  });

  it('should handle first scene (no previous)', () => {
    const scenes = [
      createScene({ id: 0, order: 0, image_asset_id: 100, _auto_pin_previous: true }),
    ];
    const updateScene = vi.fn();

    applyAutoPinAfterGeneration(scenes, 0, updateScene);

    expect(updateScene).not.toHaveBeenCalled();
  });

  it('should return toast message on success', () => {
    const scenes = [
      createScene({ id: 0, order: 0, image_asset_id: 100 }),
      createScene({ id: 1, order: 1, image_asset_id: 101, _auto_pin_previous: true }),
    ];
    const updateScene = vi.fn();

    const result = applyAutoPinAfterGeneration(scenes, 1, updateScene);

    expect(result).toEqual({
      success: true,
      message: 'Scene 0의 배경을 참조로 설정했습니다',
    });
  });

  it('should return null when no action taken', () => {
    const scenes = [
      createScene({ id: 0, order: 0, image_asset_id: 100 }),
      createScene({ id: 1, order: 1, image_asset_id: 101, _auto_pin_previous: false }),
    ];
    const updateScene = vi.fn();

    const result = applyAutoPinAfterGeneration(scenes, 1, updateScene);

    expect(result).toBeNull();
  });
});
