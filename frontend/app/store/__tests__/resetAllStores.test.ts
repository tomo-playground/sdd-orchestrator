import { describe, it, expect, vi, beforeEach } from "vitest";
import { useContextStore } from "../useContextStore";
import { useStoryboardStore, getStoryboardPersistKey, STORYBOARD_STORE_KEY } from "../useStoryboardStore";
import { useRenderStore, getRenderPersistKey, RENDER_STORE_KEY } from "../useRenderStore";
import { useUIStore } from "../useUIStore";
import { useChatStore } from "../useChatStore";

// Mock groupActions dynamic import
vi.mock("../actions/groupActions", () => ({
  loadGroupDefaults: vi.fn().mockResolvedValue(undefined),
}));

describe("resetAllStores", () => {
  const mockResetContext = vi.fn();
  const mockSetContext = vi.fn();
  const mockSbReset = vi.fn();
  const mockRenderReset = vi.fn();
  const mockResetUI = vi.fn();
  const mockClearMessages = vi.fn();
  const mockRemoveItem = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Provide localStorage mock
    Object.defineProperty(globalThis, "localStorage", {
      value: { removeItem: mockRemoveItem, getItem: () => null, setItem: vi.fn() },
      writable: true,
      configurable: true,
    });

    vi.spyOn(useContextStore, "getState").mockReturnValue({
      projectId: 10,
      groupId: 20,
      storyboardId: 99,
      storyboardTitle: "Old Title",
      resetContext: mockResetContext,
      setContext: mockSetContext,
    } as unknown as ReturnType<typeof useContextStore.getState>);

    vi.spyOn(useStoryboardStore, "getState").mockReturnValue({
      reset: mockSbReset,
    } as unknown as ReturnType<typeof useStoryboardStore.getState>);

    vi.spyOn(useRenderStore, "getState").mockReturnValue({
      reset: mockRenderReset,
    } as unknown as ReturnType<typeof useRenderStore.getState>);

    vi.spyOn(useUIStore, "getState").mockReturnValue({
      resetUI: mockResetUI,
      chatResetToken: 0,
      set: vi.fn(),
    } as unknown as ReturnType<typeof useUIStore.getState>);

    vi.spyOn(useChatStore, "getState").mockReturnValue({
      clearMessages: mockClearMessages,
    } as unknown as ReturnType<typeof useChatStore.getState>);
  });

  it("clears localStorage keys", async () => {
    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    expect(mockRemoveItem).toHaveBeenCalledWith(getStoryboardPersistKey());
    expect(mockRemoveItem).toHaveBeenCalledWith(getRenderPersistKey());
  });

  it("resets all stores including chat temporary key", async () => {
    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    expect(mockResetContext).toHaveBeenCalled();
    expect(mockSbReset).toHaveBeenCalled();
    expect(mockRenderReset).toHaveBeenCalled();
    expect(mockResetUI).toHaveBeenCalled();
    expect(mockClearMessages).toHaveBeenCalledWith(null);
  });

  it("preserves projectId/groupId after reset", async () => {
    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    expect(mockSetContext).toHaveBeenCalledWith({
      projectId: 10,
      groupId: 20,
    });
  });

  it("reloads group defaults by default", async () => {
    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    const { loadGroupDefaults } = await import("../actions/groupActions");
    expect(loadGroupDefaults).toHaveBeenCalledWith(20);
  });

  it("skips group defaults reload when opted out", async () => {
    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores({ reloadGroupDefaults: false });

    const { loadGroupDefaults } = await import("../actions/groupActions");
    expect(loadGroupDefaults).not.toHaveBeenCalled();
  });

  it("bumps chatResetToken after resetUI", async () => {
    const mockSet = vi.fn();
    vi.spyOn(useUIStore, "getState").mockReturnValue({
      resetUI: mockResetUI,
      chatResetToken: 5,
      set: mockSet,
    } as unknown as ReturnType<typeof useUIStore.getState>);

    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    expect(mockSet).toHaveBeenCalledWith({ chatResetToken: 6 });
  });

  it("skips group defaults reload when groupId is null", async () => {
    vi.spyOn(useContextStore, "getState").mockReturnValue({
      projectId: 10,
      groupId: null,
      storyboardId: null,
      storyboardTitle: "",
      resetContext: mockResetContext,
      setContext: mockSetContext,
    } as unknown as ReturnType<typeof useContextStore.getState>);

    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    const { loadGroupDefaults } = await import("../actions/groupActions");
    expect(loadGroupDefaults).not.toHaveBeenCalled();
  });

  it("clears :new localStorage keys in resetAllStores", async () => {
    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    expect(mockRemoveItem).toHaveBeenCalledWith(`${STORYBOARD_STORE_KEY}:new`);
    expect(mockRemoveItem).toHaveBeenCalledWith(`${RENDER_STORE_KEY}:new`);
  });

  it("clears :new localStorage keys in resetTransientStores", async () => {
    const { resetTransientStores } = await import("../resetAllStores");
    resetTransientStores();

    expect(mockRemoveItem).toHaveBeenCalledWith(`${STORYBOARD_STORE_KEY}:new`);
    expect(mockRemoveItem).toHaveBeenCalledWith(`${RENDER_STORE_KEY}:new`);
  });
});
