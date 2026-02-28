"use client";

import { Search } from "lucide-react";
import { useTagBrowser } from "../../../hooks/useTagBrowser";
import TagCard from "../../../components/ui/TagCard";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";

const GROUP_LABELS: Record<string, string> = {
  expression: "Expression",
  pose: "Pose",
  camera: "Camera",
  clothing_top: "Clothing Top",
  clothing_outfit: "Clothing Outfit",
  hair_color: "Hair Color",
  hair_style: "Hair Style",
};

export default function TagBrowserTab() {
  const {
    groups,
    activeGroup,
    setActiveGroup,
    tags,
    loading,
    search,
    setSearch,
  } = useTagBrowser();

  return (
    <div className="flex gap-6">
      {/* Left: Group sidebar */}
      <div className="w-40 shrink-0">
        <h3 className="mb-3 text-sm font-semibold text-zinc-700">Groups</h3>
        <ul className="space-y-0.5">
          {groups.map((g) => (
            <li key={g}>
              <button
                onClick={() => setActiveGroup(g)}
                className={`w-full rounded-lg px-3 py-2 text-left text-xs transition ${
                  activeGroup === g
                    ? "bg-zinc-900 font-medium text-white"
                    : "text-zinc-600 hover:bg-zinc-100"
                }`}
              >
                {GROUP_LABELS[g] ?? g}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Right: Tag grid */}
      <div className="flex-1">
        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder="Search tags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-zinc-200 bg-white py-2 pl-9 pr-3 text-sm text-zinc-700 outline-none transition focus:border-zinc-400"
          />
        </div>

        {/* Grid */}
        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <LoadingSpinner size="md" />
          </div>
        ) : tags.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-zinc-400">
            No tags found
          </div>
        ) : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-3">
            {tags.map((tag) => (
              <TagCard key={tag.id} tag={tag} />
            ))}
          </div>
        )}

        {/* Count */}
        <div className="mt-4 text-[12px] text-zinc-400">
          {tags.length} tags in {GROUP_LABELS[activeGroup] ?? activeGroup}
        </div>
      </div>
    </div>
  );
}
