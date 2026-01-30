import type { StateCreator } from "zustand";
import type { Toast, AutopilotCheckpoint } from "../../types";

export type StudioTab = "plan" | "scenes" | "output" | "insights";

export interface MetaSlice {
  // Storyboard identity
  storyboardId: number | null;
  storyboardTitle: string;

  // UI
  activeTab: StudioTab;
  toast: Toast;

  // Modals
  imagePreviewSrc: string | null;
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

  // Setters
  setMeta: (updates: Partial<MetaSlice>) => void;
  showToast: (message: string, type: "success" | "error") => void;
  setActiveTab: (tab: StudioTab) => void;
  resetMeta: () => void;
}

const initialMetaState = {
  storyboardId: null as number | null,
  storyboardTitle: "",
  activeTab: "plan" as StudioTab,
  toast: null as Toast,
  imagePreviewSrc: null as string | null,
  videoPreviewSrc: null as string | null,
  showResumeModal: false,
  resumableCheckpoint: null as AutopilotCheckpoint | null,
  showPreflightModal: false,
  isHelperOpen: false,
  examplePrompt: "",
  suggestedBase: "",
  suggestedScene: "",
  isSuggesting: false,
  copyStatus: "",
};

export const createMetaSlice: StateCreator<MetaSlice, [], [], MetaSlice> = (set) => ({
  ...initialMetaState,
  setMeta: (updates) => set((state) => ({ ...state, ...updates })),
  showToast: (message, type) => {
    set({ toast: { message, type } });
    setTimeout(() => set({ toast: null }), 3000);
  },
  setActiveTab: (tab) => set({ activeTab: tab }),
  resetMeta: () => set(initialMetaState),
});
