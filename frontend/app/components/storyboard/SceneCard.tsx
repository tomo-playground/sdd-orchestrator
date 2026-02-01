"use client";

import { useState } from "react";
import type { Scene, SceneValidation, ImageValidation, FixSuggestion, Tag } from "../../types";
import ValidationTabContent from "../quality/ValidationTabContent";
import DebugTabContent from "../quality/DebugTabContent";
import SceneImagePanel from "../quality/SceneImagePanel";
import FixSuggestionsPanel from "./FixSuggestionsPanel";
import GenerationSettings from "./GenerationSettings";
import SceneActionBar from "./SceneActionBar";
import SceneFormFields from "./SceneFormFields";
import SceneGeminiModals from "./SceneGeminiModals";

type SceneCardProps = {
  scene: Scene;
  sceneIndex: number;  // 씬 순서 (0-based, 표시는 +1)
  validationResult?: SceneValidation;
  imageValidationResult?: ImageValidation;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  sceneTab: "validate" | "debug" | null;
  onSceneTabChange: (tab: "validate" | "debug" | null) => void;
  sceneMenuOpen: boolean;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  suggestionExpanded: boolean;
  onSuggestionToggle: () => void;
  validatingSceneId: number | null;
  autoComposePrompt: boolean;
  // LoRA trigger words for highlighting
  loraTriggerWords?: string[];
  // LoRA info for composition
  characterLoras?: Array<{
    name: string;
    weight?: number;
    trigger_words?: string[];
    lora_type?: string;
    optimal_weight?: number;
  }>;
  promptMode?: "auto" | "standard" | "lora";
  // Scene Context Tags
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isExclusiveGroup: (groupName: string) => boolean;
  // Scene update handlers
  onUpdateScene: (updates: Partial<Scene>) => void;
  onRemoveScene: () => void;
  onSpeakerChange: (speaker: Scene["speaker"]) => void;
  onImageUpload: (file: File | undefined) => void;
  onGenerateImage: () => void;
  onEditWithGemini: (targetChange: string) => void;
  onSuggestEditWithGemini: () => Promise<any[]>;
  onValidateImage: () => void;
  onApplyMissingTags: (tags: string[]) => void;
  onImagePreview: (url: string | null, candidates?: string[]) => void;
  onPinToggle?: () => void;
  onSavePrompt?: () => void;
  onMarkSuccess?: () => void;
  onMarkFail?: () => void;
  isMarkingStatus?: boolean;
  // V3 prompt integration
  selectedCharacterId?: number | null;
  basePromptA?: string;
  // Utility functions
  getSceneStatus: (scene: Scene) => string;
  getFixSuggestions: (scene: Scene, validation: SceneValidation) => FixSuggestion[];
  applySuggestion: (scene: Scene, suggestion: FixSuggestion) => void;
  buildNegativePrompt: (scene: Scene) => string;
  buildScenePrompt: (scene: Scene) => Promise<string | null>;
  showToast: (message: string, type: "success" | "error") => void;
};

export default function SceneCard({
  scene,
  sceneIndex,
  validationResult,
  imageValidationResult,
  qualityScore,
  sceneTab,
  onSceneTabChange,
  sceneMenuOpen,
  onSceneMenuToggle,
  onSceneMenuClose,
  suggestionExpanded,
  onSuggestionToggle,
  validatingSceneId,
  autoComposePrompt,
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
  onSavePrompt,
  onMarkSuccess,
  onMarkFail,
  isMarkingStatus = false,
  selectedCharacterId,
  basePromptA = "",
  getSceneStatus,
  getFixSuggestions,
  applySuggestion,
  buildNegativePrompt,
  buildScenePrompt,
  showToast,
}: SceneCardProps) {
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");
  const [geminiSuggestionsOpen, setGeminiSuggestionsOpen] = useState(false);
  const [geminiSuggestions, setGeminiSuggestions] = useState<any[]>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  const suggestions = validationResult ? getFixSuggestions(scene, validationResult) : [];

  // Quality badge helper
  const getQualityBadge = (rate: number) => {
    if (rate >= 0.8) return { emoji: "✅", label: "Excellent", color: "bg-emerald-100 text-emerald-700" };
    if (rate >= 0.7) return { emoji: "⚠️", label: "Good", color: "bg-amber-100 text-amber-700" };
    return { emoji: "🔴", label: "Poor", color: "bg-rose-100 text-rose-700" };
  };

  // Gemini auto-suggest handler
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

  // Handle suggestion approval
  const handleApproveSuggestion = (suggestion: any) => {
    setGeminiSuggestionsOpen(false);
    onEditWithGemini(suggestion.target_change);
  };

  return (
    <div className="grid gap-4 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-zinc-800">Scene {sceneIndex + 1}</h3>
        <div className="flex items-center gap-2">
          {qualityScore && (
            <span
              className={`rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.2em] uppercase ${getQualityBadge(qualityScore.match_rate).color
                }`}
              title={`Match Rate: ${(qualityScore.match_rate * 100).toFixed(0)}%${qualityScore.missing_tags.length > 0
                ? `\nMissing: ${qualityScore.missing_tags.slice(0, 3).join(", ")}`
                : ""
                }`}
            >
              {getQualityBadge(qualityScore.match_rate).emoji} {(qualityScore.match_rate * 100).toFixed(0)}%
            </span>
          )}
          {validationResult && (
            <button
              type="button"
              onClick={() => {
                if (validationResult.status === "ok") return;
                onSuggestionToggle();
              }}
              className={`rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.2em] uppercase ${validationResult.status === "ok"
                ? "bg-emerald-100 text-emerald-700"
                : validationResult.status === "warn"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-rose-100 text-rose-700"
                }`}
            >
              {validationResult.status}
            </button>
          )}
          <button
            onClick={() => {
              if (window.confirm(`Scene ${sceneIndex + 1}을(를) 삭제하시겠습니까?`)) {
                onRemoveScene();
              }
            }}
            className="text-[10px] font-semibold tracking-[0.2em] text-rose-500 uppercase hover:text-rose-600"
          >
            Remove
          </button>
        </div>
      </div>

      {/* Status */}
      <p className="text-[11px] font-semibold tracking-[0.2em] text-zinc-400 uppercase">
        {getSceneStatus(scene)}
      </p>

      {/* Validation Issues */}
      {validationResult && (
        <p className="text-[11px] text-zinc-500">
          {validationResult.issues.length > 0
            ? validationResult.issues[0].message
            : "No issues found."}
        </p>
      )}

      {/* Fix Suggestions Toggle */}
      {validationResult && validationResult.status !== "ok" && (
        <button
          type="button"
          onClick={onSuggestionToggle}
          className="w-fit rounded-full border border-zinc-300 bg-white/80 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
        >
          Fix Suggestions
        </button>
      )}

      {/* Fix Suggestions Panel */}
      {validationResult && suggestionExpanded && (
        <FixSuggestionsPanel
          scene={scene}
          suggestions={suggestions}
          applySuggestion={applySuggestion}
        />
      )}

      {/* Main Content Grid */}
      <div className="grid gap-4 md:grid-cols-[1.2fr_1fr]">
        {/* Left Column: Form Fields */}
        <div className="grid gap-3">
          <SceneFormFields
            scene={scene}
            loraTriggerWords={loraTriggerWords}
            characterLoras={characterLoras}
            promptMode={promptMode}
            selectedCharacterId={selectedCharacterId}
            basePromptA={basePromptA}
            tagsByGroup={tagsByGroup}
            sceneTagGroups={sceneTagGroups}
            isExclusiveGroup={isExclusiveGroup}
            onUpdateScene={onUpdateScene}
            onSpeakerChange={onSpeakerChange}
            onImageUpload={onImageUpload}
          />

          {/* Generation Settings */}
          <GenerationSettings
            scene={scene}
            autoComposePrompt={autoComposePrompt}
            onUpdateScene={onUpdateScene}
          />

          {/* Primary Action + More Menu */}
          <SceneActionBar
            scene={scene}
            sceneIndex={sceneIndex}
            qualityScore={qualityScore}
            sceneMenuOpen={sceneMenuOpen}
            isLoadingSuggestions={isLoadingSuggestions}
            isMarkingStatus={isMarkingStatus}
            onGenerateImage={onGenerateImage}
            onGeminiEditOpen={() => setGeminiEditOpen(true)}
            onAutoSuggest={handleAutoSuggest}
            onPinToggle={onPinToggle}
            onMarkSuccess={onMarkSuccess}
            onMarkFail={onMarkFail}
            onSceneMenuToggle={onSceneMenuToggle}
            onSceneMenuClose={onSceneMenuClose}
            onUpdateScene={onUpdateScene}
            onRemoveScene={onRemoveScene}
            onSavePrompt={onSavePrompt}
            showToast={showToast}
          />

          {/* Tab Navigation */}
          <div className="flex gap-1 rounded-xl border border-zinc-200 bg-zinc-100 p-1">
            {(["validate", "debug"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => onSceneTabChange(sceneTab === tab ? null : tab)}
                className={`flex-1 rounded-lg px-3 py-1.5 text-[10px] font-semibold uppercase transition ${sceneTab === tab
                  ? "bg-white text-zinc-900 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-700"
                  }`}
              >
                {tab === "validate" && (
                  <span className="flex items-center justify-center gap-1">
                    Validate
                    {imageValidationResult && (
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${imageValidationResult.match_rate >= 0.8
                          ? "bg-emerald-500"
                          : imageValidationResult.match_rate >= 0.5
                            ? "bg-amber-500"
                            : "bg-red-500"
                          }`}
                      />
                    )}
                  </span>
                )}
                {tab === "debug" && "Debug"}
              </button>
            ))}
          </div>

          {/* Tab Content: Validate */}
          {sceneTab === "validate" && (
            <ValidationTabContent
              scene={scene}
              validationResult={imageValidationResult}
              isValidating={validatingSceneId === scene.id}
              onValidate={onValidateImage}
              onApplyMissingTags={onApplyMissingTags}
            />
          )}

          {/* Tab Content: Debug */}
          {sceneTab === "debug" && (
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
                  steps: scene.steps,
                  cfg_scale: scene.cfg_scale,
                  sampler_name: scene.sampler_name,
                  seed: scene.seed,
                  clip_skip: scene.clip_skip,
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

        {/* Right Column: Image Panel */}
        <SceneImagePanel
          scene={scene}
          onImageClick={(url) => onImagePreview(url, scene.candidates?.map((c) => c.image_url))}
          onCandidateSelect={(imageUrl) => onUpdateScene({ image_url: imageUrl })}
        />
      </div>

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
