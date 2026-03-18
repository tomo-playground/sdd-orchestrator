"use client";

import { useState } from "react";
import type { Scene, ImageValidation, ImageGenProgress, TTSPreviewState } from "../../types";
import type { AudioPlayer } from "../../hooks/useAudioPlayer";
import { isMultiCharStructure } from "../../utils/structure";
import { useUIStore } from "../../store/useUIStore";
import { SceneProvider, type SceneContextValue } from "./SceneContext";
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
import SceneEnvironmentPicker from "./SceneEnvironmentPicker";
import type { GeminiSuggestion, Tag } from "../../types";

export type SceneEditTab = "script" | "visual" | "settings";

/** Instance-specific props (vary per-card) */
type SceneCardProps = {
  scene: Scene;
  sceneIndex: number;
  sceneMenuOpen: boolean;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  /** Context-level data injected by ScenesTab */
  contextData: Omit<SceneContextValue["data"], never>;
  contextCallbacks: Omit<SceneContextValue["callbacks"], "onSceneMenuToggle" | "onSceneMenuClose">;
  imageValidationResult?: ImageValidation;
  genProgress?: ImageGenProgress | null;
  ttsState?: TTSPreviewState;
  onTTSPreview?: () => void;
  onTTSRegenerate?: () => void;
  audioPlayer?: AudioPlayer;
};

export default function SceneCard({
  scene,
  sceneIndex,
  sceneMenuOpen,
  onSceneMenuToggle,
  onSceneMenuClose,
  contextData,
  contextCallbacks,
  imageValidationResult,
  genProgress,
  ttsState,
  onTTSPreview,
  onTTSRegenerate,
  audioPlayer,
}: SceneCardProps) {
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");
  const [geminiSuggestionsOpen, setGeminiSuggestionsOpen] = useState(false);
  const [geminiSuggestions, setGeminiSuggestions] = useState<GeminiSuggestion[]>([]);
  const [editImageOpen, setEditImageOpen] = useState(false);
  const [clothingOpen, setClothingOpen] = useState(false);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  const showAdvancedSettings = useUIStore((s) => s.showAdvancedSettings);

  const hasMultipleSpeakers = isMultiCharStructure(contextData.structure ?? "");

  const { showToast, onSuggestEditWithGemini, onEditWithGemini, onUpdateScene } =
    contextCallbacks;

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
      showToast("추천 생성 중 오류가 발생했습니다", "error");
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  const handleApproveSuggestion = (suggestion: { target_change: string }) => {
    setGeminiSuggestionsOpen(false);
    onEditWithGemini(suggestion.target_change);
  };

  // Build full context value (inject instance-specific callbacks)
  const contextValue: SceneContextValue = {
    data: {
      ...contextData,
      imageValidationResult,
      genProgress,
      validatingSceneId: contextData.validatingSceneId,
    },
    callbacks: {
      ...contextCallbacks,
      onSceneMenuToggle,
      onSceneMenuClose,
    },
  };

  return (
    <SceneProvider value={contextValue}>
      <div className="group relative grid gap-2 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30 transition hover:border-zinc-300">
        {/* Multi-character badge */}
        {scene.scene_mode === "multi" && (
          <span className="absolute right-4 top-4 z-30 rounded bg-indigo-100 px-1.5 py-0.5 text-[11px] font-semibold text-indigo-700">
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
                contextCallbacks.onImagePreview(
                  url,
                  scene.candidates?.filter((c) => c.image_url).map((c) => c.image_url!)
                )
              }
              onCandidateSelect={(imageUrl) => onUpdateScene({ image_url: imageUrl })}
              onGenerateImage={contextCallbacks.onGenerateImage}
              validationResult={imageValidationResult}
              isValidating={contextData.validatingSceneId === scene.client_id}
              onValidate={contextCallbacks.onValidateImage}
              onApplyMissingTags={contextCallbacks.onApplyMissingTags}
              genProgress={genProgress}
            />
            <SceneActionBar
              scene={scene}
              sceneIndex={sceneIndex}
              sceneMenuOpen={sceneMenuOpen}
              isLoadingSuggestions={isLoadingSuggestions}
              onGeminiEditOpen={() => setGeminiEditOpen(true)}
              onEditImageOpen={() => setEditImageOpen(true)}
              onClothingOpen={() => setClothingOpen(true)}
              onAutoSuggest={handleAutoSuggest}
              compact={true}
            />
          </div>

          {/* Right: Script & Details */}
          <div className="relative z-20 flex flex-col gap-4">
            <SceneEssentialFields
              scene={scene}
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
              <ScenePromptFields scene={scene} />
              <SceneEnvironmentPicker
                contextTags={scene.context_tags}
                tagsByGroup={contextData.tagsByGroup}
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
              />
            </CollapsibleSection>
          </div>
        )}

        {/* ── Tier 4: Advanced (Advanced only) ── */}
        {showAdvancedSettings && (
          <div className="relative z-0">
            <CollapsibleSection title="Advanced" defaultOpen={false}>
              <SceneToolsContent />
              {scene.activity_log_id &&
                contextCallbacks.onMarkSuccess &&
                contextCallbacks.onMarkFail && (
                  <div className="mt-4 flex gap-2 border-t border-zinc-100 pt-4">
                    <Button
                      variant="success"
                      size="sm"
                      onClick={contextCallbacks.onMarkSuccess}
                      disabled={contextData.isMarkingStatus}
                      className="flex-1"
                    >
                      👍 Success
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={contextCallbacks.onMarkFail}
                      disabled={contextData.isMarkingStatus}
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
          geminiEditOpen={geminiEditOpen}
          setGeminiEditOpen={setGeminiEditOpen}
          geminiTargetChange={geminiTargetChange}
          setGeminiTargetChange={setGeminiTargetChange}
          geminiSuggestionsOpen={geminiSuggestionsOpen}
          setGeminiSuggestionsOpen={setGeminiSuggestionsOpen}
          geminiSuggestions={geminiSuggestions}
          setGeminiSuggestions={setGeminiSuggestions}
          onApproveSuggestion={handleApproveSuggestion}
        />

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
    </SceneProvider>
  );
}
