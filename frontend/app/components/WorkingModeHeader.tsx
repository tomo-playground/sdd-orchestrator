"use client";

import Link from "next/link";

type WorkingModeHeaderProps = {
  onBack: () => void;
};

export default function WorkingModeHeader({ onBack }: WorkingModeHeaderProps) {
  return (
    <header className="flex flex-col gap-4">
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onBack}
          className="rounded-full border border-zinc-300 bg-white/80 px-3 py-1.5 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition hover:bg-zinc-50"
        >
          ← Back
        </button>
        <p className="text-xs tracking-[0.3em] text-zinc-500 uppercase">Shorts MVP</p>
      </div>
      <h1 className="text-4xl font-semibold tracking-tight text-zinc-900">
        Script-first storyboard studio
      </h1>
      <p className="max-w-2xl text-sm text-zinc-600">
        Start from a script, generate scene descriptions, then upload the exact images you
        want. The system only assembles and renders.
      </p>
      <Link
        href="/manage"
        className="w-fit rounded-full border border-zinc-300 bg-white/80 px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm"
      >
        Manage
      </Link>
    </header>
  );
}
