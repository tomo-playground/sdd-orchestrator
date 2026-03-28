"use client";

import { useState, useMemo, type ReactNode } from "react";
import { Search, Plus, ArrowLeft } from "lucide-react";
import { cx, SEARCH_INPUT_CLASSES } from "../ui/variants";

// ── Types ────────────────────────────────────────────────────

export type MasterDetailItem = { id: number; name: string };

export type LibraryMasterDetailProps<T extends MasterDetailItem> = {
  /** Full list of items to display in the master panel. */
  items: T[];
  /** Currently selected item ID (null = nothing selected). */
  selectedId: number | null;
  /** Called when user selects an item (null = deselect, used by mobile back). */
  onSelect: (id: number | null) => void;
  /** Render the detail panel for the selected item. */
  renderDetail: (item: T) => ReactNode;
  /** Render each item row in the master list. Falls back to item.name. */
  renderItem?: (item: T, isSelected: boolean) => ReactNode;
  /** Called when the "+" button is clicked. Omit to hide the button. */
  onAdd?: () => void;
  /** Placeholder text for the search input. */
  searchPlaceholder?: string;
  /** Loading state — shows skeleton rows in master panel. */
  loading?: boolean;
  /** Empty state content when items is empty (after loading). */
  emptyState?: ReactNode;
  /** Optional header displayed above the master list. */
  header?: ReactNode;
  /** Content shown in detail panel when nothing is selected. */
  detailEmptyState?: ReactNode;
  /** Custom filter function. Overrides default name-only filter when provided. */
  filterFn?: (item: T, query: string) => boolean;
};

// ── Component ────────────────────────────────────────────────

export default function LibraryMasterDetail<T extends MasterDetailItem>({
  items,
  selectedId,
  onSelect,
  renderDetail,
  renderItem,
  onAdd,
  searchPlaceholder = "Search...",
  loading = false,
  emptyState,
  header,
  detailEmptyState,
  filterFn,
}: LibraryMasterDetailProps<T>) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return filterFn
      ? items.filter((item) => filterFn(item, q))
      : items.filter((item) => item.name.toLowerCase().includes(q));
  }, [items, search, filterFn]);

  const selectedItem = useMemo(
    () => (selectedId != null ? (items.find((i) => i.id === selectedId) ?? null) : null),
    [items, selectedId]
  );

  // Mobile: show detail fullscreen when item is selected
  const showMobileDetail = selectedItem != null;

  return (
    <div className="flex h-full min-h-0">
      {/* ── Master panel ──────────────────────────────────── */}
      <div
        className={cx(
          "flex w-full flex-col border-r border-zinc-200 md:w-80 md:shrink-0",
          showMobileDetail && "hidden md:flex"
        )}
      >
        {/* Header */}
        {header && <div className="px-4 pt-4">{header}</div>}

        {/* Search + Add */}
        <div className="flex items-center gap-2 px-4 py-3">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className={cx(SEARCH_INPUT_CLASSES, "pl-8")}
              aria-label="Search items"
            />
          </div>
          {onAdd && (
            <button
              onClick={onAdd}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-zinc-200 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-700"
              aria-label="Add item"
            >
              <Plus className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Item list */}
        <ul className="flex-1 overflow-y-auto" role="listbox" aria-label="Item list">
          {loading && <MasterSkeleton />}

          {!loading && filtered.length === 0 && (
            <li className="px-4 py-8 text-center text-xs text-zinc-400">
              {items.length === 0 ? (emptyState ?? "No items") : "No results"}
            </li>
          )}

          {!loading &&
            filtered.map((item) => {
              const selected = item.id === selectedId;
              return (
                <li
                  key={item.id}
                  role="option"
                  aria-selected={selected}
                  onClick={() => onSelect(item.id)}
                  className={cx(
                    "cursor-pointer border-b border-zinc-100 px-4 py-3 text-sm transition",
                    selected
                      ? "bg-zinc-100 font-medium text-zinc-900"
                      : "text-zinc-600 hover:bg-zinc-50"
                  )}
                >
                  {renderItem ? renderItem(item, selected) : item.name}
                </li>
              );
            })}
        </ul>
      </div>

      {/* ── Detail panel ──────────────────────────────────── */}
      <div className={cx("flex-1 overflow-y-auto", !showMobileDetail && "hidden md:block")}>
        {selectedItem ? (
          <div className="h-full">
            {/* Mobile back button */}
            <div className="sticky top-0 z-10 flex items-center border-b border-zinc-100 bg-white/90 px-4 py-2 backdrop-blur-sm md:hidden">
              <button
                onClick={() => onSelect(null)}
                className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-700"
                aria-label="Back to list"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back
              </button>
            </div>
            {renderDetail(selectedItem)}
          </div>
        ) : (
          <div className="hidden h-full items-center justify-center md:flex">
            {detailEmptyState ?? (
              <p className="text-sm text-zinc-400">Select an item to view details</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Skeleton ─────────────────────────────────────────────────

function MasterSkeleton() {
  return (
    <>
      {Array.from({ length: 6 }, (_, i) => (
        <li key={i} className="animate-pulse border-b border-zinc-100 px-4 py-3">
          <div className="h-4 w-3/4 rounded bg-zinc-200" />
          <div className="mt-1.5 h-3 w-1/2 rounded bg-zinc-100" />
        </li>
      ))}
    </>
  );
}
