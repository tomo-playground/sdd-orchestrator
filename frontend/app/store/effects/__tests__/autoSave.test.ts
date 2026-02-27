import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useStoryboardStore } from "../../useStoryboardStore";
import { useUIStore } from "../../useUIStore";

vi.mock("../../actions/storyboardActions", () => ({
  persistStoryboard: vi.fn().mockResolvedValue(true),
}));

import { persistStoryboard } from "../../actions/storyboardActions";
import { initAutoSave } from "../autoSave";

// Access module internals for reset between tests
let cleanup: (() => void) | null = null;

function triggerSubscription(state: Record<string, unknown>, prevState: Record<string, unknown>) {
  const calls = vi.mocked(useStoryboardStore.subscribe).mock.calls;
  const listener = calls[calls.length - 1]?.[0];
  if (listener) listener(state as never, prevState as never);
}

describe("autoSave", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    vi.spyOn(useStoryboardStore, "subscribe").mockReturnValue(vi.fn());
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      isDirty: true,
      scenes: [{ id: 1, client_id: "c1", script: "test" }],
    } as never);
    vi.spyOn(useUIStore, "getState").mockReturnValue({
      isAutoRunning: false,
    } as never);
  });

  afterEach(() => {
    if (cleanup) {
      cleanup();
      cleanup = null;
    }
    vi.useRealTimers();
  });

  it("isDirty 변경 시 debounce 후 persistStoryboard 호출", async () => {
    cleanup = initAutoSave();

    triggerSubscription({ isDirty: true }, { isDirty: false });

    // Before debounce
    expect(persistStoryboard).not.toHaveBeenCalled();

    // After 2s debounce
    await vi.advanceTimersByTimeAsync(2000);

    expect(persistStoryboard).toHaveBeenCalledTimes(1);
  });

  it("isDirty가 false일 때 저장하지 않음", async () => {
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      isDirty: false,
      scenes: [{ id: 1, client_id: "c1" }],
    } as never);

    cleanup = initAutoSave();

    // isDirty stays false → guard should skip
    triggerSubscription({ isDirty: false }, { isDirty: false });

    await vi.advanceTimersByTimeAsync(2000);

    expect(persistStoryboard).not.toHaveBeenCalled();
  });

  it("debounce 중 추가 변경 시 타이머 리셋", async () => {
    cleanup = initAutoSave();

    triggerSubscription({ isDirty: true }, { isDirty: false });

    // Advance 1.5s (not yet fired)
    await vi.advanceTimersByTimeAsync(1500);
    expect(persistStoryboard).not.toHaveBeenCalled();

    // Trigger again → resets timer
    triggerSubscription({ isDirty: true }, { isDirty: false });

    // Another 1.5s (total 3s from first, but only 1.5s from second)
    await vi.advanceTimersByTimeAsync(1500);
    expect(persistStoryboard).not.toHaveBeenCalled();

    // 0.5s more → 2s from second trigger
    await vi.advanceTimersByTimeAsync(500);
    expect(persistStoryboard).toHaveBeenCalledTimes(1);
  });

  it("isSaving 중 중복 저장 방지", async () => {
    // Make persistStoryboard take time
    let resolvePromise: () => void;
    vi.mocked(persistStoryboard).mockImplementation(
      () =>
        new Promise<boolean>((resolve) => {
          resolvePromise = () => resolve(true);
        })
    );

    cleanup = initAutoSave();

    // First trigger
    triggerSubscription({ isDirty: true }, { isDirty: false });
    await vi.advanceTimersByTimeAsync(2000);
    expect(persistStoryboard).toHaveBeenCalledTimes(1);

    // Second trigger while first is still saving
    triggerSubscription({ isDirty: true }, { isDirty: false });
    await vi.advanceTimersByTimeAsync(2000);

    // Should NOT call again because isSaving is true
    expect(persistStoryboard).toHaveBeenCalledTimes(1);

    // Resolve first save
    resolvePromise!();
    await vi.advanceTimersByTimeAsync(0);
  });

  it("cleanup 호출 시 unsubscribe + timer 정리", async () => {
    const unsubscribeFn = vi.fn();
    vi.mocked(useStoryboardStore.subscribe).mockReturnValue(unsubscribeFn);

    cleanup = initAutoSave();

    triggerSubscription({ isDirty: true }, { isDirty: false });

    // Cleanup before debounce fires
    cleanup();
    cleanup = null;

    await vi.advanceTimersByTimeAsync(2000);

    expect(unsubscribeFn).toHaveBeenCalledTimes(1);
    expect(persistStoryboard).not.toHaveBeenCalled();
  });

  it("이중 초기화 시 HMR 가드: cleanup 후 재구독", () => {
    const unsubscribeFn = vi.fn();
    vi.mocked(useStoryboardStore.subscribe).mockReturnValue(unsubscribeFn);

    cleanup = initAutoSave();
    const secondCleanup = initAutoSave();

    // HMR guard: first subscription cleaned up, then re-subscribed
    expect(unsubscribeFn).toHaveBeenCalledTimes(1);
    expect(useStoryboardStore.subscribe).toHaveBeenCalledTimes(2);

    secondCleanup();
    cleanup = null; // secondCleanup already cleaned up
  });

  it("isAutoRunning 중 autoSave 건너뜀", async () => {
    vi.spyOn(useUIStore, "getState").mockReturnValue({
      isAutoRunning: true,
    } as never);

    cleanup = initAutoSave();

    triggerSubscription({ isDirty: true }, { isDirty: false });

    await vi.advanceTimersByTimeAsync(2000);

    // Should NOT call persistStoryboard because isAutoRunning is true
    expect(persistStoryboard).not.toHaveBeenCalled();
  });

  it("이미지 생성 중(isGenerating) autoSave 건너뜀", async () => {
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      isDirty: true,
      scenes: [{ id: 1, client_id: "c1", script: "test", isGenerating: true }],
    } as never);

    cleanup = initAutoSave();

    triggerSubscription({ isDirty: true }, { isDirty: false });

    await vi.advanceTimersByTimeAsync(2000);

    expect(persistStoryboard).not.toHaveBeenCalled();
  });

  it("이미지 생성 완료 후 재스케줄로 저장 실행", async () => {
    // Phase 1: isGenerating: true → 저장 스킵
    const getStateSpy = vi.spyOn(useStoryboardStore, "getState");
    getStateSpy.mockReturnValue({
      isDirty: true,
      scenes: [{ id: 1, client_id: "c1", isGenerating: true }],
    } as never);

    cleanup = initAutoSave();
    triggerSubscription({ isDirty: true }, { isDirty: false });

    await vi.advanceTimersByTimeAsync(2000);
    expect(persistStoryboard).not.toHaveBeenCalled();

    // Phase 2: isGenerating: false → 재스케줄 후 저장
    getStateSpy.mockReturnValue({
      isDirty: true,
      scenes: [{ id: 1, client_id: "c1", isGenerating: false }],
    } as never);

    await vi.advanceTimersByTimeAsync(2000);
    expect(persistStoryboard).toHaveBeenCalledTimes(1);
  });

  it("일부 씬만 생성 중이어도 저장 건너뜀", async () => {
    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      isDirty: true,
      scenes: [
        { id: 1, client_id: "c1", isGenerating: false },
        { id: 2, client_id: "c2", isGenerating: true },
        { id: 3, client_id: "c3", isGenerating: false },
      ],
    } as never);

    cleanup = initAutoSave();
    triggerSubscription({ isDirty: true }, { isDirty: false });

    await vi.advanceTimersByTimeAsync(2000);

    expect(persistStoryboard).not.toHaveBeenCalled();
  });
});
