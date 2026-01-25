"use client";

import type { Scene, SceneValidation, ImageValidation, FixSuggestion, Tag } from "../types";
import { SAMPLERS } from "../constants";
import ValidationTabContent from "./ValidationTabContent";
import DebugTabContent from "./DebugTabContent";
import SceneImagePanel from "./SceneImagePanel";
import SceneContextTags from "./SceneContextTags";

type SceneCardProps = {
  scene: Scene;
  validationResult?: SceneValidation;
  imageValidationResult?: ImageValidation;
  sceneTab: "validate" | "debug" | null;
  onSceneTabChange: (tab: "validate" | "debug" | null) => void;
  sceneMenuOpen: boolean;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
  suggestionExpanded: boolean;
  onSuggestionToggle: () => void;
  validatingSceneId: number | null;
  autoComposePrompt: boolean;
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
  onValidateImage: () => void;
  onApplyMissingTags: (tags: string[]) => void;
  onImagePreview: (url: string | null) => void;
  // Utility functions
  getSceneStatus: (scene: Scene) => string;
  getFixSuggestions: (scene: Scene, validation: SceneValidation) => FixSuggestion[];
  applySuggestion: (scene: Scene, suggestion: FixSuggestion) => void;
  buildPositivePrompt: (scene: Scene) => string;
  buildNegativePrompt: (scene: Scene) => string;
  getBasePromptForScene: (scene: Scene) => string;
  showToast: (message: string, type: "success" | "error") => void;
};

export default function SceneCard({
  scene,
  validationResult,
  imageValidationResult,
  sceneTab,
  onSceneTabChange,
  sceneMenuOpen,
  onSceneMenuToggle,
  onSceneMenuClose,
  suggestionExpanded,
  onSuggestionToggle,
  validatingSceneId,
  autoComposePrompt,
  tagsByGroup,
  sceneTagGroups,
  isExclusiveGroup,
  onUpdateScene,
  onRemoveScene,
  onSpeakerChange,
  onImageUpload,
  onGenerateImage,
  onValidateImage,
  onApplyMissingTags,
  onImagePreview,
  getSceneStatus,
  getFixSuggestions,
  applySuggestion,
  buildPositivePrompt,
  buildNegativePrompt,
  getBasePromptForScene,
  showToast,
}: SceneCardProps) {
  const suggestions = validationResult ? getFixSuggestions(scene, validationResult) : [];
  const actionableSuggestions = suggestions.filter((item) => item.action);

  return (
    <div className="grid gap-4 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-800">Scene {scene.id}</h3>
        {validationResult && (
          <button
            type="button"
            onClick={() => {
              if (validationResult.status === "ok") return;
              onSuggestionToggle();
            }}
            className={`rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.2em] uppercase ${
              validationResult.status === "ok"
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
            if (window.confirm(`Scene ${scene.id}를 삭제하시겠습니까?`)) {
              onRemoveScene();
            }
          }}
          className="text-[10px] font-semibold tracking-[0.2em] text-rose-500 uppercase hover:text-rose-600"
        >
          Remove
        </button>
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
            <textarea
              value={scene.image_prompt}
              onChange={(e) => onUpdateScene({ image_prompt: e.target.value })}
              rows={2}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
            />
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
            <textarea
              value={scene.image_prompt_ko}
              onChange={(e) => onUpdateScene({ image_prompt_ko: e.target.value })}
              rows={2}
              className="rounded-2xl border border-zinc-200 bg-white/80 p-3 text-sm outline-none focus:border-zinc-400"
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
            <button
              type="button"
              onClick={onGenerateImage}
              disabled={scene.isGenerating}
              className="rounded-full bg-zinc-900 px-5 py-2.5 text-[10px] font-semibold tracking-[0.2em] text-white uppercase shadow-md shadow-zinc-900/20 transition disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {scene.isGenerating ? "Generating..." : "Generate Image"}
            </button>
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
                className={`flex-1 rounded-lg px-3 py-1.5 text-[10px] font-semibold uppercase transition ${
                  sceneTab === tab
                    ? "bg-white text-zinc-900 shadow-sm"
                    : "text-zinc-500 hover:text-zinc-700"
                }`}
              >
                {tab === "validate" && (
                  <span className="flex items-center justify-center gap-1">
                    Validate
                    {imageValidationResult && (
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          imageValidationResult.match_rate >= 0.8
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
              onGenerateDebug={() => {
                const basePrompt = getBasePromptForScene(scene);
                const scenePrompt = scene.image_prompt;
                const prompt =
                  autoComposePrompt && basePrompt ? `${basePrompt}, ${scenePrompt}` : scenePrompt;
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
          onImageClick={onImagePreview}
          onCandidateSelect={(imageUrl) => onUpdateScene({ image_url: imageUrl })}
        />
      </div>
    </div>
  );
}
