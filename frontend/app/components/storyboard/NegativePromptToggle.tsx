"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { NegativeSourceInfo } from "../prompt/ComposedPromptPreview";
import CopyButton from "../ui/CopyButton";
import TagAutocomplete from "../ui/TagAutocomplete";
import useTagValidationDebounced from "../../hooks/useTagValidationDebounced";
import TagValidationWarning from "../prompt/TagValidationWarning";

const SOURCE_COLORS: Record<string, { bg: string; text: string }> = {
  style_profile: { bg: "bg-fuchsia-50", text: "text-fuchsia-700" },
  character: { bg: "bg-blue-50", text: "text-blue-700" },
  scene: { bg: "bg-amber-50", text: "text-amber-700" },
};

function getSourceStyle(source: string) {
  if (source.startsWith("character:")) return SOURCE_COLORS.character;
  return SOURCE_COLORS[source] || SOURCE_COLORS.scene;
}

function getSourceLabel(source: string) {
  if (source === "style_profile") return "Style";
  if (source.startsWith("character:")) return source.replace("character:", "");
  if (source === "scene") return "Scene";
  return source;
}

type NegativePromptToggleProps = {
  negativePrompt: string;
  onChange: (value: string) => void;
  composedNegative?: string;
  negativeSources?: NegativeSourceInfo[];
};

export default function NegativePromptToggle({
  negativePrompt,
  onChange,
  composedNegative,
  negativeSources,
}: NegativePromptToggleProps) {
  const [expanded, setExpanded] = useState(false);
  const hasComposed = !!composedNegative;

  // Tag validation (only when expanded)
  const { validationResult, handleAutoReplace, clearValidation } = useTagValidationDebounced(
    negativePrompt,
    onChange,
    { enabled: expanded }
  );

  return (
    <>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase transition hover:text-zinc-600"
      >
        <ChevronDown className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
        Negative
        {hasComposed && (
          <span className="ml-1 rounded-full bg-fuchsia-100 px-1.5 py-0.5 text-[11px] font-semibold tracking-normal text-fuchsia-600 normal-case">
            Composed
          </span>
        )}
        {!expanded && !hasComposed && negativePrompt && (
          <span className="ml-1 max-w-[200px] truncate text-[11px] font-normal tracking-normal text-zinc-300 normal-case">
            {negativePrompt.slice(0, 40)}
          </span>
        )}
        {!expanded && hasComposed && (
          <span className="ml-1 max-w-[300px] truncate text-[11px] font-normal tracking-normal text-zinc-400 normal-case">
            {composedNegative.slice(0, 50)}
          </span>
        )}
      </button>

      {expanded && (
        <div className="grid gap-3">
          {/* Composed negative preview (read-only) */}
          {hasComposed && negativeSources && negativeSources.length > 0 && (
            <div className="space-y-2 rounded-xl border border-zinc-100 bg-zinc-50/50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold tracking-[0.15em] text-zinc-400 uppercase">
                  Composed Negative
                </span>
                <CopyButton text={composedNegative} variant="label" />
              </div>
              <div className="space-y-1.5">
                {negativeSources.map((src) => {
                  const style = getSourceStyle(src.source);
                  return (
                    <div key={src.source} className="flex items-start gap-2">
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${style.bg} ${style.text}`}
                      >
                        {getSourceLabel(src.source)}
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {src.tokens.map((token, idx) => (
                          <span
                            key={idx}
                            className="rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-[12px] text-zinc-600"
                          >
                            {token}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* User-editable negative prompt */}
          <div className="grid gap-2">
            <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Scene Negative (Override)
            </label>
            <TagAutocomplete
              value={negativePrompt}
              onChange={onChange}
              rows={2}
              placeholder="씬별 추가 네거티브 태그 (선택)"
              className="w-full rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
            />
            <TagValidationWarning
              result={validationResult}
              onAutoReplace={handleAutoReplace}
              onDismiss={clearValidation}
            />
          </div>
        </div>
      )}
    </>
  );
}
