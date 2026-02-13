"use client";

import { OverrideToggleRow, SliderRow, StatBadge } from "../storyboard/SidePanelControls";
import { SIDE_PANEL_LABEL } from "../ui/variants";

type ReferenceImage = {
  character_key: string;
  filename: string;
  preset?: { weight: number; model: string; description?: string };
};

type ValidationSummary = {
  ok: number;
  warn: number;
  error: number;
};

type SceneToolsContentProps = {
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
  currentSpeaker?: "Narrator" | "A" | "B";
  validationSummary: ValidationSummary;
  onValidate?: () => void;
  onAutoFixAll?: () => void;
  scenesCount?: number;
};

export default function SceneToolsContent({
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
  onValidate,
  onAutoFixAll,
  scenesCount = 0,
}: SceneToolsContentProps) {
  const isNarrator = currentSpeaker === "Narrator";
  const totalValidation = validationSummary.ok + validationSummary.warn + validationSummary.error;

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
    <div className="space-y-4">
      {/* Validate / Fix All */}
      {onValidate && onAutoFixAll && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onValidate}
            className="flex-1 rounded-lg bg-zinc-900 px-3 py-2 text-xs font-semibold text-white shadow transition hover:bg-zinc-800"
          >
            Validate
          </button>
          <button
            type="button"
            onClick={onAutoFixAll}
            disabled={scenesCount === 0}
            className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-xs font-semibold text-zinc-600 shadow-sm transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Fix All
          </button>
        </div>
      )}

      {/* Generation Settings */}
      <div className="pb-3">
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
                className={`w-full rounded-lg border bg-white px-2 py-1.5 text-[12px] text-zinc-600 ${
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
        <div className="border-t border-zinc-100 pt-3">
          <label className={SIDE_PANEL_LABEL}>Validation</label>
          <div className="grid grid-cols-3 gap-1.5">
            <StatBadge label="OK" count={validationSummary.ok} color="emerald" />
            <StatBadge label="Warn" count={validationSummary.warn} color="amber" />
            <StatBadge label="Error" count={validationSummary.error} color="rose" />
          </div>
        </div>
      )}
    </div>
  );
}
