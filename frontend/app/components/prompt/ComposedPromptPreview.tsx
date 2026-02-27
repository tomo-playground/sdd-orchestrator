"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { ADMIN_API_BASE } from "../../constants";
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
import LayerView from "./LayerView";
import GroupedView from "./GroupedView";
import LinearView from "./LinearView";

type LoRAInfo = {
  name: string;
  weight?: number;
  trigger_words?: string[];
  lora_type?: string;
  optimal_weight?: number;
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

export type ComposedLayer = { index: number; name: string; tokens: string[] };

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
  layers?: ComposedLayer[];
};

type ViewMode = "layers" | "grouped" | "linear";

// Category colors for visual grouping
const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  quality: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  subject: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  identity: { bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
  hair_color: { bg: "bg-pink-50", text: "text-pink-700", border: "border-pink-200" },
  hair_length: { bg: "bg-pink-50", text: "text-pink-700", border: "border-pink-200" },
  hair_style: { bg: "bg-pink-50", text: "text-pink-700", border: "border-pink-200" },
  hair_accessory: { bg: "bg-pink-50", text: "text-pink-700", border: "border-pink-200" },
  eye_color: { bg: "bg-cyan-50", text: "text-cyan-700", border: "border-cyan-200" },
  skin_color: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  body_feature: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  body_type: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  eye_detail: { bg: "bg-cyan-50", text: "text-cyan-700", border: "border-cyan-200" },
  appearance: { bg: "bg-slate-50", text: "text-slate-700", border: "border-slate-200" },
  expression: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  gaze: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  pose: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  action_body: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  action_hand: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  action_daily: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  action: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  gesture: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  camera: { bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200" },
  location_indoor: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  location_indoor_general: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
  },
  location_indoor_specific: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
  },
  location_outdoor: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  environment: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  background_type: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  time_of_day: { bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200" },
  weather: { bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200" },
  particle: { bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200" },
  lighting: { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200" },
  mood: { bg: "bg-violet-50", text: "text-violet-700", border: "border-violet-200" },
  clothing_top: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  clothing_bottom: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  clothing_outfit: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  clothing: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  clothing_detail: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  legwear: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  footwear: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
  accessory: { bg: "bg-fuchsia-50", text: "text-fuchsia-700", border: "border-fuchsia-200" },
  style: { bg: "bg-fuchsia-50", text: "text-fuchsia-700", border: "border-fuchsia-200" },
  lora: { bg: "bg-violet-100", text: "text-violet-700", border: "border-violet-300" },
  break: { bg: "bg-red-100", text: "text-red-700", border: "border-red-300" },
  unknown: { bg: "bg-zinc-100", text: "text-zinc-600", border: "border-zinc-200" },
};

// Category display names
const CATEGORY_LABELS: Record<string, string> = {
  quality: "퀄리티",
  subject: "피사체",
  identity: "캐릭터",
  hair_color: "헤어",
  hair_length: "헤어",
  hair_style: "헤어",
  hair_accessory: "헤어",
  eye_color: "눈",
  eye_detail: "눈 디테일",
  skin_color: "피부",
  body_feature: "신체",
  body_type: "체형",
  appearance: "외모",
  expression: "표정",
  gaze: "시선",
  pose: "포즈",
  action: "동작",
  action_body: "몸 동작",
  action_hand: "손 동작",
  action_daily: "일상 동작",
  gesture: "제스처",
  camera: "카메라",
  location_indoor: "실내",
  location_indoor_general: "실내 일반",
  location_indoor_specific: "실내 상세",
  location_outdoor: "야외",
  environment: "환경",
  background_type: "배경",
  time_of_day: "시간대",
  time_weather: "시간/날씨",
  weather: "날씨",
  particle: "파티클",
  lighting: "조명",
  mood: "분위기",
  clothing: "의류",
  clothing_top: "상의",
  clothing_bottom: "하의",
  clothing_outfit: "전신복",
  clothing_detail: "의상 디테일",
  legwear: "레그웨어",
  footwear: "신발",
  accessory: "액세서리",
  style: "스타일",
  lora: "LoRA",
  break: "구분선",
  unknown: "기타",
};

/** Fallback: format raw group_name as display label. */
function getCategoryLabel(group: string): string {
  return CATEGORY_LABELS[group] ?? group.replace(/_/g, " ");
}

function getTokenCategory(token: string): string {
  if (token.startsWith("<lora:")) return "lora";
  if (token.startsWith("<model:")) return "lora";
  if (token === "BREAK") return "break";
  return "unknown";
}

const VIEW_MODES: { key: ViewMode; label: string }[] = [
  { key: "layers", label: "Layers" },
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
  const [viewMode, setViewMode] = useState<ViewMode>("layers");

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
      if (token.startsWith("<lora:")) return "lora";
      if (token === "BREAK") return "break";

      const apiCategory = apiCategories[token] || getCachedCategory(token);
      if (apiCategory) return apiCategory;

      return getTokenCategory(token);
    },
    [apiCategories, getCachedCategory]
  );

  const composePrompt = useCallback(async () => {
    if (tokens.length === 0 || !characterId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${ADMIN_API_BASE}/prompt/compose`, {
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

  // Group tokens by display label for grouped view
  const groupedTokens = (result?.tokens || tokens).reduce(
    (acc, token) => {
      const category = getCategory(token);
      const label = getCategoryLabel(category);
      if (!acc[label]) acc[label] = { category, tokens: [] };
      acc[label].tokens.push(token);
      return acc;
    },
    {} as Record<string, { category: string; tokens: string[] }>
  );

  const getTokenStyle = useCallback(
    (token: string) => {
      const category = getCategory(token);
      return CATEGORY_COLORS[category] || CATEGORY_COLORS.unknown;
    },
    [getCategory]
  );

  // Determine effective view mode (fallback if layers unavailable)
  const hasLayers = !!result?.layers && result.layers.length > 0;
  const effectiveMode = viewMode === "layers" && !hasLayers ? "grouped" : viewMode;

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
          {/* 3-way segment control */}
          <div className="flex overflow-hidden rounded-full border border-zinc-200">
            {VIEW_MODES.map(({ key, label }) => {
              const isDisabled = key === "layers" && !hasLayers;
              const isActive = effectiveMode === key;
              return (
                <button
                  key={key}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => setViewMode(key)}
                  className={`px-2 py-1 text-[11px] font-semibold transition-colors ${
                    isActive
                      ? "bg-zinc-800 text-white"
                      : isDisabled
                        ? "cursor-not-allowed bg-white text-zinc-300"
                        : "bg-white text-zinc-600 hover:bg-zinc-50"
                  }`}
                  title={isDisabled ? "Multi-character scenes have no layer data" : undefined}
                >
                  {label}
                </button>
              );
            })}
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
        (effectiveMode === "layers" && result.layers ? (
          <LayerView layers={result.layers} />
        ) : effectiveMode === "grouped" ? (
          <GroupedView
            groupedTokens={groupedTokens}
            categoryColors={CATEGORY_COLORS}
            getTokenStyle={getTokenStyle}
          />
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
