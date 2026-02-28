"use client";

import { useEffect } from "react";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import ConfirmDialog, { useConfirm } from "../../../components/ui/ConfirmDialog";
import { useUIStore } from "../../../store/useUIStore";
import StyleProfileEditor from "./StyleProfileEditor";
import { useStyleTab } from "../../../hooks/styles/useStyleTab";

export default function LibraryStylesPage() {
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();

  const {
    styleProfiles,
    selectedProfile,
    setSelectedProfile,
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
      if (e.key === "Escape" && selectedProfile && !dialogProps.open) {
        setSelectedProfile(null);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [selectedProfile, setSelectedProfile, dialogProps.open]);

  return (
    <div className="px-8 py-6">
      <section className="grid gap-8 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
        {/* Style Profiles List */}
        <div className="grid gap-6">
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <span className="text-[13px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
              Style Profiles
            </span>
            <button
              type="button"
              onClick={handleCreateStyle}
              className="rounded-full bg-zinc-900 px-4 py-1.5 text-[13px] font-bold text-white shadow hover:bg-zinc-700"
            >
              + New Style
            </button>
          </div>

          {isStyleLoading ? (
            <div className="flex justify-center p-8">
              <LoadingSpinner />
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {styleProfiles.map((style) => {
                const sdModel =
                  style.sd_model_id != null ? sdModelMap.get(style.sd_model_id) : undefined;
                const loraCount = style.loras?.length ?? 0;
                const charCount = characterCounts.get(style.id) ?? 0;
                return (
                  <div
                    key={style.id}
                    className={`flex flex-col gap-3 rounded-2xl border p-4 transition-all hover:shadow-md ${
                      selectedProfile?.id === style.id
                        ? "border-indigo-300 bg-indigo-50/10"
                        : "border-zinc-200 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="truncate font-bold text-zinc-700">
                          {style.display_name || style.name}
                        </span>
                        {style.is_default && (
                          <span className="shrink-0 rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-bold text-indigo-600">
                            Default
                          </span>
                        )}
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <button
                          onClick={() => handleDuplicateStyle(style.id)}
                          className="rounded p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
                          title="Duplicate"
                        >
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDeleteStyle(style.id)}
                          className="rounded p-1.5 text-zinc-400 hover:bg-red-50 hover:text-red-500"
                          title="Delete"
                        >
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {sdModel && (
                        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-600">
                          {sdModel.display_name || sdModel.name}
                        </span>
                      )}
                      {loraCount > 0 && (
                        <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[11px] font-semibold text-violet-600">
                          {loraCount} LoRA{loraCount > 1 ? "s" : ""}
                        </span>
                      )}
                      {charCount > 0 && (
                        <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-semibold text-sky-600">
                          {charCount} character{charCount > 1 ? "s" : ""}
                        </span>
                      )}
                    </div>

                    <button
                      onClick={() => handleLoadProfile(style.id)}
                      className="w-full rounded-xl border border-zinc-200 bg-white py-2 text-[13px] font-bold text-zinc-500 hover:border-indigo-200 hover:text-indigo-600"
                    >
                      {selectedProfile?.id === style.id ? "Editing..." : "Edit Profile"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Editor Panel */}
        {selectedProfile && (
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
            onClose={() => setSelectedProfile(null)}
          />
        )}

        <ConfirmDialog {...dialogProps} />
      </section>
    </div>
  );
}
