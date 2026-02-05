"use client";

import { useCharacters } from "../../../hooks";
import { usePromptsTab } from "../hooks/usePromptsTab";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import type { Character } from "../../../types";

export default function PromptsTab() {
  const { characters } = useCharacters();
  const {
    promptHistories,
    isPromptsLoading,
    promptsFilter,
    setPromptsFilter,
    promptsCharacterFilter,
    setPromptsCharacterFilter,
    promptsSort,
    setPromptsSort,
    promptsSearch,
    setPromptsSearch,
    deletingPromptId,
    fetchPromptHistories,
    deletePromptHistory,
    togglePromptFavorite,
    applyPromptHistory,
  } = usePromptsTab();

  return (
    <section className="grid gap-4 rounded-2xl border border-zinc-200/60 bg-white p-6 shadow-sm">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={promptsFilter}
          onChange={(e) => setPromptsFilter(e.target.value as "all" | "favorites")}
          className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-medium text-zinc-600 shadow-sm transition outline-none focus:border-zinc-400"
        >
          <option value="all">All Prompts</option>
          <option value="favorites">Favorites Only</option>
        </select>
        <select
          value={promptsCharacterFilter ?? ""}
          onChange={(e) =>
            setPromptsCharacterFilter(e.target.value ? Number(e.target.value) : null)
          }
          className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-medium text-zinc-600 shadow-sm transition outline-none focus:border-zinc-400"
        >
          <option value="">All Characters</option>
          {characters.map((char: Character) => (
            <option key={char.id} value={char.id}>
              {char.name}
            </option>
          ))}
        </select>
        <select
          value={promptsSort}
          onChange={(e) => setPromptsSort(e.target.value as typeof promptsSort)}
          className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition outline-none focus:border-zinc-400"
        >
          <option value="created_at">Newest</option>
          <option value="use_count">Most Used</option>
          <option value="avg_match_rate">Highest Score</option>
        </select>
        <input
          value={promptsSearch}
          onChange={(e) => setPromptsSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && fetchPromptHistories()}
          placeholder="Search prompts..."
          className="min-w-[140px] flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2 text-[11px] outline-none focus:border-zinc-400"
        />
        <button
          type="button"
          onClick={fetchPromptHistories}
          disabled={isPromptsLoading}
          className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase shadow-sm transition disabled:cursor-not-allowed disabled:text-zinc-400"
        >
          {isPromptsLoading ? (
            <div className="flex items-center gap-2">
              <LoadingSpinner size="sm" color="text-zinc-400" />
              <span>Loading...</span>
            </div>
          ) : (
            "Search"
          )}
        </button>
      </div>

      {/* Prompt List */}
      {isPromptsLoading && promptHistories.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" color="text-zinc-400" />
        </div>
      )}

      {!isPromptsLoading && promptHistories.length === 0 && (
        <div className="rounded-2xl border border-dashed border-zinc-300 bg-zinc-50 p-12 text-center">
          <div className="mb-3 text-3xl">📝</div>
          <div className="mb-1 text-sm font-medium text-zinc-600">No saved prompts yet</div>
          <div className="text-[11px] text-zinc-400">
            Save prompts from SceneCard using the &quot;Save&quot; button
          </div>
        </div>
      )}

      {promptHistories.length > 0 && (
        <div className="grid gap-3">
          {promptHistories.map((prompt) => (
            <div
              key={prompt.id}
              className="rounded-2xl border border-zinc-200 bg-white p-4 transition hover:border-zinc-300"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex items-center gap-2">
                    <span className="truncate text-sm font-semibold text-zinc-800">
                      {prompt.name}
                    </span>
                    {prompt.is_favorite && <span className="text-xs text-amber-500">★</span>}
                    {prompt.avg_match_rate != null && (
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                        {prompt.avg_match_rate.toFixed(1)}%
                      </span>
                    )}
                  </div>
                  <p className="mb-2 line-clamp-2 text-[11px] text-zinc-500">
                    {prompt.positive_prompt}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 text-[10px] text-zinc-400">
                    <span>Used {prompt.use_count}x</span>
                    {prompt.character_id && (
                      <span className="rounded-full bg-violet-50 px-2 py-0.5 text-violet-600">
                        {characters.find((c: Character) => c.id === prompt.character_id)?.name ??
                          `Character #${prompt.character_id}`}
                      </span>
                    )}
                    {prompt.lora_settings && prompt.lora_settings.length > 0 && (
                      <span className="rounded-full bg-blue-50 px-2 py-0.5 text-blue-600">
                        {prompt.lora_settings.length} LoRA
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    onClick={() => applyPromptHistory(prompt.id)}
                    className="rounded-full bg-emerald-500 px-3 py-1.5 text-[10px] font-semibold text-white transition hover:bg-emerald-600"
                    title="Apply to current scene"
                  >
                    Apply
                  </button>
                  <button
                    type="button"
                    onClick={() => togglePromptFavorite(prompt.id)}
                    className={`rounded-full p-2 text-xs transition ${
                      prompt.is_favorite
                        ? "bg-amber-50 text-amber-500 hover:bg-amber-100"
                        : "bg-zinc-50 text-zinc-400 hover:bg-zinc-100"
                    }`}
                    title={prompt.is_favorite ? "Remove from favorites" : "Add to favorites"}
                  >
                    {prompt.is_favorite ? "★" : "☆"}
                  </button>
                  <button
                    type="button"
                    onClick={() => deletePromptHistory(prompt.id)}
                    disabled={deletingPromptId === prompt.id}
                    className="rounded-full bg-rose-50 p-2 text-xs text-rose-500 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
