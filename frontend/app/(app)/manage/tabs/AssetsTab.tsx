"use client";

import { useState, useEffect, useRef } from "react";
import type { ReactNode } from "react";
import axios from "axios";
import { API_BASE, OVERLAY_STYLES } from "../../../constants";

type AudioItem = { name: string; url: string };
type FontItem = { name: string };
type LoraItem = { name: string; alias?: string };

/** Strip file extension and clean up display name */
function displayName(filename: string): string {
  return filename
    .replace(/\.[^.]+$/, "")
    .replace(/[-_]/g, " ")
    .replace(/\s+\d{4,}$/, "")
    .trim();
}

export default function AssetsTab() {
  const [bgmList, setBgmList] = useState<AudioItem[]>([]);
  const [fontList, setFontList] = useState<FontItem[]>([]);
  const [loraList, setLoraList] = useState<LoraItem[]>([]);
  const [playingBgm, setPlayingBgm] = useState<string | null>(null);

  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewTimeoutRef = useRef<number | null>(null);

  const stopBgmPreview = () => {
    if (previewTimeoutRef.current) {
      window.clearTimeout(previewTimeoutRef.current);
      previewTimeoutRef.current = null;
    }
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current.currentTime = 0;
    }
    setPlayingBgm(null);
  };

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
      .then((res) => setFontList(res.data.fonts || []))
      .catch(() => setFontList([]));

    return () => {
      stopBgmPreview();
    };
  }, []);

  const handlePreviewBgm = (name: string, url: string) => {
    if (!url) return;
    if (playingBgm === name) {
      stopBgmPreview();
      return;
    }
    stopBgmPreview();
    const audio = new Audio(url);
    audio.onerror = () => {
      stopBgmPreview();
      alert(`BGM load failed: ${url}`);
    };
    previewAudioRef.current = audio;
    setPlayingBgm(name);
    audio.play().catch((err) => {
      stopBgmPreview();
      alert(`BGM preview failed: ${err.message || err}`);
    });
    previewTimeoutRef.current = window.setTimeout(() => {
      stopBgmPreview();
    }, 10000);
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Overlay Architectures */}
      <AssetCard title="Overlay Architectures" count={OVERLAY_STYLES.length} countLabel="Styles">
        <div className="flex flex-wrap gap-4">
          {OVERLAY_STYLES.map((style) => (
            <div
              key={style.id}
              className="group relative flex w-28 flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-2 transition-all duration-300 hover:border-indigo-300 hover:shadow-lg"
            >
              <div className="aspect-[9/16] overflow-hidden rounded-xl border border-zinc-100 bg-zinc-50">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`${API_BASE}/assets/overlay/${style.id}`}
                  alt={style.label}
                  className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
              </div>
              <span className="truncate px-1 text-center text-[10px] font-bold text-zinc-600">
                {style.label}
              </span>
            </div>
          ))}
        </div>
      </AssetCard>

      {/* Scene Text Typography */}
      <AssetCard title="Scene Text Typography" count={fontList.length} countLabel="Fonts">
        {fontList.length === 0 ? (
          <EmptyState message="No fonts available." />
        ) : (
          <div className="grid grid-cols-1 gap-1.5">
            {fontList.map((font) => (
              <div
                key={font.name}
                className="flex min-w-0 items-center gap-2.5 rounded-xl border border-zinc-200 bg-white px-3 py-2 transition-all duration-300 hover:border-indigo-200 hover:bg-indigo-50/10"
              >
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-zinc-50 text-[10px] font-bold text-zinc-400">
                  Ag
                </div>
                <span className="truncate text-[11px] font-medium text-zinc-700">
                  {displayName(font.name)}
                </span>
              </div>
            ))}
          </div>
        )}
      </AssetCard>

      {/* Background Audio */}
      <AssetCard title="Background Audio" count={bgmList.length} countLabel="Tracks">
        {bgmList.length === 0 ? (
          <EmptyState message="No soundtracks found." />
        ) : (
          <div className="grid gap-1.5">
            {bgmList.map((bgm) => (
              <div
                key={bgm.name}
                className="group flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2 transition-all duration-300 hover:border-indigo-200 hover:bg-indigo-50/10"
              >
                <div className="flex min-w-0 flex-1 items-center gap-2.5">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-400">
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                      />
                    </svg>
                  </div>
                  <span className="truncate text-[11px] font-medium text-zinc-700">
                    {displayName(bgm.name)}
                  </span>
                </div>
                {playingBgm === bgm.name ? (
                  <button
                    type="button"
                    onClick={stopBgmPreview}
                    className="shrink-0 rounded-full bg-red-500 px-3 py-1 text-[9px] font-bold tracking-wider text-white uppercase transition hover:bg-red-600"
                  >
                    Stop
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handlePreviewBgm(bgm.name, bgm.url)}
                    className="shrink-0 rounded-full bg-zinc-900 px-3 py-1 text-[9px] font-bold tracking-wider text-white uppercase transition hover:bg-indigo-600"
                  >
                    Preview
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </AssetCard>

      {/* LoRA Weights */}
      <AssetCard title="Model Weights (LoRA)" count={loraList.length} countLabel="Files">
        {loraList.length === 0 ? (
          <EmptyState message="No weight files found." />
        ) : (
          <div className="grid gap-1.5">
            {loraList.map((lora) => {
              const name = lora.alias || lora.name;
              return (
                <div
                  key={name}
                  className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2 transition-all duration-300 hover:border-zinc-300"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-orange-50 text-[9px] font-bold text-orange-400">
                      L
                    </div>
                    <span className="truncate text-[11px] font-medium text-zinc-700">{name}</span>
                  </div>
                  <code className="shrink-0 rounded-md border border-zinc-100 bg-zinc-50 px-1.5 py-0.5 text-[7px] font-bold text-zinc-400 uppercase">
                    {name}
                  </code>
                </div>
              );
            })}
          </div>
        )}
      </AssetCard>
    </div>
  );
}

// ── Shared card wrapper ──────────────────────────────────────

function AssetCard({
  title,
  count,
  countLabel,
  children,
}: {
  title: string;
  count?: number;
  countLabel?: string;
  children: ReactNode;
}) {
  return (
    <section className="flex max-h-96 flex-col rounded-2xl border border-zinc-200/60 bg-white shadow-sm">
      <div className="flex shrink-0 items-center justify-between px-6 pt-5 pb-3">
        <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
          {title}
        </span>
        {count !== undefined && countLabel && (
          <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-bold text-indigo-500 uppercase">
            {count} {countLabel}
          </span>
        )}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto border-t border-zinc-100 px-6 py-4">
        {children}
      </div>
    </section>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/30 p-8 text-center">
      <p className="text-xs font-medium text-zinc-400">{message}</p>
    </div>
  );
}
