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
  VoicePreset,
} from "../types";
import axios from "axios";
import {
  API_BASE,
  DEFAULT_OVERLAY_SETTINGS,
  DEFAULT_POST_CARD_SETTINGS,
  DEFAULT_SCENE_TEXT_FONT,
} from "../constants";
import { useContextStore } from "./useContextStore";
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
    default_steps: number | null;
    default_cfg_scale: number | null;
    default_sampler_name: string | null;
    default_clip_skip: number | null;
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
  /** Backend SSOT: loaded from /presets API. Fallback: "qwen" */
  ttsEngine: string;
  voiceDesignPrompt: string;
  voicePresetId: number | null;
  /** Cached voice presets — shared across Studio tabs */
  voicePresets: VoicePreset[];

  bgmMode: "manual" | "auto";
  musicPresetId: number | null;
  bgmPrompt: string;
  bgmMood: string;
  bgmPreviewUrl: string | null;
  /** Director control — selected BGM mood preset (persisted) */
  selectedBgmPreset: string | null;
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
  /** Fetch voice presets from API */
  fetchVoicePresets: () => Promise<void>;
}

const initialState: Omit<RenderStore, "set" | "reset" | "fetchVoicePresets"> = {
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
  voicePresets: [] as VoicePreset[],
  bgmMode: "manual",
  musicPresetId: null,
  bgmPrompt: "",
  bgmMood: "",
  bgmPreviewUrl: null,
  selectedBgmPreset: null,
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

// Migrate: remove old single-key format (replaced by per-storyboard keys :sb_{id} / :new)
if (typeof window !== "undefined" && localStorage.getItem(RENDER_STORE_KEY) !== null) {
  localStorage.removeItem(RENDER_STORE_KEY);
}

/** Returns the active per-storyboard localStorage key for render settings. */
export function getRenderPersistKey(): string {
  const sbId = useContextStore.getState().storyboardId;
  return sbId ? `${RENDER_STORE_KEY}:sb_${sbId}` : `${RENDER_STORE_KEY}:new`;
}

/** Custom storage that scopes render settings to the active storyboard. */
const renderScopedStorage = {
  getItem: (_name: string): string | null => localStorage.getItem(getRenderPersistKey()),
  setItem: (_name: string, value: string): void =>
    localStorage.setItem(getRenderPersistKey(), value),
  removeItem: (_name: string): void => localStorage.removeItem(getRenderPersistKey()),
};

/** Fields excluded from persistence (transient / runtime-derived). */
const TRANSIENT_KEYS: (keyof RenderStore)[] = [
  "isRendering",
  "renderProgress",
  "bgmList",
  "fontList",
  "loadedFonts",
  "overlayAvatarUrl",
  "postAvatarUrl",
  "voicePresets",
];

export const useRenderStore = create<RenderStore>()(
  persist(
    (set) => ({
      ...initialState,
      set: (updates) => set((state) => ({ ...state, ...updates })),
      reset: () => set(initialState),
      fetchVoicePresets: async () => {
        try {
          const res = await axios.get<VoicePreset[]>(`${API_BASE}/voice-presets`);
          set({ voicePresets: res.data });
        } catch {
          console.warn("[RenderStore] Voice presets fetch failed");
        }
      },
    }),
    {
      name: RENDER_STORE_KEY,
      storage: createJSONStorage(() => renderScopedStorage),
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
      version: 1,
      migrate: (persisted, version) => {
        const state = persisted as Record<string, unknown>;
        if (version < 1) {
          const mode = state.bgmMode as string | undefined;
          if (mode === "file" || mode === "ai") {
            state.bgmMode = "manual";
          }
        }
        return state as Partial<RenderStore>;
      },
    }
  )
);
