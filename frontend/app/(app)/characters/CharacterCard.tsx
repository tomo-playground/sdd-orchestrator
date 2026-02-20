"use client";

import Link from "next/link";
import { Lock, Sparkles, Tag } from "lucide-react";
import type { Character } from "../../types";
import { resolveImageUrl } from "../../utils/url";

type Props = {
  character: Character;
};

const GENDER_ACCENT: Record<string, string> = {
  female: "from-rose-500/80 to-pink-600/80",
  male: "from-sky-500/80 to-indigo-600/80",
};
const DEFAULT_ACCENT = "from-zinc-400/80 to-zinc-500/80";

const GENDER_RING: Record<string, string> = {
  female: "group-hover:ring-rose-400/40",
  male: "group-hover:ring-sky-400/40",
};
const DEFAULT_RING = "group-hover:ring-zinc-400/40";

const GENDER_GLOW: Record<string, string> = {
  female: "group-hover:shadow-rose-500/20",
  male: "group-hover:shadow-sky-500/20",
};
const DEFAULT_GLOW = "group-hover:shadow-zinc-500/20";

export default function CharacterCard({ character: ch }: Props) {
  const imgSrc = resolveImageUrl(ch.preview_image_url);
  const loraCount = ch.loras?.length ?? 0;
  const tagCount = ch.tags?.length ?? 0;
  const gender = ch.gender ?? "unknown";
  const accent = GENDER_ACCENT[gender] ?? DEFAULT_ACCENT;
  const ring = GENDER_RING[gender] ?? DEFAULT_RING;
  const glow = GENDER_GLOW[gender] ?? DEFAULT_GLOW;

  return (
    <Link
      href={`/characters/${ch.id}`}
      className={`group relative flex flex-col overflow-hidden rounded-2xl bg-zinc-900 shadow-lg transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl ${glow} ring-2 ring-transparent ${ring}`}
    >
      {/* Image / Placeholder */}
      <div className="relative aspect-[3/4] w-full overflow-hidden bg-zinc-800">
        {imgSrc ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={imgSrc}
            alt={ch.name}
            loading="lazy"
            className="h-full w-full object-cover object-top transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <span className="text-5xl font-black text-zinc-700/60">
              {ch.name.charAt(0).toUpperCase()}
            </span>
          </div>
        )}

        {/* Gradient overlay */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

        {/* Floating badges (top-right) */}
        <div className="absolute top-2 right-2 flex flex-col gap-1">
          {ch.preview_locked && (
            <span className="flex items-center gap-1 rounded-full bg-black/50 px-2 py-0.5 text-[11px] font-medium text-amber-400 backdrop-blur-sm">
              <Lock size={10} />
              Locked
            </span>
          )}
          {loraCount > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-black/50 px-2 py-0.5 text-[11px] font-medium text-indigo-300 backdrop-blur-sm">
              <Sparkles size={10} />
              LoRA x{loraCount}
            </span>
          )}
        </div>

        {/* Bottom info overlay */}
        <div className="absolute inset-x-0 bottom-0 p-3">
          {/* Name + Gender accent bar */}
          <div className="flex items-end gap-2">
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-sm font-bold tracking-wide text-white drop-shadow-lg">
                {ch.name}
              </h3>
              <div className="mt-1 flex items-center gap-2">
                <span
                  className={`inline-block rounded-full bg-gradient-to-r ${accent} px-2 py-0.5 text-[11px] font-semibold text-white shadow-sm`}
                >
                  {gender.charAt(0).toUpperCase() + gender.slice(1)}
                </span>
                {ch.prompt_mode !== "auto" && (
                  <span className="rounded-full bg-white/15 px-2 py-0.5 text-[11px] font-medium text-zinc-200 backdrop-blur-sm">
                    {ch.prompt_mode}
                  </span>
                )}
              </div>
            </div>
            {tagCount > 0 && (
              <span className="flex shrink-0 items-center gap-1 rounded-full bg-white/15 px-2 py-0.5 text-[11px] font-medium text-zinc-300 backdrop-blur-sm">
                <Tag size={10} />
                {tagCount}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
