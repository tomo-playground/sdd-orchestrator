"use client";

import { useState, useCallback } from "react";
import { ArrowLeft } from "lucide-react";
import { useUIStore } from "../../../store/useUIStore";
import { useVoicePresets } from "../../../hooks/useVoicePresets";
import LibraryMasterDetail from "../../../components/layout/LibraryMasterDetail";
import VoiceDetailPanel from "./VoiceDetailPanel";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import type { VoicePreset } from "../../../types";

export default function VoicesPage() {
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
    previewUrl,
    handleCreate,
    handleEdit,
    handleDelete,
    handlePreview,
    handleSave,
    handleCancel,
    playAudio,
    set,
  } = useVoicePresets({
    showToast,
    confirmDialog: confirm,
    onCreated: (id) => setSelectedId(id),
  });

  const isCreating = editing != null && editId == null;

  const handleSelect = useCallback(
    async (id: number | null) => {
      if (editing) {
        const ok = await confirm({
          title: "변경사항 폐기",
          message: "저장하지 않은 변경사항이 있습니다. 폐기하시겠습니까?",
          confirmLabel: "폐기",
          variant: "danger",
        });
        if (!ok) return;
        handleCancel();
      }
      setSelectedId(id);
    },
    [editing, handleCancel, confirm],
  );

  const handleCreateNew = useCallback(() => {
    setSelectedId(null);
    handleCreate();
  }, [handleCreate]);

  const filterFn = useCallback(
    (item: VoicePreset, q: string) =>
      item.name.toLowerCase().includes(q) ||
      (item.description?.toLowerCase().includes(q) ?? false) ||
      (item.voice_design_prompt?.toLowerCase().includes(q) ?? false),
    [],
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
      <LibraryMasterDetail<VoicePreset>
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
            {(item.description || item.voice_design_prompt) && (
              <span className="truncate text-xs text-zinc-400">
                {item.description || item.voice_design_prompt}
              </span>
            )}
          </div>
        )}
        renderDetail={(item) => (
          <VoiceDetailPanel
            preset={item}
            editing={editId === item.id ? editing : null}
            onEdit={() => handleEdit(item)}
            onDelete={() => void handleDelete(item)}
            {...formProps}
          />
        )}
        onAdd={handleCreateNew}
        searchPlaceholder="이름 또는 프롬프트 검색..."
        loading={isLoading}
        emptyState="음성 프리셋이 없습니다"
        filterFn={filterFn}
        detailEmptyState={
          isCreating ? <VoiceDetailPanel editing={editing} {...formProps} /> : undefined
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
          <VoiceDetailPanel editing={editing} {...formProps} />
        </div>
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
