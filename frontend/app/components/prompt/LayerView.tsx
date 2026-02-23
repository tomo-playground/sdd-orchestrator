/**
 * LayerView — 12-Layer breakdown visualization for ComposedPromptPreview.
 * Shows each semantic layer (Quality, Identity, Expression, etc.) with its tokens.
 */

import type { ComposedLayer } from "./ComposedPromptPreview";

// Layer-specific colors (ordered by layer index visual weight)
const LAYER_COLORS: Record<string, { bg: string; text: string; border: string; label: string }> = {
  Quality: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    label: "bg-amber-100",
  },
  Subject: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    border: "border-blue-200",
    label: "bg-blue-100",
  },
  Identity: {
    bg: "bg-purple-50",
    text: "text-purple-700",
    border: "border-purple-200",
    label: "bg-purple-100",
  },
  Body: {
    bg: "bg-pink-50",
    text: "text-pink-700",
    border: "border-pink-200",
    label: "bg-pink-100",
  },
  "Main Cloth": {
    bg: "bg-teal-50",
    text: "text-teal-700",
    border: "border-teal-200",
    label: "bg-teal-100",
  },
  "Detail Cloth": {
    bg: "bg-teal-50",
    text: "text-teal-600",
    border: "border-teal-200",
    label: "bg-teal-100",
  },
  Accessory: {
    bg: "bg-cyan-50",
    text: "text-cyan-700",
    border: "border-cyan-200",
    label: "bg-cyan-100",
  },
  Expression: {
    bg: "bg-rose-50",
    text: "text-rose-700",
    border: "border-rose-200",
    label: "bg-rose-100",
  },
  Action: {
    bg: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-200",
    label: "bg-orange-100",
  },
  Camera: {
    bg: "bg-indigo-50",
    text: "text-indigo-700",
    border: "border-indigo-200",
    label: "bg-indigo-100",
  },
  Environment: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    label: "bg-emerald-100",
  },
  Atmosphere: {
    bg: "bg-violet-50",
    text: "text-violet-700",
    border: "border-violet-200",
    label: "bg-violet-100",
  },
};

const DEFAULT_COLOR = {
  bg: "bg-zinc-50",
  text: "text-zinc-600",
  border: "border-zinc-200",
  label: "bg-zinc-100",
};

type LayerViewProps = {
  layers: ComposedLayer[];
};

export default function LayerView({ layers }: LayerViewProps) {
  return (
    <div className="space-y-1.5">
      {layers.map((layer) => {
        const color = LAYER_COLORS[layer.name] || DEFAULT_COLOR;
        return (
          <div key={layer.index} className="flex items-start gap-2">
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${color.label} ${color.text}`}
              style={{ minWidth: "5.5rem", textAlign: "center" }}
            >
              {layer.name}
            </span>
            <div className="flex flex-wrap gap-1">
              {layer.tokens.map((token, idx) => (
                <span
                  key={`${layer.index}-${idx}`}
                  className={`rounded-full border px-2 py-0.5 text-[12px] ${color.bg} ${color.text} ${color.border}`}
                >
                  {token.startsWith("<lora:") ? (
                    <>
                      <span className="opacity-60">&#9889;</span>
                      {token.replace(/<lora:|>/g, "")}
                    </>
                  ) : (
                    token
                  )}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
