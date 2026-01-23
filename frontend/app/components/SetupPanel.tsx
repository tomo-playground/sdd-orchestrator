"use client";

import Link from "next/link";
import type { AudioItem } from "../types";
import { VOICES } from "../constants";
import LayoutSelector from "./LayoutSelector";

type SetupPanelProps = {
  topic: string;
  setTopic: (value: string) => void;
  layoutStyle: "full" | "post";
  setLayoutStyle: (value: "full" | "post") => void;
  narratorVoice: string;
  setNarratorVoice: (value: string) => void;
  bgmFile: string | null;
  setBgmFile: (value: string | null) => void;
  bgmList: AudioItem[];
  speedMultiplier: number;
  setSpeedMultiplier: (value: number) => void;
  onAutoRun: () => void;
  onManualMode: () => void;
};

export default function SetupPanel({
  topic,
  setTopic,
  layoutStyle,
  setLayoutStyle,
  narratorVoice,
  setNarratorVoice,
  bgmFile,
  setBgmFile,
  bgmList,
  speedMultiplier,
  setSpeedMultiplier,
  onAutoRun,
  onManualMode,
}: SetupPanelProps) {
  return (
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
          <LayoutSelector value={layoutStyle} onChange={setLayoutStyle} variant="compact" />

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
            onClick={onAutoRun}
            disabled={!topic.trim()}
            className="w-full rounded-full bg-gradient-to-r from-zinc-800 to-zinc-900 py-4 text-base font-semibold text-white shadow-lg transition hover:from-zinc-700 hover:to-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Auto Run
          </button>
          <button
            type="button"
            onClick={onManualMode}
            className="w-full rounded-full border border-zinc-300 bg-white py-3 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
          >
            Manual Mode
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
  );
}
