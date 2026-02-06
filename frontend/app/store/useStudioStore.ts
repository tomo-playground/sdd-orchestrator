import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { createPlanSlice, type PlanSlice } from "./slices/planSlice";
import { createScenesSlice, type ScenesSlice } from "./slices/scenesSlice";
import { createOutputSlice, type OutputSlice } from "./slices/outputSlice";
import { createMetaSlice, type MetaSlice } from "./slices/metaSlice";
import { createContextSlice, type ContextSlice } from "./slices/contextSlice";
import { migrateDraft } from "./migrations/draftMigration";

export type StudioState = PlanSlice & ScenesSlice & OutputSlice & MetaSlice & ContextSlice;

const STORE_KEY = "shorts-producer:studio:v1";

/** Fields excluded from persistence (transient UI state). */
const TRANSIENT_KEYS: (keyof StudioState)[] = [
  // ScenesSlice transient
  "isGenerating",
  "validatingSceneId",
  "markingStatusSceneId",
  "sceneTab",
  "sceneMenuOpen",
  "advancedExpanded",
  "suggestionExpanded",
  "validationExpanded",
  "validationResults",
  "validationSummary",
  "imageValidationResults",
  // OutputSlice transient
  "isRendering",
  "bgmList",
  "fontList",
  "loadedFonts",
  "sceneTextFont", // Render preset controls this; don't persist
  "overlayAvatarUrl",
  "postAvatarUrl",
  // MetaSlice transient
  "toast",
  "imagePreviewSrc",
  "videoPreviewSrc",
  "showResumeModal",
  "resumableCheckpoint",
  "showPreflightModal",
  "isHelperOpen",
  "isSuggesting",
  "copyStatus",
  "suggestedBase",
  "suggestedScene",
  "isAutoRunning",
  // PlanSlice transient (runtime-derived)
  "loraTriggerWords",
  "characterLoras",
  "characterPromptMode",
  // ContextSlice transient
  "projects",
  "groups",
  "isLoadingProjects",
  "isLoadingGroups",
  "effectiveStyleProfileId",
  "effectiveCharacterId",
  "effectiveConfigLoaded",
];

// Pre-hydration cleanup: clear localStorage before Zustand hydrates old data
if (typeof window !== "undefined") {
  const params = new URLSearchParams(window.location.search);
  if (params.get("new") === "true") {
    localStorage.removeItem(STORE_KEY);
  }
}

export const useStudioStore = create<StudioState>()(
  persist(
    (...a) => ({
      ...createPlanSlice(...a),
      ...createScenesSlice(...a),
      ...createOutputSlice(...a),
      ...createMetaSlice(...a),
      ...createContextSlice(...a),
    }),
    {
      name: STORE_KEY,
      storage: createJSONStorage(() => {
        // Run migration on first access
        if (typeof window !== "undefined") {
          migrateDraft();
        }
        return localStorage;
      }),
      merge: (persisted, current) => {
        const merged = { ...current, ...(persisted as object) };
        // Force ttsEngine to "qwen" (Edge-TTS removed in Phase 6-8.2)
        if ((merged as Record<string, unknown>).ttsEngine === "edge") {
          (merged as Record<string, unknown>).ttsEngine = "qwen";
        }
        return merged as typeof current;
      },
      partialize: (state) => {
        const persisted: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(state)) {
          if (typeof value === "function") continue;
          if (TRANSIENT_KEYS.includes(key as keyof StudioState)) continue;
          // Skip Set objects (not JSON-serializable)
          if (value instanceof Set) continue;
          persisted[key] = value;
        }
        return persisted as Partial<StudioState>;
      },
    }
  )
);

/**
 * Reset all store slices to initial state.
 * Call this when creating a new storyboard to clear previous data.
 * Channel info is now derived from the selected Project (no profileSlice).
 */
export const resetStudioStore = () => {
  const state = useStudioStore.getState();

  // Preserve context data before reset
  const preserved = {
    projectId: state.projectId,
    groupId: state.groupId,
  };

  // Clear localStorage to prevent rehydration of old data
  if (typeof window !== "undefined") {
    localStorage.removeItem(STORE_KEY);
  }

  // Reset all slices
  state.resetMeta();
  state.resetPlan();
  state.resetScenes();
  state.resetOutput();

  // Restore preserved data (intentionally persists across storyboards)
  state.setMeta({
    projectId: preserved.projectId,
    groupId: preserved.groupId,
  });
};
