import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// localStorage mock must be hoisted before any imports that touch stores
vi.hoisted(() => {
  const store: Record<string, string> = {};
  const mock: Storage = {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      for (const k of Object.keys(store)) delete store[k];
    },
    key: () => null,
    length: 0,
  };
  globalThis.localStorage = mock;
});

import { useAutopilotCheckpoint } from "../../app/hooks/useAutopilotCheckpoint";
import type { UseAutopilotReturn } from "../../app/hooks/useAutopilot";
import type { AutoRunState } from "../../app/hooks/useAutopilot";
import type { AutopilotCheckpoint } from "../../app/types";

// ── helpers ────────────────────────────────────────────────

function makeAutoRunState(overrides: Partial<AutoRunState> = {}): AutoRunState {
  return {
    status: "idle",
    step: "idle",
    message: "",
    ...overrides,
  };
}

function makeAutopilot(stateOverrides: Partial<AutoRunState> = {}): UseAutopilotReturn {
  return {
    autoRunState: makeAutoRunState(stateOverrides),
    autoRunLog: [],
    isAutoRunning: false,
    autoRunProgress: 0,
    startRun: vi.fn(),
    setStep: vi.fn(),
    setDone: vi.fn(),
    setError: vi.fn(),
    checkCancelled: vi.fn(),
    cancel: vi.fn(),
    reset: vi.fn(),
    pushLog: vi.fn(),
    getCheckpoint: vi.fn(() => null),
    initializeFromCheckpoint: vi.fn(),
  };
}

function getLocalStorage(): Record<string, string> {
  // Access internal store via the mock
  return (globalThis.localStorage as unknown as { getItem: (k: string) => string | null }) as never;
}

// ── tests ──────────────────────────────────────────────────

describe("useAutopilotCheckpoint", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("storyboardId가 null인 경우", () => {
    it("localStorage를 읽지 않고 pendingCheckpoint는 null 유지", () => {
      const getItemSpy = vi.spyOn(localStorage, "getItem");
      const autopilot = makeAutopilot();

      const { result } = renderHook(() =>
        useAutopilotCheckpoint(null, autopilot)
      );

      expect(result.current.CKPT_KEY).toBeNull();
      expect(result.current.pendingCheckpoint).toBeNull();
      expect(getItemSpy).not.toHaveBeenCalled();
    });

    it("autoRunState가 running이어도 localStorage에 저장하지 않음", () => {
      const setItemSpy = vi.spyOn(localStorage, "setItem");
      const autopilot = makeAutopilot({ status: "running", step: "images" });

      renderHook(() => useAutopilotCheckpoint(null, autopilot));

      expect(setItemSpy).not.toHaveBeenCalled();
    });
  });

  describe("storyboardId가 설정된 경우", () => {
    it("localStorage에 유효한 interrupted 체크포인트가 있으면 pendingCheckpoint 설정", () => {
      const ckpt: AutopilotCheckpoint = {
        step: "images",
        timestamp: Date.now(),
        interrupted: true,
      };
      localStorage.setItem("autopilot_ckpt_42", JSON.stringify(ckpt));

      const autopilot = makeAutopilot();
      const { result } = renderHook(() =>
        useAutopilotCheckpoint(42, autopilot)
      );

      expect(result.current.CKPT_KEY).toBe("autopilot_ckpt_42");
      expect(result.current.pendingCheckpoint).toMatchObject({
        step: "images",
        interrupted: true,
      });
    });

    it("interrupted: false인 체크포인트는 pendingCheckpoint를 null로 유지", () => {
      const ckpt: AutopilotCheckpoint = {
        step: "render",
        timestamp: Date.now(),
        interrupted: false,
      };
      localStorage.setItem("autopilot_ckpt_42", JSON.stringify(ckpt));

      const autopilot = makeAutopilot();
      const { result } = renderHook(() =>
        useAutopilotCheckpoint(42, autopilot)
      );

      expect(result.current.pendingCheckpoint).toBeNull();
    });

    it("localStorage에 항목이 없으면 pendingCheckpoint는 null", () => {
      const autopilot = makeAutopilot();
      const { result } = renderHook(() =>
        useAutopilotCheckpoint(42, autopilot)
      );

      expect(result.current.pendingCheckpoint).toBeNull();
    });

    it("localStorage 값이 잘못된 JSON이면 parse 에러를 무시하고 null 유지", () => {
      localStorage.setItem("autopilot_ckpt_42", "invalid-json{{{");

      const autopilot = makeAutopilot();
      const { result } = renderHook(() =>
        useAutopilotCheckpoint(42, autopilot)
      );

      expect(result.current.pendingCheckpoint).toBeNull();
    });
  });

  describe("autoRunState 변경에 따른 localStorage 저장/삭제", () => {
    it("status: running → localStorage에 interrupted: true로 저장", () => {
      const setItemSpy = vi.spyOn(localStorage, "setItem");
      const autopilot = makeAutopilot({ status: "running", step: "images" });

      renderHook(() => useAutopilotCheckpoint(42, autopilot));

      expect(setItemSpy).toHaveBeenCalledWith(
        "autopilot_ckpt_42",
        expect.stringContaining('"interrupted":true')
      );
      expect(setItemSpy).toHaveBeenCalledWith(
        "autopilot_ckpt_42",
        expect.stringContaining('"step":"images"')
      );
    });

    it("status: error → localStorage에 interrupted: true로 저장", () => {
      const setItemSpy = vi.spyOn(localStorage, "setItem");
      const autopilot = makeAutopilot({ status: "error", step: "render" });

      renderHook(() => useAutopilotCheckpoint(42, autopilot));

      expect(setItemSpy).toHaveBeenCalledWith(
        "autopilot_ckpt_42",
        expect.stringContaining('"interrupted":true')
      );
    });

    it("status: done → localStorage에서 삭제", () => {
      const removeItemSpy = vi.spyOn(localStorage, "removeItem");
      // Pre-populate
      localStorage.setItem("autopilot_ckpt_42", JSON.stringify({ step: "render", timestamp: 1, interrupted: true }));

      const autopilot = makeAutopilot({ status: "done", step: "render" });
      renderHook(() => useAutopilotCheckpoint(42, autopilot));

      expect(removeItemSpy).toHaveBeenCalledWith("autopilot_ckpt_42");
    });

    it("status: idle → localStorage에서 삭제", () => {
      const removeItemSpy = vi.spyOn(localStorage, "removeItem");
      localStorage.setItem("autopilot_ckpt_42", JSON.stringify({ step: "images", timestamp: 1, interrupted: true }));

      const autopilot = makeAutopilot({ status: "idle", step: "idle" });
      renderHook(() => useAutopilotCheckpoint(42, autopilot));

      expect(removeItemSpy).toHaveBeenCalledWith("autopilot_ckpt_42");
    });
  });

  describe("setPendingCheckpoint setter", () => {
    it("setPendingCheckpoint(null) 호출 시 pendingCheckpoint 초기화", () => {
      const ckpt: AutopilotCheckpoint = {
        step: "images",
        timestamp: Date.now(),
        interrupted: true,
      };
      localStorage.setItem("autopilot_ckpt_42", JSON.stringify(ckpt));

      const autopilot = makeAutopilot();
      const { result } = renderHook(() =>
        useAutopilotCheckpoint(42, autopilot)
      );

      expect(result.current.pendingCheckpoint).not.toBeNull();

      act(() => {
        result.current.setPendingCheckpoint(null);
      });

      expect(result.current.pendingCheckpoint).toBeNull();
    });
  });

  describe("stale 체크포인트 (24시간 초과)", () => {
    it("타임스탬프가 24시간 이전이어도 interrupted: true면 pendingCheckpoint 설정 (현재 구현 기준)", () => {
      // NOTE: 현재 useAutopilotCheckpoint 구현에는 24시간 staleness 체크가 없음.
      // interrupted: true인 체크포인트는 항상 복원됨.
      const staleTimestamp = Date.now() - 25 * 60 * 60 * 1000; // 25시간 전
      const ckpt: AutopilotCheckpoint = {
        step: "stage",
        timestamp: staleTimestamp,
        interrupted: true,
      };
      localStorage.setItem("autopilot_ckpt_99", JSON.stringify(ckpt));

      const autopilot = makeAutopilot();
      const { result } = renderHook(() =>
        useAutopilotCheckpoint(99, autopilot)
      );

      // 현재 구현은 타임스탬프를 확인하지 않으므로 복원됨
      expect(result.current.pendingCheckpoint).toMatchObject({
        step: "stage",
        interrupted: true,
      });
    });
  });
});
