"use client";

import { useEffect, useCallback } from "react";
import { Copy, Trash2 } from "lucide-react";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import { useUIStore } from "../../../store/useUIStore";
import LibraryMasterDetail from "../../../components/layout/LibraryMasterDetail";
import StyleProfileEditor from "./StyleProfileEditor";
import { useStyleTab } from "../../../hooks/styles/useStyleTab";
import type { StyleProfile } from "../../../types";

export default function LibraryStylesPage() {
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();

  const {
    styleProfiles,
    selectedProfile,
    setSelectedProfile,
    selectedProfileId,
    setSelectedProfileId,
    isStyleLoading,
    handleCreateStyle,
    handleDeleteStyle,
    handleDuplicateStyle,
    handleLoadProfile,
    handleUpdateStyle,
    sdModels,
    sdModelMap,
    filteredLorasForEditor,
    filteredEmbeddingsForEditor,
    characterCounts,
    linkedCharacters,
    handleSetProfileModel,
    handleToggleProfileLora,
    handleToggleProfileEmbedding,
    selectedBaseModel,
  } = useStyleTab({
    showToast,
    confirmDialog: confirm,
    promptDialog: confirm,
  });

  // Escape key: close editor
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && selectedProfileId != null && !dialogProps.open) {
        setSelectedProfile(null);
        setSelectedProfileId(null);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [selectedProfileId, setSelectedProfile, setSelectedProfileId, dialogProps.open]);

  const handleSelect = useCallback(
    (id: number | null) => {
      if (id == null) {
        setSelectedProfile(null);
        setSelectedProfileId(null);
      } else {
        void handleLoadProfile(id);
      }
    },
    [setSelectedProfile, setSelectedProfileId, handleLoadProfile]
  );

  const renderItem = useCallback(
    (item: StyleProfile, isSelected: boolean) => {
      const sdModel = item.sd_model_id != null ? sdModelMap.get(item.sd_model_id) : undefined;
      const loraCount = item.loras?.length ?? 0;
      const charCount = characterCounts.get(item.id) ?? 0;

      return (
        <div className="flex flex-col gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <span
              className={`truncate text-[13px] font-semibold ${isSelected ? "text-zinc-900" : "text-zinc-700"}`}
            >
              {item.display_name || item.name}
            </span>
            {item.is_default && (
              <span className="shrink-0 rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-bold text-indigo-600">
                Default
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-1">
            {sdModel && (
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[11px] font-semibold text-emerald-600">
                {sdModel.display_name || sdModel.name}
              </span>
            )}
            {loraCount > 0 && (
              <span className="rounded-full border border-violet-200 bg-violet-50 px-1.5 py-0.5 text-[11px] font-semibold text-violet-600">
                {loraCount} LoRA{loraCount > 1 ? "s" : ""}
              </span>
            )}
            {charCount > 0 && (
              <span className="rounded-full border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[11px] font-semibold text-sky-600">
                {charCount} char{charCount > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
      );
    },
    [sdModelMap, characterCounts]
  );

  const renderDetail = useCallback(
    (item: StyleProfile) => {
      // item is the shallow list entry; selectedProfile is the full detail from API.
      // While API is loading, selectedProfile may be null or stale — show spinner.
      if (!selectedProfile || selectedProfile.id !== item.id) {
        return (
          <div className="flex h-32 items-center justify-center">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-600" />
          </div>
        );
      }
      return (
        <div className="p-6">
          <div className="mb-4 flex items-center justify-end gap-1">
            <button
              onClick={() => handleDuplicateStyle(item.id)}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
              title="복제"
            >
              <Copy className="h-3.5 w-3.5" />
              복제
            </button>
            <button
              onClick={() => handleDeleteStyle(item.id)}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-500 hover:bg-red-50 hover:text-red-500"
              title="삭제"
            >
              <Trash2 className="h-3.5 w-3.5" />
              삭제
            </button>
          </div>
          <StyleProfileEditor
            profile={selectedProfile}
            sdModels={sdModels}
            loraEntries={filteredLorasForEditor}
            embeddings={filteredEmbeddingsForEditor}
            linkedCharacters={linkedCharacters}
            selectedBaseModel={selectedBaseModel}
            onUpdateStyle={handleUpdateStyle}
            onSetModel={handleSetProfileModel}
            onToggleLora={handleToggleProfileLora}
            onToggleEmbedding={handleToggleProfileEmbedding}
          />
        </div>
      );
    },
    [
      selectedProfile,
      sdModels,
      filteredLorasForEditor,
      filteredEmbeddingsForEditor,
      linkedCharacters,
      selectedBaseModel,
      handleUpdateStyle,
      handleSetProfileModel,
      handleToggleProfileLora,
      handleToggleProfileEmbedding,
      handleDuplicateStyle,
      handleDeleteStyle,
    ]
  );

  return (
    <div className="h-full">
      <LibraryMasterDetail<StyleProfile>
        items={styleProfiles}
        selectedId={selectedProfileId}
        onSelect={handleSelect}
        renderDetail={renderDetail}
        renderItem={renderItem}
        onAdd={handleCreateStyle}
        searchPlaceholder="Search styles..."
        loading={isStyleLoading}
        emptyState={<p className="text-xs text-zinc-400">No styles yet. Click + to create one.</p>}
        detailEmptyState={<p className="text-sm text-zinc-400">Select a style to edit</p>}
      />
      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
