"use client";

type ValidationSummary = {
  ok: number;
  warn: number;
  error: number;
};

type SceneListHeaderProps = {
  // Actions
  onValidate: () => void;
  onAutoFixAll: () => void;
  onAddScene: () => void;
  // Settings
  imageCheckMode: "local" | "gemini";
  onImageCheckModeChange: (mode: "local" | "gemini") => void;
  multiGenEnabled: boolean;
  onMultiGenEnabledChange: (enabled: boolean) => void;
  // Validation summary
  validationSummary: ValidationSummary;
  // Disable state
  scenesCount: number;
};

export default function SceneListHeader({
  onValidate,
  onAutoFixAll,
  onAddScene,
  imageCheckMode,
  onImageCheckModeChange,
  multiGenEnabled,
  onMultiGenEnabledChange,
  validationSummary,
  scenesCount,
}: SceneListHeaderProps) {
  const totalValidation = validationSummary.ok + validationSummary.warn + validationSummary.error;

  return (
    <div className="grid gap-4">
      {/* Header Row */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">Scenes</h2>
          <p className="text-xs text-zinc-500">
            Upload the exact images you want for each scene.
          </p>
        </div>
        {/* Action Buttons - Right */}
        <div className="flex items-center gap-2">
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
            Auto Fix All
          </button>
          <button
            onClick={onAddScene}
            className="rounded-full border border-zinc-300 bg-white px-4 py-2 text-xs font-semibold tracking-[0.2em] text-zinc-600 uppercase shadow-sm transition hover:bg-zinc-50"
          >
            + Add Scene
          </button>
        </div>
      </div>
      {/* Settings Row */}
      <div className="flex items-center gap-3 rounded-xl border border-zinc-100 bg-zinc-50/50 px-4 py-2">
        <span className="text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">Settings</span>
        <div className="h-4 w-px bg-zinc-200" />
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-medium text-zinc-500">Image Check</span>
          <select
            value={imageCheckMode}
            onChange={(e) => onImageCheckModeChange(e.target.value as "local" | "gemini")}
            className="rounded-lg border border-zinc-200 bg-white px-2 py-1 text-[10px] text-zinc-600"
          >
            <option value="local">Local (WD14)</option>
            <option value="gemini">Gemini (Cloud)</option>
          </select>
        </div>
        <div className="h-4 w-px bg-zinc-200" />
        <label className="flex items-center gap-2 text-[10px] font-medium text-zinc-500 cursor-pointer">
          3x Candidates
          <input
            type="checkbox"
            checked={multiGenEnabled}
            onChange={(e) => onMultiGenEnabledChange(e.target.checked)}
            className="h-3.5 w-3.5 accent-zinc-900"
          />
        </label>
      </div>

      {/* Validation Summary Badges */}
      {totalValidation > 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-emerald-600 uppercase">
            OK {validationSummary.ok}
          </span>
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-amber-600 uppercase">
            Warn {validationSummary.warn}
          </span>
          <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-rose-600 uppercase">
            Error {validationSummary.error}
          </span>
        </div>
      )}
    </div>
  );
}
