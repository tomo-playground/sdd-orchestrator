"use client";

import { useRef, useState } from "react";
import { FolderOpen } from "lucide-react";
import Popover from "../ui/Popover";
import type { GroupItem } from "../../types";

type Props = {
  groups: GroupItem[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onEdit?: (group: GroupItem) => void;
  onDelete?: (group: GroupItem) => void;
  collapsed?: boolean;
};

export default function GroupDropdown({
  groups,
  currentId,
  onSelect,
  onNew,
  onEdit,
  onDelete,
  collapsed,
}: Props) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const current = groups.find((g) => g.id === currentId);

  const isEmpty = groups.length === 0;

  if (collapsed) {
    return (
      <>
        <button
          ref={btnRef}
          onClick={() => (isEmpty ? onNew() : setOpen((v) => !v))}
          title={current?.name ?? "Groups"}
          className="flex items-center justify-center rounded-lg p-1.5 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-700"
        >
          <FolderOpen className="h-4 w-4" />
        </button>
        <Popover anchorRef={btnRef} open={open} onClose={() => setOpen(false)}>
          <DropdownContent
            groups={groups}
            currentId={currentId}
            onSelect={(id) => {
              onSelect(id);
              setOpen(false);
            }}
            onEdit={
              onEdit
                ? (g) => {
                    onEdit(g);
                    setOpen(false);
                  }
                : undefined
            }
            onDelete={
              onDelete
                ? (g) => {
                    onDelete(g);
                    setOpen(false);
                  }
                : undefined
            }
          />
          <DropdownFooter
            onNew={() => {
              onNew();
              setOpen(false);
            }}
          />
        </Popover>
      </>
    );
  }

  return (
    <>
      <button
        ref={btnRef}
        onClick={() => (isEmpty ? onNew() : setOpen((v) => !v))}
        className={`flex max-w-[200px] items-center gap-1.5 truncate rounded-lg px-2 py-1 text-xs font-semibold transition ${
          isEmpty
            ? "border border-dashed border-amber-400 text-amber-600 hover:bg-amber-50"
            : "text-zinc-700 hover:bg-zinc-100"
        }`}
      >
        <FolderOpen className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{isEmpty ? "+ Add Group" : (current?.name ?? "Group")}</span>
        {!isEmpty && (
          <svg className="h-3 w-3 shrink-0 text-zinc-400" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </button>

      <Popover anchorRef={btnRef} open={open} onClose={() => setOpen(false)}>
        <DropdownContent
          groups={groups}
          currentId={currentId}
          onSelect={(id) => {
            onSelect(id);
            setOpen(false);
          }}
          onEdit={
            onEdit
              ? (g) => {
                  onEdit(g);
                  setOpen(false);
                }
              : undefined
          }
          onDelete={
            onDelete
              ? (g) => {
                  onDelete(g);
                  setOpen(false);
                }
              : undefined
          }
        />
        <DropdownFooter
          onNew={() => {
            onNew();
            setOpen(false);
          }}
        />
      </Popover>
    </>
  );
}

function DropdownContent({
  groups,
  currentId,
  onSelect,
  onEdit,
  onDelete,
}: {
  groups: GroupItem[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onEdit?: (group: GroupItem) => void;
  onDelete?: (group: GroupItem) => void;
}) {
  return (
    <div className="max-h-60 overflow-y-auto">
      {groups.map((g) => (
        <div
          key={g.id}
          className={`group/item flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition hover:bg-zinc-50 ${
            g.id === currentId ? "bg-zinc-50 font-semibold text-zinc-900" : "text-zinc-600"
          }`}
        >
          <button
            onClick={() => onSelect(g.id)}
            className="flex min-w-0 flex-1 items-center gap-2 text-left"
          >
            <FolderOpen className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
            <span className="truncate">{g.name}</span>
            {g.id === currentId && (
              <svg
                className="ml-auto h-3 w-3 shrink-0 text-zinc-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </button>
          {onEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit(g);
              }}
              className="hidden h-5 w-5 shrink-0 items-center justify-center rounded text-zinc-400 group-hover/item:flex hover:bg-zinc-100 hover:text-zinc-700"
              title="Edit group"
            >
              <svg
                className="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z"
                />
              </svg>
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(g);
              }}
              className="hidden h-5 w-5 shrink-0 items-center justify-center rounded text-zinc-400 group-hover/item:flex hover:bg-zinc-100 hover:text-red-500"
              title="Delete group"
            >
              <svg
                className="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                />
              </svg>
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function DropdownFooter({ onNew }: { onNew: () => void }) {
  return (
    <div className="border-t border-zinc-100">
      <button
        onClick={onNew}
        className="flex w-full items-center gap-1 px-3 py-2 text-left text-xs font-medium text-zinc-500 transition hover:bg-zinc-50 hover:text-zinc-700"
      >
        + New Group
      </button>
    </div>
  );
}
