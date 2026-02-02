"use client";

import { useRef, useState } from "react";
import Popover from "../ui/Popover";
import type { GroupItem } from "../../types";

type Props = {
  groups: GroupItem[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onEdit?: (group: GroupItem) => void;
};

export default function GroupDropdown({ groups, currentId, onSelect, onNew, onEdit }: Props) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const current = groups.find((g) => g.id === currentId);

  const isEmpty = groups.length === 0;

  return (
    <>
      <button
        ref={btnRef}
        onClick={() => isEmpty ? onNew() : setOpen((v) => !v)}
        className={`flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold transition truncate max-w-[140px] ${
          isEmpty
            ? "border border-dashed border-amber-400 text-amber-600 hover:bg-amber-50"
            : "text-zinc-700 hover:bg-zinc-100"
        }`}
      >
        <span className="truncate">{isEmpty ? "+ Add Group" : (current?.name ?? "Group")}</span>
        {!isEmpty && (
          <svg className="h-3 w-3 shrink-0 text-zinc-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
          </svg>
        )}
      </button>

      <Popover anchorRef={btnRef} open={open} onClose={() => setOpen(false)}>
        <div className="max-h-60 overflow-y-auto">
          {groups.map((g) => (
            <div
              key={g.id}
              className={`group/item flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition hover:bg-zinc-50 ${
                g.id === currentId ? "bg-zinc-50 font-semibold text-zinc-900" : "text-zinc-600"
              }`}
            >
              <button
                onClick={() => { onSelect(g.id); setOpen(false); }}
                className="flex-1 truncate text-left"
              >
                {g.name}
              </button>
              {onEdit && (
                <button
                  onClick={(e) => { e.stopPropagation(); onEdit(g); setOpen(false); }}
                  className="hidden shrink-0 rounded p-0.5 text-zinc-400 hover:bg-zinc-200 hover:text-zinc-600 group-hover/item:block"
                  title="Edit group"
                >
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
                  </svg>
                </button>
              )}
              {g.id === currentId && !onEdit && (
                <svg className="ml-auto h-3 w-3 shrink-0 text-zinc-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                </svg>
              )}
            </div>
          ))}
        </div>
        <div className="border-t border-zinc-100">
          <button
            onClick={() => { onNew(); setOpen(false); }}
            className="flex w-full items-center gap-1 px-3 py-2 text-left text-xs font-medium text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700 transition"
          >
            + New Group
          </button>
        </div>
      </Popover>
    </>
  );
}
