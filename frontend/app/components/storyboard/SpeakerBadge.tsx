"use client";

import { useState, useRef, useEffect } from "react";
import type { Scene } from "../../types";

type SpeakerBadgeProps = {
  speaker: Scene["speaker"];
  structure?: string;
  characterAName?: string | null;
  characterBName?: string | null;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
};

const SPEAKER_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  A: { bg: "bg-blue-100", text: "text-blue-700", label: "A" },
  B: { bg: "bg-violet-100", text: "text-violet-700", label: "B" },
  Narrator: { bg: "bg-amber-100", text: "text-amber-700", label: "N" },
};

function getAvailableSpeakers(structure?: string): Scene["speaker"][] {
  const s = structure?.toLowerCase() || "";
  if (s === "narrated dialogue") return ["A", "B", "Narrator"];
  if (s === "dialogue") return ["A", "B"];
  return ["A"];
}

function shouldShowBadge(speaker: Scene["speaker"], structure?: string): boolean {
  const s = structure?.toLowerCase() || "";
  if (speaker === "B") return true;
  if (speaker === "A" && (s === "dialogue" || s === "narrated dialogue")) return true;
  if (speaker === "Narrator" && s === "narrated dialogue") return true;
  return false;
}

export default function SpeakerBadge({
  speaker,
  structure,
  characterAName,
  characterBName,
  onSpeakerChange,
}: SpeakerBadgeProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  if (!shouldShowBadge(speaker, structure)) return null;

  const style = SPEAKER_STYLES[speaker];
  const available = getAvailableSpeakers(structure);
  const charName = speaker === "A" ? characterAName : speaker === "B" ? characterBName : null;
  const displayLabel = charName ? `${style.label} \u00B7 ${charName}` : style.label;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`rounded-full px-2 py-0.5 text-[12px] font-semibold ${style.bg} ${style.text} transition hover:opacity-80`}
      >
        {displayLabel}
      </button>
      {open && available.length > 1 && (
        <div className="absolute top-full left-0 z-20 mt-1 min-w-[120px] rounded-xl border border-zinc-200 bg-white py-1 shadow-lg">
          {available.map((s) => {
            const opt = SPEAKER_STYLES[s];
            const name = s === "A" ? characterAName : s === "B" ? characterBName : null;
            return (
              <button
                key={s}
                type="button"
                onClick={() => {
                  onSpeakerChange(s);
                  setOpen(false);
                }}
                className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition hover:bg-zinc-50 ${
                  s === speaker ? "font-semibold" : ""
                }`}
              >
                <span
                  className={`inline-block rounded-full px-1.5 py-0.5 text-[12px] font-semibold ${opt.bg} ${opt.text}`}
                >
                  {opt.label}
                </span>
                <span className="text-zinc-700">{name || s}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
