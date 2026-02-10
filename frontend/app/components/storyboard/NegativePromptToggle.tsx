"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

type NegativePromptToggleProps = {
  negativePrompt: string;
  onChange: (value: string) => void;
};

export default function NegativePromptToggle({
  negativePrompt,
  onChange,
}: NegativePromptToggleProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase transition hover:text-zinc-600"
      >
        <ChevronDown
          className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
        />
        Negative
        {!expanded && negativePrompt && (
          <span className="ml-1 max-w-[200px] truncate text-[9px] font-normal tracking-normal text-zinc-300 normal-case">
            {negativePrompt.slice(0, 40)}
          </span>
        )}
      </button>

      {expanded && (
        <div className="grid gap-2">
          <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Negative Prompt
          </label>
          <textarea
            value={negativePrompt}
            onChange={(e) => onChange(e.target.value)}
            rows={2}
            className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
          />
        </div>
      )}
    </>
  );
}
