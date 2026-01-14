"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { 
  Loader2, Send, Wand2, ChevronDown, ChevronUp, 
  Palette, Dices, Monitor, Smartphone, Square as SquareIcon,
  Sparkles, ImageIcon, Clapperboard, Image as LucideImage, User, Clock, Music,
  Trash2, Edit3, UserCircle, RefreshCw, Volume2, Download, CheckCircle2, Globe, Play, Film
} from "lucide-react";
import Image from "next/image";

const STYLE_PRESETS = ["Chibi", "Studio Ghibli", "Photorealistic", "Cyberpunk", "Watercolor", "Pixel Art", "Oil Painting", "Cinematic", "3D Render"];
const SAMPLE_PROMPTS = ["비 오는 사이버펑크 도시의 고양이", "지브리 스타일의 평화로운 숲속 마을", "우주복을 입고 달 위에서 서핑하는 강아지"];
const SIZES = {
  square: { w: 512, h: 512, label: "1:1", icon: SquareIcon, desc: "Square" },
  landscape: { w: 768, h: 512, label: "3:2", icon: Monitor, desc: "Wide" },
  portrait: { w: 512, h: 768, label: "2:3", icon: Smartphone, desc: "Tall" },
};

const LANGUAGES = [
  { label: "Korean", value: "Korean", voice: "ko-KR-SunHiNeural" },
  { label: "English", value: "English", voice: "en-US-AriaNeural" },
  { label: "Japanese", value: "Japanese", voice: "ja-JP-NanamiNeural" },
];

export default function Home() {
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS[0]);
  const [negativePrompt, setNegativePrompt] = useState("low quality, worst quality, bad anatomy, deformed, text, watermark");
  const [lorasList, setLorasList] = useState<string[]>([]);
  const [currentModel, setCurrentModel] = useState<string>("Loading...");
  const [selectedLora, setSelectedLora] = useState("");
  const [selectedStyles, setSelectedStyles] = useState<string[]>(["Chibi"]);
  const [aspectRatio, setAspectRatio] = useState<keyof typeof SIZES>("square");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isRandomLoading, setIsRandomLoading] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [translatedPrompt, setTranslatedPrompt] = useState<string | null>(null);
  const [activeNegativePrompt, setActiveNegativePrompt] = useState<string | null>(null);
  
  const [activeTab, setActiveTab] = useState<"single" | "storyboard">("single");
  const [storyTopic, setStoryTopic] = useState("");
  const [storyDuration, setStoryDuration] = useState(30);
  const [storyLanguage, setStoryLanguage] = useState("Korean");
  const [storyScenes, setStoryScenes] = useState<any[]>([]);
  const [isStoryLoading, setIsStoryLoading] = useState(false);
  const [characterDesc, setCharacterDesc] = useState("A cute 7-year-old boy with orange hair");
  const [fixedSeed, setFixedSeed] = useState<number>(-1);
  const [characterImageUrl, setCharacterImageUrl] = useState<string | null>(null);
  const [isCharLoading, setIsCharLoading] = useState(false);
  const [autopilotProgress, setAutopilotProgress] = useState(0);
  const [isAutopilotRunning, setIsAutopilotRunning] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isVideoLoading, setIsVideoLoading] = useState(false);
  const [videoStatus, setVideoStatus] = useState("");
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);
  const [producedVideos, setProducedVideos] = useState<any[]>([]);
  
  const [bgmList, setBgmList] = useState<string[]>([]);
  const [selectedBgm, setSelectedBgm] = useState("");
  const [bgmPrompt, setBgmPrompt] = useState("lo-fi hip hop, calm piano");
  const [isBgmLoading, setIsBgmLoading] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState("ko-KR-SunHiNeural");
  const [previewLoadingIndex, setPreviewLoadingIndex] = useState<number | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  const fetchAudioList = async () => {
    try {
      const response = await axios.get("http://localhost:8000/audio/list");
      setBgmList(response.data.audios || []);
    } catch (err) { console.error("Failed to fetch audio list"); }
  };

  const fetchProducedVideos = async () => {
    try {
      const res = await axios.get("http://localhost:8000/video/list");
      setProducedVideos(res.data.videos || []);
    } catch (err) { console.error("Failed to fetch video list"); }
  };

  const fetchInitialData = async () => {
    try {
      const [lorasRes, configRes] = await Promise.all([
        axios.get("http://localhost:8000/loras"),
        axios.get("http://localhost:8000/config")
      ]);
      setLorasList(lorasRes.data.loras || []);
      setCurrentModel(configRes.data.model || "Unknown");
      await fetchAudioList();
      await fetchProducedVideos();
    } catch (err) { setCurrentModel("Disconnected"); }
  };

  useEffect(() => { fetchInitialData(); }, []);

  useEffect(() => {
    const lang = LANGUAGES.find(l => l.value === storyLanguage);
    if (lang) setSelectedVoice(lang.voice);
  }, [storyLanguage]);

  const toggleStyle = (style: string) => {
    setSelectedStyles(prev => prev.includes(style) ? prev.filter(s => s !== style) : [...prev, style]);
  };

  const updateScene = (index: number, field: string, value: any) => {
    const newScenes = [...storyScenes];
    newScenes[index] = { ...newScenes[index], [field]: value };
    setStoryScenes(newScenes);
  };

  const deleteScene = (index: number) => {
    setStoryScenes(storyScenes.filter((_, i) => i !== index));
  };

  const deleteVideo = async (filename: string) => {
    if (!confirm("Delete this video?")) return;
    try {
      await axios.delete(`http://localhost:8000/video/${filename}`);
      await fetchProducedVideos();
    } catch (err) { alert("Failed to delete"); }
  };

  const setRandomPrompt = async () => {
    setIsRandomLoading(true);
    try {
      const response = await axios.get("http://localhost:8000/random-prompt");
      setPrompt(response.data.prompt);
    } catch (err) { setPrompt(SAMPLE_PROMPTS[Math.floor(Math.random() * SAMPLE_PROMPTS.length)]); } finally { setIsRandomLoading(false); }
  };

  const handleGenerate = async () => {
    if (!prompt) return;
    setLoading(true); setError(null); setImageUrl(null);
    try {
      const size = SIZES[aspectRatio];
      const response = await axios.post("http://localhost:8000/generate", {
        prompt, lora: selectedLora || null, negative_prompt: negativePrompt,
        styles: selectedStyles, width: size.w, height: size.h, seed: -1
      });
      const { images, translated_prompt, negative_prompt } = response.data;
      if (images?.[0]) {
        setImageUrl(`data:image/png;base64,${images[0]}`);
        setTranslatedPrompt(translated_prompt);
        setActiveNegativePrompt(negative_prompt);
      }
    } catch (err) { setError("연결 실패."); } finally { setLoading(false); }
  };

  const handleRegenerateScene = async (index: number) => {
    setRegeneratingIndex(index);
    try {
      const scene = storyScenes[index];
      const size = SIZES[aspectRatio];
      const finalPrompt = fixedSeed !== -1 ? `Protagonist: ${characterDesc}, Scene: ${scene.image_prompt}` : scene.image_prompt;
      const response = await axios.post("http://localhost:8000/generate", {
        prompt: finalPrompt, styles: selectedStyles, width: size.w, height: size.h, seed: fixedSeed,
      });
      if (response.data.images?.[0]) { updateScene(index, 'image_url', `data:image/png;base64,${response.data.images[0]}`); }
    } catch (err) { setError("장면 재생성 실패."); } finally { setRegeneratingIndex(null); }
  };

  const handlePreviewVoice = async (index: number) => {
    setPreviewLoadingIndex(index);
    try {
        const response = await axios.post("http://localhost:8000/audio/preview", {
            text: storyScenes[index].script, voice: selectedVoice
        });
        if (audioRef.current) { audioRef.current.src = response.data.url; audioRef.current.play(); }
    } catch (err) { console.error("Voice preview failed"); } finally { setPreviewLoadingIndex(null); }
  };

  const handleGenerateCharacter = async () => {
    setIsCharLoading(true);
    try {
      const size = SIZES[aspectRatio];
      const response = await axios.post("http://localhost:8000/generate", {
        prompt: `Character reference: ${characterDesc}`, styles: selectedStyles, width: size.w, height: size.h, seed: -1,
      });
      if (response.data.images?.[0]) { setCharacterImageUrl(`data:image/png;base64,${response.data.images[0]}`); setFixedSeed(response.data.seed); }
    } catch (err) { setError("캐릭터 생성 실패."); } finally { setIsCharLoading(false); }
  };

  const handleCreateStoryboard = async () => {
    if (!storyTopic) return;
    setIsStoryLoading(true); setStoryScenes([]);
    try {
      const enhancedTopic = fixedSeed !== -1 ? `${storyTopic}. Main character: ${characterDesc}` : storyTopic;
      const response = await axios.post("http://localhost:8000/storyboard/create", {
        topic: enhancedTopic, duration: storyDuration, language: storyLanguage, style: selectedStyles.join(", ") || "Cinematic"
      });
      setStoryScenes(response.data.scenes);
    } catch (err) { setError("스토리보드 생성 실패."); } finally { setIsStoryLoading(false); }
  };

  const handleGenerateAudio = async () => {
    if (!bgmPrompt) return;
    setIsBgmLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/audio/generate", { prompt: bgmPrompt });
      await fetchAudioList();
      setSelectedBgm(response.data.filename);
      alert("AI 음악 생성 및 선택 완료!");
    } catch (err) { setError("AI 음악 생성 실패."); } finally { setIsBgmLoading(false); }
  };

  const startAutopilot = async () => {
    setIsAutopilotRunning(true); setAutopilotProgress(0);
    const newScenes = [...storyScenes]; const size = SIZES[aspectRatio];
    for (let i = 0; i < newScenes.length; i++) {
        try {
            const finalPrompt = fixedSeed !== -1 ? `Protagonist: ${characterDesc}, Scene: ${newScenes[i].image_prompt}` : newScenes[i].image_prompt;
            const res = await axios.post("http://localhost:8000/generate", { prompt: finalPrompt, styles: selectedStyles, width: size.w, height: size.h, seed: fixedSeed });
            if (res.data.images?.[0]) { newScenes[i].image_url = `data:image/png;base64,${res.data.images[0]}`; setStoryScenes([...newScenes]); }
            setAutopilotProgress(((i + 1) / newScenes.length) * 100);
        } catch (err) { console.error(`Scene ${i} failed`); }
    }
    setIsAutopilotRunning(false);
  };

  const handleCreateVideo = async () => {
    setIsVideoLoading(true); setVideoUrl(null); setVideoStatus("🎬 Rendering...");
    try {
      const response = await axios.post("http://localhost:8000/video/create", {
        scenes: storyScenes, project_name: storyTopic.substring(0, 10).replace(/\s/g, "_"),
        bgm_file: selectedBgm || null, voice: selectedVoice,
        width: SIZES[aspectRatio].w, height: SIZES[aspectRatio].h
      });
      setVideoUrl(response.data.video_url);
      setVideoStatus("✅ Success!");
      await fetchProducedVideos();
    } catch (err) { setError("영상 제작 실패."); setVideoStatus(""); } finally { setIsVideoLoading(false); }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans selection:bg-zinc-200 dark:selection:bg-zinc-800 pb-20">
      <audio ref={audioRef} hidden />
      <div className="max-w-5xl mx-auto px-6 py-12 flex flex-col items-center">
        
        <header className="w-full max-w-2xl mb-8 flex flex-col items-center text-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-full shadow-sm">
            <div className={`w-2 h-2 rounded-full ${currentModel === "Disconnected" ? "bg-red-500" : "bg-emerald-500 animate-pulse"}`} />
            <span className="text-[10px] font-bold uppercase tracking-tighter opacity-70">Model: {currentModel.split("[")[0]}</span>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl uppercase italic text-zinc-900 dark:text-white">Shorts Producer <span className="text-zinc-400">AI</span></h1>
        </header>

        <div className="flex items-center gap-2 p-1 bg-zinc-200 dark:bg-zinc-800 rounded-xl mb-10 shadow-inner">
          <button onClick={() => setActiveTab("single")} className={`px-6 py-2.5 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${activeTab === "single" ? "bg-white dark:bg-zinc-950 text-zinc-900 dark:text-white shadow-sm" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"}`}><LucideImage className="w-4 h-4" /> Single Image</button>
          <button onClick={() => setActiveTab("storyboard")} className={`px-6 py-2.5 rounded-lg text-sm font-bold flex items-center gap-2 transition-all ${activeTab === "storyboard" ? "bg-white dark:bg-zinc-950 text-zinc-900 dark:text-white shadow-sm" : "text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300"}`}><Clapperboard className="w-4 h-4" /> Storyboard Mode</button>
        </div>

        {activeTab === "storyboard" ? (
          <div className="w-full max-w-4xl flex flex-col gap-10">
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
                <label className="text-sm font-bold flex items-center gap-2"><User className="w-4 h-4" /> Step 1: Define Protagonist</label>
                <textarea className="w-full p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none text-sm resize-none focus:ring-1 focus:ring-zinc-400" rows={3} value={characterDesc} onChange={(e) => setCharacterDesc(e.target.value)} />
                <button onClick={handleGenerateCharacter} disabled={isCharLoading} className="w-full py-3 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-bold hover:bg-zinc-200 transition-all flex items-center justify-center gap-2">{isCharLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Generate Character</button>
              </div>
              <div className="aspect-square relative rounded-3xl overflow-hidden bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center">
                {characterImageUrl ? <><Image src={characterImageUrl} alt="Base Character" fill className="object-cover" unoptimized /><div className="absolute bottom-3 right-3 px-3 py-1 bg-black/60 backdrop-blur-md rounded-full text-[10px] text-white font-bold">Seed: {fixedSeed}</div></> : <div className="text-zinc-400 flex flex-col items-center gap-2 opacity-30"><ImageIcon className="w-12 h-12" /><p className="text-xs">Character View</p></div>}
              </div>
            </section>

            <section className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
              <label className="text-sm font-bold flex items-center gap-2"><Clapperboard className="w-4 h-4" /> Step 2: Story Planning & Language</label>
              <div className="flex flex-col md:flex-row gap-3">
                <div className="relative flex-1"><input className="w-full p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition-all text-sm" placeholder="Topic: e.g. Samurai Zombie Survival" value={storyTopic} onChange={(e) => setStoryTopic(e.target.value)} /></div>
                <div className="flex gap-2">
                    <div className="relative"><select value={storyLanguage} onChange={(e) => setStoryLanguage(e.target.value)} className="pl-9 pr-4 py-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-bold appearance-none focus:ring-1 focus:ring-zinc-400 cursor-pointer">{LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}</select><Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" /></div>
                    <div className="flex items-center gap-2 bg-zinc-50 dark:bg-zinc-800 rounded-2xl px-4 border border-zinc-100 dark:border-zinc-800"><Clock className="w-4 h-4 text-zinc-400" /><input type="number" min={10} max={60} className="w-10 bg-transparent border-none text-sm font-bold text-center focus:ring-0" value={storyDuration} onChange={(e) => setStoryDuration(Number(e.target.value))} /><span className="text-[10px] text-zinc-400 font-bold">SEC</span></div>
                </div>
                <button onClick={handleCreateStoryboard} disabled={isStoryLoading || !storyTopic} className="px-8 py-4 rounded-2xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-bold hover:opacity-90 transition-all shadow-lg">{isStoryLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Plan Story"}</button>
              </div>
            </section>

            {storyScenes.length > 0 && (
              <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between px-2 text-center md:text-left flex-wrap gap-4">
                  <h3 className="font-bold text-lg w-full md:w-auto">Storyboard Scenes</h3>
                  <div className="flex gap-2 items-center flex-wrap">
                    <div className="flex gap-1 items-center bg-zinc-100 dark:bg-zinc-800 p-1 rounded-xl border border-zinc-200 dark:border-zinc-700">
                        <input className="bg-transparent border-none text-[10px] w-24 focus:ring-0 px-2" placeholder="Music style..." value={bgmPrompt} onChange={(e) => setBgmPrompt(e.target.value)} />
                        <button onClick={handleGenerateAudio} disabled={isBgmLoading} className="px-2 py-1.5 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-[9px] font-black hover:opacity-80 flex items-center gap-1">{isBgmLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />} AI BGM</button>
                    </div>
                    <div className="relative"><select value={selectedVoice} onChange={(e) => setSelectedVoice(e.target.value)} className="pl-9 pr-4 py-2.5 rounded-xl bg-zinc-100 dark:bg-zinc-800 border-none text-xs font-bold appearance-none focus:ring-1 focus:ring-purple-500 cursor-pointer"><option value="ko-KR-SunHiNeural">SunHi (KR)</option><option value="ko-KR-InJoonNeural">InJoon (KR)</option><option value="en-US-AriaNeural">Aria (EN)</option><option value="ja-JP-NanamiNeural">Nanami (JP)</option></select><UserCircle className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" /></div>
                    <div className="relative"><select value={selectedBgm} onChange={(e) => setSelectedBgm(e.target.value)} className="pl-9 pr-4 py-2.5 rounded-xl bg-zinc-100 dark:bg-zinc-800 border-none text-xs font-bold appearance-none focus:ring-1 focus:ring-blue-500 cursor-pointer"><option value="">No BGM</option>{bgmList.map(bgm => <option key={bgm} value={bgm}>{bgm}</option>)}</select><Music className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 pointer-events-none" /></div>
                    <button onClick={startAutopilot} disabled={isAutopilotRunning || isVideoLoading} className="px-6 py-2.5 rounded-xl bg-emerald-500 text-white font-bold hover:bg-emerald-600 transition-all flex items-center gap-2 shadow-lg">{isAutopilotRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : "Autopilot"}</button>
                    {storyScenes.every(s => s.image_url) && <button onClick={handleCreateVideo} disabled={isVideoLoading} className="px-6 py-2.5 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition-all flex items-center gap-2 shadow-lg">{isVideoLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Produce 🎬"}</button>}
                  </div>
                </div>

                {videoUrl && (
                    <div className="p-8 bg-zinc-900 rounded-[40px] border border-zinc-800 shadow-2xl animate-in zoom-in-95 duration-500">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-blue-400 mb-6 block text-center">New Produced Video</label>
                        <video src={videoUrl} controls className="w-full max-w-sm mx-auto rounded-3xl shadow-2xl border border-white/10" />
                        <div className="mt-6 flex justify-center"><a href={videoUrl} download className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-2xl text-sm font-bold hover:bg-blue-700 transition-all"><Download className="w-4 h-4" /> Download MP4</a></div>
                    </div>
                )}

                {(isAutopilotRunning || isVideoLoading) && (
                    <div className="w-full bg-white dark:bg-zinc-900 p-6 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-3">
                        <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-zinc-400">
                            <span className="flex items-center gap-2 text-emerald-500"><Loader2 className="w-3 h-3 animate-spin" /> {isVideoLoading ? videoStatus : "Autopilot Active"}</span>
                            <span>{isAutopilotRunning ? `${Math.round(autopilotProgress)}%` : ""}</span>
                        </div>
                        <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden"><div className="bg-emerald-500 h-full transition-all duration-500" style={{ width: isAutopilotRunning ? `${autopilotProgress}%` : "100%" }} /></div>
                    </div>
                )}

                <div className="grid grid-cols-1 gap-4">
                  {storyScenes.map((scene, idx) => (
                    <div key={idx} className="p-5 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 flex flex-col md:flex-row gap-6 relative group transition-all hover:border-zinc-300 dark:hover:border-zinc-700">
                      <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-all">
                        <button onClick={() => handlePreviewVoice(idx)} disabled={previewLoadingIndex === idx} className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded-full text-zinc-400 hover:text-blue-500 transition-colors shadow-sm"><Volume2 className="w-4 h-4" /></button>
                        <button onClick={() => handleRegenerateScene(idx)} disabled={regeneratingIndex !== null} className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded-full text-zinc-400 hover:text-emerald-500 transition-colors shadow-sm"><RefreshCw className={`w-4 h-4 ${regeneratingIndex === idx ? "animate-spin" : ""}`} /></button>
                        <button onClick={() => deleteScene(idx)} className="p-2 bg-zinc-50 dark:bg-zinc-800 rounded-full text-zinc-400 hover:text-red-500 transition-colors shadow-sm"><Trash2 className="w-4 h-4" /></button>
                      </div>
                      <div className="w-full md:w-48 aspect-square relative rounded-2xl overflow-hidden bg-zinc-100 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800 shrink-0 shadow-inner">
                        {scene.image_url ? <><Image src={scene.image_url} alt={`Scene ${idx}`} fill className="object-cover" unoptimized />{regeneratingIndex === idx && <div className="absolute inset-0 bg-black/40 flex items-center justify-center backdrop-blur-sm"><Loader2 className="w-8 h-8 animate-spin text-white" /></div>}<div className="absolute top-2 left-2"><CheckCircle2 className="w-5 h-5 text-emerald-500 drop-shadow-md bg-white rounded-full" /></div></> : <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-300 gap-2 font-bold uppercase text-[10px] opacity-20"><ImageIcon className="w-8 h-8" /> Pending</div>}
                      </div>
                      <div className="flex-1 flex flex-col gap-3">
                        <div className="flex items-center gap-3"><span className="px-2.5 py-1 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-lg text-[10px] font-black uppercase tracking-wider">Scene {idx + 1}</span><div className="flex items-center gap-1.5"><Clock className="w-3 h-3 text-zinc-400" /><input type="number" className="w-10 bg-transparent border-none p-0 text-xs font-bold text-zinc-500 focus:ring-0" value={scene.duration} onChange={(e) => updateScene(idx, 'duration', Number(e.target.value))} /> <span className="text-[10px] font-bold text-zinc-400">SEC</span></div></div>
                        <div className="space-y-3"><textarea className="w-full p-0 bg-transparent border-none text-sm font-semibold leading-relaxed focus:ring-0 resize-none text-zinc-800 dark:text-zinc-200" rows={2} value={scene.script} onChange={(e) => updateScene(idx, 'script', e.target.value)} /><div className="text-[10px] text-zinc-400 bg-zinc-50 dark:bg-zinc-950 p-3 rounded-2xl border border-zinc-100 dark:border-zinc-800"><span className="text-emerald-500 font-bold uppercase tracking-widest mr-2">Prompt</span><textarea className="w-full p-0 bg-transparent border-none focus:ring-0 resize-none mt-1" rows={2} value={scene.image_prompt} onChange={(e) => updateScene(idx, 'image_prompt', e.target.value)} /></div></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Video Gallery */}
            {producedVideos.length > 0 && (
                <section className="mt-10 border-t border-zinc-200 dark:border-zinc-800 pt-10 w-full">
                    <h2 className="text-xl font-bold mb-6 flex items-center gap-2"><Film className="w-5 h-5 text-zinc-400" /> Produced Video Gallery</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                        {producedVideos.map((video) => (
                            <div key={video.name} className="bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 overflow-hidden group hover:shadow-xl transition-all">
                                <div className="aspect-[9/16] relative bg-black flex items-center justify-center">
                                    <video src={video.url} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" muted />
                                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all bg-black/40 backdrop-blur-sm">
                                        <div className="flex gap-3">
                                            <a href={video.url} target="_blank" className="p-3 bg-white text-black rounded-full hover:scale-110 transition-transform"><Play className="w-5 h-5 fill-current" /></a>
                                            <button onClick={() => deleteVideo(video.name)} className="p-3 bg-red-500 text-white rounded-full hover:scale-110 transition-transform"><Trash2 className="w-5 h-5" /></button>
                                        </div>
                                    </div>
                                </div>
                                <div className="p-4 flex items-center justify-between">
                                    <div className="overflow-hidden"><p className="text-xs font-bold truncate text-zinc-500">{video.name.substring(0, 20)}...</p><p className="text-[9px] text-zinc-400 font-bold uppercase">{new Date(video.created_at * 1000).toLocaleDateString()}</p></div>
                                    <a href={video.url} download className="p-2 text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors"><Download className="w-4 h-4" /></a>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            )}
          </div>
        ) : (
          <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-10">
            <div className="lg:col-span-5 flex flex-col gap-6">
              <section className="p-5 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
                <textarea className="w-full p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition-all resize-none text-sm leading-relaxed" placeholder="어떤 이미지를 만들고 싶나요?" rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={loading} />
                <button onClick={handleGenerate} disabled={loading || !prompt} className="w-full py-4 rounded-2xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-bold hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-20 flex items-center justify-center gap-2">{loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Send className="w-4 h-4" /> Generate Image</>}</button>
              </section>
              <section className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-6">
                <div>
                  <label className="text-xs font-bold uppercase tracking-widest text-zinc-400 mb-3 block">Ratio</label>
                  <div className="grid grid-cols-3 gap-3">
                    {(Object.keys(SIZES) as Array<keyof typeof SIZES>).map((key) => {
                      const Icon = SIZES[key].icon;
                      return (
                        <button key={key} onClick={() => setAspectRatio(key)} className={`flex flex-col items-center p-3 rounded-2xl border transition-all ${aspectRatio === key ? "border-zinc-900 bg-zinc-900 text-white dark:border-white dark:bg-white dark:text-zinc-900 shadow-md" : "border-zinc-100 bg-zinc-50 text-zinc-400 hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-800"}`}>
                          <Icon className="w-5 h-5 mb-1" />
                          <span className="text-[10px] font-bold">{SIZES[key].desc}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div><label className="text-xs font-bold uppercase tracking-widest text-zinc-400 mb-3 block flex items-center gap-1.5"><Palette className="w-3 h-3" /> Art Styles</label><div className="flex flex-wrap gap-2">{STYLE_PRESETS.map((style) => (<button key={style} onClick={() => toggleStyle(style)} className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${selectedStyles.includes(style) ? "bg-zinc-900 text-white border-zinc-900 dark:bg-white dark:text-zinc-900 dark:border-white" : "bg-zinc-50 text-zinc-500 border-transparent hover:border-zinc-200 dark:bg-zinc-800"}`}>{style}</button>))}</div></div>
                <div><label className="text-xs font-bold uppercase tracking-widest text-zinc-400 mb-2 block">LoRA Model</label><div className="relative"><select value={selectedLora} onChange={(e) => setSelectedLora(e.target.value)} className="w-full p-3 pl-10 rounded-xl bg-zinc-50 dark:bg-zinc-800 border-none text-xs font-medium appearance-none focus:ring-1 focus:ring-zinc-400"><option value="">None (Default)</option>{lorasList.map(lora => <option key={lora} value={lora}>{lora}</option>)}</select><Wand2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" /></div></div>
                <div><button onClick={() => setShowAdvanced(!showAdvanced)} className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 hover:text-zinc-900 flex items-center gap-1 transition-colors">{showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />} Advanced Settings</button>{showAdvanced && (<div className="mt-3 p-4 bg-zinc-50 dark:bg-zinc-800 rounded-2xl animate-in fade-in slide-in-from-top-2 duration-200"><label className="text-[10px] font-bold text-zinc-400 mb-2 block uppercase">Negative Prompt</label><textarea className="w-full p-3 rounded-xl bg-white dark:bg-zinc-900 border-none text-xs leading-relaxed" rows={2} value={negativePrompt} onChange={(e) => setNegativePrompt(e.target.value)} /></div>)}</div>
              </section>
            </div>
            <div className="lg:col-span-7 flex flex-col gap-6">
              <div className={`relative w-full overflow-hidden rounded-[32px] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm transition-all duration-500 ${aspectRatio === "landscape" ? "aspect-[3/2]" : aspectRatio === "portrait" ? "aspect-[2/3]" : "aspect-square"}`}>{loading ? <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-zinc-50/50 dark:bg-zinc-950/50 backdrop-blur-sm z-10"><Loader2 className="w-10 h-10 animate-spin text-zinc-400" /><p className="text-sm font-medium text-zinc-500 animate-pulse">Processing...</p></div> : !imageUrl ? <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-zinc-300 dark:text-zinc-700 font-bold uppercase text-[10px]"><ImageIcon className="w-16 h-16 opacity-20" /><p>Image Viewer</p></div> : <Image src={imageUrl} alt="Generated" fill className="object-cover animate-in fade-in zoom-in-95 duration-700" unoptimized />}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
