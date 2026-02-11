import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type {
  AudioItem,
  FontItem,
  KenBurnsPreset,
  OverlaySettings,
  PostCardSettings,
  RecentVideo,
  RenderProgress,
} from "../types";
import {
  DEFAULT_OVERLAY_SETTINGS,
  DEFAULT_POST_CARD_SETTINGS,
  DEFAULT_SCENE_TEXT_FONT,
} from "../constants";
import type { OutputSlice } from "./slices/outputSlice";

/** Render store = OutputSlice data fields + simplified setters. */
export type RenderStore = Omit<OutputSlice, "setOutput" | "resetOutput"> & {
  set: (updates: Partial<RenderStore>) => void;
  reset: () => void;
};

const initialState: Omit<RenderStore, "set" | "reset"> = {
  currentStyleProfile: null,
  layoutStyle: "post",
  frameStyle: "",
  kenBurnsPreset: "random" as KenBurnsPreset,
  kenBurnsIntensity: 1.0,
  transitionType: "random",
  isRendering: false,
  includeSceneText: true,
  bgmList: [] as AudioItem[],
  bgmFile: null,
  audioDucking: true,
  bgmVolume: 0.25,
  speedMultiplier: 1.0,
  fontList: [] as FontItem[],
  sceneTextFont: DEFAULT_SCENE_TEXT_FONT,
  loadedFonts: new Set<string>(),
  ttsEngine: "qwen",
  voiceDesignPrompt: "",
  voicePresetId: null,
  bgmMode: "file",
  musicPresetId: null,
  videoCaption: "",
  videoLikesCount: "",
  overlaySettings: DEFAULT_OVERLAY_SETTINGS,
  postCardSettings: DEFAULT_POST_CARD_SETTINGS,
  overlayAvatarUrl: null,
  postAvatarUrl: null,
  videoUrl: null,
  videoUrlFull: null,
  videoUrlPost: null,
  recentVideos: [] as RecentVideo[],
  renderProgress: null as RenderProgress | null,
};

const STORE_KEY = "shorts-producer:render:v1";

/** Fields excluded from persistence (transient / runtime-derived). */
const TRANSIENT_KEYS: (keyof RenderStore)[] = [
  "isRendering",
  "renderProgress",
  "bgmList",
  "fontList",
  "loadedFonts",
  "sceneTextFont",
  "overlayAvatarUrl",
  "postAvatarUrl",
];

export const useRenderStore = create<RenderStore>()(
  persist(
    (set) => ({
      ...initialState,
      set: (updates) => set((state) => ({ ...state, ...updates })),
      reset: () => set(initialState),
    }),
    {
      name: STORE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => {
        const persisted: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(state)) {
          if (typeof value === "function") continue;
          if (TRANSIENT_KEYS.includes(key as keyof RenderStore)) continue;
          if (value instanceof Set) continue;
          persisted[key] = value;
        }
        return persisted as Partial<RenderStore>;
      },
    },
  ),
);
