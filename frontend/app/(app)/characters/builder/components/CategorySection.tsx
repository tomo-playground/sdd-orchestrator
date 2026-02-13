"use client";

import { useState, useMemo, useCallback } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { Tag } from "../../../../types";
import Badge from "../../../../components/ui/Badge";
import { cx } from "../../../../components/ui/variants";
import { TAG_COLOR_DOTS, type WizardCategory } from "../wizardTemplates";
import type { WizardTag } from "../steps/AppearanceStep";

// ── Helpers ──────────────────────────────────────────────────

function sortByPopularity(tags: Tag[]): { popular: Tag[]; rest: Tag[] } {
  const withCount = tags.filter((t) => (t.wd14_count ?? 0) > 0);
  const sorted = [...withCount].sort((a, b) => (b.wd14_count ?? 0) - (a.wd14_count ?? 0));
  const popular = sorted.slice(0, 5);
  const popularIds = new Set(popular.map((t) => t.id));
  const rest = tags
    .filter((t) => !popularIds.has(t.id))
    .sort((a, b) => a.name.localeCompare(b.name));
  return { popular, rest };
}

// ── Component ────────────────────────────────────────────────

type CategorySectionProps = {
  category: WizardCategory;
  tags: Tag[];
  selectedTags: WizardTag[];
  onToggleTag: (tag: Tag, category: WizardCategory) => void;
};

export default function CategorySection({
  category,
  tags,
  selectedTags,
  onToggleTag,
}: CategorySectionProps) {
  const selectedInGroup = selectedTags.filter((t) => t.groupName === category.groupName);
  const hasSelection = selectedInGroup.length > 0;
  const [open, setOpen] = useState(category.defaultOpen || hasSelection);

  const { popular, rest } = useMemo(() => sortByPopularity(tags), [tags]);
  const selectedIds = useMemo(() => new Set(selectedTags.map((t) => t.tagId)), [selectedTags]);

  const renderChip = useCallback(
    (tag: Tag) => {
      const isSelected = selectedIds.has(tag.id);
      const colorDot = category.hasColorDot ? TAG_COLOR_DOTS[tag.name] : null;

      return (
        <button
          key={tag.id}
          onClick={() => onToggleTag(tag, category)}
          className={cx(
            "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition",
            isSelected ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
          )}
        >
          {colorDot && (
            <span className={cx("inline-block h-2.5 w-2.5 shrink-0 rounded-full", colorDot)} />
          )}
          {tag.name.replace(/_/g, " ")}
        </button>
      );
    },
    [selectedIds, category, onToggleTag]
  );

  return (
    <div className="rounded-xl border border-zinc-100 bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-2.5"
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-zinc-400" />
          )}
          <span className="text-sm font-semibold text-zinc-700">{category.label}</span>
        </div>
        {selectedInGroup.length > 0 && (
          <Badge variant="default" size="sm">
            {selectedInGroup.length}/{tags.length}
          </Badge>
        )}
      </button>

      {open && (
        <div className="border-t border-zinc-100 px-4 py-3">
          {/* Popular row */}
          {popular.length > 0 && (
            <>
              <div className="mb-1.5 text-[11px] font-medium tracking-wider text-zinc-400 uppercase">
                Popular
              </div>
              <div className="mb-2 flex flex-wrap gap-1.5">{popular.map(renderChip)}</div>
              {rest.length > 0 && <hr className="mb-2 border-zinc-100" />}
            </>
          )}
          {/* All tags */}
          <div className="flex flex-wrap gap-1.5">
            {(popular.length > 0
              ? rest
              : [...tags].sort((a, b) => a.name.localeCompare(b.name))
            ).map(renderChip)}
          </div>
          {category.maxSelect && (
            <p className="mt-2 text-[11px] text-zinc-400">Max {category.maxSelect} selections</p>
          )}
        </div>
      )}
    </div>
  );
}
