"use client";

import { useState } from "react";
import type { Scene, ImageValidation, ImageGenProgress, Tag, TTSPreviewState } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";
import { isMultiCharStructure } from "../../utils/structure";
import { useUIStore } from "../../store/useUIStore";
import SceneImagePanel from "./SceneImagePanel";
import Button from "../ui/Button";
import SceneActionBar from "./SceneActionBar";
import ScenePromptFields from "./ScenePromptFields";
import SceneSettingsFields from "./SceneSettingsFields";
import SceneGeminiModals from "./SceneGeminiModals";
import SceneClothingModal from "./SceneClothingModal";
import CollapsibleSection from "../ui/CollapsibleSection";
import SceneEssentialFields from "./SceneEssentialFields";
import SceneToolsContent from "../studio/SceneToolsContent";
import SceneEnvironmentPicker from "./SceneEnvironmentPicker";

export type SceneEditTab = "script" | "visual" | "settings"; // Keep for compatibility if needed, but unused in logic

type SceneCardProps = {
  scene: Scene;
  sceneIndex: number;
  imageValidationResult?: ImageValidation;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  sceneMenuOpen: boolean;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  loraTriggerWords?: string[];
  characterLoras?: Array<{
    name: string;
    weight?: number;
    trigger_words?: string[];
    lora_type?: string;
  }>;
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isExclusiveGroup: (groupName: string) => boolean;
  onUpdateScene: (updates: Partial<Scene>) => void;
  onRemoveScene: () => void;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
  onImageUpload: (file: File | undefined) => void;
  onGenerateImage: () => void;
  onApplyMissingTags: (tags: string[]) => void;
  onImagePreview: (url: string | null, candidates?: string[]) => void;
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
  ttsState?: TTSPreviewState;
  onTTSPreview?: () => void;
  onTTSRegenerate?: () => void;
  audioPlayer?: AudioPlayer;
};

export default function SceneCard({
  scene,
  sceneIndex,
  imageValidationResult,
  qualityScore,
  sceneMenuOpen,
  onSceneMenuToggle,
  onSceneMenuClose,
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
  onApplyMissingTags,
  onImagePreview,
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
  ttsState,
  onTTSPreview,
  onTTSRegenerate,
  audioPlayer,
}: SceneCardProps) {
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");
  const [clothingOpen, setClothingOpen] = useState(false);

  const showAdvancedSettings = useUIStore((s) => s.showAdvancedSettings);

  const hasMultipleSpeakers = isMultiCharStructure(structure ?? "");

  return (
    <div className="group relative grid gap-2 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30 transition hover:border-zinc-300">
      {/* Multi-character badge */}
      {scene.scene_mode === "multi" && (
        <span className="absolute top-4 right-4 z-30 rounded bg-indigo-100 px-1.5 py-0.5 text-[11px] font-semibold text-indigo-700">
          2P
        </span>
      )}

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
            onApplyMissingTags={onApplyMissingTags}
            genProgress={genProgress}
          />
          {/* Action Bar (Buttons) moved here for easy access */}
          <SceneActionBar
            scene={scene}
            sceneIndex={sceneIndex}
            qualityScore={qualityScore}
            sceneMenuOpen={sceneMenuOpen}
            onGenerateImage={onGenerateImage}
            onGeminiEditOpen={() => setGeminiEditOpen(true)}
            onClothingOpen={() => setClothingOpen(true)}
            onSceneMenuToggle={onSceneMenuToggle}
            onSceneMenuClose={onSceneMenuClose}
            onUpdateScene={onUpdateScene}
            onRemoveScene={onRemoveScene}
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
            ttsState={ttsState}
            onTTSPreview={onTTSPreview}
            onTTSRegenerate={onTTSRegenerate}
            audioPlayer={audioPlayer}
          />
        </div>
      </div>

      {/* ── Tier 2: Customize (Collapsible, Default Closed) ── */}
      <div className="relative z-10">
        <CollapsibleSection
          title="Customize"
          hint="프롬프트 상세"
          defaultOpen={false}
          className="mt-2"
        >
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
            {/* Environment Picker (environment, time, weather, particle) */}
            <SceneEnvironmentPicker
              contextTags={scene.context_tags}
              tagsByGroup={tagsByGroup}
              onUpdate={(tags) => onUpdateScene({ context_tags: tags })}
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
        onApplyPromptEdit={(edited) => onUpdateScene({ image_prompt: edited })}
        showToast={showToast}
        selectedCharacterId={selectedCharacterId}
      />

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
