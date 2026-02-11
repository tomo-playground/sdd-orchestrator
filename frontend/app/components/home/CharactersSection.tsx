"use client";

import Link from "next/link";
import { useCharacters } from "../../hooks/useCharacters";
import { resolveImageUrl } from "../../utils/url";
import Button from "../ui/Button";
import { LABEL_CLASSES } from "../ui/variants";

export default function CharactersSection() {
  const { characters } = useCharacters();
  const recent = characters.slice(0, 3);

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className={LABEL_CLASSES}>
            Characters{characters.length > 0 ? ` (${characters.length})` : ""}
          </h2>
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[9px] font-medium text-zinc-400">
            Global
          </span>
        </div>
        <Link href="/characters">
          <Button size="sm" variant="ghost" className="shrink-0 rounded-full">
            View All &rarr;
          </Button>
        </Link>
      </div>

      {characters.length === 0 ? (
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
            <p className="text-sm font-medium text-zinc-500">No characters yet</p>
            <p className="mt-1 text-xs text-zinc-400">
              Characters maintain visual consistency across scenes
            </p>
          </div>
          <Link href="/characters/new">
            <Button size="md">+ New Character</Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {recent.map((ch) => {
            const imgSrc = resolveImageUrl(ch.preview_image_url);
            return (
              <Link
                key={ch.id}
                href={`/characters/${ch.id}`}
                className="group flex items-start gap-3 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm transition hover:shadow-md"
              >
                {imgSrc ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={imgSrc}
                    alt={ch.name}
                    className="h-14 w-14 rounded-xl bg-zinc-100 object-cover object-top"
                  />
                ) : (
                  <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-zinc-100 text-lg font-bold text-zinc-400">
                    {ch.name.charAt(0)}
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold text-zinc-900">{ch.name}</h3>
                  <p className="line-clamp-1 text-xs text-zinc-500">
                    {ch.description || ch.gender}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
