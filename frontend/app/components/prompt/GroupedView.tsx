/**
 * GroupedView — Tokens grouped by semantic category for ComposedPromptPreview.
 */

import { LAYER_COLORS } from "./ComposedPromptPreview";

type GroupedViewProps = {
  groupedTokens: Record<string, { category: string; tokens: string[] }>;
  getTokenStyle: (token: string) => { bg: string; text: string; border: string };
};

export default function GroupedView({
  groupedTokens,
  getTokenStyle,
}: GroupedViewProps) {
  return (
    <div className="space-y-2">
      {Object.entries(groupedTokens).map(([label, group]) => (
        <div key={label} className="flex items-start gap-2">
          <span
            className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${LAYER_COLORS[group.category]?.bg || "bg-zinc-100"} ${LAYER_COLORS[group.category]?.text || "text-zinc-600"}`}
          >
            {label}
          </span>
          <div className="flex flex-wrap gap-1">
            {group.tokens.map((token, idx) => {
              const style = getTokenStyle(token);
              return (
                <span
                  key={`${label}-${idx}`}
                  className={`rounded-full border px-2 py-0.5 text-[12px] ${style.bg} ${style.text} ${style.border}`}
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
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
