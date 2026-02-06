"use client";

import { SIDE_PANEL_CLASSES, SIDE_PANEL_LABEL } from "../ui/variants";

type ReferenceImage = {
  character_key: string;
  filename: string;
  preset?: { weight: number; model: string; description?: string };
};

type SceneMatchRate = {
  match_rate?: number;
  missing?: string[];
};

type ValidationSummary = {
  ok: number;
  warn: number;
  error: number;
};

type SceneSidePanelProps = {
  // Settings
  multiGenEnabled: boolean;
  onMultiGenEnabledChange: (enabled: boolean) => void;
  useControlnet: boolean;
  onUseControlnetChange: (enabled: boolean) => void;
  controlnetWeight: number;
  onControlnetWeightChange: (weight: number) => void;
  useIpAdapter: boolean;
  onUseIpAdapterChange: (enabled: boolean) => void;
  ipAdapterReference: string;
  onIpAdapterReferenceChange: (ref: string) => void;
  ipAdapterWeight: number;
  onIpAdapterWeightChange: (weight: number) => void;
  referenceImages: ReferenceImage[];
  // Current speaker context for IP-Adapter display
  currentSpeaker?: "Narrator" | "A" | "B";
  // Validation
  validationSummary: ValidationSummary;
  // Match rates
  imageValidationResults?: Record<number, SceneMatchRate>;
  scenes?: { id: number; order?: number }[];
  onSceneSelect?: (index: number) => void;
};

export default function SceneSidePanel({
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
  currentSpeaker,
  validationSummary,
  imageValidationResults,
  scenes: scenesInfo,
  onSceneSelect,
}: SceneSidePanelProps) {
  const isNarrator = currentSpeaker === "Narrator";
  const totalValidation = validationSummary.ok + validationSummary.warn + validationSummary.error;
  const hasMatchRateGrid =
    scenesInfo &&
    scenesInfo.length > 0 &&
    imageValidationResults &&
    Object.keys(imageValidationResults).length > 0;

  return (
    <div className={SIDE_PANEL_CLASSES}>
      {/* Generation Settings */}
      <div>
        <label className={SIDE_PANEL_LABEL}>Settings</label>
        <div className="space-y-2">
          <ToggleRow
            label="3x Candidates"
            checked={multiGenEnabled}
            onChange={onMultiGenEnabledChange}
          />
          <ToggleRow
            label="ControlNet"
            checked={useControlnet}
            onChange={onUseControlnetChange}
            accent="violet"
            disabled={isNarrator}
            disabledReason="Narrator 씬에서는 사용 불가"
          />
          {useControlnet && !isNarrator && (
            <SliderRow
              value={controlnetWeight}
              onChange={onControlnetWeightChange}
              min={0.3}
              max={1.0}
              step={0.1}
              accent="violet"
            />
          )}
          <ToggleRow
            label={currentSpeaker === "B" ? "IP-Adapter (B)" : "IP-Adapter"}
            checked={useIpAdapter}
            onChange={onUseIpAdapterChange}
            accent={currentSpeaker === "B" ? "sky" : "amber"}
            disabled={isNarrator}
            disabledReason="Narrator 씬에서는 사용 불가"
          />
          {useIpAdapter && !isNarrator && (
            <>
              <select
                value={ipAdapterReference}
                onChange={(e) => {
                  const key = e.target.value;
                  onIpAdapterReferenceChange(key);
                  const match = referenceImages.find((r) => r.character_key === key);
                  if (match?.preset?.weight) onIpAdapterWeightChange(match.preset.weight);
                }}
                className={`w-full rounded-lg border bg-white px-2 py-1.5 text-[10px] text-zinc-600 ${
                  currentSpeaker === "B" ? "border-sky-300" : "border-zinc-200"
                }`}
              >
                <option value="">Select Reference</option>
                {referenceImages.map((ref) => (
                  <option key={ref.character_key} value={ref.character_key}>
                    {ref.character_key} {ref.preset ? `(${ref.preset.weight})` : ""}
                  </option>
                ))}
              </select>
              <SliderRow
                value={ipAdapterWeight}
                onChange={onIpAdapterWeightChange}
                min={0.3}
                max={1.0}
                step={0.05}
                accent={currentSpeaker === "B" ? "sky" : "amber"}
              />
            </>
          )}
        </div>
      </div>

      {/* Validation Summary */}
      {totalValidation > 0 && (
        <div>
          <label className={SIDE_PANEL_LABEL}>Validation</label>
          <div className="grid grid-cols-3 gap-1.5">
            <StatBadge label="OK" count={validationSummary.ok} color="emerald" />
            <StatBadge label="Warn" count={validationSummary.warn} color="amber" />
            <StatBadge label="Error" count={validationSummary.error} color="rose" />
          </div>
        </div>
      )}

      {/* Match Rate Grid */}
      {hasMatchRateGrid && (
        <div>
          <label className={SIDE_PANEL_LABEL}>Match Rates</label>
          <div className="grid grid-cols-3 gap-1.5">
            {scenesInfo!.map((scene, index) => {
              const result = imageValidationResults![scene.id];
              const rate = result?.match_rate;
              const hasRate = rate !== undefined && rate !== null;
              const colorClass = !hasRate
                ? "border-zinc-200 bg-zinc-50 text-zinc-400"
                : rate >= 80
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : rate >= 60
                    ? "border-amber-200 bg-amber-50 text-amber-700"
                    : "border-rose-200 bg-rose-50 text-rose-700";

              return (
                <button
                  key={scene.id}
                  type="button"
                  onClick={() => onSceneSelect?.(index)}
                  title={
                    hasRate
                      ? `Scene ${index + 1}: ${Math.round(rate)}% match`
                      : `Scene ${index + 1}: not validated`
                  }
                  className={`flex cursor-pointer flex-col items-center rounded-lg border px-1 py-1.5 text-[9px] leading-tight font-semibold transition-all hover:scale-105 ${colorClass}`}
                >
                  <span>S{index + 1}</span>
                  <span>{hasRate ? `${Math.round(rate)}%` : "--"}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Sub-components ---- */

function ToggleRow({
  label,
  checked,
  onChange,
  accent = "zinc",
  disabled = false,
  disabledReason,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  accent?: string;
  disabled?: boolean;
  disabledReason?: string;
}) {
  return (
    <label
      className={`flex items-center justify-between text-[10px] font-medium ${
        disabled ? "cursor-not-allowed text-zinc-300" : "cursor-pointer text-zinc-500"
      }`}
      title={disabled ? disabledReason : undefined}
    >
      {label}
      <input
        type="checkbox"
        checked={disabled ? false : checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className={`h-3.5 w-3.5 accent-${accent}-600 ${disabled ? "opacity-30" : ""}`}
      />
    </label>
  );
}

function SliderRow({
  value,
  onChange,
  min,
  max,
  step,
  accent = "zinc",
}: {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  accent?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className={`h-1 flex-1 accent-${accent}-600`}
      />
      <span className={`text-[10px] font-semibold text-${accent}-600 w-8 text-right`}>
        {value.toFixed(step < 0.1 ? 2 : 1)}
      </span>
    </div>
  );
}

function StatBadge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div
      className={`flex flex-col items-center rounded-lg border border-${color}-200 bg-${color}-50 px-2 py-1.5`}
    >
      <span className={`text-xs font-bold text-${color}-700`}>{count}</span>
      <span className={`text-[9px] text-${color}-500`}>{label}</span>
    </div>
  );
}
