export type SceneContextTags = {
  expression?: string[];
  gaze?: string;  // exclusive (single select)
  pose?: string[];
  action?: string[];
  camera?: string;  // exclusive (single select)
  environment?: string[];
  mood?: string[];
};

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
  context_tags?: SceneContextTags;
  prompt_history_id?: number;  // Track which prompt history was applied
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

// Ken Burns effect presets
export type KenBurnsPreset =
  | "none"
  | "slow_zoom"
  | "zoom_in_center"
  | "zoom_out_center"
  | "pan_left"
  | "pan_right"
  | "pan_up"
  | "pan_down"
  | "zoom_pan_left"
  | "zoom_pan_right"
  | "pan_up_vertical"
  | "pan_down_vertical"
  | "zoom_in_bottom"
  | "zoom_in_top"
  | "pan_zoom_up"
  | "pan_zoom_down"
  | "random";

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
  context_tags?: SceneContextTags;
  prompt_history_id?: number;
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
  gender_locked: ActorGender | null;  // female, male, null(자유)
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
  // Calibration fields
  optimal_weight: number | null;
  calibration_score: number | null;
};

export type CharacterLoRA = {
  lora_id: number;
  weight: number;
};

export type Character = {
  id: number;
  name: string;
  description: string | null;
  gender: ActorGender | null;
  identity_tags: number[] | null;
  clothing_tags: number[] | null;
  loras: CharacterLoRA[] | null;
  recommended_negative: string[] | null;
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

export type CharacterFullLoRA = {
  id: number;
  name: string;
  display_name: string;
  trigger_words: string[];
  weight: number;
  optimal_weight?: number;
  calibration_score?: number;
  lora_type?: string; // character, style, concept
};

export type PromptMode = "auto" | "standard" | "lora";
export type EffectiveMode = "standard" | "lora";

export type CharacterFull = {
  id: number;
  name: string;
  description: string | null;
  gender: ActorGender | null;
  identity_tags: { id: number; name: string; group_name: string }[];
  clothing_tags: { id: number; name: string; group_name: string }[];
  loras: CharacterFullLoRA[];
  recommended_negative: string[];
  preview_image_url: string | null;
  prompt_mode: PromptMode;
  effective_mode: EffectiveMode;
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
  selectedCharacterId?: number | null;
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
  kenBurnsPreset?: KenBurnsPreset;
  kenBurnsIntensity?: number;  // 0.5 ~ 2.0
  hiResEnabled?: boolean;
  veoEnabled?: boolean;
  useControlnet?: boolean;
  controlnetWeight?: number;
  useIpAdapter?: boolean;
  ipAdapterReference?: string;
  ipAdapterWeight?: number;
  videoUrl?: string | null;
  videoUrlFull?: string | null;
  videoUrlPost?: string | null;
  recentVideos?: RecentVideo[];
  scenes?: DraftScene[];
  checkpoint?: AutopilotCheckpoint;
};

// ============================================================
// Prompt History Types
// ============================================================

export type PromptHistoryLoRA = {
  lora_id: number;
  name: string;
  weight: number;
};

export type PromptHistory = {
  id: number;
  name: string;
  positive_prompt: string;
  negative_prompt: string | null;
  steps: number | null;
  cfg_scale: number | null;
  sampler_name: string | null;
  seed: number | null;
  clip_skip: number | null;
  character_id: number | null;
  lora_settings: PromptHistoryLoRA[] | null;
  context_tags: SceneContextTags | null;
  last_match_rate: number | null;
  avg_match_rate: number | null;
  validation_count: number;
  is_favorite: boolean;
  use_count: number;
  preview_image_url: string | null;
};

// Evaluation types (15.6)
export type TestPromptInfo = {
  name: string;
  description: string;
  tokens: string[];
  subject: string;
};

export type EvaluationResult = {
  id: number;
  test_name: string;
  mode: "standard" | "lora";
  character_id: number | null;
  character_name: string | null;
  match_rate: number | null;
  matched_tags: string[] | null;
  missing_tags: string[] | null;
  seed: number | null;
  batch_id: string | null;
  created_at: string | null;
};

export type EvaluationTestSummary = {
  test_name: string;
  standard_avg?: number;
  standard_count?: number;
  lora_avg?: number;
  lora_count?: number;
  diff: number;
  winner: "standard" | "lora" | "tie";
};

export type EvaluationSummary = {
  tests: EvaluationTestSummary[];
  overall: {
    standard_avg: number;
    lora_avg: number;
    diff: number;
    winner: "standard" | "lora" | "tie";
  };
};
