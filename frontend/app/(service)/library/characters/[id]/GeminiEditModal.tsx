"use client";

import { useState } from "react";
import { X } from "lucide-react";
import Button from "../../../../components/ui/Button";
import PromptEditDiff from "../../../../components/prompt/PromptEditDiff";

const EXAMPLES = [
  "Smile brightly, looking at viewer",
  "Sitting on chair with hands on lap",
  "Turn around, looking over shoulder",
  "Wave hand with cheerful expression",
  "Close-up face portrait",
  "Standing with arms crossed",
];

type Props = {
  previewImageUrl: string | undefined;
  isProcessing: boolean;
  currentPrompt: string;
  characterId: number;
  onClose: () => void;
  onSubmit: (instruction: string) => void;
  onApplyPromptEdit: (editedPrompt: string) => void;
};

export default function GeminiEditModal({
  previewImageUrl,
  isProcessing,
  currentPrompt,
  characterId,
  onClose,
  onSubmit,
  onApplyPromptEdit,
}: Props) {
  const [instruction, setInstruction] = useState("");
  const [phase, setPhase] = useState<"input" | "diff">("input");
  const [diffInstruction, setDiffInstruction] = useState("");

  const handlePromptPreview = () => {
    if (!instruction.trim()) return;
    setDiffInstruction(instruction.trim());
    setPhase("diff");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-bold text-zinc-800">
            {phase === "input" ? "Edit with Gemini" : "Prompt Edit Preview"}
          </h3>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {phase === "input" && (
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

            {/* Examples */}
            <div>
              <label className="mb-2 block text-xs font-semibold text-zinc-700">
                How would you like to change this image?
              </label>
              <div className="mb-2 flex flex-wrap gap-1.5">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setInstruction(ex)}
                    className="rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-[12px] text-zinc-600 transition hover:border-indigo-300 hover:bg-indigo-50"
                  >
                    {ex}
                  </button>
                ))}
              </div>
              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Describe the change in natural language..."
                className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-indigo-400"
                rows={3}
              />
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={handlePromptPreview}
                disabled={!instruction.trim()}
                className="w-full"
              >
                ✨ Prompt Preview
              </Button>
              <div className="flex justify-end gap-2">
                <Button variant="secondary" size="sm" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onSubmit(instruction)}
                  disabled={!instruction.trim() || isProcessing}
                  loading={isProcessing}
                >
                  🖼️ Direct Image Edit (~$0.04)
                </Button>
              </div>
            </div>

            <p className="text-[11px] text-zinc-400">
              Prompt Preview: review tag changes before applying. Image Edit: Gemini modifies the
              image directly.
            </p>
          </div>
        )}

        {phase === "diff" && (
          <PromptEditDiff
            currentPrompt={currentPrompt}
            instruction={diffInstruction}
            characterId={characterId}
            onApply={(edited) => {
              onApplyPromptEdit(edited);
              onClose();
            }}
            onCancel={() => setPhase("input")}
          />
        )}
      </div>
    </div>
  );
}
