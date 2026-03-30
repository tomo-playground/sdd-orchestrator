"use client";

import Modal from "../ui/Modal";
import type { GroupItem } from "../../types";

interface Props {
  groups: GroupItem[];
  onSelect: (groupId: number) => void;
  onClose: () => void;
}

export default function GroupSelectModal({ groups, onSelect, onClose }: Props) {
  return (
    <Modal open size="md" onClose={onClose} ariaLabelledBy="group-select-title">
      <Modal.Header>
        <h2 id="group-select-title" className="text-sm font-semibold text-zinc-900">
          어떤 시리즈에 만들까요?
        </h2>
      </Modal.Header>

      <div className="flex max-h-80 flex-col gap-2 overflow-y-auto px-5 py-4">
        {groups.map((g) => (
          <button
            key={g.id}
            onClick={() => onSelect(g.id)}
            className="flex flex-col gap-1.5 rounded-xl border border-zinc-200 px-4 py-3 text-left transition hover:border-zinc-400 hover:bg-zinc-50"
          >
            <span className="text-sm font-semibold text-zinc-900">{g.name}</span>
            <ConfigBadges group={g} />
          </button>
        ))}
      </div>
    </Modal>
  );
}

function ConfigBadges({ group }: { group: GroupItem }) {
  const badges: string[] = [];
  if (group.style_profile_name) badges.push(group.style_profile_name);
  if (group.voice_preset_name) badges.push(group.voice_preset_name);
  if (group.render_preset_name) badges.push(group.render_preset_name);
  if (badges.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {badges.map((label, i) => (
        <span
          key={`${i}-${label}`}
          className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] text-zinc-500"
        >
          {label}
        </span>
      ))}
    </div>
  );
}
