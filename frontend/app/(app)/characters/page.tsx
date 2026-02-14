"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UserRound } from "lucide-react";
import { useCharacters } from "../../hooks/useCharacters";
import CharacterCard from "./CharacterCard";
import CharacterCardSkeleton from "./CharacterCardSkeleton";
import Button from "../../components/ui/Button";
import EmptyState from "../../components/ui/EmptyState";
import { SkeletonGrid } from "../../components/ui/Skeleton";
import {
  PAGE_TITLE_CLASSES,
  SEARCH_INPUT_CLASSES,
  FILTER_PILL_ACTIVE,
  FILTER_PILL_INACTIVE,
} from "../../components/ui/variants";

type FilterKey = "all" | "has_lora" | "has_preview" | "locked";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "has_lora", label: "Has LoRA" },
  { key: "has_preview", label: "Has Preview" },
  { key: "locked", label: "Locked" },
];

/** Redirect /characters → /library?tab=characters */
export default function CharactersPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/library?tab=characters");
  }, [router]);
  return null;
}

export function CharactersContent() {
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
    <div className="py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className={PAGE_TITLE_CLASSES}>
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
          className={SEARCH_INPUT_CLASSES}
        />
        <div className="flex gap-1.5">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${filter === key ? FILTER_PILL_ACTIVE : FILTER_PILL_INACTIVE
                }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <SkeletonGrid>{(i) => <CharacterCardSkeleton key={i} />}</SkeletonGrid>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={UserRound}
          title={characters.length === 0 ? "No characters yet" : "No characters match your filter"}
          description={
            characters.length === 0
              ? "Characters maintain visual consistency across scenes"
              : "Try a different search or filter"
          }
          action={
            characters.length === 0 ? (
              <Link href="/characters/new">
                <Button size="md">+ New Character</Button>
              </Link>
            ) : undefined
          }
        />
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
