"use client";

import { useState } from "react";
import type {
  Scene,
  SceneValidation,
  ImageValidation,
  ImageGenProgress,
  FixSuggestion,
  Tag,
  GeminiSuggestion,
  Background,
} from "../../types";
import { isMultiCharStructure } from "../../utils/structure";
import { TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";
import SceneImagePanel from "./SceneImagePanel";
import Button from "../ui/Button";
import SceneActionBar from "./SceneActionBar";
import SceneScriptFields from "./SceneScriptFields";
import ScenePromptFields from "./ScenePromptFields";
import SceneSettingsFields from "./SceneSettingsFields";
import SceneGeminiModals from "./SceneGeminiModals";

export type SceneEditTab = "script" | "visual" | "settings";

const TAB_BASE = "px-3 py-1.5 text-xs font-semibold rounded-lg transition";

const TABS: { key: SceneEditTab; label: string }[] = [
  { key: "script", label: "대본" },
  { key: "visual", label: "비주얼" },
  { key: "settings", label: "설정" },
];

type SceneCardProps = {
  scene: Scene;
  sceneIndex: number;
  activeTab: SceneEditTab;
  onTabChange: (tab: SceneEditTab) => void;
  validationResult?: SceneValidation;
  imageValidationResult?: ImageValidation;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  sceneMenuOpen: boolean;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  suggestionExpanded: boolean;
  onSuggestionToggle: () => void;
  validatingSceneId: string | null;
  loraTriggerWords?: string[];
  characterLoras?: Array<{
    name: string;
    weight?: number;
    trigger_words?: string[];
    lora_type?: string;
    optimal_weight?: number;
  }>;
  promptMode?: "auto" | "standard" | "lora";
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isExclusiveGroup: (groupName: string) => boolean;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onRemoveScene: () => void;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
  onImageUpload: (file: File | undefined) => void;
  onGenerateImage: () => void;
  onEditWithGemini: (targetChange: string) => void;
  onSuggestEditWithGemini: () => Promise<GeminiSuggestion[]>;
  onValidateImage: () => void;
  onApplyMissingTags: (tags: string[]) => void;
  onImagePreview: (url: string | null, candidates?: string[]) => void;
  onPinToggle?: () => void;
  pinnedSceneOrder?: number;
  onSavePrompt?: () => void;
  onMarkSuccess?: () => void;
  onMarkFail?: () => void;
  isMarkingStatus?: boolean;
  selectedCharacterId?: number | null;
  basePromptA?: string;
  structure?: string;
  characterAName?: string | null;
  characterBName?: string | null;
  selectedCharacterBId?: number | null;
  backgrounds?: Background[];
  genProgress?: ImageGenProgress | null;
  getFixSuggestions: (scene: Scene, validation: SceneValidation) => FixSuggestion[];
  applySuggestion: (scene: Scene, suggestion: FixSuggestion) => void;
  buildNegativePrompt: (scene: Scene) => string;
  buildScenePrompt: (scene: Scene) => Promise<string | null>;
  showToast: (message: string, type: "success" | "error") => void;
};

export default function SceneCard({
  scene,
  sceneIndex,
  activeTab,
  onTabChange,
  validationResult,
  imageValidationResult,
  qualityScore,
  sceneMenuOpen,
  onSceneMenuToggle,
  onSceneMenuClose,
  suggestionExpanded,
  onSuggestionToggle,
  validatingSceneId,
  loraTriggerWords = [],
  characterLoras = [],
  promptMode = "auto",
  tagsByGroup,
  sceneTagGroups,
  isExclusiveGroup,
  onUpdateScene,
  onRemoveScene,
  onSpeakerChange,
  onImageUpload,
  onGenerateImage,
  onEditWithGemini,
  onSuggestEditWithGemini,
  onValidateImage,
  onApplyMissingTags,
  onImagePreview,
  onPinToggle,
  pinnedSceneOrder,
  onSavePrompt,
  onMarkSuccess,
  onMarkFail,
  isMarkingStatus = false,
  selectedCharacterId,
  basePromptA = "",
  structure,
  characterAName,
  characterBName,
  selectedCharacterBId,
  backgrounds = [],
  genProgress,
  getFixSuggestions,
  applySuggestion,
  buildNegativePrompt,
  buildScenePrompt,
  showToast,
}: SceneCardProps) {
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");
  const [geminiSuggestionsOpen, setGeminiSuggestionsOpen] = useState(false);
  const [geminiSuggestions, setGeminiSuggestions] = useState<GeminiSuggestion[]>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  const suggestions = validationResult ? getFixSuggestions(scene, validationResult) : [];
  const hasMultipleSpeakers = isMultiCharStructure(structure ?? "");

  const handleAutoSuggest = async () => {
    setIsLoadingSuggestions(true);
    try {
      const result = await onSuggestEditWithGemini();
      if (result && result.length > 0) {
        setGeminiSuggestions(result);
        setGeminiSuggestionsOpen(true);
      }
    } catch (error) {
      console.error("Auto-suggest failed:", error);
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  const handleApproveSuggestion = (suggestion: { target_change: string }) => {
    setGeminiSuggestionsOpen(false);
    onEditWithGemini(suggestion.target_change);
  };

  return (
    <div className="grid gap-4 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30">
      {/* Tab Bar */}
      <div className="flex gap-1">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onTabChange(tab.key)}
            className={`${TAB_BASE} ${activeTab === tab.key ? TAB_ACTIVE : TAB_INACTIVE}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── 대본 Tab ── */}
      {activeTab === "script" && (
        <div className="grid gap-3">
          <SceneScriptFields
            scene={scene}
            structure={structure}
            onUpdateScene={onUpdateScene}
            onSpeakerChange={onSpeakerChange}
            onImageUpload={onImageUpload}
            backgrounds={backgrounds}
          />
        </div>
      )}

      {/* ── 비주얼 Tab ── */}
      {activeTab === "visual" && (
        <div className="grid gap-3">
          <SceneImagePanel
            scene={scene}
            onImageClick={(url) =>
              onImagePreview(
                url,
                scene.candidates?.filter((c) => c.image_url).map((c) => c.image_url!)
              )
            }
            onCandidateSelect={(imageUrl) => onUpdateScene({ image_url: imageUrl })}
            onGenerateImage={onGenerateImage}
            validationResult={imageValidationResult}
            isValidating={validatingSceneId === scene.client_id}
            onValidate={onValidateImage}
            onApplyMissingTags={onApplyMissingTags}
            genProgress={genProgress}
          />

          {/* Mark Success / Fail */}
          {scene.activity_log_id && onMarkSuccess && onMarkFail && (
            <div className="flex gap-2">
              <Button
                variant="success"
                size="sm"
                onClick={onMarkSuccess}
                disabled={isMarkingStatus}
                className="flex-1"
              >
                👍 Success
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={onMarkFail}
                disabled={isMarkingStatus}
                className="flex-1"
              >
                👎 Fail
              </Button>
            </div>
          )}

          <ScenePromptFields
            scene={scene}
            loraTriggerWords={loraTriggerWords}
            characterLoras={characterLoras}
            promptMode={promptMode}
            selectedCharacterId={selectedCharacterId}
            basePromptA={basePromptA}
            onUpdateScene={onUpdateScene}
          />

          <SceneActionBar
            scene={scene}
            sceneIndex={sceneIndex}
            qualityScore={qualityScore}
            sceneMenuOpen={sceneMenuOpen}
            isLoadingSuggestions={isLoadingSuggestions}
            pinnedSceneOrder={pinnedSceneOrder}
            onGenerateImage={onGenerateImage}
            onGeminiEditOpen={() => setGeminiEditOpen(true)}
            onAutoSuggest={handleAutoSuggest}
            onPinToggle={onPinToggle}
            onSceneMenuToggle={onSceneMenuToggle}
            onSceneMenuClose={onSceneMenuClose}
            onUpdateScene={onUpdateScene}
            onRemoveScene={onRemoveScene}
            onSavePrompt={onSavePrompt}
            showToast={showToast}
          />
        </div>
      )}

      {/* ── 설정 Tab ── */}
      {activeTab === "settings" && (
        <SceneSettingsFields
          scene={scene}
          hasMultipleSpeakers={hasMultipleSpeakers}
          tagsByGroup={tagsByGroup}
          sceneTagGroups={sceneTagGroups}
          isExclusiveGroup={isExclusiveGroup}
          onUpdateScene={onUpdateScene}
          characterAName={characterAName}
          characterBName={characterBName}
          selectedCharacterId={selectedCharacterId}
          selectedCharacterBId={selectedCharacterBId}
          validationResult={validationResult}
          suggestions={suggestions}
          suggestionExpanded={suggestionExpanded}
          onSuggestionToggle={onSuggestionToggle}
          applySuggestion={applySuggestion}
          buildNegativePrompt={buildNegativePrompt}
          buildScenePrompt={buildScenePrompt}
          showToast={showToast}
        />
      )}

      {/* Gemini Modals */}
      <SceneGeminiModals
        scene={scene}
        qualityScore={qualityScore}
        geminiEditOpen={geminiEditOpen}
        setGeminiEditOpen={setGeminiEditOpen}
        geminiTargetChange={geminiTargetChange}
        setGeminiTargetChange={setGeminiTargetChange}
        onEditWithGemini={onEditWithGemini}
        showToast={showToast}
        geminiSuggestionsOpen={geminiSuggestionsOpen}
        setGeminiSuggestionsOpen={setGeminiSuggestionsOpen}
        geminiSuggestions={geminiSuggestions}
        setGeminiSuggestions={setGeminiSuggestions}
        onApproveSuggestion={handleApproveSuggestion}
      />
    </div>
  );
}
