"use client";

import { useState } from "react";
import { ChevronDown, X } from "lucide-react";
import type { SceneCharacterAction } from "../../types";

type SceneCharacterActionsProps = {
  characterActions: SceneCharacterAction[];
  characterAName?: string | null;
  characterBName?: string | null;
  characterAId?: number | null;
  characterBId?: number | null;
  onUpdate: (actions: SceneCharacterAction[]) => void;
};

type GroupedActions = {
  characterId: number;
  name: string;
  actions: SceneCharacterAction[];
};

function groupByCharacter(
  actions: SceneCharacterAction[],
  characterAId?: number | null,
  characterBId?: number | null,
  characterAName?: string | null,
  characterBName?: string | null
): GroupedActions[] {
  const map = new Map<number, SceneCharacterAction[]>();
  for (const action of actions) {
    const existing = map.get(action.character_id) || [];
    existing.push(action);
    map.set(action.character_id, existing);
  }

  const groups: GroupedActions[] = [];
  for (const [charId, charActions] of map.entries()) {
    let name = `Character #${charId}`;
    if (charId === characterAId) name = characterAName || "Character A";
    else if (charId === characterBId) name = characterBName || "Character B";
    groups.push({ characterId: charId, name, actions: charActions });
  }
  return groups;
}

function WeightDisplay({ weight }: { weight: number }) {
  if (weight === 1.0) return null;
  return <span className="ml-0.5 text-[9px] text-zinc-400">{weight.toFixed(1)}</span>;
}

function TagPill({ action, onRemove }: { action: SceneCharacterAction; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-0.5 rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-semibold text-zinc-600">
      {action.tag_name || `tag:${action.tag_id}`}
      <WeightDisplay weight={action.weight} />
      <button
        type="button"
        onClick={onRemove}
        className="ml-0.5 rounded-full p-0.5 text-zinc-400 transition hover:bg-zinc-200 hover:text-zinc-600"
      >
        <X className="h-2.5 w-2.5" />
      </button>
    </span>
  );
}

function AddTagInput({
  characterId,
  onAdd,
}: {
  characterId: number;
  onAdd: (action: SceneCharacterAction) => void;
}) {
  const [value, setValue] = useState("");

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && value.trim()) {
      e.preventDefault();
      onAdd({
        character_id: characterId,
        tag_id: 0, // Backend will resolve by tag_name
        tag_name: value.trim(),
        weight: 1.0,
      });
      setValue("");
    }
  };

  return (
    <input
      type="text"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onKeyDown={handleKeyDown}
      placeholder="Add tag..."
      className="w-24 rounded-full border border-dashed border-zinc-300 bg-white/80 px-2 py-0.5 text-[10px] outline-none placeholder:text-zinc-300 focus:border-zinc-400"
    />
  );
}

export default function SceneCharacterActions({
  characterActions,
  characterAName,
  characterBName,
  characterAId,
  characterBId,
  onUpdate,
}: SceneCharacterActionsProps) {
  const [expanded, setExpanded] = useState(false);

  const groups = groupByCharacter(
    characterActions,
    characterAId,
    characterBId,
    characterAName,
    characterBName
  );

  const handleRemove = (charId: number, tagIndex: number) => {
    const charActions = characterActions.filter((a) => a.character_id === charId);
    const otherActions = characterActions.filter((a) => a.character_id !== charId);
    charActions.splice(tagIndex, 1);
    onUpdate([...otherActions, ...charActions]);
  };

  const handleAdd = (action: SceneCharacterAction) => {
    onUpdate([...characterActions, action]);
  };

  const totalCount = characterActions.length;

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase transition hover:text-zinc-600"
      >
        <ChevronDown className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
        Character Actions
        {totalCount > 0 && (
          <span className="ml-1 rounded-full bg-zinc-100 px-1.5 text-[9px] font-medium text-zinc-500">
            {totalCount}
          </span>
        )}
      </button>

      {expanded && (
        <div className="mt-2 space-y-3">
          {groups.length === 0 && (
            <p className="text-[11px] text-zinc-400">No character actions defined.</p>
          )}
          {groups.map((group) => (
            <CharacterGroup
              key={group.characterId}
              group={group}
              onRemove={(tagIndex) => handleRemove(group.characterId, tagIndex)}
              onAdd={handleAdd}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CharacterGroup({
  group,
  onRemove,
  onAdd,
}: {
  group: GroupedActions;
  onRemove: (tagIndex: number) => void;
  onAdd: (action: SceneCharacterAction) => void;
}) {
  return (
    <div className="rounded-xl border border-zinc-100 bg-zinc-50/50 p-2.5">
      <div className="mb-1.5 text-[10px] font-semibold text-zinc-500">{group.name}</div>
      <div className="flex flex-wrap items-center gap-1">
        {group.actions.map((action, idx) => (
          <TagPill key={`${action.tag_id}-${idx}`} action={action} onRemove={() => onRemove(idx)} />
        ))}
        <AddTagInput characterId={group.characterId} onAdd={onAdd} />
      </div>
    </div>
  );
}
