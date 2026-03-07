"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import Link from "next/link";
import axios from "axios";
import { UserRound } from "lucide-react";
import { useCharacters } from "../../../hooks/useCharacters";
import CharacterCard from "./CharacterCard";
import CharacterCardSkeleton from "./CharacterCardSkeleton";
import CharacterGroupSection from "./CharacterGroupSection";
import Button from "../../../components/ui/Button";
import EmptyState from "../../../components/ui/EmptyState";
import { SkeletonGrid } from "../../../components/ui/Skeleton";
import { PAGE_TITLE_CLASSES, SEARCH_INPUT_CLASSES } from "../../../components/ui/variants";
import { API_BASE } from "../../../constants";
import type { GroupItem } from "../../../types";

type FilterKey = "all" | "has_lora" | "has_reference";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "has_lora", label: "Has LoRA" },
  { key: "has_reference", label: "Has Reference" },
];

export default function AdminCharactersPage() {
  const { characters, isLoading } = useCharacters();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
  const [groups, setGroups] = useState<GroupItem[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);

  const [collapsedGroups, setCollapsedGroups] = useState<Set<number>>(new Set());

  const toggleGroup = useCallback((groupId: number) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  }, []);

  useEffect(() => {
    axios
      .get<GroupItem[]>(`${API_BASE}/groups`)
      .then((res) => setGroups(res.data))
      .catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    let result = characters;

    if (selectedGroupId !== null) {
      result = result.filter((ch) => ch.group_id === selectedGroupId);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (ch) =>
          ch.name.toLowerCase().includes(q) ||
          ch.description?.toLowerCase().includes(q) ||
          ch.positive_prompt?.toLowerCase().includes(q)
      );
    }

    if (filter === "has_lora") result = result.filter((ch) => (ch.loras?.length ?? 0) > 0);
    if (filter === "has_reference") result = result.filter((ch) => !!ch.reference_image_url);

    return result;
  }, [characters, search, filter, selectedGroupId]);

  const charactersByGroup = useMemo(() => {
    if (groups.length === 0) return [];
    return groups
      .map((g) => ({
        group: g,
        chars: filtered.filter((ch) => ch.group_id === g.id),
      }))
      .filter((section) => section.chars.length > 0);
  }, [groups, filtered]);

  const useGroupView = groups.length > 0 && selectedGroupId === null && !search.trim();

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
        <div className="flex items-center gap-3">
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
          {groups.length > 0 && (
            <select
              value={selectedGroupId ?? ""}
              onChange={(e) => setSelectedGroupId(e.target.value ? Number(e.target.value) : null)}
              className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-600 transition hover:border-zinc-300 focus:border-zinc-400 focus:outline-none"
            >
              <option value="">전체 시리즈</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          )}
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
      ) : useGroupView ? (
        <div className="space-y-6">
          {charactersByGroup.map(({ group, chars }) => (
            <CharacterGroupSection
              key={group.id}
              group={group}
              characters={chars}
              isCollapsed={collapsedGroups.has(group.id)}
              onToggle={() => toggleGroup(group.id)}
            />
          ))}
        </div>
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
