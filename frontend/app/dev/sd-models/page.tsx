"use client";

import { useEffect } from "react";
import ConfirmDialog, { useConfirm } from "../../components/ui/ConfirmDialog";
import { useUIStore } from "../../store/useUIStore";
import EditLoraModal from "../../components/lora/EditLoraModal";
import { useStyleTab } from "../../hooks/styles/useStyleTab";

export default function DevSdModelsPage() {
  const showToast = useUIStore((s) => s.showToast);
  const { confirm, dialogProps } = useConfirm();

  const {
    sdModels,
    embeddings,
    loraEntries,
    editingLora,
    setEditingLora,
    isUpdatingLora,
    handleUpdateLora,
    handleDeleteLora,
    civitaiSearch,
    setCivitaiSearch,
    civitaiResults,
    isSearchingCivitai,
    handleCivitaiSearch,
    handleDownloadModel,
  } = useStyleTab({
    showToast,
    confirmDialog: confirm,
    promptDialog: confirm,
  });

  // Escape key: close Edit LoRA modal
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && editingLora && !dialogProps.open) {
        setEditingLora(null);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [editingLora, setEditingLora, dialogProps.open]);

  return (
    <div className="px-8 py-6">
      <section className="grid gap-8 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
        {/* SD Checkpoints + Embeddings */}
        <div className="grid gap-8 md:grid-cols-2">
          {/* SD Checkpoints */}
          <div className="grid gap-4">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <span className="text-[13px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                SD Checkpoints
              </span>
            </div>
            <div className="custom-scrollbar max-h-60 overflow-y-auto rounded-xl border border-zinc-200 bg-zinc-50 p-2">
              {sdModels.map((model) => (
                <div
                  key={model.name}
                  className="flex items-center gap-3 rounded-lg p-2 transition hover:bg-white"
                >
                  <div className="h-2 w-2 rounded-full bg-emerald-400" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-bold text-zinc-700">
                      {model.display_name || model.name}
                    </p>
                    <p className="truncate text-[13px] text-zinc-400">
                      {model.base_model || "Unknown Base"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Embeddings */}
          <div className="grid gap-4">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <span className="text-[13px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                Embeddings
              </span>
            </div>
            <div className="custom-scrollbar max-h-60 overflow-y-auto rounded-xl border border-zinc-200 bg-zinc-50 p-2">
              {embeddings.map((emb) => (
                <div
                  key={emb.name}
                  className="flex items-center justify-between rounded-lg p-2 transition hover:bg-white"
                >
                  <span className="text-[13px] font-bold text-zinc-600">{emb.name}</span>
                  <div className="flex items-center gap-2">
                    {emb.base_model && (
                      <span className="rounded-full border border-zinc-200 bg-zinc-100 px-1.5 py-0.5 text-[11px] font-semibold text-zinc-500">
                        {emb.base_model}
                      </span>
                    )}
                    <span className="text-[13px] text-zinc-400">{emb.embedding_type}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Civitai Search */}
        <div className="grid gap-6 rounded-2xl border border-zinc-200 bg-zinc-50/50 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-[13px] font-bold tracking-[0.2em] text-zinc-500 uppercase">
              Civitai Model Search
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={civitaiSearch}
                onChange={(e) => setCivitaiSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCivitaiSearch()}
                placeholder="Search LoRA or Checkpoint..."
                className="w-64 rounded-full border border-zinc-200 px-4 py-1.5 text-[13px] outline-none focus:border-indigo-400"
              />
              <button
                onClick={handleCivitaiSearch}
                disabled={isSearchingCivitai}
                className="rounded-full bg-indigo-600 px-4 py-1.5 text-[13px] font-bold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
              >
                {isSearchingCivitai ? "..." : "Search"}
              </button>
            </div>
          </div>

          {civitaiResults.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {civitaiResults.map((item) => (
                <div
                  key={item.civitai_id}
                  className="group relative overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm hover:shadow-md"
                >
                  <div className="relative aspect-video w-full bg-zinc-100">
                    {item.preview_image && (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img src={item.preview_image} alt={item.name} className="h-full w-full object-cover" />
                    )}
                    <div className="absolute top-2 right-2 rounded bg-black/50 px-2 py-0.5 text-[13px] font-bold text-white backdrop-blur-md">
                      LoRA
                    </div>
                  </div>
                  <div className="p-4">
                    <h4 className="mb-1 truncate text-xs font-bold text-zinc-800" title={item.name}>
                      {item.name}
                    </h4>
                    <div className="mt-3 flex items-center justify-between">
                      <button
                        onClick={() => handleDownloadModel(item.civitai_id, "LORA")}
                        className="flex-1 rounded-lg bg-zinc-900 py-1.5 text-[13px] font-bold text-white transition hover:bg-indigo-600"
                      >
                        Download
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Registered LoRAs */}
        <div className="grid gap-4">
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <span className="text-[13px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
              Registered LoRAs (Database)
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {loraEntries.map((lora) => {
              const typeBadge =
                lora.lora_type === "style"
                  ? "border-violet-200 bg-violet-50 text-violet-600"
                  : "border-sky-200 bg-sky-50 text-sky-600";
              return (
                <div
                  key={lora.id}
                  className="relative rounded-2xl border border-zinc-200 bg-white p-4 transition hover:border-violet-200 hover:shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-xs font-bold text-zinc-700">
                          {lora.display_name || lora.name}
                        </p>
                        <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[13px] font-semibold ${typeBadge}`}>
                          {lora.lora_type || "character"}
                        </span>
                        {lora.base_model && (
                          <span className="shrink-0 rounded-full border border-zinc-200 bg-zinc-100 px-1.5 py-0.5 text-[11px] font-semibold text-zinc-500">
                            {lora.base_model}
                          </span>
                        )}
                        {lora.is_multi_character_capable && (
                          <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[13px] font-semibold text-emerald-600">
                            Multi
                          </span>
                        )}
                      </div>
                      {lora.display_name && lora.display_name !== lora.name && (
                        <p className="mt-0.5 truncate font-mono text-[13px] text-zinc-400">{lora.name}</p>
                      )}
                      <p className="mt-1 text-[13px] text-zinc-400">
                        trigger: {lora.trigger_words?.join(", ") || "none"}
                      </p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[13px] text-zinc-400">
                        <span>
                          w: {lora.optimal_weight ?? lora.default_weight}
                          {lora.calibration_score != null && (
                            <span className="ml-1 text-emerald-500">({lora.calibration_score}%)</span>
                          )}
                        </span>
                        <span>range: {lora.weight_min}&ndash;{lora.weight_max}</span>
                        {lora.civitai_url && (
                          <a
                            href={lora.civitai_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-400 underline hover:text-indigo-600"
                          >
                            Civitai
                          </a>
                        )}
                      </div>
                    </div>
                    <div className="ml-2 flex shrink-0 gap-1">
                      <button
                        onClick={() => setEditingLora(lora)}
                        className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-indigo-500"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteLora(lora.id!)}
                        className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-rose-500"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  {lora.preview_image_url && (
                    <div className="mt-3 aspect-[3/2] w-full overflow-hidden rounded-lg bg-zinc-100">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={lora.preview_image_url} alt="" className="h-full w-full object-cover opacity-80" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Edit LoRA Modal */}
        {editingLora && (
          <EditLoraModal
            lora={editingLora}
            onChange={setEditingLora}
            onSave={handleUpdateLora}
            onClose={() => setEditingLora(null)}
            isSaving={isUpdatingLora}
          />
        )}

        <ConfirmDialog {...dialogProps} />
      </section>
    </div>
  );
}
