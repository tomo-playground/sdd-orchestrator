"use client";

import { useRef, useState } from "react";
import type { SceneContextTags } from "../../types";
import Popover from "../ui/Popover";
import TagSuggestInput from "../ui/TagSuggestInput";
import { useSceneContext } from "./SceneContext";

export const ENV_GROUPS = ["environment", "time_of_day", "weather", "particle"] as const;
type EnvGroup = (typeof ENV_GROUPS)[number];

const GROUP_META: Record<EnvGroup, { icon: string; label: string }> = {
  environment: { icon: "🏠", label: "Environment" },
  time_of_day: { icon: "🕐", label: "Time" },
  weather: { icon: "🌤️", label: "Weather" },
  particle: { icon: "✨", label: "Particle" },
};

const LARGE_GROUP_THRESHOLD = 10;

type Props = {
  contextTags: SceneContextTags | undefined;
  onUpdate: (tags: SceneContextTags) => void;
};

export default function SceneEnvironmentPicker({ contextTags, onUpdate }: Props) {
  const { data } = useSceneContext();
  const { tagsByGroup } = data;

  const [openGroup, setOpenGroup] = useState<EnvGroup | null>(null);
  const anchorRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const getSelected = (group: EnvGroup): string[] => {
    if (!contextTags) return [];
    return (contextTags[group] as string[] | undefined) || [];
  };

  const toggleTag = (group: EnvGroup, tagName: string) => {
    const current = { ...contextTags };
    const existing = (current[group] as string[] | undefined) || [];
    if (existing.includes(tagName)) {
      (current[group] as string[]) = existing.filter((t) => t !== tagName);
    } else {
      (current[group] as string[]) = [...existing, tagName];
    }
    onUpdate(current);
  };

  const removeTag = (group: EnvGroup, tagName: string) => {
    const current = { ...contextTags };
    const existing = (current[group] as string[] | undefined) || [];
    (current[group] as string[]) = existing.filter((t) => t !== tagName);
    onUpdate(current);
  };

  const totalSelected = ENV_GROUPS.reduce((acc, g) => acc + getSelected(g).length, 0);

  return (
    <div className="grid gap-2">
      <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
        Environment
        {totalSelected > 0 && (
          <span className="ml-1.5 inline-flex rounded-full bg-sky-100 px-1.5 py-0.5 text-[11px] font-bold text-sky-700">
            {totalSelected}
          </span>
        )}
      </span>

      <div className="flex flex-wrap gap-x-5 gap-y-2">
        {ENV_GROUPS.map((group) => {
          const meta = GROUP_META[group];
          const selected = getSelected(group);
          const tags = tagsByGroup[group] || [];

          if (tags.length === 0) return null;

          return (
            <div key={group} className="flex items-center gap-1 text-xs">
              <span className="mr-0.5 text-[11px] text-zinc-400">
                {meta.icon} {meta.label}
              </span>

              {/* Selected chips */}
              {selected.map((name) => (
                <span
                  key={name}
                  className="inline-flex items-center gap-0.5 rounded-full bg-sky-100 px-2 py-0.5 text-[12px] font-medium text-sky-800"
                >
                  {name}
                  <button
                    type="button"
                    onClick={() => removeTag(group, name)}
                    className="ml-0.5 text-sky-400 hover:text-sky-700"
                    aria-label={`Remove ${name}`}
                  >
                    x
                  </button>
                </span>
              ))}

              {/* Add button */}
              <button
                ref={(el) => {
                  anchorRefs.current[group] = el;
                }}
                type="button"
                onClick={() => setOpenGroup(openGroup === group ? null : group)}
                className="rounded-full border border-dashed border-zinc-300 px-2 py-0.5 text-[12px] text-zinc-400 transition hover:border-zinc-400 hover:text-zinc-600"
              >
                + Add
              </button>

              {/* Popover for tag selection */}
              <Popover
                anchorRef={{ current: anchorRefs.current[group] ?? null }}
                open={openGroup === group}
                onClose={() => setOpenGroup(null)}
                className="max-h-[260px] overflow-y-auto p-2"
                aria-label={`${meta.label} tags`}
              >
                {tags.length > LARGE_GROUP_THRESHOLD && (
                  <div className="mb-2">
                    <TagSuggestInput
                      onTagSelect={(tagName) => {
                        if (!selected.includes(tagName)) toggleTag(group, tagName);
                      }}
                      placeholder="Search tags..."
                      className="w-full rounded-lg border border-zinc-200 px-2 py-1 text-xs outline-none focus:border-sky-300"
                    />
                  </div>
                )}
                <div className="flex flex-wrap gap-1">
                  {tags.map((tag) => {
                    const isSelected = selected.includes(tag.name);
                    return (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => toggleTag(group, tag.name)}
                        className={`rounded-full px-2 py-0.5 text-[12px] transition-all ${
                          isSelected
                            ? "bg-sky-600 font-medium text-white"
                            : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                        }`}
                      >
                        {tag.name}
                      </button>
                    );
                  })}
                </div>
              </Popover>
            </div>
          );
        })}
      </div>
    </div>
  );
}
