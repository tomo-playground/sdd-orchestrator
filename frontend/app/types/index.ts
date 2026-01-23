export type Scene = {
  id: number;
  script: string;
  speaker: "Narrator" | "A";
  duration: number;
  image_prompt: string;
  image_prompt_ko: string;
  image_url: string | null;
  candidates?: Array<{ image_url: string; match_rate?: number }>;
  negative_prompt: string;
  steps: number;
  cfg_scale: number;
  sampler_name: string;
  seed: number;
  clip_skip: number;
  isGenerating: boolean;
  debug_payload: string;
  debug_prompt?: string;
};

export type AudioItem = { name: string; url: string };
export type FontItem = { name: string };

export type OverlaySettings = {
  channel_name: string;
  avatar_key: string;
  likes_count: string;
  caption: string;
  frame_style: string;
};

export type PostCardSettings = {
  channel_name: string;
  avatar_key: string;
  caption: string;
};

export type SdModel = { title: string; model_name: string };
export type ActorGender = "male" | "female";

export type AutoRunStepId = "storyboard" | "fix" | "images" | "validate" | "render";

export type ValidationIssue = { level: "warn" | "error"; message: string };

export type SceneValidation = {
  status: "ok" | "warn" | "error";
  issues: ValidationIssue[];
};

export type FixSuggestion = {
  id: string;
  message: string;
  action?: {
    type:
      | "add_positive"
      | "remove_negative_scene"
      | "set_speaker_a"
      | "fill_script"
      | "trim_script";
    tokens?: string[];
    value?: string;
  };
};

export type ImageValidation = {
  match_rate: number;
  matched: string[];
  missing: string[];
  extra: string[];
};

export type AutoRunState = {
  status: "idle" | "running" | "error" | "done";
  step: AutoRunStepId | "idle";
  message: string;
  error?: string;
};

export type RecentVideo = {
  url: string;
  label: "full" | "post" | "single";
  createdAt: number;
};

export type Toast = {
  message: string;
  type: "success" | "error";
} | null;

export type DraftScene = {
  id: number;
  script: string;
  speaker: Scene["speaker"];
  duration: number;
  image_prompt: string;
  image_prompt_ko: string;
  image_url: string | null;
  candidates?: Array<{ image_url: string; match_rate?: number }>;
  negative_prompt: string;
  steps: number;
  cfg_scale: number;
  sampler_name: string;
  seed: number;
  clip_skip: number;
};

export type DraftData = {
  topic?: string;
  duration?: number;
  style?: string;
  language?: string;
  structure?: string;
  actorAGender?: ActorGender;
  basePromptA?: string;
  baseNegativePromptA?: string;
  baseStepsA?: number;
  baseCfgScaleA?: number;
  baseSamplerA?: string;
  baseSeedA?: number;
  baseClipSkipA?: number;
  includeSubtitles?: boolean;
  narratorVoice?: string;
  bgmFile?: string | null;
  subtitleFont?: string;
  speedMultiplier?: number;
  overlaySettings?: OverlaySettings;
  postCardSettings?: PostCardSettings;
  layoutStyle?: "full" | "post";
  motionStyle?: "none" | "slow_zoom";
  hiResEnabled?: boolean;
  veoEnabled?: boolean;
  videoUrl?: string | null;
  videoUrlFull?: string | null;
  videoUrlPost?: string | null;
  recentVideos?: RecentVideo[];
  scenes?: DraftScene[];
};
