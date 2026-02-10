"use client";

type SceneListHeaderProps = {
  onValidate: () => void;
  onAutoFixAll: () => void;
  onAddScene: () => void;
  scenesCount: number;
};

export default function SceneListHeader({
  onValidate,
  onAutoFixAll,
  onAddScene,
  scenesCount,
}: SceneListHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="min-w-0">
        <h2 className="text-lg font-semibold text-zinc-900">Scenes</h2>
        <p className="text-xs text-zinc-500">Manage prompts and generate images per scene.</p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <button
          onClick={onValidate}
          className="rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold tracking-[0.2em] text-white uppercase shadow"
        >
          Validate
        </button>
        <button
          onClick={onAutoFixAll}
          disabled={scenesCount === 0}
          className="rounded-full border border-zinc-300 bg-white px-4 py-2 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Fix All
        </button>
        <button
          onClick={onAddScene}
          className="rounded-full border border-zinc-300 bg-white px-4 py-2 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition hover:bg-zinc-50"
        >
          + Add Scene
        </button>
      </div>
    </div>
  );
}
