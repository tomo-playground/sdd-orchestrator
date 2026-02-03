"use client";

import { useEffect, useRef, useState } from "react";
import type { Character } from "../../types";
import { API_BASE } from "../../constants";

type CharacterSelectorProps = {
  characters: Character[];
  selectedCharacterId: number | null;
  onSelect: (charId: number | null) => void;
};

function resolveImageUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

function CharacterThumbnail({ src, name, size = 28 }: { src: string | null; name: string; size?: number }) {
  if (!src) {
    return (
      <div
        className="shrink-0 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-400 text-[10px] font-bold"
        style={{ width: size, height: size }}
      >
        {name.charAt(0).toUpperCase()}
      </div>
    );
  }
  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img
      src={src}
      alt={name}
      className="shrink-0 rounded-full border border-zinc-200 object-cover object-top"
      style={{ width: size, height: size }}
    />
  );
}

export default function CharacterSelector({
  characters,
  selectedCharacterId,
  onSelect,
}: CharacterSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Click outside to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Keyboard: Escape to close
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  const selectedChar = characters.find((c) => c.id === selectedCharacterId);
  const female = characters.filter((c) => c.gender === "female");
  const male = characters.filter((c) => c.gender === "male");
  const other = characters.filter((c) => c.gender !== "female" && c.gender !== "male");
  const groups = [
    { label: "Female", items: female },
    { label: "Male", items: male },
    { label: "Other", items: other },
  ].filter((g) => g.items.length > 0);

  return (
    <div ref={ref} className="relative flex-1 min-w-[200px]">
      <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase mb-1 block">
        Character
      </label>

      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`flex w-full items-center gap-2.5 rounded-2xl border px-3 py-2 text-sm outline-none transition hover:border-zinc-400 ${
          !selectedCharacterId
            ? "border-amber-300 bg-amber-50/80 text-amber-700"
            : "border-zinc-200 bg-white/80 text-zinc-800"
        }`}
      >
        {selectedChar ? (
          <>
            <CharacterThumbnail
              src={resolveImageUrl(selectedChar.preview_image_url)}
              name={selectedChar.name}
            />
            <span className="truncate">{selectedChar.name}</span>
          </>
        ) : (
          <span className="text-amber-600/70">Select Character...</span>
        )}
        <svg className="ml-auto h-4 w-4 shrink-0 opacity-40" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-2xl border border-zinc-200 bg-white shadow-xl shadow-zinc-200/50">
          {groups.map((group) => (
            <div key={group.label}>
              <div className="sticky top-0 bg-zinc-50 px-3 py-1.5 text-[10px] font-semibold tracking-[0.15em] text-zinc-400 uppercase border-b border-zinc-100">
                {group.label}
              </div>
              {group.items.map((char) => {
                const isSelected = char.id === selectedCharacterId;
                return (
                  <button
                    key={char.id}
                    type="button"
                    onClick={() => {
                      onSelect(char.id);
                      setOpen(false);
                    }}
                    className={`flex w-full items-center gap-2.5 px-3 py-2 text-sm transition hover:bg-zinc-50 ${
                      isSelected ? "bg-zinc-50 font-medium" : ""
                    }`}
                  >
                    <CharacterThumbnail
                      src={resolveImageUrl(char.preview_image_url)}
                      name={char.name}
                      size={32}
                    />
                    <span className="truncate">{char.name}</span>
                    {isSelected && (
                      <svg className="ml-auto h-4 w-4 shrink-0 text-zinc-600" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
          {characters.length === 0 && (
            <div className="px-3 py-4 text-center text-xs text-zinc-400">
              No characters available
            </div>
          )}
        </div>
      )}
    </div>
  );
}
