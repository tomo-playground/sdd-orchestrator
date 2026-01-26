"use client";

type ValidationSummary = {
  ok: number;
  warn: number;
  error: number;
};

type ReferenceImage = {
  character_key: string;
  filename: string;
  preset?: { weight: number; model: string; description?: string };
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
  useControlnet: boolean;
  onUseControlnetChange: (enabled: boolean) => void;
  controlnetWeight: number;
  onControlnetWeightChange: (weight: number) => void;
  // IP-Adapter settings
  useIpAdapter: boolean;
  onUseIpAdapterChange: (enabled: boolean) => void;
  ipAdapterReference: string;
  onIpAdapterReferenceChange: (ref: string) => void;
  ipAdapterWeight: number;
  onIpAdapterWeightChange: (weight: number) => void;
  referenceImages: ReferenceImage[];
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
  useControlnet,
  onUseControlnetChange,
  controlnetWeight,
  onControlnetWeightChange,
  useIpAdapter,
  onUseIpAdapterChange,
  ipAdapterReference,
  onIpAdapterReferenceChange,
  ipAdapterWeight,
  onIpAdapterWeightChange,
  referenceImages,
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
        <div className="h-4 w-px bg-zinc-200" />
        <label className="flex items-center gap-2 text-[10px] font-medium text-zinc-500 cursor-pointer">
          ControlNet
          <input
            type="checkbox"
            checked={useControlnet}
            onChange={(e) => onUseControlnetChange(e.target.checked)}
            className="h-3.5 w-3.5 accent-violet-600"
          />
        </label>
        {useControlnet && (
          <>
            <span className="text-[10px] font-medium text-zinc-500">Weight</span>
            <input
              type="range"
              min="0.3"
              max="1.0"
              step="0.1"
              value={controlnetWeight}
              onChange={(e) => onControlnetWeightChange(parseFloat(e.target.value))}
              className="h-1 w-16 accent-violet-600"
            />
            <span className="text-[10px] font-semibold text-violet-600">{controlnetWeight.toFixed(1)}</span>
          </>
        )}
        <div className="h-4 w-px bg-zinc-200" />
        <label className="flex items-center gap-2 text-[10px] font-medium text-zinc-500 cursor-pointer">
          IP-Adapter
          <input
            type="checkbox"
            checked={useIpAdapter}
            onChange={(e) => onUseIpAdapterChange(e.target.checked)}
            className="h-3.5 w-3.5 accent-amber-600"
          />
        </label>
        {useIpAdapter && (
          <>
            <select
              value={ipAdapterReference}
              onChange={(e) => {
                const selectedKey = e.target.value;
                onIpAdapterReferenceChange(selectedKey);
                // Apply preset weight if available
                const matchingRef = referenceImages.find(r => r.character_key === selectedKey);
                if (matchingRef?.preset?.weight) {
                  onIpAdapterWeightChange(matchingRef.preset.weight);
                }
              }}
              className="rounded-lg border border-zinc-200 bg-white px-2 py-1 text-[10px] text-zinc-600"
            >
              <option value="">Select Reference</option>
              {referenceImages.map((ref) => (
                <option key={ref.character_key} value={ref.character_key}>
                  {ref.character_key} {ref.preset ? `(${ref.preset.weight})` : ""}
                </option>
              ))}
            </select>
            <input
              type="range"
              min="0.3"
              max="1.0"
              step="0.05"
              value={ipAdapterWeight}
              onChange={(e) => onIpAdapterWeightChange(parseFloat(e.target.value))}
              className="h-1 w-12 accent-amber-600"
            />
            <span className="text-[10px] font-semibold text-amber-600">{ipAdapterWeight.toFixed(2)}</span>
          </>
        )}
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
