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
export interface RenderStore {
  // Style Profile
  currentStyleProfile: {
    id: number;
    name: string;
    display_name: string | null;
    sd_model_name: string | null;
    loras: { name: string; trigger_words: string[]; weight: number }[];
    negative_embeddings: { name: string; trigger_word: string }[];
    positive_embeddings: { name: string; trigger_word: string }[];
    default_positive: string | null;
    default_negative: string | null;
  } | null;
  layoutStyle: "full" | "post";
  frameStyle: string;
  kenBurnsPreset: KenBurnsPreset;
  kenBurnsIntensity: number;
  transitionType: string;
  isRendering: boolean;
  includeSceneText: boolean;
  bgmList: AudioItem[];
  bgmFile: string | null;
  audioDucking: boolean;
  bgmVolume: number;
  speedMultiplier: number;
  fontList: FontItem[];
  sceneTextFont: string;
  loadedFonts: Set<string>;
  ttsEngine: "qwen";
  voiceDesignPrompt: string;
  voicePresetId: number | null;
  bgmMode: "file" | "ai";
  musicPresetId: number | null;
  videoCaption: string;
  videoLikesCount: string;
  overlaySettings: OverlaySettings;
  postCardSettings: PostCardSettings;
  overlayAvatarUrl: string | null;
  postAvatarUrl: string | null;
  videoUrl: string | null;
  videoUrlFull: string | null;
  videoUrlPost: string | null;
  recentVideos: RecentVideo[];
  renderProgress: RenderProgress | null;
  set: (updates: Partial<RenderStore>) => void;
  reset: () => void;
}

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

export const RENDER_STORE_KEY = "shorts-producer:render:v1";

// Pre-hydration cleanup: clear localStorage before Zustand hydrates old data
if (typeof window !== "undefined") {
  const params = new URLSearchParams(window.location.search);
  if (params.get("new") === "true") {
    localStorage.removeItem(RENDER_STORE_KEY);
  }
}

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
      name: RENDER_STORE_KEY,
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
    }
  )
);
