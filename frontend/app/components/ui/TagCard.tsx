"use client";

import { useState } from "react";
import type { Tag } from "../../types";
import { formatPostCount } from "./TagSuggestionDropdown";

const getCardGroupColor = (group: string | null): string => {
  switch (group) {
    case "expression":
      return "bg-amber-100";
    case "pose":
      return "bg-blue-100";
    case "camera":
      return "bg-purple-100";
    case "clothing":
      return "bg-pink-100";
    case "hair_color":
      return "bg-orange-100";
    case "hair_style":
      return "bg-teal-100";
    default:
      return "bg-zinc-100";
  }
};

export default function TagCard({ tag }: { tag: Tag }) {
  const [imgError, setImgError] = useState(false);

  return (
    <div className="group flex flex-col items-center gap-1.5 rounded-xl border border-zinc-100 bg-white p-2 transition hover:border-zinc-300 hover:shadow-sm">
      <div
        className={`flex h-[128px] w-[128px] items-center justify-center overflow-hidden rounded-lg ${
          !tag.thumbnail_url || imgError ? getCardGroupColor(tag.group_name) : ""
        }`}
      >
        {tag.thumbnail_url && !imgError ? (
          // eslint-disable-next-line @next/next/no-img-element -- external Danbooru CDN images
          <img
            src={tag.thumbnail_url}
            alt={tag.name}
            loading="lazy"
            className="h-full w-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <span className="text-sm text-zinc-400">
            {tag.name.replace(/_/g, " ")}
          </span>
        )}
      </div>
      <div className="w-full text-center">
        <div className="truncate text-xs font-medium text-zinc-700">
          {tag.name}
        </div>
        {tag.wd14_count != null && tag.wd14_count > 0 && (
          <div className="text-[11px] text-zinc-400">
            {formatPostCount(tag.wd14_count)}
          </div>
        )}
      </div>
    </div>
  );
}
