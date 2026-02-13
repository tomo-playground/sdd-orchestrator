"use client";

import { Search } from "lucide-react";
import type { Tag } from "../../../../types";
import { cx } from "../../../../components/ui/variants";
import { WIZARD_CATEGORIES, type WizardCategory } from "../wizardTemplates";
import CategorySection from "../components/CategorySection";

// ── Types ────────────────────────────────────────────────────

export type WizardTag = {
  tagId: number;
  name: string;
  groupName: string;
  isPermanent: boolean;
};

type AppearanceStepProps = {
  tagsByGroup: Record<string, Tag[]>;
  selectedTags: WizardTag[];
  onToggleTag: (tag: Tag, category: WizardCategory) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  searchResults: Tag[];
  onSearchTagSelect: (tag: Tag) => void;
};

// ── Main Component ───────────────────────────────────────────

export default function AppearanceStep({
  tagsByGroup,
  selectedTags,
  onToggleTag,
  searchQuery,
  onSearchChange,
  searchResults,
  onSearchTagSelect,
}: AppearanceStepProps) {
  return (
    <div className="space-y-3">
      {/* Category sections */}
      {WIZARD_CATEGORIES.map((cat) => {
        const tags = tagsByGroup[cat.groupName] ?? [];
        if (tags.length === 0) return null;
        return (
          <CategorySection
            key={cat.groupName}
            category={cat}
            tags={tags}
            selectedTags={selectedTags}
            onToggleTag={onToggleTag}
          />
        );
      })}

      {/* Search bar */}
      <div className="mt-4 rounded-xl border border-zinc-200 bg-white p-3">
        <div className="relative">
          <Search className="absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search more tags..."
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 py-2 pr-3 pl-9 text-sm outline-none focus:border-zinc-400"
          />
        </div>
        {searchResults.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {searchResults.map((tag) => {
              const isSelected = selectedTags.some((t) => t.tagId === tag.id);
              return (
                <button
                  key={tag.id}
                  onClick={() => onSearchTagSelect(tag)}
                  className={cx(
                    "rounded-full px-3 py-1 text-xs font-medium transition",
                    isSelected
                      ? "bg-zinc-900 text-white"
                      : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
                  )}
                >
                  {tag.name.replace(/_/g, " ")}
                  {tag.group_name && (
                    <span className="ml-1 text-zinc-400">
                      ({tag.group_name.replace(/_/g, " ")})
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
