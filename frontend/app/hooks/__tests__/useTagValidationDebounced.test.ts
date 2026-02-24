import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock useTagValidation
const mockValidateTags = vi.fn();
const mockAutoReplaceTags = vi.fn();
const mockClearValidation = vi.fn();
const mockValidationResult = { ref: null as null | object };

vi.mock("../useTagValidation", () => ({
  default: () => ({
    validationResult: mockValidationResult.ref,
    isValidating: false,
    validateTags: mockValidateTags,
    autoReplaceTags: mockAutoReplaceTags,
    clearValidation: mockClearValidation,
  }),
}));

import useTagValidationDebounced from "../useTagValidationDebounced";

describe("useTagValidationDebounced", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    mockValidationResult.ref = null;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("validates tags after default 800ms debounce", () => {
    renderHook(() => useTagValidationDebounced("brown_hair, blue_eyes", vi.fn()));

    expect(mockValidateTags).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(800);
    });

    expect(mockValidateTags).toHaveBeenCalledWith(["brown_hair", "blue_eyes"]);
  });

  it("respects custom debounceMs", () => {
    renderHook(() =>
      useTagValidationDebounced("brown_hair", vi.fn(), { debounceMs: 300 })
    );

    act(() => {
      vi.advanceTimersByTime(299);
    });
    expect(mockValidateTags).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(mockValidateTags).toHaveBeenCalledWith(["brown_hair"]);
  });

  it("clears validation for empty prompt", () => {
    renderHook(() => useTagValidationDebounced("", vi.fn()));

    expect(mockClearValidation).toHaveBeenCalled();
    expect(mockValidateTags).not.toHaveBeenCalled();
  });

  it("clears validation for null/undefined prompt", () => {
    renderHook(() => useTagValidationDebounced(null, vi.fn()));
    expect(mockClearValidation).toHaveBeenCalled();

    vi.clearAllMocks();
    renderHook(() => useTagValidationDebounced(undefined, vi.fn()));
    expect(mockClearValidation).toHaveBeenCalled();
  });

  it("clears validation for whitespace-only prompt", () => {
    renderHook(() => useTagValidationDebounced("   ", vi.fn()));
    expect(mockClearValidation).toHaveBeenCalled();
    expect(mockValidateTags).not.toHaveBeenCalled();
  });

  it("does not validate when enabled=false", () => {
    renderHook(() =>
      useTagValidationDebounced("brown_hair", vi.fn(), { enabled: false })
    );

    act(() => {
      vi.advanceTimersByTime(800);
    });

    expect(mockClearValidation).toHaveBeenCalled();
    expect(mockValidateTags).not.toHaveBeenCalled();
  });

  it("cancels pending debounce on prompt change", () => {
    const { rerender } = renderHook(
      ({ prompt }: { prompt: string }) =>
        useTagValidationDebounced(prompt, vi.fn()),
      { initialProps: { prompt: "brown_hair" } }
    );

    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(mockValidateTags).not.toHaveBeenCalled();

    // Change prompt — should cancel the previous timer
    rerender({ prompt: "blue_eyes" });

    act(() => {
      vi.advanceTimersByTime(400);
    });
    // Still not called — new debounce started
    expect(mockValidateTags).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(400);
    });
    // Now called with the new value
    expect(mockValidateTags).toHaveBeenCalledTimes(1);
    expect(mockValidateTags).toHaveBeenCalledWith(["blue_eyes"]);
  });

  it("handleAutoReplace calls onReplace with joined tags", async () => {
    mockAutoReplaceTags.mockResolvedValue(["safe_tag", "another_tag"]);
    const onReplace = vi.fn();

    const { result } = renderHook(() =>
      useTagValidationDebounced("risky_tag, another_tag", onReplace)
    );

    await act(async () => {
      await result.current.handleAutoReplace();
    });

    expect(mockAutoReplaceTags).toHaveBeenCalledWith(["risky_tag", "another_tag"]);
    expect(onReplace).toHaveBeenCalledWith("safe_tag, another_tag");
  });

  it("handleAutoReplace does nothing when prompt is empty", async () => {
    const onReplace = vi.fn();

    const { result } = renderHook(() =>
      useTagValidationDebounced("", onReplace)
    );

    await act(async () => {
      await result.current.handleAutoReplace();
    });

    expect(mockAutoReplaceTags).not.toHaveBeenCalled();
    expect(onReplace).not.toHaveBeenCalled();
  });

  it("handleAutoReplace does nothing when API returns null", async () => {
    mockAutoReplaceTags.mockResolvedValue(null);
    const onReplace = vi.fn();

    const { result } = renderHook(() =>
      useTagValidationDebounced("risky_tag", onReplace)
    );

    await act(async () => {
      await result.current.handleAutoReplace();
    });

    expect(onReplace).not.toHaveBeenCalled();
  });

  it("parseTags correctly splits comma-separated tags", () => {
    renderHook(() =>
      useTagValidationDebounced("  a , b,  ,c  ", vi.fn())
    );

    act(() => {
      vi.advanceTimersByTime(800);
    });

    // Empty strings should be filtered out
    expect(mockValidateTags).toHaveBeenCalledWith(["a", "b", "c"]);
  });

  it("cleans up timer on unmount", () => {
    const { unmount } = renderHook(() =>
      useTagValidationDebounced("brown_hair", vi.fn())
    );

    unmount();

    act(() => {
      vi.advanceTimersByTime(800);
    });

    // Should not validate after unmount
    expect(mockValidateTags).not.toHaveBeenCalled();
  });
});
