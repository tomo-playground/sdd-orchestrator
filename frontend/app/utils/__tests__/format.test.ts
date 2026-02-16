import { describe, it, expect, vi, afterEach } from "vitest";
import { formatRelativeTime } from "../format";

describe("formatRelativeTime", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  const NOW = new Date("2026-02-16T12:00:00Z").getTime();

  function mockNow() {
    vi.spyOn(Date, "now").mockReturnValue(NOW);
  }

  // --- epoch ms input ---

  it("returns 'just now' for < 1 minute ago (epoch ms)", () => {
    mockNow();
    expect(formatRelativeTime(NOW - 30_000)).toBe("just now");
  });

  it("returns 'just now' for 0ms ago", () => {
    mockNow();
    expect(formatRelativeTime(NOW)).toBe("just now");
  });

  it("returns minutes for 1-59 minutes ago", () => {
    mockNow();
    expect(formatRelativeTime(NOW - 5 * 60_000)).toBe("5m ago");
    expect(formatRelativeTime(NOW - 59 * 60_000)).toBe("59m ago");
  });

  it("returns '1m ago' at exactly 1 minute", () => {
    mockNow();
    expect(formatRelativeTime(NOW - 60_000)).toBe("1m ago");
  });

  it("returns hours for 1-23 hours ago", () => {
    mockNow();
    expect(formatRelativeTime(NOW - 2 * 3_600_000)).toBe("2h ago");
    expect(formatRelativeTime(NOW - 23 * 3_600_000)).toBe("23h ago");
  });

  it("returns '1h ago' at exactly 60 minutes", () => {
    mockNow();
    expect(formatRelativeTime(NOW - 60 * 60_000)).toBe("1h ago");
  });

  it("returns days for 24+ hours ago", () => {
    mockNow();
    expect(formatRelativeTime(NOW - 24 * 3_600_000)).toBe("1d ago");
    expect(formatRelativeTime(NOW - 72 * 3_600_000)).toBe("3d ago");
  });

  // --- ISO string input ---

  it("handles ISO string input", () => {
    mockNow();
    const tenMinAgo = new Date(NOW - 10 * 60_000).toISOString();
    expect(formatRelativeTime(tenMinAgo)).toBe("10m ago");
  });

  it("handles ISO string for hours", () => {
    mockNow();
    const fiveHoursAgo = new Date(NOW - 5 * 3_600_000).toISOString();
    expect(formatRelativeTime(fiveHoursAgo)).toBe("5h ago");
  });

  it("handles ISO string for days", () => {
    mockNow();
    const twoDaysAgo = new Date(NOW - 48 * 3_600_000).toISOString();
    expect(formatRelativeTime(twoDaysAgo)).toBe("2d ago");
  });
});
