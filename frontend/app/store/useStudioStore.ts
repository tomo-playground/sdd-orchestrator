import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { createPlanSlice, type PlanSlice } from "./slices/planSlice";
import { createScenesSlice, type ScenesSlice } from "./slices/scenesSlice";
import { createOutputSlice, type OutputSlice } from "./slices/outputSlice";
import { createMetaSlice, type MetaSlice } from "./slices/metaSlice";
import { migrateDraft } from "./migrations/draftMigration";

export type StudioState = PlanSlice & ScenesSlice & OutputSlice & MetaSlice;

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
  "isModelUpdating",
  "isRegeneratingAvatar",
  "sdModels",
  "currentModel",
  "selectedModel",
  "bgmList",
  "fontList",
  "loadedFonts",
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
  // PlanSlice transient (runtime-derived)
  "loraTriggerWords",
  "characterLoras",
  "characterPromptMode",
];

export const useStudioStore = create<StudioState>()(
  persist(
    (...a) => ({
      ...createPlanSlice(...a),
      ...createScenesSlice(...a),
      ...createOutputSlice(...a),
      ...createMetaSlice(...a),
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
