import { describe, it, expect } from "vitest";
import {
  resolveSceneControlnet,
  resolveSceneIpAdapter,
  resolveSceneMultiGen,
} from "../sceneSettingsResolver";
import type { Scene } from "../../types";

function makeScene(overrides: Partial<Scene> = {}): Scene {
  return {
    id: 1,
    order: 1,
    script: "",
    speaker: "A",
    duration: 3,
    image_prompt: "",
    image_prompt_ko: "",
    image_url: null,
    negative_prompt: "",
    isGenerating: false,
    debug_payload: "",
    ...overrides,
  };
}

const GLOBAL_STATE = {
  useControlnet: true,
  controlnetWeight: 0.8,
  useIpAdapter: true,
  ipAdapterReference: "char_a_ref",
  ipAdapterWeight: 0.7,
  ipAdapterReferenceB: "char_b_ref",
  ipAdapterWeightB: 0.6,
  multiGenEnabled: false,
};

describe("resolveSceneControlnet", () => {
  it("inherits global when scene has null override", () => {
    const scene = makeScene({ use_controlnet: null, controlnet_weight: null });
    const result = resolveSceneControlnet(scene, GLOBAL_STATE);
    expect(result.enabled).toBe(true);
    expect(result.weight).toBe(0.8);
  });

  it("inherits global when scene has undefined override", () => {
    const scene = makeScene();
    const result = resolveSceneControlnet(scene, GLOBAL_STATE);
    expect(result.enabled).toBe(true);
    expect(result.weight).toBe(0.8);
  });

  it("uses scene override when set to false", () => {
    const scene = makeScene({ use_controlnet: false });
    const result = resolveSceneControlnet(scene, GLOBAL_STATE);
    expect(result.enabled).toBe(false);
  });

  it("uses scene override weight", () => {
    const scene = makeScene({ use_controlnet: true, controlnet_weight: 0.5 });
    const result = resolveSceneControlnet(scene, GLOBAL_STATE);
    expect(result.enabled).toBe(true);
    expect(result.weight).toBe(0.5);
  });

  it("scene override false overrides global true", () => {
    const scene = makeScene({ use_controlnet: false });
    const result = resolveSceneControlnet(scene, { useControlnet: true, controlnetWeight: 0.8 });
    expect(result.enabled).toBe(false);
  });
});

describe("resolveSceneIpAdapter", () => {
  it("inherits global for Speaker A", () => {
    const scene = makeScene({ speaker: "A" });
    const result = resolveSceneIpAdapter(scene, GLOBAL_STATE);
    expect(result.enabled).toBe(true);
    expect(result.reference).toBe("char_a_ref");
    expect(result.weight).toBe(0.7);
  });

  it("inherits global for Speaker B with correct reference", () => {
    const scene = makeScene({ speaker: "B" });
    const result = resolveSceneIpAdapter(scene, GLOBAL_STATE);
    expect(result.enabled).toBe(true);
    expect(result.reference).toBe("char_b_ref");
    expect(result.weight).toBe(0.6);
  });

  it("uses scene override reference", () => {
    const scene = makeScene({
      speaker: "A",
      use_ip_adapter: true,
      ip_adapter_reference: "custom_ref",
      ip_adapter_weight: 0.9,
    });
    const result = resolveSceneIpAdapter(scene, GLOBAL_STATE);
    expect(result.enabled).toBe(true);
    expect(result.reference).toBe("custom_ref");
    expect(result.weight).toBe(0.9);
  });

  it("scene disable overrides global enable", () => {
    const scene = makeScene({ use_ip_adapter: false });
    const result = resolveSceneIpAdapter(scene, GLOBAL_STATE);
    expect(result.enabled).toBe(false);
  });

  it("Narrator returns empty reference from speaker resolver", () => {
    const scene = makeScene({ speaker: "Narrator" });
    const result = resolveSceneIpAdapter(scene, GLOBAL_STATE);
    expect(result.reference).toBe("");
  });
});

describe("resolveSceneMultiGen", () => {
  it("inherits global when scene has null", () => {
    const scene = makeScene({ multi_gen_enabled: null });
    const result = resolveSceneMultiGen(scene, GLOBAL_STATE);
    expect(result).toBe(false);
  });

  it("inherits global when scene has undefined", () => {
    const scene = makeScene();
    const result = resolveSceneMultiGen(scene, GLOBAL_STATE);
    expect(result).toBe(false);
  });

  it("scene override true overrides global false", () => {
    const scene = makeScene({ multi_gen_enabled: true });
    const result = resolveSceneMultiGen(scene, { multiGenEnabled: false });
    expect(result).toBe(true);
  });

  it("scene override false overrides global true", () => {
    const scene = makeScene({ multi_gen_enabled: false });
    const result = resolveSceneMultiGen(scene, { multiGenEnabled: true });
    expect(result).toBe(false);
  });
});
