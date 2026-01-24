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

export type AutopilotCheckpoint = {
  step: AutoRunStepId;
  timestamp: number;
  interrupted: boolean;
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

// ============================================================
// Phase 6: Character & Prompt System Types
// ============================================================

export type Tag = {
  id: number;
  name: string;
  category: string;
  group_name: string | null;
  priority: number;
  exclusive: boolean;
};

export type LoRA = {
  id: number;
  name: string;
  display_name: string | null;
  civitai_id: number | null;
  civitai_url: string | null;
  trigger_words: string[] | null;
  default_weight: number;
  weight_min: number;
  weight_max: number;
  base_models: string[] | null;
  character_defaults: Record<string, string> | null;
  recommended_negative: string[] | null;
  preview_image_url: string | null;
};

export type Character = {
  id: number;
  name: string;
  identity_tags: number[] | null;
  clothing_tags: number[] | null;
  lora_id: number | null;
  lora_weight: number | null;
  preview_image_url: string | null;
};

export type SDModelEntry = {
  id: number;
  name: string;
  display_name: string | null;
  model_type: string;
  base_model: string | null;
  civitai_id: number | null;
  civitai_url: string | null;
  description: string | null;
  preview_image_url: string | null;
  is_active: boolean;
};

export type Embedding = {
  id: number;
  name: string;
  display_name: string | null;
  embedding_type: string;
  trigger_word: string | null;
  description: string | null;
  is_active: boolean;
};

export type StyleProfile = {
  id: number;
  name: string;
  display_name: string | null;
  description: string | null;
  sd_model_id: number | null;
  loras: { lora_id: number; weight: number }[] | null;
  negative_embeddings: number[] | null;
  positive_embeddings: number[] | null;
  default_positive: string | null;
  default_negative: string | null;
  is_default: boolean;
  is_active: boolean;
};

export type StyleProfileFull = {
  id: number;
  name: string;
  display_name: string | null;
  description: string | null;
  sd_model: { id: number; name: string; display_name: string } | null;
  loras: { id: number; name: string; display_name: string; trigger_words: string[]; weight: number }[];
  negative_embeddings: { id: number; name: string; trigger_word: string }[];
  positive_embeddings: { id: number; name: string; trigger_word: string }[];
  default_positive: string | null;
  default_negative: string | null;
  is_default: boolean;
  is_active: boolean;
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
  audioDucking?: boolean;
  bgmVolume?: number;
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
  checkpoint?: AutopilotCheckpoint;
};
