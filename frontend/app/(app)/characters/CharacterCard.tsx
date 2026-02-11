"use client";

import Link from "next/link";
import type { Character } from "../../types";
import { resolveImageUrl } from "../../utils/url";

type Props = {
  character: Character;
};

export default function CharacterCard({ character: ch }: Props) {
  const imgSrc = resolveImageUrl(ch.preview_image_url);

  const loraCount = ch.loras?.length ?? 0;
  const tagCount = ch.tags?.length ?? 0;

  return (
    <Link
      href={`/characters/${ch.id}`}
      className="group flex items-start gap-3 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm transition hover:border-zinc-300 hover:shadow-md"
    >
      {imgSrc ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={imgSrc}
          alt={ch.name}
          className="h-20 w-20 shrink-0 rounded-xl bg-zinc-100 object-cover object-top"
        />
      ) : (
        <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-zinc-100 text-2xl font-bold text-zinc-300">
          {ch.name.charAt(0)}
        </div>
      )}

      <div className="min-w-0 flex-1">
        <h3 className="truncate text-sm font-semibold text-zinc-900 group-hover:text-zinc-700">
          {ch.name}
        </h3>
        <p className="mt-0.5 text-xs text-zinc-500 capitalize">{ch.gender ?? "unknown"}</p>

        {/* Badges */}
        <div className="mt-2 flex flex-wrap gap-1">
          {loraCount > 0 && (
            <span className="rounded-full bg-indigo-50 px-1.5 py-0.5 text-[12px] font-medium text-indigo-600">
              LoRA x{loraCount}
            </span>
          )}
          {ch.preview_locked && (
            <span className="rounded-full bg-amber-50 px-1.5 py-0.5 text-[12px] font-medium text-amber-600">
              Locked
            </span>
          )}
          {ch.prompt_mode !== "auto" && (
            <span className="rounded-full bg-zinc-100 px-1.5 py-0.5 text-[12px] font-medium text-zinc-500">
              {ch.prompt_mode}
            </span>
          )}
          {!imgSrc && (
            <span className="rounded-full bg-rose-50 px-1.5 py-0.5 text-[12px] font-medium text-rose-400">
              No Image
            </span>
          )}
          {tagCount > 0 && (
            <span className="rounded-full bg-purple-50 px-1.5 py-0.5 text-[12px] font-medium text-purple-500">
              {tagCount} tags
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
