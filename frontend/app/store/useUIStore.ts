import { create } from "zustand";
import type { Toast, AutopilotCheckpoint } from "../types";

export type StudioTab = "scenes" | "render" | "output";

export interface UIState {
  // Toast
  toast: Toast;

  // Navigation
  activeTab: StudioTab;

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

  // Autopilot lock
  isAutoRunning: boolean;

  // Actions
  set: (updates: Partial<UIState>) => void;
  setActiveTab: (tab: StudioTab) => void;
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  resetUI: () => void;
}

const initialState: Omit<UIState, "set" | "setActiveTab" | "showToast" | "resetUI"> = {
  toast: null,
  activeTab: "scenes",
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
  isAutoRunning: false,
};

export const useUIStore = create<UIState>((set) => ({
  ...initialState,
  set: (updates) => set((state) => ({ ...state, ...updates })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  showToast: (message, type) => {
    set({ toast: { message, type } });
    setTimeout(() => set({ toast: null }), 3000);
  },
  resetUI: () => set(initialState),
}));
