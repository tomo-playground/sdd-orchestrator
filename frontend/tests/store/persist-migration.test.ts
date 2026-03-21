import { describe, it, expect, beforeEach } from "vitest";
import { migrateStoryboardStore } from "../../app/store/useStoryboardStore";

/**
 * Zustand persist store version + migrate 테스트
 * PR #118 Test plan 검증:
 * - localStorage 삭제 후 정상 동작
 * - 기존 데이터 마이그레이션 동작
 */

// Mock localStorage for store initialization tests
const storage = new Map<string, string>();
const mockLocalStorage = {
  getItem: (key: string) => storage.get(key) ?? null,
  setItem: (key: string, value: string) => storage.set(key, value),
  removeItem: (key: string) => storage.delete(key),
  clear: () => storage.clear(),
  length: 0,
  key: (_index: number) => null,
};

beforeEach(() => {
  storage.clear();
  Object.defineProperty(global, "localStorage", {
    value: mockLocalStorage,
    writable: true,
  });
});

describe("localStorage 삭제 후 정상 동작", () => {
  it("useChatStore — localStorage 비어있을 때 기본값으로 초기화", async () => {
    const { useChatStore } = await import("../../app/store/useChatStore");
    const state = useChatStore.getState();

    expect(typeof state.saveMessages).toBe("function");
    expect(typeof state.migrateFromTemp).toBe("function");
  });

  it("useContextStore — localStorage 비어있을 때 기본값으로 초기화", async () => {
    const { useContextStore } = await import("../../app/store/useContextStore");
    const state = useContextStore.getState();

    expect(state.projectId).toBeDefined();
  });

  it("useStoryboardStore — localStorage 비어있을 때 기본값으로 초기화", async () => {
    const { useStoryboardStore } = await import("../../app/store/useStoryboardStore");
    const state = useStoryboardStore.getState();

    expect(state.scenes).toBeDefined();
    expect(Array.isArray(state.scenes)).toBe(true);
  });
});

describe("migrateStoryboardStore — v0→v1", () => {
  it("subtitleFont 삭제", () => {
    const stale = { subtitleFont: "NotoSans", scenes: [], topic: "test" };
    const result = migrateStoryboardStore(stale, 0);
    expect(result).not.toHaveProperty("subtitleFont");
  });

  it("includeSubtitles 삭제", () => {
    const stale = { includeSubtitles: true, scenes: [], topic: "test" };
    const result = migrateStoryboardStore(stale, 0);
    expect(result).not.toHaveProperty("includeSubtitles");
  });

  it("다른 필드는 보존", () => {
    const stale = { subtitleFont: "NotoSans", includeSubtitles: true, topic: "test", scenes: [] };
    const result = migrateStoryboardStore(stale, 0);
    expect(result).toHaveProperty("topic", "test");
    expect(result).toHaveProperty("scenes");
  });

  it("v1 이상 데이터는 변경 없이 반환", () => {
    const current = { sceneTextFont: "NotoSans", scenes: [] };
    const result = migrateStoryboardStore(current, 1);
    expect(result).toHaveProperty("sceneTextFont", "NotoSans");
  });

  it("null 입력 — 빈 객체 반환 (hydration 오류 방지)", () => {
    const result = migrateStoryboardStore(null, 0);
    expect(result).toEqual({});
  });

  it("undefined 입력 — 빈 객체 반환", () => {
    const result = migrateStoryboardStore(undefined, 0);
    expect(result).toEqual({});
  });

  it("배열 입력 — 빈 객체 반환 (오염 데이터 방어)", () => {
    const result = migrateStoryboardStore([], 0);
    expect(result).toEqual({});
  });
});
