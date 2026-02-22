// ── Shared UI Callback Types ──────────────────────────

export type UiCallbacks = {
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
    variant?: "default" | "danger";
  }) => Promise<boolean | string>;
};

export type UiCallbacksWithPrompt = UiCallbacks & {
  promptDialog: (opts: {
    title: string;
    message?: string;
    inputField: { label: string; placeholder?: string; defaultValue?: string };
  }) => Promise<boolean | string>;
};

export type GeminiSuggestion = {
  edit_type: string;
  issue: string;
  description: string;
  confidence: number;
  target_change: string;
};

export type SceneContextTags = {
  expression?: string[];
  gaze?: string; // exclusive (single select)
  pose?: string[];
  action?: string[];
  camera?: string; // exclusive (single select)
  environment?: string[];
  mood?: string[];
};

export type SceneCharacterAction = {
  character_id: number;
  tag_id: number;
  tag_name?: string; // GET 응답에서 enriched
  weight: number;
};

export type SceneMode = "single" | "multi";

export type Scene = {
  id: number;
  client_id: string;
  order: number; // 씬 순서 (1, 2, 3...)
  script: string;
  speaker: "Narrator" | "A" | "B";
  duration: number;
  scene_mode?: SceneMode;
  image_prompt: string;
  image_prompt_ko: string;
  image_url: string | null;
  image_asset_id?: number | null;
  width?: number;
  height?: number;
  candidates?: Array<{
    media_asset_id: number;
    match_rate?: number;
    image_url?: string; // Backend가 조회 시 채워줌
  }>;
  negative_prompt: string;
  isGenerating: boolean;
  debug_payload: string;
  debug_prompt?: string;
  context_tags?: SceneContextTags;
  prompt_history_id?: number; // Track which prompt history was applied
  activity_log_id?: number; // Track generation log for success/fail marking
  // Consistency Enhancements
  use_reference_only?: boolean;
  reference_only_weight?: number;
  // Background asset reference
  background_id?: number | null;
  environment_reference_id?: number | null;
  environment_reference_weight?: number;
  // Per-scene generation settings override (null = inherit global)
  use_controlnet?: boolean | null;
  controlnet_weight?: number | null;
  controlnet_pose?: string | null;
  use_ip_adapter?: boolean | null;
  ip_adapter_reference?: string | null;
  ip_adapter_weight?: number | null;
  negative_prompt_extra?: string | null;
  multi_gen_enabled?: boolean | null;
  // Auto-pin flag from backend (Gemini context_tags analysis)
  _auto_pin_previous?: boolean;
  // V3 scene-level character actions (expression/pose per character)
  character_actions?: SceneCharacterAction[];
  // Per-scene clothing override: { "<character_id>": ["tag1", "tag2"] }
  clothing_tags?: Record<string, string[]> | null;
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

export type AutoRunStepId = "images" | "validate" | "render";

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
  renderHistoryId?: number;
  projectId?: number;
  projectName?: string;
  groupId?: number;
  groupName?: string;
};

export type RenderHistoryItem = {
  id: number;
  label: string;
  url: string;
  created_at: string;
  storyboard_id: number;
  storyboard_title: string | null;
  project_id: number | null;
  project_name: string | null;
  group_id: number | null;
  group_name: string | null;
};

export type ToastItem = {
  id: string;
  message: string;
  type: "success" | "error" | "warning";
};

// Backward compat alias
export type Toast = ToastItem | null;

export type DraftScene = {
  id: number;
  client_id: string;
  script: string;
  speaker: Scene["speaker"];
  duration: number;
  scene_mode?: SceneMode;
  image_prompt: string;
  image_prompt_ko: string;
  image_url: string | null;
  image_asset_id?: number | null;
  candidates?: Array<{
    media_asset_id: number;
    match_rate?: number;
    image_url?: string; // Backend가 조회 시 채워줌
  }>;
  negative_prompt: string;
  context_tags?: SceneContextTags;
  prompt_history_id?: number;
  activity_log_id?: number;
  // Background asset reference
  background_id?: number | null;
  environment_reference_id?: number | null;
  environment_reference_weight?: number;
  // Per-scene generation settings override (null = inherit global)
  use_controlnet?: boolean | null;
  controlnet_weight?: number | null;
  use_ip_adapter?: boolean | null;
  ip_adapter_reference?: string | null;
  ip_adapter_weight?: number | null;
  multi_gen_enabled?: boolean | null;
  // V3 scene-level character actions (expression/pose per character)
  character_actions?: SceneCharacterAction[];
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
  wd14_count?: number;
};

export type LoRA = {
  id: number;
  name: string;
  display_name: string | null;
  gender_locked: ActorGender | null; // female, male, null(자유)
  civitai_id: number | null;
  civitai_url: string | null;
  trigger_words: string[] | null;
  default_weight: number;
  weight_min: number;
  weight_max: number;
  lora_type: string | null;
  base_model: string | null;
  character_defaults: Record<string, string> | null;
  recommended_negative: string[] | null;
  preview_image_url: string | null;
  // Calibration fields
  optimal_weight: number | null;
  calibration_score: number | null;
  // Multi-Character Support
  is_multi_character_capable?: boolean;
  multi_char_weight_scale?: number | null;
  multi_char_trigger_prompt?: string | null;
};

export type ReferenceImage = {
  character_key: string;
  character_id?: number;
  filename: string;
  preset?: { weight: number; model: string; description?: string };
};

export type CharacterLoRA = {
  lora_id: number;
  weight: number;
};

export type CharacterTagLink = {
  tag_id: number;
  name?: string;
  group_name?: string;
  layer?: number;
  weight: number;
  is_permanent: boolean;
};

export type Character = {
  id: number;
  style_profile_id: number | null;
  style_profile_name: string | null;
  name: string;
  description: string | null;
  gender: ActorGender | null;
  identity_tags: number[] | null; // Legacy
  clothing_tags: number[] | null; // Legacy
  tags: CharacterTagLink[] | null; // V3
  loras: CharacterLoRA[] | null;
  recommended_negative: string[] | null;
  custom_base_prompt: string | null;
  custom_negative_prompt: string | null;
  reference_base_prompt: string | null;
  reference_negative_prompt: string | null;
  preview_image_asset_id: number | null;
  preview_image_url: string | null;
  preview_key: string | null;
  preview_locked: boolean;
  prompt_mode: PromptMode;
  ip_adapter_weight: number | null;
  ip_adapter_model: string | null;
  voice_preset_id: number | null;
  deleted_at?: string | null;
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
  base_model: string | null;
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
  default_steps: number | null;
  default_cfg_scale: number | null;
  default_sampler_name: string | null;
  default_clip_skip: number | null;
  default_enable_hr: boolean | null;
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
  style_profile_id: number | null;
  style_profile_name: string | null;
  name: string;
  description: string | null;
  gender: ActorGender | null;
  tags: CharacterTagLink[];
  identity_tags: { id: number; name: string; group_name: string }[];
  clothing_tags: { id: number; name: string; group_name: string }[];
  loras: CharacterFullLoRA[];
  recommended_negative: string[];
  custom_base_prompt: string | null;
  custom_negative_prompt: string | null;
  reference_base_prompt: string | null;
  reference_negative_prompt: string | null;
  preview_image_url: string | null;
  prompt_mode: PromptMode;
  ip_adapter_weight: number | null;
  ip_adapter_model: string | null;
  ip_adapter_guidance_start: number | null;
  ip_adapter_guidance_end: number | null;
  reference_source_type: string | null;
  reference_images: { angle: string; asset_id: number }[] | null;
  voice_preset_id: number | null;
  effective_mode: EffectiveMode;
};

export type StyleProfileFull = {
  id: number;
  name: string;
  display_name: string | null;
  description: string | null;
  sd_model: { id: number; name: string; display_name: string } | null;
  loras: {
    id: number;
    name: string;
    display_name: string;
    trigger_words: string[];
    weight: number;
  }[];
  negative_embeddings: { id: number; name: string; trigger_word: string }[];
  positive_embeddings: { id: number; name: string; trigger_word: string }[];
  default_positive: string | null;
  default_negative: string | null;
  default_steps: number | null;
  default_cfg_scale: number | null;
  default_sampler_name: string | null;
  default_clip_skip: number | null;
  default_enable_hr: boolean | null;
  is_default: boolean;
  is_active: boolean;
};

export type DraftData = {
  topic?: string;
  description?: string;
  duration?: number;
  style?: string;
  language?: string;
  structure?: string;
  actorAGender?: ActorGender;
  selectedCharacterId?: number | null;
  basePromptA?: string;
  baseNegativePromptA?: string;
  includeSceneText?: boolean;
  bgmFile?: string | null;
  audioDucking?: boolean;
  bgmVolume?: number;
  subtitleFont?: string;
  speedMultiplier?: number;
  ttsEngine?: "qwen";
  voiceDesignPrompt?: string;
  overlaySettings?: OverlaySettings;
  postCardSettings?: PostCardSettings;
  layoutStyle?: "full" | "post";
  kenBurnsPreset?: KenBurnsPreset;
  kenBurnsIntensity?: number; // 0.5 ~ 2.0
  hiResEnabled?: boolean;
  veoEnabled?: boolean;
  useControlnet?: boolean;
  controlnetWeight?: number;
  useIpAdapter?: boolean;
  ipAdapterReference?: string;
  ipAdapterWeight?: number;
  // Environment Pinning defaults
  environmentReferenceWeight?: number;
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
  deleted_at?: string | null;
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

// ============================================================
// Storyboard List Types
// ============================================================

export type StoryboardCastMember = {
  id: number;
  name: string;
  speaker: string;
  preview_url: string | null;
};

export type StoryboardListItem = {
  id: number;
  title: string;
  description: string | null;
  scene_count: number;
  image_count: number;
  cast: StoryboardCastMember[];
  created_at: string | null;
  updated_at: string | null;
};

// ============================================================
// Project & Group Types
// ============================================================

export type ProjectItem = {
  id: number;
  name: string;
  description: string | null;
  handle: string | null;
  avatar_media_asset_id: number | null;
  avatar_url: string | null; // Read-only from backend
  avatar_key: string | null; // Read-only from backend (storage key for rendering)
  created_at: string | null;
};

export type RenderPreset = {
  id: number;
  name: string;
  description: string | null;
  is_system: boolean;
  bgm_file: string | null;
  bgm_volume: number | null;
  audio_ducking: boolean | null;
  scene_text_font: string | null;
  layout_style: string | null;
  frame_style: string | null;
  transition_type: string | null;
  ken_burns_preset: string | null;
  ken_burns_intensity: number | null;
  speed_multiplier: number | null;
  bgm_mode: string | null;
  music_preset_id: number | null;
};

export type VoicePreset = {
  id: number;
  name: string;
  description: string | null;
  source_type: "generated";
  audio_url: string | null;
  voice_design_prompt: string | null;
  voice_seed: number | null;
  language: string;
  sample_text: string | null;
  is_system: boolean;
  created_at: string;
};

export type MusicPreset = {
  id: number;
  name: string;
  description: string | null;
  prompt: string | null;
  duration: number | null;
  seed: number | null;
  audio_url: string | null;
  is_system: boolean;
  created_at: string | null;
};

export type Background = {
  id: number;
  name: string;
  description: string | null;
  image_url: string | null;
  image_asset_id: number | null;
  tags: string[] | null;
  category: string | null;
  weight: number;
  is_system: boolean;
  created_at: string;
};

export type GroupItem = {
  id: number;
  project_id: number;
  name: string;
  description: string | null;
};

// ============================================================
// YouTube Types
// ============================================================

export type YouTubeCredential = {
  project_id: number;
  channel_id: string | null;
  channel_title: string | null;
  is_valid: boolean;
  created_at: string | null;
};

export type YouTubeUploadStatus = {
  render_history_id: number;
  youtube_video_id: string | null;
  youtube_upload_status: string | null;
  youtube_uploaded_at: string | null;
};

// ============================================================
// Render Progress (SSE) Types
// ============================================================

export type RenderStage =
  | "queued"
  | "setup_avatars"
  | "process_scenes"
  | "calculate_durations"
  | "prepare_bgm"
  | "build_filters"
  | "encode"
  | "upload"
  | "completed"
  | "failed";

export type RenderProgress = {
  task_id: string;
  stage: RenderStage;
  percent: number;
  message: string;
  encode_percent: number;
  current_scene: number;
  total_scenes: number;
  elapsed_seconds?: number;
  estimated_remaining_seconds?: number;
  video_url?: string;
  media_asset_id?: number;
  render_history_id?: number;
  error?: string;
};

// ============================================================
// Image Generation Progress (SSE) Types
// ============================================================

export type ImageGenStage =
  | "queued"
  | "composing"
  | "generating"
  | "storing"
  | "completed"
  | "failed";

export type ImageGenProgress = {
  task_id: string;
  stage: ImageGenStage;
  percent: number;
  message: string;
  elapsed_seconds?: number;
  estimated_remaining_seconds?: number;
  preview_image?: string; // Base64 preview during generation
  // Flat fields from Backend SSE completed event
  image?: string; // Base64 result on completion
  used_prompt?: string;
  warnings?: string[];
  error?: string;
  controlnet_pose?: string;
  ip_adapter_reference?: string;
};

// ============================================================
// Script Generation SSE Types
// ============================================================

export type SceneReasoning = {
  narrative_function: string;
  why: string;
  alternatives: string[];
};

export type ConceptCandidate = {
  agent_role: string;
  title: string;
  concept: string;
  strengths?: string[];
  weaknesses?: string[];
};

export type NarrativeScore = {
  hook: number;
  emotional_arc: number;
  twist_payoff: number;
  speaker_tone: number;
  script_image_sync: number;
  overall: number;
  feedback?: string;
};

export type PipelineStep = {
  id: string;
  label: string;
  status: "idle" | "running" | "done" | "error";
  nodes?: string[];
};

export type QualityGate = {
  review_passed?: boolean;
  review_summary?: string;
  narrative_score?: NarrativeScore;
  checkpoint_score?: number | null; // 0.0-1.0
  checkpoint_decision?: "proceed" | "revise";
};

export type RevisionHistoryEntry = {
  attempt: number;
  errors?: string[];
  reflection?: string;
  score?: number;
  tier?: "rule_fix" | "expansion" | "regeneration";
};

export type DebateLogEntry = {
  round: number;
  action?: string;
  concepts?: Array<Record<string, unknown>>;
  [key: string]: unknown;
};

export type AgentMessageItem = {
  sender?: string;
  recipient?: string;
  message_type?: string;
  content?: string;
  [key: string]: unknown;
};

export type DirectorDecision = {
  decision?: string;
  feedback?: string;
  reasoning_steps?: Array<Record<string, unknown>>;
};

export type ProductionSnapshot = {
  director_plan?: {
    creative_goal?: string;
    target_emotion?: string;
    quality_criteria?: string[];
    style_direction?: string;
  };
  cinematographer?: Record<string, unknown>;
  tts_designer?: Record<string, unknown>;
  sound_designer?: Record<string, unknown>;
  copyright_reviewer?: Record<string, unknown>;
  director?: DirectorDecision;
  agent_messages?: AgentMessageItem[];
  quality_gate?: QualityGate;
  revision_history?: RevisionHistoryEntry[];
  debate_log?: DebateLogEntry[];
};

export type ScriptStreamEvent = {
  node: string;
  label: string;
  percent: number;
  status: "running" | "completed" | "error" | "waiting_for_input";
  node_result?: Record<string, unknown>;
  result?: {
    scenes?: Scene[];
    character_id?: number | null;
    character_b_id?: number | null;
    // concept_gate
    type?: "concept_selection";
    candidates?: ConceptCandidate[];
    selected_concept?: ConceptCandidate;
    evaluation?: Record<string, unknown>;
    // human_gate
    review_result?: Record<string, unknown>;
    scene_reasoning?: Record<string, unknown>[];
    production_snapshot?: ProductionSnapshot;
    // sound_designer → finalize
    sound_recommendation?: { prompt?: string; mood?: string; duration?: number };
  };
  error?: string;
  thread_id?: string;
  trace_id?: string;
};

export type ScriptPreset = {
  id: string;
  name: string;
  name_ko: string;
  description: string;
  mode: string;
  auto_approve: boolean;
};

export type ChannelDNA = {
  tone: string | null;
  target_audience: string | null;
  worldview: string | null;
  guidelines: string | null;
};

export type FeedbackPreset = {
  id: string;
  label: string;
  icon: string;
  has_params?: boolean;
  param_options?: Record<string, string[]>;
};

export type EffectiveConfig = {
  render_preset_id: number | null;
  style_profile_id: number | null;
  narrator_voice_preset_id: number | null;
  language: string | null;
  structure: string | null;
  duration: number | null;
  sd_steps: number | null;
  sd_cfg_scale: number | null;
  sd_sampler_name: string | null;
  sd_clip_skip: number | null;
  channel_dna: ChannelDNA | null;
  render_preset: RenderPreset | null;
  sources: Record<string, string>;
};
