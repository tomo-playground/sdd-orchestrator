"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { Scene } from "../../types";
import { isMultiCharStructure } from "../../utils/structure";
import DebugTabContent from "./DebugTabContent";
import SceneContextTags from "../prompt/SceneContextTags";
import SceneCharacterActions from "./SceneCharacterActions";
import { ENV_GROUPS } from "./SceneEnvironmentPicker";
import { useSceneContext } from "./SceneContext";

type SceneSettingsFieldsProps = {
  scene: Scene;
};

export default function SceneSettingsFields({ scene }: SceneSettingsFieldsProps) {
  const { data, callbacks } = useSceneContext();
  const {
    structure,
    tagsByGroup,
    sceneTagGroups,
    isExclusiveGroup,
    characterAName,
    characterBName,
    selectedCharacterId,
    selectedCharacterBId,
  } = data;
  const { onUpdateScene, buildNegativePrompt, buildScenePrompt, showToast } = callbacks;

  const hasMultipleSpeakers = isMultiCharStructure(structure ?? "");
  const [showSettings, setShowSettings] = useState(false);

  return (
    <div className="grid gap-3">
      {/* Scene Context Tags */}
      <SceneContextTags
        contextTags={scene.context_tags}
        tagsByGroup={tagsByGroup}
        sceneTagGroups={sceneTagGroups}
        isExclusiveGroup={isExclusiveGroup}
        onUpdate={(tags) => onUpdateScene({ context_tags: tags })}
        excludeGroups={[...ENV_GROUPS]}
      />

      {/* Scene Character Actions (Dialogue only) */}
      {hasMultipleSpeakers && (
        <SceneCharacterActions
          characterActions={scene.character_actions || []}
          characterAName={characterAName}
          characterBName={characterBName}
          characterAId={selectedCharacterId}
          characterBId={selectedCharacterBId}
          onUpdate={(actions) => onUpdateScene({ character_actions: actions })}
        />
      )}

      {/* Details Toggle */}
      <button
        type="button"
        onClick={() => setShowSettings((v) => !v)}
        className="flex items-center gap-1 text-[12px] font-semibold tracking-[0.2em] text-zinc-400 uppercase transition hover:text-zinc-600"
      >
        <ChevronDown
          className={`h-3 w-3 transition-transform ${showSettings ? "rotate-180" : ""}`}
        />
        Details
      </button>

      {showSettings && (
        <DebugTabContent
          scene={scene}
          onGenerateDebug={async () => {
            const prompt = buildScenePrompt(scene);
            if (!prompt) {
              showToast("프롬프트 생성 실패", "error");
              return;
            }
            const payload = {
              prompt,
              negative_prompt: buildNegativePrompt(scene),
              width: 832,
              height: 1216,
            };
            onUpdateScene({
              debug_payload: JSON.stringify(payload, null, 2),
              debug_prompt: payload.prompt,
            });
          }}
        />
      )}
    </div>
  );
}
