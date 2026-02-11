"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMaterialsCheck } from "../../hooks/useMaterialsCheck";
import type { MaterialStatus } from "../../hooks/useMaterialsCheck";

interface MaterialsCheckSectionProps {
  storyboardId: number | null;
}

type MaterialKey = "script" | "characters" | "voice" | "music" | "background";

const MATERIALS: Array<{
  key: MaterialKey;
  label: string;
  icon: string;
  link: string;
}> = [
  { key: "script", label: "Script", icon: "📝", link: "/scripts" },
  { key: "characters", label: "Characters", icon: "👤", link: "/manage?tab=characters" },
  { key: "voice", label: "Voice", icon: "🎙", link: "/manage?tab=voice" },
  { key: "music", label: "Music", icon: "🎵", link: "/manage?tab=music" },
  { key: "background", label: "Background", icon: "🖼", link: "/backgrounds" },
];

export default function MaterialsCheckSection({ storyboardId }: MaterialsCheckSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const { data, isLoading } = useMaterialsCheck(storyboardId);
  const router = useRouter();

  const readyCount = data ? MATERIALS.filter((m) => data[m.key]?.ready).length : 0;

  return (
    <section className="rounded-xl border border-zinc-200 bg-white">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between px-5 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-800">Materials</span>
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[12px] text-zinc-500">
            {isLoading ? "..." : `${readyCount}/${MATERIALS.length}`}
          </span>
        </div>
        <svg
          className={`h-4 w-4 text-zinc-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="grid grid-cols-5 gap-2 border-t border-zinc-100 px-5 py-4">
          {MATERIALS.map((mat) => {
            const status: MaterialStatus | undefined = data?.[mat.key];
            const ready = status?.ready ?? false;

            return (
              <div
                key={mat.key}
                className={`flex flex-col items-center gap-1.5 rounded-lg border p-3 ${
                  ready ? "border-emerald-200 bg-emerald-50/50" : "border-zinc-200 bg-zinc-50"
                }`}
              >
                <span className="text-base">{mat.icon}</span>
                <span className="text-[12px] font-semibold text-zinc-600">{mat.label}</span>
                <span
                  className={`text-[11px] font-medium ${ready ? "text-emerald-600" : "text-zinc-400"}`}
                >
                  {ready ? "Ready" : "Missing"}
                </span>
                <button
                  onClick={() => router.push(mat.link)}
                  className="mt-0.5 text-[11px] font-medium text-zinc-400 transition hover:text-zinc-600"
                >
                  Open →
                </button>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
