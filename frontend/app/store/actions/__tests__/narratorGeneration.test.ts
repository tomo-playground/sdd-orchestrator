import { describe, it, expect } from "vitest";

/**
 * Tests for Narrator scene generation logic.
 * Validates that ControlNet and IP-Adapter are correctly disabled for Narrator scenes.
 */

describe("Narrator scene generation payload", () => {
  // Mirrors the logic in imageActions.ts:generateSceneImageFor (lines 119-132)
  function buildControlPayload(
    speaker: string,
    useControlnet: boolean,
    controlnetWeight: number,
    useIpAdapter: boolean,
    ipAdapterReference: string,
    ipAdapterWeight: number
  ) {
    const isNarrator = speaker === "Narrator";
    const controlnetPayload =
      useControlnet && !isNarrator
        ? { use_controlnet: true, controlnet_weight: controlnetWeight }
        : { use_controlnet: false };
    const ipAdapterPayload =
      useIpAdapter && ipAdapterReference && !isNarrator
        ? {
            use_ip_adapter: true,
            ip_adapter_reference: ipAdapterReference,
            ip_adapter_weight: ipAdapterWeight,
          }
        : { use_ip_adapter: false };
    return { ...controlnetPayload, ...ipAdapterPayload };
  }

  it("enables ControlNet for speaker A when setting is on", () => {
    const result = buildControlPayload("A", true, 0.8, false, "", 0.7);
    expect(result.use_controlnet).toBe(true);
    expect(result.controlnet_weight).toBe(0.8);
  });

  it("disables ControlNet for Narrator even when setting is on", () => {
    const result = buildControlPayload("Narrator", true, 0.8, false, "", 0.7);
    expect(result.use_controlnet).toBe(false);
    expect(result).not.toHaveProperty("controlnet_weight");
  });

  it("enables IP-Adapter for speaker A with reference", () => {
    const result = buildControlPayload("A", false, 0.8, true, "flat_color_girl", 0.35);
    expect(result.use_ip_adapter).toBe(true);
    expect(result.ip_adapter_reference).toBe("flat_color_girl");
    expect(result.ip_adapter_weight).toBe(0.35);
  });

  it("disables IP-Adapter for Narrator even with reference", () => {
    const result = buildControlPayload("Narrator", false, 0.8, true, "flat_color_girl", 0.35);
    expect(result.use_ip_adapter).toBe(false);
    expect(result).not.toHaveProperty("ip_adapter_reference");
  });

  it("disables IP-Adapter for speaker B without reference", () => {
    const result = buildControlPayload("B", false, 0.8, true, "", 0.35);
    expect(result.use_ip_adapter).toBe(false);
  });

  it("disables both for Narrator when both are globally on", () => {
    const result = buildControlPayload("Narrator", true, 0.8, true, "flat_color_girl", 0.35);
    expect(result.use_controlnet).toBe(false);
    expect(result.use_ip_adapter).toBe(false);
  });

  it("enables both for speaker A when both are globally on", () => {
    const result = buildControlPayload("A", true, 0.8, true, "flat_color_girl", 0.35);
    expect(result.use_controlnet).toBe(true);
    expect(result.use_ip_adapter).toBe(true);
  });
});

describe("Batch generation Narrator payload", () => {
  // Mirrors the logic in imageGeneration.ts buildSceneRequest
  function buildBatchControlPayload(
    speaker: string,
    useControlnet: boolean,
    useIpAdapter: boolean,
    ref: string
  ) {
    const isNarrator = speaker === "Narrator";
    return {
      use_controlnet: useControlnet && !isNarrator,
      use_ip_adapter: useIpAdapter && !!ref && !isNarrator,
      ip_adapter_reference: isNarrator ? undefined : ref || undefined,
    };
  }

  it("disables ControlNet for Narrator in batch mode", () => {
    const result = buildBatchControlPayload("Narrator", true, false, "");
    expect(result.use_controlnet).toBe(false);
  });

  it("disables IP-Adapter for Narrator in batch mode", () => {
    const result = buildBatchControlPayload("Narrator", false, true, "flat_color_girl");
    expect(result.use_ip_adapter).toBe(false);
    expect(result.ip_adapter_reference).toBeUndefined();
  });

  it("enables ControlNet for speaker A in batch mode", () => {
    const result = buildBatchControlPayload("A", true, false, "");
    expect(result.use_controlnet).toBe(true);
  });

  it("enables IP-Adapter for speaker B in batch mode", () => {
    const result = buildBatchControlPayload("B", false, true, "cool_boy");
    expect(result.use_ip_adapter).toBe(true);
    expect(result.ip_adapter_reference).toBe("cool_boy");
  });
});
