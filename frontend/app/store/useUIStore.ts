import { create } from "zustand";
import type { ToastItem, AutopilotCheckpoint } from "../types";

export type StudioTab = "script" | "edit" | "publish";
export type RightPanelTab = "image" | "tools" | "insight";

const MAX_TOASTS = 3;

// Module-scope timer map (not in Zustand state — avoids serialization issues)
// SSR-safe: Map works in Node.js, but guard prevents timer leaks during SSR
const _timerIds =
  typeof window !== "undefined" ? new Map<string, ReturnType<typeof setTimeout>>() : null;

/** Safe accessor — returns no-op stubs during SSR */
function timerMap() {
  return _timerIds ?? new Map<string, ReturnType<typeof setTimeout>>();
}

export interface UIState {
  // Toast queue
  toasts: ToastItem[];

  // Navigation
  activeTab: StudioTab;
  rightPanelTab: RightPanelTab;

  // Modals / Previews
  imagePreviewSrc: string | null;
  imagePreviewCandidates: string[] | null;
  videoPreviewSrc: string | null;
  showResumeModal: boolean;
  resumableCheckpoint: AutopilotCheckpoint | null;
  showPreflightModal: boolean;
  isHelperOpen: boolean;

  // Prompt helper
  examplePrompt: string;
  suggestedBase: string;
  suggestedScene: string;
  isSuggesting: boolean;
  copyStatus: string;

  // Setup wizard
  showSetupWizard: boolean;
  setupWizardInitialStep: 1 | 2;

  // New storyboard mode (URL-independent flag for ?new=true)
  isNewStoryboardMode: boolean;

  // Autopilot lock
  isAutoRunning: boolean;

  // Script → AutoRun chain signal
  pendingAutoRun: boolean;
  setPendingAutoRun: (v: boolean) => void;

  // Preferences
  showAdvancedSettings: boolean;
  toggleAdvancedSettings: () => void;
  showLabMenu: boolean;
  toggleLabMenu: () => void;

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
  | "resetUI"
  | "toggleAdvancedSettings"
  | "toggleLabMenu"
  | "setPendingAutoRun"
> = {
  toasts: [],
  activeTab: "edit",
  rightPanelTab: "tools" as RightPanelTab,
  showAdvancedSettings: false, // Default closed
  showLabMenu: false,
  imagePreviewSrc: null,
  imagePreviewCandidates: null,
  videoPreviewSrc: null,
  showResumeModal: false,
  resumableCheckpoint: null,
  showPreflightModal: false,
  isHelperOpen: false,
  examplePrompt: "",
  suggestedBase: "",
  suggestedScene: "",
  isSuggesting: false,
  copyStatus: "",
  showSetupWizard: false,
  setupWizardInitialStep: 1 as 1 | 2,
  isNewStoryboardMode: false,
  isAutoRunning: false,
  pendingAutoRun: false,
};

export const useUIStore = create<UIState>((set) => ({
  ...initialState,
  set: (updates) => set((state) => ({ ...state, ...updates })),
  toggleAdvancedSettings: () =>
    set((state) => ({ showAdvancedSettings: !state.showAdvancedSettings })),
  toggleLabMenu: () => set((state) => ({ showLabMenu: !state.showLabMenu })),
  setPendingAutoRun: (v) => set({ pendingAutoRun: v }),
  setActiveTab: (tab) => set({ activeTab: tab }),

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
