"use client";

import { useMemo } from "react";
import type { Scene, ImageValidation, SceneContextTags } from "../../types";

type ValidationTabContentProps = {
  scene: Scene;
  validationResult: ImageValidation | undefined;
  isValidating: boolean;
  onValidate: () => void;
  onApplyMissingTags: (tags: string[]) => void;
};

function getContextTagsList(contextTags: SceneContextTags | undefined): string[] {
  if (!contextTags) return [];
  const tags: string[] = [];

  // Helper to safely add tags (filter out non-strings)
  const addTags = (arr: unknown) => {
    if (!Array.isArray(arr)) return;
    arr.forEach((item) => {
      if (typeof item === "string" && item.trim()) {
        tags.push(item);
      }
    });
  };

  addTags(contextTags.expression);
  if (typeof contextTags.gaze === "string" && contextTags.gaze.trim()) {
    tags.push(contextTags.gaze);
  }
  addTags(contextTags.pose);
  addTags(contextTags.action);
  if (typeof contextTags.camera === "string" && contextTags.camera.trim()) {
    tags.push(contextTags.camera);
  }
  addTags(contextTags.environment);
  addTags(contextTags.mood);

  return tags;
}

function normalizeTag(tag: string | unknown): string {
  if (typeof tag !== "string") {
    console.warn("[normalizeTag] Non-string tag:", tag);
    return "";
  }
  return tag.toLowerCase().replace(/_/g, " ").trim();
}

export default function ValidationTabContent({
  scene,
  validationResult,
  isValidating,
  onValidate,
  onApplyMissingTags,
}: ValidationTabContentProps) {
  // Compute intent validation from context_tags
  const intentValidation = useMemo(() => {
    const contextTags = getContextTagsList(scene.context_tags);
    if (contextTags.length === 0 || !validationResult) {
      return null;
    }

    const matchedSet = new Set(
      validationResult.matched
        .map(normalizeTag)
        .filter((tag) => tag.length > 0)
    );
    const extraSet = new Set(
      validationResult.extra
        .map(normalizeTag)
        .filter((tag) => tag.length > 0)
    );
    const allDetected = new Set([...matchedSet, ...extraSet]);

    const matched: string[] = [];
    const missing: string[] = [];

    for (const tag of contextTags) {
      const normalized = normalizeTag(tag);
      if (allDetected.has(normalized)) {
        matched.push(tag);
      } else {
        missing.push(tag);
      }
    }

    const intentRate = contextTags.length > 0 ? matched.length / contextTags.length : 0;

    return { matched, missing, intentRate };
  }, [scene.context_tags, validationResult]);
  return (
    <div className="grid gap-3 rounded-xl border border-zinc-200 bg-white/80 p-4">
      <button
        type="button"
        onClick={onValidate}
        disabled={!scene.image_url || isValidating}
        className="w-full rounded-full border border-zinc-300 bg-white py-2.5 text-[10px] font-semibold tracking-[0.2em] text-zinc-700 uppercase transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isValidating ? "Validating..." : "Run Validation"}
      </button>

      {validationResult && (
        <>
          {/* Match Rate */}
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-zinc-200">
                <div
                  className={`h-full rounded-full transition-all ${
                    validationResult.match_rate >= 0.8
                      ? "bg-emerald-500"
                      : validationResult.match_rate >= 0.5
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }`}
                  style={{
                    width: `${Math.round(validationResult.match_rate * 100)}%`,
                  }}
                />
              </div>
            </div>
            <span
              className={`text-lg font-bold ${
                validationResult.match_rate >= 0.8
                  ? "text-emerald-600"
                  : validationResult.match_rate >= 0.5
                    ? "text-amber-600"
                    : "text-red-600"
              }`}
            >
              {Math.round(validationResult.match_rate * 100)}%
            </span>
          </div>

          {/* Scene Intent Validation */}
          {intentValidation && (
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-[10px] font-semibold text-indigo-600 uppercase">
                  Scene Intent
                </span>
                <span
                  className={`text-sm font-bold ${
                    intentValidation.intentRate >= 0.8
                      ? "text-emerald-600"
                      : intentValidation.intentRate >= 0.5
                        ? "text-amber-600"
                        : "text-red-600"
                  }`}
                >
                  {Math.round(intentValidation.intentRate * 100)}%
                </span>
              </div>
              {intentValidation.matched.length > 0 && (
                <div className="mb-1.5 flex flex-wrap gap-1">
                  {intentValidation.matched.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              {intentValidation.missing.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {intentValidation.missing.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-600"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              {intentValidation.matched.length > 0 && intentValidation.missing.length === 0 && (
                <p className="text-[11px] text-emerald-600">All scene tags detected</p>
              )}
            </div>
          )}

          {/* Missing */}
          {validationResult.missing.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-[10px] font-semibold text-red-600 uppercase">
                  Missing ({validationResult.missing.length})
                </span>
                <button
                  type="button"
                  onClick={() => onApplyMissingTags(validationResult.missing)}
                  className="rounded-full bg-red-500 px-2.5 py-1 text-[9px] font-semibold text-white hover:bg-red-600"
                >
                  + Add
                </button>
              </div>
              <p className="text-xs text-red-700">
                {validationResult.missing.slice(0, 6).join(", ")}
                {validationResult.missing.length > 6 && " ..."}
              </p>
            </div>
          )}

          {/* Extra */}
          {validationResult.extra.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <span className="text-[10px] font-semibold text-amber-600 uppercase">
                Extra ({validationResult.extra.length})
              </span>
              <p className="mt-1 text-xs text-amber-700">
                {validationResult.extra.slice(0, 6).join(", ")}
              </p>
            </div>
          )}

          {/* Success */}
          {validationResult.missing.length === 0 &&
            validationResult.extra.length === 0 && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
                <span className="text-sm font-medium text-emerald-700">Perfect Match</span>
              </div>
            )}
        </>
      )}

      {!validationResult && !scene.image_url && (
        <p className="text-center text-xs text-zinc-400">이미지를 먼저 생성하세요</p>
      )}
      {!validationResult && scene.image_url && (
        <p className="text-center text-xs text-zinc-400">Run Validation을 클릭하세요</p>
      )}
    </div>
  );
}
