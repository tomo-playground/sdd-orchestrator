"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

type Props = {
  isCreateMode: boolean;
  referenceBasePrompt: string;
  setReferenceBasePrompt: React.Dispatch<React.SetStateAction<string>>;
  referenceNegativePrompt: string;
  setReferenceNegativePrompt: (v: string) => void;
  customBasePrompt: string;
  customNegativePrompt: string;
  referenceProfileWarning: string | null;
};

const DEFAULT_NEGATIVE =
  "lowres, (bad_anatomy:1.2), (bad_hands:1.2), text, error, missing_fingers, extra_digit, fewer_digits, cropped, worst_quality, low_quality, normal_quality, jpeg_artifacts, signature, watermark, username, blurry, easynegative, verybadimagenegative_v1.3, detailed_background, scenery, outdoors, indoors";

export default function ReferencePromptsPanel({
  isCreateMode,
  referenceBasePrompt,
  setReferenceBasePrompt,
  referenceNegativePrompt,
  setReferenceNegativePrompt,
  customBasePrompt,
  customNegativePrompt,
  referenceProfileWarning,
}: Props) {
  const [isExpanded, setIsExpanded] = useState(false);

  const applyStudioSetup = () => {
    setReferenceBasePrompt((prev) => {
      const studio =
        "full_body, (standing:1.2), white_background, simple_background, solo, straight_on, facing_viewer";
      let updated = prev;
      if (!updated.includes("masterpiece")) updated = `masterpiece, best_quality, ${updated}`;
      if (!updated.includes("white_background")) updated = `${updated}, ${studio}`;
      return updated.replace(/,\s*,/g, ",").replace(/^,\s+/, "").trim();
    });
  };

  return (
    <div className="mt-4 border-t border-zinc-200 pt-6">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-controls="reference-prompts-content"
        className="mb-3 flex w-full items-center justify-between"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-zinc-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-zinc-400" />
          )}
          <div className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
          <span className="block text-sm font-bold tracking-tight text-zinc-800 uppercase">
            Reference Image Generation
          </span>
          <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[13px] font-bold text-indigo-500 uppercase">
            IP-Adapter Context
          </span>
        </div>
        <span className="rounded-full border border-zinc-100 bg-zinc-50 px-2 py-0.5 text-[13px] font-medium text-zinc-400">
          {isExpanded ? "Click to collapse" : "Click to expand"}
        </span>
      </button>

      {!isExpanded ? null : (
        <div id="reference-prompts-content" className="grid gap-4 md:grid-cols-2">
          {/* Positive */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[13px] font-bold tracking-wider text-zinc-500 uppercase">
                Reference Positive (Studio Profile)
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={applyStudioSetup}
                  className="rounded bg-indigo-50 px-1.5 py-0.5 text-[13px] font-bold text-indigo-600 transition-colors hover:bg-indigo-100 hover:text-indigo-800"
                >
                  SET STUDIO SETUP
                </button>
                {!isCreateMode && (
                  <button
                    type="button"
                    onClick={() => setReferenceBasePrompt(customBasePrompt)}
                    className="rounded bg-zinc-100 px-1.5 py-0.5 text-[13px] font-bold text-zinc-500 transition-colors hover:bg-zinc-200 hover:text-zinc-700"
                  >
                    COPY FROM SCENE ↑
                  </button>
                )}
              </div>
            </div>
            <div className="group relative">
              <textarea
                value={referenceBasePrompt}
                onChange={(e) => setReferenceBasePrompt(e.target.value)}
                rows={4}
                placeholder="masterpiece, best_quality, anime_portrait, looking_at_viewer..."
                className={`w-full rounded-2xl border ${referenceProfileWarning ? "border-indigo-200" : "border-zinc-200"} resize-none bg-zinc-50/50 px-4 py-3 font-mono text-[13px] transition-all outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50`}
              />
              {referenceProfileWarning && (
                <p className="mt-1 text-[13px] font-medium text-indigo-500 italic">
                  {referenceProfileWarning}
                </p>
              )}
              <div className="absolute right-2 bottom-2 opacity-0 transition-opacity group-hover:opacity-100">
                <span className="font-mono text-[13px] text-zinc-300">Positive</span>
              </div>
            </div>
          </div>

          {/* Negative */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[13px] font-bold tracking-wider text-zinc-500 uppercase">
                Reference Negative (Studio Profile)
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setReferenceNegativePrompt(DEFAULT_NEGATIVE)}
                  className="rounded bg-indigo-50 px-1.5 py-0.5 text-[13px] font-bold text-indigo-600 transition-colors hover:bg-indigo-100 hover:text-indigo-800"
                >
                  RESET TO DEFAULT
                </button>
                {!isCreateMode && (
                  <button
                    type="button"
                    onClick={() => setReferenceNegativePrompt(customNegativePrompt)}
                    className="rounded bg-zinc-100 px-1.5 py-0.5 text-[13px] font-bold text-zinc-500 transition-colors hover:bg-zinc-200 hover:text-zinc-700"
                  >
                    COPY FROM SCENE ↑
                  </button>
                )}
              </div>
            </div>
            <div className="group relative">
              <textarea
                value={referenceNegativePrompt}
                onChange={(e) => setReferenceNegativePrompt(e.target.value)}
                rows={4}
                placeholder="easynegative, from_side, from_behind, profile..."
                className="w-full resize-none rounded-2xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 font-mono text-[13px] transition-all outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50"
              />
              <div className="absolute right-2 bottom-2 opacity-0 transition-opacity group-hover:opacity-100">
                <span className="font-mono text-[13px] text-zinc-300">Negative</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
