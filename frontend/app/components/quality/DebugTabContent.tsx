"use client";

import { useState } from "react";
import type { Scene } from "../../types";
import CopyButton from "../ui/CopyButton";

type DebugTabContentProps = {
  scene: Scene;
  onGenerateDebug: () => void | Promise<void>;
};

export default function DebugTabContent({
  scene,
  onGenerateDebug,
}: DebugTabContentProps) {
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      await onGenerateDebug();
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="grid gap-3 rounded-xl border border-zinc-200 bg-white/80 p-4">
      <button
        type="button"
        onClick={handleGenerate}
        disabled={isGenerating}
        className="w-full rounded-full border border-zinc-300 bg-white py-2.5 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase transition hover:bg-zinc-50 disabled:opacity-50"
      >
        {isGenerating ? "Generating..." : "Generate Debug Info"}
      </button>
      {scene.debug_payload && (
        <div className="relative">
          <textarea
            value={scene.debug_payload}
            readOnly
            rows={8}
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50 p-3 pr-16 font-mono text-[10px] text-zinc-600"
          />
          <div className="absolute right-2 top-2">
            <CopyButton text={scene.debug_payload!} variant="label" />
          </div>
        </div>
      )}
      {!scene.debug_payload && !isGenerating && (
        <p className="text-center text-xs text-zinc-400">Generate Debug Info를 클릭하세요</p>
      )}
    </div>
  );
}
