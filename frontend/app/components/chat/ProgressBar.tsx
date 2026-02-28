"use client";

import { Loader2 } from "lucide-react";

type Props = {
  progress: { node: string; label: string; percent: number };
};

export default function ProgressBar({ progress }: Props) {
  return (
    <div className="border-t border-zinc-100 bg-white/80 px-4 py-3 backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-500" />
        <span className="text-xs font-medium text-zinc-600">{progress.label}</span>
        <span className="ml-auto text-xs text-zinc-400">{Math.round(progress.percent)}%</span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-zinc-100">
        <div
          className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-500 transition-all duration-500 ease-out"
          style={{ width: `${Math.min(progress.percent, 100)}%` }}
        />
      </div>
    </div>
  );
}
