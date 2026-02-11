import { describe, it, expect } from "vitest";
import { resolveImageUrl } from "../url";

describe("resolveImageUrl", () => {
  it("returns null for null input", () => {
    expect(resolveImageUrl(null)).toBeNull();
  });

  it("returns null for undefined input", () => {
    expect(resolveImageUrl(undefined)).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(resolveImageUrl("")).toBeNull();
  });

  it("returns absolute http URL as-is", () => {
    const url = "http://example.com/img.png";
    expect(resolveImageUrl(url)).toBe(url);
  });

  it("returns absolute https URL as-is", () => {
    const url = "https://cdn.example.com/img.webp";
    expect(resolveImageUrl(url)).toBe(url);
  });

  it("prepends API_BASE to relative path", () => {
    const result = resolveImageUrl("/uploads/characters/1/preview.png");
    expect(result).toMatch(/\/uploads\/characters\/1\/preview\.png$/);
    expect(result!.startsWith("http")).toBe(true);
  });

  it("prepends API_BASE to relative path without leading slash", () => {
    const result = resolveImageUrl("media/img.jpg");
    expect(result).toContain("media/img.jpg");
    expect(result!.startsWith("http")).toBe(true);
  });
});
