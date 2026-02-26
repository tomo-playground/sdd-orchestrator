"use client";

import { useState } from "react";
import type { Tag } from "../../types";
import { ERROR_TEXT } from "./variants";

export const getTagColor = (category: string) => {
  switch (category) {
    case "character":
      return "text-emerald-600";
    case "copyright":
      return "text-purple-600";
    case "artist":
      return ERROR_TEXT;
    case "meta":
      return "text-orange-600";
    case "scene":
    case "general":
      return "text-blue-600";
    default:
      return "text-zinc-600";
  }
};

export const getGroupColor = (group: string | null): string => {
  switch (group) {
    case "expression":
      return "bg-amber-200";
    case "pose":
      return "bg-blue-200";
    case "camera":
      return "bg-purple-200";
    case "clothing_top":
    case "clothing_bottom":
    case "clothing_outfit":
    case "clothing_detail":
      return "bg-pink-200";
    case "legwear":
    case "footwear":
      return "bg-rose-200";
    case "accessory":
      return "bg-fuchsia-200";
    case "action_body":
    case "action_hand":
    case "action_daily":
      return "bg-orange-200";
    case "time_of_day":
    case "weather":
    case "particle":
      return "bg-sky-200";
    case "hair_color":
      return "bg-orange-200";
    case "hair_style":
      return "bg-teal-200";
    default:
      return "bg-zinc-200";
  }
};

function TagThumbnail({ tag }: { tag: Tag }) {
  const [error, setError] = useState(false);

  if (tag.thumbnail_url && !error) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- external Danbooru CDN images
      <img
        src={tag.thumbnail_url}
        alt={tag.name}
        loading="lazy"
        width={32}
        height={32}
        className="rounded shrink-0 object-cover"
        onError={() => setError(true)}
      />
    );
  }
  return (
    <div
      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded ${getGroupColor(tag.group_name)}`}
    />
  );
}

export const formatPostCount = (count: number): string => {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${Math.round(count / 1_000)}K`;
  return String(count);
};

type TagSuggestionDropdownProps = {
  suggestions: Tag[];
  highlightedIndex: number;
  onSelect: (tag: Tag) => void;
  onHighlight: (index: number) => void;
  dropdownRef: React.RefObject<HTMLDivElement | null>;
  listboxId: string;
};

export default function TagSuggestionDropdown({
  suggestions,
  highlightedIndex,
  onSelect,
  onHighlight,
  dropdownRef,
  listboxId,
}: TagSuggestionDropdownProps) {
  return (
    <div
      ref={dropdownRef}
      className="absolute z-[var(--z-popover)] mt-1 max-h-60 w-full overflow-y-auto rounded-xl border border-zinc-200 bg-white shadow-xl"
    >
      <ul role="listbox" id={listboxId} className="grid gap-0.5 p-1">
        {suggestions.map((tag, index) => (
          <li
            key={tag.id}
            role="option"
            aria-selected={index === highlightedIndex}
            onClick={() => onSelect(tag)}
            onMouseEnter={() => onHighlight(index)}
            className={`flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-xs transition ${
              index === highlightedIndex ? "bg-zinc-100" : "hover:bg-zinc-50"
            } ${tag.is_active === false ? "opacity-50" : ""}`}
          >
            <div className="flex items-center gap-2">
              <TagThumbnail tag={tag} />
              <span
                className={`font-semibold ${getTagColor(tag.category)} ${
                  tag.is_active === false ? "line-through" : ""
                }`}
              >
                {tag.name}
              </span>
              {tag.is_active === false && tag.replacement_tag_name && (
                <span className="text-[11px] text-zinc-500">&rarr; {tag.replacement_tag_name}</span>
              )}
              {tag.is_active === false && tag.deprecated_reason && (
                <span className="text-[11px] text-zinc-400 italic">{tag.deprecated_reason}</span>
              )}
              {tag.group_name && (
                <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[12px] text-zinc-500">
                  {tag.group_name}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[12px] tracking-wide text-zinc-400 uppercase">
                {tag.category}
              </span>
              {tag.priority && tag.priority < 5 && (
                <span className="text-[12px] text-amber-500">&starf;</span>
              )}
              {tag.wd14_count != null && tag.wd14_count > 0 && (
                <span className="text-[11px] text-zinc-400 tabular-nums">
                  {formatPostCount(tag.wd14_count)}
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
      <div className="border-t border-zinc-100 bg-zinc-50 px-3 py-1.5 text-[12px] text-zinc-400">
        Use <kbd className="font-sans">&uarr;</kbd> <kbd className="font-sans">&darr;</kbd> to
        navigate, <kbd className="font-sans">Enter</kbd> to select
      </div>
    </div>
  );
}
