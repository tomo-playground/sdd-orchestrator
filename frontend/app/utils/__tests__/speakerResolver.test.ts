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
    expect(resolveCharacterIdForSpeaker("A", state)).toBe(10);
  });

  it("returns selectedCharacterId for Narrator", () => {
    expect(resolveCharacterIdForSpeaker("Narrator", state)).toBe(10);
  });

  it("returns selectedCharacterBId for speaker B", () => {
    expect(resolveCharacterIdForSpeaker("B", state)).toBe(20);
  });

  it("returns null when selectedCharacterId is null (A)", () => {
    expect(
      resolveCharacterIdForSpeaker("A", { selectedCharacterId: null, selectedCharacterBId: 20 })
    ).toBeNull();
  });

  it("returns null when selectedCharacterBId is null (B)", () => {
    expect(
      resolveCharacterIdForSpeaker("B", { selectedCharacterId: 10, selectedCharacterBId: null })
    ).toBeNull();
  });
});

describe("resolveNegativePromptForSpeaker", () => {
  const negA = "bad_anatomy, lowres";
  const negB = "bad_anatomy, blurry";

  it("returns negativeA for speaker A", () => {
    expect(resolveNegativePromptForSpeaker("A", negA, negB)).toBe(negA);
  });

  it("returns negativeA for Narrator", () => {
    expect(resolveNegativePromptForSpeaker("Narrator", negA, negB)).toBe(negA);
  });

  it("returns negativeB for speaker B", () => {
    expect(resolveNegativePromptForSpeaker("B", negA, negB)).toBe(negB);
  });

  it("returns empty string when negativeB is empty", () => {
    expect(resolveNegativePromptForSpeaker("B", negA, "")).toBe("");
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
    const result = resolveIpAdapterForSpeaker("A", state);
    expect(result.reference).toBe("flat_color_girl");
    expect(result.weight).toBe(0.35);
  });

  it("returns A reference for Narrator", () => {
    const result = resolveIpAdapterForSpeaker("Narrator", state);
    expect(result.reference).toBe("flat_color_girl");
    expect(result.weight).toBe(0.35);
  });

  it("returns B reference for speaker B", () => {
    const result = resolveIpAdapterForSpeaker("B", state);
    expect(result.reference).toBe("cool_boy");
    expect(result.weight).toBe(0.5);
  });

  it("returns empty reference when B has no reference", () => {
    const noRef = { ...state, ipAdapterReferenceB: "", ipAdapterWeightB: 0.7 };
    const result = resolveIpAdapterForSpeaker("B", noRef);
    expect(result.reference).toBe("");
    expect(result.weight).toBe(0.7);
  });
});

describe("resolveBasePromptForSpeaker", () => {
  const promptA = "1girl, solo, red_hair, school_uniform";
  const promptB = "1boy, solo, blue_hair, casual_clothes";

  it("returns basePromptA for speaker A", () => {
    expect(resolveBasePromptForSpeaker("A", promptA, promptB)).toBe(promptA);
  });

  it("returns basePromptA for Narrator", () => {
    expect(resolveBasePromptForSpeaker("Narrator", promptA, promptB)).toBe(promptA);
  });

  it("returns basePromptB for speaker B", () => {
    expect(resolveBasePromptForSpeaker("B", promptA, promptB)).toBe(promptB);
  });

  it("returns empty string when speaker B prompt is empty", () => {
    expect(resolveBasePromptForSpeaker("B", promptA, "")).toBe("");
  });
});

describe("resolveCharacterLorasForSpeaker", () => {
  const lorasA = [
    { id: 1, weight: 0.8, name: "Doremi LoRA" },
    { id: 2, weight: 0.6, name: "School Uniform" },
  ];
  const lorasB = [{ id: 3, weight: 0.9, name: "Takeshi LoRA" }];

  it("returns characterLoras for speaker A", () => {
    const result = resolveCharacterLorasForSpeaker("A", lorasA, lorasB);
    expect(result).toEqual(lorasA);
    expect(result).toHaveLength(2);
  });

  it("returns characterLoras for Narrator", () => {
    const result = resolveCharacterLorasForSpeaker("Narrator", lorasA, lorasB);
    expect(result).toEqual(lorasA);
  });

  it("returns characterBLoras for speaker B", () => {
    const result = resolveCharacterLorasForSpeaker("B", lorasA, lorasB);
    expect(result).toEqual(lorasB);
    expect(result).toHaveLength(1);
  });

  it("returns empty array when speaker B has no LoRAs", () => {
    const result = resolveCharacterLorasForSpeaker("B", lorasA, []);
    expect(result).toEqual([]);
    expect(result).toHaveLength(0);
  });

  it("handles empty arrays for both speakers", () => {
    const result = resolveCharacterLorasForSpeaker("A", [], []);
    expect(result).toEqual([]);
  });
});
