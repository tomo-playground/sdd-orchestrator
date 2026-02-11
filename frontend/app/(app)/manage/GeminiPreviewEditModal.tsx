"use client";

import { useFocusTrap } from "../../hooks/useFocusTrap";
import { useUIStore } from "../../store/useUIStore";

const EXAMPLE_INSTRUCTIONS = [
  "Smile brightly, looking at viewer",
  "Sitting on chair with hands on lap",
  "Turn around, looking over shoulder",
  "Wave hand with cheerful expression",
  "Close-up face portrait",
  "Standing with arms crossed",
];

type Props = {
  previewImageUrl: string;
  geminiTargetChange: string;
  setGeminiTargetChange: (v: string) => void;
  onClose: () => void;
  onSubmit: (instruction: string) => void;
};

export default function GeminiPreviewEditModal({
  previewImageUrl,
  geminiTargetChange,
  setGeminiTargetChange,
  onClose,
  onSubmit,
}: Props) {
  const trapRef = useFocusTrap(true);

  const handleClose = () => {
    setGeminiTargetChange("");
    onClose();
  };

  const showToast = useUIStore((s) => s.showToast);

  const handleStart = () => {
    if (!geminiTargetChange.trim()) {
      showToast("Please describe what to change.", "warning");
      return;
    }
    onSubmit(geminiTargetChange.trim());
  };

  return (
    <div
      className="fixed inset-0 z-[var(--z-nested-modal)] flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="gemini-preview-edit-title"
    >
      <div
        ref={trapRef}
        tabIndex={-1}
        className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl outline-none"
      >
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 id="gemini-preview-edit-title" className="text-lg font-semibold text-zinc-800">
            Edit with Gemini
          </h3>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close dialog"
            className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
          >
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Current preview */}
          {previewImageUrl && (
            <div className="flex justify-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewImageUrl}
                alt="Current Preview"
                className="h-40 w-auto rounded-xl border border-zinc-200 object-cover"
              />
            </div>
          )}

          {/* Instruction */}
          <div>
            <label
              htmlFor="gemini-preview-instruction"
              className="mb-2 block text-sm font-semibold text-zinc-700"
            >
              How would you like to change this image?
            </label>
            <div className="mb-2 flex flex-wrap gap-2">
              {EXAMPLE_INSTRUCTIONS.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setGeminiTargetChange(example)}
                  className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs text-zinc-600 transition hover:border-purple-300 hover:bg-purple-50"
                >
                  {example}
                </button>
              ))}
            </div>
            <textarea
              id="gemini-preview-instruction"
              value={geminiTargetChange}
              onChange={(e) => setGeminiTargetChange(e.target.value)}
              placeholder="Describe the change in natural language..."
              className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-purple-400"
              rows={3}
            />
          </div>

          {/* Actions */}
          <div className="flex justify-between gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleStart}
              disabled={!geminiTargetChange.trim()}
              className="flex-1 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:from-purple-600 hover:to-pink-600 disabled:cursor-not-allowed disabled:from-purple-300 disabled:to-pink-300"
            >
              Start Editing (~$0.04)
            </button>
          </div>

          <p className="text-[12px] text-zinc-400">
            Gemini preserves face and art style while editing pose, expression, and gaze.
          </p>
        </div>
      </div>
    </div>
  );
}
