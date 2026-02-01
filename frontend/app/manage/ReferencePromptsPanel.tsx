"use client";

import React from "react";

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
  const applyStudioSetup = () => {
    setReferenceBasePrompt(prev => {
      const studio = "full_body, (standing:1.2), white_background, simple_background, solo, straight_on, facing_viewer";
      let updated = prev;
      if (!updated.includes("masterpiece")) updated = `masterpiece, best_quality, ${updated}`;
      if (!updated.includes("white_background")) updated = `${updated}, ${studio}`;
      return updated.replace(/,\s*,/g, ",").replace(/^,\s+/, "").trim();
    });
  };

  return (
    <div className="border-t border-zinc-200 pt-6 mt-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
          <label className="block text-sm font-bold text-zinc-800 uppercase tracking-tight">Reference Image Generation</label>
          <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[9px] font-bold text-indigo-500 uppercase">IP-Adapter Context</span>
        </div>
        <span className="text-[10px] text-zinc-400 font-medium bg-zinc-50 px-2 py-0.5 rounded-full border border-zinc-100">
          Determines the visual quality of the character profile image
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Positive */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Reference Positive (Studio Profile)</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={applyStudioSetup}
                className="text-[9px] text-indigo-600 hover:text-indigo-800 font-bold bg-indigo-50 hover:bg-indigo-100 px-1.5 py-0.5 rounded transition-colors"
              >
                SET STUDIO SETUP
              </button>
              {!isCreateMode && (
                <button
                  type="button"
                  onClick={() => setReferenceBasePrompt(customBasePrompt)}
                  className="text-[9px] text-zinc-500 hover:text-zinc-700 font-bold bg-zinc-100 hover:bg-zinc-200 px-1.5 py-0.5 rounded transition-colors"
                >
                  COPY FROM BASE
                </button>
              )}
            </div>
          </div>
          <div className="relative group">
            <textarea
              value={referenceBasePrompt}
              onChange={(e) => setReferenceBasePrompt(e.target.value)}
              rows={4}
              placeholder="masterpiece, best_quality, anime_portrait, looking_at_viewer..."
              className={`w-full rounded-2xl border ${referenceProfileWarning ? "border-indigo-200" : "border-zinc-200"} bg-zinc-50/50 px-4 py-3 text-[11px] outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50 font-mono resize-none transition-all`}
            />
            {referenceProfileWarning && (
              <p className="text-[10px] text-indigo-500 mt-1 font-medium italic">{referenceProfileWarning}</p>
            )}
            <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-[9px] text-zinc-300 font-mono">Positive</span>
            </div>
          </div>
        </div>

        {/* Negative */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Reference Negative (Studio Profile)</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setReferenceNegativePrompt(DEFAULT_NEGATIVE)}
                className="text-[9px] text-indigo-600 hover:text-indigo-800 font-bold bg-indigo-50 hover:bg-indigo-100 px-1.5 py-0.5 rounded transition-colors"
              >
                RESET TO DEFAULT
              </button>
              {!isCreateMode && (
                <button
                  type="button"
                  onClick={() => setReferenceNegativePrompt(customNegativePrompt)}
                  className="text-[9px] text-zinc-500 hover:text-zinc-700 font-bold bg-zinc-100 hover:bg-zinc-200 px-1.5 py-0.5 rounded transition-colors"
                >
                  COPY FROM BASE
                </button>
              )}
            </div>
          </div>
          <div className="relative group">
            <textarea
              value={referenceNegativePrompt}
              onChange={(e) => setReferenceNegativePrompt(e.target.value)}
              rows={4}
              placeholder="easynegative, from_side, from_behind, profile..."
              className="w-full rounded-2xl border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-[11px] outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50 font-mono resize-none transition-all"
            />
            <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-[9px] text-zinc-300 font-mono">Negative</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
