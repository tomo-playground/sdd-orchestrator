"use client";

import { useShallow } from "zustand/react/shallow";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { resolveIpAdapterForSpeaker } from "../../utils/speakerResolver";
import { runValidation, handleAutoFixAll } from "../../store/actions/sceneActions";
import { OverrideToggleRow, SliderRow, StatBadge } from "../storyboard/SidePanelControls";
import { SIDE_PANEL_LABEL } from "../ui/variants";

export default function SceneToolsContent() {
  const {
    scenes,
    currentSceneIndex,
    multiGenEnabled,
    useControlnet,
    controlnetWeight,
    useIpAdapter,
    ipAdapterReference,
    ipAdapterWeight,
    ipAdapterReferenceB,
    ipAdapterWeightB,
    referenceImages,
    validationSummary,
  } = useStoryboardStore(
    useShallow((s) => ({
      scenes: s.scenes,
      currentSceneIndex: s.currentSceneIndex,
      multiGenEnabled: s.multiGenEnabled,
      useControlnet: s.useControlnet,
      controlnetWeight: s.controlnetWeight,
      useIpAdapter: s.useIpAdapter,
      ipAdapterReference: s.ipAdapterReference,
      ipAdapterWeight: s.ipAdapterWeight,
      ipAdapterReferenceB: s.ipAdapterReferenceB,
      ipAdapterWeightB: s.ipAdapterWeightB,
      referenceImages: s.referenceImages,
      validationSummary: s.validationSummary,
    }))
  );

  const sbSet = useStoryboardStore((s) => s.set);
  const updateScene = useStoryboardStore((s) => s.updateScene);

  const currentScene = scenes[currentSceneIndex];
  const currentSpeaker = currentScene?.speaker ?? "A";
  const isNarrator = currentSpeaker === "Narrator";

  const resolvedIpAdapter = resolveIpAdapterForSpeaker(currentSpeaker, {
    ipAdapterReference,
    ipAdapterWeight,
    ipAdapterReferenceB,
    ipAdapterWeightB,
  });

  // Scene-level overrides (null = inherit global)
  const sceneMultiGen = currentScene?.multi_gen_enabled;
  const sceneControlnet = currentScene?.use_controlnet;
  const sceneControlnetWeight = currentScene?.controlnet_weight;
  const sceneIpAdapter = currentScene?.use_ip_adapter;
  const sceneIpAdapterRef = currentScene?.ip_adapter_reference;
  const sceneIpAdapterWeight = currentScene?.ip_adapter_weight;

  const effectiveMultiGen = sceneMultiGen ?? multiGenEnabled;
  const effectiveControlnet = sceneControlnet ?? useControlnet;
  const effectiveControlnetWeight = sceneControlnetWeight ?? controlnetWeight;
  const effectiveIpAdapter = sceneIpAdapter ?? useIpAdapter;
  const effectiveIpAdapterRef = sceneIpAdapterRef ?? resolvedIpAdapter.reference;
  const effectiveIpAdapterWeight = sceneIpAdapterWeight ?? resolvedIpAdapter.weight;

  const hasMultiGenOverride = sceneMultiGen != null;
  const hasControlnetOverride = sceneControlnet != null;
  const hasIpAdapterOverride = sceneIpAdapter != null;

  const setSceneField = (field: string, value: unknown) => {
    if (currentScene) updateScene(currentScene.client_id, { [field]: value });
  };

  const totalValidation = validationSummary.ok + validationSummary.warn + validationSummary.error;

  return (
    <div className="space-y-4">
      {/* Validate / Fix All */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={runValidation}
          className="flex-1 rounded-lg bg-zinc-900 px-3 py-2 text-xs font-semibold text-white shadow transition hover:bg-zinc-800"
        >
          Validate
        </button>
        <button
          type="button"
          onClick={handleAutoFixAll}
          disabled={scenes.length === 0}
          className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-xs font-semibold text-zinc-600 shadow-sm transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Fix All
        </button>
      </div>

      {/* Generation Settings */}
      <div className="pb-3">
        <label className={SIDE_PANEL_LABEL}>Settings</label>
        <div className="space-y-2">
          <OverrideToggleRow
            label="3x Candidates"
            checked={effectiveMultiGen}
            hasOverride={hasMultiGenOverride}
            onChange={(v) => setSceneField("multi_gen_enabled", v)}
            onReset={() => setSceneField("multi_gen_enabled", null)}
          />
          <OverrideToggleRow
            label="ControlNet"
            checked={effectiveControlnet}
            hasOverride={hasControlnetOverride}
            onChange={(v) => setSceneField("use_controlnet", v)}
            onReset={() => setSceneField("use_controlnet", null)}
            accent="violet"
            disabled={isNarrator}
            disabledReason="Narrator 씬에서는 사용 불가"
          />
          {effectiveControlnet && !isNarrator && (
            <SliderRow
              value={effectiveControlnetWeight}
              onChange={(v) => {
                if (hasControlnetOverride) {
                  setSceneField("controlnet_weight", v);
                } else {
                  sbSet({ controlnetWeight: v });
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
            onChange={(v) => setSceneField("use_ip_adapter", v)}
            onReset={() => setSceneField("use_ip_adapter", null)}
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
                    setSceneField("ip_adapter_reference", key || null);
                    const match = referenceImages.find((r) => r.character_key === key);
                    if (match?.preset?.weight)
                      setSceneField("ip_adapter_weight", match.preset.weight);
                  } else {
                    sbSet(
                      currentSpeaker === "B"
                        ? { ipAdapterReferenceB: key }
                        : { ipAdapterReference: key }
                    );
                    const match = referenceImages.find((r) => r.character_key === key);
                    if (match?.preset?.weight) {
                      sbSet(
                        currentSpeaker === "B"
                          ? { ipAdapterWeightB: match.preset.weight }
                          : { ipAdapterWeight: match.preset.weight }
                      );
                    }
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
                    setSceneField("ip_adapter_weight", v);
                  } else {
                    sbSet(
                      currentSpeaker === "B" ? { ipAdapterWeightB: v } : { ipAdapterWeight: v }
                    );
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
