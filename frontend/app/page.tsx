"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { 
  Loader2, Wand2, Palette, Dices, Monitor, Smartphone, 
  Sparkles, ImageIcon, Clapperboard, 
  User, Clock, Trash2, UserCircle, RefreshCw, Volume2, Download, 
  CheckCircle2, Globe, Play, Save, History, Boxes, Eye, X, Settings2,
  PlayCircle, PauseCircle, Layout, Mic,
  Upload
} from "lucide-react";
import Image from "next/image";

// --- Constants ---
const API_BASE = "http://localhost:8000";
const STYLE_PRESETS = [
  "Studio Ghibli",
  "Makoto Shinkai",
  "Korean Webtoon",
  "Romance Fantasy Webtoon",
  "Manhwa Style",
  "Vintage Anime (90s)",
  "Chibi",
  "Photorealistic",
  "Cyberpunk",
  "Unreal Engine 5",
  "Watercolor",
  "Flat Design (Vector)",
  "Pixel Art",
  "Oil Painting",
  "Cinematic",
  "3D Render"
];

const SAMPLER_PRESETS = [
  "DPM++ 2M Karras",
  "DPM++ SDE Karras",
  "DPM++ 2M SDE Karras",
  "Euler a",
  "DDIM"
];

const SAMPLE_PERSONAS = [
  "주황색 머리에 파란 눈을 가진 장난기 가득한 7살 소년",
  "은색 갑옷을 입고 빛나는 검을 든 고귀한 기사",
  "안경을 쓰고 책을 든 지적인 분위기의 어린 마법사",
  "분홍색 원피스를 입고 숲속을 뛰어노는 귀여운 소녀",
  "미래 기술이 접목된 의상을 입은 사이버펑크 스타일의 해커",
  "하얀 가운을 입고 실험 도구를 든 엉뚱한 과학자 고양이",
  "망토를 두르고 밤거리를 지키는 용감한 꼬마 영웅",
  "화려한 한복을 입고 부채를 든 우아한 선녀"
];

const RESOLUTIONS = {
  shorts: { w: 512, h: 512, label: "YouTube Shorts (9:16)", desc: "Stable Gen @ 512px" },
};
const DEFAULT_NEGATIVE_PROMPT = "low quality, worst quality, bad anatomy, deformed, text, watermark, signature, ugly";

type StoryScene = {
  image_url?: string | null;
  image_prompt: string;
  image_prompt_ko?: string;
  negative_prompt?: string;
  script: string;
  duration: number;
  visual_focus?: "A" | "B" | "Both" | "Landscape";
  speaker?: "A" | "B" | "Narrator";
  ref_used_a?: boolean;
  ref_used_b?: boolean;
};

type Project = {
  id: string;
  title: string;
  updated_at: number;
};

type BgmItem = {
  name: string;
  url: string;
};

type VideoItem = {
  name: string;
  url: string;
};

interface Character {
  id: number;
  role: string;
  desc: string;
  translatedDesc: string;
  image: string | null;
  reference_image: string | null; // Added for IP-Adapter
  seed_image: string | null;
  reference_images_face: string[];
  reference_images_body: string[];
  reference_loading_kind: "face" | "body" | null;
  face_detected: boolean | null;
  face_count: number | null;
  voice: string;
  seed: number;
  reference_seed_face: number;
  reference_seed_body: number;
  isTranslating: boolean;
  isLoading: boolean;
}

export default function Home() {
  // --- UI States ---
  const [showProjectList, setShowProjectList] = useState(false); // Project Browser Modal State
  const [activeStep, setActiveStep] = useState<"cast" | "scene">("cast");
  const [castLocked, setCastLocked] = useState(false);
  
  // --- Global Settings ---
  const [selectedStyles, setSelectedStyles] = useState<string[]>([]);
  const [resolution, setResolution] = useState<keyof typeof RESOLUTIONS>("shorts");
  const [selectedLora, setSelectedLora] = useState<string[]>([]);
  const [narratorVoice, setNarratorVoice] = useState("ko-KR-SunHiNeural"); // Default Narrator

  // --- Logic States ---
  const [projectId, setProjectId] = useState<string | null>(null);
  const [storyTopic, setStoryTopic] = useState("");
  const [storyDuration, setStoryDuration] = useState(30);
  const [storyLanguage, setStoryLanguage] = useState("Korean");
  const [storyStructure, setStoryStructure] = useState("Free Flow"); // New state
  const [overlaySettings, setOverlaySettings] = useState({
    enabled: true,
    profile_name: "Daily_Romance",
    likes_count: "12.5k",
    caption: "설레는 순간들... #럽스타그램"
  });
  const [runtimeSteps, setRuntimeSteps] = useState(30);
  const [runtimeCfgScale, setRuntimeCfgScale] = useState(7);
  const [runtimeSampler, setRuntimeSampler] = useState("DPM++ 2M Karras");
  const [useIpAdapter, setUseIpAdapter] = useState(true);
  const [strictIdentity, setStrictIdentity] = useState(true);
  const [storyScenes, setStoryScenes] = useState<StoryScene[]>([]);
  const [batchNegative, setBatchNegative] = useState(DEFAULT_NEGATIVE_PROMPT);
  const [isBatchOpen, setIsBatchOpen] = useState(false);
  
  // New Multi-Character State
  const [characters, setCharacters] = useState<Character[]>([
    { id: 0, role: "Actor A (Main)", desc: "", translatedDesc: "", image: null, reference_image: null, seed_image: null, reference_images_face: [], reference_images_body: [], reference_loading_kind: null, face_detected: null, face_count: null, voice: "ko-KR-SunHiNeural", seed: -1, reference_seed_face: -1, reference_seed_body: -1, isTranslating: false, isLoading: false },
    { id: 1, role: "Actor B (Side)", desc: "", translatedDesc: "", image: null, reference_image: null, seed_image: null, reference_images_face: [], reference_images_body: [], reference_loading_kind: null, face_detected: null, face_count: null, voice: "ko-KR-InJoonNeural", seed: -1, reference_seed_face: -1, reference_seed_body: -1, isTranslating: false, isLoading: false }
  ]);

  const [isStoryLoading, setIsStoryLoading] = useState(false);
  const [isAutopilotRunning, setIsAutopilotRunning] = useState(false);
  const [autopilotProgress, setAutopilotProgress] = useState(0);
  const [isVideoLoading, setIsVideoLoading] = useState(false);
  const [videoStatus, setVideoStatus] = useState("");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);
  const [previewLoadingIndex, setPreviewLoadingIndex] = useState<number | null>(null);
  const [isRandomLoading, setIsRandomLoading] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadingCharIdx, setUploadingCharIdx] = useState<number | null>(null);

  const [projects, setProjects] = useState<Project[]>([]);
  const [bgmList, setBgmList] = useState<BgmItem[]>([]);
  const [selectedBgm, setSelectedBgm] = useState("");
  const [producedVideos, setProducedVideos] = useState<VideoItem[]>([]);
  const [lorasList, setLorasList] = useState<string[]>([]);
  const [loraSearch, setLoraSearch] = useState("");
  const [currentModel, setCurrentModel] = useState<string>("Loading...");
  const [webuiSettings, setWebuiSettings] = useState<{ model: string; options: Record<string, unknown> } | null>(null);
  const [isWebuiSettingsLoading, setIsWebuiSettingsLoading] = useState(false);
  const [webuiSettingsError, setWebuiSettingsError] = useState<string | null>(null);
  const [controlnetSettings, setControlnetSettings] = useState<{ webui?: Record<string, unknown>; preset?: Record<string, { module: string; model: string; weight: number }[]>; runtime_settings?: Record<string, unknown>; error?: string } | null>(null);
  const [isControlnetLoading, setIsControlnetLoading] = useState(false);
  const [controlnetError, setControlnetError] = useState<string | null>(null);
  const [playingBgm, setPlayingBgm] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const bgmPlayerRef = useRef<HTMLAudioElement | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [loras, webui, controlnet, audios, vids, projs] = await Promise.all([
        axios.get(`${API_BASE}/loras`).catch(() => ({ data: { loras: [] } })),
        axios.get(`${API_BASE}/settings/webui`).catch(() => ({ data: { model: "Offline", options: {} } })),
        axios.get(`${API_BASE}/settings/controlnet`).catch(() => ({ data: { webui: {}, preset: {} } })),
        axios.get(`${API_BASE}/audio/list`).catch(() => ({ data: { audios: [] } })),
        axios.get(`${API_BASE}/video/list`).catch(() => ({ data: { videos: [] } })),
        axios.get(`${API_BASE}/projects/list`).catch(() => ({ data: { projects: [] } }))
      ]);
      setLorasList(loras.data.loras || []);
      setCurrentModel(webui.data.model || "Unknown");
      setWebuiSettings(webui.data || null);
      setWebuiSettingsError(null);
      setControlnetSettings(controlnet.data || null);
      setControlnetError(null);
      setBgmList(audios.data.audios || []);
      setProducedVideos(vids.data.videos || []);
      setProjects(projs.data.projects || []);
    } catch {
      setCurrentModel("Disconnected");
      setWebuiSettingsError("WebUI sync failed");
      setControlnetError("ControlNet sync failed");
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const fetchWebuiSettings = async () => {
    setIsWebuiSettingsLoading(true);
    setWebuiSettingsError(null);
    try {
      const res = await axios.get(`${API_BASE}/settings/webui`);
      setWebuiSettings(res.data || null);
      setCurrentModel(res.data?.model || "Unknown");
    } catch {
      setWebuiSettingsError("WebUI reload failed");
    } finally {
      setIsWebuiSettingsLoading(false);
    }
  };

  const fetchControlnetSettings = async () => {
    setIsControlnetLoading(true);
    setControlnetError(null);
    try {
      const res = await axios.get(`${API_BASE}/settings/controlnet`);
      setControlnetSettings(res.data || null);
    } catch {
      setControlnetError("ControlNet reload failed");
    } finally {
      setIsControlnetLoading(false);
    }
  };

  const getControlnetVersion = () => {
    const version = controlnetSettings?.webui?.["version"];
    return version ? String(version) : "-";
  };

  const getControlnetUnitCount = () => {
    const runtime = controlnetSettings?.runtime_settings || {};
    const candidates = [
      runtime["control_net_unit_count"],
      runtime["unit_count"],
      runtime["num_units"]
    ];
    const value = candidates.find((item) => item !== undefined && item !== null);
    return value !== undefined && value !== null ? String(value) : "-";
  };

  const computeSharpness = (dataUrl: string): Promise<number> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const size = 256;
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(0);
          return;
        }
        ctx.drawImage(img, 0, 0, size, size);
        const { data } = ctx.getImageData(0, 0, size, size);
        let sum = 0;
        let sumSq = 0;
        const idx = (x: number, y: number) => (y * size + x) * 4;
        for (let y = 1; y < size - 1; y++) {
          for (let x = 1; x < size - 1; x++) {
            const i = idx(x, y);
            const c = (data[i] + data[i + 1] + data[i + 2]) / 3;
            const l = (data[idx(x - 1, y)] + data[idx(x - 1, y) + 1] + data[idx(x - 1, y) + 2]) / 3;
            const r = (data[idx(x + 1, y)] + data[idx(x + 1, y) + 1] + data[idx(x + 1, y) + 2]) / 3;
            const u = (data[idx(x, y - 1)] + data[idx(x, y - 1) + 1] + data[idx(x, y - 1) + 2]) / 3;
            const d = (data[idx(x, y + 1)] + data[idx(x, y + 1) + 1] + data[idx(x, y + 1) + 2]) / 3;
            const lap = (4 * c) - l - r - u - d;
            sum += lap;
            sumSq += lap * lap;
          }
        }
        const n = (size - 2) * (size - 2);
        const variance = sumSq / n - (sum / n) * (sum / n);
        resolve(variance);
      };
      img.onerror = () => resolve(0);
      img.src = dataUrl;
    });
  };

  const sortImagesBySharpness = async (images: string[]) => {
    const scores = await Promise.all(images.map(async (img) => ({ img, score: await computeSharpness(img) })));
    scores.sort((a, b) => b.score - a.score);
    return scores.map((item) => item.img);
  };

  const getRuntimeUnits = () => {
    const runtime = controlnetSettings?.runtime_settings || {};
    const candidates = [
      runtime["control_net_units"],
      runtime["units"],
      runtime["controlnet_units"],
      runtime["control_net_unit_settings"]
    ];
    const units = candidates.find((item) => Array.isArray(item));
    return Array.isArray(units) ? (units as Record<string, unknown>[]) : [];
  };

  const getUnitValue = (unit: Record<string, unknown>, key: string) => {
    const value = unit[key];
    if (value === undefined || value === null || value === "") return "-";
    return String(value);
  };

  const getUnitFields = (unit: Record<string, unknown>) => {
    const keys = [
      "enabled",
      "module",
      "model",
      "weight",
      "guidance_start",
      "guidance_end",
      "pixel_perfect",
      "control_mode",
      "resize_mode",
      "processor_res",
      "threshold_a",
      "threshold_b",
      "lowvram",
      "save_detected_map",
      "guess_mode",
      "hr_option",
      "mask",
      "invert"
    ];
    return keys
      .map((key) => ({ key, value: getUnitValue(unit, key) }))
      .filter((item) => item.value !== "-");
  };

  const getWebuiOption = (key: string) => {
    const value = webuiSettings?.options?.[key];
    if (value === undefined || value === null || value === "") return "-";
    return String(value);
  };


  const toggleStyle = (style: string) => {
    setSelectedStyles(prev => prev.includes(style) ? prev.filter(s => s !== style) : [...prev, style]);
  };

  const updateCharacter = (idx: number, field: keyof Character, value: Character[keyof Character]) => {
    setCharacters(prev => {
        const newChars = [...prev];
        newChars[idx] = { ...newChars[idx], [field]: value };
        return newChars;
    });
  };

  const setReferenceImage = (idx: number, dataUrl: string | null) => {
    updateCharacter(idx, "reference_image", dataUrl);
    updateCharacter(idx, "seed_image", dataUrl);
    if (!dataUrl) {
      updateCharacter(idx, "face_detected", null);
      updateCharacter(idx, "face_count", null);
    }
  };

  const setSeedReference = (idx: number, dataUrl: string) => {
    updateCharacter(idx, "seed_image", dataUrl);
    updateCharacter(idx, "reference_image", dataUrl);
    updateCharacter(idx, "face_detected", null);
    updateCharacter(idx, "face_count", null);
  };

  const setPrimaryReference = (idx: number, dataUrl: string) => {
    const char = characters[idx];
    const nextImages = char.reference_images_face.includes(dataUrl)
      ? char.reference_images_face
      : [...char.reference_images_face, dataUrl];
    updateCharacter(idx, "reference_images_face", nextImages);
    updateCharacter(idx, "reference_image", dataUrl);
  };

  const buildFaceReferencePrompts = (char: Character) => {
    const baseRaw = (char.translatedDesc || char.desc || "").trim();
    const base = baseRaw
      .replace(/\b(front[- ]facing|facing the camera|looking at (the )?viewer|looking at (the )?camera|standing|full body|head-to-toe|long shot|wide shot)\b/gi, "")
      .replace(/\s{2,}/g, " ")
      .replace(/\s+,/g, ",")
      .trim();
    const styles = selectedStyles.length ? `, ${selectedStyles.join(", ")}` : "";
    const anchor = base ? `${base}, same person, single person, solo, one person only` : "same person, single person, solo, one person only";
    return [
      `${anchor}, front view, front-facing, looking at camera, both eyes visible, symmetrical face, square shoulders, close-up portrait, tight close-up, head and shoulders only, crop at shoulders, face centered, face occupies 50 percent of frame, hands not visible, no hands, sharp focus, plain background${styles}`,
      `${anchor}, left side headshot, perfect profile, left profile, facing left, looking left, only one eye visible, one ear visible, nose profile, tight close-up, head and shoulders only, crop at shoulders, face occupies 50 percent of frame, hands not visible, no hands, plain background${styles}`,
      `${anchor}, right side headshot, perfect profile, right profile, facing right, looking right, only one eye visible, one ear visible, nose profile, tight close-up, head and shoulders only, crop at shoulders, face occupies 50 percent of frame, hands not visible, no hands, plain background${styles}`,
      `${anchor}, back view, rear view, facing away, back of head only, nape visible, no face visible, no eyes visible, no nose visible, square shoulders, back straight, tight close-up, head and shoulders only, crop at shoulders, centered composition, hands not visible, no hands, plain background${styles}`
    ];
  };

  const buildBodyReferencePrompts = (char: Character) => {
    const base = (char.translatedDesc || char.desc || "").trim();
    const styles = selectedStyles.length ? `, ${selectedStyles.join(", ")}` : "";
    const anchor = base ? `${base}, same person, single person, solo, one person only` : "same person, single person, solo, one person only";
    return [
      `${anchor}, full body, head-to-toe, long shot, front view, front-facing, standing, attention pose, upright posture, feet together, square shoulders, back straight, arms straight at sides, centered, no occlusion, hands visible, five fingers, anatomically correct hands, plain background${styles}`,
      `${anchor}, full body, head-to-toe, long shot, left side view, left profile, facing left, left ear visible, attention pose, upright posture, feet together, arms straight at sides, hands visible, five fingers, anatomically correct hands, centered, no occlusion, plain background${styles}`,
      `${anchor}, full body, head-to-toe, long shot, right side view, right profile, facing right, right ear visible, attention pose, upright posture, feet together, arms straight at sides, hands visible, five fingers, anatomically correct hands, centered, no occlusion, plain background${styles}`,
      `${anchor}, full body, head-to-toe, long shot, back view, rear view, facing away, back of head visible, no face visible, shoulder blades visible, square shoulders, back straight, attention pose, upright posture, feet together, arms straight at sides, centered, no occlusion, hands visible, five fingers, anatomically correct hands, plain background${styles}`
    ];
  };

  const generateReferenceImages = async (idx: number, kind: "face" | "body") => {
    const char = characters[idx];
    const seedImage = char.seed_image || char.reference_image;
    if (!seedImage) {
      alert("기준 얼굴 이미지를 먼저 업로드해주세요.");
      return;
    }
    updateCharacter(idx, "reference_loading_kind", kind);
    const prompts = kind === "face"
      ? buildFaceReferencePrompts(char)
      : buildBodyReferencePrompts(char);
    if (!prompts.length) return;
    const seedField = kind === "face" ? "reference_seed_face" : "reference_seed_body";
    const existingSeed = kind === "face" ? char.reference_seed_face : char.reference_seed_body;
    const baseSeed = existingSeed === -1 ? Math.floor(Math.random() * 1_000_000_000) : existingSeed;
    if (existingSeed === -1) {
      updateCharacter(idx, seedField as keyof Character, baseSeed);
    }
    updateCharacter(idx, "isLoading", true);
    try {
      const singlePersonNegative = "(multiple people:1.7), (two people:1.7), (group:1.6), (crowd:1.6), (duplicate:1.5), (twins:1.5), (clone:1.5), extra person, extra face, extra head, extra body, extra torso";
      const anatomyNegative = "(bad hands:1.4), (bad fingers:1.4), (missing fingers:1.4), (extra fingers:1.4), (fused fingers:1.4), (deformed hands:1.4), (malformed hands:1.4), (extra limbs:1.4), (extra legs:1.5), (three legs:1.5), (missing legs:1.4), (deformed legs:1.4)";
      const backgroundNegative = "(busy background:1.4), (complex background:1.4), (cluttered background:1.4), (detailed background:1.3), (patterned background:1.3), (text:1.6), (letters:1.6), (words:1.6), (watermark:1.6), (logo:1.6), (signage:1.6), (subtitle:1.5), (caption:1.5), (speech bubble:1.5), (typography:1.5)";
      const faceAngleNegatives = [
        "back view, rear view, side view, profile, three-quarter view, facing away",
        "front view, front-facing, facing camera, looking at viewer, right side view, three-quarter view, back view, rear view",
        "front view, front-facing, facing camera, looking at viewer, left side view, three-quarter view, back view, rear view",
        "front view, side view, profile, three-quarter view, face visible, eyes visible, nose visible, mouth visible"
      ];
      const bodyAngleNegatives = [
        "back view, rear view, side view, left profile, right profile, three-quarter view",
        "front view, right side view, right profile, back view, rear view",
        "front view, left side view, left profile, back view, rear view",
        "front view, left side view, right side view, profile, three-quarter view, face visible"
      ];
      const faceBase = `${singlePersonNegative}, ${anatomyNegative}, ${backgroundNegative}, (hands:1.7), (hands visible:1.7), (fingers:1.7), (arms:1.6), (forearms:1.6), (deformed arms:1.7), (bad arms:1.6), (deformed fingers:1.7), (mutated hands:1.7), full body, full length, head-to-toe, long shot, wide shot, extreme angle, tilted head, occluded face, face covered`;
      const bodyBase = `${singlePersonNegative}, ${anatomyNegative}, ${backgroundNegative}, (deformed arms:1.7), (bad arms:1.6), (deformed fingers:1.7), (mutated hands:1.7), action pose, dynamic pose, running, jumping, crouching, close-up, cropped, out of frame, head cut off, body cut off, half body, extreme angle, duplicated legs, extra limb`;
      const images: string[] = [];
      for (const prompt of prompts) {
        const slot = images.length;
        const angleNegative = kind === "face"
          ? faceAngleNegatives[slot] || ""
          : bodyAngleNegatives[slot] || "";
        const weight = kind === "face" ? (slot === 0 ? 0.85 : slot === 3 ? 0.15 : 0.08) : 0.85;
        const seed = kind === "face" ? baseSeed + slot * 997 : baseSeed;
        const res = await axios.post(`${API_BASE}/character/reference_single`, {
          prompt,
          width: kind === "face" ? 768 : 768,
          height: kind === "face" ? 768 : 1024,
          styles: selectedStyles,
          negative_prompt: `${kind === "face" ? faceBase : bodyBase}, ${angleNegative}`.trim(),
          seed,
          reference_image: seedImage,
          use_ip_adapter: true,
          ip_adapter_weight: weight
        });
        if (res.data.image) {
          const dataUrl = `data:image/png;base64,${res.data.image}`;
          images.push(dataUrl);
          if (kind === "face") {
            updateCharacter(idx, "reference_images_face", [...images]);
          } else {
            updateCharacter(idx, "reference_images_body", [...images]);
          }
        }
      }
      if (kind === "body" && images.length > 1) {
        const sorted = await sortImagesBySharpness(images);
        updateCharacter(idx, "reference_images_body", sorted);
      }
    } catch {
      alert("Batch portrait generation failed");
    } finally {
      updateCharacter(idx, "reference_loading_kind", null);
      updateCharacter(idx, "isLoading", false);
    }
  };

  const generateAllReferenceSets = async (idx: number) => {
    await generateReferenceImages(idx, "face");
    await generateReferenceImages(idx, "body");
  };

  const regenerateReferenceImage = async (idx: number, kind: "face" | "body", slot: number) => {
    const char = characters[idx];
    const seedImage = char.seed_image || char.reference_image;
    if (!seedImage) {
      alert("기준 얼굴 이미지를 먼저 업로드해주세요.");
      return;
    }
    updateCharacter(idx, "reference_loading_kind", kind);
    const prompts = kind === "face"
      ? buildFaceReferencePrompts(char)
      : buildBodyReferencePrompts(char);
    if (!prompts[slot]) return;
    const seedField = kind === "face" ? "reference_seed_face" : "reference_seed_body";
    const existingSeed = kind === "face" ? char.reference_seed_face : char.reference_seed_body;
    const baseSeed = existingSeed === -1 ? Math.floor(Math.random() * 1_000_000_000) : existingSeed;
    if (existingSeed === -1) {
      updateCharacter(idx, seedField as keyof Character, baseSeed);
    }
    updateCharacter(idx, "isLoading", true);
    try {
      const singlePersonNegative = "(multiple people:1.7), (two people:1.7), (group:1.6), (crowd:1.6), (duplicate:1.5), (twins:1.5), (clone:1.5), extra person, extra face, extra head, extra body, extra torso";
      const anatomyNegative = "(bad hands:1.4), (bad fingers:1.4), (missing fingers:1.4), (extra fingers:1.4), (fused fingers:1.4), (deformed hands:1.4), (malformed hands:1.4), (extra limbs:1.4), (extra legs:1.5), (three legs:1.5), (missing legs:1.4), (deformed legs:1.4)";
      const backgroundNegative = "(busy background:1.4), (complex background:1.4), (cluttered background:1.4), (detailed background:1.3), (patterned background:1.3), (text:1.6), (letters:1.6), (words:1.6), (watermark:1.6), (logo:1.6), (signage:1.6), (subtitle:1.5), (caption:1.5), (speech bubble:1.5), (typography:1.5)";
      const faceAngleNegatives = [
        "back view, rear view, side view, profile",
        "front view, right side view, back view, rear view",
        "front view, left side view, back view, rear view",
        "front view, side view, profile, face visible"
      ];
      const bodyAngleNegatives = [
        "back view, rear view, side view, profile",
        "front view, right side view, back view, rear view",
        "front view, left side view, back view, rear view",
        "front view, left side view, right side view"
      ];
      const faceBase = `${singlePersonNegative}, ${anatomyNegative}, ${backgroundNegative}, (hands:1.7), (hands visible:1.7), (fingers:1.7), (arms:1.6), (forearms:1.6), (deformed arms:1.7), (bad arms:1.6), (deformed fingers:1.7), (mutated hands:1.7), full body, full length, head-to-toe, long shot, wide shot, extreme angle, tilted head, occluded face, face covered`;
      const bodyBase = `${singlePersonNegative}, ${anatomyNegative}, ${backgroundNegative}, (deformed arms:1.7), (bad arms:1.6), (deformed fingers:1.7), (mutated hands:1.7), action pose, dynamic pose, running, jumping, crouching, close-up, cropped, out of frame, head cut off, body cut off, half body, extreme angle, duplicated legs, extra limb`;
      const angleNegative = kind === "face"
        ? (faceAngleNegatives[slot] || "")
        : (bodyAngleNegatives[slot] || "");
      const weight = kind === "face" ? (slot === 0 ? 0.85 : slot === 3 ? 0.15 : 0.08) : 0.85;
      const seed = kind === "face" ? baseSeed + slot * 997 + Math.floor(Math.random() * 13) : baseSeed + Math.floor(Math.random() * 97);
      const res = await axios.post(`${API_BASE}/character/reference_single`, {
        prompt: prompts[slot],
        width: kind === "face" ? 768 : 768,
        height: kind === "face" ? 768 : 1024,
        styles: selectedStyles,
        negative_prompt: `${kind === "face" ? faceBase : bodyBase}, ${angleNegative}`.trim(),
        seed,
        reference_image: seedImage,
        use_ip_adapter: true,
        ip_adapter_weight: weight
      });
      if (res.data.image) {
        const dataUrl = `data:image/png;base64,${res.data.image}`;
        if (kind === "face") {
          const next = [...char.reference_images_face];
          next[slot] = dataUrl;
          updateCharacter(idx, "reference_images_face", next);
        } else {
          const next = [...char.reference_images_body];
          next[slot] = dataUrl;
          updateCharacter(idx, "reference_images_body", next);
        }
      }
    } catch {
      alert("Regenerate failed");
    } finally {
      updateCharacter(idx, "reference_loading_kind", null);
      updateCharacter(idx, "isLoading", false);
    }
  };

  const setRandomPersona = (idx: number) => {
    const random = SAMPLE_PERSONAS[Math.floor(Math.random() * SAMPLE_PERSONAS.length)];
    updateCharacter(idx, "desc", random);
  };

  const setRandomPrompt = async () => {
    setIsRandomLoading(true);
    try {
        const response = await axios.get(`${API_BASE}/random-prompt`);
        setStoryTopic(response.data.prompt);
    } catch {
        setStoryTopic("");
    } finally {
        setIsRandomLoading(false);
    }
  };

  const handleSaveProject = async () => {
    if (!storyTopic && storyScenes.length === 0) return;
    try {
        const res = await axios.post(`${API_BASE}/projects/save`, {
            id: projectId, title: storyTopic || "Untitled",
            data: { storyTopic, storyDuration, storyLanguage, storyScenes, characters, narratorVoice, selectedStyles, aspectRatio: resolution, selectedLora, overlaySettings }
        });
        setProjectId(res.data.id); fetchData(); alert("Saved!");
    } catch { alert("Save failed"); }
  };

  const handleLoadProject = async (id: string) => {
    try {
        const res = await axios.get(`${API_BASE}/projects/${id}`);
        const c = res.data.content;
        setProjectId(res.data.id);
        setStoryTopic(c.storyTopic); setStoryDuration(c.storyDuration); setStoryLanguage(c.storyLanguage);
        const fallbackNegative = c.negativePrompt || DEFAULT_NEGATIVE_PROMPT;
        setStoryScenes(
          (c.storyScenes || []).map((scene: StoryScene) => ({
            ...scene,
            negative_prompt: scene.negative_prompt || fallbackNegative
          }))
        );
        if (c.characters) {
            setCharacters(
              c.characters.map((char: Character) => ({
                ...char,
                reference_images_face: char.reference_images_face || [],
                reference_images_body: char.reference_images_body || [],
                reference_image: char.reference_image || null,
                seed_image: char.seed_image || char.reference_image || null,
                reference_loading_kind: null,
                face_detected: typeof char.face_detected === "boolean" ? char.face_detected : null,
                face_count: typeof char.face_count === "number" ? char.face_count : null,
                reference_seed_face: typeof char.reference_seed_face === "number" ? char.reference_seed_face : -1,
                reference_seed_body: typeof char.reference_seed_body === "number" ? char.reference_seed_body : -1
              }))
            );
        }
        if (c.narratorVoice) setNarratorVoice(c.narratorVoice);
        setSelectedStyles(c.selectedStyles || []); setResolution(c.aspectRatio || "shorts");
        if (Array.isArray(c.selectedLora)) {
            setSelectedLora(c.selectedLora);
        } else if (typeof c.selectedLora === "string" && c.selectedLora) {
            setSelectedLora([c.selectedLora]);
        } else {
            setSelectedLora([]);
        }
        if (c.overlaySettings) setOverlaySettings(c.overlaySettings);
    } catch { alert("Load failed"); }
  };

  const handleTranslateActor = async (idx: number) => {
    const char = characters[idx];
    if (!char.desc) return;
    updateCharacter(idx, "isTranslating", true);
    try {
        const res = await axios.post(`${API_BASE}/prompt/translate`, {
            text: char.desc,
            styles: selectedStyles
        });
        updateCharacter(idx, "translatedDesc", res.data.translated_prompt);
    } catch (e) { console.error(e); alert("Translation failed"); } 
    finally { updateCharacter(idx, "isTranslating", false); }
  };

  const checkFaceDetection = async (idx: number, image: string) => {
    try {
      const res = await axios.post(`${API_BASE}/face/check`, { image });
      updateCharacter(idx, "face_detected", !!res.data.has_face);
      updateCharacter(idx, "face_count", typeof res.data.faces === "number" ? res.data.faces : null);
    } catch {
      updateCharacter(idx, "face_detected", null);
      updateCharacter(idx, "face_count", null);
    }
  };

  const analyzeCharacter = async (idx: number, image: string) => {
    updateCharacter(idx, "isTranslating", true);
    try {
        const res = await axios.post(`${API_BASE}/character/analyze`, { image });
        if (res.data.description) {
            updateCharacter(idx, "desc", res.data.description);
        }
    } catch (e) { console.error("Analysis failed", e); } 
    finally { updateCharacter(idx, "isTranslating", false); }
  };

  const handleReferenceUpload = (idx: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      setSeedReference(idx, result);
      void checkFaceDetection(idx, result);
      // Automatically analyze the uploaded face to update text description
      analyzeCharacter(idx, result);
    };
    reader.readAsDataURL(file);
  };

  const handleGeneratePortrait = async (idx: number) => {
    const char = characters[idx];
    if (!char.desc) return;
    updateCharacter(idx, "isLoading", true);
    try {
        const tr = await axios.post(`${API_BASE}/prompt/translate`, {
            text: char.desc,
            styles: selectedStyles
        });
        const portraitDesc = tr.data.translated_prompt || char.desc;
        updateCharacter(idx, "translatedDesc", portraitDesc);
        const res = await axios.post(`${API_BASE}/character/portrait`, {
            description: portraitDesc || char.desc,
            width: 768,
            height: 768,
            styles: selectedStyles
        });
        if (res.data.image) {
            const dataUrl = `data:image/png;base64,${res.data.image}`;
            setSeedReference(idx, dataUrl);
            void checkFaceDetection(idx, dataUrl);
            // Keep text description in sync with the generated reference
            void analyzeCharacter(idx, dataUrl);
        }
    } catch {
        alert("Portrait generation failed");
    } finally {
        updateCharacter(idx, "isLoading", false);
    }
  };

  const handleCreateStoryboard = async () => {
    if (!storyTopic) return;
    setIsStoryLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/storyboard/create`, {
        topic: storyTopic, 
        duration: storyDuration, 
        language: storyLanguage, 
        style: selectedStyles.join(", "), 
        structure: storyStructure,
        characters: characters 
      });
      setStoryScenes(
        (res.data.scenes || []).map((scene: StoryScene) => ({
          ...scene,
          negative_prompt: scene.negative_prompt || DEFAULT_NEGATIVE_PROMPT
        }))
      );
    } catch { alert("AI Planning failed"); } finally { setIsStoryLoading(false); }
  };

  const startAutopilot = async () => {
    const neededChars = new Set<number>();
    storyScenes.forEach((scene) => {
      const focus = scene.visual_focus || "Landscape";
      if (focus === "A" || focus === "Both") neededChars.add(0);
      if (focus === "B" || focus === "Both") neededChars.add(1);
    });
    setIsAutopilotRunning(true); setAutopilotProgress(0);
    const newScenes = [...storyScenes]; const size = RESOLUTIONS[resolution];
    
    for (let i = 0; i < newScenes.length; i++) {
        try {
            const scene = newScenes[i];
            const focus = scene.visual_focus || "Landscape";
            
            let charPrompt = "";
            let seedToUse = -1;
            let refImageToUse = null;
            
            const charA = characters[0];
            const charB = characters[1];

            if (focus === "A") {
                charPrompt = `((${charA.translatedDesc || charA.desc}:1.2))`;
                seedToUse = charA.seed;
                refImageToUse = charA.reference_image;
            } else if (focus === "B") {
                charPrompt = `((${charB.translatedDesc || charB.desc}:1.2))`;
                seedToUse = charB.seed;
                refImageToUse = charB.reference_image;
            } else if (focus === "Both") {
                const res = await axios.post(`${API_BASE}/generate/compose_dual`, {
                    scene_prompt: scene.image_prompt,
                    char_a_prompt: charA.translatedDesc || charA.desc,
                    char_b_prompt: charB.translatedDesc || charB.desc,
                    char_a_ref: charA.reference_image || null,
                    char_b_ref: charB.reference_image || null,
                    negative_prompt: scene.negative_prompt || DEFAULT_NEGATIVE_PROMPT,
                    styles: selectedStyles,
                    lora: selectedLora.length ? selectedLora : null,
                    width: size.w,
                    height: size.h,
                    steps: runtimeSteps,
                    cfg_scale: runtimeCfgScale,
                    strict_identity: strictIdentity,
                    use_ip_adapter: useIpAdapter
                });
                if (res.data.image) {
                  newScenes[i].image_url = `data:image/png;base64,${res.data.image}`;
                  newScenes[i].ref_used_a = !!charA.reference_image;
                  newScenes[i].ref_used_b = !!charB.reference_image;
                  setStoryScenes([...newScenes]);
                }
                setAutopilotProgress(((i + 1) / newScenes.length) * 100);
                continue;
            } else { 
                charPrompt = "(No humans:1.2), (Scenery:1.3)";
                seedToUse = -1;
            }

            const combinedPrompt = `${charPrompt}, ${scene.image_prompt}, masterpiece, best quality`;

            const res = await axios.post(`${API_BASE}/generate`, { 
                prompt: combinedPrompt, 
                persona: null, 
                negative_prompt: scene.negative_prompt || DEFAULT_NEGATIVE_PROMPT,
                styles: selectedStyles, 
                lora: selectedLora.length ? selectedLora : null, 
                width: size.w, height: size.h, 
                seed: seedToUse,
                reference_image: refImageToUse,
                steps: runtimeSteps,
                cfg_scale: runtimeCfgScale,
                sampler_name: runtimeSampler,
                use_ip_adapter: useIpAdapter
            });
            if (res.data.images?.[0]) {
              newScenes[i].image_url = `data:image/png;base64,${res.data.images[0]}`;
              newScenes[i].ref_used_a = focus === "A" && !!charA.reference_image;
              newScenes[i].ref_used_b = focus === "B" && !!charB.reference_image;
              setStoryScenes([...newScenes]);
            }
            setAutopilotProgress(((i + 1) / newScenes.length) * 100);
        } catch (err) { console.error("Scene error", err); }
    }
    setIsAutopilotRunning(false);
  };

  const handleCreateVideo = async () => {
    setIsVideoLoading(true); setVideoStatus("🎬 Rendering...");
    try {
      // YouTube Shorts: 1080x1920 (9:16)
      // Square: 512x512 (1:1)
      const isShortsMode = resolution === "shorts";
      const finalWidth = isShortsMode ? 1080 : 512;
      const finalHeight = isShortsMode ? 1920 : 512;

      console.log(`🎬 Rendering video at: ${finalWidth}x${finalHeight}`);

      const res = await axios.post(`${API_BASE}/video/create`, {
        scenes: storyScenes, 
        project_name: storyTopic.substring(0, 10).replace(/\s/g, "_") || "my_shorts",
        bgm_file: selectedBgm || null, 
        width: finalWidth, 
        height: finalHeight,
        overlay_settings: overlaySettings,
        characters: characters,
        narrator_voice: narratorVoice
      });
      setVideoUrl(res.data.video_url); fetchData();
    } catch { alert("Video failed"); } finally { setIsVideoLoading(false); setVideoStatus(""); }
  };

  const downloadReferenceImage = (idx: number) => {
    const char = characters[idx];
    if (!char.seed_image) return;
    const link = document.createElement("a");
    const safeRole = char.role.replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_-]/g, "");
    link.href = char.seed_image;
    link.download = `${safeRole || `actor_${idx + 1}`}_seed.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const applyBatchNegativePrompt = () => {
    if (storyScenes.length === 0) return;
    const updated = storyScenes.map((scene) => ({
      ...scene,
      negative_prompt: batchNegative
    }));
    setStoryScenes(updated);
  };

  const lockCast = async () => {
    const hasAllRefs = characters.every((char) => !!char.reference_image);
    if (!hasAllRefs) {
      alert("Actor A/B의 Reference Face를 먼저 준비해주세요.");
      return;
    }
    setCastLocked(true);
    setActiveStep("scene");
  };

  const handlePreviewVoice = async (idx: number) => {
    setPreviewLoadingIndex(idx);
    try {
        const scene = storyScenes[idx];
        const speaker = scene.speaker || "A";
        let voiceToUse = narratorVoice;
        if (speaker === "A") voiceToUse = characters[0].voice;
        else if (speaker === "B") voiceToUse = characters[1].voice;
        
        const res = await axios.post(`${API_BASE}/audio/preview`, { text: scene.script, voice: voiceToUse });
        if (audioRef.current) { audioRef.current.src = res.data.url; audioRef.current.play().catch(() => {}); }
    } catch (err) { console.error("Preview fail", err); } finally { setPreviewLoadingIndex(null); }
  };

  const handleRegenerateScene = async (idx: number) => {
    setRegeneratingIndex(idx);
    try {
      const scene = storyScenes[idx]; const size = RESOLUTIONS[resolution];
      const focus = scene.visual_focus || "Landscape"; 
      let charPrompt = "";
      let seedToUse = -1;
      let refImageToUse = null;
      const charA = characters[0];
      const charB = characters[1];

      if (focus === "A") {
          charPrompt = `((${charA.translatedDesc || charA.desc}:1.2))`;
          seedToUse = charA.seed;
          refImageToUse = charA.reference_image;
      } else if (focus === "B") {
          charPrompt = `((${charB.translatedDesc || charB.desc}:1.2))`;
          seedToUse = charB.seed;
          refImageToUse = charB.reference_image;
      } else if (focus === "Both") {
          const res = await axios.post(`${API_BASE}/generate/compose_dual`, {
            scene_prompt: scene.image_prompt,
            char_a_prompt: charA.translatedDesc || charA.desc,
            char_b_prompt: charB.translatedDesc || charB.desc,
            char_a_ref: charA.reference_image || null,
            char_b_ref: charB.reference_image || null,
            negative_prompt: scene.negative_prompt || DEFAULT_NEGATIVE_PROMPT,
            styles: selectedStyles,
            lora: selectedLora.length ? selectedLora : null,
            width: size.w,
            height: size.h,
            steps: runtimeSteps,
            cfg_scale: runtimeCfgScale,
            strict_identity: strictIdentity,
            use_ip_adapter: useIpAdapter
          });
          if (res.data.image) {
            const updated = [...storyScenes];
            updated[idx].image_url = `data:image/png;base64,${res.data.image}`;
            updated[idx].ref_used_a = !!charA.reference_image;
            updated[idx].ref_used_b = !!charB.reference_image;
            setStoryScenes(updated);
          }
          return;
      } else { 
          charPrompt = "(No humans:1.2), (Scenery:1.3)";
          seedToUse = -1;
      }

      const combinedPrompt = `${charPrompt}, ${scene.image_prompt}, masterpiece, best quality`;

      const res = await axios.post(`${API_BASE}/generate`, { 
        prompt: combinedPrompt, 
        persona: null,
        negative_prompt: scene.negative_prompt || DEFAULT_NEGATIVE_PROMPT,
        styles: selectedStyles, 
        lora: selectedLora.length ? selectedLora : null, 
        width: size.w, height: size.h, 
        seed: seedToUse,
        reference_image: refImageToUse,
        steps: runtimeSteps,
        cfg_scale: runtimeCfgScale,
        sampler_name: runtimeSampler,
        use_ip_adapter: useIpAdapter
      });
      if (res.data.images?.[0]) {
        const updated = [...storyScenes];
        updated[idx].image_url = `data:image/png;base64,${res.data.images[0]}`;
        updated[idx].ref_used_a = focus === "A" && !!charA.reference_image;
        updated[idx].ref_used_b = focus === "B" && !!charB.reference_image;
        setStoryScenes(updated);
      }
    } catch { alert("Regen fail"); } finally { setRegeneratingIndex(null); }
  };

  // --- Visual Settings Component (Global Sidebar) ---
  const VisualSettingsSection = () => (
    <section className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-6 h-fit sticky top-6">
        <div className="flex items-center justify-between px-1">
            <label className="text-sm font-bold flex items-center gap-2"><Palette className="w-4 h-4" /> Visual Style & Settings</label>
        </div>
        <div className="grid grid-cols-1 gap-6">
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">Frontend Settings</span>
                <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-300">Editable</span>
            </div>
            <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-3">
                <div className="p-4 bg-zinc-100 dark:bg-zinc-800 rounded-2xl border border-zinc-200 dark:border-zinc-700 flex flex-col gap-3 animate-in fade-in slide-in-from-top-2">
                    <div className="flex items-center justify-between">
                        <label className="text-xs font-bold uppercase tracking-widest text-zinc-500 flex items-center gap-2" title="영상 위에 SNS 스타일의 UI(프로필, 좋아요 등)를 겹쳐서 표시합니다.">
                            <Monitor className="w-4 h-4" /> SNS Overlay
                        </label>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" checked={overlaySettings.enabled} onChange={(e) => setOverlaySettings({...overlaySettings, enabled: e.target.checked})} className="sr-only peer" />
                            <div className="w-9 h-5 bg-zinc-300 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                        </label>
                    </div>
                    {overlaySettings.enabled && (
                        <div className="grid grid-cols-1 gap-2">
                            <input type="text" placeholder="Profile Name" className="p-2 rounded-xl text-xs font-bold bg-white dark:bg-zinc-900 border-none focus:ring-1 focus:ring-zinc-400" value={overlaySettings.profile_name} onChange={(e) => setOverlaySettings({...overlaySettings, profile_name: e.target.value})} />
                            <input type="text" placeholder="Likes (e.g. 12.5k)" className="p-2 rounded-xl text-xs font-bold bg-white dark:bg-zinc-900 border-none focus:ring-1 focus:ring-zinc-400" value={overlaySettings.likes_count} onChange={(e) => setOverlaySettings({...overlaySettings, likes_count: e.target.value})} />
                            <input type="text" placeholder="Caption / Hashtags" className="p-2 rounded-xl text-xs font-bold bg-white dark:bg-zinc-900 border-none focus:ring-1 focus:ring-zinc-400" value={overlaySettings.caption} onChange={(e) => setOverlaySettings({...overlaySettings, caption: e.target.value})} />
                        </div>
                    )}
                </div>
            </div>
            
            {/* Resolution Display (Fixed to Shorts) */}
            <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2" title="현재는 유튜브 쇼츠(9:16) 해상도에 최적화되어 있습니다."><Smartphone className="w-3.5 h-3.5" /> Output Format</label>
                <div className="p-3 rounded-xl bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
                    <p className="text-xs font-bold text-zinc-900 dark:text-zinc-100">YouTube Shorts (9:16)</p>
                    <p className="text-[10px] text-zinc-500 mt-0.5">Auto-scaled to 1080x1920 HD</p>
                </div>
            </div>

            {/* Generation Settings */}
            <div className="flex flex-col gap-3">
                <label className="text-xs font-bold uppercase tracking-widest text-zinc-400">Generation Settings</label>
                <div className="grid grid-cols-2 gap-2">
                    <div className="flex flex-col gap-1" title="이미지 생성 반복 횟수입니다. 높을수록 디테일이 좋아지지만 속도가 느려집니다. (기본값: 30)">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase">Steps</span>
                        <input
                            type="number"
                            min={5}
                            max={80}
                            className="w-full p-2 rounded-xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-bold focus:ring-1 focus:ring-zinc-400"
                            value={runtimeSteps}
                            onChange={(e) => setRuntimeSteps(Number(e.target.value))}
                        />
                    </div>
                    <div className="flex flex-col gap-1" title="프롬프트(명령어)를 얼마나 엄격하게 따를지 결정합니다. 높을수록 프롬프트를 따르는 성향이 강해집니다. (기본값: 7)">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase">CFG</span>
                        <input
                            type="number"
                            min={1}
                            max={20}
                            step={0.5}
                            className="w-full p-2 rounded-xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-bold focus:ring-1 focus:ring-zinc-400"
                            value={runtimeCfgScale}
                            onChange={(e) => setRuntimeCfgScale(Number(e.target.value))}
                        />
                    </div>
                </div>
                <div className="flex flex-col gap-1" title="노이즈를 제거하여 이미지를 만드는 알고리즘입니다. 종류에 따라 질감이나 화풍이 미묘하게 달라집니다.">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase">Sampler</span>
                    <select
                        value={runtimeSampler}
                        onChange={(e) => setRuntimeSampler(e.target.value)}
                        className="w-full p-2 rounded-xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-bold appearance-none focus:ring-1 focus:ring-zinc-400 cursor-pointer"
                    >
                        {SAMPLER_PRESETS.map((sampler) => (
                            <option key={sampler} value={sampler}>{sampler}</option>
                        ))}
                    </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                    <label className="flex items-center gap-2 p-2 rounded-xl bg-zinc-50 dark:bg-zinc-800 text-[10px] font-bold uppercase text-zinc-500 cursor-pointer" title="캐릭터의 얼굴 특징을 강력하게 유지하는 기술(IP-Adapter)을 사용합니다.">
                        <input type="checkbox" checked={useIpAdapter} onChange={(e) => setUseIpAdapter(e.target.checked)} />
                        Use Face ID+
                    </label>
                    <label className="flex items-center gap-2 p-2 rounded-xl bg-zinc-50 dark:bg-zinc-800 text-[10px] font-bold uppercase text-zinc-500 cursor-pointer" title="얼굴 일치도를 더 엄격하게 검사하고 적용합니다. 켜두면 얼굴이 더 비슷하게 나옵니다.">
                        <input type="checkbox" checked={strictIdentity} onChange={(e) => setStrictIdentity(e.target.checked)} />
                        Strict Identity
                    </label>
                </div>
            </div>

            {/* Narrator Voice Selection */}
            <div className="flex flex-col gap-2">
                <label className="text-xs font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2" title="영상 전체를 설명하는 내레이터(해설자)의 목소리를 선택합니다."><Mic className="w-3.5 h-3.5" /> Narrator Voice</label>
                <div className="relative">
                    <select 
                        value={narratorVoice} 
                        onChange={(e) => setNarratorVoice(e.target.value)} 
                        className="w-full p-2.5 pl-9 rounded-xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-bold appearance-none focus:ring-1 focus:ring-zinc-400 cursor-pointer"
                    >
                        <option value="ko-KR-SunHiNeural">SunHi (F)</option>
                        <option value="ko-KR-InJoonNeural">InJoon (M)</option>
                        <option value="ko-KR-HyunsuMultilingualNeural">Hyunsu (M)</option>
                    </select>
                    <UserCircle className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                </div>
            </div>

            <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                    <label className="text-xs font-bold uppercase tracking-widest text-zinc-400" title="특정 화풍, 캐릭터, 의상 스타일 등을 추가로 적용하는 보조 모델입니다."><Wand2 className="w-3.5 h-3.5 inline-block mr-1" /> LoRA Models</label>
                    {selectedLora.length > 0 && (
                        <button onClick={() => setSelectedLora([])} className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 hover:text-zinc-900 transition-colors">Clear</button>
                    )}
                </div>
                <div className="relative">
                    <input
                        value={loraSearch}
                        onChange={(e) => setLoraSearch(e.target.value)}
                        placeholder="Search LoRA..."
                        className="w-full p-2.5 pl-9 rounded-xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-medium focus:ring-1 focus:ring-zinc-400"
                    />
                    <Settings2 className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400" />
                </div>
                <div className="grid grid-cols-2 gap-2 max-h-36 overflow-y-auto pr-1">
                    {lorasList
                        .filter((lora) => lora.toLowerCase().includes(loraSearch.toLowerCase()))
                        .map((lora) => {
                            const active = selectedLora.includes(lora);
                            return (
                                <button
                                    key={lora}
                                    onClick={() => {
                                        if (active) {
                                            setSelectedLora(selectedLora.filter((item) => item !== lora));
                                        } else {
                                            setSelectedLora([...selectedLora, lora]);
                                        }
                                    }}
                                    className={`px-2.5 py-2 rounded-xl text-[11px] font-semibold border transition-all text-left ${active ? "bg-zinc-900 text-white border-zinc-900 dark:bg-white dark:text-zinc-900 dark:border-white" : "bg-zinc-50 text-zinc-500 border-transparent hover:border-zinc-200 dark:bg-zinc-800"}`}
                                >
                                    {lora}
                                </button>
                            );
                        })}
                </div>
                {selectedLora.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                        {selectedLora.map((lora) => (
                            <button
                                key={lora}
                                onClick={() => setSelectedLora(selectedLora.filter((item) => item !== lora))}
                                className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                            >
                                {lora} ×
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <div className="flex flex-col gap-3">
                <label className="text-xs font-bold uppercase tracking-widest text-zinc-400" title="영상의 전체적인 그림체를 결정합니다. 여러 스타일을 동시에 선택하여 섞을 수 있습니다.">Art Styles</label>
                <div className="flex flex-wrap gap-2">
                    {STYLE_PRESETS.map((style) => (
                        <button key={style} onClick={() => toggleStyle(style)} className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${selectedStyles.includes(style) ? "bg-zinc-900 text-white border-zinc-900 dark:bg-white dark:text-zinc-900 dark:border-white" : "bg-zinc-50 text-zinc-500 border-transparent hover:border-zinc-200 dark:bg-zinc-800"}`}>
                            {style}
                        </button>
                    ))}
                </div>
            </div>
            </div>
            <div className="h-px w-full bg-zinc-200 dark:bg-zinc-800" />
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">WebUI Settings</span>
                <span className="text-[9px] font-bold uppercase tracking-wider text-zinc-300">Read-only</span>
            </div>
            <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">Sync Status</span>
                  <button
                    onClick={fetchWebuiSettings}
                    disabled={isWebuiSettingsLoading}
                    className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 hover:text-zinc-900 disabled:opacity-50"
                  >
                    {isWebuiSettingsLoading ? "Loading..." : "Reload"}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px] text-zinc-500">
                  <div className="flex flex-col gap-1">
                    <span className="font-bold uppercase tracking-wider text-zinc-400">Model</span>
                    <span className="text-zinc-600 dark:text-zinc-300">{webuiSettings?.model || currentModel}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-bold uppercase tracking-wider text-zinc-400">VAE</span>
                    <span className="text-zinc-600 dark:text-zinc-300">{getWebuiOption("sd_vae")}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-bold uppercase tracking-wider text-zinc-400">Clip Skip</span>
                    <span className="text-zinc-600 dark:text-zinc-300">{getWebuiOption("CLIP_stop_at_last_layers")}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-bold uppercase tracking-wider text-zinc-400">ETA Noise Seed</span>
                    <span className="text-zinc-600 dark:text-zinc-300">{getWebuiOption("eta_noise_seed_delta")}</span>
                  </div>
                </div>
                {webuiSettingsError && (
                  <p className="text-[10px] font-bold text-red-500">{webuiSettingsError}</p>
                )}
            </div>
            <div className="flex flex-col gap-2 mt-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">ControlNet</span>
                  <button
                    onClick={fetchControlnetSettings}
                    disabled={isControlnetLoading}
                    className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 hover:text-zinc-900 disabled:opacity-50"
                  >
                    {isControlnetLoading ? "Loading..." : "Reload"}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px] text-zinc-500">
                  <div className="flex flex-col gap-1">
                    <span className="font-bold uppercase tracking-wider text-zinc-400">Version</span>
                    <span className="text-zinc-600 dark:text-zinc-300">{getControlnetVersion()}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-bold uppercase tracking-wider text-zinc-400">Presets</span>
                    <span className="text-zinc-600 dark:text-zinc-300">
                      {controlnetSettings?.preset ? Object.keys(controlnetSettings.preset).length : 0}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-bold uppercase tracking-wider text-zinc-400">Unit Count</span>
                    <span className="text-zinc-600 dark:text-zinc-300">{getControlnetUnitCount()}</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="text-[9px] font-bold uppercase tracking-wider text-zinc-400">Runtime Units</div>
                  {getRuntimeUnits().length === 0 && (
                    <div className="text-[10px] text-zinc-500">No runtime unit data available.</div>
                  )}
                  {getRuntimeUnits().map((unit, idx) => (
                    <div key={`runtime-${idx}`} className="rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 p-2">
                      <div className="text-[9px] font-bold uppercase tracking-wider text-zinc-400 mb-1">Unit {idx}</div>
                      <div className="text-[10px] text-zinc-600 dark:text-zinc-300">
                        {getUnitFields(unit).length === 0
                          ? "No fields available."
                          : getUnitFields(unit).map((item) => `${item.key}=${item.value}`).join(" · ")}
                      </div>
                    </div>
                  ))}
                </div>
                {controlnetSettings?.preset && (
                  <div className="space-y-2">
                    <div className="text-[9px] font-bold uppercase tracking-wider text-zinc-400">Backend Preset Units</div>
                    {Object.entries(controlnetSettings.preset).map(([key, items]) => (
                      <div key={key} className="rounded-xl bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 p-2">
                        <div className="text-[9px] font-bold uppercase tracking-wider text-zinc-400 mb-1">{key}</div>
                        <div className="space-y-1">
                          {items.map((item, idx) => (
                            <div key={`${item.module}-${item.model}-${idx}`} className="text-[10px] text-zinc-600 dark:text-zinc-300">
                              Unit {idx} · {item.module} · {item.model} · w={item.weight}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {(controlnetSettings?.error || controlnetError) && (
                  <p className="text-[10px] font-bold text-red-500">{controlnetSettings?.error || controlnetError}</p>
                )}
            </div>
        </div>
    </section>
  );

  return (
    <div className="flex min-h-screen flex-col items-center p-8 bg-zinc-50 dark:bg-black font-sans text-zinc-900 dark:text-zinc-100 pb-20">
      <audio ref={audioRef} hidden />
      <audio 
        ref={bgmPlayerRef} 
        hidden 
        onEnded={() => setPlayingBgm(null)} 
        onTimeUpdate={(e) => {
          if (e.currentTarget.currentTime >= 3) {
            e.currentTarget.pause();
            e.currentTarget.currentTime = 0;
            setPlayingBgm(null);
          }
        }}
      />

      <main className="flex w-full max-w-7xl flex-col items-center gap-6 mt-10">
        <div className="flex flex-col items-center gap-2">
          <h1 className="text-4xl font-bold tracking-tight text-center">
            Shorts Producer AI
          </h1>
          <div className="px-3 py-1 bg-zinc-100 dark:bg-zinc-900 rounded-full border border-zinc-200 dark:border-zinc-800 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${currentModel === "Disconnected" ? "bg-red-500" : "bg-green-500 animate-pulse"}`} />
            <span className="text-[10px] font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
              Model: {currentModel}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 w-full">
            <div className="lg:col-span-4 flex flex-col gap-6">
                <VisualSettingsSection />
            </div>

            <div className="lg:col-span-8 flex flex-col gap-6">
                <div className="w-full flex flex-col gap-10">
                    <section className="p-4 rounded-3xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">Workflow</span>
                                <div className="flex items-center gap-2 rounded-full bg-zinc-100 dark:bg-zinc-800 p-1">
                                    <button
                                        onClick={() => setActiveStep("cast")}
                                        className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all ${activeStep === "cast" ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900" : "text-zinc-500 hover:text-zinc-900"}`}
                                    >
                                        Step 1 · Cast Setup
                                    </button>
                                    <button
                                        onClick={() => castLocked && setActiveStep("scene")}
                                        className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all ${activeStep === "scene" && castLocked ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900" : "text-zinc-500 hover:text-zinc-900"} ${!castLocked ? "opacity-40 cursor-not-allowed" : ""}`}
                                        disabled={!castLocked}
                                    >
                                        Step 2 · Scene Builder
                                    </button>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className={`text-[10px] font-bold uppercase tracking-wider ${castLocked ? "text-green-600" : "text-zinc-400"}`}>
                                    {castLocked ? "Cast Locked" : "Cast Not Locked"}
                                </span>
                                <button
                                    onClick={lockCast}
                                    className="px-4 py-2 rounded-xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-[10px] font-black uppercase tracking-widest hover:opacity-90 transition-all"
                                >
                                    Lock Cast
                                </button>
                            </div>
                        </div>
                    </section>

                    {activeStep === "cast" && (
                        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {characters.map((char, idx) => (
                                <div key={char.id} className="p-5 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
                                    <div className="flex items-center justify-between px-1">
                                        <label className="text-sm font-bold flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
                                            <User className="w-4 h-4" /> {char.role}
                                        </label>
                                        <button onClick={() => setRandomPersona(idx)} className="text-[10px] font-bold flex items-center gap-1 text-zinc-400 hover:text-zinc-800 transition-colors">
                                            <Dices className="w-3.5 h-3.5" /> Random
                                        </button>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">Seed Image</label>
                                        <div
                                            className={`aspect-square relative rounded-2xl overflow-hidden bg-zinc-100 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800 shrink-0 shadow-inner transition-all group ${char.seed_image ? "cursor-zoom-in" : ""}`}
                                            onClick={() => char.seed_image && setPreviewImage(char.seed_image)}
                                        >
                                            {char.seed_image ? (
                                                <>
                                                    <Image src={char.seed_image} alt="Seed Image" fill className="object-cover" unoptimized />
                                                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 backdrop-blur-sm z-20 pointer-events-none">
                                                        <button onClick={() => { setUploadingCharIdx(idx); fileInputRef.current?.click(); }} className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white backdrop-blur-md transition-all pointer-events-auto" title="Replace Photo">
                                                            <Upload className="w-4 h-4" />
                                                        </button>
                                                        <button onClick={() => setReferenceImage(idx, null)} className="p-2 bg-red-500/80 hover:bg-red-600 rounded-full text-white backdrop-blur-md transition-all pointer-events-auto" title="Remove">
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                    <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/60 backdrop-blur-md rounded-lg text-[10px] text-white font-bold z-10 pointer-events-none">
                                                        Seed Image
                                                    </div>
                                                    {char.face_detected !== null && (
                                                        <div className={`absolute top-2 left-2 px-2 py-1 rounded-lg text-[10px] font-bold z-10 pointer-events-none ${char.face_detected ? "bg-emerald-600/90 text-white" : "bg-rose-600/90 text-white"}`}>
                                                            {char.face_detected ? `Face OK${typeof char.face_count === "number" ? ` (${char.face_count})` : ""}` : "No Face"}
                                                        </div>
                                                    )}
                                                </>
                                            ) : (
                                                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-4 text-center">
                                                    <div className="w-12 h-12 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center text-zinc-400">
                                                        <UserCircle className="w-6 h-6" />
                                                    </div>
                                                    <button onClick={(e) => { e.stopPropagation(); setUploadingCharIdx(idx); fileInputRef.current?.click(); }} className="px-4 py-2 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-xl text-[10px] font-bold uppercase tracking-wider hover:opacity-90 transition-all shadow-sm">
                                                        Upload Photo
                                                    </button>
                                                </div>
                                            )}
                                            {char.isLoading && !char.reference_loading_kind && (
                                                <div className="absolute inset-0 flex items-center justify-center bg-zinc-50/50 dark:bg-zinc-950/50 backdrop-blur-sm z-30">
                                                    <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    
                                    <div className="space-y-3">
                                        <textarea 
                                            className="w-full p-3 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs resize-none focus:ring-1 focus:ring-indigo-400 font-medium" 
                                            rows={2} 
                                            value={char.desc} 
                                            placeholder={`Describe ${char.role}...`}
                                            onChange={(e) => updateCharacter(idx, "desc", e.target.value)} 
                                        />
                                        
                                    <div className="flex flex-wrap gap-2">
                                        <button onClick={() => { setUploadingCharIdx(idx); fileInputRef.current?.click(); }} className="flex-1 py-2 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-bold hover:bg-zinc-200 transition-all flex items-center justify-center gap-1 text-[9px] uppercase tracking-wider border border-zinc-200 dark:border-zinc-700">
                                            <Upload className="w-3 h-3" /> Upload Seed
                                        </button>
                                        <button onClick={() => handleGeneratePortrait(idx)} disabled={char.isLoading || !char.desc} className="flex-1 py-2 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 font-bold hover:bg-indigo-100 transition-all flex items-center justify-center gap-1 text-[9px] uppercase tracking-wider border border-indigo-100 dark:border-indigo-900/30">
                                            <Sparkles className="w-3 h-3" /> Generate Seed
                                        </button>
                                        <button onClick={() => downloadReferenceImage(idx)} disabled={!char.seed_image} className="flex-1 py-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 font-bold hover:bg-emerald-100 transition-all flex items-center justify-center gap-1 text-[9px] uppercase tracking-wider border border-emerald-100 dark:border-emerald-900/30 disabled:opacity-40">
                                            <Download className="w-3 h-3" /> Download Seed
                                        </button>
                                    </div>
                                    <div className="pt-1">
                                        <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">Seed Prompt</span>
                                    </div>

                                    <div className="flex gap-2">
                                        <button onClick={() => handleTranslateActor(idx)} disabled={char.isTranslating || !char.desc} className="flex-1 py-2 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-bold hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-all flex items-center justify-center gap-1 text-[9px] uppercase tracking-wider border border-blue-100 dark:border-blue-900/30">
                                            {char.isTranslating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Globe className="w-3 h-3" />} Seed Prompt
                                        </button>
                                            <div className="relative flex-1">
                                                <select 
                                                    value={char.voice} 
                                                    onChange={(e) => updateCharacter(idx, "voice", e.target.value)} 
                                                    className="w-full py-2 pl-2 pr-6 rounded-xl bg-zinc-100 dark:bg-zinc-800 border-none text-[9px] font-bold appearance-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
                                                >
                                                    <option value="ko-KR-SunHiNeural">SunHi (F)</option>
                                                    <option value="ko-KR-InJoonNeural">InJoon (M)</option>
                                                    <option value="ko-KR-HyunsuMultilingualNeural">Hyunsu (M)</option>
                                                </select>
                                                <Mic className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-400 pointer-events-none" />
                                            </div>
                                        </div>

                                    {char.translatedDesc && (
                                        <textarea 
                                            className="w-full p-3 rounded-xl bg-indigo-50/50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-900/30 text-[10px] resize-none focus:ring-1 focus:ring-indigo-500 font-medium text-indigo-900 dark:text-indigo-100" 
                                            rows={2} 
                                            value={char.translatedDesc} 
                                            onChange={(e) => updateCharacter(idx, "translatedDesc", e.target.value)} 
                                        />
                                    )}
                                    <div className="pt-1">
                                        <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">Reference Sets</span>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        <button onClick={() => generateReferenceImages(idx, "face")} disabled={!char.desc && !char.translatedDesc} className="flex-1 py-2 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 font-bold hover:bg-indigo-100 transition-all flex items-center justify-center gap-1 text-[9px] uppercase tracking-wider border border-indigo-100 dark:border-indigo-900/30">
                                            <Sparkles className="w-3 h-3" /> Generate Face Set
                                        </button>
                                        <button onClick={() => generateReferenceImages(idx, "body")} disabled={!char.desc && !char.translatedDesc} className="flex-1 py-2 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 font-bold hover:bg-indigo-100 transition-all flex items-center justify-center gap-1 text-[9px] uppercase tracking-wider border border-indigo-100 dark:border-indigo-900/30">
                                            <Sparkles className="w-3 h-3" /> Generate Body Set
                                        </button>
                                        <button onClick={() => generateAllReferenceSets(idx)} disabled={!char.desc && !char.translatedDesc} className="flex-1 py-2 rounded-xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-bold hover:opacity-90 transition-all flex items-center justify-center gap-1 text-[9px] uppercase tracking-wider">
                                            <Sparkles className="w-3 h-3" /> Generate All
                                        </button>
                                    </div>
                                    {(char.reference_images_face.length > 0 || char.reference_loading_kind === "face") && (
                                        <div className="space-y-2">
                                            <label className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">Face Reference Images</label>
                                            <div className="grid grid-cols-4 gap-2">
                                                {Array.from({ length: 4 }).map((_, pIdx) => {
                                                    const img = char.reference_images_face[pIdx];
                                                    return (
                                                        <div
                                                            key={`${char.id}-face-${pIdx}`}
                                                            onClick={() => img && setPreviewImage(img)}
                                                            className={`relative aspect-square rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-900 ${img ? "cursor-pointer" : ""}`}
                                                        >
                                                            {img ? (
                                                                <>
                                                                    <Image src={img} alt={`Face ${pIdx + 1}`} fill className="object-cover" unoptimized />
                                                                    <button
                                                                      onClick={(e) => { e.stopPropagation(); void regenerateReferenceImage(idx, "face", pIdx); }}
                                                                      className="absolute bottom-1 right-1 p-1 rounded-md bg-white/80 hover:bg-white text-zinc-700 shadow"
                                                                      title="Regenerate"
                                                                    >
                                                                      <RefreshCw className="w-3 h-3" />
                                                                    </button>
                                                                </>
                                                            ) : (
                                                                <div className="absolute inset-0 flex items-center justify-center bg-zinc-50/70 dark:bg-zinc-950/60">
                                                                    {char.reference_loading_kind === "face" ? (
                                                                        <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
                                                                    ) : null}
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                    {(char.reference_images_body.length > 0 || char.reference_loading_kind === "body") && (
                                        <div className="space-y-2">
                                            <label className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">Body Reference Images</label>
                                            <div className="grid grid-cols-4 gap-2">
                                                {Array.from({ length: 4 }).map((_, pIdx) => {
                                                    const img = char.reference_images_body[pIdx];
                                                    return (
                                                    <div
                                                        key={`${char.id}-body-${pIdx}`}
                                                        onClick={() => img && setPreviewImage(img)}
                                                        className={`relative aspect-square rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-900 ${img ? "cursor-pointer" : ""}`}
                                                    >
                                                        {img ? (
                                                            <>
                                                                <Image src={img} alt={`Body ${pIdx + 1}`} fill className="object-cover" unoptimized />
                                                                <button
                                                                  onClick={(e) => { e.stopPropagation(); void regenerateReferenceImage(idx, "body", pIdx); }}
                                                                  className="absolute bottom-1 right-1 p-1 rounded-md bg-white/80 hover:bg-white text-zinc-700 shadow"
                                                                  title="Regenerate"
                                                                >
                                                                  <RefreshCw className="w-3 h-3" />
                                                                </button>
                                                                {pIdx === 0 && (
                                                                  <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded-md bg-indigo-600 text-white text-[8px] font-bold uppercase tracking-wider shadow">
                                                                    Best
                                                                  </div>
                                                                )}
                                                            </>
                                                        ) : (
                                                            <div className="absolute inset-0 flex items-center justify-center bg-zinc-50/70 dark:bg-zinc-950/60">
                                                                <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
                                                            </div>
                                                        )}
                                                    </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </section>
                    )}

                    {activeStep === "scene" && (
                    <section className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
                    <div className="flex items-center justify-between px-1">
                        <label className="text-sm font-bold flex items-center gap-2"><Clapperboard className="w-4 h-4" /> Step 2: Story Planning & Language</label>
                        <button onClick={setRandomPrompt} disabled={isRandomLoading} className="text-[10px] font-bold flex items-center gap-1 text-zinc-400 hover:text-zinc-800 transition-colors">
                            <Dices className={`w-3.5 h-3.5 ${isRandomLoading ? "animate-spin" : ""}`} /> Suggest Topic
                        </button>
                    </div>
                    <div className="flex flex-col gap-4">
                        <div className="relative flex-1">
                        <textarea 
                            className="w-full p-6 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition-all text-base font-medium resize-none shadow-inner" 
                            placeholder="Enter a detailed topic or scenario for your shorts..." 
                            rows={3}
                            value={storyTopic} 
                            onChange={(e) => setStoryTopic(e.target.value)} 
                        />
                        </div>
                        <div className="flex flex-col md:flex-row gap-3">
                            <div className="flex-1 flex gap-2">
                                <div className="flex items-center gap-2 bg-zinc-50 dark:bg-zinc-800 rounded-2xl px-6 border border-zinc-100 dark:border-zinc-800 shadow-sm flex-1 justify-center">
                                    <Clock className="w-4 h-4 text-zinc-400" />
                                    <span className="text-xs font-bold text-zinc-400 uppercase tracking-widest mr-2">Duration</span>
                                    <input type="number" min={10} max={60} className="w-10 bg-transparent border-none text-sm font-bold text-center focus:ring-0" value={storyDuration} onChange={(e) => setStoryDuration(Number(e.target.value))} />
                                    <span className="text-[10px] text-zinc-400 font-bold">SEC</span>
                                </div>
                            </div>
                            <div className="flex-1 min-w-[140px]">
                                <div className="relative h-full">
                                    <select value={storyStructure} onChange={(e) => setStoryStructure(e.target.value)} className="w-full h-full px-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-bold appearance-none focus:ring-1 focus:ring-zinc-400 cursor-pointer">
                                        <option value="Free Flow">Free Flow (Basic)</option>
                                        <option value="The Listicle (Top N)">Listicle (Top 3)</option>
                                        <option value="Problem & Solution">Problem & Solution</option>
                                        <option value="Narrative Arc (Story)">Storytelling (Drama)</option>
                                        <option value="Versus (Comparison)">Versus (A vs B)</option>
                                        <option value="Romance / Couple Vlog">Couple Vlog (Romance)</option>
                                    </select>
                                    <Layout className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 pointer-events-none" />
                                </div>
                            </div>
                            <button onClick={handleCreateStoryboard} disabled={isStoryLoading || !storyTopic} className="px-10 py-4 rounded-2xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-black uppercase tracking-widest text-xs hover:opacity-90 transition-all shadow-xl active:scale-95 flex items-center justify-center gap-2">{isStoryLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Plan Story with AI"}</button>
                        </div>
                    </div>
                    </section>
                    )}

                    {/* Step 3: Scenes */}
                    {activeStep === "scene" && storyScenes.length > 0 && (
                    <div className="flex flex-col gap-6">
                        <div className="flex items-center justify-between px-2 text-center md:text-left flex-wrap gap-4">
                        <h3 className="font-bold text-lg w-full md:w-auto">Step 3: Storyboard Scenes</h3>

                        <div className="flex gap-2 items-center flex-wrap">
                            {/* Enhanced BGM Selection */}
                            <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800 p-1 rounded-xl border border-zinc-200 dark:border-zinc-700">
                                <select value={selectedBgm} onChange={(e) => setSelectedBgm(e.target.value)} className="bg-transparent border-none text-xs font-bold px-3 py-1.5 focus:ring-0 cursor-pointer min-w-[120px]">
                                    <option value="">No BGM</option>
                                    {bgmList.map(bgm => <option key={bgm.name} value={bgm.name}>{bgm.name}</option>)}
                                </select>
                                {selectedBgm && (
                                    <button 
                                        onClick={() => {
                                            const bgm = bgmList.find(b => b.name === selectedBgm);
                                            if (!bgm) return;
                                            if (playingBgm === selectedBgm) {
                                                bgmPlayerRef.current?.pause();
                                                setPlayingBgm(null);
                                            } else if (bgmPlayerRef.current) {
                                                bgmPlayerRef.current.src = bgm.url;
                                                bgmPlayerRef.current.play().catch(() => {});
                                                setPlayingBgm(selectedBgm);
                                            }
                                        }}
                                        className="p-1.5 text-zinc-500 hover:text-indigo-600 transition-colors"
                                    >
                                        {playingBgm === selectedBgm ? <PauseCircle className="w-4 h-4" /> : <PlayCircle className="w-4 h-4" />}
                                    </button>
                                )}
                            </div>

                            <button onClick={() => setIsBatchOpen(!isBatchOpen)} className="px-4 py-2.5 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all text-[11px] uppercase tracking-wider">
                              {isBatchOpen ? "Close Neg Prompt" : "Batch Neg Prompt"}
                            </button>
                            <button onClick={startAutopilot} disabled={isAutopilotRunning || isVideoLoading} className="px-6 py-2.5 rounded-xl bg-emerald-500 text-white font-bold hover:bg-emerald-600 transition-all flex items-center gap-2 shadow-lg">{isAutopilotRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : "일괄생성"}</button>
                            {storyScenes.every(s => s.image_url) && <button onClick={handleCreateVideo} disabled={isVideoLoading} className="px-6 py-2.5 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition-all flex items-center gap-2 shadow-lg">{isVideoLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Produce 🎬"}</button>}
                        </div>
                        </div>

                        {isBatchOpen && (
                          <div className="w-full bg-white dark:bg-zinc-900 p-5 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-3">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">Batch Negative Prompt</span>
                              <button
                                onClick={() => setBatchNegative(DEFAULT_NEGATIVE_PROMPT)}
                                className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 hover:text-zinc-900"
                              >
                                Reset Default
                              </button>
                            </div>
                            <textarea
                              className="w-full p-3 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs leading-relaxed"
                              rows={2}
                              value={batchNegative}
                              onChange={(e) => setBatchNegative(e.target.value)}
                            />
                            <div className="flex justify-end">
                              <button
                                onClick={applyBatchNegativePrompt}
                                className="px-4 py-2 rounded-xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-[10px] font-black uppercase tracking-widest hover:opacity-90 transition-all"
                              >
                                Apply to All Scenes
                              </button>
                            </div>
                          </div>
                        )}

                        {(isAutopilotRunning || isVideoLoading) && (
                            <div className="w-full bg-white dark:bg-zinc-900 p-6 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-3">
                                <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-zinc-400">
                                    <span className="flex items-center gap-2 text-indigo-500"><Loader2 className="w-3 h-3 animate-spin" /> {isVideoLoading ? videoStatus : "Autopilot Active"}</span>
                                    <span>{isAutopilotRunning ? `${Math.round(autopilotProgress)}%` : ""}</span>
                                </div>
                                <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden"><div className="bg-indigo-500 h-full transition-all duration-500" style={{ width: isAutopilotRunning ? `${autopilotProgress}%` : "100%" }} /></div>
                            </div>
                        )}

                        <div className="grid grid-cols-1 gap-4">
                        {storyScenes.map((scene, idx) => (
                            <div key={idx} className="p-5 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 flex flex-col md:flex-row gap-6 relative group transition-all hover:border-zinc-300 dark:hover:border-zinc-700">
                            <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-all">
                                <button onClick={() => handlePreviewVoice(idx)} disabled={previewLoadingIndex === idx} className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded-full text-zinc-400 hover:text-blue-500 transition-colors shadow-sm"><Volume2 className="w-4 h-4" /></button>
                                <button onClick={() => handleRegenerateScene(idx)} disabled={regeneratingIndex !== null} className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded-full text-zinc-400 hover:text-emerald-500 transition-colors shadow-sm"><RefreshCw className={`w-4 h-4 ${regeneratingIndex === idx ? "animate-spin" : ""}`} /></button>
                            </div>
                            <div className={`w-full md:w-48 aspect-square relative rounded-2xl overflow-hidden bg-zinc-100 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800 shrink-0 shadow-inner transition-all ${scene.image_url ? "cursor-zoom-in hover:opacity-90 hover:ring-4 ring-indigo-500/30" : ""}`} onClick={() => scene.image_url && setPreviewImage(scene.image_url)}>
                                {scene.image_url ? <><Image src={scene.image_url} alt={`Scene ${idx}`} fill className="object-cover" unoptimized />{regeneratingIndex === idx && <div className="absolute inset-0 bg-black/40 flex items-center justify-center backdrop-blur-sm"><Loader2 className="w-8 h-8 animate-spin text-white" /></div>}<div className="absolute top-2 left-2"><CheckCircle2 className="w-5 h-5 text-emerald-500 drop-shadow-md bg-white rounded-full" /></div></> : <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-300 gap-2 font-bold uppercase text-[10px] opacity-20"><ImageIcon className="w-8 h-8" /> Pending</div>}
                            </div>
                            <div className="flex-1 flex flex-col gap-3">
                                <div className="flex flex-wrap items-center gap-3">
                                    <span className="px-2.5 py-1 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg text-[10px] font-black uppercase tracking-wider">Scene {idx + 1}</span>
                                    <div className="flex items-center gap-1.5">
                                        <Clock className="w-3 h-3 text-zinc-400" />
                                        <input type="number" className="w-10 bg-transparent border-none p-0 text-xs font-bold text-zinc-500 focus:ring-0" value={scene.duration} onChange={(e) => { const ns = [...storyScenes]; ns[idx].duration = Number(e.target.value); setStoryScenes(ns); }} />
                                        <span className="text-[10px] font-bold text-zinc-400">SEC</span>
                                    </div>
                                    {(scene.ref_used_a || scene.ref_used_b) && (
                                        <div className="flex items-center gap-1.5">
                                            {scene.ref_used_a && <span className="px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">Ref A OK</span>}
                                            {scene.ref_used_b && <span className="px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200">Ref B OK</span>}
                                        </div>
                                    )}
                                </div>
                                <div className="space-y-3"><textarea className="w-full p-0 bg-transparent border-none text-sm font-semibold leading-relaxed focus:ring-0 resize-none text-zinc-800 dark:text-zinc-200" rows={2} value={scene.script} onChange={(e) => { const ns = [...storyScenes]; ns[idx].script = e.target.value; setStoryScenes(ns); }} />                        <div className="text-[10px] text-zinc-400 bg-zinc-50 dark:bg-zinc-950 p-3 rounded-2xl border border-zinc-100 dark:border-zinc-800">
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-emerald-500 font-bold uppercase tracking-widest mr-2">Prompt</span>
                                    {scene.image_prompt_ko && (
                                    <div className="flex items-center gap-1 text-[9px] text-zinc-500 font-medium">
                                        <Eye className="w-3 h-3" /> {scene.image_prompt_ko}
                                    </div>
                                    )}
                                    <div className="flex items-center gap-2">
                                        <select value={scene.visual_focus || "Landscape"} onChange={(e) => { const ns = [...storyScenes]; ns[idx].visual_focus = e.target.value; ns[idx].ref_used_a = undefined; ns[idx].ref_used_b = undefined; setStoryScenes(ns); }} className="bg-transparent border border-zinc-200 dark:border-zinc-700 text-[9px] font-bold rounded-lg px-1.5 py-0.5">
                                            <option value="A">Focus: A</option>
                                            <option value="B">Focus: B</option>
                                            <option value="Both">Focus: Both</option>
                                            <option value="Landscape">Landscape</option>
                                        </select>
                                        <select value={scene.speaker || "A"} onChange={(e) => { const ns = [...storyScenes]; ns[idx].speaker = e.target.value; setStoryScenes(ns); }} className="bg-transparent border border-zinc-200 dark:border-zinc-700 text-[9px] font-bold rounded-lg px-1.5 py-0.5">
                                            <option value="A">Speaker: A</option>
                                            <option value="B">Speaker: B</option>
                                            <option value="Narrator">Narrator</option>
                                        </select>
                                    </div>
                                </div>
                                <textarea 
                                    className="w-full p-0 bg-transparent border-none focus:ring-0 resize-none mt-1" 
                                    rows={2} 
                                    value={scene.image_prompt} 
                                    title={scene.image_prompt_ko || "No Korean description available"}
                                    onChange={(e) => { const ns = [...storyScenes]; ns[idx].image_prompt = e.target.value; setStoryScenes(ns); }} 
                                />
                                <div className="mt-3">
                                    <div className="flex items-center justify-between">
                                      <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">Negative Prompt</span>
                                      <button
                                        onClick={() => { const ns = [...storyScenes]; ns[idx].negative_prompt = DEFAULT_NEGATIVE_PROMPT; setStoryScenes(ns); }}
                                        className="text-[9px] font-bold uppercase tracking-widest text-zinc-500 hover:text-zinc-900"
                                      >
                                        Reset
                                      </button>
                                    </div>
                                    <textarea
                                      className="w-full mt-1 p-2 rounded-xl bg-white/70 dark:bg-zinc-900/60 border border-zinc-100 dark:border-zinc-800 text-[10px] leading-relaxed focus:ring-1 focus:ring-zinc-400"
                                      rows={2}
                                      value={scene.negative_prompt || ""}
                                      onChange={(e) => { const ns = [...storyScenes]; ns[idx].negative_prompt = e.target.value; setStoryScenes(ns); }}
                                    />
                                </div>
                                </div></div>
                            </div>
                            </div>
                        ))}
                        </div>

                        {videoUrl && (
                            <div className="p-8 bg-zinc-900 rounded-[40px] border border-zinc-800 shadow-2xl animate-in zoom-in-95 duration-500 mt-6">
                                <label className="text-[10px] font-bold uppercase tracking-widest text-blue-400 mb-6 block text-center">New Produced Video</label>
                                <video src={videoUrl} controls className="w-full max-w-sm mx-auto rounded-3xl shadow-2xl border border-white/10" />
                                <div className="mt-6 flex justify-center"><a href={videoUrl} download className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-2xl text-sm font-bold hover:bg-blue-700 transition-all"><Download className="w-4 h-4" /> Download MP4</a></div>
                            </div>
                        )}
                    </div>
                    )}
                </div>
            </div>
        </div>

        {/* Produced History & Monitor - Simpler placement */}
        <section className="w-full mt-10 border-t border-zinc-200 dark:border-zinc-800 pt-10">
            <div className="flex items-center justify-between mb-6 px-2">
                <h2 className="text-xl font-bold flex items-center gap-2"><History className="w-5 h-5 text-zinc-400" /> Recent Production</h2>
                <div className="flex gap-2">
                    <button onClick={() => setShowProjectList(true)} className="px-5 py-2.5 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white border border-zinc-200 dark:border-zinc-800 rounded-xl text-xs font-black uppercase tracking-wider hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-all flex items-center gap-2 shadow-sm active:scale-95"><Boxes className="w-4 h-4" /> Load Project</button>
                    <button onClick={handleSaveProject} className="px-5 py-2.5 bg-zinc-900 dark:bg-white text-white dark:text-black rounded-xl text-xs font-black uppercase tracking-wider hover:opacity-80 transition-all flex items-center gap-2 shadow-lg active:scale-95"><Save className="w-4 h-4" /> Save Project</button>
                </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {producedVideos?.slice(0, 4).map(v => (
                    <div key={v.name} className="aspect-[9/16] bg-zinc-900 rounded-3xl overflow-hidden relative group border border-zinc-200 dark:border-zinc-800 shadow-md">
                        <video src={v.url} className="w-full h-full object-cover opacity-60 transition-opacity group-hover:opacity-100" muted />
                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/40 backdrop-blur-sm transition-all">
                            <a href={v.url} target="_blank" className="p-3 bg-white text-black rounded-full hover:scale-110 transition-all"><Play className="w-6 h-6 fill-current" /></a>
                        </div>
                    </div>
                ))}
            </div>
        </section>

        {/* Project Browser Modal */}
        {showProjectList && (
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-in fade-in duration-200">
                <div className="bg-white dark:bg-zinc-900 w-full max-w-2xl rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-2xl p-8 flex flex-col max-h-[80vh]">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-bold flex items-center gap-2"><Boxes className="w-5 h-5 text-indigo-500" /> Saved Projects</h3>
                        <button onClick={() => setShowProjectList(false)} className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors"><X className="w-5 h-5" /></button>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                        {projects.length === 0 ? (
                            <div className="text-center py-20 text-zinc-400 text-sm font-medium">No saved projects found.</div>
                        ) : (
                            projects.map((proj: Project) => (
                                <div key={proj.id} className="flex items-center justify-between p-4 bg-zinc-50 dark:bg-zinc-950 rounded-2xl border border-zinc-100 dark:border-zinc-800 hover:border-indigo-500 transition-all group">
                                    <div>
                                        <h4 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">{proj.title}</h4>
                                        <p className="text-[10px] text-zinc-400 mt-1 flex items-center gap-2">
                                            <Clock className="w-3 h-3" /> {new Date(proj.updated_at * 1000).toLocaleString()}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={() => { handleLoadProject(proj.id); setShowProjectList(false); }} className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition-colors">Load</button>
                                        <button onClick={async () => {
                                            if(!confirm("Delete this project?")) return;
                                            await axios.delete(`${API_BASE}/projects/${proj.id}`);
                                            fetchData();
                                        }} className="p-2 text-zinc-400 hover:text-red-500 transition-colors"><Trash2 className="w-4 h-4" /></button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        )}
        {/* Image Preview Modal */}
        {previewImage && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md p-4 animate-in fade-in duration-200" onClick={() => setPreviewImage(null)}>
                <div className="relative w-full max-w-6xl h-full flex items-center justify-center p-4">
                    <button onClick={() => setPreviewImage(null)} className="absolute top-6 right-6 p-3 bg-white/10 hover:bg-white/20 rounded-full text-white transition-all backdrop-blur-sm z-50 group">
                        <X className="w-6 h-6 group-hover:scale-110 transition-transform" />
                    </button>
                    <Image
                        src={previewImage}
                        alt="Preview"
                        width={1600}
                        height={900}
                        onClick={(e) => e.stopPropagation()}
                        className="max-w-full max-h-[90vh] w-auto h-auto object-contain rounded-xl shadow-2xl animate-in zoom-in-95 duration-300 select-none"
                        unoptimized
                    />
                </div>
            </div>
        )}
        
        {/* Hidden File Input for Character Reference Upload */}
        <input 
            type="file" 
            ref={fileInputRef} 
            hidden 
            accept="image/*" 
            onChange={(e) => uploadingCharIdx !== null && handleReferenceUpload(uploadingCharIdx, e)} 
        />
      </main>
    </div>
  );
}
