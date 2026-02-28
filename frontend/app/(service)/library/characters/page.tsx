"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { UserRound } from "lucide-react";
import { useCharacters } from "../../../hooks/useCharacters";
import CharacterCard from "./CharacterCard";
import CharacterCardSkeleton from "./CharacterCardSkeleton";
import Button from "../../../components/ui/Button";
import EmptyState from "../../../components/ui/EmptyState";
import { SkeletonGrid } from "../../../components/ui/Skeleton";
import { PAGE_TITLE_CLASSES, SEARCH_INPUT_CLASSES } from "../../../components/ui/variants";

type FilterKey = "all" | "has_lora" | "has_preview" | "locked";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "has_lora", label: "Has LoRA" },
  { key: "has_preview", label: "Has Preview" },
  { key: "locked", label: "Locked" },
];

export default function AdminCharactersPage() {
  const { characters, isLoading } = useCharacters();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");

  const filtered = useMemo(() => {
    let result = characters;

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (ch) =>
          ch.name.toLowerCase().includes(q) ||
          ch.description?.toLowerCase().includes(q) ||
          ch.custom_base_prompt?.toLowerCase().includes(q),
      );
    }

    if (filter === "has_lora") result = result.filter((ch) => (ch.loras?.length ?? 0) > 0);
    if (filter === "has_preview") result = result.filter((ch) => !!ch.preview_image_url);
    if (filter === "locked") result = result.filter((ch) => ch.preview_locked);

    return result;
  }, [characters, search, filter]);

  return (
    <div className="px-8 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className={PAGE_TITLE_CLASSES}>
          Characters{characters.length > 0 ? ` (${characters.length})` : ""}
        </h1>
        <Link href="/library/characters/new">
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
            <Button
              key={key}
              onClick={() => setFilter(key)}
              variant={filter === key ? "primary" : "outline"}
              size="sm"
              className="rounded-full"
            >
              {label}
            </Button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <SkeletonGrid
          count={8}
          className="grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
        >
          {(i) => <CharacterCardSkeleton key={i} />}
        </SkeletonGrid>
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
              <Link href="/library/characters/new">
                <Button size="md">+ New Character</Button>
              </Link>
            ) : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {filtered.map((ch) => (
            <CharacterCard key={ch.id} character={ch} />
          ))}
        </div>
      )}
    </div>
  );
}
