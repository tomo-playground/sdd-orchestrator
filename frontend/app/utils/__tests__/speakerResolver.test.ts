import { describe, it, expect } from "vitest";
import {
  resolveCharacterIdForSpeaker,
  resolveIpAdapterForSpeaker,
  resolveNegativePromptForSpeaker,
  resolveBasePromptForSpeaker,
  resolveCharacterLorasForSpeaker,
} from "../speakerResolver";

describe("resolveCharacterIdForSpeaker", () => {
  const state = { selectedCharacterId: 10, selectedCharacterBId: 20 };

  it("returns selectedCharacterId for speaker A", () => {
    expect(resolveCharacterIdForSpeaker("speaker_1", state)).toBe(10);
  });

  it("returns null for Narrator (background-only scene)", () => {
    expect(resolveCharacterIdForSpeaker("narrator", state)).toBeNull();
  });

  it("returns selectedCharacterBId for speaker B", () => {
    expect(resolveCharacterIdForSpeaker("speaker_2", state)).toBe(20);
  });

  it("returns null when selectedCharacterId is null (A)", () => {
    expect(
      resolveCharacterIdForSpeaker("speaker_1", { selectedCharacterId: null, selectedCharacterBId: 20 })
    ).toBeNull();
  });

  it("returns null when selectedCharacterBId is null (B)", () => {
    expect(
      resolveCharacterIdForSpeaker("speaker_2", { selectedCharacterId: 10, selectedCharacterBId: null })
    ).toBeNull();
  });
});

describe("resolveNegativePromptForSpeaker", () => {
  const negA = "bad_anatomy, lowres";
  const negB = "bad_anatomy, blurry";

  it("returns negativeA for speaker A", () => {
    expect(resolveNegativePromptForSpeaker("speaker_1", negA, negB)).toBe(negA);
  });

  it("returns negativeA for Narrator", () => {
    expect(resolveNegativePromptForSpeaker("narrator", negA, negB)).toBe(negA);
  });

  it("returns negativeB for speaker B", () => {
    expect(resolveNegativePromptForSpeaker("speaker_2", negA, negB)).toBe(negB);
  });

  it("returns empty string when negativeB is empty", () => {
    expect(resolveNegativePromptForSpeaker("speaker_2", negA, "")).toBe("");
  });
});

describe("resolveIpAdapterForSpeaker", () => {
  const state = {
    ipAdapterReference: "flat_color_girl",
    ipAdapterWeight: 0.35,
    ipAdapterReferenceB: "cool_boy",
    ipAdapterWeightB: 0.5,
  };

  it("returns A reference for speaker A", () => {
    const result = resolveIpAdapterForSpeaker("speaker_1", state);
    expect(result.reference).toBe("flat_color_girl");
    expect(result.weight).toBe(0.35);
  });

  it("returns empty reference for Narrator (background-only scene)", () => {
    const result = resolveIpAdapterForSpeaker("narrator", state);
    expect(result.reference).toBe("");
    expect(result.weight).toBe(0);
  });

  it("returns B reference for speaker B", () => {
    const result = resolveIpAdapterForSpeaker("speaker_2", state);
    expect(result.reference).toBe("cool_boy");
    expect(result.weight).toBe(0.5);
  });

  it("returns empty reference when B has no reference", () => {
    const noRef = { ...state, ipAdapterReferenceB: "", ipAdapterWeightB: 0.7 };
    const result = resolveIpAdapterForSpeaker("speaker_2", noRef);
    expect(result.reference).toBe("");
    expect(result.weight).toBe(0.7);
  });
});

describe("resolveBasePromptForSpeaker", () => {
  const promptA = "1girl, solo, red_hair, school_uniform";
  const promptB = "1boy, solo, blue_hair, casual_clothes";

  it("returns basePromptA for speaker A", () => {
    expect(resolveBasePromptForSpeaker("speaker_1", promptA, promptB)).toBe(promptA);
  });

  it("returns basePromptA for Narrator", () => {
    expect(resolveBasePromptForSpeaker("narrator", promptA, promptB)).toBe(promptA);
  });

  it("returns basePromptB for speaker B", () => {
    expect(resolveBasePromptForSpeaker("speaker_2", promptA, promptB)).toBe(promptB);
  });

  it("returns empty string when speaker B prompt is empty", () => {
    expect(resolveBasePromptForSpeaker("speaker_2", promptA, "")).toBe("");
  });
});

describe("resolveCharacterLorasForSpeaker", () => {
  const lorasA = [
    { id: 1, weight: 0.8, name: "Doremi LoRA", lora_type: "character" },
    { id: 2, weight: 0.6, name: "Flat Color Style", lora_type: "style" },
  ];
  const lorasB = [
    { id: 3, weight: 0.9, name: "Takeshi LoRA", lora_type: "character" },
    { id: 4, weight: 0.7, name: "Another Style", lora_type: "style" },
  ];

  // Style LoRA Unification: A and B should return identity-only (style from StyleProfile)
  it("returns character LoRAs only for speaker A (style filtered out for StyleProfile unification)", () => {
    const result = resolveCharacterLorasForSpeaker("speaker_1", lorasA, lorasB);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("Doremi LoRA");
    expect(result[0].lora_type).toBe("character");
    // Style LoRA should NOT be included (comes from StyleProfile instead)
    expect(result.find((l) => l.lora_type === "style")).toBeUndefined();
  });

  it("returns character LoRAs only for speaker B (style filtered out for StyleProfile unification)", () => {
    const result = resolveCharacterLorasForSpeaker("speaker_2", lorasA, lorasB);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("Takeshi LoRA");
    expect(result[0].lora_type).toBe("character");
    // Style LoRA should NOT be included
    expect(result.find((l) => l.lora_type === "style")).toBeUndefined();
  });

  it("returns empty array for Narrator (style LoRAs come from StyleProfile, not character)", () => {
    const result = resolveCharacterLorasForSpeaker("narrator", lorasA, lorasB);
    expect(result).toEqual([]);
  });

  it("returns all character LoRAs when character has multiple", () => {
    const multiCharacter = [
      { id: 1, weight: 0.8, name: "Face LoRA", lora_type: "character" },
      { id: 2, weight: 0.6, name: "Outfit LoRA", lora_type: "character" },
      { id: 3, weight: 0.5, name: "Style LoRA", lora_type: "style" },
    ];
    const result = resolveCharacterLorasForSpeaker("speaker_1", multiCharacter, lorasB);
    expect(result).toHaveLength(2);
    expect(result.every((l) => l.lora_type === "character")).toBe(true);
  });

  it("returns empty array when character has only style LoRAs", () => {
    const styleOnly = [{ id: 1, weight: 0.6, name: "Style Only", lora_type: "style" }];
    const result = resolveCharacterLorasForSpeaker("speaker_1", styleOnly, lorasB);
    expect(result).toEqual([]);
  });

  it("returns empty array when speaker B has no LoRAs", () => {
    const result = resolveCharacterLorasForSpeaker("speaker_2", lorasA, []);
    expect(result).toEqual([]);
    expect(result).toHaveLength(0);
  });

  it("handles empty arrays for both speakers", () => {
    const result = resolveCharacterLorasForSpeaker("speaker_1", [], []);
    expect(result).toEqual([]);
  });
});
