import type { StateCreator } from "zustand";
import type {
  AudioItem,
  FontItem,
  KenBurnsPreset,
  OverlaySettings,
  PostCardSettings,
  RecentVideo,
} from "../../types";
import {
  DEFAULT_OVERLAY_SETTINGS,
  DEFAULT_POST_CARD_SETTINGS,
} from "../../constants";

export interface OutputSlice {
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

  // Render settings
  layoutStyle: "full" | "post";
  frameStyle: string;
  kenBurnsPreset: KenBurnsPreset;
  kenBurnsIntensity: number;
  transitionType: string;
  isRendering: boolean;

  // Audio
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
  voiceRefAudioUrl: string;
  voicePresetId: number | null;

  // Video metadata
  videoCaption: string;
  videoLikesCount: string;

  // Overlay
  overlaySettings: OverlaySettings;
  postCardSettings: PostCardSettings;
  overlayAvatarUrl: string | null;
  postAvatarUrl: string | null;

  // Video results
  videoUrl: string | null;
  videoUrlFull: string | null;
  videoUrlPost: string | null;
  recentVideos: RecentVideo[];

  // Setters
  setOutput: (updates: Partial<OutputSlice>) => void;
  resetOutput: () => void;
}

const initialOutputState = {
  currentStyleProfile: null as {
    id: number;
    name: string;
    display_name: string | null;
    sd_model_name: string | null;
    loras: { name: string; trigger_words: string[]; weight: number }[];
    negative_embeddings: { name: string; trigger_word: string }[];
    positive_embeddings: { name: string; trigger_word: string }[];
    default_positive: string | null;
    default_negative: string | null;
  } | null,
  layoutStyle: "post" as const,
  frameStyle: "",
  kenBurnsPreset: "random" as KenBurnsPreset,
  kenBurnsIntensity: 1.0,
  transitionType: "random",
  isRendering: false,
  includeSceneText: true,
  bgmList: [] as AudioItem[],
  bgmFile: null as string | null,
  audioDucking: true,
  bgmVolume: 0.25,
  speedMultiplier: 1.0,
  fontList: [] as FontItem[],
  sceneTextFont: "",
  loadedFonts: new Set<string>(),
  ttsEngine: "qwen" as const,
  voiceDesignPrompt: "",
  voiceRefAudioUrl: "",
  voicePresetId: null as number | null,
  videoCaption: "",
  videoLikesCount: "",
  overlaySettings: DEFAULT_OVERLAY_SETTINGS,
  postCardSettings: DEFAULT_POST_CARD_SETTINGS,
  overlayAvatarUrl: null as string | null,
  postAvatarUrl: null as string | null,
  videoUrl: null as string | null,
  videoUrlFull: null as string | null,
  videoUrlPost: null as string | null,
  recentVideos: [] as RecentVideo[],
};

export const createOutputSlice: StateCreator<OutputSlice, [], [], OutputSlice> = (set) => ({
  ...initialOutputState,
  setOutput: (updates) => set((state) => ({ ...state, ...updates })),
  resetOutput: () => set(initialOutputState),
});
