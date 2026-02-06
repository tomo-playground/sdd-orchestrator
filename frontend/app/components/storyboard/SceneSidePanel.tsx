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
  // Global settings (default values)
  multiGenEnabled: boolean;
  useControlnet: boolean;
  controlnetWeight: number;
  onControlnetWeightChange: (weight: number) => void;
  useIpAdapter: boolean;
  ipAdapterReference: string;
  onIpAdapterReferenceChange: (ref: string) => void;
  ipAdapterWeight: number;
  onIpAdapterWeightChange: (weight: number) => void;
  referenceImages: ReferenceImage[];
  // Per-scene override values (null = inherit global)
  sceneMultiGen: boolean | null | undefined;
  onSceneMultiGenChange: (v: boolean | null) => void;
  sceneControlnet: boolean | null | undefined;
  onSceneControlnetChange: (v: boolean | null) => void;
  sceneControlnetWeight: number | null | undefined;
  onSceneControlnetWeightChange: (v: number | null) => void;
  sceneIpAdapter: boolean | null | undefined;
  onSceneIpAdapterChange: (v: boolean | null) => void;
  sceneIpAdapterReference: string | null | undefined;
  onSceneIpAdapterReferenceChange: (v: string | null) => void;
  sceneIpAdapterWeight: number | null | undefined;
  onSceneIpAdapterWeightChange: (v: number | null) => void;
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
  useControlnet,
  controlnetWeight,
  onControlnetWeightChange,
  useIpAdapter,
  ipAdapterReference,
  onIpAdapterReferenceChange,
  ipAdapterWeight,
  onIpAdapterWeightChange,
  referenceImages,
  sceneMultiGen,
  onSceneMultiGenChange,
  sceneControlnet,
  onSceneControlnetChange,
  sceneControlnetWeight,
  onSceneControlnetWeightChange,
  sceneIpAdapter,
  onSceneIpAdapterChange,
  sceneIpAdapterReference,
  onSceneIpAdapterReferenceChange,
  sceneIpAdapterWeight,
  onSceneIpAdapterWeightChange,
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

  // Effective values (scene override ?? global)
  const effectiveMultiGen = sceneMultiGen ?? multiGenEnabled;
  const effectiveControlnet = sceneControlnet ?? useControlnet;
  const effectiveControlnetWeight = sceneControlnetWeight ?? controlnetWeight;
  const effectiveIpAdapter = sceneIpAdapter ?? useIpAdapter;
  const effectiveIpAdapterRef = sceneIpAdapterReference ?? ipAdapterReference;
  const effectiveIpAdapterWeight = sceneIpAdapterWeight ?? ipAdapterWeight;

  const hasMultiGenOverride = sceneMultiGen != null;
  const hasControlnetOverride = sceneControlnet != null;
  const hasIpAdapterOverride = sceneIpAdapter != null;

  return (
    <div className={SIDE_PANEL_CLASSES}>
      {/* Generation Settings */}
      <div>
        <label className={SIDE_PANEL_LABEL}>Settings</label>
        <div className="space-y-2">
          <OverrideToggleRow
            label="3x Candidates"
            checked={effectiveMultiGen}
            hasOverride={hasMultiGenOverride}
            onChange={(v) => onSceneMultiGenChange(v)}
            onReset={() => onSceneMultiGenChange(null)}

          />
          <OverrideToggleRow
            label="ControlNet"
            checked={effectiveControlnet}
            hasOverride={hasControlnetOverride}
            onChange={(v) => onSceneControlnetChange(v)}
            onReset={() => onSceneControlnetChange(null)}

            accent="violet"
            disabled={isNarrator}
            disabledReason="Narrator 씬에서는 사용 불가"
          />
          {effectiveControlnet && !isNarrator && (
            <SliderRow
              value={effectiveControlnetWeight}
              onChange={(v) => {
                if (hasControlnetOverride) {
                  onSceneControlnetWeightChange(v);
                } else {
                  onControlnetWeightChange(v);
                }
              }}
              min={0.3}
              max={1.0}
              step={0.1}
              accent="violet"
            />
          )}
          <OverrideToggleRow
            label={currentSpeaker === "B" ? "IP-Adapter (B)" : "IP-Adapter"}
            checked={effectiveIpAdapter}
            hasOverride={hasIpAdapterOverride}
            onChange={(v) => onSceneIpAdapterChange(v)}
            onReset={() => onSceneIpAdapterChange(null)}

            accent={currentSpeaker === "B" ? "sky" : "amber"}
            disabled={isNarrator}
            disabledReason="Narrator 씬에서는 사용 불가"
          />
          {effectiveIpAdapter && !isNarrator && (
            <>
              <select
                value={effectiveIpAdapterRef}
                onChange={(e) => {
                  const key = e.target.value;
                  if (hasIpAdapterOverride) {
                    onSceneIpAdapterReferenceChange(key || null);
                    const match = referenceImages.find((r) => r.character_key === key);
                    if (match?.preset?.weight) onSceneIpAdapterWeightChange(match.preset.weight);
                  } else {
                    onIpAdapterReferenceChange(key);
                    const match = referenceImages.find((r) => r.character_key === key);
                    if (match?.preset?.weight) onIpAdapterWeightChange(match.preset.weight);
                  }
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
                value={effectiveIpAdapterWeight}
                onChange={(v) => {
                  if (hasIpAdapterOverride) {
                    onSceneIpAdapterWeightChange(v);
                  } else {
                    onIpAdapterWeightChange(v);
                  }
                }}
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

/** Toggle row with override indicator and reset button */
function OverrideToggleRow({
  label,
  checked,
  hasOverride,
  onChange,
  onReset,
  accent = "zinc",
  disabled = false,
  disabledReason,
}: {
  label: string;
  checked: boolean;
  hasOverride: boolean;
  onChange: (v: boolean) => void;
  onReset: () => void;
  accent?: string;
  disabled?: boolean;
  disabledReason?: string;
}) {
  return (
    <div className="flex items-center justify-between text-[10px] font-medium">
      <span
        className={disabled ? "text-zinc-300" : "text-zinc-500"}
        title={disabled ? disabledReason : undefined}
      >
        {label}
        {hasOverride && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onReset();
            }}
            className="ml-1 inline-flex items-center rounded bg-blue-100 px-1 text-[8px] font-bold text-blue-600 hover:bg-blue-200"
            title="씬 오버라이드 활성. 클릭하면 글로벌 값으로 복원"
          >
            Scene
          </button>
        )}
      </span>
      <input
        type="checkbox"
        checked={disabled ? false : checked}
        onChange={(e) => {
          if (hasOverride) {
            onChange(e.target.checked);
          } else {
            // First toggle creates scene override
            onChange(e.target.checked);
          }
        }}
        disabled={disabled}
        className={`h-3.5 w-3.5 accent-${accent}-600 ${disabled ? "opacity-30" : ""}`}
      />
    </div>
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
