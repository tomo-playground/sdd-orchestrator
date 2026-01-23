"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Scene = {
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

type AudioItem = { name: string; url: string };
type FontItem = { name: string };
type OverlaySettings = {
  channel_name: string;
  avatar_key: string;
  likes_count: string;
  caption: string;
  frame_style: string;
};
type PostCardSettings = {
  channel_name: string;
  avatar_key: string;
  caption: string;
};
type SdModel = { title: string; model_name: string };
type ActorGender = "male" | "female";

const DEFAULT_BGM = "kawaii-dance-upbeat-japan-anime-edm-242104.mp3";
const DEFAULT_SUBTITLE_FONT = "온글잎 박다현체.ttf";
const DRAFT_STORAGE_KEY = "shorts-producer:draft:v1";
const MAX_IMAGE_CACHE_SIZE = 8_000_000;
const DEFAULT_OVERLAY_SETTINGS: OverlaySettings = {
  channel_name: "",
  avatar_key: "",
  likes_count: "",
  caption: "",
  frame_style: "overlay_minimal.png",
};
const DEFAULT_POST_CARD_SETTINGS: PostCardSettings = {
  channel_name: "",
  avatar_key: "",
  caption: "",
};
const AUTO_RUN_STEPS = [
  { id: "storyboard", label: "Storyboard" },
  { id: "fix", label: "Auto Fix" },
  { id: "images", label: "Images" },
  { id: "validate", label: "Validate" },
  { id: "render", label: "Render" },
] as const;
type AutoRunStepId = (typeof AUTO_RUN_STEPS)[number]["id"];
type ValidationIssue = { level: "warn" | "error"; message: string };
type SceneValidation = { status: "ok" | "warn" | "error"; issues: ValidationIssue[] };
type FixSuggestion = {
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
type ImageValidation = {
  match_rate: number;
  matched: string[];
  missing: string[];
  extra: string[];
};

const VOICES = [
  { id: "ko-KR-SunHiNeural", label: "SunHi (F)" },
  { id: "ko-KR-InJoonNeural", label: "InJoon (M)" },
  { id: "ko-KR-HyunsuMultilingualNeural", label: "Hyunsu (M)" },
];

const SAMPLERS = ["DPM++ 2M Karras", "Euler a", "Euler", "DDIM"];

const OVERLAY_STYLES = [{ id: "overlay_minimal.png", label: "Minimal" }];
const HEART_EMOJIS = ["❤", "💖", "💗", "💘", "💜", "💙", "💚", "🧡", "🤍"];
const ASCII_HEARTS = ["<3", "**", "^^", "<<>>"];
const PROMPT_SAMPLES = [
  {
    id: "eureka",
    label: "Eureka",
    basePrompt:
      "1girl, eureka, (black t-shirt:1.2), purple eyes, aqua hair, short hair, jeans, glasses, hairclip, short sleeves, <lora:eureka_v9:1.0>",
    baseNegative: "verybadimagenegative_v1.3",
  },
  {
    id: "chibi-laugh",
    label: "Chibi Laugh",
    basePrompt: "chibi, eyebrow, laughing, eyebrow down, <lora:chibi-laugh:0.6>",
    baseNegative: "easynegative",
  },
];

const STRUCTURES = ["Monologue"];
const CAMERA_KEYWORDS = [
  "close-up",
  "close up",
  "wide shot",
  "medium shot",
  "full body",
  "low angle",
  "high angle",
  "from above",
  "top-down",
];
const ACTION_KEYWORDS = [
  "sitting",
  "standing",
  "walking",
  "running",
  "jumping",
  "reading",
  "looking",
  "holding",
  "smiling",
  "crying",
  "talking",
];
const BACKGROUND_KEYWORDS = [
  "library",
  "street",
  "room",
  "city",
  "park",
  "school",
  "classroom",
  "bedroom",
  "office",
  "cafe",
  "forest",
  "beach",
  "sky",
];
const LIGHTING_KEYWORDS = [
  "lighting",
  "sunlight",
  "shadow",
  "moody",
  "warm",
  "soft light",
  "neon",
  "rain",
  "night",
  "sunset",
];

export default function Home() {
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState(10);
  const [style, setStyle] = useState("Anime");
  const [language, setLanguage] = useState("Korean");
  const [structure, setStructure] = useState("Monologue");
  const [actorAGender, setActorAGender] = useState<ActorGender>("female");
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [basePromptA, setBasePromptA] = useState("");
  const [baseNegativePromptA, setBaseNegativePromptA] = useState("");
  const [autoComposePrompt, setAutoComposePrompt] = useState(true);
  const [autoRewritePrompt, setAutoRewritePrompt] = useState(true);
  const [baseTab, setBaseTab] = useState<"global" | "A">("A");
  const [examplePrompt, setExamplePrompt] = useState("");
  const [suggestedBase, setSuggestedBase] = useState("");
  const [suggestedScene, setSuggestedScene] = useState("");
  const [multiGenEnabled, setMultiGenEnabled] = useState(true);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [isHelperOpen, setIsHelperOpen] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const [validationResults, setValidationResults] = useState<Record<number, SceneValidation>>({});
  const [validationSummary, setValidationSummary] = useState({ ok: 0, warn: 0, error: 0 });
  const [validationExpanded, setValidationExpanded] = useState<Record<number, boolean>>({});
  const [suggestionExpanded, setSuggestionExpanded] = useState<Record<number, boolean>>({});
  const [imageCheckMode, setImageCheckMode] = useState<"local" | "gemini">("local");
  const [imageValidationResults, setImageValidationResults] = useState<
    Record<number, ImageValidation>
  >({});
  const [validatingSceneId, setValidatingSceneId] = useState<number | null>(null);
  const [baseStepsA, setBaseStepsA] = useState(27);
  const [baseCfgScaleA, setBaseCfgScaleA] = useState(7);
  const [baseSamplerA, setBaseSamplerA] = useState("DPM++ 2M Karras");
  const [baseSeedA, setBaseSeedA] = useState(-1);
  const [baseClipSkipA, setBaseClipSkipA] = useState(2);
  const [selectedSampleId, setSelectedSampleId] = useState(PROMPT_SAMPLES[0].id);
  const [advancedExpanded, setAdvancedExpanded] = useState<Record<number, boolean>>({});
  const [sceneTab, setSceneTab] = useState<Record<number, "validate" | "debug" | null>>({});
  const [sceneMenuOpen, setSceneMenuOpen] = useState<number | null>(null);
  const prevBaseNegativeRefA = useRef("");
  const [includeSubtitles, setIncludeSubtitles] = useState(true);
  const [narratorVoice, setNarratorVoice] = useState(VOICES[0].id);
  const [bgmList, setBgmList] = useState<AudioItem[]>([]);
  const [bgmFile, setBgmFile] = useState<string | null>(DEFAULT_BGM);
  const [fontList, setFontList] = useState<FontItem[]>([]);
  const [subtitleFont, setSubtitleFont] = useState<string>(DEFAULT_SUBTITLE_FONT);
  const [loadedFonts, setLoadedFonts] = useState<Set<string>>(new Set());
  const [speedMultiplier, setSpeedMultiplier] = useState(1.3);
  const [overlaySettings, setOverlaySettings] = useState<OverlaySettings>(DEFAULT_OVERLAY_SETTINGS);
  const [postCardSettings, setPostCardSettings] = useState<PostCardSettings>(
    DEFAULT_POST_CARD_SETTINGS
  );
  const [sdModels, setSdModels] = useState<SdModel[]>([]);
  const [currentModel, setCurrentModel] = useState("Unknown");
  const [selectedModel, setSelectedModel] = useState("");
  const [isModelUpdating, setIsModelUpdating] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [isRegeneratingAvatar, setIsRegeneratingAvatar] = useState(false);
  const [overlayAvatarUrl, setOverlayAvatarUrl] = useState<string | null>(null);
  const [postAvatarUrl, setPostAvatarUrl] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoUrlFull, setVideoUrlFull] = useState<string | null>(null);
  const [videoUrlPost, setVideoUrlPost] = useState<string | null>(null);
  const [recentVideos, setRecentVideos] = useState<
    Array<{ url: string; label: "full" | "post" | "single"; createdAt: number }>
  >([]);
  const [layoutStyle, setLayoutStyle] = useState<"full" | "post">("full");
  const [motionStyle, setMotionStyle] = useState<"none" | "slow_zoom">("slow_zoom");
  const [hiResEnabled, setHiResEnabled] = useState(false);
  const [veoEnabled, setVeoEnabled] = useState(false);
  const [imagePreviewSrc, setImagePreviewSrc] = useState<string | null>(null);
  const [videoPreviewSrc, setVideoPreviewSrc] = useState<string | null>(null);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);
  const [autoRunState, setAutoRunState] = useState<{
    status: "idle" | "running" | "error" | "done";
    step: AutoRunStepId | "idle";
    message: string;
    error?: string;
  }>({ status: "idle", step: "idle", message: "" });
  const [autoRunLog, setAutoRunLog] = useState<string[]>([]);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [viewMode, setViewMode] = useState<"setup" | "working">("setup");
  const isAutoRunning = autoRunState.status === "running";
  const autoRunCancelRef = useRef(false);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);
  const draftSaveTimeoutRef = useRef<number | null>(null);
  const hasHydratedDraftRef = useRef(false);

  const slugifyAvatarKey = (value: string) => {
    const trimmed = value.trim().toLowerCase();
    const ascii = trimmed
      .normalize("NFKD")
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-+|-+$/g, "");
    if (ascii) return ascii;
    let hash = 0;
    for (let i = 0; i < trimmed.length; i += 1) {
      hash = (hash * 31 + trimmed.charCodeAt(i)) >>> 0;
    }
    return `channel-${hash.toString(16).slice(0, 6)}`;
  };

  const generateChannelName = (seedText: string) => {
    const adjectives = [
      "잔잔한",
      "빛나는",
      "조용한",
      "따뜻한",
      "느린",
      "고요한",
      "푸른",
      "은은한",
      "깊은",
      "희미한",
      "아련한",
      "눈부신",
      "부드러운",
      "차분한",
      "맑은",
      "희미한",
      "조심스런",
      "여린",
      "섬세한",
      "포근한",
      "잔잔한",
    ];
    const nouns = [
      "하늘",
      "밤",
      "바람",
      "별빛",
      "파도",
      "기억",
      "노을",
      "꿈",
      "길",
      "숲",
      "빛",
      "여운",
      "달",
      "안개",
      "새벽",
      "기척",
      "울림",
      "정원",
      "호수",
      "온기",
      "숨결",
      "편지",
    ];
    const base = seedText.trim() || "shorts";
    let hash = 0;
    for (let i = 0; i < base.length; i += 1) {
      hash = (hash * 31 + base.charCodeAt(i)) >>> 0;
    }
    const adjective = adjectives[hash % adjectives.length];
    const noun = nouns[Math.floor(hash / adjectives.length) % nouns.length];
    return `${adjective} ${noun}`;
  };

  const normalizeOverlaySettings = (raw: any): OverlaySettings => {
    const channelName = raw?.channel_name ?? raw?.profile_name ?? "";
    const avatarKey = raw?.avatar_key ?? raw?.profile_name ?? slugifyAvatarKey(channelName);
    return {
      ...DEFAULT_OVERLAY_SETTINGS,
      ...(raw || {}),
      channel_name: channelName,
      avatar_key: avatarKey,
    };
  };

  const normalizePostCardSettings = (raw: any): PostCardSettings => {
    const channelName = raw?.channel_name ?? raw?.profile_name ?? "";
    const avatarKey = raw?.avatar_key ?? raw?.profile_name ?? slugifyAvatarKey(channelName);
    return {
      ...DEFAULT_POST_CARD_SETTINGS,
      ...(raw || {}),
      channel_name: channelName,
      avatar_key: avatarKey,
    };
  };

  useEffect(() => {
    axios
      .get(`${API_BASE}/audio/list`)
      .then((res) => {
        const list = res.data.audios || [];
        setBgmList(list);
        const names = list.map((item: AudioItem) => item.name);
        if (bgmFile && !names.includes(bgmFile)) {
          setBgmFile(null);
        } else if (!bgmFile && names.includes(DEFAULT_BGM)) {
          setBgmFile(DEFAULT_BGM);
        }
      })
      .catch(() => setBgmList([]));
  }, []);

  useEffect(() => {
    axios
      .get(`${API_BASE}/fonts/list`)
      .then((res) => {
        const list = (res.data.fonts || []).map((name: string) => ({ name }));
        setFontList(list);
        if (list.length) {
          const hasCurrent = list.some((font: FontItem) => font.name === subtitleFont);
          const fallback = list.find((font: FontItem) => font.name === DEFAULT_SUBTITLE_FONT);
          if (!subtitleFont || subtitleFont === "Default" || !hasCurrent) {
            setSubtitleFont(fallback?.name ?? list[0].name);
          }
        }
      })
      .catch(() => setFontList([]));
  }, []);

  useEffect(() => {
    if (hasHydratedDraftRef.current) return;
    if (typeof window === "undefined") return;
    try {
      const stored = window.localStorage.getItem(DRAFT_STORAGE_KEY);
      if (!stored) {
        hasHydratedDraftRef.current = true;
        return;
      }
      const draft = JSON.parse(stored) as {
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
        recentVideos?: Array<{ url: string; label: "full" | "post" | "single"; createdAt: number }>;
        scenes?: Array<{
          id: number;
          script: string;
          speaker: Scene["speaker"];
          duration: number;
          image_prompt: string;
          image_prompt_ko: string;
          image_url?: string | null;
          negative_prompt: string;
          steps: number;
          cfg_scale: number;
          sampler_name: string;
          seed: number;
          clip_skip: number;
        }>;
      };
      if (draft.topic !== undefined) setTopic(draft.topic);
      if (draft.duration !== undefined) setDuration(draft.duration);
      if (draft.style !== undefined) setStyle(draft.style);
      if (draft.language !== undefined) setLanguage(draft.language);
      if (draft.structure !== undefined) setStructure(draft.structure);
      if (draft.actorAGender !== undefined) setActorAGender(draft.actorAGender);
      if (draft.basePromptA !== undefined) setBasePromptA(draft.basePromptA);
      if (draft.baseNegativePromptA !== undefined)
        setBaseNegativePromptA(draft.baseNegativePromptA);
      if (draft.baseStepsA !== undefined) setBaseStepsA(draft.baseStepsA);
      if (draft.baseCfgScaleA !== undefined) setBaseCfgScaleA(draft.baseCfgScaleA);
      if (draft.baseSamplerA !== undefined) setBaseSamplerA(draft.baseSamplerA);
      if (draft.baseSeedA !== undefined) setBaseSeedA(draft.baseSeedA);
      if (draft.baseClipSkipA !== undefined) setBaseClipSkipA(draft.baseClipSkipA);
      if (draft.includeSubtitles !== undefined) setIncludeSubtitles(draft.includeSubtitles);
      if (draft.narratorVoice !== undefined) setNarratorVoice(draft.narratorVoice);
      if (draft.bgmFile !== undefined) setBgmFile(draft.bgmFile);
      if (draft.subtitleFont !== undefined) setSubtitleFont(draft.subtitleFont);
      if (draft.speedMultiplier !== undefined) setSpeedMultiplier(draft.speedMultiplier);
      if (draft.overlaySettings !== undefined) {
        setOverlaySettings(normalizeOverlaySettings(draft.overlaySettings));
      }
      if (draft.postCardSettings !== undefined) {
        setPostCardSettings(normalizePostCardSettings(draft.postCardSettings));
      }
      if (draft.layoutStyle !== undefined) setLayoutStyle(draft.layoutStyle);
      if (draft.motionStyle !== undefined) setMotionStyle(draft.motionStyle);
      if (draft.hiResEnabled !== undefined) setHiResEnabled(draft.hiResEnabled);
      if (draft.veoEnabled !== undefined) setVeoEnabled(draft.veoEnabled);
      if (draft.videoUrl !== undefined) setVideoUrl(draft.videoUrl ?? null);
      if (draft.videoUrlFull !== undefined) setVideoUrlFull(draft.videoUrlFull ?? null);
      if (draft.videoUrlPost !== undefined) setVideoUrlPost(draft.videoUrlPost ?? null);
      if (Array.isArray(draft.recentVideos)) setRecentVideos(draft.recentVideos);
      if (Array.isArray(draft.scenes)) {
        setScenes(
          draft.scenes.map((scene: Partial<Scene> & { id: number }) => ({
            ...scene,
            image_url: scene.image_url ?? null,
            candidates: Array.isArray(scene.candidates) ? scene.candidates : [],
            isGenerating: false,
            debug_prompt: "",
            debug_payload: "",
          })) as Scene[]
        );
        setCurrentSceneIndex(0);
      }
    } catch {
      // Ignore malformed drafts.
    } finally {
      hasHydratedDraftRef.current = true;
    }
  }, []);

  useEffect(() => {
    if (!hasHydratedDraftRef.current) return;
    if (typeof window === "undefined") return;
    if (draftSaveTimeoutRef.current) {
      window.clearTimeout(draftSaveTimeoutRef.current);
    }
    draftSaveTimeoutRef.current = window.setTimeout(() => {
      const draftScenes = scenes.map((scene) => ({
        id: scene.id,
        script: scene.script,
        speaker: scene.speaker,
        duration: scene.duration,
        image_prompt: scene.image_prompt,
        image_prompt_ko: scene.image_prompt_ko,
        image_url: scene.image_url,
        candidates: scene.candidates ?? [],
        negative_prompt: scene.negative_prompt,
        steps: scene.steps,
        cfg_scale: scene.cfg_scale,
        sampler_name: scene.sampler_name,
        seed: scene.seed,
        clip_skip: scene.clip_skip,
      }));
      const totalImageSize = draftScenes.reduce((acc, scene) => {
        const baseSize = scene.image_url ? scene.image_url.length : 0;
        const candidateSize = (scene.candidates || []).reduce((sum, candidate) => {
          return sum + (candidate.image_url ? candidate.image_url.length : 0);
        }, 0);
        return acc + baseSize + candidateSize;
      }, 0);
      if (totalImageSize > MAX_IMAGE_CACHE_SIZE) {
        draftScenes.forEach((scene) => {
          scene.image_url = null;
          scene.candidates = [];
        });
      }
      const draft = {
        topic,
        duration,
        style,
        language,
        structure,
        actorAGender,
        basePromptA,
        baseNegativePromptA,
        baseStepsA,
        baseCfgScaleA,
        baseSamplerA,
        baseSeedA,
        baseClipSkipA,
        includeSubtitles,
        narratorVoice,
        bgmFile,
        subtitleFont,
        speedMultiplier,
        overlaySettings,
        postCardSettings,
        layoutStyle,
        motionStyle,
        hiResEnabled,
        veoEnabled,
        videoUrl,
        videoUrlFull,
        videoUrlPost,
        recentVideos,
        scenes: draftScenes,
      };
      try {
        window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
      } catch (error) {
        if (error instanceof DOMException && error.name === "QuotaExceededError") {
          const slimScenes = draftScenes.map((scene) => ({
            ...scene,
            image_url: null,
            candidates: [],
          }));
          const slimDraft = {
            ...draft,
            recentVideos: [],
            scenes: slimScenes,
          };
          window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(slimDraft));
        } else {
          console.error(error);
        }
      }
    }, 300);
    return () => {
      if (draftSaveTimeoutRef.current) {
        window.clearTimeout(draftSaveTimeoutRef.current);
        draftSaveTimeoutRef.current = null;
      }
    };
  }, [
    topic,
    duration,
    style,
    language,
    structure,
    actorAGender,
    basePromptA,
    baseNegativePromptA,
    baseStepsA,
    baseCfgScaleA,
    baseSamplerA,
    baseSeedA,
    baseClipSkipA,
    includeSubtitles,
    narratorVoice,
    bgmFile,
    subtitleFont,
    speedMultiplier,
    overlaySettings,
    postCardSettings,
    layoutStyle,
    motionStyle,
    hiResEnabled,
    veoEnabled,
    videoUrl,
    videoUrlFull,
    videoUrlPost,
    recentVideos,
    scenes,
  ]);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        if (typeof window !== "undefined") {
          const cached = window.sessionStorage.getItem("sdOptionsCache");
          if (cached) {
            const parsed = JSON.parse(cached) as { models: SdModel[]; modelName: string };
            setSdModels(parsed.models);
            setCurrentModel(parsed.modelName);
            setSelectedModel(parsed.modelName);
            return;
          }
        }
        const [modelsRes, optionsRes] = await Promise.all([
          axios.get(`${API_BASE}/sd/models`),
          axios.get(`${API_BASE}/sd/options`),
        ]);
        const models = (modelsRes.data.models || []) as SdModel[];
        const modelName = optionsRes.data.model || "Unknown";
        setSdModels(models);
        setCurrentModel(modelName);
        setSelectedModel(modelName);
        if (typeof window !== "undefined") {
          window.sessionStorage.setItem("sdOptionsCache", JSON.stringify({ models, modelName }));
        }
      } catch {
        setSdModels([]);
      }
    };
    void fetchModels();
  }, []);

  // Toast helper
  const showToast = (message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      // Arrow Left/Right: Navigate scenes
      if (e.key === "ArrowLeft" && scenes.length > 0) {
        e.preventDefault();
        setCurrentSceneIndex((prev) => Math.max(0, prev - 1));
      }
      if (e.key === "ArrowRight" && scenes.length > 0) {
        e.preventDefault();
        setCurrentSceneIndex((prev) => Math.min(scenes.length - 1, prev + 1));
      }

      // Escape: Close modals
      if (e.key === "Escape") {
        setImagePreviewSrc(null);
        setVideoPreviewSrc(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [scenes.length]);

  // Dynamic font loading for preview
  useEffect(() => {
    if (!subtitleFont || loadedFonts.has(subtitleFont)) return;
    const fontUrl = `${API_BASE}/fonts/file/${encodeURIComponent(subtitleFont)}`;
    const fontFace = new FontFace(subtitleFont, `url(${fontUrl})`);
    fontFace
      .load()
      .then((loaded) => {
        document.fonts.add(loaded);
        setLoadedFonts((prev) => new Set(prev).add(subtitleFont));
      })
      .catch((err) => {
        console.warn("Font load failed:", subtitleFont, err);
      });
  }, [subtitleFont, loadedFonts]);

  const canRender = useMemo(() => {
    return scenes.length > 0 && scenes.every((scene) => !!scene.image_url);
  }, [scenes]);

  const updateScene = (id: number, patch: Partial<Scene>) => {
    setScenes((prev) => prev.map((scene) => (scene.id === id ? { ...scene, ...patch } : scene)));
  };

  const mapStoryboardScenes = (incoming: any[]) => {
    return incoming.map((scene: any, idx: number) => {
      const rawSpeaker = String(scene.speaker ?? "Narrator");
      const speaker: Scene["speaker"] =
        rawSpeaker === "A" || rawSpeaker === "Narrator"
          ? (rawSpeaker as Scene["speaker"])
          : "Narrator";
      const baseSettings = getBaseSettingsForSpeaker(speaker);
      return {
        id: scene.scene_id ?? idx + 1,
        script: scene.script ?? "",
        speaker,
        duration: Number(scene.duration ?? 3),
        image_prompt: scene.image_prompt ?? "",
        image_prompt_ko: scene.image_prompt_ko ?? "",
        image_url: null,
        negative_prompt: baseNegativePromptA,
        steps: baseSettings.steps,
        cfg_scale: baseSettings.cfg,
        sampler_name: baseSettings.sampler,
        seed: baseSettings.seed,
        clip_skip: baseSettings.clipSkip,
        isGenerating: false,
        debug_payload: "",
      };
    });
  };

  const fetchStoryboardScenes = async () => {
    const res = await axios.post(`${API_BASE}/storyboard/create`, {
      topic,
      duration,
      style,
      language,
      structure,
      actor_a_gender: actorAGender,
    });
    const incoming = Array.isArray(res.data.scenes) ? res.data.scenes : [];
    return mapStoryboardScenes(incoming);
  };

  const handleGenerateScenes = async () => {
    if (!topic.trim()) return;
    setIsGenerating(true);
    try {
      const mapped = await fetchStoryboardScenes();
      setScenes(mapped);
      setCurrentSceneIndex(0);
      const overlayAuto = buildOverlayContext(mapped);
      setOverlaySettings((prev) => ({
        ...prev,
        ...overlayAuto,
      }));
      const postAuto = buildPostCardContext(mapped);
      setPostCardSettings((prev) => ({ ...prev, ...postAuto }));
    } catch {
      alert("Storyboard generation failed");
    } finally {
      setIsGenerating(false);
    }
  };

  const stripLeadingHearts = (text: string) => {
    let result = text.trimStart();
    let updated = true;
    while (updated) {
      updated = false;
      for (const heart of HEART_EMOJIS) {
        if (result.startsWith(heart)) {
          result = result.slice(heart.length).trimStart();
          updated = true;
        }
      }
    }
    return result;
  };

  const applyHeartPrefix = (text: string) => {
    const cleaned = stripLeadingHearts(text);
    const hearts = Array.from({ length: 3 }, () => {
      const idx = Math.floor(Math.random() * ASCII_HEARTS.length);
      return ASCII_HEARTS[idx];
    }).join("");
    if (!cleaned) return hearts;
    return `${hearts} ${cleaned}`;
  };

  const buildOverlayContext = (scenesOverride: Scene[] = scenes) => {
    const fallbackProfile = generateChannelName(topic);
    const scripts = scenesOverride.map((scene) => scene.script.trim()).filter(Boolean);
    const baseCaption = scripts[0] || topic.trim() || "오늘의 쇼츠";
    const hashtagSource = (topic || baseCaption).split(/\s+/).slice(0, 2);
    const hashtags = hashtagSource
      .map((token) => token.replace(/[^\w가-힣]/g, ""))
      .filter(Boolean)
      .map((token) => `#${token}`);
    const caption = applyHeartPrefix(hashtags.join(" "));
    const likesPool = ["1.2k", "3.8k", "7.4k", "12.5k", "18.9k"];
    const likes_count = likesPool[baseCaption.length % likesPool.length];
    return {
      channel_name: fallbackProfile,
      avatar_key: slugifyAvatarKey(fallbackProfile),
      likes_count,
      caption,
    };
  };

  const buildPostCardContext = (scenesOverride: Scene[] = scenes) => {
    const overlay = buildOverlayContext(scenesOverride);
    return {
      channel_name: overlay.channel_name,
      avatar_key: overlay.avatar_key,
      caption: overlay.caption,
    };
  };

  const handleImageUpload = (sceneId: number, file?: File) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = async () => {
      const dataUrl = reader.result as string;
      const storedUrl = await storeSceneImage(dataUrl);
      updateScene(sceneId, { image_url: storedUrl, candidates: [] });
    };
    reader.readAsDataURL(file);
  };

  const handleAddScene = () => {
    const baseSettings = getBaseSettingsForSpeaker("Narrator");
    setScenes((prev) => [
      ...prev,
      {
        id: prev.length ? Math.max(...prev.map((scene) => scene.id)) + 1 : 1,
        script: "",
        speaker: "Narrator",
        duration: 3,
        image_prompt: "",
        image_prompt_ko: "",
        image_url: null,
        negative_prompt: baseNegativePromptA,
        steps: baseSettings.steps,
        cfg_scale: baseSettings.cfg,
        sampler_name: baseSettings.sampler,
        seed: baseSettings.seed,
        clip_skip: baseSettings.clipSkip,
        isGenerating: false,
        debug_payload: "",
      },
    ]);
  };

  const handleRemoveScene = (sceneId: number) => {
    setScenes((prev) => {
      const newScenes = prev.filter((scene) => scene.id !== sceneId);
      // Adjust currentSceneIndex if needed
      if (currentSceneIndex >= newScenes.length && newScenes.length > 0) {
        setCurrentSceneIndex(newScenes.length - 1);
      }
      return newScenes;
    });
  };

  const getBaseNegativeForScene = () => baseNegativePromptA.trim();

  const pushRecentVideo = (url: string, label: "full" | "post" | "single") => {
    if (!url) return;
    setRecentVideos((prev) => {
      const filtered = prev.filter((item) => item.url !== url);
      const next = [{ url, label, createdAt: Date.now() }, ...filtered];
      return next.slice(0, 8);
    });
  };

  const getVideoFilename = (url: string) => {
    try {
      const parsed = new URL(url, window.location.origin);
      return decodeURIComponent(parsed.pathname.split("/").pop() || "");
    } catch {
      const last = url.split("/").pop() || "";
      const clean = last.split("?")[0].split("#")[0];
      return decodeURIComponent(clean);
    }
  };

  const handleDeleteRecentVideo = async (url: string) => {
    const filename = getVideoFilename(url);
    if (!filename) return;
    try {
      await axios.post(`${API_BASE}/video/delete`, { filename });
      setRecentVideos((prev) => prev.filter((item) => item.url !== url));
      if (videoUrl === url) setVideoUrl(null);
      if (videoUrlFull === url) setVideoUrlFull(null);
      if (videoUrlPost === url) setVideoUrlPost(null);
    } catch {
      alert("Failed to delete video");
    }
  };

  useEffect(() => {
    if (!recentVideos.length) return;
    let isActive = true;
    const pruneMissing = async () => {
      const checks = await Promise.all(
        recentVideos.map(async (item) => {
          const filename = getVideoFilename(item.url);
          if (!filename) return { url: item.url, exists: false };
          try {
            const res = await fetch(
              `${API_BASE}/video/exists?filename=${encodeURIComponent(filename)}`
            );
            if (!res.ok) return { url: item.url, exists: false };
            const data = await res.json();
            return { url: item.url, exists: Boolean(data?.exists) };
          } catch {
            return { url: item.url, exists: true };
          }
        })
      );
      if (!isActive) return;
      const missing = new Set(checks.filter((item) => !item.exists).map((item) => item.url));
      if (!missing.size) return;
      setRecentVideos((prev) => prev.filter((item) => !missing.has(item.url)));
      if (videoUrl && missing.has(videoUrl)) setVideoUrl(null);
      if (videoUrlFull && missing.has(videoUrlFull)) setVideoUrlFull(null);
      if (videoUrlPost && missing.has(videoUrlPost)) setVideoUrlPost(null);
    };
    void pruneMissing();
    return () => {
      isActive = false;
    };
  }, [recentVideos, videoUrl, videoUrlFull, videoUrlPost]);

  useEffect(() => {
    const prevBase = prevBaseNegativeRefA.current;
    if (prevBase === baseNegativePromptA) return;
    setScenes((prev) =>
      prev.map((scene) => {
        if (!scene.negative_prompt || scene.negative_prompt === prevBase) {
          return { ...scene, negative_prompt: baseNegativePromptA };
        }
        return scene;
      })
    );
    prevBaseNegativeRefA.current = baseNegativePromptA;
  }, [baseNegativePromptA]);

  const handleRenderVideo = async () => {
    const url = await requestRenderVideo(layoutStyle);
    if (url) {
      const urlWithTs = `${url}?t=${Date.now()}`;
      setVideoUrl(urlWithTs);
      pushRecentVideo(urlWithTs, "single");
    } else {
      setVideoUrl(url);
    }
    return Boolean(url);
  };

  const handleRenderFull = async () => {
    const url = await requestRenderVideo("full");
    if (url) {
      const urlWithTs = `${url}?t=${Date.now()}`;
      setVideoUrlFull(urlWithTs);
      setVideoUrl(urlWithTs);
      pushRecentVideo(urlWithTs, "full");
      showToast("Full 렌더링 완료!", "success");
    } else {
      showToast("Full 렌더링 실패", "error");
    }
    return Boolean(url);
  };

  const handleRenderPost = async () => {
    const url = await requestRenderVideo("post");
    if (url) {
      const urlWithTs = `${url}?t=${Date.now()}`;
      setVideoUrlPost(urlWithTs);
      setVideoUrl(urlWithTs);
      pushRecentVideo(urlWithTs, "post");
      showToast("Post 렌더링 완료!", "success");
    } else {
      showToast("Post 렌더링 실패", "error");
    }
    return Boolean(url);
  };

  const handleRenderBoth = async () => {
    setIsRendering(true);
    try {
      // Render Full
      const fullUrl = await requestRenderVideo("full", true);
      if (fullUrl) {
        const fullUrlWithTs = `${fullUrl}?t=${Date.now()}`;
        setVideoUrlFull(fullUrlWithTs);
        setVideoUrl(fullUrlWithTs);
        pushRecentVideo(fullUrlWithTs, "full");
      }
      // Render Post
      const postUrl = await requestRenderVideo("post", true);
      if (postUrl) {
        const postUrlWithTs = `${postUrl}?t=${Date.now()}`;
        setVideoUrlPost(postUrlWithTs);
        pushRecentVideo(postUrlWithTs, "post");
      }
      if (fullUrl && postUrl) {
        showToast("Full + Post 렌더링 완료!", "success");
      } else if (fullUrl || postUrl) {
        showToast("일부 렌더링 완료", "success");
      } else {
        showToast("렌더링 실패", "error");
      }
    } catch {
      showToast("렌더링 실패", "error");
    } finally {
      setIsRendering(false);
    }
  };

  const buildRenderPayload = (
    layoutOverride?: "full" | "post",
    scenesOverride?: Scene[],
    overlayOverride?: OverlaySettings,
    postCardOverride?: PostCardSettings
  ) => ({
    scenes: (scenesOverride ?? scenes).map((scene) => ({
      image_url: scene.image_url,
      script: scene.script,
      speaker: scene.speaker,
      duration: scene.duration,
    })),
    project_name: topic.trim().replace(/\s+/g, "_") || "my_shorts",
    width: 1080,
    height: 1920,
    layout_style: layoutOverride ?? layoutStyle,
    motion_style: motionStyle,
    narrator_voice: narratorVoice,
    bgm_file: bgmFile,
    speed_multiplier: speedMultiplier,
    include_subtitles: includeSubtitles,
    subtitle_font: subtitleFont,
    overlay_settings: overlayOverride ?? overlaySettings,
    post_card_settings: postCardOverride ?? postCardSettings,
  });

  const requestRenderVideo = async (
    layoutOverride?: "full" | "post",
    silent = false,
    scenesOverride?: Scene[],
    overlayOverride?: OverlaySettings,
    postCardOverride?: PostCardSettings
  ) => {
    if (!canRender && !silent) return null;
    setIsRendering(true);
    try {
      const res = await axios.post(
        `${API_BASE}/video/create`,
        buildRenderPayload(layoutOverride, scenesOverride, overlayOverride, postCardOverride)
      );
      return res.data.video_url || null;
    } catch {
      if (!silent) {
        alert("Video rendering failed");
      }
      return null;
    } finally {
      setIsRendering(false);
    }
  };

  const pushAutoRunLog = (message: string) => {
    setAutoRunLog((prev) => {
      const next = [...prev, message];
      return next.slice(-6);
    });
  };

  const runAutoRunFromStep = async (startStep: AutoRunStepId) => {
    if (!topic.trim()) {
      alert("Enter a topic first.");
      return;
    }
    autoRunCancelRef.current = false;
    setAutoRunLog([]);
    let workingScenes = scenes;
    let currentStep: AutoRunStepId = startStep;
    setMotionStyle("none");
    const assertNotCancelled = () => {
      if (autoRunCancelRef.current) {
        throw new Error("Autopilot cancelled");
      }
    };
    try {
      const overlayAuto = buildOverlayContext(workingScenes);
      setOverlaySettings((prev) => ({ ...prev, ...overlayAuto }));
      setPostCardSettings(buildPostCardContext(workingScenes));
      const steps = AUTO_RUN_STEPS.map((step) => step.id);
      const startIndex = steps.indexOf(startStep);
      for (let idx = startIndex; idx < steps.length; idx += 1) {
        currentStep = steps[idx];
        assertNotCancelled();
        if (currentStep === "storyboard") {
          setAutoRunState({
            status: "running",
            step: "storyboard",
            message: "Generating storyboard...",
          });
          pushAutoRunLog("Storyboard started");
          workingScenes = await fetchStoryboardScenes();
          if (!workingScenes.length) {
            throw new Error("Storyboard is empty");
          }
          setScenes(workingScenes);
          const storyboardOverlay = buildOverlayContext(workingScenes);
          setOverlaySettings((prev) => ({ ...prev, ...storyboardOverlay }));
          setPostCardSettings(buildPostCardContext(workingScenes));
          pushAutoRunLog(`Storyboard created (${workingScenes.length} scenes)`);
        }

        if (currentStep === "fix") {
          setAutoRunState({
            status: "running",
            step: "fix",
            message: "Auto-fixing scripts and prompts...",
          });
          workingScenes = applyAutoFixForScenes(workingScenes);
          setScenes(workingScenes);
          const { results, summary } = computeValidationResults(workingScenes);
          setValidationResults(results);
          setValidationSummary(summary);
          pushAutoRunLog("Auto-fix applied");
        }

        if (currentStep === "images") {
          setAutoRunState({
            status: "running",
            step: "images",
            message: "Generating scene images...",
          });
          for (const scene of workingScenes) {
            assertNotCancelled();
            if (scene.image_url) {
              continue;
            }
            updateScene(scene.id, { isGenerating: true });
            let result = multiGenEnabled
              ? await generateSceneCandidates(scene, true)
              : await generateSceneImageFor(scene, true);
            if (!result || !result.image_url) {
              pushAutoRunLog(`Retry image generation (Scene ${scene.id})`);
              result = multiGenEnabled
                ? await generateSceneCandidates(scene, true)
                : await generateSceneImageFor(scene, true);
            }
            updateScene(scene.id, { isGenerating: false });
            if (!result || !result.image_url) {
              throw new Error(`Image generation failed for Scene ${scene.id}`);
            }
            updateScene(scene.id, result);
            workingScenes = workingScenes.map((item) =>
              item.id === scene.id ? { ...item, ...result } : item
            );
          }
          pushAutoRunLog("Images generated");
        }

        if (currentStep === "validate") {
          setAutoRunState({ status: "running", step: "validate", message: "Validating images..." });
          for (const scene of workingScenes) {
            assertNotCancelled();
            if (!scene.image_url) continue;
            await validateSceneImage(scene, true);
          }
          const { results, summary } = computeValidationResults(workingScenes);
          setValidationResults(results);
          setValidationSummary(summary);
          if (summary.error > 0) {
            throw new Error(`Validation failed (${summary.error} errors)`);
          }
          pushAutoRunLog("Validation complete");
        }

        if (currentStep === "render") {
          setAutoRunState({ status: "running", step: "render", message: "Rendering video..." });
          const overlayAuto = buildOverlayContext(workingScenes);
          const mergedOverlay = { ...overlaySettings, ...overlayAuto };
          setOverlaySettings(mergedOverlay);
          const postAuto = buildPostCardContext(workingScenes);
          const mergedPostCard = { ...postCardSettings, ...postAuto };
          setPostCardSettings(mergedPostCard);
          const fullUrl = await requestRenderVideo(
            "full",
            true,
            workingScenes,
            mergedOverlay,
            mergedPostCard
          );
          if (!fullUrl) {
            throw new Error("Full render failed");
          }
          const fullUrlWithTs = `${fullUrl}?t=${Date.now()}`;
          setVideoUrlFull(fullUrlWithTs);
          setVideoUrl(fullUrlWithTs);
          pushRecentVideo(fullUrlWithTs, "full");
          pushAutoRunLog("Full render complete");
          const postUrl = await requestRenderVideo(
            "post",
            true,
            workingScenes,
            mergedOverlay,
            mergedPostCard
          );
          if (!postUrl) {
            throw new Error("Post render failed");
          }
          const postUrlWithTs = `${postUrl}?t=${Date.now()}`;
          setVideoUrlPost(postUrlWithTs);
          pushRecentVideo(postUrlWithTs, "post");
          pushAutoRunLog("Post render complete");
        }
      }
      setAutoRunState({ status: "done", step: "render", message: "Autopilot complete." });
      showToast("Auto Run 완료! 영상이 생성되었습니다.", "success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Autopilot failed";
      const failedMessage =
        message === "Autopilot cancelled" ? "Autopilot cancelled." : "Autopilot failed.";
      setAutoRunState({
        status: "error",
        step: currentStep,
        message: failedMessage,
        error: message,
      });
      pushAutoRunLog(message);
      if (message !== "Autopilot cancelled") {
        alert(`Autopilot stopped: ${message}`);
      }
    }
  };

  const handleAutoRun = async () => {
    await runAutoRunFromStep("storyboard");
  };

  const handleAutoRunResume = async () => {
    if (autoRunState.step === "idle") return;
    await runAutoRunFromStep(autoRunState.step);
  };

  const handleAutoRunCancel = () => {
    if (!isAutoRunning) return;
    autoRunCancelRef.current = true;
    pushAutoRunLog("Autopilot cancel requested");
  };

  const autoRunProgress = useMemo(() => {
    if (autoRunState.status === "done") return 100;
    if (autoRunState.step === "idle") return 0;
    const index = AUTO_RUN_STEPS.findIndex((step) => step.id === autoRunState.step);
    if (index < 0) return 0;
    return Math.round(((index + 1) / AUTO_RUN_STEPS.length) * 100);
  }, [autoRunState.status, autoRunState.step]);

  const resetScenesOnly = () => {
    setScenes([]);
    setCurrentSceneIndex(0);
    setValidationResults({});
    setValidationSummary({ ok: 0, warn: 0, error: 0 });
    setValidationExpanded({});
    setSuggestionExpanded({});
    setImageValidationResults({});
    setVideoUrl(null);
    setVideoUrlFull(null);
    setVideoUrlPost(null);
  };

  const resetDraft = () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(DRAFT_STORAGE_KEY);
    }
    setTopic("");
    setDuration(10);
    setStyle("Anime");
    setLanguage("Korean");
    setStructure("Monologue");
    setActorAGender("female");
    setBasePromptA("");
    setBaseNegativePromptA("");
    setAutoComposePrompt(true);
    setAutoRewritePrompt(true);
    setBaseTab("A");
    setExamplePrompt("");
    setSuggestedBase("");
    setSuggestedScene("");
    setIsHelperOpen(false);
    setCopyStatus("");
    setImageCheckMode("local");
    setBaseStepsA(27);
    setBaseCfgScaleA(7);
    setBaseSamplerA("DPM++ 2M Karras");
    setBaseSeedA(-1);
    setBaseClipSkipA(2);
    setIncludeSubtitles(true);
    setNarratorVoice(VOICES[0].id);
    setBgmFile(DEFAULT_BGM);
    setSpeedMultiplier(1.3);
    setSubtitleFont(DEFAULT_SUBTITLE_FONT);
    setOverlaySettings(DEFAULT_OVERLAY_SETTINGS);
    setPostCardSettings(DEFAULT_POST_CARD_SETTINGS);
    setLayoutStyle("full");
    setMotionStyle("slow_zoom");
    setHiResEnabled(false);
    setVeoEnabled(false);
    setImagePreviewSrc(null);
    setAutoRunState({ status: "idle", step: "idle", message: "" });
    setAutoRunLog([]);
    resetScenesOnly();
  };

  const handleModelChange = async (value: string) => {
    if (!value) return;
    setSelectedModel(value);
    setIsModelUpdating(true);
    try {
      const res = await axios.post(`${API_BASE}/sd/options`, {
        sd_model_checkpoint: value,
      });
      setCurrentModel(res.data.model || value);
    } catch {
      alert("Model update failed");
      setSelectedModel(currentModel);
    } finally {
      setIsModelUpdating(false);
    }
  };

  const stopBgmPreview = () => {
    if (previewTimeoutRef.current) {
      window.clearTimeout(previewTimeoutRef.current);
      previewTimeoutRef.current = null;
    }
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current.currentTime = 0;
    }
    setIsPreviewingBgm(false);
  };

  const handlePreviewBgm = (urlOverride?: string) => {
    const sourceUrl = urlOverride ?? bgmList.find((bgm) => bgm.name === bgmFile)?.url ?? "";
    if (!sourceUrl) {
      alert("Select a BGM first.");
      return;
    }
    stopBgmPreview();
    const audio = new Audio(sourceUrl);
    previewAudioRef.current = audio;
    setIsPreviewingBgm(true);
    audio.play().catch(() => {
      stopBgmPreview();
      alert("BGM preview failed.");
    });
    previewTimeoutRef.current = window.setTimeout(() => {
      stopBgmPreview();
    }, 10000);
  };

  const getAvatarInitial = (name: string) => {
    const trimmed = name.trim();
    return (trimmed[0] || "A").toUpperCase();
  };

  const resolveAvatarPreview = async (avatarKey: string, setUrl: (url: string | null) => void) => {
    const trimmed = avatarKey.trim();
    if (!trimmed) {
      setUrl(null);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/avatar/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ avatar_key: trimmed }),
      });
      if (!res.ok) {
        setUrl(null);
        return;
      }
      const data = await res.json();
      if (data?.filename) {
        setUrl(`${API_BASE}/outputs/avatars/${data.filename}?t=${Date.now()}`);
      } else {
        setUrl(null);
      }
    } catch (error) {
      console.error(error);
      setUrl(null);
    }
  };

  const handleRegenerateAvatar = async (avatarKey: string) => {
    const trimmed = avatarKey.trim();
    if (!trimmed) {
      alert("Enter an avatar key first.");
      return;
    }
    setIsRegeneratingAvatar(true);
    try {
      const res = await fetch(`${API_BASE}/avatar/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ avatar_key: trimmed }),
      });
      if (!res.ok) {
        throw new Error("Avatar regenerate failed");
      }
      const data = await res.json();
      if (data?.filename) {
        const url = `${API_BASE}/outputs/avatars/${data.filename}?t=${Date.now()}`;
        if (trimmed === overlaySettings.avatar_key.trim()) {
          setOverlayAvatarUrl(url);
        }
        if (trimmed === postCardSettings.avatar_key.trim()) {
          setPostAvatarUrl(url);
        }
      }
    } catch (error) {
      console.error(error);
      alert("Avatar regeneration failed.");
    } finally {
      setIsRegeneratingAvatar(false);
    }
  };

  useEffect(() => {
    resolveAvatarPreview(overlaySettings.avatar_key ?? "", setOverlayAvatarUrl);
  }, [overlaySettings.avatar_key]);

  useEffect(() => {
    resolveAvatarPreview(postCardSettings.avatar_key ?? "", setPostAvatarUrl);
  }, [postCardSettings.avatar_key]);

  useEffect(() => {
    return () => {
      stopBgmPreview();
    };
  }, []);

  const getBasePromptForScene = (scene: Scene) => {
    if (scene.speaker === "A") return basePromptA.trim();
    return basePromptA.trim();
  };

  const getBaseSettingsForSpeaker = (speaker: Scene["speaker"]) => {
    return {
      steps: baseStepsA,
      cfg: baseCfgScaleA,
      sampler: baseSamplerA,
      seed: baseSeedA,
      clipSkip: baseClipSkipA,
    };
  };

  const buildPositivePrompt = (scene: Scene) => {
    const base = getBasePromptForScene(scene);
    const scenePrompt = scene.image_prompt.trim();
    if (!autoComposePrompt || !base) return scenePrompt;
    if (!scenePrompt) return base;
    const sceneKeywords = [
      "sitting",
      "standing",
      "walking",
      "running",
      "jumping",
      "kneeling",
      "crouching",
      "lying",
      "from above",
      "top-down",
      "low angle",
      "high angle",
      "close-up",
      "wide shot",
      "full body",
      "library",
      "cafe",
      "street",
      "room",
      "bedroom",
      "office",
      "classroom",
      "park",
      "forest",
      "beach",
      "city",
      "night",
      "sunset",
      "sunrise",
      "rain",
      "snow",
      "background",
      "lighting",
      "indoors",
      "outdoors",
    ];
    const splitTokens = (text: string) =>
      text
        .split(",")
        .map((token) => token.trim())
        .filter(Boolean);
    const baseTokens = splitTokens(base).filter((token) => {
      const lower = token.toLowerCase();
      return !sceneKeywords.some((keyword) => lower.includes(keyword));
    });
    const sceneTokens = splitTokens(scenePrompt);
    const merged: string[] = [];
    const seen = new Set<string>();
    const loraSeen = new Set<string>();
    const modelSeen = new Set<string>();
    const pushToken = (token: string) => {
      const lower = token.toLowerCase();
      if (lower.startsWith("<lora:")) {
        if (loraSeen.has(lower)) return;
        loraSeen.add(lower);
      }
      if (lower.startsWith("<model:")) {
        if (modelSeen.has(lower)) return;
        modelSeen.add(lower);
      }
      if (seen.has(lower)) return;
      seen.add(lower);
      merged.push(token);
    };
    baseTokens.forEach(pushToken);
    sceneTokens.forEach(pushToken);
    return merged.join(", ");
  };

  const buildNegativePrompt = (scene: Scene) => {
    const base = getBaseNegativeForScene();
    const sceneNeg = scene.negative_prompt.trim();
    if (!autoComposePrompt) return sceneNeg;
    const combined = base && sceneNeg ? `${base}, ${sceneNeg}` : base || sceneNeg;
    const tokens = combined
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean);
    const seen = new Set<string>();
    const merged: string[] = [];
    for (const token of tokens) {
      const lower = token.toLowerCase();
      if (seen.has(lower)) continue;
      seen.add(lower);
      merged.push(token);
    }
    return merged.join(", ");
  };

  const resolveSteps = (scene: Scene) => scene.steps;
  const resolveCfgScale = (scene: Scene) => scene.cfg_scale;
  const resolveSampler = (scene: Scene) => scene.sampler_name;
  const resolveSeed = (scene: Scene) => scene.seed;
  const resolveClipSkip = (scene: Scene) => scene.clip_skip;

  const handleSpeakerChange = (scene: Scene, speaker: Scene["speaker"]) => {
    const baseSettings = getBaseSettingsForSpeaker(speaker);
    updateScene(scene.id, {
      speaker,
      steps: baseSettings.steps,
      cfg_scale: baseSettings.cfg,
      sampler_name: baseSettings.sampler,
      seed: baseSettings.seed,
      clip_skip: baseSettings.clipSkip,
      negative_prompt: baseNegativePromptA,
    });
  };

  const buildScenePrompt = async (scene: Scene) => {
    const fallbackPrompt = buildPositivePrompt(scene);
    if (!fallbackPrompt) return null;
    let prompt = fallbackPrompt;
    const basePrompt = getBasePromptForScene(scene);
    const scenePrompt = scene.image_prompt;
    if (autoComposePrompt && autoRewritePrompt && basePrompt && scenePrompt.trim()) {
      try {
        const rewrite = await axios.post(`${API_BASE}/prompt/rewrite`, {
          base_prompt: basePrompt,
          scene_prompt: scenePrompt,
          style,
          mode: "compose",
        });
        if (rewrite.data.prompt) {
          prompt = rewrite.data.prompt;
        }
      } catch {
        prompt = `${basePrompt}, ${scenePrompt}`;
      }
    } else {
      prompt = autoComposePrompt && basePrompt ? `${basePrompt}, ${scenePrompt}` : scenePrompt;
    }
    return prompt;
  };

  const buildHiResPayload = () =>
    hiResEnabled
      ? {
          enable_hr: true,
          hr_scale: 1.5,
          hr_upscaler: "Latent",
          hr_second_pass_steps: 10,
          denoising_strength: 0.25,
        }
      : {};

  const storeSceneImage = async (dataUrl: string) => {
    if (!dataUrl || !dataUrl.startsWith("data:")) return dataUrl;
    try {
      const res = await fetch(`${API_BASE}/image/store`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_b64: dataUrl }),
      });
      if (!res.ok) return dataUrl;
      const data = await res.json();
      if (data?.url) return data.url as string;
      return dataUrl;
    } catch (error) {
      console.error(error);
      return dataUrl;
    }
  };

  const generateSceneImageFor = async (scene: Scene, silent = false) => {
    const prompt = await buildScenePrompt(scene);
    if (!prompt) {
      if (!silent) alert("Prompt is required");
      return null;
    }
    const hiResPayload = buildHiResPayload();
    const debugPayload = {
      prompt,
      negative_prompt: buildNegativePrompt(scene),
      steps: resolveSteps(scene),
      cfg_scale: resolveCfgScale(scene),
      sampler_name: resolveSampler(scene),
      seed: resolveSeed(scene),
      clip_skip: resolveClipSkip(scene),
      width: 512,
      height: 512,
      ...hiResPayload,
    };
    try {
      const res = await axios.post(`${API_BASE}/scene/generate`, {
        prompt,
        negative_prompt: buildNegativePrompt(scene),
        steps: resolveSteps(scene),
        cfg_scale: resolveCfgScale(scene),
        sampler_name: resolveSampler(scene),
        seed: resolveSeed(scene),
        clip_skip: resolveClipSkip(scene),
        width: 512,
        height: 512,
        ...hiResPayload,
      });
      if (res.data.image) {
        const dataUrl = `data:image/png;base64,${res.data.image}`;
        const storedUrl = await storeSceneImage(dataUrl);
        return {
          image_url: storedUrl,
          debug_prompt: prompt,
          debug_payload: JSON.stringify(debugPayload, null, 2),
        } as Partial<Scene>;
      }
      return {
        debug_prompt: prompt,
        debug_payload: JSON.stringify(debugPayload, null, 2),
      } as Partial<Scene>;
    } catch {
      if (!silent) alert("Scene image generation failed");
      return null;
    }
  };

  const validateImageCandidate = async (imageUrl: string, prompt: string) => {
    try {
      const res = await axios.post(`${API_BASE}/scene/validate_image`, {
        image_b64: imageUrl,
        prompt,
        mode: imageCheckMode,
      });
      return res.data;
    } catch {
      return null;
    }
  };

  const generateSceneCandidates = async (scene: Scene, silent = false) => {
    const prompt = await buildScenePrompt(scene);
    if (!prompt) {
      if (!silent) alert("Prompt is required");
      return null;
    }
    const candidates: Array<{ image_url: string; match_rate?: number }> = [];
    for (let i = 0; i < 3; i += 1) {
      const result = await generateSceneImageFor(scene, true);
      if (!result?.image_url) continue;
      const validation = await validateImageCandidate(result.image_url, prompt);
      candidates.push({
        image_url: result.image_url,
        match_rate: typeof validation?.match_rate === "number" ? validation.match_rate : 0,
      });
    }
    if (!candidates.length) return null;
    const best = [...candidates].sort((a, b) => (b.match_rate ?? 0) - (a.match_rate ?? 0))[0];
    if (best?.image_url) {
      const validation = await validateImageCandidate(best.image_url, prompt);
      if (validation) {
        setImageValidationResults((prev) => ({ ...prev, [scene.id]: validation }));
      }
    }
    return { image_url: best.image_url, candidates, debug_prompt: prompt } as Partial<Scene>;
  };

  const handleGenerateSceneImage = async (scene: Scene) => {
    updateScene(scene.id, { isGenerating: true });
    try {
      const result = multiGenEnabled
        ? await generateSceneCandidates(scene)
        : await generateSceneImageFor(scene);
      if (result) updateScene(scene.id, result);
    } finally {
      updateScene(scene.id, { isGenerating: false });
    }
  };

  const handleSuggestSplit = async () => {
    if (!examplePrompt.trim()) return;
    setIsSuggesting(true);
    try {
      const res = await axios.post(`${API_BASE}/prompt/split`, {
        example_prompt: examplePrompt,
        style,
      });
      setSuggestedBase(res.data.base_prompt || "");
      setSuggestedScene(res.data.scene_prompt || "");
    } catch {
      alert("Prompt split failed");
    } finally {
      setIsSuggesting(false);
    }
  };

  const copyText = async (value: string) => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopyStatus("Copied");
      setTimeout(() => setCopyStatus(""), 1200);
    } catch {
      setCopyStatus("Copy failed");
      setTimeout(() => setCopyStatus(""), 1200);
    }
  };

  const computeValidationResults = (inputScenes: Scene[] = scenes) => {
    const hasAny = (text: string, list: string[]) => list.some((keyword) => text.includes(keyword));

    const results: Record<number, SceneValidation> = {};
    let ok = 0;
    let warn = 0;
    let error = 0;

    inputScenes.forEach((scene) => {
      const issues: ValidationIssue[] = [];
      const script = scene.script.trim();
      const prompt = scene.image_prompt.toLowerCase();
      const negative = scene.negative_prompt.toLowerCase();

      if (!script) {
        issues.push({ level: "error", message: "Script is empty." });
      } else if (script.length > 40) {
        issues.push({ level: "warn", message: "Script is longer than 40 characters." });
      }

      if (scene.speaker !== "A") {
        issues.push({ level: "error", message: "Speaker must be Actor A (monologue)." });
      }

      if (!scene.image_prompt.trim()) {
        issues.push({ level: "error", message: "Positive Prompt is empty." });
      } else {
        const tokenCount = scene.image_prompt.split(",").filter(Boolean).length;
        if (tokenCount < 5) {
          issues.push({ level: "warn", message: "Prompt is too short; add more visual details." });
        }
        if (!hasAny(prompt, CAMERA_KEYWORDS)) {
          issues.push({ level: "warn", message: "Missing camera/shot keywords." });
        }
        if (!hasAny(prompt, ACTION_KEYWORDS)) {
          issues.push({ level: "warn", message: "Missing action/pose keywords." });
        }
        if (!hasAny(prompt, BACKGROUND_KEYWORDS)) {
          issues.push({ level: "warn", message: "Missing background/setting keywords." });
        }
        if (!hasAny(prompt, LIGHTING_KEYWORDS)) {
          issues.push({ level: "warn", message: "Missing lighting/mood keywords." });
        }
      }

      const forbidden = CAMERA_KEYWORDS.concat(ACTION_KEYWORDS, BACKGROUND_KEYWORDS);
      if (negative && forbidden.some((keyword) => negative.includes(keyword))) {
        issues.push({ level: "warn", message: "Negative Prompt contains scene keywords." });
      }

      const status = issues.some((item) => item.level === "error")
        ? "error"
        : issues.length
          ? "warn"
          : "ok";

      results[scene.id] = { status, issues };
      if (status === "ok") ok += 1;
      if (status === "warn") warn += 1;
      if (status === "error") error += 1;
    });

    return { results, summary: { ok, warn, error } };
  };

  const runValidation = () => {
    const { results, summary } = computeValidationResults();
    setValidationResults(results);
    setValidationSummary(summary);
  };

  const applyAutoFixForScenes = (inputScenes: Scene[]) => {
    const { results, summary } = computeValidationResults(inputScenes);
    setValidationResults(results);
    setValidationSummary(summary);

    let updated = [...inputScenes];
    updated.forEach((scene) => {
      const validation = results[scene.id];
      if (!validation || validation.status === "ok") return;
      const suggestions = getFixSuggestions(scene, validation);
      suggestions
        .filter((item) => item.action)
        .forEach((item) => {
          if (!item.action) return;
          if (item.action.type === "set_speaker_a") {
            const baseSettings = getBaseSettingsForSpeaker("A");
            updated = updated.map((target) =>
              target.id === scene.id
                ? {
                    ...target,
                    speaker: "A",
                    steps: baseSettings.steps,
                    cfg_scale: baseSettings.cfg,
                    sampler_name: baseSettings.sampler,
                    seed: baseSettings.seed,
                    clip_skip: baseSettings.clipSkip,
                    negative_prompt: baseNegativePromptA,
                  }
                : target
            );
            return;
          }
          if (item.action.type === "add_positive") {
            const tokens = item.action.tokens ?? [];
            if (tokens.length === 0) return;
            updated = updated.map((target) => {
              if (target.id !== scene.id) return target;
              const existing = target.image_prompt
                .split(",")
                .map((token) => token.trim())
                .filter(Boolean);
              const existingSet = new Set(existing.map((token) => token.toLowerCase()));
              const nextTokens = [...existing];
              tokens.forEach((token) => {
                if (!existingSet.has(token.toLowerCase())) {
                  nextTokens.push(token);
                }
              });
              return { ...target, image_prompt: nextTokens.join(", ") };
            });
            return;
          }
          if (item.action.type === "fill_script") {
            const value = item.action.value?.trim() || "";
            if (!value) return;
            updated = updated.map((target) =>
              target.id === scene.id ? { ...target, script: value } : target
            );
            return;
          }
          if (item.action.type === "trim_script") {
            const value = item.action.value?.trim() || "";
            if (!value) return;
            updated = updated.map((target) =>
              target.id === scene.id ? { ...target, script: value } : target
            );
            return;
          }
          if (item.action.type === "remove_negative_scene") {
            const keywords = CAMERA_KEYWORDS.concat(ACTION_KEYWORDS, BACKGROUND_KEYWORDS);
            updated = updated.map((target) => {
              if (target.id !== scene.id) return target;
              const filtered = target.negative_prompt
                .split(",")
                .map((token) => token.trim())
                .filter(Boolean)
                .filter((token) => {
                  const lower = token.toLowerCase();
                  return !keywords.some((keyword) => lower.includes(keyword));
                });
              return { ...target, negative_prompt: filtered.join(", ") };
            });
          }
        });
    });
    return updated;
  };

  const handleAutoFixAll = () => {
    const updated = applyAutoFixForScenes(scenes);
    setScenes(updated);
    setTimeout(() => runValidation(), 0);
  };

  const getFixSuggestions = (scene: Scene, validation?: SceneValidation): FixSuggestion[] => {
    if (!validation) return [];
    const suggestions: FixSuggestion[] = [];
    const issueText = validation.issues.map((issue) => issue.message);
    const includes = (needle: string) => issueText.some((text) => text.includes(needle));
    const scriptFallback = (
      scene.image_prompt_ko ||
      scene.image_prompt ||
      topic.trim() ||
      "오늘의 장면"
    ).slice(0, 40);

    if (includes("Script is empty")) {
      suggestions.push({
        id: "script-empty",
        message: "Add one short line of dialogue (monologue).",
        action: { type: "fill_script", value: scriptFallback },
      });
    }
    if (includes("Script is longer than 40 characters")) {
      suggestions.push({
        id: "script-long",
        message: "Shorten the script to 40 characters or fewer.",
        action: { type: "trim_script", value: scene.script.slice(0, 40) },
      });
    }
    if (includes("Speaker must be Actor A")) {
      suggestions.push({
        id: "speaker-a",
        message: "Change Speaker to Actor A for monologue mode.",
        action: { type: "set_speaker_a" },
      });
    }
    if (includes("Positive Prompt is empty")) {
      suggestions.push({
        id: "prompt-empty",
        message: "Add a Positive Prompt with subject + action + background.",
        action: {
          type: "add_positive",
          tokens: ["full body", "standing", "plain background", "soft light"],
        },
      });
    }
    if (includes("Prompt is too short")) {
      suggestions.push({
        id: "prompt-short",
        message: "Add 3-5 more visual tokens (pose, setting, lighting).",
        action: {
          type: "add_positive",
          tokens: ["full body", "standing", "plain background", "soft light", "neutral pose"],
        },
      });
    }
    if (includes("Missing camera/shot keywords")) {
      suggestions.push({
        id: "missing-camera",
        message: "Add camera keywords like: full body, wide shot, close-up, low angle.",
        action: { type: "add_positive", tokens: ["full body"] },
      });
    }
    if (includes("Missing action/pose keywords")) {
      suggestions.push({
        id: "missing-action",
        message: "Add action keywords like: standing, walking, running, holding.",
        action: { type: "add_positive", tokens: ["standing"] },
      });
    }
    if (includes("Missing background/setting keywords")) {
      suggestions.push({
        id: "missing-background",
        message: "Add background keywords like: library, room, street, cafe.",
        action: { type: "add_positive", tokens: ["library", "room", "street", "cafe"] },
      });
    }
    if (includes("Missing lighting/mood keywords")) {
      suggestions.push({
        id: "missing-lighting",
        message: "Add lighting keywords like: soft light, sunset, neon, moody.",
        action: { type: "add_positive", tokens: ["soft light"] },
      });
    }
    if (includes("Negative Prompt contains scene keywords")) {
      suggestions.push({
        id: "negative-scene-keywords",
        message: "Remove scene/location words from Negative Prompt.",
        action: { type: "remove_negative_scene" },
      });
    }

    if (suggestions.length === 0) return [];
    return suggestions;
  };

  const applySuggestion = (scene: Scene, suggestion: FixSuggestion) => {
    if (!suggestion.action) return;
    if (suggestion.action.type === "set_speaker_a") {
      handleSpeakerChange(scene, "A");
      return;
    }

    const splitTokens = (text: string) =>
      text
        .split(",")
        .map((token) => token.trim())
        .filter(Boolean);

    if (suggestion.action.type === "add_positive") {
      const tokens = suggestion.action.tokens ?? [];
      if (tokens.length === 0) return;
      const existing = splitTokens(scene.image_prompt);
      const existingSet = new Set(existing.map((token) => token.toLowerCase()));
      const nextTokens = [...existing];
      if (suggestion.id === "missing-background") {
        const candidate = tokens.find((token) => !existingSet.has(token.toLowerCase()));
        if (candidate) {
          nextTokens.push(candidate);
        }
      } else {
        tokens.forEach((token) => {
          if (!existingSet.has(token.toLowerCase())) {
            nextTokens.push(token);
          }
        });
      }
      updateScene(scene.id, { image_prompt: nextTokens.join(", ") });
      return;
    }

    if (suggestion.action.type === "remove_negative_scene") {
      const keywords = CAMERA_KEYWORDS.concat(ACTION_KEYWORDS, BACKGROUND_KEYWORDS);
      const filtered = splitTokens(scene.negative_prompt).filter((token) => {
        const lower = token.toLowerCase();
        return !keywords.some((keyword) => lower.includes(keyword));
      });
      updateScene(scene.id, { negative_prompt: filtered.join(", ") });
    }
  };

  const applyMissingImageTags = (scene: Scene, missingOverride?: string[], limit = 5) => {
    const missing = missingOverride ?? imageValidationResults[scene.id]?.missing ?? [];
    if (missing.length === 0) return;
    const splitTokens = (text: string) =>
      text
        .split(",")
        .map((token) => token.trim())
        .filter(Boolean);
    const existing = splitTokens(scene.image_prompt);
    const existingSet = new Set(existing.map((token) => token.toLowerCase()));
    const nextTokens = [...existing];
    missing.slice(0, limit).forEach((token) => {
      if (!existingSet.has(token.toLowerCase())) {
        nextTokens.push(token);
      }
    });
    updateScene(scene.id, { image_prompt: nextTokens.join(", ") });
  };

  const getSceneStatus = (scene: Scene) => {
    if (!scene.image_url) return "Need Image";
    if (!imageValidationResults[scene.id]) return "Ready to Validate";
    return "Ready to Render";
  };

  const handleValidateImage = async (scene: Scene) => {
    if (!scene.image_url) {
      showToast("이미지를 먼저 업로드하세요.", "error");
      return;
    }
    setValidatingSceneId(scene.id);
    const prompt = scene.debug_prompt || buildPositivePrompt(scene);
    try {
      const res = await axios.post(`${API_BASE}/scene/validate_image`, {
        image_b64: scene.image_url,
        prompt,
        mode: imageCheckMode,
      });
      setImageValidationResults((prev) => ({ ...prev, [scene.id]: res.data }));
      const matchRate = Math.round((res.data.match_rate || 0) * 100);
      if (matchRate >= 80) {
        showToast(`검증 완료! Match ${matchRate}%`, "success");
      } else {
        showToast(`Match ${matchRate}% - Missing 태그 확인 필요`, "error");
      }
    } catch {
      showToast("이미지 검증 실패", "error");
    } finally {
      setValidatingSceneId(null);
    }
  };

  const validateSceneImage = async (scene: Scene, silent = false) => {
    if (!scene.image_url) {
      if (!silent) alert("Upload or generate an image first.");
      return null;
    }
    const prompt = scene.debug_prompt || buildPositivePrompt(scene);
    try {
      const res = await axios.post(`${API_BASE}/scene/validate_image`, {
        image_b64: scene.image_url,
        prompt,
        mode: imageCheckMode,
      });
      setImageValidationResults((prev) => ({ ...prev, [scene.id]: res.data }));
      if (Array.isArray(res.data?.missing) && res.data.missing.length > 0) {
        applyMissingImageTags(scene, res.data.missing);
      }
      return res.data;
    } catch {
      if (!silent) alert("Image validation failed");
      return null;
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff3db,_#f7f1ff_45%,_#e6f7ff_100%)] text-zinc-900">
      <div className="relative overflow-hidden">
        <div className="absolute -top-40 -right-32 h-80 w-80 rounded-full bg-gradient-to-br from-amber-200 via-rose-200 to-fuchsia-200 opacity-70 blur-3xl" />
        <div className="absolute top-40 -left-32 h-72 w-72 rounded-full bg-gradient-to-br from-sky-200 via-emerald-200 to-lime-200 opacity-60 blur-3xl" />

        {/* ============ SETUP MODE ============ */}
        {viewMode === "setup" && (
          <main className="relative mx-auto flex w-full max-w-2xl flex-col gap-8 px-6 py-16">
            <header className="flex flex-col items-center gap-2 text-center">
              <p className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Shorts Producer</p>
              <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">
                새 영상 만들기
              </h1>
            </header>

            <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/80 p-8 shadow-xl shadow-slate-200/40 backdrop-blur">
              {/* Topic */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Topic
                </label>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  rows={3}
                  className="rounded-2xl border border-zinc-200 bg-white p-4 text-sm shadow-inner outline-none focus:border-zinc-400"
                  placeholder="예: 혼자 사는 직장인의 하루 루틴, 고양이와 함께하는 일상..."
                />
              </div>

              {/* Quick Settings */}
              <div className="grid gap-4">
                <label className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Output Settings
                </label>

                {/* Layout Selection */}
                <div className="flex justify-center gap-4">
                  <button
                    type="button"
                    onClick={() => setLayoutStyle("full")}
                    className={`flex flex-col items-center gap-2 rounded-2xl border-2 p-4 transition ${
                      layoutStyle === "full"
                        ? "border-zinc-900 bg-zinc-900/5 shadow-md"
                        : "border-zinc-200 bg-white hover:border-zinc-400"
                    }`}
                  >
                    <div
                      className={`flex h-16 w-9 flex-col items-center justify-center rounded-lg border-2 ${
                        layoutStyle === "full" ? "border-zinc-700 bg-zinc-200" : "border-zinc-300 bg-zinc-100"
                      }`}
                    >
                      <div className={`h-4 w-4 rounded ${layoutStyle === "full" ? "bg-zinc-500" : "bg-zinc-300"}`} />
                    </div>
                    <div className="text-center">
                      <p className={`text-xs font-semibold ${layoutStyle === "full" ? "text-zinc-900" : "text-zinc-600"}`}>Full</p>
                      <p className={`text-[10px] ${layoutStyle === "full" ? "text-zinc-600" : "text-zinc-400"}`}>9:16</p>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setLayoutStyle("post")}
                    className={`flex flex-col items-center gap-2 rounded-2xl border-2 p-4 transition ${
                      layoutStyle === "post"
                        ? "border-zinc-900 bg-zinc-900/5 shadow-md"
                        : "border-zinc-200 bg-white hover:border-zinc-400"
                    }`}
                  >
                    <div
                      className={`flex h-11 w-11 flex-col items-center justify-center rounded-lg border-2 ${
                        layoutStyle === "post" ? "border-zinc-700 bg-zinc-200" : "border-zinc-300 bg-zinc-100"
                      }`}
                    >
                      <div className={`h-4 w-4 rounded ${layoutStyle === "post" ? "bg-zinc-500" : "bg-zinc-300"}`} />
                    </div>
                    <div className="text-center">
                      <p className={`text-xs font-semibold ${layoutStyle === "post" ? "text-zinc-900" : "text-zinc-600"}`}>Post</p>
                      <p className={`text-[10px] ${layoutStyle === "post" ? "text-zinc-600" : "text-zinc-400"}`}>1:1</p>
                    </div>
                  </button>
                </div>

                {/* Voice, BGM, Speed */}
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Voice</label>
                    <select
                      value={narratorVoice}
                      onChange={(e) => setNarratorVoice(e.target.value)}
                      className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    >
                      {VOICES.map((voice) => (
                        <option key={voice.id} value={voice.id}>{voice.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">BGM</label>
                    <select
                      value={bgmFile ?? ""}
                      onChange={(e) => setBgmFile(e.target.value || null)}
                      className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    >
                      <option value="">None</option>
                      {bgmList.map((bgm) => (
                        <option key={bgm.name} value={bgm.name}>{bgm.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Speed ({speedMultiplier.toFixed(1)}x)
                    </label>
                    <input
                      type="range"
                      min={0.8}
                      max={1.5}
                      step={0.1}
                      value={speedMultiplier}
                      onChange={(e) => setSpeedMultiplier(Number(e.target.value))}
                      className="mt-1 w-full accent-zinc-900"
                    />
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setViewMode("working");
                    handleAutoRun();
                  }}
                  disabled={!topic.trim()}
                  className="w-full rounded-full bg-gradient-to-r from-zinc-800 to-zinc-900 py-4 text-base font-semibold text-white shadow-lg transition hover:from-zinc-700 hover:to-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  ✨ Auto Run
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("working")}
                  className="w-full rounded-full border border-zinc-300 bg-white py-3 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
                >
                  Manual Mode →
                </button>
              </div>
            </section>

            <footer className="flex justify-center">
              <Link
                href="/manage"
                className="text-xs text-zinc-500 underline underline-offset-2 hover:text-zinc-700"
              >
                Manage Keywords & Assets
              </Link>
            </footer>
          </main>
        )}

        {/* ============ WORKING MODE ============ */}
        {viewMode === "working" && (
        <main
          className={`relative mx-auto flex w-full max-w-6xl flex-col gap-10 px-6 py-12 ${
            isAutoRunning ? "pointer-events-none opacity-60" : ""
          }`}
        >
          <header className="flex flex-col gap-4">
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => setViewMode("setup")}
                className="rounded-full border border-zinc-300 bg-white/80 px-3 py-1.5 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition hover:bg-zinc-50"
              >
                ← Back
              </button>
              <p className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Shorts MVP</p>
            </div>
            <h1 className="text-4xl font-semibold tracking-tight text-zinc-900">
              Script-first storyboard studio
            </h1>
            <p className="max-w-2xl text-sm text-zinc-600">
              Start from a script, generate scene descriptions, then upload the exact images you
              want. The system only assembles and renders.
            </p>
            <Link
              href="/manage"
              className="w-fit rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm"
            >
              Manage
            </Link>
          </header>

          <div className="flex items-center gap-3">
            <span className="text-[10px] font-semibold tracking-[0.3em] text-zinc-500 uppercase">
              Plan & Generate
            </span>
            <div className="h-px flex-1 bg-zinc-200/70" />
          </div>

          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Storyboard Generator</h2>
                <p className="text-xs text-zinc-500">
                  Generate scene scripts and visual descriptions.
                </p>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-[1.5fr_1fr]">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Topic
                </label>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  rows={4}
                  className="rounded-2xl border border-zinc-200 bg-white/80 p-4 text-sm shadow-inner outline-none focus:border-zinc-400"
                  placeholder="예: 혼자 사는 직장인의 하루 루틴, 고양이와 함께하는 일상..."
                />
              </div>
              <div className="grid gap-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Duration <span className="text-zinc-400">(10-120s)</span>
                    </label>
                    <input
                      type="number"
                      min={10}
                      max={120}
                      value={duration}
                      onChange={(e) => setDuration(Number(e.target.value))}
                      className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Language
                    </label>
                    <input
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    />
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Visual Style
                  </label>
                  <input
                    value={style}
                    onChange={(e) => setStyle(e.target.value)}
                    className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Structure
                  </label>
                  <select
                    value={structure}
                    onChange={(e) => setStructure(e.target.value)}
                    className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  >
                    {STRUCTURES.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </section>

          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Prompt Setup</h2>
                <p className="text-xs text-zinc-500">Define global prompt rules and actor setup.</p>
                <p className="text-[10px] text-zinc-400">
                  Tip: Base Prompt is identity/style. Scene prompts handle action, camera, and
                  background.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { id: "global", label: "Global" },
                { id: "A", label: "Actor A" },
              ].map((tab) => {
                const active = baseTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setBaseTab(tab.id as "global" | "A")}
                    className={`rounded-full px-4 py-2 text-[10px] font-semibold tracking-[0.2em] uppercase transition ${
                      active ? "bg-zinc-900 text-white" : "bg-white/80 text-zinc-600"
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {baseTab === "global" && (
              <div className="grid gap-3">
                <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                  Auto Compose Prompt
                  <input
                    type="checkbox"
                    checked={autoComposePrompt}
                    onChange={(e) => setAutoComposePrompt(e.target.checked)}
                    className="h-4 w-4 accent-zinc-900"
                  />
                </label>
                <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                  Auto Rewrite Prompt (Gemini)
                  <input
                    type="checkbox"
                    checked={autoRewritePrompt}
                    onChange={(e) => setAutoRewritePrompt(e.target.checked)}
                    className="h-4 w-4 accent-zinc-900"
                  />
                </label>
                <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                  Hi-Res Fix (1.5x)
                  <input
                    type="checkbox"
                    checked={hiResEnabled}
                    onChange={(e) => setHiResEnabled(e.target.checked)}
                    className="h-4 w-4 accent-zinc-900"
                  />
                </label>
                <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                  VEO Clip
                  <input
                    type="checkbox"
                    checked={veoEnabled}
                    onChange={(e) => setVeoEnabled(e.target.checked)}
                    className="h-4 w-4 accent-zinc-900"
                  />
                </label>
                {!veoEnabled && (
                  <p className="text-[10px] text-zinc-400">
                    VEO is off. Autopilot will skip motion clip generation.
                  </p>
                )}
              </div>
            )}

            {baseTab === "A" && (
              <div className="grid gap-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Actor A Setup
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={selectedSampleId}
                      onChange={(e) => setSelectedSampleId(e.target.value)}
                      className="rounded-full border border-zinc-200 bg-white/80 px-3 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                    >
                      {PROMPT_SAMPLES.map((sample) => (
                        <option key={sample.id} value={sample.id}>
                          {sample.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() =>
                        (() => {
                          const sample = PROMPT_SAMPLES.find(
                            (item) => item.id === selectedSampleId
                          );
                          if (!sample) return;
                          setBasePromptA(sample.basePrompt);
                          setBaseNegativePromptA(sample.baseNegative);
                        })()
                      }
                      className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                    >
                      Insert Sample
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsHelperOpen(true)}
                      className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                    >
                      Prompt Helper
                    </button>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Actor A Gender
                  </label>
                  <select
                    value={actorAGender}
                    onChange={(e) => setActorAGender(e.target.value as ActorGender)}
                    className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  >
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                  </select>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Base Prompt (Actor A)
                  </label>
                  <textarea
                    value={basePromptA}
                    onChange={(e) => setBasePromptA(e.target.value)}
                    rows={2}
                    className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
                    placeholder="1girl, eureka, (black t-shirt:1.2), ... <lora:...:1.0>"
                  />
                  <p className="text-[10px] text-zinc-500">
                    Model tags like &lt;model:...&gt; are ignored. Use the SD Model selector
                    instead.
                  </p>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Base Negative (Actor A)
                  </label>
                  <textarea
                    value={baseNegativePromptA}
                    onChange={(e) => setBaseNegativePromptA(e.target.value)}
                    rows={2}
                    className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
                    placeholder="verybadimagenegative_v1.3"
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-5">
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Base Steps (Actor A)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={80}
                      value={baseStepsA}
                      onChange={(e) => setBaseStepsA(Number(e.target.value))}
                      className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Base CFG (Actor A)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      step={0.5}
                      value={baseCfgScaleA}
                      onChange={(e) => setBaseCfgScaleA(Number(e.target.value))}
                      className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Base Sampler (Actor A)
                    </label>
                    <select
                      value={baseSamplerA}
                      onChange={(e) => setBaseSamplerA(e.target.value)}
                      className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    >
                      {SAMPLERS.map((sampler) => (
                        <option key={sampler} value={sampler}>
                          {sampler}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Base Seed (Actor A)
                    </label>
                    <input
                      type="number"
                      value={baseSeedA}
                      onChange={(e) => setBaseSeedA(Number(e.target.value))}
                      className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Base Clip Skip (Actor A)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={baseClipSkipA}
                      onChange={(e) => setBaseClipSkipA(Number(e.target.value))}
                      className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    />
                  </div>
                </div>
              </div>
            )}
          </section>

          <div className="flex flex-wrap items-center justify-end gap-3">
            <button
              onClick={resetScenesOnly}
              disabled={isAutoRunning}
              className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-lg shadow-zinc-200/40 transition disabled:cursor-not-allowed disabled:bg-zinc-100 disabled:text-zinc-400"
            >
              Reset Scenes
            </button>
            <button
              onClick={resetDraft}
              disabled={isAutoRunning}
              className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-lg shadow-zinc-200/40 transition disabled:cursor-not-allowed disabled:bg-zinc-100 disabled:text-zinc-400"
            >
              Reset Draft
            </button>
            <button
              onClick={handleGenerateScenes}
              disabled={isGenerating || !topic.trim() || isAutoRunning}
              className="rounded-full border border-zinc-300 bg-white/80 px-6 py-2 text-xs font-semibold tracking-[0.2em] text-zinc-700 uppercase shadow-lg shadow-zinc-200/40 transition hover:bg-white hover:border-zinc-400 disabled:cursor-not-allowed disabled:bg-zinc-100 disabled:text-zinc-400"
            >
              {isGenerating ? "Generating..." : "Generate"}
            </button>
            <button
              onClick={handleAutoRun}
              disabled={isGenerating || isRendering || isAutoRunning || !topic.trim()}
              className="rounded-full bg-zinc-900 px-6 py-2 text-xs font-semibold tracking-[0.2em] text-white uppercase shadow-lg shadow-zinc-900/20 transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {isAutoRunning
                ? `${AUTO_RUN_STEPS.find((s) => s.id === autoRunState.step)?.label || "Running"}...`
                : "Auto Run"}
            </button>
          </div>
          {autoRunState.status !== "idle" && (
            <div className="grid gap-3 rounded-2xl border border-zinc-200 bg-white/80 p-4 text-xs text-zinc-600">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Autopilot Status
                </span>
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  {autoRunState.status}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {AUTO_RUN_STEPS.map((step) => {
                  const isActive = autoRunState.step === step.id;
                  const isDone =
                    autoRunState.status !== "idle" &&
                    AUTO_RUN_STEPS.findIndex((item) => item.id === step.id) <
                      AUTO_RUN_STEPS.findIndex((item) => item.id === autoRunState.step);
                  return (
                    <span
                      key={step.id}
                      className={`rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.2em] uppercase ${
                        isActive
                          ? "bg-zinc-900 text-white"
                          : isDone
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-zinc-100 text-zinc-500"
                      }`}
                    >
                      {step.label}
                    </span>
                  );
                })}
              </div>
              <p>{autoRunState.message}</p>
              {autoRunState.error && <p className="text-red-500">{autoRunState.error}</p>}
              {autoRunState.status === "error" && autoRunState.step !== "idle" && (
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleAutoRunResume}
                    className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                  >
                    Resume from Step
                  </button>
                  <button
                    type="button"
                    onClick={handleAutoRun}
                    className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                  >
                    Restart Autopilot
                  </button>
                </div>
              )}
              {autoRunLog.length > 0 && (
                <div className="grid gap-1 text-[11px] text-zinc-500">
                  {autoRunLog.map((entry, idx) => (
                    <span key={`${entry}-${idx}`}>• {entry}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center gap-3">
            <span className="text-[10px] font-semibold tracking-[0.3em] text-zinc-500 uppercase">
              Scene Work
            </span>
            <div className="h-px flex-1 bg-zinc-200/70" />
          </div>

          <section className="grid gap-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Scenes</h2>
                <p className="text-xs text-zinc-500">
                  Upload the exact images you want for each scene.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-2 rounded-full border border-zinc-200 bg-white/80 px-3 py-2">
                  <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Image Check
                  </span>
                  <select
                    value={imageCheckMode}
                    onChange={(e) => setImageCheckMode(e.target.value as "local" | "gemini")}
                    className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[10px] tracking-[0.2em] text-zinc-600 uppercase"
                  >
                    <option value="local">Local (WD14)</option>
                    <option value="gemini">Gemini (Cloud)</option>
                  </select>
                </div>
                <label className="flex items-center gap-2 rounded-full border border-zinc-200 bg-white/80 px-3 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  3x Candidates
                  <input
                    type="checkbox"
                    checked={multiGenEnabled}
                    onChange={(e) => setMultiGenEnabled(e.target.checked)}
                    className="h-4 w-4 accent-zinc-900"
                  />
                </label>
                <button
                  onClick={runValidation}
                  className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold tracking-[0.2em] text-white uppercase shadow"
                >
                  Validate
                </button>
                <button
                  onClick={handleAutoFixAll}
                  disabled={scenes.length === 0}
                  className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Auto Fix All
                </button>
                <button
                  onClick={handleAddScene}
                  className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow"
                >
                  Add Scene
                </button>
              </div>
            </div>

            {validationSummary.ok + validationSummary.warn + validationSummary.error > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-emerald-600 uppercase">
                  OK {validationSummary.ok}
                </span>
                <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-amber-600 uppercase">
                  Warn {validationSummary.warn}
                </span>
                <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-rose-600 uppercase">
                  Error {validationSummary.error}
                </span>
              </div>
            )}

            {/* Filmstrip Navigation */}
            {scenes.length > 0 && (
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setCurrentSceneIndex((prev) => Math.max(0, prev - 1))}
                  disabled={currentSceneIndex === 0}
                  className="flex h-8 w-8 items-center justify-center rounded-full border border-zinc-300 bg-white/80 text-zinc-600 disabled:opacity-40"
                >
                  ‹
                </button>
                <div className="flex flex-1 gap-2 overflow-x-auto py-2">
                  {scenes.map((s, idx) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setCurrentSceneIndex(idx)}
                      className={`relative flex-shrink-0 overflow-hidden rounded-xl border-2 transition ${
                        idx === currentSceneIndex
                          ? "border-zinc-900 shadow-md"
                          : "border-zinc-200 opacity-60 hover:opacity-100"
                      }`}
                      style={{ width: 64, height: 64 }}
                    >
                      {s.image_url ? (
                        <img
                          src={s.image_url}
                          alt={`Scene ${s.id}`}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-zinc-100 text-[10px] text-zinc-400">
                          {s.id}
                        </div>
                      )}
                      <span className="absolute bottom-0 left-0 right-0 bg-black/50 py-0.5 text-center text-[9px] text-white">
                        Scene {s.id}
                      </span>
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentSceneIndex((prev) => Math.min(scenes.length - 1, prev + 1))}
                  disabled={currentSceneIndex === scenes.length - 1}
                  className="flex h-8 w-8 items-center justify-center rounded-full border border-zinc-300 bg-white/80 text-zinc-600 disabled:opacity-40"
                >
                  ›
                </button>
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500">
                  {currentSceneIndex + 1} / {scenes.length}
                </span>
              </div>
            )}

            {/* Current Scene Card */}
            {scenes.length > 0 && (() => {
              const scene = scenes[currentSceneIndex];
              if (!scene) return null;
              return (
                <div
                  key={scene.id}
                  className="grid gap-4 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-zinc-800">Scene {scene.id}</h3>
                    {validationResults[scene.id] && (
                      <button
                        type="button"
                        onClick={() => {
                          const status = validationResults[scene.id].status;
                          if (status === "ok") return;
                          setSuggestionExpanded((prev) => ({
                            ...prev,
                            [scene.id]: !prev[scene.id],
                          }));
                        }}
                        className={`rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.2em] uppercase ${
                          validationResults[scene.id].status === "ok"
                            ? "bg-emerald-100 text-emerald-700"
                            : validationResults[scene.id].status === "warn"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {validationResults[scene.id].status}
                      </button>
                    )}
                    <button
                      onClick={() => {
                        if (window.confirm(`Scene ${scene.id}를 삭제하시겠습니까?`)) {
                          handleRemoveScene(scene.id);
                        }
                      }}
                      className="text-[10px] font-semibold tracking-[0.2em] text-rose-500 uppercase hover:text-rose-600"
                    >
                      Remove
                    </button>
                  </div>
                  <p className="text-[11px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
                    {getSceneStatus(scene)}
                  </p>
                  {validationResults[scene.id] && (
                    <p className="text-[11px] text-zinc-500">
                      {validationResults[scene.id].issues.length > 0
                        ? validationResults[scene.id].issues[0].message
                        : "No issues found."}
                    </p>
                  )}
                  {validationResults[scene.id] && validationResults[scene.id].status !== "ok" && (
                    <button
                      type="button"
                      onClick={() =>
                        setSuggestionExpanded((prev) => ({
                          ...prev,
                          [scene.id]: !prev[scene.id],
                        }))
                      }
                      className="w-fit rounded-full border border-zinc-300 bg-white/80 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                    >
                      Fix Suggestions
                    </button>
                  )}
                  {validationResults[scene.id] && suggestionExpanded[scene.id] && (
                    <div className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-xs text-zinc-600">
                      <div className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                        Fix Suggestions
                      </div>
                      {(() => {
                        const suggestions = getFixSuggestions(scene, validationResults[scene.id]);
                        const actionable = suggestions.filter((item) => item.action);
                        if (suggestions.length === 0) {
                          return (
                            <p className="mt-2 text-[11px] text-zinc-500">No auto suggestions.</p>
                          );
                        }
                        return (
                          <>
                            {actionable.length > 0 && (
                              <button
                                type="button"
                                onClick={() => {
                                  actionable.forEach((item) => applySuggestion(scene, item));
                                }}
                                className="mt-2 rounded-full border border-zinc-300 bg-white/80 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                              >
                                Apply All
                              </button>
                            )}
                            <ul className="mt-2 grid gap-2 text-[11px]">
                              {suggestions.map((item) => (
                                <li
                                  key={`${scene.id}-${item.id}`}
                                  className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white/70 px-3 py-2"
                                >
                                  <span className="text-zinc-600">{item.message}</span>
                                  {item.action ? (
                                    <button
                                      type="button"
                                      onClick={() => applySuggestion(scene, item)}
                                      className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                                    >
                                      Apply
                                    </button>
                                  ) : (
                                    <span className="text-[10px] tracking-[0.2em] text-zinc-400 uppercase">
                                      Manual
                                    </span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </>
                        );
                      })()}
                    </div>
                  )}

                  <div className="grid gap-4 md:grid-cols-[1.2fr_1fr]">
                    <div className="grid gap-3">
                      <div className="grid gap-2">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                          Script
                        </label>
                        <textarea
                          value={scene.script}
                          onChange={(e) => updateScene(scene.id, { script: e.target.value })}
                          rows={3}
                          className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="grid grid-cols-3 gap-3">
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            Speaker
                          </label>
                          <select
                            value={scene.speaker}
                            onChange={(e) =>
                              handleSpeakerChange(scene, e.target.value as Scene["speaker"])
                            }
                            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                          >
                            <option value="A">Actor A</option>
                          </select>
                        </div>
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            Duration
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={10}
                            value={scene.duration}
                            onChange={(e) =>
                              updateScene(scene.id, { duration: Number(e.target.value) })
                            }
                            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                          />
                        </div>
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            Image
                          </label>
                          <label className="flex h-10 cursor-pointer items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white/80 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                            Upload
                            <input
                              type="file"
                              accept="image/*"
                              className="hidden"
                              onChange={(e) => handleImageUpload(scene.id, e.target.files?.[0])}
                            />
                          </label>
                        </div>
                      </div>
                      <div className="grid gap-2">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                          Positive Prompt
                        </label>
                        <textarea
                          value={scene.image_prompt}
                          onChange={(e) => updateScene(scene.id, { image_prompt: e.target.value })}
                          rows={2}
                          className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="grid gap-2">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                          Negative Prompt
                        </label>
                        <textarea
                          value={scene.negative_prompt}
                          onChange={(e) =>
                            updateScene(scene.id, { negative_prompt: e.target.value })
                          }
                          rows={2}
                          className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="grid gap-2">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                          Prompt (KO)
                        </label>
                        <textarea
                          value={scene.image_prompt_ko}
                          onChange={(e) =>
                            updateScene(scene.id, { image_prompt_ko: e.target.value })
                          }
                          rows={2}
                          className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="grid gap-3 md:grid-cols-3">
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            Steps
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={80}
                            value={scene.steps}
                            onChange={(e) =>
                              updateScene(scene.id, { steps: Number(e.target.value) })
                            }
                            disabled={autoComposePrompt}
                            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                          />
                        </div>
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            CFG
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={20}
                            step={0.5}
                            value={scene.cfg_scale}
                            onChange={(e) =>
                              updateScene(scene.id, { cfg_scale: Number(e.target.value) })
                            }
                            disabled={autoComposePrompt}
                            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                          />
                        </div>
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            Sampler
                          </label>
                          <select
                            value={scene.sampler_name}
                            onChange={(e) =>
                              updateScene(scene.id, { sampler_name: e.target.value })
                            }
                            disabled={autoComposePrompt}
                            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                          >
                            {SAMPLERS.map((sampler) => (
                              <option key={sampler} value={sampler}>
                                {sampler}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            Seed
                          </label>
                          <input
                            type="number"
                            value={scene.seed}
                            onChange={(e) =>
                              updateScene(scene.id, { seed: Number(e.target.value) })
                            }
                            disabled={autoComposePrompt}
                            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                          />
                        </div>
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            Clip Skip
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={12}
                            value={scene.clip_skip}
                            onChange={(e) =>
                              updateScene(scene.id, { clip_skip: Number(e.target.value) })
                            }
                            disabled={autoComposePrompt}
                            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                          />
                        </div>
                      </div>
                      {/* Primary Action + More Menu */}
                      <div className="flex items-center justify-between">
                        <button
                          type="button"
                          onClick={() => handleGenerateSceneImage(scene)}
                          disabled={scene.isGenerating}
                          className="rounded-full bg-zinc-900 px-5 py-2.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
                        >
                          {scene.isGenerating ? "Generating..." : "Generate Image"}
                        </button>
                        <div className="relative">
                          <button
                            type="button"
                            onClick={() => setSceneMenuOpen(sceneMenuOpen === scene.id ? null : scene.id)}
                            className="rounded-full border border-zinc-200 bg-white p-2 text-zinc-500 transition hover:bg-zinc-50"
                          >
                            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                            </svg>
                          </button>
                          {sceneMenuOpen === scene.id && (
                            <div className="absolute right-0 z-10 mt-1 w-40 rounded-xl border border-zinc-200 bg-white py-1 shadow-lg">
                              <button
                                type="button"
                                onClick={() => {
                                  navigator.clipboard.writeText(buildPositivePrompt(scene));
                                  showToast("프롬프트 복사됨", "success");
                                  setSceneMenuOpen(null);
                                }}
                                className="w-full px-3 py-2 text-left text-xs text-zinc-700 hover:bg-zinc-50"
                              >
                                Copy Prompt
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  updateScene(scene.id, { seed: Math.floor(Math.random() * 999999999) });
                                  setSceneMenuOpen(null);
                                }}
                                className="w-full px-3 py-2 text-left text-xs text-zinc-700 hover:bg-zinc-50"
                              >
                                Randomize Seed
                              </button>
                              <hr className="my-1 border-zinc-100" />
                              <button
                                type="button"
                                onClick={() => {
                                  if (confirm("이 씬을 삭제하시겠습니까?")) {
                                    handleRemoveScene(scene.id);
                                  }
                                  setSceneMenuOpen(null);
                                }}
                                className="w-full px-3 py-2 text-left text-xs text-red-600 hover:bg-red-50"
                              >
                                Delete Scene
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Tab Navigation */}
                      <div className="flex gap-1 rounded-xl border border-zinc-200 bg-zinc-100 p-1">
                        {(["validate", "debug"] as const).map((tab) => (
                          <button
                            key={tab}
                            type="button"
                            onClick={() =>
                              setSceneTab((prev) => ({
                                ...prev,
                                [scene.id]: prev[scene.id] === tab ? null : tab,
                              }))
                            }
                            className={`flex-1 rounded-lg px-3 py-1.5 text-[10px] font-semibold uppercase transition ${
                              sceneTab[scene.id] === tab
                                ? "bg-white text-zinc-900 shadow-sm"
                                : "text-zinc-500 hover:text-zinc-700"
                            }`}
                          >
                            {tab === "validate" && (
                              <span className="flex items-center justify-center gap-1">
                                Validate
                                {imageValidationResults[scene.id] && (
                                  <span
                                    className={`h-1.5 w-1.5 rounded-full ${
                                      imageValidationResults[scene.id].match_rate >= 0.8
                                        ? "bg-emerald-500"
                                        : imageValidationResults[scene.id].match_rate >= 0.5
                                          ? "bg-amber-500"
                                          : "bg-red-500"
                                    }`}
                                  />
                                )}
                              </span>
                            )}
                            {tab === "debug" && "Debug"}
                          </button>
                        ))}
                      </div>

                      {/* Tab Content: Validate */}
                      {sceneTab[scene.id] === "validate" && (
                        <div className="grid gap-3 rounded-xl border border-zinc-200 bg-white/80 p-4">
                          <button
                            type="button"
                            onClick={() => handleValidateImage(scene)}
                            disabled={!scene.image_url || validatingSceneId === scene.id}
                            className="w-full rounded-full border border-zinc-300 bg-white py-2.5 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {validatingSceneId === scene.id ? "Validating..." : "Run Validation"}
                          </button>

                          {imageValidationResults[scene.id] && (
                            <>
                              {/* Match Rate */}
                              <div className="flex items-center gap-3">
                                <div className="flex-1">
                                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-zinc-200">
                                    <div
                                      className={`h-full rounded-full transition-all ${
                                        imageValidationResults[scene.id].match_rate >= 0.8
                                          ? "bg-emerald-500"
                                          : imageValidationResults[scene.id].match_rate >= 0.5
                                            ? "bg-amber-500"
                                            : "bg-red-500"
                                      }`}
                                      style={{
                                        width: `${Math.round(imageValidationResults[scene.id].match_rate * 100)}%`,
                                      }}
                                    />
                                  </div>
                                </div>
                                <span
                                  className={`text-lg font-bold ${
                                    imageValidationResults[scene.id].match_rate >= 0.8
                                      ? "text-emerald-600"
                                      : imageValidationResults[scene.id].match_rate >= 0.5
                                        ? "text-amber-600"
                                        : "text-red-600"
                                  }`}
                                >
                                  {Math.round(imageValidationResults[scene.id].match_rate * 100)}%
                                </span>
                              </div>

                              {/* Missing */}
                              {imageValidationResults[scene.id].missing.length > 0 && (
                                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                                  <div className="mb-2 flex items-center justify-between">
                                    <span className="text-[10px] font-semibold text-red-600 uppercase">
                                      Missing ({imageValidationResults[scene.id].missing.length})
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() =>
                                        applyMissingImageTags(scene, imageValidationResults[scene.id]?.missing ?? [])
                                      }
                                      className="rounded-full bg-red-500 px-2.5 py-1 text-[9px] font-semibold text-white hover:bg-red-600"
                                    >
                                      + Add
                                    </button>
                                  </div>
                                  <p className="text-xs text-red-700">
                                    {imageValidationResults[scene.id].missing.slice(0, 6).join(", ")}
                                    {imageValidationResults[scene.id].missing.length > 6 && " ..."}
                                  </p>
                                </div>
                              )}

                              {/* Extra */}
                              {imageValidationResults[scene.id].extra.length > 0 && (
                                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                                  <span className="text-[10px] font-semibold text-amber-600 uppercase">
                                    Extra ({imageValidationResults[scene.id].extra.length})
                                  </span>
                                  <p className="mt-1 text-xs text-amber-700">
                                    {imageValidationResults[scene.id].extra.slice(0, 6).join(", ")}
                                  </p>
                                </div>
                              )}

                              {/* Success */}
                              {imageValidationResults[scene.id].missing.length === 0 &&
                                imageValidationResults[scene.id].extra.length === 0 && (
                                  <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
                                    <span className="text-sm font-medium text-emerald-700">✓ Perfect Match</span>
                                  </div>
                                )}
                            </>
                          )}

                          {!imageValidationResults[scene.id] && !scene.image_url && (
                            <p className="text-center text-xs text-zinc-400">이미지를 먼저 생성하세요</p>
                          )}
                          {!imageValidationResults[scene.id] && scene.image_url && (
                            <p className="text-center text-xs text-zinc-400">Run Validation을 클릭하세요</p>
                          )}
                        </div>
                      )}

                      {/* Tab Content: Debug */}
                      {sceneTab[scene.id] === "debug" && (
                        <div className="grid gap-3 rounded-xl border border-zinc-200 bg-white/80 p-4">
                          <button
                            type="button"
                            onClick={() => {
                              const basePrompt = getBasePromptForScene(scene);
                              const scenePrompt = scene.image_prompt;
                              const prompt =
                                autoComposePrompt && basePrompt ? `${basePrompt}, ${scenePrompt}` : scenePrompt;
                              const payload = {
                                prompt,
                                negative_prompt: buildNegativePrompt(scene),
                                steps: resolveSteps(scene),
                                cfg_scale: resolveCfgScale(scene),
                                sampler_name: resolveSampler(scene),
                                seed: resolveSeed(scene),
                                clip_skip: resolveClipSkip(scene),
                                width: 512,
                                height: 512,
                              };
                              updateScene(scene.id, {
                                debug_payload: JSON.stringify(payload, null, 2),
                                debug_prompt: payload.prompt,
                              });
                            }}
                            className="w-full rounded-full border border-zinc-300 bg-white py-2.5 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase transition hover:bg-zinc-50"
                          >
                            Generate Debug Info
                          </button>
                          {scene.debug_payload && (
                            <textarea
                              value={scene.debug_payload}
                              readOnly
                              rows={8}
                              className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 font-mono text-[10px] text-zinc-600"
                            />
                          )}
                          {!scene.debug_payload && (
                            <p className="text-center text-xs text-zinc-400">Generate Debug Info를 클릭하세요</p>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-3">
                      <div className="aspect-square w-full overflow-hidden rounded-2xl border border-zinc-200 bg-white/70">
                        {scene.image_url ? (
                          <img
                            src={scene.image_url}
                            alt={`Scene ${scene.id}`}
                            onClick={() => setImagePreviewSrc(scene.image_url)}
                            className="h-full w-full cursor-pointer object-cover"
                          />
                        ) : (
                          <div className="flex h-full flex-col items-center justify-center gap-2">
                            <p className="text-xs text-zinc-400">No image</p>
                            <p className="text-[10px] text-zinc-300">Click Generate or Upload</p>
                          </div>
                        )}
                      </div>
                      {scene.candidates && scene.candidates.length > 1 && (
                        <div className="grid grid-cols-3 gap-2">
                          {scene.candidates.map((candidate, idx) => {
                            const isSelected = candidate.image_url === scene.image_url;
                            return (
                              <button
                                key={`${scene.id}-candidate-${idx}`}
                                type="button"
                                onClick={() =>
                                  updateScene(scene.id, { image_url: candidate.image_url })
                                }
                                className={`overflow-hidden rounded-xl border ${
                                  isSelected ? "border-zinc-900" : "border-zinc-200"
                                }`}
                              >
                                <img
                                  src={candidate.image_url}
                                  alt={`Candidate ${idx + 1}`}
                                  loading="lazy"
                                  className="h-full w-full object-cover"
                                />
                              </button>
                            );
                          })}
                        </div>
                      )}
                      <div className="flex flex-wrap items-center gap-2 text-[10px] tracking-[0.2em] text-zinc-400 uppercase">
                        <span>{scene.image_url ? "Ready" : "Upload required"}</span>
                        <span className="rounded-full border border-zinc-200 bg-white/80 px-2 py-0.5 text-[9px] text-zinc-500">
                          512x512
                        </span>
                        <span className="rounded-full border border-zinc-200 bg-white/80 px-2 py-0.5 text-[9px] text-zinc-500">
                          Steps {scene.steps}
                        </span>
                        <span className="rounded-full border border-zinc-200 bg-white/80 px-2 py-0.5 text-[9px] text-zinc-500">
                          Seed {scene.seed}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}
          </section>

          <div className="flex items-center gap-3">
            <span className="text-[10px] font-semibold tracking-[0.3em] text-zinc-500 uppercase">
              Output
            </span>
            <div className="h-px flex-1 bg-zinc-200/70" />
          </div>

          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Render Settings</h2>
                <p className="text-xs text-zinc-500">Configure layout, audio, and rendering.</p>
              </div>
            </div>

            {/* 1. LAYOUT SELECTION (TOP - Most Important) */}
            <div className="grid gap-3">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Layout
              </label>
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setLayoutStyle("full")}
                  className={`group flex flex-col items-center gap-2 rounded-2xl border-2 p-4 transition ${
                    layoutStyle === "full"
                      ? "border-zinc-900 bg-zinc-900/5 shadow-md"
                      : "border-zinc-200 bg-white/80 hover:border-zinc-400"
                  }`}
                >
                  <div
                    className={`flex h-20 w-11 flex-col items-center justify-center rounded-lg border-2 ${
                      layoutStyle === "full" ? "border-zinc-700 bg-zinc-200" : "border-zinc-300 bg-zinc-100"
                    }`}
                  >
                    <div className={`h-6 w-6 rounded ${layoutStyle === "full" ? "bg-zinc-500" : "bg-zinc-300"}`} />
                    <div className={`mt-1 h-1 w-5 rounded ${layoutStyle === "full" ? "bg-zinc-400" : "bg-zinc-200"}`} />
                    <div className={`mt-0.5 h-1 w-4 rounded ${layoutStyle === "full" ? "bg-zinc-400" : "bg-zinc-200"}`} />
                  </div>
                  <div className="text-center">
                    <p className={`text-xs font-semibold ${layoutStyle === "full" ? "text-zinc-900" : "text-zinc-600"}`}>Full</p>
                    <p className={`text-[10px] ${layoutStyle === "full" ? "text-zinc-600" : "text-zinc-400"}`}>9:16 세로</p>
                  </div>
                  {layoutStyle === "full" && (
                    <span className="rounded-full bg-zinc-900 px-2 py-0.5 text-[9px] font-semibold text-white">선택됨</span>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setLayoutStyle("post")}
                  className={`group flex flex-col items-center gap-2 rounded-2xl border-2 p-4 transition ${
                    layoutStyle === "post"
                      ? "border-zinc-900 bg-zinc-900/5 shadow-md"
                      : "border-zinc-200 bg-white/80 hover:border-zinc-400"
                  }`}
                >
                  <div
                    className={`flex h-14 w-14 flex-col items-center justify-center rounded-lg border-2 ${
                      layoutStyle === "post" ? "border-zinc-700 bg-zinc-200" : "border-zinc-300 bg-zinc-100"
                    }`}
                  >
                    <div className={`h-6 w-6 rounded ${layoutStyle === "post" ? "bg-zinc-500" : "bg-zinc-300"}`} />
                    <div className={`mt-1 h-1 w-5 rounded ${layoutStyle === "post" ? "bg-zinc-400" : "bg-zinc-200"}`} />
                  </div>
                  <div className="text-center">
                    <p className={`text-xs font-semibold ${layoutStyle === "post" ? "text-zinc-900" : "text-zinc-600"}`}>Post</p>
                    <p className={`text-[10px] ${layoutStyle === "post" ? "text-zinc-600" : "text-zinc-400"}`}>1:1 정사각형</p>
                  </div>
                  {layoutStyle === "post" && (
                    <span className="rounded-full bg-zinc-900 px-2 py-0.5 text-[9px] font-semibold text-white">선택됨</span>
                  )}
                </button>
              </div>
            </div>

            {/* 2. RENDER ACTIONS (Prominent) */}
            <div className="flex flex-col items-center gap-4 rounded-2xl border-2 border-zinc-200 bg-gradient-to-r from-zinc-50 to-white p-5">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRenderFull}
                  disabled={!canRender || isRendering}
                  className={`rounded-full px-5 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
                    layoutStyle === "full"
                      ? "bg-zinc-900 text-white shadow-lg"
                      : "border border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50"
                  }`}
                >
                  Render Full
                </button>
                <button
                  onClick={handleRenderPost}
                  disabled={!canRender || isRendering}
                  className={`rounded-full px-5 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
                    layoutStyle === "post"
                      ? "bg-zinc-900 text-white shadow-lg"
                      : "border border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50"
                  }`}
                >
                  Render Post
                </button>
                <button
                  onClick={handleRenderBoth}
                  disabled={!canRender || isRendering}
                  className="rounded-full bg-gradient-to-r from-zinc-800 to-zinc-900 px-6 py-2.5 text-sm font-semibold text-white shadow-lg transition hover:from-zinc-700 hover:to-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isRendering ? "Rendering..." : "Render Both ✨"}
                </button>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2 text-[10px] text-zinc-500">
                <span className="rounded-full border border-zinc-200 bg-white px-2 py-1">
                  Images: {scenes.filter((scene) => !!scene.image_url).length}/{scenes.length}
                </span>
                <span className="rounded-full border border-zinc-200 bg-white px-2 py-1">
                  Layout: {layoutStyle.toUpperCase()}
                </span>
              </div>
              {!canRender && scenes.length > 0 && (
                <p className="text-xs text-rose-500">Upload images for every scene to enable rendering.</p>
              )}
            </div>

            {/* 3. VIDEO SETTINGS (Collapsible) */}
            <details open className="group rounded-2xl border border-zinc-200 bg-white/80">
              <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                Video Settings
                <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
              </summary>
              <div className="grid gap-4 border-t border-zinc-100 p-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <label className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-4 py-3 text-xs font-medium text-zinc-600">
                    Include Subtitles
                    <input
                      type="checkbox"
                      checked={includeSubtitles}
                      onChange={(e) => setIncludeSubtitles(e.target.checked)}
                      className="h-4 w-4 accent-zinc-900"
                    />
                  </label>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Subtitle Font
                    </label>
                    <select
                      value={subtitleFont ?? ""}
                      onChange={(e) => setSubtitleFont(e.target.value)}
                      className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    >
                      {fontList.length === 0 && <option value="">Default</option>}
                      {fontList.map((font) => (
                        <option key={font.name} value={font.name}>{font.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Effects</label>
                    <select
                      value={motionStyle}
                      onChange={(e) => setMotionStyle(e.target.value as "none" | "slow_zoom")}
                      className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    >
                      <option value="none">None</option>
                      <option value="slow_zoom">Slow Zoom</option>
                    </select>
                  </div>
                </div>
                {/* Font Preview */}
                <div
                  className="rounded-xl border border-zinc-200 bg-zinc-900 px-4 py-3 text-center text-white"
                  style={{ fontFamily: `"${subtitleFont}", sans-serif` }}
                >
                  <span className="text-lg">{loadedFonts.has(subtitleFont) ? "가나다 ABC 123" : "Loading..."}</span>
                </div>
              </div>
            </details>

            {/* 4. AUDIO SETTINGS (Collapsible) */}
            <details open className="group rounded-2xl border border-zinc-200 bg-white/80">
              <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                Audio Settings
                <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
              </summary>
              <div className="grid gap-4 border-t border-zinc-100 p-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Voice</label>
                    <select
                      value={narratorVoice}
                      onChange={(e) => setNarratorVoice(e.target.value)}
                      className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                    >
                      {VOICES.map((voice) => (
                        <option key={voice.id} value={voice.id}>{voice.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                      Speed ({speedMultiplier.toFixed(2)}x)
                    </label>
                    <input
                      type="range"
                      min={0.8}
                      max={1.5}
                      step={0.05}
                      value={speedMultiplier}
                      onChange={(e) => setSpeedMultiplier(Number(e.target.value))}
                      className="mt-2 w-full accent-zinc-900"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">BGM</label>
                    <div className="flex items-center gap-2">
                      <select
                        value={bgmFile ?? ""}
                        onChange={(e) => setBgmFile(e.target.value || null)}
                        className="flex-1 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                      >
                        <option value="">None</option>
                        {bgmList.map((bgm) => (
                          <option key={bgm.name} value={bgm.name}>{bgm.name}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => handlePreviewBgm()}
                        disabled={!bgmFile || isPreviewingBgm}
                        className="rounded-full border border-zinc-200 bg-white px-3 py-2 text-[10px] font-semibold text-zinc-600 transition disabled:cursor-not-allowed disabled:text-zinc-400"
                      >
                        {isPreviewingBgm ? "▶" : "▶ 10s"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </details>

            {/* 5. OVERLAY / POST CARD (Collapsible) */}
            <details className="group rounded-2xl border border-zinc-200 bg-white/80">
              <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                {layoutStyle === "full" ? "SNS Overlay" : "Post Card Meta"}
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full border border-zinc-200 bg-white text-[10px] font-semibold text-zinc-600">
                    {layoutStyle === "full" ? (
                      overlayAvatarUrl ? (
                        <img src={overlayAvatarUrl} alt="Avatar" className="h-full w-full object-cover" />
                      ) : (
                        getAvatarInitial(overlaySettings.channel_name ?? "")
                      )
                    ) : postAvatarUrl ? (
                      <img src={postAvatarUrl} alt="Avatar" className="h-full w-full object-cover" />
                    ) : (
                      getAvatarInitial(postCardSettings.channel_name ?? "")
                    )}
                  </div>
                  <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
                </div>
              </summary>
              <div className="border-t border-zinc-100 p-4">
                {layoutStyle === "full" ? (
                  <div className="grid gap-4">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setOverlaySettings((prev) => ({ ...prev, ...buildOverlayContext() }))}
                        className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50"
                      >
                        Auto Fill
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRegenerateAvatar(overlaySettings.avatar_key ?? "")}
                        disabled={isRegeneratingAvatar || !(overlaySettings.avatar_key ?? "").trim()}
                        className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                      >
                        {isRegeneratingAvatar ? "Regenerating..." : "Regenerate Avatar"}
                      </button>
                    </div>
                    <input type="hidden" value={overlaySettings.frame_style} />
                    <div className="grid gap-3 md:grid-cols-4">
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Channel</label>
                        <input
                          value={overlaySettings.channel_name ?? ""}
                          onChange={(e) =>
                            setOverlaySettings((prev) => ({
                              ...prev,
                              channel_name: e.target.value,
                              avatar_key:
                                !prev.avatar_key || prev.avatar_key === slugifyAvatarKey(prev.channel_name)
                                  ? slugifyAvatarKey(e.target.value)
                                  : prev.avatar_key,
                            }))
                          }
                          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Avatar Key</label>
                        <input
                          value={overlaySettings.avatar_key ?? ""}
                          onChange={(e) => setOverlaySettings((prev) => ({ ...prev, avatar_key: e.target.value }))}
                          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Likes</label>
                        <input
                          value={overlaySettings.likes_count ?? ""}
                          onChange={(e) => setOverlaySettings((prev) => ({ ...prev, likes_count: e.target.value }))}
                          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Caption</label>
                        <input
                          value={overlaySettings.caption ?? ""}
                          onChange={(e) => setOverlaySettings((prev) => ({ ...prev, caption: e.target.value }))}
                          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="grid gap-4">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setPostCardSettings(buildPostCardContext())}
                        className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50"
                      >
                        Auto Fill
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRegenerateAvatar(postCardSettings.avatar_key ?? "")}
                        disabled={isRegeneratingAvatar || !(postCardSettings.avatar_key ?? "").trim()}
                        className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 text-[10px] font-semibold text-zinc-600 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-400"
                      >
                        {isRegeneratingAvatar ? "Regenerating..." : "Regenerate Avatar"}
                      </button>
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Channel</label>
                        <input
                          value={postCardSettings.channel_name ?? ""}
                          onChange={(e) =>
                            setPostCardSettings((prev) => ({
                              ...prev,
                              channel_name: e.target.value,
                              avatar_key:
                                !prev.avatar_key || prev.avatar_key === slugifyAvatarKey(prev.channel_name)
                                  ? slugifyAvatarKey(e.target.value)
                                  : prev.avatar_key,
                            }))
                          }
                          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Avatar Key</label>
                        <input
                          value={postCardSettings.avatar_key ?? ""}
                          onChange={(e) => setPostCardSettings((prev) => ({ ...prev, avatar_key: e.target.value }))}
                          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">Caption</label>
                        <input
                          value={postCardSettings.caption ?? ""}
                          onChange={(e) => setPostCardSettings((prev) => ({ ...prev, caption: e.target.value }))}
                          className="rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </details>

            {/* 6. ADVANCED (Collapsible - SD Model) */}
            <details className="group rounded-2xl border border-zinc-200 bg-white/80">
              <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                Advanced
                <span className="text-zinc-400 transition group-open:rotate-180">▼</span>
              </summary>
              <div className="border-t border-zinc-100 p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-xs text-zinc-500">SD Model:</span>
                  <span className="text-xs font-semibold text-zinc-700">{currentModel}</span>
                  {isModelUpdating && (
                    <span className="text-[10px] text-zinc-400">Updating...</span>
                  )}
                  <select
                    value={selectedModel}
                    onChange={(e) => handleModelChange(e.target.value)}
                    disabled={isModelUpdating || sdModels.length === 0}
                    className="min-w-[200px] rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400 disabled:bg-zinc-100"
                  >
                    {sdModels.length === 0 && <option value="">No models found</option>}
                    {sdModels.map((model) => (
                      <option key={model.title} value={model.title}>{model.title}</option>
                    ))}
                  </select>
                </div>
              </div>
            </details>
          </section>

          {(videoUrl || videoUrlFull || videoUrlPost || recentVideos.length > 0) && (
            <section className="grid gap-4 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">
                  {videoUrlFull || videoUrlPost ? "Rendered Videos" : "Rendered Video"}
                </h2>
                <p className="text-xs text-zinc-500">
                  {videoUrlFull || videoUrlPost
                    ? "Compare full and post renders."
                    : "Preview the latest render."}
                </p>
              </div>
              {recentVideos.length > 0 && (
                <div className="grid gap-3">
                  <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Recent Rendered Videos (8)
                  </span>
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {recentVideos.map((item, idx) => (
                      <div
                        key={`${item.url}-${item.createdAt}`}
                        className={`group grid gap-2 rounded-2xl border bg-white/70 p-3 shadow-sm ${
                          idx === 0
                            ? "border-zinc-900/40 bg-white shadow-lg ring-2 shadow-zinc-900/10 ring-zinc-900/10"
                            : "border-zinc-200"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                            {item.label}
                          </span>
                          <span className="text-[10px] text-zinc-400">
                            {new Date(item.createdAt).toLocaleString()}
                          </span>
                          {idx === 0 && (
                            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[9px] font-semibold tracking-[0.2em] text-emerald-600 uppercase">
                              Latest
                            </span>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDeleteRecentVideo(item.url)}
                            className="text-[10px] font-semibold tracking-[0.2em] text-rose-500 uppercase opacity-0 transition group-hover:opacity-100"
                          >
                            Delete
                          </button>
                        </div>
                        <div className="aspect-[9/16] w-full overflow-hidden rounded-2xl bg-black shadow">
                          <button
                            type="button"
                            onClick={() => setVideoPreviewSrc(item.url)}
                            className="h-full w-full"
                          >
                            <video
                              muted
                              playsInline
                              preload="metadata"
                              src={item.url}
                              className="pointer-events-none h-full w-full object-cover"
                            />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {recentVideos.length === 0 && (
                <div className="rounded-2xl border border-dashed border-zinc-200 bg-white/70 p-4 text-xs text-zinc-500">
                  No rendered videos yet. Run a render to see results here.
                </div>
              )}
            </section>
          )}
        </main>
        )}

        {/* ============ SHARED: Auto Run Progress Modal ============ */}
        {isAutoRunning && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-6 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-3xl border border-white/60 bg-white/90 p-6 text-sm text-zinc-700 shadow-2xl">
              <div className="mb-3 flex items-center justify-between text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                <span>Autopilot Running</span>
                <span>
                  Step {AUTO_RUN_STEPS.findIndex((step) => step.id === autoRunState.step) + 1}/
                  {AUTO_RUN_STEPS.length}
                </span>
              </div>
              <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-zinc-200">
                <div
                  className="h-full rounded-full bg-zinc-900 transition-all duration-500"
                  style={{ width: `${autoRunProgress}%` }}
                />
              </div>
              <p className="text-base font-semibold text-zinc-900">{autoRunState.message}</p>
              {autoRunLog.length > 0 && (
                <div className="mt-3 grid gap-1 text-[11px] text-zinc-500">
                  {autoRunLog.map((entry, idx) => (
                    <span key={`${entry}-${idx}`}>• {entry}</span>
                  ))}
                </div>
              )}
              <button
                type="button"
                onClick={() => {
                  if (window.confirm("Autopilot을 취소하시겠습니까?")) {
                    handleAutoRunCancel();
                  }
                }}
                className="mt-5 w-full rounded-full border border-zinc-300 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase hover:bg-zinc-50 hover:border-zinc-400"
              >
                Cancel Autopilot
              </button>
            </div>
          </div>
        )}
      </div>
      {imagePreviewSrc && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60"
            onClick={() => setImagePreviewSrc(null)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
            <div className="max-h-[90vh] w-full max-w-3xl rounded-3xl border border-white/40 bg-white/90 p-4 shadow-2xl backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Image Preview
                </span>
                <button
                  type="button"
                  onClick={() => setImagePreviewSrc(null)}
                  className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
                >
                  Close
                </button>
              </div>
              <div className="mt-3 flex max-h-[80vh] w-full items-center justify-center overflow-hidden rounded-2xl bg-zinc-100 p-3">
                <img
                  src={imagePreviewSrc}
                  alt="Generated scene"
                  className="max-h-[76vh] w-auto max-w-full object-contain"
                />
              </div>
            </div>
          </div>
        </>
      )}
      {videoPreviewSrc && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60"
            onClick={() => setVideoPreviewSrc(null)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
            <div className="max-h-[90vh] w-full max-w-3xl rounded-3xl border border-white/40 bg-white/90 p-4 shadow-2xl backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                  Video Preview
                </span>
                <button
                  type="button"
                  onClick={() => setVideoPreviewSrc(null)}
                  className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
                >
                  Close
                </button>
              </div>
              <div className="mt-3 flex max-h-[80vh] w-full items-center justify-center overflow-hidden rounded-2xl bg-black">
                <video
                  controls
                  autoPlay
                  src={videoPreviewSrc}
                  className="max-h-[78vh] w-auto max-w-full object-contain"
                />
              </div>
            </div>
          </div>
        </>
      )}
      <div
        className={`fixed inset-0 z-40 bg-black/30 transition-opacity ${isHelperOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={() => setIsHelperOpen(false)}
      />
      <aside
        className={`fixed top-0 right-0 z-50 h-full w-full max-w-md transform bg-white shadow-2xl transition-transform ${isHelperOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="flex h-full flex-col gap-4 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Prompt Helper</p>
              <h3 className="text-lg font-semibold text-zinc-900">Split Example Prompt</h3>
            </div>
            <button
              type="button"
              onClick={() => setIsHelperOpen(false)}
              className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
            >
              Close
            </button>
          </div>
          {copyStatus && (
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              {copyStatus}
            </div>
          )}
          <div className="grid gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Example Prompt
            </label>
            <textarea
              value={examplePrompt}
              onChange={(e) => setExamplePrompt(e.target.value)}
              rows={4}
              className="rounded-2xl border border-zinc-200 bg-white p-3 text-sm outline-none focus:border-zinc-400"
              placeholder="Paste a full prompt line from Civitai"
            />
            <button
              type="button"
              onClick={handleSuggestSplit}
              disabled={isSuggesting || !examplePrompt.trim()}
              className="rounded-full bg-zinc-900 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {isSuggesting ? "Suggesting..." : "Suggest Base/Scene"}
            </button>
          </div>
          {(suggestedBase || suggestedScene) && (
            <div className="grid gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Suggested Base
                  </label>
                  <button
                    type="button"
                    onClick={() => copyText(suggestedBase)}
                    className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
                  >
                    Copy
                  </button>
                </div>
                <textarea
                  value={suggestedBase}
                  readOnly
                  rows={3}
                  className="rounded-2xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600"
                />
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                    Suggested Scene
                  </label>
                  <button
                    type="button"
                    onClick={() => copyText(suggestedScene)}
                    className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
                  >
                    Copy
                  </button>
                </div>
                <textarea
                  value={suggestedScene}
                  readOnly
                  rows={3}
                  className="rounded-2xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600"
                />
              </div>
            </div>
          )}
          <div className="mt-auto text-[10px] text-zinc-400">
            Suggestions do not auto-apply. Copy and paste into Base Prompt or Scene Prompt.
          </div>
        </div>
      </aside>

      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed bottom-6 left-1/2 z-[100] -translate-x-1/2 transform rounded-full px-6 py-3 text-sm font-medium shadow-lg transition-all ${
            toast.type === "success"
              ? "bg-emerald-500 text-white"
              : "bg-red-500 text-white"
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}
