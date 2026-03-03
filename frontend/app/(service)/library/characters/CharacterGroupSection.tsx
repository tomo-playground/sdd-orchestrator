"use client";

import { ChevronDown, ChevronRight, FolderOpen, Palette, Plus } from "lucide-react";
import Link from "next/link";
import type { Character, GroupItem } from "../../../types";
import CharacterCard from "./CharacterCard";

type Props = {
  group: GroupItem;
  characters: Character[];
  isCollapsed: boolean;
  onToggle: () => void;
};

export default function CharacterGroupSection({ group, characters, isCollapsed, onToggle }: Props) {
  return (
    <section>
      {/* Section header */}
      <div className="mb-3 flex w-full items-center gap-2">
        <button
          onClick={onToggle}
          className="flex items-center gap-2 text-left"
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4 shrink-0 text-zinc-400" />
          ) : (
            <ChevronDown className="h-4 w-4 shrink-0 text-zinc-400" />
          )}
          <FolderOpen className="h-4 w-4 text-zinc-500" />
          <span className="text-sm font-semibold text-zinc-800">{group.name}</span>
          {group.style_profile_name && (
            <span className="flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-600">
              <Palette className="h-3 w-3" />
              {group.style_profile_name}
            </span>
          )}
          <span className="text-xs text-zinc-400">{characters.length}명</span>
        </button>
        <Link
          href={`/library/characters/new?group_id=${group.id}`}
          className="ml-auto flex items-center gap-1 rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-500 transition hover:bg-zinc-200"
        >
          <Plus className="h-3 w-3" />
          추가
        </Link>
      </div>

      {/* Cards grid */}
      {!isCollapsed && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {characters.map((ch) => (
            <CharacterCard key={ch.id} character={ch} />
          ))}
        </div>
      )}
    </section>
  );
}
