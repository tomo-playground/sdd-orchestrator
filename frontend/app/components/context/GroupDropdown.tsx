"use client";

import { useRef, useState, useCallback } from "react";
import { Check, ChevronDown, FolderOpen, Pencil, Trash2 } from "lucide-react";
import Popover from "../ui/Popover";
import { ALL_GROUPS_ID } from "../../constants";
import type { GroupItem } from "../../types";

type Props = {
  groups: GroupItem[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onNew: () => void;
  onEdit?: (group: GroupItem) => void;
  onDelete?: (group: GroupItem) => void;
  showAllOption?: boolean;
};

export default function GroupDropdown({
  groups,
  currentId,
  onSelect,
  onNew,
  onEdit,
  onDelete,
  showAllOption,
}: Props) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const isAll = currentId === ALL_GROUPS_ID;
  const current = isAll ? null : groups.find((g) => g.id === currentId);

  const isEmpty = groups.length === 0;

  const close = useCallback(() => setOpen(false), []);
  const wrapClose = useCallback(
    <T,>(fn?: (arg: T) => void) =>
      fn
        ? (arg: T) => {
            fn(arg);
            close();
          }
        : undefined,
    [close]
  );

  const popover = (
    <Popover anchorRef={btnRef} open={open} onClose={close}>
      <DropdownContent
        groups={groups}
        currentId={currentId}
        onSelect={wrapClose<number>(onSelect)!}
        onEdit={wrapClose<GroupItem>(onEdit)}
        onDelete={wrapClose<GroupItem>(onDelete)}
        showAllOption={showAllOption}
      />
      <DropdownFooter onNew={wrapClose<void>(onNew)!} />
    </Popover>
  );

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
        <span className="truncate">
          {isEmpty ? "+ 시리즈 추가" : isAll ? "전체 시리즈" : (current?.name ?? "시리즈")}
        </span>
        {!isEmpty && <ChevronDown className="h-3 w-3 shrink-0 text-zinc-400" />}
      </button>
      {popover}
    </>
  );
}

function DropdownContent({
  groups,
  currentId,
  onSelect,
  onEdit,
  onDelete,
  showAllOption,
}: {
  groups: GroupItem[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onEdit?: (group: GroupItem) => void;
  onDelete?: (group: GroupItem) => void;
  showAllOption?: boolean;
}) {
  const isAll = currentId === ALL_GROUPS_ID;
  return (
    <div className="max-h-60 overflow-y-auto">
      {showAllOption && (
        <button
          onClick={() => onSelect(ALL_GROUPS_ID)}
          className={`flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition hover:bg-zinc-50 ${
            isAll ? "bg-zinc-50 font-semibold text-zinc-900" : "text-zinc-600"
          }`}
        >
          <FolderOpen className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
          <span className="truncate">전체 시리즈</span>
          {isAll && <Check className="ml-auto h-3 w-3 shrink-0 text-zinc-400" />}
        </button>
      )}
      {groups.map((g) => (
        <div
          key={g.id}
          className={`group/item flex w-full flex-col gap-0.5 px-3 py-2 text-left text-xs transition hover:bg-zinc-50 ${
            g.id === currentId ? "bg-zinc-50 font-semibold text-zinc-900" : "text-zinc-600"
          }`}
        >
          <div className="flex items-center gap-2">
            <button
              onClick={() => onSelect(g.id)}
              className="flex min-w-0 flex-1 items-center gap-2 text-left"
            >
              <FolderOpen className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
              <span className="truncate">{g.name}</span>
              {g.id === currentId && <Check className="ml-auto h-3 w-3 shrink-0 text-zinc-400" />}
            </button>
            {onEdit && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(g);
                }}
                className="hidden h-5 w-5 shrink-0 items-center justify-center rounded text-zinc-400 group-hover/item:flex hover:bg-zinc-100 hover:text-zinc-700"
                title="시리즈 편집"
              >
                <Pencil className="h-3 w-3" />
              </button>
            )}
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(g);
                }}
                className="hidden h-5 w-5 shrink-0 items-center justify-center rounded text-zinc-400 group-hover/item:flex hover:bg-zinc-100 hover:text-red-500"
                title="시리즈 삭제"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )}
          </div>
          <ConfigBadges group={g} />
        </div>
      ))}
    </div>
  );
}

function ConfigBadges({ group }: { group: GroupItem }) {
  const badges: string[] = [];
  if (group.style_profile_name) badges.push(group.style_profile_name);
  if (group.voice_preset_name) badges.push(group.voice_preset_name);
  if (group.render_preset_name) badges.push(group.render_preset_name);
  if (badges.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 pl-5">
      {badges.map((label, i) => (
        <span key={`${i}-${label}`} className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] text-zinc-500">
          {label}
        </span>
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
        + 새 시리즈
      </button>
    </div>
  );
}
