import type { StateCreator } from "zustand";
import type { Toast, AutopilotCheckpoint } from "../../types";

export type StudioTab = "plan" | "scenes" | "render" | "output";

export interface MetaSlice {
  // Storyboard identity
  projectId: number | null;
  groupId: number | null;
  storyboardId: number | null;
  storyboardTitle: string;

  // UI
  activeTab: StudioTab;
  toast: Toast;

  // Modals
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

  // Setters
  setMeta: (updates: Partial<MetaSlice>) => void;
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  setActiveTab: (tab: StudioTab) => void;
  resetMeta: () => void;
}

const initialMetaState = {
  projectId: null as number | null,
  groupId: null as number | null,
  storyboardId: null as number | null,
  storyboardTitle: "",
  activeTab: "plan" as StudioTab,
  toast: null as Toast,
  imagePreviewSrc: null as string | null,
  imagePreviewCandidates: null as string[] | null,
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
  isAutoRunning: false,
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
