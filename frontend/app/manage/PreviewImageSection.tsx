"use client";

import LoadingSpinner from "../components/ui/LoadingSpinner";

type Props = {
  isCreateMode: boolean;
  previewImageUrl: string;
  previewLocked: boolean;
  setPreviewLocked: (v: boolean) => void;
  isGenerating: boolean;
  isEnhancing: boolean;
  isEditing: boolean;
  onGenerate: () => void;
  onEnhance: () => void;
  onOpenGeminiEdit: () => void;
  onOpenPreview: () => void;
};

export default function PreviewImageSection({
  isCreateMode,
  previewImageUrl,
  previewLocked,
  setPreviewLocked,
  isGenerating,
  isEnhancing,
  isEditing,
  onGenerate,
  onEnhance,
  onOpenGeminiEdit,
  onOpenPreview,
}: Props) {
  const anyLoading = isGenerating || isEnhancing || isEditing;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider">Preview Image</label>
        {previewImageUrl && (
          <button
            type="button"
            onClick={() => setPreviewLocked(!previewLocked)}
            className={`flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-semibold transition ${previewLocked
                ? "bg-amber-100 text-amber-700 border border-amber-300"
                : "bg-zinc-100 text-zinc-500 border border-zinc-200 hover:bg-zinc-200"
              }`}
          >
            {previewLocked ? "Locked" : "Unlocked"}
          </button>
        )}
      </div>

      {/* URL + Generate / Enhance buttons */}
      <div className="flex gap-2">
        <input
          value={previewImageUrl}
          readOnly
          className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-mono text-zinc-500 outline-none"
        />
        <button
          type="button"
          onClick={onGenerate}
          disabled={isCreateMode || previewLocked || anyLoading}
          className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-4 py-2 text-xs font-semibold text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <>
              <LoadingSpinner size="sm" color="text-zinc-400" />
              <span>Generating...</span>
            </>
          ) : (
            "Generate"
          )}
        </button>
        <button
          type="button"
          onClick={onEnhance}
          disabled={isCreateMode || previewLocked || !previewImageUrl || anyLoading}
          className="flex items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2 text-xs font-semibold text-indigo-600 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isEnhancing ? (
            <>
              <LoadingSpinner size="sm" color="text-indigo-400" />
              <span>Enhancing...</span>
            </>
          ) : (
            "Enhance"
          )}
        </button>
      </div>

      {isCreateMode && (
        <p className="text-[10px] text-zinc-400 mt-1">
          Save the character first to generate a reference image.
        </p>
      )}

      {/* Thumbnail + Gemini Edit */}
      {previewImageUrl && (
        <div className="mt-3 flex items-center gap-3">
          <div className="relative">
            <img
              src={previewImageUrl}
              alt="Character Preview"
              onClick={onOpenPreview}
              className={`h-32 w-auto rounded-xl border-2 object-cover object-top cursor-pointer hover:shadow-lg transition-all ${previewLocked ? "border-amber-300" : "border-zinc-200 hover:border-zinc-400"
                }`}
            />
            {previewLocked && (
              <div className="absolute top-1 right-1 rounded-full bg-amber-500 p-1">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="white" className="w-3 h-3">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                </svg>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onOpenGeminiEdit}
            disabled={isCreateMode || previewLocked || anyLoading}
            className="flex items-center gap-2 rounded-xl border border-purple-200 bg-gradient-to-r from-purple-50 to-pink-50 px-4 py-2 text-xs font-semibold text-purple-600 hover:from-purple-100 hover:to-pink-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isEditing ? (
              <>
                <LoadingSpinner size="sm" color="text-purple-400" />
                <span>Editing...</span>
              </>
            ) : (
              "Edit with Gemini"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
