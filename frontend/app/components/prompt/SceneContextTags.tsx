"use client";

import { useState } from "react";
import type { Tag, SceneContextTags as SceneContextTagsType } from "../../types";

type Props = {
  contextTags: SceneContextTagsType | undefined;
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isExclusiveGroup: (groupName: string) => boolean;
  onUpdate: (tags: SceneContextTagsType) => void;
};

const GROUP_LABELS: Record<string, string> = {
  expression: "Expression",
  gaze: "Gaze",
  pose: "Pose",
  action: "Action",
};

const GROUP_ICONS: Record<string, string> = {
  expression: "😊",
  gaze: "👁️",
  pose: "🧍",
  action: "🏃",
};

export default function SceneContextTags({
  contextTags,
  tagsByGroup,
  sceneTagGroups,
  isExclusiveGroup,
  onUpdate,
}: Props) {
  const [expanded, setExpanded] = useState(false);

  const getSelectedTags = (group: string): string[] => {
    if (!contextTags) return [];
    if (group === "gaze") {
      return contextTags.gaze ? [contextTags.gaze] : [];
    }
    return (contextTags[group as keyof Omit<SceneContextTagsType, "gaze">] as string[] | undefined) || [];
  };

  const handleTagToggle = (group: string, tagName: string) => {
    const current = { ...contextTags };
    const isExclusive = isExclusiveGroup(group);

    if (isExclusive) {
      // Single select: toggle on/off
      if (current.gaze === tagName) {
        current.gaze = undefined;
      } else {
        current.gaze = tagName;
      }
    } else {
      // Multi select
      const key = group as keyof Omit<SceneContextTagsType, "gaze">;
      const existing = (current[key] as string[] | undefined) || [];
      if (existing.includes(tagName)) {
        (current[key] as string[]) = existing.filter((t) => t !== tagName);
      } else {
        (current[key] as string[]) = [...existing, tagName];
      }
    }

    onUpdate(current);
  };

  const totalSelected = sceneTagGroups.reduce((acc, group) => acc + getSelectedTags(group).length, 0);

  if (sceneTagGroups.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-2">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase"
      >
        <span className="flex items-center gap-1.5">
          Scene Tags
          {totalSelected > 0 && (
            <span className="rounded-full bg-zinc-200 px-1.5 py-0.5 text-[11px] font-bold text-zinc-600">
              {totalSelected}
            </span>
          )}
        </span>
        <svg
          className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="rounded-2xl border border-zinc-200 bg-white/80 p-3 grid gap-3">
          {sceneTagGroups.map((group) => {
            const tags = tagsByGroup[group] || [];
            const selected = getSelectedTags(group);
            const isExclusive = isExclusiveGroup(group);

            return (
              <div key={group} className="grid gap-1.5">
                <div className="flex items-center gap-1 text-[11px] font-semibold tracking-[0.15em] text-zinc-400 uppercase">
                  <span>{GROUP_ICONS[group]}</span>
                  <span>{GROUP_LABELS[group] || group}</span>
                  {isExclusive && (
                    <span className="text-[8px] text-zinc-300">(single)</span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1">
                  {tags.map((tag) => {
                    const isSelected = selected.includes(tag.name);
                    return (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => handleTagToggle(group, tag.name)}
                        className={`rounded-full px-2 py-0.5 text-[12px] transition-all ${
                          isSelected
                            ? "bg-zinc-800 text-white font-medium"
                            : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                        }`}
                      >
                        {tag.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
