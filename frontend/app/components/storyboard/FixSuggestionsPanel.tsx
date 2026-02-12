"use client";

import type { Scene, FixSuggestion } from "../../types";

type FixSuggestionsPanelProps = {
  scene: Scene;
  suggestions: FixSuggestion[];
  applySuggestion: (scene: Scene, suggestion: FixSuggestion) => void;
};

export default function FixSuggestionsPanel({
  scene,
  suggestions,
  applySuggestion,
}: FixSuggestionsPanelProps) {
  const actionableSuggestions = suggestions.filter((item) => item.action);

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-xs text-zinc-600">
      <div className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
        Fix Suggestions
      </div>
      {suggestions.length === 0 ? (
        <p className="mt-2 text-[13px] text-zinc-500">No auto suggestions.</p>
      ) : (
        <>
          {actionableSuggestions.length > 0 && (
            <button
              type="button"
              onClick={() => {
                actionableSuggestions.forEach((item) => applySuggestion(scene, item));
              }}
              className="mt-2 rounded-full border border-zinc-300 bg-white/80 px-3 py-1 text-[12px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
            >
              Apply All
            </button>
          )}
          <ul className="mt-2 grid gap-2 text-[13px]">
            {suggestions.map((item) => (
              <li
                key={`${scene.client_id}-${item.id}`}
                className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white/70 px-3 py-2"
              >
                <span className="text-zinc-600">{item.message}</span>
                {item.action ? (
                  <button
                    type="button"
                    onClick={() => applySuggestion(scene, item)}
                    className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-[12px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                  >
                    Apply
                  </button>
                ) : (
                  <span className="text-[12px] tracking-[0.2em] text-zinc-400 uppercase">
                    Manual
                  </span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
