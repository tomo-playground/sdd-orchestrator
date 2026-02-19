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
  INFO_BG,
  INFO_TEXT,
} from "../ui/variants";

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
  loras?: LoRAInfo[];
  mode?: "auto" | "standard" | "lora";
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
  effective_mode: string;
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
  appearance: { bg: "bg-slate-50", text: "text-slate-700", border: "border-slate-200" },
  expression: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  gaze: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" },
  pose: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  action: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  camera: { bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200" },
  location_indoor: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  location_outdoor: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  environment: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  background_type: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  time_weather: { bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200" },
  lighting: { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200" },
  mood: { bg: "bg-violet-50", text: "text-violet-700", border: "border-violet-200" },
  clothing: { bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200" },
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
  skin_color: "피부",
  body_feature: "신체",
  appearance: "외모",
  expression: "표정",
  gaze: "시선",
  pose: "포즈",
  action: "동작",
  camera: "카메라",
  location_indoor: "실내",
  location_outdoor: "야외",
  environment: "환경",
  background_type: "배경",
  time_weather: "시간/날씨",
  lighting: "조명",
  mood: "분위기",
  clothing: "의상",
  style: "스타일",
  lora: "LoRA",
  break: "구분선",
  unknown: "기타",
};

function getTokenCategory(token: string): string {
  // LoRA detection (special client-rule)
  if (token.startsWith("<lora:")) return "lora";
  if (token.startsWith("<model:")) return "lora";
  if (token === "BREAK") return "break";

  // All other categorization logic has been moved to the backend.
  // If useTagClassifier hook doesn't provide a category, it's unknown.
  return "unknown";
}

export default function ComposedPromptPreview({
  tokens,
  characterId,
  storyboardId,
  sceneId,
  basePrompt,
  contextTags,
  loras = [],
  mode = "auto",
  useBreak = true,
  onComposed,
  onNegativeComposed,
  className = "",
}: ComposedPromptPreviewProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComposeResult | null>(null);
  const [showGrouped, setShowGrouped] = useState(true);

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

    // Skip if already classified this set
    if (tokenKey === classifiedTokensRef.current || tokensToClassify.length === 0) {
      return;
    }

    classifiedTokensRef.current = tokenKey;
    classifyTags(tokensToClassify).then((results) => {
      setApiCategories(results);
    });
  }, [result?.tokens, tokens, classifyTags]);

  // Get category with API fallback
  const getCategory = useCallback(
    (token: string): string => {
      // Special tokens
      if (token.startsWith("<lora:")) return "lora";
      if (token === "BREAK") return "break";

      // Check API result first
      const apiCategory = apiCategories[token] || getCachedCategory(token);
      if (apiCategory) return apiCategory;

      // Fallback to local pattern matching
      return getTokenCategory(token);
    },
    [apiCategories, getCachedCategory]
  );

  const composePrompt = useCallback(async () => {
    if (tokens.length === 0 || !characterId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Style LoRAs resolved by Backend from storyboard → group → style_profile (SSOT)
      const response = await fetch(`${API_BASE}/prompt/compose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tokens,
          character_id: characterId,
          storyboard_id: storyboardId || undefined,
          scene_id: sceneId || undefined,
          context_tags: contextTags || undefined,
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
      mode +
      "|" +
      (characterId ?? "") +
      "|" +
      (basePrompt ?? "");

    // Skip if same as previous
    if (tokenKey === prevTokensRef.current || tokens.length === 0) {
      return;
    }

    prevTokensRef.current = tokenKey;

    // Debounce: wait 300ms before calling API
    const timer = setTimeout(() => {
      composePrompt();
    }, 300);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokens, composePrompt]);

  // Group tokens by display label for grouped view (merges hair_color, hair_length, etc. into "헤어")
  const groupedTokens = (result?.tokens || tokens).reduce(
    (acc, token) => {
      const category = getCategory(token);
      const label = CATEGORY_LABELS[category] || category;
      if (!acc[label]) acc[label] = { category, tokens: [] };
      acc[label].tokens.push(token);
      return acc;
    },
    {} as Record<string, { category: string; tokens: string[] }>
  );

  const getTokenStyle = (token: string) => {
    const category = getCategory(token);
    return CATEGORY_COLORS[category] || CATEGORY_COLORS.unknown;
  };

  if (tokens.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header with controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
            Composed Preview
          </span>
          {isLoading && (
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-semibold text-blue-700">
              Composing...
            </span>
          )}
          {!isLoading && result && (
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${SUCCESS_BG} ${SUCCESS_TEXT}`}
            >
              Filtered
            </span>
          )}
          {!isLoading && !result && (
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-semibold text-zinc-500">
              Raw
            </span>
          )}
          {result && (
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                result.effective_mode === "lora"
                  ? `${INFO_BG} ${INFO_TEXT}`
                  : "bg-zinc-100 text-zinc-600"
              }`}
            >
              {result.effective_mode.toUpperCase()}
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
          <button
            type="button"
            onClick={() => setShowGrouped(!showGrouped)}
            className="rounded-full border border-zinc-200 bg-white px-2 py-1 text-[11px] font-semibold text-zinc-600 hover:bg-zinc-50"
          >
            {showGrouped ? "Linear" : "Grouped"}
          </button>
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

      {/* Token display */}
      {showGrouped ? (
        // Grouped view by category
        <div className="space-y-2">
          {Object.entries(groupedTokens).map(([label, group]) => (
            <div key={label} className="flex items-start gap-2">
              <span
                className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${CATEGORY_COLORS[group.category]?.bg || "bg-zinc-100"} ${CATEGORY_COLORS[group.category]?.text || "text-zinc-600"}`}
              >
                {label}
              </span>
              <div className="flex flex-wrap gap-1">
                {group.tokens.map((token, idx) => {
                  const style = getTokenStyle(token);
                  return (
                    <span
                      key={`${label}-${idx}`}
                      className={`rounded-full border px-2 py-0.5 text-[12px] ${style.bg} ${style.text} ${style.border}`}
                    >
                      {token.startsWith("<lora:") ? (
                        <>
                          <span className="opacity-60">⚡</span>
                          {token.replace(/<lora:|>/g, "")}
                        </>
                      ) : (
                        token
                      )}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        // Linear view (all tokens in order)
        <div className="flex flex-wrap gap-1">
          {(result?.tokens || tokens).map((token, idx) => {
            const style = getTokenStyle(token);
            return (
              <span
                key={idx}
                className={`rounded-full border px-2 py-0.5 text-[12px] ${style.bg} ${style.text} ${style.border}`}
                title={getCategory(token)}
              >
                {token === "BREAK" ? (
                  <span className="font-bold">BREAK</span>
                ) : token.startsWith("<lora:") ? (
                  <>
                    <span className="opacity-60">⚡</span>
                    {token.replace(/<lora:|>/g, "")}
                  </>
                ) : (
                  token
                )}
              </span>
            );
          })}
        </div>
      )}

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
