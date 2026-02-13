"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { Scene, SceneValidation, FixSuggestion, Tag } from "../../types";
import DebugTabContent from "./DebugTabContent";
import FixSuggestionsPanel from "./FixSuggestionsPanel";
import SceneContextTags from "../prompt/SceneContextTags";
import SceneCharacterActions from "./SceneCharacterActions";

type SceneSettingsFieldsProps = {
  scene: Scene;
  hasMultipleSpeakers: boolean;
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isExclusiveGroup: (groupName: string) => boolean;
  onUpdateScene: (updates: Partial<Scene>) => void;
  // Character
  characterAName?: string | null;
  characterBName?: string | null;
  selectedCharacterId?: number | null;
  selectedCharacterBId?: number | null;
  // Validation
  validationResult?: SceneValidation;
  suggestions: FixSuggestion[];
  suggestionExpanded: boolean;
  onSuggestionToggle: () => void;
  applySuggestion: (scene: Scene, suggestion: FixSuggestion) => void;
  // Debug
  buildNegativePrompt: (scene: Scene) => string;
  buildScenePrompt: (scene: Scene) => Promise<string | null>;
  showToast: (message: string, type: "success" | "error") => void;
};

export default function SceneSettingsFields({
  scene,
  hasMultipleSpeakers,
  tagsByGroup,
  sceneTagGroups,
  isExclusiveGroup,
  onUpdateScene,
  characterAName,
  characterBName,
  selectedCharacterId,
  selectedCharacterBId,
  validationResult,
  suggestions,
  suggestionExpanded,
  onSuggestionToggle,
  applySuggestion,
  buildNegativePrompt,
  buildScenePrompt,
  showToast,
}: SceneSettingsFieldsProps) {
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

      {/* Script Validation + Fix Suggestions */}
      {validationResult && validationResult.status !== "ok" && (
        <div className="rounded-xl border border-zinc-200 bg-white p-3">
          <div className="mb-2 flex items-center justify-between">
            <span
              className={`rounded-full px-2.5 py-0.5 text-[12px] font-semibold uppercase ${
                validationResult.status === "warn"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-rose-100 text-rose-700"
              }`}
            >
              {validationResult.status}
            </span>
            <button
              type="button"
              onClick={onSuggestionToggle}
              className="text-[12px] font-semibold text-zinc-500 hover:text-zinc-700"
            >
              {suggestionExpanded ? "Hide" : "Fix"}
            </button>
          </div>
          <p className="text-[13px] text-zinc-500">
            {validationResult.issues[0]?.message ?? ""}
          </p>
          {suggestionExpanded && (
            <div className="mt-2 border-t border-zinc-100 pt-2">
              <FixSuggestionsPanel
                scene={scene}
                suggestions={suggestions}
                applySuggestion={applySuggestion}
              />
            </div>
          )}
        </div>
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
            const prompt = await buildScenePrompt(scene);
            if (!prompt) {
              showToast("프롬프트 생성 실패", "error");
              return;
            }
            const payload = {
              prompt,
              negative_prompt: buildNegativePrompt(scene),
              width: 512,
              height: 768,
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
