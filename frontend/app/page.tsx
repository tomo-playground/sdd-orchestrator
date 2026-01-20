"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import axios from "axios";

const API_BASE = "http://localhost:8000";

type Scene = {
  id: number;
  script: string;
  speaker: "Narrator" | "A";
  duration: number;
  image_prompt: string;
  image_prompt_ko: string;
  image_url: string | null;
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
type OverlaySettings = {
  enabled: boolean;
  profile_name: string;
  likes_count: string;
  caption: string;
  frame_style: string;
};
type SdModel = { title: string; model_name: string };
type ActorGender = "male" | "female";
type ValidationIssue = { level: "warn" | "error"; message: string };
type SceneValidation = { status: "ok" | "warn" | "error"; issues: ValidationIssue[] };
type FixSuggestion = {
  id: string;
  message: string;
  action?: {
    type: "add_positive" | "remove_negative_scene" | "set_speaker_a";
    tokens?: string[];
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

const OVERLAY_STYLES = [
  { id: "overlay_minimal.png", label: "Minimal" },
  { id: "overlay_clean.png", label: "Clean" },
  { id: "overlay_bold.png", label: "Bold" },
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
  const [isGenerating, setIsGenerating] = useState(false);
  const [basePromptA, setBasePromptA] = useState("");
  const [baseNegativePromptA, setBaseNegativePromptA] = useState("");
  const [autoComposePrompt, setAutoComposePrompt] = useState(true);
  const [autoRewritePrompt, setAutoRewritePrompt] = useState(true);
  const [baseTab, setBaseTab] = useState<"global" | "A">("A");
  const [examplePrompt, setExamplePrompt] = useState("");
  const [suggestedBase, setSuggestedBase] = useState("");
  const [suggestedScene, setSuggestedScene] = useState("");
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [isHelperOpen, setIsHelperOpen] = useState(false);
  const [copyStatus, setCopyStatus] = useState("");
  const [validationResults, setValidationResults] = useState<Record<number, SceneValidation>>({});
  const [validationSummary, setValidationSummary] = useState({ ok: 0, warn: 0, error: 0 });
  const [validationExpanded, setValidationExpanded] = useState<Record<number, boolean>>({});
  const [suggestionExpanded, setSuggestionExpanded] = useState<Record<number, boolean>>({});
  const [imageCheckMode, setImageCheckMode] = useState<"local" | "gemini">("local");
  const [imageValidationResults, setImageValidationResults] = useState<Record<number, ImageValidation>>({});
  const [baseStepsA, setBaseStepsA] = useState(27);
  const [baseCfgScaleA, setBaseCfgScaleA] = useState(7);
  const [baseSamplerA, setBaseSamplerA] = useState("DPM++ 2M Karras");
  const [baseSeedA, setBaseSeedA] = useState(-1);
  const [baseClipSkipA, setBaseClipSkipA] = useState(2);
  const [advancedExpanded, setAdvancedExpanded] = useState<Record<number, boolean>>({});
  const prevBaseNegativeRefA = useRef("");
  const [includeSubtitles, setIncludeSubtitles] = useState(true);
  const [narratorVoice, setNarratorVoice] = useState(VOICES[0].id);
  const [bgmList, setBgmList] = useState<AudioItem[]>([]);
  const [bgmFile, setBgmFile] = useState<string | null>(null);
  const [speedMultiplier, setSpeedMultiplier] = useState(1.0);
  const [overlaySettings, setOverlaySettings] = useState<OverlaySettings>({
    enabled: true,
    profile_name: "",
    likes_count: "",
    caption: "",
    frame_style: "overlay_minimal.png",
  });
  const [sdModels, setSdModels] = useState<SdModel[]>([]);
  const [currentModel, setCurrentModel] = useState("Unknown");
  const [selectedModel, setSelectedModel] = useState("");
  const [isModelUpdating, setIsModelUpdating] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [layoutStyle, setLayoutStyle] = useState<"full" | "post">("full");
  const [motionStyle, setMotionStyle] = useState<"none" | "slow_zoom">("none");
  const [hiResEnabled, setHiResEnabled] = useState(false);
  const [imagePreviewSrc, setImagePreviewSrc] = useState<string | null>(null);
  const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    axios
      .get(`${API_BASE}/audio/list`)
      .then((res) => setBgmList(res.data.audios || []))
      .catch(() => setBgmList([]));
  }, []);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const [modelsRes, optionsRes] = await Promise.all([
          axios.get(`${API_BASE}/sd/models`),
          axios.get(`${API_BASE}/sd/options`),
        ]);
        const models = (modelsRes.data.models || []) as SdModel[];
        const modelName = optionsRes.data.model || "Unknown";
        setSdModels(models);
        setCurrentModel(modelName);
        setSelectedModel(modelName);
      } catch {
        setSdModels([]);
      }
    };
    void fetchModels();
  }, []);

  const canRender = useMemo(() => {
    return scenes.length > 0 && scenes.every((scene) => !!scene.image_url);
  }, [scenes]);

  const updateScene = (id: number, patch: Partial<Scene>) => {
    setScenes((prev) =>
      prev.map((scene) => (scene.id === id ? { ...scene, ...patch } : scene))
    );
  };

  const handleGenerateScenes = async () => {
    if (!topic.trim()) return;
    setIsGenerating(true);
    try {
      const res = await axios.post(`${API_BASE}/storyboard/create`, {
        topic,
        duration,
        style,
        language,
        structure,
        actor_a_gender: actorAGender,
      });
      const incoming = Array.isArray(res.data.scenes) ? res.data.scenes : [];
      const mapped: Scene[] = incoming.map((scene: any, idx: number) => {
        const rawSpeaker = String(scene.speaker ?? "Narrator");
        const speaker: Scene["speaker"] =
          rawSpeaker === "A" || rawSpeaker === "Narrator" ? (rawSpeaker as Scene["speaker"]) : "Narrator";
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
      setScenes(mapped);
    } catch {
      alert("Storyboard generation failed");
    } finally {
      setIsGenerating(false);
    }
  };

  const buildOverlayContext = () => {
    const fallbackProfile = topic.trim().split(/\s+/)[0] || "shorts";
    const scripts = scenes
      .map((scene) => scene.script.trim())
      .filter(Boolean);
    const baseCaption = scripts[0] || topic.trim() || "오늘의 쇼츠";
    const hashtagSource = (topic || baseCaption).split(/\s+/).slice(0, 2);
    const hashtags = hashtagSource
      .map((token) => token.replace(/[^\w가-힣]/g, ""))
      .filter(Boolean)
      .map((token) => `#${token}`);
    const caption = `${baseCaption}${hashtags.length ? " " + hashtags.join(" ") : ""}`.trim();
    const likesPool = ["1.2k", "3.8k", "7.4k", "12.5k", "18.9k"];
    const likes_count = likesPool[baseCaption.length % likesPool.length];
    return {
      profile_name: fallbackProfile,
      likes_count,
      caption,
    };
  };

  const handleImageUpload = (sceneId: number, file?: File) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      updateScene(sceneId, { image_url: reader.result as string });
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
    setScenes((prev) => prev.filter((scene) => scene.id !== sceneId));
  };

  const getBaseNegativeForScene = () => baseNegativePromptA.trim();

  useEffect(() => {
    const prevBase = prevBaseNegativeRefA.current;
    if (prevBase === baseNegativePromptA) return;
    setScenes((prev) =>
      prev.map((scene) => {
        if (scene.speaker === "B") return scene;
        if (!scene.negative_prompt || scene.negative_prompt === prevBase) {
          return { ...scene, negative_prompt: baseNegativePromptA };
        }
        return scene;
      })
    );
    prevBaseNegativeRefA.current = baseNegativePromptA;
  }, [baseNegativePromptA]);


  const handleRenderVideo = async () => {
    if (!canRender) return;
    setIsRendering(true);
    try {
      const res = await axios.post(`${API_BASE}/video/create`, {
        scenes: scenes.map((scene) => ({
          image_url: scene.image_url,
          script: scene.script,
          speaker: scene.speaker,
          duration: scene.duration,
        })),
        project_name: topic.trim().replace(/\s+/g, "_") || "my_shorts",
        width: 1080,
        height: 1920,
        layout_style: layoutStyle,
        motion_style: motionStyle,
        narrator_voice: narratorVoice,
        bgm_file: bgmFile,
        speed_multiplier: speedMultiplier,
        include_subtitles: includeSubtitles,
        overlay_settings: overlaySettings,
      });
      setVideoUrl(res.data.video_url || null);
    } catch {
      alert("Video rendering failed");
    } finally {
      setIsRendering(false);
    }
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
    const sourceUrl = urlOverride
      ?? bgmList.find((bgm) => bgm.name === bgmFile)?.url
      ?? "";
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
      "sitting", "standing", "walking", "running", "jumping", "kneeling", "crouching", "lying",
      "from above", "top-down", "low angle", "high angle", "close-up", "wide shot", "full body",
      "library", "cafe", "street", "room", "bedroom", "office", "classroom", "park", "forest",
      "beach", "city", "night", "sunset", "sunrise", "rain", "snow", "background", "lighting",
      "indoors", "outdoors"
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
    const base = getBaseNegativeForScene(scene);
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

  const handleGenerateSceneImage = async (scene: Scene) => {
    const fallbackPrompt = buildPositivePrompt(scene);
    if (!fallbackPrompt) {
      alert("Prompt is required");
      return;
    }
    updateScene(scene.id, { isGenerating: true });
    try {
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
      const hiResPayload = hiResEnabled
        ? {
            enable_hr: true,
            hr_scale: 1.5,
            hr_upscaler: "Latent",
            hr_second_pass_steps: 10,
            denoising_strength: 0.25,
          }
        : {};
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
      updateScene(scene.id, { debug_payload: JSON.stringify(debugPayload, null, 2) });
      updateScene(scene.id, { debug_prompt: prompt });
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
        updateScene(scene.id, { image_url: `data:image/png;base64,${res.data.image}` });
      }
    } catch {
      alert("Scene image generation failed");
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

  const computeValidationResults = () => {
    const hasAny = (text: string, list: string[]) =>
      list.some((keyword) => text.includes(keyword));

    const results: Record<number, SceneValidation> = {};
    let ok = 0;
    let warn = 0;
    let error = 0;

    scenes.forEach((scene) => {
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

  const handleAutoFixAll = () => {
    const { results, summary } = computeValidationResults();
    setValidationResults(results);
    setValidationSummary(summary);

    scenes.forEach((scene) => {
      const validation = results[scene.id];
      if (!validation || validation.status === "ok") return;
      const suggestions = getFixSuggestions(scene, validation);
      suggestions
        .filter((item) => item.action)
        .forEach((item) => applySuggestion(scene, item));
    });
    setTimeout(() => runValidation(), 0);
  };

  const getFixSuggestions = (scene: Scene, validation?: SceneValidation): FixSuggestion[] => {
    if (!validation) return [];
    const suggestions: FixSuggestion[] = [];
    const issueText = validation.issues.map((issue) => issue.message);
    const includes = (needle: string) => issueText.some((text) => text.includes(needle));

    if (includes("Script is empty")) {
      suggestions.push({
        id: "script-empty",
        message: "Add one short line of dialogue (monologue).",
      });
    }
    if (includes("Script is longer than 40 characters")) {
      suggestions.push({
        id: "script-long",
        message: "Shorten the script to 40 characters or fewer.",
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
        action: { type: "add_positive", tokens: ["plain background"] },
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
      tokens.forEach((token) => {
        if (!existingSet.has(token.toLowerCase())) {
          nextTokens.push(token);
        }
      });
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

  const getSceneStatus = (scene: Scene) => {
    if (!scene.image_url) return "Need Image";
    if (!imageValidationResults[scene.id]) return "Ready to Validate";
    return "Ready to Render";
  };

  const handleValidateImage = async (scene: Scene) => {
    if (!scene.image_url) {
      alert("Upload or generate an image first.");
      return;
    }
    const prompt = scene.debug_prompt || buildPositivePrompt(scene);
    try {
      const res = await axios.post(`${API_BASE}/scene/validate_image`, {
        image_b64: scene.image_url,
        prompt,
        mode: imageCheckMode,
      });
      setImageValidationResults((prev) => ({ ...prev, [scene.id]: res.data }));
    } catch {
      alert("Image validation failed");
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff3db,_#f7f1ff_45%,_#e6f7ff_100%)] text-zinc-900">
      <div className="relative overflow-hidden">
        <div className="absolute -top-40 -right-32 h-80 w-80 rounded-full bg-gradient-to-br from-amber-200 via-rose-200 to-fuchsia-200 blur-3xl opacity-70" />
        <div className="absolute top-40 -left-32 h-72 w-72 rounded-full bg-gradient-to-br from-sky-200 via-emerald-200 to-lime-200 blur-3xl opacity-60" />
        <main className="relative mx-auto flex w-full max-w-6xl flex-col gap-10 px-6 py-12">
          <header className="flex flex-col gap-4">
            <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Shorts MVP</p>
            <h1 className="text-4xl font-semibold tracking-tight text-zinc-900">
              Script-first storyboard studio
            </h1>
            <p className="max-w-2xl text-sm text-zinc-600">
              Start from a script, generate scene descriptions, then upload the exact images you want. The
              system only assembles and renders.
            </p>
            <Link
              href="/manage"
              className="w-fit rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 shadow-sm"
            >
              Manage
            </Link>
          </header>

          <div className="flex items-center gap-3">
            <span className="text-[10px] font-semibold uppercase tracking-[0.3em] text-zinc-500">
              Plan & Generate
            </span>
            <div className="h-px flex-1 bg-zinc-200/70" />
          </div>

          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Storyboard Generator</h2>
                <p className="text-xs text-zinc-500">Generate scene scripts and visual descriptions.</p>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-[1.5fr_1fr]">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">Topic</label>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  rows={4}
                  className="rounded-2xl border border-zinc-200 bg-white/80 p-4 text-sm shadow-inner outline-none focus:border-zinc-400"
                  placeholder="Enter your story topic or hook..."
                />
              </div>
              <div className="grid gap-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                      Duration (s)
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
                    <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                  <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                    Visual Style
                  </label>
                  <input
                    value={style}
                    onChange={(e) => setStyle(e.target.value)}
                    className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                  Tip: Base Prompt is identity/style. Scene prompts handle action, camera, and background.
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
                    onClick={() => setBaseTab(tab.id as "global" | "A" | "B")}
                    className={`rounded-full px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] transition ${
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
                <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600">
                  Auto Compose Prompt
                  <input
                    type="checkbox"
                    checked={autoComposePrompt}
                    onChange={(e) => setAutoComposePrompt(e.target.checked)}
                    className="h-4 w-4 accent-zinc-900"
                  />
                </label>
                <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600">
                  Auto Rewrite Prompt (Gemini)
                  <input
                    type="checkbox"
                    checked={autoRewritePrompt}
                    onChange={(e) => setAutoRewritePrompt(e.target.checked)}
                    className="h-4 w-4 accent-zinc-900"
                  />
                </label>
                <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600">
                  Hi-Res Fix (1.5x)
                  <input
                    type="checkbox"
                    checked={hiResEnabled}
                    onChange={(e) => setHiResEnabled(e.target.checked)}
                    className="h-4 w-4 accent-zinc-900"
                  />
                </label>
              </div>
            )}

            {baseTab === "A" && (
              <div className="grid gap-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
                    Actor A Setup
                  </span>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        (() => {
                          setBasePromptA(
                            "1girl, eureka, (black t-shirt:1.2), purple eyes, aqua hair, short hair, jeans, glasses, hairclip, short sleeves, <lora:eureka_v9:1.0>"
                          );
                          setBaseNegativePromptA("verybadimagenegative_v1.3");
                        })()
                      }
                      className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600"
                    >
                      Insert Sample
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsHelperOpen(true)}
                      className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600"
                    >
                      Prompt Helper
                    </button>
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                  <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                    Model tags like &lt;model:...&gt; are ignored. Use the SD Model selector instead.
                  </p>
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                    <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                    <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                    <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                    <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                    <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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

          <div className="flex justify-end">
            <button
              onClick={handleGenerateScenes}
              disabled={isGenerating || !topic.trim()}
              className="rounded-full bg-zinc-900 px-6 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white shadow-lg shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {isGenerating ? "Generating..." : "Generate"}
            </button>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[10px] font-semibold uppercase tracking-[0.3em] text-zinc-500">
              Scene Work
            </span>
            <div className="h-px flex-1 bg-zinc-200/70" />
          </div>

          <section className="grid gap-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Scenes</h2>
                <p className="text-xs text-zinc-500">Upload the exact images you want for each scene.</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-2 rounded-full border border-zinc-200 bg-white/80 px-3 py-2">
                  <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                    Image Check
                  </span>
                  <select
                    value={imageCheckMode}
                    onChange={(e) => setImageCheckMode(e.target.value as "local" | "gemini")}
                    className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-zinc-600"
                  >
                    <option value="local">Local (WD14)</option>
                    <option value="gemini">Gemini (Cloud)</option>
                  </select>
                </div>
                <button
                  onClick={runValidation}
                  className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white shadow"
                >
                  Validate
                </button>
                <button
                  onClick={handleAutoFixAll}
                  disabled={scenes.length === 0}
                  className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600 shadow disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Auto Fix All
                </button>
                <button
                  onClick={handleAddScene}
                  className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600 shadow"
                >
                  Add Scene
                </button>
              </div>
            </div>

            {(validationSummary.ok + validationSummary.warn + validationSummary.error > 0) && (
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-600">
                  OK {validationSummary.ok}
                </span>
                <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-600">
                  Warn {validationSummary.warn}
                </span>
                <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-600">
                  Error {validationSummary.error}
                </span>
              </div>
            )}

            <div className="grid gap-6">
              {scenes.map((scene) => (
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
                        className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${
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
                      onClick={() => handleRemoveScene(scene.id)}
                      className="text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-500"
                    >
                      Remove
                    </button>
                  </div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
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
                      className="w-fit rounded-full border border-zinc-300 bg-white/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600"
                    >
                      Fix Suggestions
                    </button>
                  )}
                  {validationResults[scene.id] && suggestionExpanded[scene.id] && (
                    <div className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-xs text-zinc-600">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                                className="mt-2 rounded-full border border-zinc-300 bg-white/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600"
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
                                      className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600"
                                    >
                                      Apply
                                    </button>
                                  ) : (
                                    <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-400">
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
                        <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                          <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                          <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                            Duration
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={10}
                            value={scene.duration}
                            onChange={(e) => updateScene(scene.id, { duration: Number(e.target.value) })}
                            className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                          />
                        </div>
                        <div className="flex flex-col gap-2">
                          <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                            Image
                          </label>
                          <label className="flex h-10 cursor-pointer items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white/80 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600">
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
                        <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                        <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                        <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                          <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                          <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                          <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                          <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                          <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
                    <button
                      type="button"
                      onClick={() => handleGenerateSceneImage(scene)}
                      disabled={scene.isGenerating}
                      className="rounded-full bg-zinc-900 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white shadow-md shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
                    >
                      {scene.isGenerating ? "Generating..." : "Generate Image"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleValidateImage(scene)}
                      disabled={!scene.image_url}
                      className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Validate Image
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        const basePrompt = getBasePromptForScene(scene);
                          const scenePrompt = scene.image_prompt;
                          const prompt = autoComposePrompt && basePrompt
                            ? `${basePrompt}, ${scenePrompt}`
                            : scenePrompt;
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
                      className="rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600"
                    >
                      Debug Payload
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setAdvancedExpanded((prev) => ({
                          ...prev,
                          [scene.id]: !prev[scene.id],
                        }))
                      }
                      className="w-fit rounded-full border border-zinc-300 bg-white/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600"
                    >
                      {advancedExpanded[scene.id] ? "Hide Advanced" : "Show Advanced"}
                    </button>
                    {advancedExpanded[scene.id] && scene.debug_payload && (
                      <textarea
                        value={scene.debug_payload}
                        readOnly
                        rows={6}
                        className="rounded-2xl border border-zinc-200 bg-zinc-50 p-3 text-[10px] text-zinc-500"
                      />
                    )}
                    {(validationResults[scene.id] || imageValidationResults[scene.id]) && (
                      <div className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-[11px] text-zinc-600">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                            Validation
                          </span>
                          {imageValidationResults[scene.id] && (
                            <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                              Match {Math.round(imageValidationResults[scene.id].match_rate * 100)}%
                            </span>
                          )}
                        </div>
                        {validationResults[scene.id] && (
                          <p className="mt-2 text-[11px] text-zinc-600">
                            {validationResults[scene.id].issues.length > 0
                              ? validationResults[scene.id].issues[0].message
                              : "No issues found."}
                          </p>
                        )}
                        {imageValidationResults[scene.id] && (
                          <div className="mt-2 grid gap-2">
                            {imageValidationResults[scene.id].missing.length > 0 && (
                              <div>
                                <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                                  Missing
                                </span>
                                <p className="text-zinc-600">
                                  {imageValidationResults[scene.id].missing.slice(0, 8).join(", ")}
                                </p>
                              </div>
                            )}
                            {imageValidationResults[scene.id].extra.length > 0 && (
                              <div>
                                <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                                  Extra Tags
                                </span>
                                <p className="text-zinc-600">
                                  {imageValidationResults[scene.id].extra.slice(0, 8).join(", ")}
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    {validationResults[scene.id] && (
                      <div className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-xs text-zinc-600">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                            Validation Details
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                setValidationExpanded((prev) => ({
                                  ...prev,
                                  [scene.id]: !prev[scene.id],
                                }))
                              }
                              className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500"
                            >
                              {validationExpanded[scene.id] ? "Hide" : "Show"}
                            </button>
                          </div>
                          {validationExpanded[scene.id] && (
                            <div className="mt-2 grid gap-1 text-[11px]">
                              {validationResults[scene.id].issues.length === 0 ? (
                                <span className="text-emerald-600">No issues found.</span>
                              ) : (
                                validationResults[scene.id].issues.map((issue, idx) => (
                                  <span
                                    key={`${scene.id}-issue-${idx}`}
                                    className={
                                      issue.level === "error" ? "text-rose-600" : "text-amber-600"
                                    }
                                  >
                                    {issue.message}
                                  </span>
                                ))
                              )}
                            </div>
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
                          <div className="flex h-full items-center justify-center">
                            <p className="text-xs text-zinc-400">No image uploaded</p>
                          </div>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-zinc-400">
                        <span>
                          {scene.image_url ? "Ready" : "Upload required"}
                        </span>
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
              ))}
            </div>
          </section>

          <div className="flex items-center gap-3">
            <span className="text-[10px] font-semibold uppercase tracking-[0.3em] text-zinc-500">
              Output
            </span>
            <div className="h-px flex-1 bg-zinc-200/70" />
          </div>

          <section className="grid gap-6 rounded-3xl border border-white/60 bg-white/70 p-6 shadow-xl shadow-slate-200/40 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Render Settings</h2>
                <p className="text-xs text-zinc-500">Control subtitles, narration, and background music.</p>
              </div>
            </div>

            <div className="grid gap-2">
              <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                SD Model
              </label>
              <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3">
                <span className="text-xs font-semibold text-zinc-600">
                  Current: {currentModel}
                </span>
                {isModelUpdating && (
                  <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
                    Updating...
                  </span>
                )}
                <select
                  value={selectedModel}
                  onChange={(e) => handleModelChange(e.target.value)}
                  disabled={isModelUpdating || sdModels.length === 0}
                  className="min-w-[220px] rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400 disabled:bg-zinc-100"
                >
                  {sdModels.length === 0 && <option value="">No models found</option>}
                  {sdModels.map((model) => (
                    <option key={model.title} value={model.title}>
                      {model.title}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-5">
              <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600">
                Include Subtitles
                <input
                  type="checkbox"
                  checked={includeSubtitles}
                  onChange={(e) => setIncludeSubtitles(e.target.checked)}
                  className="h-4 w-4 accent-zinc-900"
                />
              </label>
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  Narrator Voice
                </label>
                <select
                  value={narratorVoice}
                  onChange={(e) => setNarratorVoice(e.target.value)}
                  className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                >
                  {VOICES.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  BGM
                </label>
                <div className="flex items-center gap-2">
                  <select
                    value={bgmFile ?? ""}
                    onChange={(e) => setBgmFile(e.target.value || null)}
                    className="min-w-0 flex-1 truncate rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                  >
                    <option value="">None</option>
                    {bgmList.map((bgm) => (
                      <option key={bgm.name} value={bgm.name}>
                        {bgm.name}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => handlePreviewBgm()}
                    disabled={!bgmFile || isPreviewingBgm}
                    className="rounded-full border border-zinc-200 bg-white/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600 transition disabled:cursor-not-allowed disabled:text-zinc-400"
                  >
                    {isPreviewingBgm ? "Playing..." : "Preview 10s"}
                  </button>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  Scene Layout
                </label>
                <select
                  value={layoutStyle}
                  onChange={(e) => setLayoutStyle(e.target.value as "full" | "post")}
                  className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                >
                  <option value="full">Full (Blur Fill)</option>
                  <option value="post">Post (Square Center)</option>
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  Effects (Skillset)
                </label>
                <select
                  value={motionStyle}
                  onChange={(e) => setMotionStyle(e.target.value as "none" | "slow_zoom")}
                  className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                >
                  <option value="none">None</option>
                  <option value="slow_zoom">Slow Zoom</option>
                </select>
              </div>
            </div>

            <div className="grid gap-3">
              <label className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-600">
                SNS Overlay
                <input
                  type="checkbox"
                  checked={overlaySettings.enabled}
                  onChange={(e) => {
                    const enabled = e.target.checked;
                    if (enabled) {
                      const auto = buildOverlayContext();
                      setOverlaySettings((prev) => ({
                        ...prev,
                        enabled,
                        profile_name: prev.profile_name || auto.profile_name,
                        likes_count: prev.likes_count || auto.likes_count,
                        caption: prev.caption || auto.caption,
                      }));
                    } else {
                      setOverlaySettings((prev) => ({ ...prev, enabled }));
                    }
                  }}
                  className="h-4 w-4 accent-zinc-900"
                />
              </label>
              {overlaySettings.enabled && (
                <div className="grid gap-4">
                  <div className="grid gap-3 md:grid-cols-3">
                    {OVERLAY_STYLES.map((style) => {
                      const selected = overlaySettings.frame_style === style.id;
                      return (
                        <button
                          key={style.id}
                          type="button"
                          onClick={() =>
                            setOverlaySettings((prev) => ({ ...prev, frame_style: style.id }))
                          }
                          className={`flex flex-col gap-3 rounded-2xl border p-3 text-left transition ${
                            selected
                              ? "border-zinc-900 bg-zinc-900 text-white"
                              : "border-zinc-200 bg-white/80 text-zinc-700 hover:border-zinc-400"
                          }`}
                        >
                          <span className="text-[10px] font-semibold uppercase tracking-[0.2em]">
                            {style.label}
                          </span>
                          <div className="aspect-[9/16] w-full overflow-hidden rounded-xl bg-zinc-100">
                            <img
                              src={`${API_BASE}/assets/overlay/${style.id}`}
                              alt={`${style.label} frame`}
                              className="h-full w-full object-cover"
                            />
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="flex flex-col gap-2">
                      <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                        Profile Name
                      </label>
                      <input
                        value={overlaySettings.profile_name}
                        onChange={(e) =>
                          setOverlaySettings((prev) => ({ ...prev, profile_name: e.target.value }))
                        }
                        className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                        Likes
                      </label>
                      <input
                        value={overlaySettings.likes_count}
                        onChange={(e) =>
                          setOverlaySettings((prev) => ({ ...prev, likes_count: e.target.value }))
                        }
                        className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                        Caption
                      </label>
                      <input
                        value={overlaySettings.caption}
                        onChange={(e) =>
                          setOverlaySettings((prev) => ({ ...prev, caption: e.target.value }))
                        }
                        className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                Read Speed ({speedMultiplier.toFixed(2)}x)
              </label>
              <input
                type="range"
                min={0.8}
                max={1.5}
                step={0.05}
                value={speedMultiplier}
                onChange={(e) => setSpeedMultiplier(Number(e.target.value))}
                className="w-full accent-zinc-900"
              />
            </div>

            {!canRender && scenes.length > 0 && (
              <p className="text-xs text-rose-500">Upload images for every scene to enable rendering.</p>
            )}
            <div className="flex justify-end">
              <button
                onClick={handleRenderVideo}
                disabled={!canRender || isRendering}
                className="rounded-full bg-zinc-900 px-5 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white shadow-lg shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
              >
                {isRendering ? "Rendering..." : "Render Video"}
              </button>
            </div>
          </section>

          {videoUrl && (
            <section className="grid gap-4 rounded-3xl border border-white/60 bg-white/80 p-6 shadow-xl shadow-slate-200/40">
              <div>
                <h2 className="text-lg font-semibold text-zinc-900">Rendered Video</h2>
                <p className="text-xs text-zinc-500">Preview the latest render.</p>
              </div>
              <div className="w-full max-w-sm sm:max-w-md md:max-w-lg lg:max-w-xl">
                <div className="aspect-[9/16] w-full overflow-hidden rounded-2xl bg-black shadow">
                  <video controls src={videoUrl} className="h-full w-full object-cover" />
                </div>
              </div>
            </section>
          )}
        </main>
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
                <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  Image Preview
                </span>
                <button
                  type="button"
                  onClick={() => setImagePreviewSrc(null)}
                  className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500"
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
      <div
        className={`fixed inset-0 z-40 bg-black/30 transition-opacity ${isHelperOpen ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={() => setIsHelperOpen(false)}
      />
      <aside
        className={`fixed right-0 top-0 z-50 h-full w-full max-w-md transform bg-white shadow-2xl transition-transform ${isHelperOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="flex h-full flex-col gap-4 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Prompt Helper</p>
              <h3 className="text-lg font-semibold text-zinc-900">Split Example Prompt</h3>
            </div>
            <button
              type="button"
              onClick={() => setIsHelperOpen(false)}
              className="rounded-full border border-zinc-200 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500"
            >
              Close
            </button>
          </div>
          {copyStatus && (
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              {copyStatus}
            </div>
          )}
          <div className="grid gap-2">
            <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
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
              className="rounded-full bg-zinc-900 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white shadow-md shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {isSuggesting ? "Suggesting..." : "Suggest Base/Scene"}
            </button>
          </div>
          {(suggestedBase || suggestedScene) && (
            <div className="grid gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                    Suggested Base
                  </label>
                  <button
                    type="button"
                    onClick={() => copyText(suggestedBase)}
                    className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500"
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
                  <label className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                    Suggested Scene
                  </label>
                  <button
                    type="button"
                    onClick={() => copyText(suggestedScene)}
                    className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500"
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
    </div>
  );
}
