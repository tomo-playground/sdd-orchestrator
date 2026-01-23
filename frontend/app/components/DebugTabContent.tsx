"use client";

import type { Scene } from "../types";

type DebugTabContentProps = {
  scene: Scene;
  onGenerateDebug: () => void;
};

export default function DebugTabContent({
  scene,
  onGenerateDebug,
}: DebugTabContentProps) {
  return (
    <div className="grid gap-3 rounded-xl border border-zinc-200 bg-white/80 p-4">
      <button
        type="button"
        onClick={onGenerateDebug}
        className="w-full rounded-full border border-zinc-300 bg-white py-2.5 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase transition hover:bg-zinc-50"
      >
        Generate Debug Info
      </button>
      {scene.debug_payload && (
        <textarea
          value={scene.debug_payload}
          readOnly
          rows={8}
          className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 font-mono text-[10px] text-zinc-600"
        />
      )}
      {!scene.debug_payload && (
        <p className="text-center text-xs text-zinc-400">Generate Debug Info를 클릭하세요</p>
      )}
    </div>
  );
}
