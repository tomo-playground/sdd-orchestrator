"use client";

import { useState } from "react";
import { useSceneContext } from "./SceneContext";
import { useUIStore } from "../../store/useUIStore";
import { isMultiCharStructure } from "../../utils/structure";
import ScenePromptFields from "./ScenePromptFields";
import SceneEnvironmentPicker from "./SceneEnvironmentPicker";
import SceneSettingsFields from "./SceneSettingsFields";
import SceneToolsContent from "../studio/SceneToolsContent";
import Button from "../ui/Button";

export default function ScenePropertyPanel() {
  const { data, callbacks } = useSceneContext();
  const showAdvancedSettings = useUIStore((s) => s.showAdvancedSettings);
  const [activeTab, setActiveTab] = useState<"basic" | "advanced">("basic");

  const hasMultipleSpeakers = isMultiCharStructure(data.structure ?? "");
  // When showAdvancedSettings is disabled, force-show basic tab.
  // When re-enabled, intentionally restore the user's previous tab selection.
  const effectiveTab =
    !showAdvancedSettings && activeTab === "advanced" ? "basic" : activeTab;

  return (
    <div className="mt-2 grid gap-3">
      {/* Tab buttons */}
      <div className="flex gap-1.5">
        <button
          type="button"
          onClick={() => setActiveTab("basic")}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            effectiveTab === "basic"
              ? "bg-zinc-800 text-white"
              : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200"
          }`}
        >
          Customize
        </button>
        {showAdvancedSettings && (
          <button
            type="button"
            onClick={() => setActiveTab("advanced")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              effectiveTab === "advanced"
                ? "bg-zinc-800 text-white"
                : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200"
            }`}
          >
            Advanced
          </button>
        )}
      </div>

      {/* Basic tab */}
      {effectiveTab === "basic" && (
        <div className="grid gap-4">
          <ScenePromptFields
            scene={data.scene}
            loraTriggerWords={data.loraTriggerWords}
            characterLoras={data.characterLoras}
            selectedCharacterId={data.selectedCharacterId}
            basePromptA={data.basePromptA}
            onUpdateScene={callbacks.onUpdateScene}
            showAdvancedSettings={showAdvancedSettings}
          />
          <SceneEnvironmentPicker
            contextTags={data.scene.context_tags}
            tagsByGroup={data.tagsByGroup}
            onUpdate={(tags) => callbacks.onUpdateScene({ context_tags: tags })}
          />
          {/* Speaker Badge (read-only summary) */}
          {data.scene.speaker && (
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-medium text-zinc-400">
                Speaker
              </span>
              <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-600">
                {data.scene.speaker}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Advanced tab */}
      {effectiveTab === "advanced" && (
        <div className="grid gap-4">
          <SceneSettingsFields
            scene={data.scene}
            hasMultipleSpeakers={hasMultipleSpeakers}
            tagsByGroup={data.tagsByGroup}
            sceneTagGroups={data.sceneTagGroups}
            isExclusiveGroup={data.isExclusiveGroup}
            onUpdateScene={callbacks.onUpdateScene}
            characterAName={data.characterAName}
            characterBName={data.characterBName}
            selectedCharacterId={data.selectedCharacterId}
            selectedCharacterBId={data.selectedCharacterBId}
            buildNegativePrompt={callbacks.buildNegativePrompt}
            buildScenePrompt={callbacks.buildScenePrompt}
            showToast={callbacks.showToast}
          />
          <SceneToolsContent />
          {data.scene.activity_log_id &&
            callbacks.onMarkSuccess &&
            callbacks.onMarkFail && (
              <div className="flex gap-2 border-t border-zinc-100 pt-4">
                <Button
                  variant="success"
                  size="sm"
                  onClick={callbacks.onMarkSuccess}
                  disabled={data.isMarkingStatus}
                  className="flex-1"
                >
                  Success
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={callbacks.onMarkFail}
                  disabled={data.isMarkingStatus}
                  className="flex-1"
                >
                  Fail
                </Button>
              </div>
            )}
        </div>
      )}
    </div>
  );
}
