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
  speaker_1: { bg: "bg-blue-100", text: "text-blue-700", label: "1" },
  speaker_2: { bg: "bg-violet-100", text: "text-violet-700", label: "2" },
  narrator: { bg: "bg-amber-100", text: "text-amber-700", label: "N" },
};

const DEFAULT_STYLE = { bg: "bg-gray-100", text: "text-gray-700", label: "?" };

function getAvailableSpeakers(structure?: string): string[] {
  if (structure === "narrated_dialogue") return ["speaker_1", "speaker_2", "narrator"];
  if (structure === "dialogue") return ["speaker_1", "speaker_2"];
  return ["speaker_1"];
}

function shouldShowBadge(speaker: Scene["speaker"], structure?: string): boolean {
  if (speaker === "speaker_2") return true;
  if (speaker === "speaker_1" && (structure === "dialogue" || structure === "narrated_dialogue"))
    return true;
  if (speaker === "narrator" && structure === "narrated_dialogue") return true;
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

  const style = SPEAKER_STYLES[speaker] || DEFAULT_STYLE;
  const available = getAvailableSpeakers(structure);
  const charName =
    speaker === "speaker_1" ? characterAName : speaker === "speaker_2" ? characterBName : null;
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
            const opt = SPEAKER_STYLES[s] || DEFAULT_STYLE;
            const name =
              s === "speaker_1" ? characterAName : s === "speaker_2" ? characterBName : null;
            const fallbackName =
              s === "speaker_1" ? "Speaker 1" : s === "speaker_2" ? "Speaker 2" : "Narrator";
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
                <span className="text-zinc-700">{name || fallbackName}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
