"use client";

import { createContext, useContext } from "react";
import type { Scene, ImageValidation, ImageGenProgress, Tag, GeminiSuggestion } from "../../types";

/** Scene data available via context (read-only values from parent) */
export type SceneDataContext = {
  imageValidationResult?: ImageValidation;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  validatingSceneId: string | null;
  loraTriggerWords: string[];
  characterLoras: Array<{
    name: string;
    weight?: number;
    trigger_words?: string[];
    lora_type?: string;
    optimal_weight?: number;
  }>;
  tagsByGroup: Record<string, Tag[]>;
  sceneTagGroups: string[];
  isExclusiveGroup: (groupName: string) => boolean;
  selectedCharacterId?: number | null;
  basePromptA: string;
  structure?: string;
  characterAName?: string | null;
  characterBName?: string | null;
  selectedCharacterBId?: number | null;
  genProgress?: ImageGenProgress | null;
  pinnedSceneOrder?: number;
  isMarkingStatus: boolean;
};

/** Scene callbacks available via context */
export type SceneCallbacksContext = {
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
  onMarkSuccess?: () => void;
  onMarkFail?: () => void;
  buildNegativePrompt: (scene: Scene) => string;
  buildScenePrompt: (scene: Scene) => string | null;
  showToast: (message: string, type: "success" | "error") => void;
  onSceneMenuToggle: () => void;
  onSceneMenuClose: () => void;
};

export type SceneContextValue = {
  data: SceneDataContext;
  callbacks: SceneCallbacksContext;
};

const SceneCtx = createContext<SceneContextValue | null>(null);

export function SceneProvider({
  value,
  children,
}: {
  value: SceneContextValue;
  children: React.ReactNode;
}) {
  return <SceneCtx.Provider value={value}>{children}</SceneCtx.Provider>;
}

export function useSceneContext(): SceneContextValue {
  const ctx = useContext(SceneCtx);
  if (!ctx) {
    throw new Error("useSceneContext must be used within a SceneProvider");
  }
  return ctx;
}
