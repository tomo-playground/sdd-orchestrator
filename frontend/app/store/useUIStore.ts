import { create } from "zustand";
import type { ToastItem, AutopilotCheckpoint } from "../types";
import { useContextStore } from "./useContextStore";
import { ALL_GROUPS_ID } from "../constants";

export type StudioTab = "script" | "stage" | "direct" | "publish";

/** 스토리보드가 없거나 초기 진입 시 보여줄 기본 탭 */
export const DEFAULT_STUDIO_TAB: StudioTab = "script";

const MAX_TOASTS = 3;

// Module-scope timer map (not in Zustand state — avoids serialization issues)
// SSR-safe: Map works in Node.js, but guard prevents timer leaks during SSR
const _timerIds =
  typeof window !== "undefined" ? new Map<string, ReturnType<typeof setTimeout>>() : null;

// Stable empty Map for SSR — avoids creating a new instance on every call
const _ssrFallback = new Map<string, ReturnType<typeof setTimeout>>();

/** Safe accessor — returns stable no-op Map during SSR */
function timerMap() {
  return _timerIds ?? _ssrFallback;
}

export interface UIState {
  // Toast queue
  toasts: ToastItem[];

  // Navigation
  activeTab: StudioTab;

  // Modals / Previews
  imagePreviewSrc: string | null;
  imagePreviewCandidates: string[] | null;
  videoPreviewSrc: string | null;
  showResumeModal: boolean;
  resumableCheckpoint: AutopilotCheckpoint | null;
  showPreflightModal: boolean;

  // Setup wizard
  showSetupWizard: boolean;
  setupWizardInitialStep: 1 | 2;

  // New storyboard mode (URL-independent flag for ?new=true)
  isNewStoryboardMode: boolean;

  // Group config modal (SSOT UI)
  configGroupId: number | null;
  openGroupConfig: () => void;

  // Autopilot lock
  isAutoRunning: boolean;

  // Auto-save failure indicator
  autoSaveFailed: boolean;

  // Script → AutoRun chain signal
  pendingAutoRun: boolean;
  setPendingAutoRun: (v: boolean) => void;

  // Store-reset detection (bumped by resetAllStores — lets hooks detect null→null resets)
  chatResetToken: number;

  // Preferences
  showAdvancedSettings: boolean;
  toggleAdvancedSettings: () => void;

  // 3-panel layout feature flag (Direct tab)
  use3PanelLayout: boolean;
  toggle3PanelLayout: () => void;

  set: (updates: Partial<UIState>) => void;
  setActiveTab: (tab: StudioTab) => void;
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  dismissToast: (id: string) => void;
  resetUI: () => void;
}

const initialState: Omit<
  UIState,
  | "set"
  | "setActiveTab"
  | "showToast"
  | "dismissToast"
  | "resetUI"
  | "toggleAdvancedSettings"
  | "toggle3PanelLayout"
  | "setPendingAutoRun"
  | "openGroupConfig"
> = {
  toasts: [],
  activeTab: DEFAULT_STUDIO_TAB,
  showAdvancedSettings: false, // Default closed
  imagePreviewSrc: null,
  imagePreviewCandidates: null,
  videoPreviewSrc: null,
  showResumeModal: false,
  resumableCheckpoint: null,
  showPreflightModal: false,
  showSetupWizard: false,
  setupWizardInitialStep: 1 as 1 | 2,
  configGroupId: null,
  isNewStoryboardMode: false,
  use3PanelLayout: false,
  isAutoRunning: false,
  autoSaveFailed: false,
  pendingAutoRun: false,
  chatResetToken: 0,
};

export const useUIStore = create<UIState>((set) => ({
  ...initialState,
  set: (updates) => set((state) => ({ ...state, ...updates })),
  toggleAdvancedSettings: () =>
    set((state) => ({ showAdvancedSettings: !state.showAdvancedSettings })),
  toggle3PanelLayout: () => set((state) => ({ use3PanelLayout: !state.use3PanelLayout })),
  setPendingAutoRun: (v) => set({ pendingAutoRun: v }),
  setActiveTab: (tab) => {
    set({ activeTab: tab });
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (url.searchParams.get("tab") !== tab) {
        url.searchParams.set("tab", tab);
        window.history.replaceState({}, "", url.toString());
      }
    }
  },
  openGroupConfig: () => {
    const gid = useContextStore.getState().groupId;
    if (gid === null || gid === ALL_GROUPS_ID) {
      set((s) => {
        const id = Date.now().toString(36) + Math.random().toString(36).slice(2);
        return {
          toasts: [
            ...s.toasts,
            { id, message: "시리즈를 먼저 선택하세요", type: "error" as const },
          ],
        };
      });
      return;
    }
    set({ configGroupId: gid });
  },

  showToast: (message, type) => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2);
    const item: ToastItem = { id, message, type };

    set((state) => {
      let next = [...state.toasts];

      // Evict oldest if at capacity
      if (next.length >= MAX_TOASTS) {
        const oldest = next[0];
        const oldTimer = timerMap().get(oldest.id);
        if (oldTimer) clearTimeout(oldTimer);
        timerMap().delete(oldest.id);
        next = next.slice(1);
      }

      return { toasts: [...next, item] };
    });

    // Auto-dismiss after 3s
    const timer = setTimeout(() => {
      timerMap().delete(id);
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
    }, 3000);
    timerMap().set(id, timer);
  },

  dismissToast: (id) => {
    const timer = timerMap().get(id);
    if (timer) clearTimeout(timer);
    timerMap().delete(id);
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },

  resetUI: () => {
    // Clear all pending timers
    const timers = timerMap();
    for (const timer of timers.values()) clearTimeout(timer);
    timers.clear();
    set(initialState);
  },
}));
