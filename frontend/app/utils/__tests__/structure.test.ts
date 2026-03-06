import { describe, it, expect } from "vitest";
import { isMultiCharStructure } from "../structure";

describe("isMultiCharStructure", () => {
  it("returns true for Dialogue (any case)", () => {
    expect(isMultiCharStructure("Dialogue")).toBe(true);
    expect(isMultiCharStructure("dialogue")).toBe(true);
    expect(isMultiCharStructure("DIALOGUE")).toBe(true);
  });

  it("returns true for Narrated Dialogue (any case)", () => {
    expect(isMultiCharStructure("Narrated Dialogue")).toBe(true);
    expect(isMultiCharStructure("narrated dialogue")).toBe(true);
  });

  it("returns false for Monologue", () => {
    expect(isMultiCharStructure("Monologue")).toBe(false);
    expect(isMultiCharStructure("monologue")).toBe(false);
  });

  it("returns false for Narration", () => {
    expect(isMultiCharStructure("Narration")).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isMultiCharStructure("")).toBe(false);
  });
});
