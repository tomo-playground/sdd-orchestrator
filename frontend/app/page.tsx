"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { Loader2, Send, Wand2, ChevronDown, ChevronUp, Palette, Dices, Monitor, Smartphone, Square as SquareIcon } from "lucide-react";
import Image from "next/image";

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

const SIZES = {
  square: { w: 512, h: 512, label: "1:1", icon: SquareIcon },
  landscape: { w: 768, h: 512, label: "3:2", icon: Monitor },
  portrait: { w: 512, h: 768, label: "2:3", icon: Smartphone },
};

export default function Home() {
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS[0]);
  const [negativePrompt, setNegativePrompt] = useState(
    "low quality, worst quality, bad anatomy, deformed, text, watermark, signature, ugly"
  );
  const [lorasList, setLorasList] = useState<string[]>([]);
  const [currentModel, setCurrentModel] = useState<string>("Loading...");
  const [selectedLora, setSelectedLora] = useState<string>("");
  const [selectedStyles, setSelectedStyles] = useState<string[]>([]);
  const [aspectRatio, setAspectRatio] = useState<keyof typeof SIZES>("square");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isRandomLoading, setIsRandomLoading] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [translatedPrompt, setTranslatedPrompt] = useState<string | null>(null);
  const [activeNegativePrompt, setActiveNegativePrompt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch data on mount
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
        console.error("Failed to fetch initial data:", err);
        setCurrentModel("Disconnected");
      }
    };
    fetchData();
  }, []);

  const toggleStyle = (style: string) => {
    setSelectedStyles((prev) =>
      prev.includes(style)
        ? prev.filter((s) => s !== style)
        : [...prev, style]
    );
  };

  const setRandomPrompt = async () => {
    setIsRandomLoading(true);
    try {
        const response = await axios.get("http://localhost:8000/random-prompt");
        setPrompt(response.data.prompt);
    } catch (err) {
        console.error("Failed to fetch random prompt:", err);
        const random = SAMPLE_PROMPTS[Math.floor(Math.random() * SAMPLE_PROMPTS.length)];
        setPrompt(random);
    } finally {
        setIsRandomLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!prompt) return;

    setLoading(true);
    setError(null);
    setImageUrl(null);
    setTranslatedPrompt(null);
    setActiveNegativePrompt(null);

    try {
      const size = SIZES[aspectRatio];
      const response = await axios.post("http://localhost:8000/generate", {
        prompt,
        lora: selectedLora || null,
        negative_prompt: negativePrompt,
        styles: selectedStyles,
        width: size.w,
        height: size.h,
      });

      const { images, translated_prompt, negative_prompt } = response.data;
      if (images && images.length > 0) {
        // SD API returns base64 strings
        setImageUrl(`data:image/png;base64,${images[0]}`);
        setTranslatedPrompt(translated_prompt);
        setActiveNegativePrompt(negative_prompt);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to generate image. Is the backend and SD WebUI running?");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center p-8 bg-zinc-50 dark:bg-black font-sans text-zinc-900 dark:text-zinc-100">
      <main className="flex w-full max-w-2xl flex-col items-center gap-6 mt-10">
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
        <p className="text-zinc-500 dark:text-zinc-400 text-center -mt-2">
          Enter a prompt and optionally select a LoRA style.
        </p>

        <div className="w-full flex flex-col gap-5">
          
          {/* Aspect Ratio Selection */}
          <div className="w-full">
            <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 ml-1 mb-2 block flex items-center gap-1">
              Aspect Ratio
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(Object.keys(SIZES) as Array<keyof typeof SIZES>).map((key) => {
                const Icon = SIZES[key].icon;
                return (
                  <button
                    key={key}
                    onClick={() => setAspectRatio(key)}
                    disabled={loading}
                    className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border transition-all ${
                      aspectRatio === key
                        ? "bg-black text-white border-black dark:bg-white dark:text-black dark:border-white shadow-sm"
                        : "bg-white text-zinc-500 border-zinc-200 hover:border-zinc-300 dark:bg-zinc-900 dark:border-zinc-800 dark:hover:border-zinc-700"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="text-[10px] font-bold uppercase">{key} ({SIZES[key].label})</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Style Presets */}
          <div className="w-full">
            <div className="flex items-center justify-between mb-2 px-1">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 flex items-center gap-1">
                <Palette className="w-3 h-3" /> Art Styles
                </label>
                <button 
                    onClick={setRandomPrompt}
                    disabled={isRandomLoading || loading}
                    className="text-[10px] flex items-center gap-1 text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors disabled:opacity-50"
                >
                    <Dices className={`w-3 h-3 ${isRandomLoading ? "animate-spin" : ""}`} /> 
                    {isRandomLoading ? "Generating..." : "Random Prompt"}
                </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {STYLE_PRESETS.map((style) => (
                <button
                  key={style}
                  onClick={() => toggleStyle(style)}
                  disabled={loading}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all border ${
                    selectedStyles.includes(style)
                      ? "bg-black text-white border-black dark:bg-white dark:text-black dark:border-white shadow-md transform scale-105"
                      : "bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300 dark:bg-zinc-900 dark:text-zinc-400 dark:border-zinc-800 dark:hover:border-zinc-700"
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
             {/* LoRA Selection */}
            <div className="w-full">
              <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 ml-1 mb-1 block">
                LoRA Model
              </label>
              <div className="relative">
                <select
                  className="w-full p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 appearance-none focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white transition-all shadow-sm pl-10 text-sm"
                  value={selectedLora}
                  onChange={(e) => setSelectedLora(e.target.value)}
                  disabled={loading}
                >
                  <option value="">No LoRA (Default)</option>
                  {lorasList.map((lora) => (
                    <option key={lora} value={lora}>
                      {lora}
                    </option>
                  ))}
                </select>
                <Wand2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              </div>
            </div>
          </div>

          {/* Input Area */}
          <div className="w-full relative">
            <textarea
              className="w-full p-4 pr-12 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 resize-none focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white transition-all shadow-sm"
              placeholder="Describe the image you want to generate..."
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              onClick={handleGenerate}
              disabled={loading || !prompt}
              className="absolute bottom-4 right-4 p-2 rounded-full bg-black dark:bg-white text-white dark:text-black hover:opacity-80 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>

          {/* Advanced Settings (Negative Prompt) */}
          <div className="w-full">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-xs font-semibold text-zinc-500 dark:text-zinc-400 ml-1 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors"
            >
              {showAdvanced ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
              Advanced Settings
            </button>
            
            {showAdvanced && (
              <div className="mt-2 animate-in fade-in slide-in-from-top-2 duration-300">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 ml-1 mb-1 block">
                  Negative Prompt (Things to exclude)
                </label>
                <textarea
                  className="w-full p-3 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 resize-none focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white transition-all shadow-sm text-sm"
                  rows={2}
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                  disabled={loading}
                />
              </div>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="w-full p-4 text-sm text-red-500 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-900/20">
            {error}
          </div>
        )}

        {/* Result Area */}
        {(imageUrl || loading) && (
          <div className="w-full flex flex-col items-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
             <div className="relative aspect-square w-full max-w-[512px] overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-900 shadow-lg">
              {loading ? (
                <div className="absolute inset-0 flex items-center justify-center text-zinc-400">
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 className="w-8 h-8 animate-spin" />
                    <span className="text-sm">Generating...</span>
                  </div>
                </div>
              ) : imageUrl ? (
                <Image
                  src={imageUrl}
                  alt={translatedPrompt || "Generated Image"}
                  fill
                  className="object-cover"
                  unoptimized
                />
              ) : null}
            </div>
            
            <div className="w-full text-sm text-zinc-500 px-4 space-y-2">
                {translatedPrompt && (
                    <div>
                        <span className="font-semibold text-zinc-900 dark:text-zinc-100">Positive:</span> {translatedPrompt}
                         {selectedStyles.length > 0 && <span className="block text-xs text-purple-500 mt-1"> + Styles: {selectedStyles.join(", ")}</span>}
                         {selectedLora && <span className="block text-xs text-blue-500 mt-1"> + LoRA: {selectedLora}</span>}
                    </div>
                )}
                 {activeNegativePrompt && (
                    <div className="text-xs text-zinc-400">
                        <span className="font-semibold">Negative:</span> {activeNegativePrompt}
                    </div>
                )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}