"use client";

import { useMemo } from "react";
import { useTags } from "../../../hooks";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import Button from "../../../components/ui/Button";
import DeprecatedTagsPanel from "../DeprecatedTagsPanel";
import { useTagManagement } from "../hooks/useTagManagement";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import { useUIStore } from "../../../store/useUIStore";
import type { Tag } from "../../../types";

export default function TagsTab() {
  const { tags: allTags, reload: fetchTagsData } = useTags(null);
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();

  const {
    isTagsLoading,
    tagGroupFilter,
    setTagGroupFilter,
    tagCategoryFilter,
    setTagCategoryFilter,
    pendingTags,
    isPendingLoading,
    pendingGroupSelection,
    setPendingGroupSelection,
    pendingApproving,
    showPendingSection,
    setShowPendingSection,
    handleRefresh,
    fetchPendingTags,
    handleApprovePendingTag,
  } = useTagManagement(fetchTagsData, { showToast, confirmDialog: confirm });

  const SCENE_TAG_GROUPS = [
    "expression",
    "gaze",
    "pose",
    "action_body",
    "action_hand",
    "action_daily",
    "camera",
    "environment",
    "mood",
    "time_of_day",
    "weather",
    "particle",
  ];

  const availableGroups = useMemo(() => {
    const groups = new Set<string>();
    allTags.forEach((tag: Tag) => {
      if (tag.group_name) groups.add(tag.group_name);
    });
    return Array.from(groups).sort();
  }, [allTags]);

  const filteredTags = useMemo(() => {
    return allTags.filter((tag: Tag) => {
      if (tagCategoryFilter && tag.category !== tagCategoryFilter) return false;
      if (tagGroupFilter && tag.group_name !== tagGroupFilter) return false;
      return true;
    });
  }, [allTags, tagCategoryFilter, tagGroupFilter]);

  const tagCategories = useMemo(() => {
    return [...new Set(allTags.map((t: Tag) => t.category))].sort();
  }, [allTags]);

  return (
    <section className="grid gap-6 rounded-2xl border border-zinc-200/60 bg-white p-6 text-xs text-zinc-600 shadow-sm">
      {/* Deprecated Tags */}
      <DeprecatedTagsPanel />

      <div className="flex items-center justify-between">
        <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Tag Analysis
        </span>
        <Button
          onClick={handleRefresh}
          disabled={isTagsLoading}
          loading={isTagsLoading}
          variant="outline"
          size="sm"
          className="rounded-full tracking-[0.2em] uppercase"
        >
          Refresh
        </Button>
      </div>

      {/* Group Statistics Overview */}
      <div className="grid gap-4">
        <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
          Scene Tag Groups ({SCENE_TAG_GROUPS.length} Groups)
        </span>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {SCENE_TAG_GROUPS.map((group: string) => {
            const count = allTags.filter(
              (t: Tag) => t.category === "scene" && t.group_name === group
            ).length;
            const isActive = tagGroupFilter === group && tagCategoryFilter === "scene";
            return (
              <button
                key={group}
                type="button"
                onClick={() => {
                  if (isActive) {
                    setTagGroupFilter("");
                    setTagCategoryFilter("");
                  } else {
                    setTagGroupFilter(group);
                    setTagCategoryFilter("scene");
                  }
                }}
                className={`rounded-xl border p-3 text-center transition ${isActive
                  ? "border-indigo-300 bg-indigo-50"
                  : "border-zinc-200 bg-white hover:border-zinc-300"
                  }`}
              >
                <div
                  className={`text-lg font-bold ${isActive ? "text-indigo-600" : "text-zinc-700"}`}
                >
                  {count}
                </div>
                <div
                  className={`text-[11px] font-medium tracking-wider uppercase ${isActive ? "text-indigo-500" : "text-zinc-400"}`}
                >
                  {group}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Character Tag Groups */}
      <div className="grid gap-4">
        <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
          Character Tag Groups
        </span>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
          {[
            ...new Set(
              allTags.filter((t) => t.category === "character").map((t) => t.group_name || "other")
            ),
          ].map((group: string) => {
            const count = allTags.filter(
              (t: Tag) =>
                t.category === "character" &&
                (group === "other" ? !t.group_name : t.group_name === group)
            ).length;
            if (count === 0) return null;
            const isActive = tagGroupFilter === group && tagCategoryFilter === "character";
            return (
              <button
                key={group}
                type="button"
                onClick={() => {
                  if (isActive) {
                    setTagGroupFilter("");
                    setTagCategoryFilter("");
                  } else {
                    setTagGroupFilter(group);
                    setTagCategoryFilter("character");
                  }
                }}
                className={`rounded-xl border p-3 text-center transition ${isActive
                  ? "border-violet-300 bg-violet-50"
                  : "border-zinc-200 bg-white hover:border-zinc-300"
                  }`}
              >
                <div
                  className={`text-lg font-bold ${isActive ? "text-violet-600" : "text-zinc-700"}`}
                >
                  {count}
                </div>
                <div
                  className={`text-[11px] font-medium tracking-wider uppercase ${isActive ? "text-violet-500" : "text-zinc-400"}`}
                >
                  {group}
                </div>
              </button>
            );
          })}
        </div>

        {/* Meta Tag Groups (Quality, Style) */}
        <div className="grid gap-4">
          <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
            Meta Tag Groups (Quality & Style)
          </span>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
            {[
              ...new Set(
                allTags.filter((t) => t.category === "meta").map((t) => t.group_name || "other")
              ),
            ].map((group: string) => {
              const count = allTags.filter(
                (t: Tag) =>
                  t.category === "meta" &&
                  (group === "other" ? !t.group_name : t.group_name === group)
              ).length;
              if (count === 0) return null;
              const isActive = tagGroupFilter === group && tagCategoryFilter === "meta";
              return (
                <button
                  key={group}
                  type="button"
                  onClick={() => {
                    if (isActive) {
                      setTagGroupFilter("");
                      setTagCategoryFilter("");
                    } else {
                      setTagGroupFilter(group);
                      setTagCategoryFilter("meta");
                    }
                  }}
                  className={`rounded-xl border p-3 text-center transition ${isActive
                    ? "border-emerald-300 bg-emerald-50"
                    : "border-zinc-200 bg-white hover:border-zinc-300"
                    }`}
                >
                  <div
                    className={`text-lg font-bold ${isActive ? "text-emerald-600" : "text-zinc-700"}`}
                  >
                    {count}
                  </div>
                  <div
                    className={`text-[11px] font-medium tracking-wider uppercase ${isActive ? "text-emerald-500" : "text-zinc-400"}`}
                  >
                    {group}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Pending Classifications */}
      <div className="grid gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-semibold tracking-[0.2em] text-amber-600 uppercase">
              Pending Classifications
            </span>
            {pendingTags.length > 0 && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                {pendingTags.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowPendingSection(!showPendingSection)}
              className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[11px] font-semibold text-zinc-500"
            >
              {showPendingSection ? "Hide" : "Show"}
            </button>
            <button
              type="button"
              onClick={fetchPendingTags}
              disabled={isPendingLoading}
              className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[11px] font-semibold text-zinc-500 disabled:opacity-50"
            >
              {isPendingLoading ? "..." : "Refresh"}
            </button>
          </div>
        </div>

        {showPendingSection && (
          <>
            {isPendingLoading ? (
              <div className="flex items-center justify-center py-4">
                <LoadingSpinner size="sm" color="text-zinc-400" />
              </div>
            ) : pendingTags.length === 0 ? (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
                <span className="text-xs text-emerald-600">All tags are classified!</span>
              </div>
            ) : (
              <div className="grid max-h-[400px] gap-2 overflow-y-auto">
                {pendingTags.map((tag) => (
                  <div
                    key={tag.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50/50 p-3"
                  >
                    <div className="flex items-center gap-3">
                      <div>
                        <span className="text-xs font-semibold text-zinc-700">{tag.name}</span>
                        <div className="mt-0.5 flex items-center gap-2">
                          <span className="text-[11px] text-zinc-400">
                            {tag.classification_source || "unknown"}
                          </span>
                          {tag.classification_confidence !== null && (
                            <span className="text-[11px] text-zinc-400">
                              ({Math.round(tag.classification_confidence * 100)}%)
                            </span>
                          )}
                          {tag.group_name && (
                            <span className="rounded-full bg-zinc-100 px-1.5 py-0.5 text-[11px] text-zinc-500">
                              {tag.group_name}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={pendingGroupSelection[tag.id] || ""}
                        onChange={(e) =>
                          setPendingGroupSelection((prev) => ({
                            ...prev,
                            [tag.id]: e.target.value,
                          }))
                        }
                        className="rounded-lg border border-zinc-200 bg-white px-2 py-1 text-[12px] outline-none focus:border-zinc-400"
                      >
                        <option value="">Select group</option>
                        {availableGroups.map((group) => (
                          <option key={group} value={group}>
                            {group}
                          </option>
                        ))}
                      </select>
                      <Button
                        onClick={() => handleApprovePendingTag(tag.id)}
                        disabled={!pendingGroupSelection[tag.id] || pendingApproving[tag.id]}
                        loading={pendingApproving[tag.id]}
                        variant="warning"
                        size="sm"
                        className="rounded-full px-3 py-1 text-[11px]"
                      >
                        Approve
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Total Stats */}
      <div className="flex flex-wrap gap-4 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-zinc-700">{allTags.length}</div>
          <div className="text-[11px] font-medium tracking-wider text-zinc-400 uppercase">
            Total Tags
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-indigo-600">
            {allTags.filter((t: Tag) => t.category === "scene").length}
          </div>
          <div className="text-[11px] font-medium tracking-wider text-zinc-400 uppercase">
            Scene Tags
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-violet-600">
            {allTags.filter((t: Tag) => t.category === "character").length}
          </div>
          <div className="text-[11px] font-medium tracking-wider text-zinc-400 uppercase">
            Character Tags
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-teal-600">
            {allTags.filter((t: Tag) => t.category === "meta" && t.group_name === "quality").length}
          </div>
          <div className="text-[11px] font-medium tracking-wider text-zinc-400 uppercase">
            Quality Tags
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-emerald-600">
            {allTags.filter((t: Tag) => t.category === "meta" && t.group_name === "style").length}
          </div>
          <div className="text-[11px] font-medium tracking-wider text-zinc-400 uppercase">
            Style Tags
          </div>
        </div>
      </div>

      {/* Filtered Tags List */}
      {(tagGroupFilter || tagCategoryFilter) && (
        <div className="grid gap-3">
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
              {tagCategoryFilter} / {tagGroupFilter} ({filteredTags.length} tags)
            </span>
            <button
              type="button"
              onClick={() => {
                setTagGroupFilter("");
                setTagCategoryFilter("");
              }}
              className="text-[12px] text-zinc-400 hover:text-zinc-600"
            >
              Clear Filter
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {filteredTags.map((tag: Tag) => (
              <span
                key={tag.id}
                className="flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-3 py-1 text-[12px] text-zinc-600"
                title={`Priority: ${tag.priority}`}
              >
                <span className="font-medium">{tag.name}</span>
                {tag.group_name && (
                  <span className="border-l border-zinc-100 pl-1.5 text-[11px] font-normal text-zinc-300 uppercase">
                    {tag.group_name}
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* All Tags by Group (collapsed by default) */}
      {!tagGroupFilter && !tagCategoryFilter && (
        <div className="grid gap-4">
          <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
            All Tags by Category
          </span>
          {tagCategories.map((category: string) => (
            <details key={category} className="rounded-xl border border-zinc-200 bg-white">
              <summary className="cursor-pointer px-4 py-3 text-[12px] font-semibold tracking-wider text-zinc-500 uppercase hover:bg-zinc-50">
                {category || "UNCATEGORIZED"} (
                {allTags.filter((t: Tag) => t.category === category).length} tags)
              </summary>
              <div className="border-t border-zinc-100 p-4">
                <div className="mt-2 flex flex-wrap gap-2">
                  {allTags
                    .filter((t: Tag) => t.category === category)
                    .slice(0, 500)
                    .map((tag: Tag) => (
                      <span
                        key={tag.id}
                        className="inline-flex items-center gap-1 rounded-full border border-zinc-100 bg-zinc-50 px-2 py-0.5 text-[11px] text-zinc-500"
                      >
                        <span>{tag.name}</span>
                        {tag.group_name && (
                          <span className="border-l border-zinc-200 pl-1 text-[7px] font-normal text-zinc-300 uppercase">
                            {tag.group_name}
                          </span>
                        )}
                      </span>
                    ))}
                </div>
              </div>
            </details>
          ))}
        </div>
      )}
      <ConfirmDialog {...dialogProps} />
    </section>
  );
}
