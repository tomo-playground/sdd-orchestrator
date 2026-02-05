"use client";

import { Tag } from "../../types";

type Props = {
  identityTags: Tag[];
  clothingTags: Tag[];
  filteredTags: Tag[];
  tagSearch: string;
  setTagSearch: (v: string) => void;
  activeTagInput: "identity" | "clothing" | null;
  setActiveTagInput: (v: "identity" | "clothing" | null) => void;
  rawEditMode: "identity" | "clothing" | null;
  rawEditText: string;
  setRawEditText: (v: string) => void;
  onAddTag: (tag: Tag) => void;
  onRemoveTag: (id: number, type: "identity" | "clothing") => void;
  onToggleRawEdit: (type: "identity" | "clothing") => void;
};

export default function CharacterTagsEditor({
  identityTags,
  clothingTags,
  filteredTags,
  tagSearch,
  setTagSearch,
  activeTagInput,
  setActiveTagInput,
  rawEditMode,
  rawEditText,
  setRawEditText,
  onAddTag,
  onRemoveTag,
  onToggleRawEdit,
}: Props) {
  return (
    <>
      {/* Identity Tags */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Identity Tags
          </label>
          <button
            onClick={() => onToggleRawEdit("identity")}
            className="text-[10px] font-semibold text-zinc-500 underline hover:text-zinc-800"
          >
            {rawEditMode === "identity" ? "Done" : "Edit as Text"}
          </button>
        </div>
        {rawEditMode === "identity" ? (
          <textarea
            value={rawEditText}
            onChange={(e) => setRawEditText(e.target.value)}
            rows={3}
            className="w-full rounded-xl border border-zinc-200 px-3 py-2 font-mono text-sm outline-none focus:border-zinc-400"
            placeholder="tag1, tag2, tag3..."
          />
        ) : (
          <TagChipList
            tags={identityTags}
            type="identity"
            chipColor="bg-purple-100 text-purple-700"
            hoverColor="hover:text-purple-900"
            tagSearch={activeTagInput === "identity" ? tagSearch : ""}
            filteredTags={activeTagInput === "identity" && tagSearch ? filteredTags : []}
            onSearchChange={(v) => {
              setActiveTagInput("identity");
              setTagSearch(v);
            }}
            onFocus={() => setActiveTagInput("identity")}
            onAddTag={onAddTag}
            onRemoveTag={(id) => onRemoveTag(id, "identity")}
          />
        )}
      </div>

      {/* Clothing Tags */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="block text-xs font-semibold tracking-wider text-zinc-500 uppercase">
            Clothing Tags
          </label>
          <button
            onClick={() => onToggleRawEdit("clothing")}
            className="text-[10px] font-semibold text-zinc-500 underline hover:text-zinc-800"
          >
            {rawEditMode === "clothing" ? "Done" : "Edit as Text"}
          </button>
        </div>
        {rawEditMode === "clothing" ? (
          <textarea
            value={rawEditText}
            onChange={(e) => setRawEditText(e.target.value)}
            rows={3}
            className="w-full rounded-xl border border-zinc-200 px-3 py-2 font-mono text-sm outline-none focus:border-zinc-400"
            placeholder="tag1, tag2, tag3..."
          />
        ) : (
          <TagChipList
            tags={clothingTags}
            type="clothing"
            chipColor="bg-amber-100 text-amber-700"
            hoverColor="hover:text-amber-900"
            tagSearch={activeTagInput === "clothing" ? tagSearch : ""}
            filteredTags={activeTagInput === "clothing" && tagSearch ? filteredTags : []}
            onSearchChange={(v) => {
              setActiveTagInput("clothing");
              setTagSearch(v);
            }}
            onFocus={() => setActiveTagInput("clothing")}
            onAddTag={onAddTag}
            onRemoveTag={(id) => onRemoveTag(id, "clothing")}
          />
        )}
      </div>
    </>
  );
}

// --- Internal sub-component for tag chips + search input ---

type TagChipListProps = {
  tags: Tag[];
  type: "identity" | "clothing";
  chipColor: string;
  hoverColor: string;
  tagSearch: string;
  filteredTags: Tag[];
  onSearchChange: (v: string) => void;
  onFocus: () => void;
  onAddTag: (tag: Tag) => void;
  onRemoveTag: (id: number) => void;
};

function TagChipList({
  tags,
  chipColor,
  hoverColor,
  tagSearch,
  filteredTags,
  onSearchChange,
  onFocus,
  onAddTag,
  onRemoveTag,
}: TagChipListProps) {
  return (
    <div className="mb-2 flex flex-wrap gap-2">
      {tags.map((tag) => (
        <span
          key={tag.id}
          className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs ${chipColor}`}
        >
          {tag.name}
          <button onClick={() => onRemoveTag(tag.id)} className={hoverColor}>
            x
          </button>
        </span>
      ))}
      <div className="relative">
        <input
          value={tagSearch}
          onChange={(e) => onSearchChange(e.target.value)}
          onFocus={onFocus}
          placeholder="+ Add tag"
          className="w-24 rounded-full border border-dashed border-zinc-300 px-3 py-1 text-xs transition-all outline-none focus:w-48 focus:border-zinc-400"
        />
        {tagSearch && filteredTags.length > 0 && (
          <div className="absolute top-full left-0 z-[var(--z-dropdown)] mt-1 max-h-40 w-48 overflow-y-auto rounded-xl border border-zinc-200 bg-white shadow-lg">
            {filteredTags.map((tag) => (
              <button
                key={tag.id}
                onClick={() => onAddTag(tag)}
                className="w-full px-3 py-2 text-left text-xs hover:bg-zinc-50"
              >
                {tag.name} <span className="text-[10px] text-zinc-400">({tag.category})</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
