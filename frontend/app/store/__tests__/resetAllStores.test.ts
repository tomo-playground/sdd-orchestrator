import { describe, it, expect, vi, beforeEach } from "vitest";
import { useContextStore } from "../useContextStore";
import { useStoryboardStore } from "../useStoryboardStore";
import { useRenderStore } from "../useRenderStore";
import { useUIStore } from "../useUIStore";

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
  const mockRemoveItem = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Provide localStorage mock
    Object.defineProperty(globalThis, "localStorage", {
      value: { removeItem: mockRemoveItem },
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
    } as unknown as ReturnType<typeof useUIStore.getState>);
  });

  it("clears localStorage keys", async () => {
    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    expect(mockRemoveItem).toHaveBeenCalledWith("shorts-producer:storyboard:v1");
    expect(mockRemoveItem).toHaveBeenCalledWith("shorts-producer:render:v1");
  });

  it("resets all 4 stores", async () => {
    const { resetAllStores } = await import("../resetAllStores");
    await resetAllStores();

    expect(mockResetContext).toHaveBeenCalled();
    expect(mockSbReset).toHaveBeenCalled();
    expect(mockRenderReset).toHaveBeenCalled();
    expect(mockResetUI).toHaveBeenCalled();
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
});
