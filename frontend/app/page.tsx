"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { 
  Loader2, Send, Wand2, ChevronDown, ChevronUp, Palette, Dices, Monitor, Smartphone, 
  Square as SquareIcon, Sparkles, ImageIcon, Clapperboard, Image as LucideImage, 
  User, Clock, Music, Trash2, Edit3, UserCircle, RefreshCw, Volume2, Download, 
  CheckCircle2, Globe, Play, Film, Save, History, Boxes, Eye, Plus, X, ChevronRight, Settings2,
  PlayCircle, PauseCircle, Layout
} from "lucide-react";
import Image from "next/image";

// --- Constants ---
const API_BASE = "http://localhost:8000";
const STYLE_PRESETS = [
  "Studio Ghibli",
  "Chibi",
  "Photorealistic",
  "Cyberpunk",
  "Watercolor",
  "Pixel Art",
  "Oil Painting",
  "Cinematic",
  "3D Render"
];

const SAMPLE_PROMPTS = [
  "비 오는 사이버펑크 도시의 고양이",
  "지브리 스타일의 평화로운 숲속 마을",
  "우주복을 입고 달 위에서 서핑하는 강아지",
  "눈 덮인 산 위에 핀 불꽃 같은 꽃",
  "바닷속 깊은 곳에 있는 빛나는 고대 도시",
  "벚꽃이 날리는 일본의 오래된 신사",
  "하늘을 나는 고래와 거대한 구름 성",
  "미래 도시의 네온사인이 비치는 밤거리"
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
  standard: { w: 512, h: 912, label: "Standard", desc: "Fast generation" },
  hd: { w: 720, h: 1280, label: "HD", desc: "Balanced quality" },
  ultra: { w: 1024, h: 1824, label: "Ultra", desc: "Best for SDXL" },
};

const LANGUAGES = [
  { label: "Korean", value: "Korean", voice: "ko-KR-SunHiNeural" },
];

export default function Home() {
  // --- UI States ---
  const [activeTab, setActiveTab] = useState<"single" | "storyboard">("single");
  const [currentStep, setCurrentStep] = useState(1);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showProjectList, setShowProjectList] = useState(false); // Project Browser Modal State
  
  // --- Global Settings ---
  const [selectedStyles, setSelectedStyles] = useState<string[]>([]);
  const [resolution, setResolution] = useState<keyof typeof RESOLUTIONS>("standard");
  const [selectedLora, setSelectedLora] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("low quality, worst quality, bad anatomy, deformed, text, watermark, signature, ugly");

  // --- Logic States ---
  const [projectId, setProjectId] = useState<string | null>(null);
  const [storyTopic, setStoryTopic] = useState("");
  const [storyDuration, setStoryDuration] = useState(30);
  const [storyLanguage, setStoryLanguage] = useState("Korean");
  const [storyStructure, setStoryStructure] = useState("Free Flow"); // New state
  const [storyScenes, setStoryScenes] = useState<any[]>([]);
  const [characterDesc, setCharacterDesc] = useState("A cute character with orange hair");
  const [fixedSeed, setFixedSeed] = useState<number>(-1);
  const [characterImageUrl, setCharacterImageUrl] = useState<string | null>(null);
  const [selectedVoice, setSelectedVoice] = useState("ko-KR-SunHiNeural");
  
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS[0]);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [translatedPrompt, setTranslatedPrompt] = useState<string | null>(null);
  const [activeNegativePrompt, setActiveNegativePrompt] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [isCharLoading, setIsCharLoading] = useState(false);
  const [isStoryLoading, setIsStoryLoading] = useState(false);
  const [isAutopilotRunning, setIsAutopilotRunning] = useState(false);
  const [autopilotProgress, setAutopilotProgress] = useState(0);
  const [isVideoLoading, setIsVideoLoading] = useState(false);
  const [videoStatus, setVideoStatus] = useState("");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);
  const [previewLoadingIndex, setPreviewLoadingIndex] = useState<number | null>(null);
  const [isRandomLoading, setIsRandomLoading] = useState(false);

  const [projects, setProjects] = useState<any[]>([]);
  const [bgmList, setBgmList] = useState<any[]>([]);
  const [selectedBgm, setSelectedBgm] = useState("");
  const [producedVideos, setProducedVideos] = useState<any[]>([]);
  const [lorasList, setLorasList] = useState<string[]>([]);
  const [currentModel, setCurrentModel] = useState<string>("Loading...");
  const [playingBgm, setPlayingBgm] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const bgmPlayerRef = useRef<HTMLAudioElement | null>(null);

  const fetchData = async () => {
    try {
      const [loras, config, audios, vids, projs] = await Promise.all([
        axios.get(`${API_BASE}/loras`).catch(() => ({ data: { loras: [] } })),
        axios.get(`${API_BASE}/config`).catch(() => ({ data: { model: "Offline" } })),
        axios.get(`${API_BASE}/audio/list`).catch(() => ({ data: { audios: [] } })),
        axios.get(`${API_BASE}/video/list`).catch(() => ({ data: { videos: [] } })),
        axios.get(`${API_BASE}/projects/list`).catch(() => ({ data: { projects: [] } }))
      ]);
      setLorasList(loras.data.loras || []);
      setCurrentModel(config.data.model || "Unknown");
      setBgmList(audios.data.audios || []);
      setProducedVideos(vids.data.videos || []);
      setProjects(projs.data.projects || []);
    } catch { setCurrentModel("Disconnected"); }
  };

  useEffect(() => { fetchData(); }, []);
  useEffect(() => {
    const lang = LANGUAGES.find(l => l.value === storyLanguage);
    if (lang) setSelectedVoice(lang.voice);
  }, [storyLanguage]);

  const toggleStyle = (style: string) => {
    setSelectedStyles(prev => prev.includes(style) ? prev.filter(s => s !== style) : [...prev, style]);
  };

  const setRandomPersona = () => {
    const random = SAMPLE_PERSONAS[Math.floor(Math.random() * SAMPLE_PERSONAS.length)];
    setCharacterDesc(random);
  };

  const setRandomPrompt = async () => {
    setIsRandomLoading(true);
    try {
        const response = await axios.get(`${API_BASE}/random-prompt`);
        if (activeTab === "single") setPrompt(response.data.prompt);
        else setStoryTopic(response.data.prompt);
    } catch (err) {
        const random = SAMPLE_PROMPTS[Math.floor(Math.random() * SAMPLE_PROMPTS.length)];
        if (activeTab === "single") setPrompt(random);
        else setStoryTopic(random);
    } finally {
        setIsRandomLoading(false);
    }
  };

  const handleSaveProject = async () => {
    if (!storyTopic && storyScenes.length === 0) return;
    try {
        const res = await axios.post(`${API_BASE}/projects/save`, {
            id: projectId, title: storyTopic || "Untitled",
            data: { storyTopic, storyDuration, storyLanguage, storyScenes, characterDesc, fixedSeed, selectedStyles, aspectRatio, selectedLora, selectedVoice, negativePrompt }
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
        setStoryScenes(c.storyScenes); setCharacterDesc(c.characterDesc); setFixedSeed(c.fixedSeed);
        setSelectedStyles(c.selectedStyles || []); setAspectRatio(c.aspectRatio || "square");
        setSelectedLora(c.selectedLora || ""); setNegativePrompt(c.negativePrompt || "low quality...");
        setSelectedVoice(c.selectedVoice); setActiveTab("storyboard");
    } catch { alert("Load failed"); }
  };

  const handleGenerate = async () => {
    if (!prompt) return;
    setLoading(true); setImageUrl(null); setTranslatedPrompt(null); setActiveNegativePrompt(null);
    try {
      const size = RESOLUTIONS[resolution];
      const response = await axios.post(`${API_BASE}/generate`, {
        prompt, 
        persona: null,
        lora: selectedLora || null, 
        negative_prompt: negativePrompt,
        styles: selectedStyles, 
        width: size.w, height: size.h, 
        seed: -1
      });
      if (response.data.images?.[0]) {
        setImageUrl(`data:image/png;base64,${response.data.images[0]}`);
        setTranslatedPrompt(response.data.translated_prompt);
        setActiveNegativePrompt(response.data.negative_prompt);
      }
    } catch { alert("Error"); } finally { setLoading(false); }
  };

  const handleGenerateCharacter = async () => {
    setIsCharLoading(true);
    try {
      const size = RESOLUTIONS[resolution];
      const res = await axios.post(`${API_BASE}/generate`, {
        prompt: `Character reference: ${characterDesc}`, styles: selectedStyles, lora: selectedLora || null, width: size.w, height: size.h, seed: -1
      });
      if (res.data.images?.[0]) {
        setCharacterImageUrl(`data:image/png;base64,${res.data.images[0]}`);
        setFixedSeed(res.data.seed);
      }
    } catch { alert("Character failed"); } finally { setIsCharLoading(false); }
  };

  const handleCreateStoryboard = async () => {
    if (!storyTopic) return;
    setIsStoryLoading(true);
    try {
      const p = fixedSeed !== -1 ? `${storyTopic}. Character: ${characterDesc}` : storyTopic;
      const res = await axios.post(`${API_BASE}/storyboard/create`, {
        topic: p, duration: storyDuration, language: storyLanguage, style: selectedStyles.join(", "), structure: storyStructure
      });
      setStoryScenes(res.data.scenes || []);
      setCurrentStep(1); // Storyboard mode usually starts at step 1 in this UI
    } catch { alert("AI Planning failed"); } finally { setIsStoryLoading(false); }
  };

  const startAutopilot = async () => {
    setIsAutopilotRunning(true); setAutopilotProgress(0);
    const newScenes = [...storyScenes]; const size = RESOLUTIONS[resolution];
    const basePersona = fixedSeed !== -1 ? characterDesc : ""; // Get base persona description

    for (let i = 0; i < newScenes.length; i++) {
        try {
            // Stronger prompt engineering: [Character Desc] + [Scene Action/Background]
            const combinedPrompt = basePersona 
                ? `((${basePersona})), ${newScenes[i].image_prompt}` 
                : newScenes[i].image_prompt;

            const res = await axios.post(`${API_BASE}/generate`, { 
                prompt: combinedPrompt, 
                persona: basePersona, // Still pass separately for backend optimization
                styles: selectedStyles, 
                lora: selectedLora || null, 
                width: size.w, height: size.h, 
                seed: fixedSeed // Keep the same seed for consistency
            });
            if (res.data.images?.[0]) { newScenes[i].image_url = `data:image/png;base64,${res.data.images[0]}`; setStoryScenes([...newScenes]); }
            setAutopilotProgress(((i + 1) / newScenes.length) * 100);
        } catch { console.error("Scene error"); }
    }
    setIsAutopilotRunning(false);
  };

  const handleCreateVideo = async () => {
    setIsVideoLoading(true); setVideoStatus("🎬 Rendering...");
    try {
      const res = await axios.post(`${API_BASE}/video/create`, {
        scenes: storyScenes, project_name: storyTopic.substring(0, 10).replace(/\s/g, "_") || "my_shorts",
        bgm_file: selectedBgm || null, voice: selectedVoice, width: RESOLUTIONS[resolution].w, height: RESOLUTIONS[resolution].h
      });
      setVideoUrl(res.data.video_url); fetchData();
    } catch { alert("Video failed"); } finally { setIsVideoLoading(false); setVideoStatus(""); }
  };

  const handlePreviewVoice = async (idx: number) => {
    setPreviewLoadingIndex(idx);
    try {
        const res = await axios.post(`${API_BASE}/audio/preview`, { text: storyScenes[idx].script, voice: selectedVoice });
        if (audioRef.current) { audioRef.current.src = res.data.url; audioRef.current.play(); }
    } catch { console.error("Preview fail"); } finally { setPreviewLoadingIndex(null); }
  };

  const handleRegenerateScene = async (idx: number) => {
    setRegeneratingIndex(idx);
    try {
      const scene = storyScenes[idx]; const size = RESOLUTIONS[resolution];
      const basePersona = fixedSeed !== -1 ? characterDesc : "";
      const combinedPrompt = basePersona 
        ? `((${basePersona})), ${scene.image_prompt}` 
        : scene.image_prompt;

      const res = await axios.post(`${API_BASE}/generate`, { 
        prompt: combinedPrompt, 
        persona: basePersona,
        styles: selectedStyles, 
        lora: selectedLora || null, 
        width: size.w, height: size.h, 
        seed: fixedSeed 
      });
      if (res.data.images?.[0]) {
        const updated = [...storyScenes]; updated[idx].image_url = `data:image/png;base64,${res.data.images[0]}`;
        setStoryScenes(updated);
      }
    } catch { alert("Regen fail"); } finally { setRegeneratingIndex(null); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center p-8 bg-zinc-50 dark:bg-black font-sans text-zinc-900 dark:text-zinc-100 pb-20">
      <audio ref={audioRef} hidden />
      <audio ref={bgmPlayerRef} hidden onEnded={() => setPlayingBgm(null)} />

      <main className="flex w-full max-w-4xl flex-col items-center gap-6 mt-10">
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

        <div className="flex items-center gap-2 p-1 bg-zinc-200 dark:bg-zinc-800 rounded-xl mb-4 shadow-inner">
          <button onClick={() => setActiveTab("single")} className={`px-6 py-2.5 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${activeTab === "single" ? "bg-white dark:bg-zinc-950 text-zinc-900 dark:text-white shadow-sm" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"}`}><LucideImage className="w-4 h-4" /> Single Image</button>
          <button onClick={() => setActiveTab("storyboard")} className={`px-6 py-2.5 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${activeTab === "storyboard" ? "bg-white dark:bg-zinc-950 text-zinc-900 dark:text-white shadow-sm" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"}`}><Clapperboard className="w-4 h-4" /> Storyboard Mode</button>
        </div>

        {activeTab === "storyboard" ? (
          <div className="w-full flex flex-col gap-10">
            {/* Step 1: Persona */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
                <div className="flex items-center justify-between px-1">
                    <label className="text-sm font-bold flex items-center gap-2"><User className="w-4 h-4" /> Step 1: Define Protagonist</label>
                    <button onClick={setRandomPersona} className="text-[10px] font-bold flex items-center gap-1 text-zinc-400 hover:text-zinc-800 transition-colors">
                        <Dices className="w-3.5 h-3.5" /> Suggest Persona
                    </button>
                </div>
                <textarea className="w-full p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none text-sm resize-none focus:ring-1 focus:ring-zinc-400 font-medium" rows={3} value={characterDesc} onChange={(e) => setCharacterDesc(e.target.value)} />
                <button onClick={handleGenerateCharacter} disabled={isCharLoading} className="w-full py-3 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-bold hover:bg-zinc-200 transition-all flex items-center justify-center gap-2">{isCharLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Generate Character</button>
              </div>
              <div className="aspect-square relative rounded-3xl overflow-hidden bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center">
                {characterImageUrl ? <><Image src={characterImageUrl} alt="Base Character" fill className="object-cover" unoptimized /><div className="absolute bottom-3 right-3 px-3 py-1 bg-black/60 backdrop-blur-md rounded-full text-[10px] text-white font-bold">Seed: {fixedSeed}</div></> : <div className="text-zinc-400 flex flex-col items-center gap-2 opacity-30"><ImageIcon className="w-12 h-12" /><p className="text-xs">Character View</p></div>}
              </div>
            </section>

            {/* Step 2: Planning */}
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
                            </select>
                            <Layout className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400 pointer-events-none" />
                        </div>
                    </div>
                    <button onClick={handleCreateStoryboard} disabled={isStoryLoading || !storyTopic} className="px-10 py-4 rounded-2xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-black uppercase tracking-widest text-xs hover:opacity-90 transition-all shadow-xl active:scale-95 flex items-center justify-center gap-2">{isStoryLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Plan Story with AI"}</button>
                </div>
              </div>
            </section>

            {/* Step 3: Editing */}
            {storyScenes.length > 0 && (
              <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between px-2 text-center md:text-left flex-wrap gap-4">
                  <h3 className="font-bold text-lg w-full md:w-auto">Storyboard Scenes</h3>
                  <div className="flex gap-2 items-center flex-wrap">
                    <div className="relative">
                        <select value={selectedVoice} onChange={(e) => setSelectedVoice(e.target.value)} className="pl-9 pr-4 py-2.5 rounded-xl bg-zinc-100 dark:bg-zinc-800 border-none text-xs font-bold appearance-none focus:ring-1 focus:ring-purple-500 cursor-pointer">
                            <option value="ko-KR-SunHiNeural">SunHi (KR)</option>
                            <option value="ko-KR-InJoonNeural">InJoon (KR)</option>
                            <option value="ko-KR-HyunsuMultilingualNeural">Hyunsu (KR)</option>
                        </select>
                        <UserCircle className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                    </div>
                    
                    {/* Enhanced BGM Selection with Preview */}
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
                                        bgmPlayerRef.current.play();
                                        setPlayingBgm(selectedBgm);
                                    }
                                }}
                                className="p-1.5 text-zinc-500 hover:text-indigo-600 transition-colors"
                            >
                                {playingBgm === selectedBgm ? <PauseCircle className="w-4 h-4" /> : <PlayCircle className="w-4 h-4" />}
                            </button>
                        )}
                    </div>

                    <button onClick={startAutopilot} disabled={isAutopilotRunning || isVideoLoading} className="px-6 py-2.5 rounded-xl bg-emerald-500 text-white font-bold hover:bg-emerald-600 transition-all flex items-center gap-2 shadow-lg">{isAutopilotRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : "Autopilot"}</button>
                    {storyScenes.every(s => s.image_url) && <button onClick={handleCreateVideo} disabled={isVideoLoading} className="px-6 py-2.5 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition-all flex items-center gap-2 shadow-lg">{isVideoLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Produce 🎬"}</button>}
                  </div>
                </div>

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
                      <div className="w-full md:w-48 aspect-square relative rounded-2xl overflow-hidden bg-zinc-100 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800 shrink-0 shadow-inner">
                        {scene.image_url ? <><Image src={scene.image_url} alt={`Scene ${idx}`} fill className="object-cover" unoptimized />{regeneratingIndex === idx && <div className="absolute inset-0 bg-black/40 flex items-center justify-center backdrop-blur-sm"><Loader2 className="w-8 h-8 animate-spin text-white" /></div>}<div className="absolute top-2 left-2"><CheckCircle2 className="w-5 h-5 text-emerald-500 drop-shadow-md bg-white rounded-full" /></div></> : <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-300 gap-2 font-bold uppercase text-[10px] opacity-20"><ImageIcon className="w-8 h-8" /> Pending</div>}
                      </div>
                      <div className="flex-1 flex flex-col gap-3">
                        <div className="flex items-center gap-3"><span className="px-2.5 py-1 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg text-[10px] font-black uppercase tracking-wider">Scene {idx + 1}</span><div className="flex items-center gap-1.5"><Clock className="w-3 h-3 text-zinc-400" /><input type="number" className="w-10 bg-transparent border-none p-0 text-xs font-bold text-zinc-500 focus:ring-0" value={scene.duration} onChange={(e) => { const ns = [...storyScenes]; ns[idx].duration = Number(e.target.value); setStoryScenes(ns); }} /> <span className="text-[10px] font-bold text-zinc-400">SEC</span></div></div>
                        <div className="space-y-3"><textarea className="w-full p-0 bg-transparent border-none text-sm font-semibold leading-relaxed focus:ring-0 resize-none text-zinc-800 dark:text-zinc-200" rows={2} value={scene.script} onChange={(e) => { const ns = [...storyScenes]; ns[idx].script = e.target.value; setStoryScenes(ns); }} />                        <div className="text-[10px] text-zinc-400 bg-zinc-50 dark:bg-zinc-950 p-3 rounded-2xl border border-zinc-100 dark:border-zinc-800">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-emerald-500 font-bold uppercase tracking-widest mr-2">Prompt</span>
                            {scene.image_prompt_ko && (
                              <div className="flex items-center gap-1 text-[9px] text-zinc-500 font-medium">
                                <Eye className="w-3 h-3" /> {scene.image_prompt_ko}
                              </div>
                            )}
                          </div>
                          <textarea 
                            className="w-full p-0 bg-transparent border-none focus:ring-0 resize-none mt-1" 
                            rows={2} 
                            value={scene.image_prompt} 
                            title={scene.image_prompt_ko || "No Korean description available"}
                            onChange={(e) => { const ns = [...storyScenes]; ns[idx].image_prompt = e.target.value; setStoryScenes(ns); }} 
                          />
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
        ) : (
          <div className="w-full flex flex-col gap-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                <div className="lg:col-span-5 flex flex-col gap-6">
                    <section className="p-5 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
                        <div className="flex items-center justify-between px-1">
                            <label className="text-xs font-bold uppercase tracking-widest text-zinc-400">Creation Prompt</label>
                            <button onClick={setRandomPrompt} disabled={isRandomLoading} className="text-[10px] font-bold flex items-center gap-1 text-zinc-400 hover:text-zinc-800 transition-colors">
                                <Dices className={`w-3.5 h-3.5 ${isRandomLoading ? "animate-spin" : ""}`} /> Suggest Prompt
                            </button>
                        </div>
                        <div className="relative">
                            <textarea className="w-full p-4 pr-12 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition-all resize-none text-sm leading-relaxed" placeholder="Describe the image..." rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={handleKeyDown} disabled={loading} />
                            <button onClick={handleGenerate} disabled={loading || !prompt} className="absolute bottom-4 right-4 p-2 rounded-xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 hover:opacity-90 active:scale-95 transition-all disabled:opacity-20 flex items-center justify-center">
                                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                            </button>
                        </div>
                    </section>
                    
                    <section className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-6">
                        <div>
                            <label className="text-xs font-bold uppercase tracking-widest text-zinc-400 mb-3 block">Resolution (9:16)</label>
                            <div className="grid grid-cols-3 gap-3">
                                {(Object.keys(RESOLUTIONS) as Array<keyof typeof RESOLUTIONS>).map((key) => {
                                    return (
                                        <button key={key} onClick={() => setResolution(key)} className={`flex flex-col items-center p-3 rounded-2xl border transition-all ${resolution === key ? "border-zinc-900 bg-zinc-900 text-white dark:border-white dark:bg-white dark:text-zinc-900 shadow-md" : "border-zinc-100 bg-zinc-50 text-zinc-400 hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-800"}`}>
                                            <span className="text-xs font-black">{RESOLUTIONS[key].label}</span>
                                            <span className="text-[9px] opacity-60 font-bold">{RESOLUTIONS[key].w}x{RESOLUTIONS[key].h}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                        <div>
                            <div className="flex items-center justify-between mb-2 px-1">
                                <label className="text-xs font-bold uppercase tracking-widest text-zinc-400 block flex items-center gap-1.5"><Palette className="w-3 h-3" /> Art Styles</label>
                                <button onClick={setRandomPrompt} disabled={isRandomLoading || loading} className="text-[10px] flex items-center gap-1 text-zinc-400 hover:text-zinc-800 transition-colors"><Dices className={`w-3 h-3 ${isRandomLoading ? "animate-spin" : ""}`} /> Random</button>
                            </div>
                            <div className="flex flex-wrap gap-2">{STYLE_PRESETS.map((style) => (<button key={style} onClick={() => toggleStyle(style)} className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${selectedStyles.includes(style) ? "bg-zinc-900 text-white border-zinc-900 dark:bg-white dark:text-zinc-900 dark:border-white" : "bg-zinc-50 text-zinc-500 border-transparent hover:border-zinc-200 dark:bg-zinc-800"}`}>{style}</button>))}</div>
                        </div>
                        <div>
                            <label className="text-xs font-bold uppercase tracking-widest text-zinc-400 mb-2 block">LoRA Model</label>
                            <div className="relative">
                                <select value={selectedLora} onChange={(e) => setSelectedLora(e.target.value)} className="w-full p-3 pl-10 rounded-xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-medium appearance-none focus:ring-1 focus:ring-zinc-400">
                                    <option value="">None (Default)</option>
                                    {lorasList.map(lora => <option key={lora} value={lora}>{lora}</option>)}
                                </select>
                                <Wand2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
                            </div>
                        </div>
                        <div>
                            <button onClick={() => setShowAdvanced(!showAdvanced)} className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 hover:text-zinc-900 flex items-center gap-1 transition-colors">{showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />} Advanced Settings</button>
                            {showAdvanced && (<div className="mt-3 p-4 bg-zinc-50 dark:bg-zinc-800 rounded-2xl animate-in fade-in slide-in-from-top-2 duration-200"><label className="text-[10px] font-bold text-zinc-400 mb-2 block uppercase">Negative Prompt</label><textarea className="w-full p-3 rounded-xl bg-white dark:bg-zinc-900 border-none text-xs leading-relaxed" rows={2} value={negativePrompt} onChange={(e) => setNegativePrompt(e.target.value)} /></div>)}
                        </div>
                    </section>
                </div>
                <div className="lg:col-span-7 flex flex-col gap-6">
                    <div className="relative w-full aspect-[9/16] overflow-hidden rounded-[32px] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm transition-all duration-500 max-w-sm mx-auto">
                        {loading ? <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-zinc-50/50 dark:bg-zinc-950/50 backdrop-blur-sm z-10"><Loader2 className="w-10 h-10 animate-spin text-zinc-400" /><p className="text-sm font-medium text-zinc-500 animate-pulse">Processing...</p></div> : !imageUrl ? <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-zinc-300 dark:text-zinc-700 font-bold uppercase text-[10px]"><ImageIcon className="w-16 h-16 opacity-20" /><p>Image Viewer</p></div> : <Image src={imageUrl} alt="Generated" fill className="object-cover animate-in fade-in zoom-in-95 duration-700" unoptimized />}
                    </div>
                    {translatedPrompt && (
                        <div className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-2">
                            <p className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Prompt Logic</p>
                            <p className="text-sm text-zinc-600 dark:text-zinc-300 italic">"{translatedPrompt}"</p>
                        </div>
                    )}
                </div>
            </div>
          </div>
        )}

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
                            projects.map((proj: any) => (
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
      </main>
    </div>
  );
}