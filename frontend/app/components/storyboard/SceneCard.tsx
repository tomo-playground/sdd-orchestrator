"use client";

import { useState } from "react";
import type { Scene, ImageValidation, ImageGenProgress, Tag, TTSPreviewState } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";
import type { SceneContextValue } from "./SceneContext";
import { SceneProvider } from "./SceneContext";
import SceneImagePanel from "./SceneImagePanel";
import SceneActionBar from "./SceneActionBar";
import SceneGeminiModals from "./SceneGeminiModals";
import SceneClothingModal from "./SceneClothingModal";
import SceneEssentialFields from "./SceneEssentialFields";
import ScenePropertyPanel from "./ScenePropertyPanel";

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

  const ctxValue: SceneContextValue = {
    data: {
      scene,
      imageValidationResult,
      qualityScore,
      loraTriggerWords,
      characterLoras,
      tagsByGroup,
      sceneTagGroups,
      isExclusiveGroup,
      selectedCharacterId,
      basePromptA,
      structure,
      characterAName,
      characterBName,
      selectedCharacterBId,
      genProgress,
      isMarkingStatus,
    },
    callbacks: {
      onUpdateScene,
      onRemoveScene,
      onSpeakerChange,
      onImageUpload,
      onGenerateImage,
      onApplyMissingTags,
      onImagePreview,
      onMarkSuccess,
      onMarkFail,
      buildNegativePrompt,
      buildScenePrompt,
      showToast,
      onSceneMenuToggle,
      onSceneMenuClose,
    },
  };

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

      {/* ── Tier 2~4: Property Panel (Customize + Advanced) ── */}
      <SceneProvider value={ctxValue}>
        <ScenePropertyPanel />
      </SceneProvider>

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
