"use client";

import { useState } from "react";
import type { Scene, SceneValidation, ImageValidation, FixSuggestion, Tag } from "../../types";
import { SAMPLERS } from "../../constants";
import ValidationTabContent from "../quality/ValidationTabContent";
import DebugTabContent from "../quality/DebugTabContent";
import SceneImagePanel from "../quality/SceneImagePanel";
import SceneContextTags from "../prompt/SceneContextTags";
import PromptTokenPreview from "../prompt/PromptTokenPreview";
import ComposedPromptPreview from "../prompt/ComposedPromptPreview";
import TagAutocomplete from "../ui/TagAutocomplete";

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
  onSavePrompt?: () => void;
  onMarkSuccess?: () => void;
  onMarkFail?: () => void;
  isMarkingStatus?: boolean;
  // Utility functions
  getSceneStatus: (scene: Scene) => string;
  getFixSuggestions: (scene: Scene, validation: SceneValidation) => FixSuggestion[];
  applySuggestion: (scene: Scene, suggestion: FixSuggestion) => void;
  buildPositivePrompt: (scene: Scene) => string;
  buildNegativePrompt: (scene: Scene) => string;
  buildScenePrompt: (scene: Scene) => Promise<string | null>;
  getBasePromptForScene: (scene: Scene) => string;
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
  onSavePrompt,
  onMarkSuccess,
  onMarkFail,
  isMarkingStatus = false,
  getSceneStatus,
  getFixSuggestions,
  applySuggestion,
  buildPositivePrompt,
  buildNegativePrompt,
  buildScenePrompt,
  getBasePromptForScene,
  showToast,
}: SceneCardProps) {
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");
  const [geminiSuggestionsOpen, setGeminiSuggestionsOpen] = useState(false);
  const [geminiSuggestions, setGeminiSuggestions] = useState<any[]>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  const suggestions = validationResult ? getFixSuggestions(scene, validationResult) : [];
  const actionableSuggestions = suggestions.filter((item) => item.action);

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
      const suggestions = await onSuggestEditWithGemini();
      if (suggestions && suggestions.length > 0) {
        setGeminiSuggestions(suggestions);
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
        <div className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-xs text-zinc-600">
          <div className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Fix Suggestions
          </div>
          {suggestions.length === 0 ? (
            <p className="mt-2 text-[11px] text-zinc-500">No auto suggestions.</p>
          ) : (
            <>
              {actionableSuggestions.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    actionableSuggestions.forEach((item) => applySuggestion(scene, item));
                  }}
                  className="mt-2 rounded-full border border-zinc-300 bg-white/80 px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                >
                  Apply All
                </button>
              )}
              <ul className="mt-2 grid gap-2 text-[11px]">
                {suggestions.map((item) => (
                  <li
                    key={`${scene.id}-${item.id}`}
                    className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-white/70 px-3 py-2"
                  >
                    <span className="text-zinc-600">{item.message}</span>
                    {item.action ? (
                      <button
                        type="button"
                        onClick={() => applySuggestion(scene, item)}
                        className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase"
                      >
                        Apply
                      </button>
                    ) : (
                      <span className="text-[10px] tracking-[0.2em] text-zinc-400 uppercase">
                        Manual
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid gap-4 md:grid-cols-[1.2fr_1fr]">
        {/* Left Column: Form Fields */}
        <div className="grid gap-3">
          {/* Script */}
          <div className="grid gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Script
            </label>
            <textarea
              value={scene.script}
              onChange={(e) => onUpdateScene({ script: e.target.value })}
              rows={3}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
            />
          </div>

          {/* Speaker, Duration, Upload */}
          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Speaker
              </label>
              <select
                value={scene.speaker}
                onChange={(e) => onSpeakerChange(e.target.value as Scene["speaker"])}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              >
                <option value="A">Actor A</option>
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Duration
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={scene.duration}
                onChange={(e) => onUpdateScene({ duration: Number(e.target.value) })}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Image
              </label>
              <label className="flex h-10 cursor-pointer items-center justify-center rounded-2xl border border-dashed border-zinc-300 bg-white/80 text-[10px] font-semibold tracking-[0.2em] text-zinc-600 uppercase">
                Upload
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => onImageUpload(e.target.files?.[0])}
                />
              </label>
            </div>
          </div>

          {/* Positive Prompt */}
          <div className="grid gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Positive Prompt
            </label>
            <TagAutocomplete
              value={scene.image_prompt}
              onChange={(value) => onUpdateScene({ image_prompt: value })}
              rows={2}
              className="w-full rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
            />
            {scene.image_prompt && (
              <>
                <PromptTokenPreview
                  prompt={scene.image_prompt}
                  triggerWords={loraTriggerWords}
                />
                <ComposedPromptPreview
                  tokens={[
                    ...getBasePromptForScene(scene).split(",").map((t) => t.trim()).filter(Boolean),
                    ...scene.image_prompt.split(",").map((t) => t.trim()).filter(Boolean),
                  ]}
                  loras={characterLoras}
                  mode={promptMode}
                  useBreak={true}
                  className="mt-2 rounded-xl border border-zinc-200 bg-zinc-50/50 p-3"
                />
              </>
            )}
          </div>

          {/* Negative Prompt */}
          <div className="grid gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Negative Prompt
            </label>
            <textarea
              value={scene.negative_prompt}
              onChange={(e) => onUpdateScene({ negative_prompt: e.target.value })}
              rows={2}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
            />
          </div>

          {/* Prompt (KO) */}
          <div className="grid gap-2">
            <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
              Prompt (KO)
            </label>
            <TagAutocomplete
              value={scene.image_prompt_ko}
              onChange={(value) => onUpdateScene({ image_prompt_ko: value })}
              rows={2}
              className="w-full rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
            />
          </div>

          {/* Scene Context Tags */}
          <SceneContextTags
            contextTags={scene.context_tags}
            tagsByGroup={tagsByGroup}
            sceneTagGroups={sceneTagGroups}
            isExclusiveGroup={isExclusiveGroup}
            onUpdate={(tags) => onUpdateScene({ context_tags: tags })}
          />

          {/* Generation Settings */}
          <div className="grid gap-3 md:grid-cols-3">
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Steps
              </label>
              <input
                type="number"
                min={1}
                max={80}
                value={scene.steps}
                onChange={(e) => onUpdateScene({ steps: Number(e.target.value) })}
                disabled={autoComposePrompt}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                CFG
              </label>
              <input
                type="number"
                min={1}
                max={20}
                step={0.5}
                value={scene.cfg_scale}
                onChange={(e) => onUpdateScene({ cfg_scale: Number(e.target.value) })}
                disabled={autoComposePrompt}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Sampler
              </label>
              <select
                value={scene.sampler_name}
                onChange={(e) => onUpdateScene({ sampler_name: e.target.value })}
                disabled={autoComposePrompt}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              >
                {SAMPLERS.map((sampler) => (
                  <option key={sampler} value={sampler}>
                    {sampler}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Seed
              </label>
              <input
                type="number"
                value={scene.seed}
                onChange={(e) => onUpdateScene({ seed: Number(e.target.value) })}
                disabled={autoComposePrompt}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Clip Skip
              </label>
              <input
                type="number"
                min={1}
                max={12}
                value={scene.clip_skip}
                onChange={(e) => onUpdateScene({ clip_skip: Number(e.target.value) })}
                disabled={autoComposePrompt}
                className="rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
              />
            </div>
          </div>

          {/* Primary Action + More Menu */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onGenerateImage}
                disabled={scene.isGenerating}
                className="rounded-full bg-zinc-900 px-5 py-2.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400 flex items-center gap-2"
              >
                {scene.isGenerating ? "Generating..." : "Generate Image"}
                {scene.environment_reference_id && !scene.isGenerating && (
                  <span className="ml-1 text-[#FFD700] animate-pulse" title="Background Pinned">📌</span>
                )}
              </button>
              {scene.image_url && !scene.isGenerating && (
                <button
                  type="button"
                  onClick={() => {
                    // Toggle pinning: if already pinned to THIS asset, unpin.
                    // If not pinned, pin to the current image's asset ID.
                    if (!scene.image_asset_id && !scene.environment_reference_id) {
                      showToast("이미지를 먼저 생성하거나 업로드해야 배경을 고정할 수 있습니다.", "error");
                      return;
                    }
                    const isPinned = !!scene.environment_reference_id;
                    onUpdateScene({
                      environment_reference_id: isPinned ? null : scene.image_asset_id,
                      environment_reference_weight: 0.3
                    });
                  }}
                  className={`rounded-full p-2.5 text-[10px] shadow-md transition ${scene.environment_reference_id ? 'bg-amber-100 text-amber-600 border border-amber-300' : 'bg-white text-zinc-400 border border-zinc-200 hover:bg-zinc-50'}`}
                  title={scene.environment_reference_id ? "배경 고정 해제" : "이 장면의 배경을 다음 생성 시 고정합니다"}
                >
                  📌
                </button>
              )}
              {scene.image_url && !scene.isGenerating && (
                <button
                  type="button"
                  onClick={() => setGeminiEditOpen(true)}
                  className={`rounded-full px-4 py-2.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md transition ${qualityScore && qualityScore.match_rate < 0.7
                    ? "bg-gradient-to-r from-purple-500 to-pink-500 shadow-purple-500/20 hover:from-purple-600 hover:to-pink-600"
                    : "bg-gradient-to-r from-purple-400/80 to-pink-400/80 shadow-purple-400/10 hover:from-purple-500/80 hover:to-pink-500/80"
                    }`}
                  title={
                    qualityScore && qualityScore.match_rate < 0.7
                      ? `Match Rate가 낮습니다 (${(qualityScore.match_rate * 100).toFixed(0)}%). Gemini로 수정하세요.`
                      : "Gemini로 포즈/표정/시선을 수정할 수 있습니다."
                  }
                >
                  ✨ Edit with Gemini
                </button>
              )}
              {scene.image_url && !scene.isGenerating && (
                <button
                  type="button"
                  onClick={handleAutoSuggest}
                  disabled={isLoadingSuggestions}
                  className="rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-2.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md shadow-indigo-500/20 transition hover:from-indigo-600 hover:to-purple-600 disabled:cursor-not-allowed disabled:opacity-50"
                  title="Gemini가 이미지와 프롬프트를 비교해 자동으로 수정 제안을 생성합니다"
                >
                  {isLoadingSuggestions ? "분석중..." : "🤖 Auto Suggest"}
                </button>
              )}
              {scene.activity_log_id && onMarkSuccess && onMarkFail && (
                <>
                  <button
                    type="button"
                    onClick={onMarkSuccess}
                    disabled={isMarkingStatus}
                    title="Mark as Success"
                    className="rounded-full bg-emerald-500 px-3 py-2 text-[10px] font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-emerald-300"
                  >
                    👍
                  </button>
                  <button
                    type="button"
                    onClick={onMarkFail}
                    disabled={isMarkingStatus}
                    title="Mark as Fail"
                    className="rounded-full bg-rose-500 px-3 py-2 text-[10px] font-semibold text-white transition hover:bg-rose-600 disabled:cursor-not-allowed disabled:bg-rose-300"
                  >
                    👎
                  </button>
                </>
              )}
            </div>
            <div className="relative">
              <button
                type="button"
                onClick={onSceneMenuToggle}
                className="rounded-full border border-zinc-200 bg-white p-2 text-zinc-500 transition hover:bg-zinc-50"
              >
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                </svg>
              </button>
              {sceneMenuOpen && (
                <div className="absolute right-0 z-10 mt-1 w-40 rounded-xl border border-zinc-200 bg-white py-1 shadow-lg">
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(buildPositivePrompt(scene));
                      showToast("프롬프트 복사됨", "success");
                      onSceneMenuClose();
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-zinc-700 hover:bg-zinc-50"
                  >
                    Copy Prompt
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onUpdateScene({ seed: Math.floor(Math.random() * 999999999) });
                      onSceneMenuClose();
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-zinc-700 hover:bg-zinc-50"
                  >
                    Randomize Seed
                  </button>
                  {onSavePrompt && scene.image_url && (
                    <button
                      type="button"
                      onClick={() => {
                        onSavePrompt();
                        onSceneMenuClose();
                      }}
                      className="w-full px-3 py-2 text-left text-xs text-emerald-600 hover:bg-emerald-50"
                    >
                      Save Prompt
                    </button>
                  )}
                  <hr className="my-1 border-zinc-100" />
                  <button
                    type="button"
                    onClick={() => {
                      if (confirm("이 씬을 삭제하시겠습니까?")) {
                        onRemoveScene();
                      }
                      onSceneMenuClose();
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-red-600 hover:bg-red-50"
                  >
                    Delete Scene
                  </button>
                </div>
              )}
            </div>
          </div>

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
                // Use the same prompt composition as actual image generation
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
                  height: 512,
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

      {/* Gemini Edit Modal */}
      {geminiEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-zinc-800">✨ Fix with Gemini Nano Banana</h3>
              <button
                type="button"
                onClick={() => {
                  setGeminiEditOpen(false);
                  setGeminiTargetChange("");
                }}
                className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
              >
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <p className="mb-2 text-sm text-zinc-600">
                  현재 Match Rate가 낮습니다 ({(qualityScore?.match_rate ?? 0) * 100}%). 어떤 부분을 수정하시겠습니까?
                </p>
                <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
                  <strong>Missing Tags:</strong>{" "}
                  {qualityScore?.missing_tags.slice(0, 5).join(", ") || "None"}
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-zinc-700">
                  어떻게 바꿀까요? (자연어로 입력하세요)
                </label>
                <div className="mb-2 flex flex-wrap gap-2">
                  {[
                    "의자에 앉아서 무릎에 손 올리기",
                    "밝게 웃으면서 정면 보기",
                    "뒤돌아서 어깨 너머로 보기",
                    "오른손 들어 손 흔들기",
                  ].map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => setGeminiTargetChange(example)}
                      className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs text-zinc-600 transition hover:border-purple-300 hover:bg-purple-50"
                    >
                      {example}
                    </button>
                  ))}
                </div>
                <textarea
                  value={geminiTargetChange}
                  onChange={(e) => setGeminiTargetChange(e.target.value)}
                  placeholder="예: 의자에 앉아서 무릎에 손 올리기 / 환하게 웃으면서 카메라 보기"
                  className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-purple-400"
                  rows={3}
                />
              </div>

              <div className="flex justify-between gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setGeminiEditOpen(false);
                    setGeminiTargetChange("");
                  }}
                  className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
                >
                  취소
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (!geminiTargetChange.trim()) {
                      showToast("변경 내용을 입력하세요", "error");
                      return;
                    }
                    onEditWithGemini(geminiTargetChange.trim());
                    setGeminiEditOpen(false);
                    setGeminiTargetChange("");
                  }}
                  disabled={!geminiTargetChange.trim() || scene.isGenerating}
                  className="flex-1 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:from-purple-600 hover:to-pink-600 disabled:cursor-not-allowed disabled:from-purple-300 disabled:to-pink-300"
                >
                  ✨ 편집 시작 (~$0.04)
                </button>
              </div>

              <p className="text-[10px] text-zinc-400">
                💡 Gemini가 얼굴/화풍을 유지하면서 포즈/표정/시선만 변경합니다.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Gemini Auto-Suggest Modal */}
      {geminiSuggestionsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-2xl rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-zinc-800">🤖 Gemini Auto Suggestions</h3>
              <button
                type="button"
                onClick={() => {
                  setGeminiSuggestionsOpen(false);
                  setGeminiSuggestions([]);
                }}
                className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
              >
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <p className="text-sm text-zinc-600">
                Gemini가 이미지와 프롬프트를 비교해 {geminiSuggestions.length}개의 수정 제안을 생성했습니다.
              </p>

              <div className="space-y-3">
                {geminiSuggestions.map((suggestion, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-zinc-200 bg-gradient-to-br from-white to-zinc-50 p-4 transition hover:border-indigo-300 hover:shadow-md"
                  >
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="mb-1 flex items-center gap-2">
                          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 uppercase">
                            {suggestion.edit_type}
                          </span>
                          <span className="text-xs font-semibold text-zinc-800">{suggestion.issue}</span>
                        </div>
                        <p className="text-sm text-zinc-600">{suggestion.description}</p>
                      </div>
                      <div className="text-xs text-zinc-500">
                        {(suggestion.confidence * 100).toFixed(0)}%
                      </div>
                    </div>

                    <div className="mb-3 rounded-lg bg-indigo-50 p-3">
                      <p className="text-xs font-semibold text-indigo-900">💡 제안:</p>
                      <p className="text-sm text-indigo-700">{suggestion.target_change}</p>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleApproveSuggestion(suggestion)}
                      className="w-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-2 text-sm font-semibold text-white transition hover:from-indigo-600 hover:to-purple-600"
                    >
                      ✅ 이 제안 승인하고 편집 (~$0.04)
                    </button>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={() => {
                  setGeminiSuggestionsOpen(false);
                  setGeminiSuggestions([]);
                }}
                className="w-full rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
              >
                모든 제안 무시
              </button>

              <p className="text-[10px] text-zinc-400">
                💡 제안을 승인하면 Gemini Nano Banana가 이미지를 자동으로 편집합니다.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
