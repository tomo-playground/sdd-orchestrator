"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useAutopilot } from "./hooks";
import axios from "axios";

import type {
  Scene,
  AudioItem,
  FontItem,
  OverlaySettings,
  PostCardSettings,
  SdModel,
  ActorGender,
  AutoRunStepId,
  ValidationIssue,
  SceneValidation,
  FixSuggestion,
  ImageValidation,
} from "./types";

import {
  API_BASE,
  DEFAULT_BGM,
  DEFAULT_SUBTITLE_FONT,
  DRAFT_STORAGE_KEY,
  MAX_IMAGE_CACHE_SIZE,
  DEFAULT_OVERLAY_SETTINGS,
  DEFAULT_POST_CARD_SETTINGS,
  AUTO_RUN_STEPS,
  VOICES,
  SAMPLERS,
  OVERLAY_STYLES,
  PROMPT_SAMPLES,
  STRUCTURES,
  CAMERA_KEYWORDS,
  ACTION_KEYWORDS,
  BACKGROUND_KEYWORDS,
  SCENE_SPECIFIC_KEYWORDS,
} from "./constants";

import SetupPanel from "./components/SetupPanel";
import AutoRunStatus from "./components/AutoRunStatus";
import SceneFilmstrip from "./components/SceneFilmstrip";
import SceneImagePanel from "./components/SceneImagePanel";
import ValidationTabContent from "./components/ValidationTabContent";
import DebugTabContent from "./components/DebugTabContent";
import LayoutSelector from "./components/LayoutSelector";
import AutoRunProgressModal from "./components/AutoRunProgressModal";
import PreviewModal from "./components/PreviewModal";
import RenderSettingsPanel from "./components/RenderSettingsPanel";
import PromptHelperSidebar from "./components/PromptHelperSidebar";
import RenderedVideosSection from "./components/RenderedVideosSection";
import StoryboardGeneratorPanel from "./components/StoryboardGeneratorPanel";
import PromptSetupPanel from "./components/PromptSetupPanel";
import SceneCard from "./components/SceneCard";
import SceneListHeader from "./components/SceneListHeader";
import StoryboardActionsBar from "./components/StoryboardActionsBar";
import WorkingModeHeader from "./components/WorkingModeHeader";
import SectionDivider from "./components/SectionDivider";
import Toast from "./components/Toast";
import {
  slugifyAvatarKey,
  normalizeOverlaySettings,
  normalizePostCardSettings,
  getAvatarInitial,
  splitPromptTokens,
  mergePromptTokens,
  deduplicatePromptTokens,
  stripLeadingHearts,
  applyHeartPrefix,
  generateChannelName,
  computeValidationResults,
  getFixSuggestions,
} from "./utils";

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
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [viewMode, setViewMode] = useState<"setup" | "working">("setup");

  // Autopilot hook
  const {
    autoRunState,
    autoRunLog,
    isAutoRunning,
    autoRunProgress,
    pushLog: pushAutoRunLog,
    setStep: setAutoRunStep,
    setError: setAutoRunError,
    setDone: setAutoRunDone,
    checkCancelled: assertNotCancelled,
    cancel: handleAutoRunCancel,
    reset: resetAutoRun,
    startRun: startAutoRun,
  } = useAutopilot();
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);
  const draftSaveTimeoutRef = useRef<number | null>(null);
  const hasHydratedDraftRef = useRef(false);

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

  const runAutoRunFromStep = async (startStep: AutoRunStepId) => {
    if (!topic.trim()) {
      alert("Enter a topic first.");
      return;
    }
    startAutoRun();
    let workingScenes = scenes;
    let currentStep: AutoRunStepId = startStep;
    setMotionStyle("none");
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
          setAutoRunStep("storyboard", "Generating storyboard...");
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
          setAutoRunStep("fix", "Auto-fixing scripts and prompts...");
          workingScenes = applyAutoFixForScenes(workingScenes);
          setScenes(workingScenes);
          const { results, summary } = computeValidationResults(workingScenes);
          setValidationResults(results);
          setValidationSummary(summary);
          pushAutoRunLog("Auto-fix applied");
        }

        if (currentStep === "images") {
          setAutoRunStep("images", "Generating scene images...");
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
          setAutoRunStep("validate", "Validating images...");
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
          setAutoRunStep("render", "Rendering video...");
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
      setAutoRunDone();
      showToast("Auto Run 완료! 영상이 생성되었습니다.", "success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Autopilot failed";
      setAutoRunError(currentStep, message);
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
    resetAutoRun();
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
    const baseTokens = splitPromptTokens(base).filter((token) => {
      const lower = token.toLowerCase();
      return !SCENE_SPECIFIC_KEYWORDS.some((keyword) => lower.includes(keyword));
    });
    const sceneTokens = splitPromptTokens(scenePrompt);
    return mergePromptTokens(baseTokens, sceneTokens).join(", ");
  };

  const buildNegativePrompt = (scene: Scene) => {
    const base = baseNegativePromptA.trim();
    const sceneNeg = scene.negative_prompt.trim();
    if (!autoComposePrompt) return sceneNeg;
    const combined = base && sceneNeg ? `${base}, ${sceneNeg}` : base || sceneNeg;
    return deduplicatePromptTokens(combined);
  };


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
      steps: scene.steps,
      cfg_scale: scene.cfg_scale,
      sampler_name: scene.sampler_name,
      seed: scene.seed,
      clip_skip: scene.clip_skip,
      width: 512,
      height: 512,
      ...hiResPayload,
    };
    try {
      const res = await axios.post(`${API_BASE}/scene/generate`, {
        prompt,
        negative_prompt: buildNegativePrompt(scene),
        steps: scene.steps,
        cfg_scale: scene.cfg_scale,
        sampler_name: scene.sampler_name,
        seed: scene.seed,
        clip_skip: scene.clip_skip,
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

  const runValidation = () => {
    const { results, summary } = computeValidationResults(scenes);
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
      const suggestions = getFixSuggestions(scene, validation, topic);
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
          <SetupPanel
            topic={topic}
            setTopic={setTopic}
            layoutStyle={layoutStyle}
            setLayoutStyle={setLayoutStyle}
            narratorVoice={narratorVoice}
            setNarratorVoice={setNarratorVoice}
            bgmFile={bgmFile}
            setBgmFile={setBgmFile}
            bgmList={bgmList}
            speedMultiplier={speedMultiplier}
            setSpeedMultiplier={setSpeedMultiplier}
            onAutoRun={() => {
              setViewMode("working");
              handleAutoRun();
            }}
            onManualMode={() => setViewMode("working")}
          />
        )}

        {/* ============ WORKING MODE ============ */}
        {viewMode === "working" && (
        <main
          className={`relative mx-auto flex w-full max-w-6xl flex-col gap-10 px-6 py-12 ${
            isAutoRunning ? "pointer-events-none opacity-60" : ""
          }`}
        >
          <WorkingModeHeader onBack={() => setViewMode("setup")} />

          <SectionDivider label="Plan & Generate" />

          <StoryboardGeneratorPanel
            topic={topic}
            setTopic={setTopic}
            duration={duration}
            setDuration={setDuration}
            language={language}
            setLanguage={setLanguage}
            style={style}
            setStyle={setStyle}
            structure={structure}
            setStructure={setStructure}
          />

          <PromptSetupPanel
            baseTab={baseTab}
            setBaseTab={setBaseTab}
            autoComposePrompt={autoComposePrompt}
            setAutoComposePrompt={setAutoComposePrompt}
            autoRewritePrompt={autoRewritePrompt}
            setAutoRewritePrompt={setAutoRewritePrompt}
            hiResEnabled={hiResEnabled}
            setHiResEnabled={setHiResEnabled}
            veoEnabled={veoEnabled}
            setVeoEnabled={setVeoEnabled}
            actorAGender={actorAGender}
            setActorAGender={setActorAGender}
            basePromptA={basePromptA}
            setBasePromptA={setBasePromptA}
            baseNegativePromptA={baseNegativePromptA}
            setBaseNegativePromptA={setBaseNegativePromptA}
            baseStepsA={baseStepsA}
            setBaseStepsA={setBaseStepsA}
            baseCfgScaleA={baseCfgScaleA}
            setBaseCfgScaleA={setBaseCfgScaleA}
            baseSamplerA={baseSamplerA}
            setBaseSamplerA={setBaseSamplerA}
            baseSeedA={baseSeedA}
            setBaseSeedA={setBaseSeedA}
            baseClipSkipA={baseClipSkipA}
            setBaseClipSkipA={setBaseClipSkipA}
            selectedSampleId={selectedSampleId}
            setSelectedSampleId={setSelectedSampleId}
            onOpenPromptHelper={() => setIsHelperOpen(true)}
          />

          <StoryboardActionsBar
            onResetScenes={resetScenesOnly}
            onResetDraft={resetDraft}
            onGenerate={handleGenerateScenes}
            onAutoRun={handleAutoRun}
            isGenerating={isGenerating}
            isRendering={isRendering}
            isAutoRunning={isAutoRunning}
            topicEmpty={!topic.trim()}
            autoRunStep={autoRunState.step}
          />
          <AutoRunStatus
            autoRunState={autoRunState}
            autoRunLog={autoRunLog}
            onResume={handleAutoRunResume}
            onRestart={handleAutoRun}
          />

          <SectionDivider label="Scene Work" />

          <section className="grid gap-6">
            <SceneListHeader
              onValidate={runValidation}
              onAutoFixAll={handleAutoFixAll}
              onAddScene={handleAddScene}
              imageCheckMode={imageCheckMode}
              onImageCheckModeChange={setImageCheckMode}
              multiGenEnabled={multiGenEnabled}
              onMultiGenEnabledChange={setMultiGenEnabled}
              validationSummary={validationSummary}
              scenesCount={scenes.length}
            />

            {/* Filmstrip Navigation */}
            <SceneFilmstrip
              scenes={scenes}
              currentSceneIndex={currentSceneIndex}
              onSceneSelect={setCurrentSceneIndex}
            />

            {/* Current Scene Card */}
            {scenes.length > 0 && scenes[currentSceneIndex] && (
              <SceneCard
                key={scenes[currentSceneIndex].id}
                scene={scenes[currentSceneIndex]}
                validationResult={validationResults[scenes[currentSceneIndex].id]}
                imageValidationResult={imageValidationResults[scenes[currentSceneIndex].id]}
                sceneTab={sceneTab[scenes[currentSceneIndex].id] ?? null}
                onSceneTabChange={(tab) =>
                  setSceneTab((prev) => ({ ...prev, [scenes[currentSceneIndex].id]: tab }))
                }
                sceneMenuOpen={sceneMenuOpen === scenes[currentSceneIndex].id}
                onSceneMenuToggle={() =>
                  setSceneMenuOpen(sceneMenuOpen === scenes[currentSceneIndex].id ? null : scenes[currentSceneIndex].id)
                }
                onSceneMenuClose={() => setSceneMenuOpen(null)}
                suggestionExpanded={suggestionExpanded[scenes[currentSceneIndex].id] ?? false}
                onSuggestionToggle={() =>
                  setSuggestionExpanded((prev) => ({
                    ...prev,
                    [scenes[currentSceneIndex].id]: !prev[scenes[currentSceneIndex].id],
                  }))
                }
                validatingSceneId={validatingSceneId}
                autoComposePrompt={autoComposePrompt}
                onUpdateScene={(updates) => updateScene(scenes[currentSceneIndex].id, updates)}
                onRemoveScene={() => handleRemoveScene(scenes[currentSceneIndex].id)}
                onSpeakerChange={(speaker) => handleSpeakerChange(scenes[currentSceneIndex], speaker)}
                onImageUpload={(file) => handleImageUpload(scenes[currentSceneIndex].id, file)}
                onGenerateImage={() => handleGenerateSceneImage(scenes[currentSceneIndex])}
                onValidateImage={() => handleValidateImage(scenes[currentSceneIndex])}
                onApplyMissingTags={(tags) => applyMissingImageTags(scenes[currentSceneIndex], tags)}
                onImagePreview={setImagePreviewSrc}
                getSceneStatus={getSceneStatus}
                getFixSuggestions={(scene, validation) => getFixSuggestions(scene, validation, topic)}
                applySuggestion={applySuggestion}
                buildPositivePrompt={buildPositivePrompt}
                buildNegativePrompt={buildNegativePrompt}
                getBasePromptForScene={getBasePromptForScene}
                showToast={showToast}
              />
            )}
          </section>

          <SectionDivider label="Output" />

          <RenderSettingsPanel
            layoutStyle={layoutStyle}
            setLayoutStyle={setLayoutStyle}
            canRender={canRender}
            isRendering={isRendering}
            scenesWithImages={scenes.filter((scene) => !!scene.image_url).length}
            totalScenes={scenes.length}
            onRenderFull={handleRenderFull}
            onRenderPost={handleRenderPost}
            onRenderBoth={handleRenderBoth}
            includeSubtitles={includeSubtitles}
            setIncludeSubtitles={setIncludeSubtitles}
            subtitleFont={subtitleFont}
            setSubtitleFont={setSubtitleFont}
            fontList={fontList}
            loadedFonts={loadedFonts}
            motionStyle={motionStyle}
            setMotionStyle={setMotionStyle}
            narratorVoice={narratorVoice}
            setNarratorVoice={setNarratorVoice}
            speedMultiplier={speedMultiplier}
            setSpeedMultiplier={setSpeedMultiplier}
            bgmFile={bgmFile}
            setBgmFile={setBgmFile}
            bgmList={bgmList}
            onPreviewBgm={handlePreviewBgm}
            isPreviewingBgm={isPreviewingBgm}
            overlaySettings={overlaySettings}
            setOverlaySettings={setOverlaySettings}
            overlayAvatarUrl={overlayAvatarUrl}
            postCardSettings={postCardSettings}
            setPostCardSettings={setPostCardSettings}
            postAvatarUrl={postAvatarUrl}
            onAutoFillOverlay={() => setOverlaySettings((prev) => ({ ...prev, ...buildOverlayContext() }))}
            onAutoFillPostCard={() => setPostCardSettings(buildPostCardContext())}
            onRegenerateAvatar={handleRegenerateAvatar}
            isRegeneratingAvatar={isRegeneratingAvatar}
            getAvatarInitial={getAvatarInitial}
            slugifyAvatarKey={slugifyAvatarKey}
            currentModel={currentModel}
            selectedModel={selectedModel}
            sdModels={sdModels}
            onModelChange={handleModelChange}
            isModelUpdating={isModelUpdating}
          />

          <RenderedVideosSection
            videoUrl={videoUrl}
            videoUrlFull={videoUrlFull}
            videoUrlPost={videoUrlPost}
            recentVideos={recentVideos}
            onVideoPreview={setVideoPreviewSrc}
            onDeleteRecentVideo={handleDeleteRecentVideo}
          />
        </main>
        )}

        {/* ============ SHARED: Auto Run Progress Modal ============ */}
        {isAutoRunning && (
          <AutoRunProgressModal
            autoRunState={autoRunState}
            autoRunLog={autoRunLog}
            autoRunProgress={autoRunProgress}
            onCancel={handleAutoRunCancel}
          />
        )}
      </div>
      {imagePreviewSrc && (
        <PreviewModal
          type="image"
          src={imagePreviewSrc}
          onClose={() => setImagePreviewSrc(null)}
        />
      )}
      {videoPreviewSrc && (
        <PreviewModal
          type="video"
          src={videoPreviewSrc}
          onClose={() => setVideoPreviewSrc(null)}
        />
      )}
      <PromptHelperSidebar
        isOpen={isHelperOpen}
        onClose={() => setIsHelperOpen(false)}
        examplePrompt={examplePrompt}
        setExamplePrompt={setExamplePrompt}
        onSuggestSplit={handleSuggestSplit}
        isSuggesting={isSuggesting}
        suggestedBase={suggestedBase}
        suggestedScene={suggestedScene}
        copyStatus={copyStatus}
        onCopyText={copyText}
      />

      {/* Toast Notification */}
      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  );
}
