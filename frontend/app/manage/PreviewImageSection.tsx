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
    <div className="flex flex-col items-center gap-2">
      {/* Image */}
      {previewImageUrl ? (
        <div className="relative">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewImageUrl}
            alt="Character Preview"
            onClick={onOpenPreview}
            className={`h-52 w-auto rounded-xl border-2 object-cover object-top cursor-pointer hover:shadow-lg transition-all ${previewLocked ? "border-amber-300" : "border-zinc-200 hover:border-zinc-400"
              }`}
          />
          {previewLocked && (
            <div className="absolute top-1.5 right-1.5 rounded-full bg-amber-500 p-1">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="white" className="w-3 h-3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
              </svg>
            </div>
          )}
        </div>
      ) : (
        <div className="h-52 w-36 rounded-xl border-2 border-dashed border-zinc-200 flex items-center justify-center">
          <span className="text-xs text-zinc-300">No image</span>
        </div>
      )}

      {/* Lock toggle */}
      {previewImageUrl && (
        <button
          type="button"
          onClick={() => setPreviewLocked(!previewLocked)}
          className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold transition ${previewLocked
              ? "bg-amber-100 text-amber-700 border border-amber-300"
              : "bg-zinc-100 text-zinc-500 border border-zinc-200 hover:bg-zinc-200"
            }`}
        >
          {previewLocked ? "Locked" : "Unlocked"}
        </button>
      )}

      {/* Buttons */}
      <div className="flex flex-col gap-1.5 w-full">
        <button
          type="button"
          onClick={onGenerate}
          disabled={isCreateMode || previewLocked || anyLoading}
          className="w-full flex items-center justify-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-[11px] font-semibold text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed"
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
          className="w-full flex items-center justify-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-[11px] font-semibold text-indigo-600 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
        <button
          type="button"
          onClick={onOpenGeminiEdit}
          disabled={isCreateMode || previewLocked || !previewImageUrl || anyLoading}
          className="w-full flex items-center justify-center gap-1.5 rounded-lg border border-purple-200 bg-gradient-to-r from-purple-50 to-pink-50 px-3 py-1.5 text-[11px] font-semibold text-purple-600 hover:from-purple-100 hover:to-pink-100 disabled:opacity-50 disabled:cursor-not-allowed"
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

      {isCreateMode && (
        <p className="text-[10px] text-zinc-400 text-center">
          Save first to generate.
        </p>
      )}
    </div>
  );
}
