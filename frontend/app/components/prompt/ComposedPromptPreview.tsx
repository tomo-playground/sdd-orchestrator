"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { API_BASE } from "../../constants";
import { useTagClassifier } from "../../hooks";
import CopyButton from "../ui/CopyButton";
import {
  SUCCESS_BG,
  SUCCESS_TEXT,
  WARNING_BG,
  WARNING_TEXT,
  ERROR_BG,
  ERROR_TEXT,
} from "../ui/variants";
import GroupedView from "./GroupedView";
import LinearView from "./LinearView";

type LoRAInfo = {
  name: string;
  weight?: number;
  trigger_words?: string[];
  lora_type?: string;
};

type ComposedPromptPreviewProps = {
  tokens: string[];
  characterId?: number | null;
  storyboardId?: number | null;
  sceneId?: number | null;
  basePrompt?: string;
  contextTags?: Record<string, unknown>;
  backgroundId?: number;
  loras?: LoRAInfo[];
  useBreak?: boolean;
  onComposed?: (result: ComposeResult) => void;
  onNegativeComposed?: (negative: string, sources: NegativeSourceInfo[]) => void;
  className?: string;
};

export type NegativeSourceInfo = {
  source: string; // "style_profile" | "character:<name>" | "scene"
  tokens: string[];
};

type ComposeResult = {
  prompt: string;
  tokens: string[];
  scene_complexity: string;
  lora_weights?: Record<string, number>;
  meta?: {
    token_count: number;
    has_break: boolean;
    quality_tags_added: boolean;
  };
  negative_prompt?: string;
  negative_sources?: NegativeSourceInfo[];
};

type ViewMode = "grouped" | "linear";

// 24 fine-grained categories → 12 layer-level groups
const CATEGORY_TO_LAYER: Record<string, string> = {
  quality: "Quality",
  subject: "Subject",
  identity: "Identity",
  hair_color: "Identity",
  hair_length: "Identity",
  hair_style: "Identity",
  hair_accessory: "Identity",
  eye_color: "Identity",
  eye_detail: "Identity",
  skin_color: "Identity",
  body_feature: "Body",
  body_type: "Body",
  appearance: "Identity",
  expression: "Expression",
  gaze: "Expression",
  pose: "Action",
  action: "Action",
  action_body: "Action",
  action_hand: "Action",
  action_daily: "Action",
  gesture: "Action",
  camera: "Camera",
  location_indoor: "Environment",
  location_indoor_general: "Environment",
  location_indoor_specific: "Environment",
  location_outdoor: "Environment",
  environment: "Environment",
  background_type: "Environment",
  time_of_day: "Atmosphere",
  time_weather: "Atmosphere",
  weather: "Atmosphere",
  particle: "Atmosphere",
  lighting: "Atmosphere",
  mood: "Atmosphere",
  clothing: "Clothing",
  clothing_top: "Clothing",
  clothing_bottom: "Clothing",
  clothing_outfit: "Clothing",
  clothing_detail: "Clothing",
  legwear: "Clothing",
  footwear: "Clothing",
  accessory: "Accessory",
  style: "Style",
  lora: "LoRA",
  break: "Break",
};

function getLayerGroup(category: string): string {
  return CATEGORY_TO_LAYER[category] ?? "Other";
}

// Layer-level colors (12 groups + extras)
export const LAYER_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  Quality: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  Subject: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  Identity: { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
  Body: { bg: "bg-pink-50", text: "text-pink-700", border: "border-pink-200" },
  Clothing: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  Accessory: { bg: "bg-cyan-50", text: "text-cyan-700", border: "border-cyan-200" },
  Expression: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  Action: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  Camera: { bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200" },
  Environment: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  Atmosphere: { bg: "bg-violet-50", text: "text-violet-700", border: "border-violet-200" },
  Style: { bg: "bg-fuchsia-50", text: "text-fuchsia-700", border: "border-fuchsia-200" },
  LoRA: { bg: "bg-violet-100", text: "text-violet-700", border: "border-violet-300" },
  Break: { bg: "bg-red-100", text: "text-red-700", border: "border-red-300" },
  Other: { bg: "bg-zinc-100", text: "text-zinc-600", border: "border-zinc-200" },
};

function getSpecialCategory(token: string): string | null {
  if (token.startsWith("<lora:") || token.startsWith("<model:")) return "lora";
  if (token === "BREAK") return "break";
  return null;
}

const VIEW_MODES: { key: ViewMode; label: string }[] = [
  { key: "grouped", label: "Grouped" },
  { key: "linear", label: "Linear" },
];

export default function ComposedPromptPreview({
  tokens,
  characterId,
  storyboardId,
  sceneId,
  basePrompt,
  contextTags,
  backgroundId,
  loras = [],
  useBreak = true,
  onComposed,
  onNegativeComposed,
  className = "",
}: ComposedPromptPreviewProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComposeResult | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("grouped");

  // API-based tag classification (15.7)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { classifyTags, getCachedCategory, isLoading: isClassifying } = useTagClassifier();
  const [apiCategories, setApiCategories] = useState<Record<string, string | null>>({});
  const classifiedTokensRef = useRef<string>("");

  // Classify tokens via API when they change
  useEffect(() => {
    const tokensToClassify = (result?.tokens || tokens).filter(
      (t) => !t.startsWith("<lora:") && t !== "BREAK"
    );
    const tokenKey = tokensToClassify.join(",");

    if (tokenKey === classifiedTokensRef.current || tokensToClassify.length === 0) {
      return;
    }

    classifiedTokensRef.current = tokenKey;
    classifyTags(tokensToClassify).then((results) => {
      setApiCategories(results);
    });
  }, [result?.tokens, tokens, classifyTags]);

  const getCategory = useCallback(
    (token: string): string => {
      const special = getSpecialCategory(token);
      if (special) return special;

      return apiCategories[token] || getCachedCategory(token) || "unknown";
    },
    [apiCategories, getCachedCategory]
  );

  const composePrompt = useCallback(async () => {
    if (tokens.length === 0 || !characterId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/prompt/compose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tokens,
          character_id: characterId,
          storyboard_id: storyboardId || undefined,
          scene_id: sceneId || undefined,
          context_tags: contextTags || undefined,
          background_id: backgroundId || undefined,
          use_break: useBreak,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to compose: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
      onComposed?.(data);
      if (data.negative_prompt || data.negative_sources) {
        onNegativeComposed?.(data.negative_prompt ?? "", data.negative_sources ?? []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, [
    tokens,
    characterId,
    storyboardId,
    sceneId,
    contextTags,
    backgroundId,
    useBreak,
    onComposed,
    onNegativeComposed,
  ]);

  // Auto-compose when tokens change (debounced)
  const prevTokensRef = useRef<string>("");
  useEffect(() => {
    const tokenKey =
      tokens.join(",") +
      "|" +
      loras.map((l) => l.name).join(",") +
      "|" +
      (characterId ?? "") +
      "|" +
      (basePrompt ?? "");

    if (tokenKey === prevTokensRef.current || tokens.length === 0) {
      return;
    }

    const timer = setTimeout(() => {
      prevTokensRef.current = tokenKey;
      composePrompt();
    }, 300);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokens, composePrompt]);

  // Group tokens by 12-layer groups
  const groupedTokens = (result?.tokens || tokens).reduce(
    (acc, token) => {
      const category = getCategory(token);
      const layer = getLayerGroup(category);
      if (!acc[layer]) acc[layer] = { category: layer, tokens: [] };
      acc[layer].tokens.push(token);
      return acc;
    },
    {} as Record<string, { category: string; tokens: string[] }>
  );

  const getTokenStyle = useCallback(
    (token: string) => {
      const category = getCategory(token);
      const layer = getLayerGroup(category);
      return LAYER_COLORS[layer] || LAYER_COLORS.Other;
    },
    [getCategory]
  );

  if (tokens.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header with controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Composed Positive
          </span>
          {isLoading && (
            <span className="animate-pulse rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-semibold text-blue-700">
              Composing...
            </span>
          )}
          {result?.scene_complexity && (
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                result.scene_complexity === "complex"
                  ? `${ERROR_BG} ${ERROR_TEXT}`
                  : result.scene_complexity === "moderate"
                    ? `${WARNING_BG} ${WARNING_TEXT}`
                    : `${SUCCESS_BG} ${SUCCESS_TEXT}`
              }`}
            >
              {result.scene_complexity}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {result?.prompt && <CopyButton text={result.prompt} variant="label" />}
          {/* View mode segment control */}
          <div className="flex overflow-hidden rounded-full border border-zinc-200">
            {VIEW_MODES.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setViewMode(key)}
                className={`px-2 py-1 text-[11px] font-semibold transition-colors ${
                  viewMode === key
                    ? "bg-zinc-800 text-white"
                    : "bg-white text-zinc-600 hover:bg-zinc-50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={composePrompt}
            disabled={isLoading}
            className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[11px] font-semibold text-zinc-600 hover:bg-zinc-50 disabled:opacity-50"
          >
            {isLoading ? "..." : result ? "Refresh" : "Compose"}
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && <div className="rounded-lg bg-red-50 p-2 text-[12px] text-red-600">{error}</div>}

      {/* Token display — compose result only */}
      {result &&
        (viewMode === "grouped" ? (
          <GroupedView groupedTokens={groupedTokens} getTokenStyle={getTokenStyle} />
        ) : (
          <LinearView
            tokens={result.tokens}
            getTokenStyle={getTokenStyle}
            getCategory={getCategory}
          />
        ))}

      {/* LoRA weights info */}
      {result?.lora_weights && Object.keys(result.lora_weights).length > 0 && (
        <div className="flex items-center gap-2 text-[12px] text-zinc-500">
          <span className="font-semibold">LoRA Weights:</span>
          {Object.entries(result.lora_weights).map(([name, weight]) => (
            <span key={name} className="rounded bg-violet-50 px-1.5 py-0.5 text-violet-700">
              {name}: {weight}
            </span>
          ))}
        </div>
      )}

      {/* Meta info */}
      {result?.meta && (
        <div className="flex items-center gap-3 text-[11px] text-zinc-400">
          <span>{result.meta.token_count} tokens</span>
          {result.meta.has_break && <span>with BREAK</span>}
          {result.meta.quality_tags_added && <span>+quality</span>}
        </div>
      )}
    </div>
  );
}
