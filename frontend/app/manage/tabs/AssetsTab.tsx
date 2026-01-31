"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { API_BASE, OVERLAY_STYLES } from "../../constants";

type AudioItem = { name: string; url: string };
type FontItem = { name: string };
type LoraItem = { name: string; alias?: string };

export default function AssetsTab() {
    const [bgmList, setBgmList] = useState<AudioItem[]>([]);
    const [fontList, setFontList] = useState<FontItem[]>([]);
    const [loraList, setLoraList] = useState<LoraItem[]>([]);
    const [isPreviewingBgm, setIsPreviewingBgm] = useState(false);

    const previewAudioRef = useRef<HTMLAudioElement | null>(null);
    const previewTimeoutRef = useRef<number | null>(null);

    useEffect(() => {
        axios
            .get(`${API_BASE}/audio/list`)
            .then((res) => setBgmList(res.data.audios || []))
            .catch(() => setBgmList([]));

        axios
            .get(`${API_BASE}/sd/loras`)
            .then((res) => setLoraList(res.data.loras || []))
            .catch(() => setLoraList([]));

        axios
            .get(`${API_BASE}/fonts/list`)
            .then((res) => {
                const list = (res.data.fonts || []).map((name: string) => ({ name }));
                setFontList(list);
            })
            .catch(() => setFontList([]));

        return () => {
            stopBgmPreview();
        };
    }, []);

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

    const handlePreviewBgm = (url: string) => {
        if (!url) return;
        stopBgmPreview();
        const audio = new Audio(url);
        audio.onerror = () => {
            stopBgmPreview();
            alert(`BGM load failed: ${url}`);
        };
        previewAudioRef.current = audio;
        setIsPreviewingBgm(true);
        audio.play().catch((err) => {
            stopBgmPreview();
            alert(`BGM preview failed: ${err.message || err}`);
        });
        previewTimeoutRef.current = window.setTimeout(() => {
            stopBgmPreview();
        }, 10000);
    };

    return (
        <section className="grid gap-8 rounded-2xl border border-zinc-200/60 bg-white p-8 shadow-sm">
            {/* Overlay Styles */}
            <div className="grid gap-4">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                    <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                        Overlay Architectures
                    </span>
                    <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-bold text-indigo-500 uppercase">
                        {OVERLAY_STYLES.length} Styles
                    </span>
                </div>
                <div className="grid gap-4 grid-cols-2 md:grid-cols-4 lg:grid-cols-6">
                    {OVERLAY_STYLES.map((style) => (
                        <div
                            key={style.id}
                            className="group relative flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-2 transition-all duration-300 hover:border-indigo-300 hover:shadow-lg"
                        >
                            <div className="aspect-[9/16] overflow-hidden rounded-xl bg-zinc-50 border border-zinc-100">
                                <img
                                    src={`${API_BASE}/assets/overlay/${style.id}`}
                                    alt={style.label}
                                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
                                />
                            </div>
                            <span className="text-[10px] font-bold text-zinc-600 text-center truncate px-1">
                                {style.label}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
                {/* Fonts */}
                <div className="grid gap-4">
                    <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                        <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                            Subtitle Typography
                        </span>
                    </div>
                    {fontList.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-zinc-200 p-8 text-center bg-zinc-50/30">
                            <p className="text-xs text-zinc-400 font-medium">No fonts available.</p>
                        </div>
                    ) : (
                        <div className="grid gap-2 grid-cols-1">
                            {fontList.map((font) => (
                                <div
                                    key={font.name}
                                    className="flex items-center gap-3 rounded-2xl border border-zinc-200 bg-white px-4 py-3 transition-all duration-300 hover:border-indigo-200 hover:bg-indigo-50/10"
                                >
                                    <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-zinc-50 text-zinc-400 font-bold">
                                        Ag
                                    </div>
                                    <span className="text-xs font-bold text-zinc-700">{font.name}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* BGM */}
                <div className="grid gap-4">
                    <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                        <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                            Background Audio
                        </span>
                    </div>
                    {bgmList.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-zinc-200 p-8 text-center bg-zinc-50/30">
                            <p className="text-xs text-zinc-400 font-medium">No soundtracks found.</p>
                        </div>
                    ) : (
                        <div className="grid gap-2">
                            {bgmList.map((bgm) => (
                                <div
                                    key={bgm.name}
                                    className="group flex items-center justify-between gap-4 rounded-2xl border border-zinc-200 bg-white px-4 py-3 transition-all duration-300 hover:border-indigo-200 hover:bg-indigo-50/10"
                                >
                                    <div className="flex-1 min-w-0 flex items-center gap-3">
                                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-400">
                                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                                            </svg>
                                        </div>
                                        <span className="truncate text-xs font-bold text-zinc-700">{bgm.name}</span>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => handlePreviewBgm(bgm.url)}
                                        disabled={isPreviewingBgm}
                                        className="shrink-0 rounded-full bg-zinc-900 px-4 py-1.5 text-[9px] font-bold uppercase tracking-wider text-white transition hover:bg-indigo-600 disabled:bg-zinc-300"
                                    >
                                        {isPreviewingBgm ? "Playing..." : "Preview"}
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* LoRA Files (Internal Only) */}
            <div className="grid gap-4">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                    <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                        Internal Model Weights (LoRA)
                    </span>
                </div>
                {loraList.length === 0 ? (
                    <p className="text-xs text-zinc-400 font-medium text-center py-8">No weight files found.</p>
                ) : (
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {loraList.map((lora) => {
                            const name = lora.alias || lora.name;
                            return (
                                <div
                                    key={name}
                                    className="flex items-center justify-between gap-4 rounded-2xl border border-zinc-200 bg-white px-4 py-3 transition-all duration-300 hover:border-zinc-300 shadow-sm"
                                >
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-orange-50 text-orange-400 font-bold text-[10px]">
                                            L
                                        </div>
                                        <span className="truncate text-[11px] font-bold text-zinc-700">{name}</span>
                                    </div>
                                    <code className="shrink-0 rounded-lg bg-zinc-50 border border-zinc-100 px-2 py-1 text-[8px] font-bold text-zinc-400 uppercase">
                                        {name}
                                    </code>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </section>
    );
}
