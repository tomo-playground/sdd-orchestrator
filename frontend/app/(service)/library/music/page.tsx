"use client";

import { useState, useCallback } from "react";
import { ArrowLeft } from "lucide-react";
import { useUIStore } from "../../../store/useUIStore";
import { useMusic } from "../../../hooks/useMusic";
import LibraryMasterDetail from "../../../components/layout/LibraryMasterDetail";
import MusicDetailPanel from "./MusicDetailPanel";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import type { MusicPreset } from "../../../types";

export default function MusicPage() {
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const {
    presets,
    isLoading,
    editing,
    editId,
    saving,
    previewing,
    previewingId,
    playingId,
    previewUrl,
    handleCreate,
    handleEdit,
    handleDelete,
    handlePreview,
    handleSave,
    handleCancel,
    playAudio,
    previewPreset,
    set,
  } = useMusic({
    showToast,
    confirmDialog: confirm,
    onCreated: (id) => setSelectedId(id),
  });

  const isCreating = editing != null && editId == null;

  const handleSelect = useCallback(
    (id: number | null) => {
      setSelectedId(id);
      if (editing) handleCancel();
    },
    [editing, handleCancel]
  );

  const handleCreateNew = useCallback(() => {
    setSelectedId(null);
    handleCreate();
  }, [handleCreate]);

  const filterFn = useCallback(
    (item: MusicPreset, q: string) =>
      item.name.toLowerCase().includes(q) ||
      (item.description?.toLowerCase().includes(q) ?? false) ||
      (item.prompt?.toLowerCase().includes(q) ?? false),
    []
  );

  const formProps = {
    saving,
    previewing,
    previewUrl,
    onSave: handleSave,
    onCancel: handleCancel,
    onPreview: handlePreview,
    onPlayAudio: playAudio,
    onSet: set,
  };

  return (
    <div className="relative h-full">
      <LibraryMasterDetail<MusicPreset>
        items={presets}
        selectedId={selectedId}
        onSelect={handleSelect}
        renderItem={(item) => (
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center gap-1.5">
              <span className="truncate">{item.name}</span>
              {item.is_system && (
                <span className="shrink-0 rounded-full bg-indigo-50 px-1.5 py-0.5 text-[11px] text-indigo-500">
                  System
                </span>
              )}
            </div>
            {(item.description || item.prompt) && (
              <span className="truncate text-xs text-zinc-400">
                {item.description || item.prompt}
              </span>
            )}
          </div>
        )}
        renderDetail={(item) => (
          <MusicDetailPanel
            preset={item}
            editing={editId === item.id ? editing : null}
            playingId={playingId}
            previewingId={previewingId}
            onEdit={() => handleEdit(item)}
            onDelete={() => void handleDelete(item)}
            onPreviewPreset={previewPreset}
            {...formProps}
          />
        )}
        onAdd={handleCreateNew}
        searchPlaceholder="이름 또는 프롬프트 검색..."
        loading={isLoading}
        emptyState="BGM 프리셋이 없습니다"
        filterFn={filterFn}
        detailEmptyState={
          isCreating ? <MusicDetailPanel editing={editing} {...formProps} /> : undefined
        }
      />

      {/* Mobile create form overlay */}
      {isCreating && (
        <div className="absolute inset-0 z-10 overflow-y-auto bg-white md:hidden">
          <div className="sticky top-0 z-10 flex items-center border-b border-zinc-100 bg-white/90 px-4 py-2 backdrop-blur-sm">
            <button
              onClick={handleCancel}
              className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-700"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back
            </button>
          </div>
          <MusicDetailPanel editing={editing} {...formProps} />
        </div>
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
