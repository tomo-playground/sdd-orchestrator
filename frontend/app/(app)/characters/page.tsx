"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useCharacters } from "../../hooks/useCharacters";
import CharacterCard from "./CharacterCard";
import Button from "../../components/ui/Button";
import { CONTAINER_CLASSES, LABEL_CLASSES } from "../../components/ui/variants";

type FilterKey = "all" | "has_lora" | "has_preview" | "locked";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "has_lora", label: "Has LoRA" },
  { key: "has_preview", label: "Has Preview" },
  { key: "locked", label: "Locked" },
];

export default function CharactersPage() {
  const { characters, isLoading } = useCharacters();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");

  const filtered = useMemo(() => {
    let result = characters;

    // Search
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (ch) =>
          ch.name.toLowerCase().includes(q) ||
          ch.description?.toLowerCase().includes(q) ||
          ch.custom_base_prompt?.toLowerCase().includes(q)
      );
    }

    // Filter
    if (filter === "has_lora") result = result.filter((ch) => (ch.loras?.length ?? 0) > 0);
    if (filter === "has_preview") result = result.filter((ch) => !!ch.preview_image_url);
    if (filter === "locked") result = result.filter((ch) => ch.preview_locked);

    return result;
  }, [characters, search, filter]);

  return (
    <div className={`${CONTAINER_CLASSES} py-8`}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-lg font-bold text-zinc-900">
          Characters{characters.length > 0 ? ` (${characters.length})` : ""}
        </h1>
        <Link href="/characters/new">
          <Button size="sm">+ New Character</Button>
        </Link>
      </div>

      {/* Search + Filters */}
      <div className="mb-6 space-y-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search characters..."
          className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm transition outline-none focus:border-zinc-400"
        />
        <div className="flex gap-1.5">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                filter === key
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="py-16 text-center">
          <p className={LABEL_CLASSES}>Loading characters...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <svg
            className="h-12 w-12 text-zinc-200"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
            />
          </svg>
          <div>
            <p className="text-sm font-medium text-zinc-500">
              {characters.length === 0 ? "No characters yet" : "No characters match your filter"}
            </p>
            <p className="mt-1 text-xs text-zinc-400">
              {characters.length === 0
                ? "Characters maintain visual consistency across scenes"
                : "Try a different search or filter"}
            </p>
          </div>
          {characters.length === 0 && (
            <Link href="/characters/new">
              <Button size="md">+ New Character</Button>
            </Link>
          )}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((ch) => (
            <CharacterCard key={ch.id} character={ch} />
          ))}
        </div>
      )}
    </div>
  );
}
