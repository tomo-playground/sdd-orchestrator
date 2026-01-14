"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Loader2, Send, Wand2, ChevronDown, ChevronUp, 
  Palette, Dices, Monitor, Smartphone, Square as SquareIcon,
  Sparkles, ImageIcon
} from "lucide-react";
import Image from "next/image";

const STYLE_PRESETS = [
  "Chibi", "Studio Ghibli", "Photorealistic", "Cyberpunk", 
  "Watercolor", "Pixel Art", "Oil Painting", "Cinematic", "3D Render"
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

const SIZES = {
  square: { w: 512, h: 512, label: "1:1", icon: SquareIcon, desc: "Square" },
  landscape: { w: 768, h: 512, label: "3:2", icon: Monitor, desc: "Wide" },
  portrait: { w: 512, h: 768, label: "2:3", icon: Smartphone, desc: "Tall" },
};

export default function Home() {
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS[0]);
  const [negativePrompt, setNegativePrompt] = useState("low quality, worst quality, bad anatomy, deformed, text, watermark");
  const [lorasList, setLorasList] = useState<string[]>([]);
  const [currentModel, setCurrentModel] = useState<string>("Loading...");
  const [selectedLora, setSelectedLora] = useState<string>("");
  const [selectedStyles, setSelectedStyles] = useState<string[]>(["Chibi"]);
  const [aspectRatio, setAspectRatio] = useState<keyof typeof SIZES>("square");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isRandomLoading, setIsRandomLoading] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [translatedPrompt, setTranslatedPrompt] = useState<string | null>(null);
  const [activeNegativePrompt, setActiveNegativePrompt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [lorasRes, configRes] = await Promise.all([
          axios.get("http://localhost:8000/loras"),
          axios.get("http://localhost:8000/config")
        ]);
        setLorasList(lorasRes.data.loras || []);
        setCurrentModel(configRes.data.model || "Unknown");
      } catch (err) {
        setCurrentModel("Disconnected");
      }
    };
    fetchData();
  }, []);

  const toggleStyle = (style: string) => {
    setSelectedStyles(prev => prev.includes(style) ? prev.filter(s => s !== style) : [...prev, style]);
  };

  const setRandomPrompt = async () => {
    setIsRandomLoading(true);
    try {
      const response = await axios.get("http://localhost:8000/random-prompt");
      setPrompt(response.data.prompt);
    } catch (err) {
      setPrompt(SAMPLE_PROMPTS[Math.floor(Math.random() * SAMPLE_PROMPTS.length)]);
    } finally {
      setIsRandomLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!prompt) return;
    setLoading(true);
    setError(null);
    setImageUrl(null);
    try {
      const size = SIZES[aspectRatio];
      const response = await axios.post("http://localhost:8000/generate", {
        prompt, lora: selectedLora || null, negative_prompt: negativePrompt,
        styles: selectedStyles, width: size.w, height: size.h,
      });
      const { images, translated_prompt, negative_prompt } = response.data;
      if (images?.[0]) {
        setImageUrl(`data:image/png;base64,${images[0]}`);
        setTranslatedPrompt(translated_prompt);
        setActiveNegativePrompt(negative_prompt);
      }
    } catch (err) {
      setError("연결 실패: 백엔드와 SD WebUI 상태를 확인하세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans selection:bg-zinc-200 dark:selection:bg-zinc-800">
      <div className="max-w-5xl mx-auto px-6 py-12 flex flex-col items-center">
        
        {/* Header */}
        <header className="w-full max-w-2xl mb-10 flex flex-col items-center text-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-full shadow-sm">
            <div className={`w-2 h-2 rounded-full ${currentModel === "Disconnected" ? "bg-red-500" : "bg-emerald-500 animate-pulse"}`} />
            <span className="text-[10px] font-bold uppercase tracking-tighter opacity-70">Model: {currentModel.split("[")[0]}</span>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">Shorts Producer <span className="text-zinc-400">AI</span></h1>
        </header>

        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-10">
          
          {/* Left: Controls */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            
            {/* Input Card */}
            <section className="p-5 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-bold flex items-center gap-2"><Sparkles className="w-4 h-4" /> Prompt</label>
                <button onClick={setRandomPrompt} disabled={isRandomLoading || loading} className="text-xs text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors flex items-center gap-1">
                  <Dices className={`w-3 h-3 ${isRandomLoading ? "animate-spin" : ""}`} /> Idea
                </button>
              </div>
              <textarea
                className="w-full p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800 border-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition-all resize-none text-sm leading-relaxed"
                placeholder="어떤 이미지를 만들고 싶나요?" rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={loading}
              />
              <button
                onClick={handleGenerate} disabled={loading || !prompt}
                className="w-full py-4 rounded-2xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-bold hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-20 flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Send className="w-4 h-4" /> Generate Image</>}
              </button>
            </section>

            {/* Settings Card */}
            <section className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col gap-6">
              {/* Aspect Ratio */}
              <div>
                <label className="text-xs font-bold uppercase tracking-widest text-zinc-400 mb-3 block">Ratio</label>
                <div className="grid grid-cols-3 gap-3">
                  {(Object.keys(SIZES) as Array<keyof typeof SIZES>).map((key) => {
                    const Icon = SIZES[key].icon;
                    const isActive = aspectRatio === key;
                    return (
                      <button key={key} onClick={() => setAspectRatio(key)} className={`flex flex-col items-center p-3 rounded-2xl border transition-all ${isActive ? "border-zinc-900 bg-zinc-900 text-white dark:border-white dark:bg-white dark:text-zinc-900 shadow-md" : "border-zinc-100 bg-zinc-50 text-zinc-400 hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-800"}`}>
                        <Icon className="w-5 h-5 mb-1" />
                        <span className="text-[10px] font-bold">{SIZES[key].desc}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Styles */}
              <div>
                <label className="text-xs font-bold uppercase tracking-widest text-zinc-400 mb-3 block flex items-center gap-1.5"><Palette className="w-3 h-3" /> Art Styles</label>
                <div className="flex flex-wrap gap-2">
                  {STYLE_PRESETS.map((style) => (
                    <button key={style} onClick={() => toggleStyle(style)} className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${selectedStyles.includes(style) ? "bg-zinc-900 text-white border-zinc-900 dark:bg-white dark:text-zinc-900 dark:border-white" : "bg-zinc-50 text-zinc-500 border-transparent hover:border-zinc-200 dark:bg-zinc-800"}`}>
                      {style}
                    </button>
                  ))}
                </div>
              </div>

              {/* LoRA */}
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

              {/* Advanced */}
              <div>
                <button onClick={() => setShowAdvanced(!showAdvanced)} className="text-[10px] font-bold uppercase tracking-widest text-zinc-400 hover:text-zinc-900 flex items-center gap-1 transition-colors">
                  {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />} Advanced Settings
                </button>
                {showAdvanced && (
                  <div className="mt-3 p-4 bg-zinc-50 dark:bg-zinc-800 rounded-2xl animate-in fade-in slide-in-from-top-2 duration-200">
                    <label className="text-[10px] font-bold text-zinc-400 mb-2 block uppercase">Negative Prompt</label>
                    <textarea className="w-full p-3 rounded-xl bg-white dark:bg-zinc-900 border-none text-xs leading-relaxed" rows={2} value={negativePrompt} onChange={(e) => setNegativePrompt(e.target.value)} />
                  </div>
                )}
              </div>
            </section>
          </div>

          {/* Right: Preview Area */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <div className={`relative w-full overflow-hidden rounded-[32px] bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm transition-all duration-500 ${aspectRatio === "landscape" ? "aspect-[3/2]" : aspectRatio === "portrait" ? "aspect-[2/3]" : "aspect-square"}`}>
              {loading ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-zinc-50/50 dark:bg-zinc-950/50 backdrop-blur-sm z-10">
                  <Loader2 className="w-10 h-10 animate-spin text-zinc-400" />
                  <p className="text-sm font-medium text-zinc-500 animate-pulse">상상하는 중...</p>
                </div>
              ) : !imageUrl ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-zinc-300 dark:text-zinc-700">
                  <ImageIcon className="w-16 h-16" />
                  <p className="text-sm font-medium">여기에 이미지가 생성됩니다</p>
                </div>
              ) : (
                <Image src={imageUrl} alt="Generated" fill className="object-cover animate-in fade-in zoom-in-95 duration-700" unoptimized />
              )}
            </div>

            {/* Prompt Info Card */}
            {(translatedPrompt || activeNegativePrompt) && (
              <section className="p-6 bg-white dark:bg-zinc-900 rounded-3xl border border-zinc-200 dark:border-zinc-800 shadow-sm animate-in slide-in-from-bottom-4 duration-500">
                <div className="flex flex-col gap-4">
                  <div>
                    <label className="text-[10px] font-bold uppercase tracking-widest text-emerald-500 mb-1 block">Optimized Positive</label>
                    <p className="text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">{translatedPrompt}</p>
                    {selectedStyles.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {selectedStyles.map(s => <span key={s} className="px-2 py-0.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-[9px] font-bold text-zinc-500">{s}</span>)}
                      </div>
                    )}
                  </div>
                  {activeNegativePrompt && (
                    <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-rose-500 mb-1 block">Active Negative</label>
                      <p className="text-xs leading-relaxed text-zinc-400">{activeNegativePrompt}</p>
                    </div>
                  )}
                </div>
              </section>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}