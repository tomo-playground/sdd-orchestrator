"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type {
  Scene,
  SceneValidation,
  ImageValidation,
  FixSuggestion,
  Tag,
  GeminiSuggestion,
} from "../../types";
import DebugTabContent from "../quality/DebugTabContent";
import SceneImagePanel from "../quality/SceneImagePanel";
import Button from "../ui/Button";
import FixSuggestionsPanel from "./FixSuggestionsPanel";
import SceneActionBar from "./SceneActionBar";
import SceneFormFields from "./SceneFormFields";
import SceneGeminiModals from "./SceneGeminiModals";

type SceneCardProps = {
  scene: Scene;
  sceneIndex: number; // 씬 순서 (0-based, 표시는 +1)
  validationResult?: SceneValidation;
  imageValidationResult?: ImageValidation;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  sceneTab?: "validate" | "debug" | null;
  onSceneTabChange?: (tab: "validate" | "debug" | null) => void;
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
  onSuggestEditWithGemini: () => Promise<GeminiSuggestion[]>;
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
  structure?: string;
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
  structure,
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
  const [geminiSuggestions, setGeminiSuggestions] = useState<GeminiSuggestion[]>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const suggestions = validationResult ? getFixSuggestions(scene, validationResult) : [];

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
  const handleApproveSuggestion = (suggestion: { target_change: string }) => {
    setGeminiSuggestionsOpen(false);
    onEditWithGemini(suggestion.target_change);
  };

  return (
    <div className="grid gap-4 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-zinc-800">Scene {sceneIndex + 1}</h3>
          {scene.speaker === "B" && (
            <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
              B
            </span>
          )}
          {scene.speaker === "A" &&
            (structure?.toLowerCase() === "dialogue" ||
              structure?.toLowerCase() === "narrated dialogue") && (
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                A
              </span>
            )}
          {scene.speaker === "Narrator" && structure?.toLowerCase() === "narrated dialogue" && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
              N
            </span>
          )}
          <span className="text-[10px] font-semibold tracking-[0.15em] text-zinc-400 uppercase">
            {getSceneStatus(scene)}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            if (window.confirm(`Scene ${sceneIndex + 1}을(를) 삭제하시겠습니까?`)) {
              onRemoveScene();
            }
          }}
          className="text-rose-500 hover:bg-rose-50 hover:text-rose-600"
        >
          Remove
        </Button>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-4 md:grid-cols-[1.2fr_1fr]">
        {/* Left: ① Content + ② Prompt + ③ Actions + ④ Details */}
        <div className="grid gap-3">
          <SceneFormFields
            scene={scene}
            loraTriggerWords={loraTriggerWords}
            characterLoras={characterLoras}
            promptMode={promptMode}
            selectedCharacterId={selectedCharacterId}
            basePromptA={basePromptA}
            structure={structure}
            tagsByGroup={tagsByGroup}
            sceneTagGroups={sceneTagGroups}
            isExclusiveGroup={isExclusiveGroup}
            onUpdateScene={onUpdateScene}
            onSpeakerChange={onSpeakerChange}
            onImageUpload={onImageUpload}
          />

          {/* ③ Actions */}
          <SceneActionBar
            scene={scene}
            sceneIndex={sceneIndex}
            qualityScore={qualityScore}
            sceneMenuOpen={sceneMenuOpen}
            isLoadingSuggestions={isLoadingSuggestions}
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

          {/* ④ Details Toggle */}
          <button
            type="button"
            onClick={() => setShowSettings((v) => !v)}
            className="flex items-center gap-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-400 uppercase transition hover:text-zinc-600"
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

        {/* Right: ⑤ Result + QA */}
        <div className="sticky top-4 space-y-3 self-start">
          <SceneImagePanel
            scene={scene}
            onImageClick={(url) =>
              onImagePreview(
                url,
                scene.candidates?.map((c) => c.image_url)
              )
            }
            onCandidateSelect={(imageUrl) => onUpdateScene({ image_url: imageUrl })}
            onGenerateImage={onGenerateImage}
            validationResult={imageValidationResult}
            isValidating={validatingSceneId === scene.id}
            onValidate={onValidateImage}
            onApplyMissingTags={onApplyMissingTags}
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

          {/* Script Validation + Fix Suggestions */}
          {validationResult && validationResult.status !== "ok" && (
            <div className="rounded-xl border border-zinc-200 bg-white p-3">
              <div className="mb-2 flex items-center justify-between">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
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
                  className="text-[10px] font-semibold text-zinc-500 hover:text-zinc-700"
                >
                  {suggestionExpanded ? "Hide" : "Fix"}
                </button>
              </div>
              <p className="text-[11px] text-zinc-500">
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
        </div>
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
