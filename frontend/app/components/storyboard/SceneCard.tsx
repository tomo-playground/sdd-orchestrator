"use client";

import { useState } from "react";
import type { Scene, ImageValidation, ImageGenProgress, Tag, GeminiSuggestion } from "../../types";
import { isMultiCharStructure } from "../../utils/structure";
import { useUIStore } from "../../store/useUIStore";
import SceneImagePanel from "./SceneImagePanel";
import Button from "../ui/Button";
import SceneActionBar from "./SceneActionBar";
import ScenePromptFields from "./ScenePromptFields";
import SceneSettingsFields from "./SceneSettingsFields";
import SceneGeminiModals from "./SceneGeminiModals";
import SceneEditImageModal from "./SceneEditImageModal";
import SceneClothingModal from "./SceneClothingModal";
import CollapsibleSection from "../ui/CollapsibleSection";
import SceneEssentialFields from "./SceneEssentialFields";
import SceneToolsContent from "../studio/SceneToolsContent";

export type SceneEditTab = "script" | "visual" | "settings"; // Keep for compatibility if needed, but unused in logic

type SceneCardProps = {
  scene: Scene;
  sceneIndex: number;
  imageValidationResult?: ImageValidation;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  sceneMenuOpen: boolean;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  validatingSceneId: string | null;
  loraTriggerWords?: string[];
  characterLoras?: Array<{
    name: string;
    weight?: number;
    trigger_words?: string[];
    lora_type?: string;
    optimal_weight?: number;
  }>;
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
  genProgress?: ImageGenProgress | null;
  buildNegativePrompt: (scene: Scene) => string;
  buildScenePrompt: (scene: Scene) => string | null;
  showToast: (message: string, type: "success" | "error") => void;
};

export default function SceneCard({
  scene,
  sceneIndex,
  imageValidationResult,
  qualityScore,
  sceneMenuOpen,
  onSceneMenuToggle,
  onSceneMenuClose,
  validatingSceneId,
  loraTriggerWords = [],
  characterLoras = [],
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

  genProgress,
  buildNegativePrompt,
  buildScenePrompt,
  showToast,
}: SceneCardProps) {
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");
  const [geminiSuggestionsOpen, setGeminiSuggestionsOpen] = useState(false);
  const [geminiSuggestions, setGeminiSuggestions] = useState<GeminiSuggestion[]>([]);
  const [editImageOpen, setEditImageOpen] = useState(false);
  const [clothingOpen, setClothingOpen] = useState(false);

  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const showAdvancedSettings = useUIStore((s) => s.showAdvancedSettings);

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
    <div className="group relative grid gap-2 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30 transition hover:border-zinc-300">
      {/* ── Tier 1: Essential (Image + Script + Basic Info) ── */}
      <div className="relative z-20 grid gap-6 md:grid-cols-[240px_1fr] lg:grid-cols-[280px_1fr]">
        {/* Left: Visuals */}
        <div className="relative z-30 flex flex-col gap-3">
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
          {/* Action Bar (Buttons) moved here for easy access */}
          <SceneActionBar
            scene={scene}
            sceneIndex={sceneIndex}
            qualityScore={qualityScore}
            sceneMenuOpen={sceneMenuOpen}
            isLoadingSuggestions={isLoadingSuggestions}
            pinnedSceneOrder={pinnedSceneOrder}
            onGenerateImage={onGenerateImage}
            onGeminiEditOpen={() => setGeminiEditOpen(true)}
            onEditImageOpen={() => setEditImageOpen(true)}
            onClothingOpen={() => setClothingOpen(true)}
            onAutoSuggest={handleAutoSuggest}
            onPinToggle={onPinToggle}
            onSceneMenuToggle={onSceneMenuToggle}
            onSceneMenuClose={onSceneMenuClose}
            onUpdateScene={onUpdateScene}
            onRemoveScene={onRemoveScene}
            onSavePrompt={onSavePrompt}
            showToast={showToast}
            compact={true}
          />
        </div>

        {/* Right: Script & Details */}
        <div className="relative z-20 flex flex-col gap-4">
          <SceneEssentialFields
            scene={scene}
            structure={structure}
            onUpdateScene={onUpdateScene}
            onSpeakerChange={onSpeakerChange}
            onImageUpload={onImageUpload}
          />
        </div>
      </div>

      {/* ── Tier 2: Customize (Collapsible, Default Open) ── */}
      <div className="relative z-10">
        <CollapsibleSection title="Customize" defaultOpen className="mt-2">
          <div className="grid gap-4">
            {/* Prompt + Background */}
            <ScenePromptFields
              scene={scene}
              loraTriggerWords={loraTriggerWords}
              characterLoras={characterLoras}
              selectedCharacterId={selectedCharacterId}
              basePromptA={basePromptA}
              onUpdateScene={onUpdateScene}
              showAdvancedSettings={showAdvancedSettings}
            />
          </div>
        </CollapsibleSection>
      </div>

      {/* ── Tier 3: Scene Tags (Advanced only) ── */}
      {showAdvancedSettings && (
        <div className="relative z-0">
          <CollapsibleSection title="Scene Tags" defaultOpen={showAdvancedSettings}>
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
              buildNegativePrompt={buildNegativePrompt}
              buildScenePrompt={buildScenePrompt}
              showToast={showToast}
            />
          </CollapsibleSection>
        </div>
      )}

      {/* ── Tier 4: Advanced (Advanced only) ── */}
      {showAdvancedSettings && (
        <div className="relative z-0">
          <CollapsibleSection title="Advanced" defaultOpen={false}>
            <SceneToolsContent />
            {/* Success/Fail Buttons for Review Mode */}
            {scene.activity_log_id && onMarkSuccess && onMarkFail && (
              <div className="mt-4 flex gap-2 border-t border-zinc-100 pt-4">
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
          </CollapsibleSection>
        </div>
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
        onApplyPromptEdit={(edited) => onUpdateScene({ image_prompt: edited })}
        showToast={showToast}
        selectedCharacterId={selectedCharacterId}
        geminiSuggestionsOpen={geminiSuggestionsOpen}
        setGeminiSuggestionsOpen={setGeminiSuggestionsOpen}
        geminiSuggestions={geminiSuggestions}
        setGeminiSuggestions={setGeminiSuggestions}
        onApproveSuggestion={handleApproveSuggestion}
      />

      {/* Edit Image Modal */}
      {editImageOpen && scene.image_url && (
        <SceneEditImageModal
          sceneId={scene.id}
          currentImageUrl={scene.image_url}
          onClose={() => setEditImageOpen(false)}
          onAccept={(imageUrl, assetId) => {
            onUpdateScene({ image_url: imageUrl, image_asset_id: assetId });
            showToast("편집된 이미지가 적용되었습니다", "success");
          }}
          showToast={showToast}
        />
      )}

      {/* Clothing Override Modal */}
      {clothingOpen && (
        <SceneClothingModal
          scene={scene}
          onClose={() => setClothingOpen(false)}
          onSave={(clothingTags) => {
            onUpdateScene({ clothing_tags: clothingTags });
            showToast("의상 태그가 저장되었습니다. 이미지를 재생성하면 반영됩니다.", "success");
          }}
          showToast={showToast}
        />
      )}
    </div>
  );
}
