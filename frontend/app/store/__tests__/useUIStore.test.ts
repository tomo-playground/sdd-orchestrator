import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useUIStore, DEFAULT_STUDIO_TAB } from "../useUIStore";
import { useContextStore } from "../useContextStore";
import { ALL_GROUPS_ID } from "../../constants";

describe("useUIStore", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useUIStore.getState().resetUI();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("setActiveTab", () => {
    it("changes the active tab", () => {
      useUIStore.getState().setActiveTab(DEFAULT_STUDIO_TAB);
      expect(useUIStore.getState().activeTab).toBe(DEFAULT_STUDIO_TAB);
    });

    it("changes to publish tab", () => {
      useUIStore.getState().setActiveTab("publish");
      expect(useUIStore.getState().activeTab).toBe("publish");
    });

    it("calls history.replaceState with ?tab= when tab changes", () => {
      const spy = vi.spyOn(window.history, "replaceState");
      useUIStore.getState().setActiveTab("stage");
      expect(spy).toHaveBeenCalledOnce();
      const calledUrl = spy.mock.calls[0][2] as string;
      expect(calledUrl).toContain("tab=stage");
      spy.mockRestore();
    });

    it("does not call history.replaceState when tab is already current in URL", () => {
      // Seed URL so ?tab=direct is already present
      window.history.replaceState({}, "", "/?tab=direct");
      const spy = vi.spyOn(window.history, "replaceState");
      useUIStore.getState().setActiveTab("direct");
      expect(spy).not.toHaveBeenCalled();
      spy.mockRestore();
    });
  });

  describe("showToast", () => {
    it("adds a toast to the queue", () => {
      useUIStore.getState().showToast("Test message", "success");
      const toasts = useUIStore.getState().toasts;
      expect(toasts).toHaveLength(1);
      expect(toasts[0].message).toBe("Test message");
      expect(toasts[0].type).toBe("success");
    });

    it("auto-dismisses after 3 seconds", () => {
      useUIStore.getState().showToast("Auto dismiss", "success");
      expect(useUIStore.getState().toasts).toHaveLength(1);

      vi.advanceTimersByTime(3000);
      expect(useUIStore.getState().toasts).toHaveLength(0);
    });

    it("evicts oldest when at max capacity", () => {
      useUIStore.getState().showToast("First", "success");
      useUIStore.getState().showToast("Second", "success");
      useUIStore.getState().showToast("Third", "success");
      expect(useUIStore.getState().toasts).toHaveLength(3);

      useUIStore.getState().showToast("Fourth", "success");
      const toasts = useUIStore.getState().toasts;
      expect(toasts).toHaveLength(3);
      expect(toasts[0].message).toBe("Second");
      expect(toasts[2].message).toBe("Fourth");
    });
  });

  describe("dismissToast", () => {
    it("removes a specific toast by id", () => {
      useUIStore.getState().showToast("To dismiss", "error");
      const id = useUIStore.getState().toasts[0].id;

      useUIStore.getState().dismissToast(id);
      expect(useUIStore.getState().toasts).toHaveLength(0);
    });

    it("does nothing for non-existent id", () => {
      useUIStore.getState().showToast("Keep me", "success");
      useUIStore.getState().dismissToast("nonexistent");
      expect(useUIStore.getState().toasts).toHaveLength(1);
    });
  });

  describe("toggleAdvancedSettings", () => {
    it("toggles showAdvancedSettings", () => {
      expect(useUIStore.getState().showAdvancedSettings).toBe(false);
      useUIStore.getState().toggleAdvancedSettings();
      expect(useUIStore.getState().showAdvancedSettings).toBe(true);
      useUIStore.getState().toggleAdvancedSettings();
      expect(useUIStore.getState().showAdvancedSettings).toBe(false);
    });
  });

  describe("toggle3PanelLayout", () => {
    it("defaults to false", () => {
      expect(useUIStore.getState().use3PanelLayout).toBe(false);
    });

    it("toggles use3PanelLayout", () => {
      useUIStore.getState().toggle3PanelLayout();
      expect(useUIStore.getState().use3PanelLayout).toBe(true);
      useUIStore.getState().toggle3PanelLayout();
      expect(useUIStore.getState().use3PanelLayout).toBe(false);
    });

    it("resets to false on resetUI()", () => {
      useUIStore.getState().toggle3PanelLayout();
      expect(useUIStore.getState().use3PanelLayout).toBe(true);
      useUIStore.getState().resetUI();
      expect(useUIStore.getState().use3PanelLayout).toBe(false);
    });
  });

  describe("setPendingAutoRun", () => {
    it("sets pendingAutoRun value", () => {
      useUIStore.getState().setPendingAutoRun(true);
      expect(useUIStore.getState().pendingAutoRun).toBe(true);
      useUIStore.getState().setPendingAutoRun(false);
      expect(useUIStore.getState().pendingAutoRun).toBe(false);
    });
  });

  describe("openGroupConfig", () => {
    it("shows error toast when groupId is null", () => {
      vi.spyOn(useContextStore, "getState").mockReturnValue({ groupId: null } as never);
      useUIStore.getState().openGroupConfig();
      const toasts = useUIStore.getState().toasts;
      expect(toasts).toHaveLength(1);
      expect(toasts[0].type).toBe("error");
    });

    it("shows error toast when groupId is ALL_GROUPS_ID", () => {
      vi.spyOn(useContextStore, "getState").mockReturnValue({
        groupId: ALL_GROUPS_ID,
      } as never);
      useUIStore.getState().openGroupConfig();
      const toasts = useUIStore.getState().toasts;
      expect(toasts).toHaveLength(1);
      expect(toasts[0].type).toBe("error");
    });

    it("sets configGroupId when groupId is valid", () => {
      vi.spyOn(useContextStore, "getState").mockReturnValue({ groupId: 5 } as never);
      useUIStore.getState().openGroupConfig();
      expect(useUIStore.getState().configGroupId).toBe(5);
    });
  });

  describe("resetUI", () => {
    it("resets all state to initial values", () => {
      useUIStore.getState().showToast("msg", "success");
      useUIStore.getState().setActiveTab(DEFAULT_STUDIO_TAB);
      useUIStore.getState().set({ isAutoRunning: true });

      useUIStore.getState().resetUI();

      const state = useUIStore.getState();
      expect(state.toasts).toEqual([]);
      expect(state.activeTab).toBe(DEFAULT_STUDIO_TAB);
      expect(state.isAutoRunning).toBe(false);
    });
  });

  describe("set", () => {
    it("merges partial updates", () => {
      useUIStore.getState().set({ imagePreviewSrc: "test.png", showResumeModal: true });
      expect(useUIStore.getState().imagePreviewSrc).toBe("test.png");
      expect(useUIStore.getState().showResumeModal).toBe(true);
    });
  });
});
