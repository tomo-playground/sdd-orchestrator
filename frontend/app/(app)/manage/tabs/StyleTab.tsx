"use client";

import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import StyleProfileEditor from "../StyleProfileEditor";
import { useStyleTab } from "../hooks/useStyleTab";

export default function StyleTab() {
  const {
    styleProfiles,
    selectedProfile,
    setSelectedProfile,
    isStyleLoading,
    handleCreateStyle,
    handleDeleteStyle,
    handleUpdateStyle,
    handleDuplicateStyle,
    handleLoadProfile,
    sdModels,
    embeddings,
    loraEntries,
    handleSetProfileModel,
    handleToggleProfileLora,
    handleToggleProfileEmbedding,
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
  } = useStyleTab();

  return (
    <section className="grid gap-8 rounded-2xl border border-zinc-200/60 bg-white p-8 text-xs text-zinc-600 shadow-sm">
      {/* Style Profiles List */}
      <div className="grid gap-6">
        <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
          <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
            Style Profiles
          </span>
          <button
            type="button"
            onClick={handleCreateStyle}
            className="rounded-full bg-zinc-900 px-4 py-1.5 text-[10px] font-bold text-white shadow hover:bg-zinc-700"
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
            {styleProfiles.map((style) => (
              <div
                key={style.id}
                className={`flex flex-col gap-3 rounded-2xl border p-4 transition-all hover:shadow-md ${
                  selectedProfile?.id === style.id
                    ? "border-indigo-300 bg-indigo-50/10"
                    : "border-zinc-200 bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-zinc-700">{style.name}</span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleDuplicateStyle(style.id)}
                      className="rounded p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
                      title="Duplicate"
                    >
                      <svg
                        className="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"
                        />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleDeleteStyle(style.id)}
                      className="rounded p-1.5 text-zinc-400 hover:bg-rose-50 hover:text-rose-500"
                      title="Delete"
                    >
                      <svg
                        className="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                </div>

                <button
                  onClick={() => handleLoadProfile(style.id)}
                  className="w-full rounded-xl border border-zinc-200 bg-white py-2 text-[10px] font-bold text-zinc-500 hover:border-indigo-200 hover:text-indigo-600"
                >
                  {selectedProfile?.id === style.id ? "Editing..." : "Edit Profile"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Editor Panel */}
      {selectedProfile && (
        <StyleProfileEditor
          profile={selectedProfile}
          sdModels={sdModels}
          loraEntries={loraEntries}
          embeddings={embeddings}
          onUpdateStyle={handleUpdateStyle}
          onSetModel={handleSetProfileModel}
          onToggleLora={handleToggleProfileLora}
          onToggleEmbedding={handleToggleProfileEmbedding}
          onClose={() => setSelectedProfile(null)}
        />
      )}

      {/* Model & Civitai Section */}
      <div className="grid gap-8 border-t border-zinc-100 pt-8">
        <div className="grid gap-8 md:grid-cols-2">
          {/* SD Checkpoints */}
          <div className="grid gap-4">
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
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
                    <p className="truncate text-[9px] text-zinc-400">
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
              <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
                Embeddings
              </span>
            </div>
            <div className="custom-scrollbar max-h-60 overflow-y-auto rounded-xl border border-zinc-200 bg-zinc-50 p-2">
              {embeddings.map((emb) => (
                <div
                  key={emb.name}
                  className="flex items-center justify-between rounded-lg p-2 transition hover:bg-white"
                >
                  <span className="text-[10px] font-bold text-zinc-600">{emb.name}</span>
                  <span className="text-[9px] text-zinc-400">{emb.embedding_type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Civitai Search */}
        <div className="grid gap-6 rounded-2xl border border-zinc-200 bg-zinc-50/50 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-[10px] font-bold tracking-[0.2em] text-zinc-500 uppercase">
              Civitai Model Search
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={civitaiSearch}
                onChange={(e) => setCivitaiSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCivitaiSearch()}
                placeholder="Search LoRA or Checkpoint..."
                className="w-64 rounded-full border border-zinc-200 px-4 py-1.5 text-[10px] outline-none focus:border-indigo-400"
              />
              <button
                onClick={handleCivitaiSearch}
                disabled={isSearchingCivitai}
                className="rounded-full bg-indigo-600 px-4 py-1.5 text-[10px] font-bold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
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
                      <img
                        src={item.preview_image}
                        alt={item.name}
                        className="h-full w-full object-cover"
                      />
                    )}
                    <div className="absolute top-2 right-2 rounded bg-black/50 px-2 py-0.5 text-[9px] font-bold text-white backdrop-blur-md">
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
                        className="flex-1 rounded-lg bg-zinc-900 py-1.5 text-[10px] font-bold text-white transition hover:bg-indigo-600"
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

        {/* Registered LoRAs List */}
        <div className="grid gap-4">
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 uppercase">
              Registered LoRAs (Database)
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {loraEntries.map((lora) => (
              <div
                key={lora.id}
                className="relative rounded-2xl border border-zinc-200 bg-white p-4 transition hover:border-violet-200 hover:shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-50 text-[10px] font-bold text-violet-500">
                      L
                    </div>
                    <div>
                      <p className="text-xs font-bold text-zinc-700">{lora.name}</p>
                      <p className="text-[10px] text-zinc-400">
                        {lora.trigger_words?.join(", ") || "No trigger words"}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => setEditingLora(lora)}
                      className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-indigo-500"
                    >
                      <svg
                        className="h-3.5 w-3.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                        />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleDeleteLora(lora.id!)}
                      className="rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-rose-500"
                    >
                      <svg
                        className="h-3.5 w-3.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
                {lora.preview_image_url && (
                  <div className="mt-3 aspect-[3/2] w-full overflow-hidden rounded-lg bg-zinc-100">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={lora.preview_image_url}
                      alt=""
                      className="h-full w-full object-cover opacity-80"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Edit LoRA Modal */}
      {editingLora && (
        <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-2xl">
            <h3 className="mb-4 text-center text-sm font-black text-zinc-800">Edit LoRA</h3>
            <div className="grid gap-4">
              <div>
                <label className="mb-1 block text-[10px] font-bold tracking-wider text-zinc-500 uppercase">
                  Name
                </label>
                <input
                  value={editingLora.name}
                  onChange={(e) => setEditingLora({ ...editingLora, name: e.target.value })}
                  className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs font-bold text-zinc-700 outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-bold tracking-wider text-zinc-500 uppercase">
                  Trigger Word (Optional)
                </label>
                <input
                  value={editingLora.trigger_words?.join(", ") || ""}
                  onChange={(e) =>
                    setEditingLora({
                      ...editingLora,
                      trigger_words: e.target.value.split(",").map((s) => s.trim()),
                    })
                  }
                  className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-xs font-bold text-zinc-700 outline-none focus:border-indigo-500"
                  placeholder="e.g. style-pixel"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-bold tracking-wider text-zinc-500 uppercase">
                  Default Weight: {editingLora.default_weight.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="2.0"
                  step="0.1"
                  value={editingLora.default_weight ?? 1.0}
                  onChange={(e) =>
                    setEditingLora({ ...editingLora, default_weight: parseFloat(e.target.value) })
                  }
                  className="w-full"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => setEditingLora(null)}
                  className="flex-1 rounded-xl border border-zinc-200 py-2.5 text-[10px] font-bold text-zinc-500 hover:bg-zinc-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpdateLora}
                  disabled={isUpdatingLora}
                  className="flex-1 rounded-xl bg-indigo-600 py-2.5 text-[10px] font-bold text-white shadow-lg shadow-indigo-200 hover:bg-indigo-700 disabled:opacity-50"
                >
                  {isUpdatingLora ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
