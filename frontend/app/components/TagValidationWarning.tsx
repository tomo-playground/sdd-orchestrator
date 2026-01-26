/**
 * Tag Validation Warning Component
 *
 * Displays warnings for risky/unknown tags detected during prompt validation.
 * Shows suggestions for safer alternatives and allows auto-replacement.
 */

import React from "react";

export type TagWarning = {
  tag: string;
  reason: string;
  suggestion: string | null;
};

export type TagValidationResult = {
  valid: string[];
  risky: string[];
  unknown: string[];
  warnings: TagWarning[];
  total_tags: number;
  valid_count: number;
  risky_count: number;
  unknown_count: number;
};

type TagValidationWarningProps = {
  result: TagValidationResult | null;
  onAutoReplace?: () => void;
  onDismiss?: () => void;
};

export default function TagValidationWarning({
  result,
  onAutoReplace,
  onDismiss,
}: TagValidationWarningProps) {
  if (!result || result.warnings.length === 0) {
    return null;
  }

  const hasRisky = result.risky_count > 0;
  const hasUnknown = result.unknown_count > 0;

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 mb-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">⚠️</span>
          <div>
            <h3 className="font-semibold text-amber-900">
              Tag Validation Warnings
            </h3>
            <p className="text-sm text-amber-700">
              {hasRisky && `${result.risky_count} risky tag(s)`}
              {hasRisky && hasUnknown && ", "}
              {hasUnknown && `${result.unknown_count} unknown tag(s)`}
            </p>
          </div>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-amber-600 hover:text-amber-800"
            aria-label="Dismiss"
          >
            ✕
          </button>
        )}
      </div>

      {/* Warning List */}
      <div className="space-y-2 mb-3">
        {result.warnings.map((warning, idx) => (
          <div
            key={idx}
            className="flex items-start gap-2 p-2 bg-white rounded border border-amber-200"
          >
            <span className="text-xs font-mono bg-amber-100 px-2 py-1 rounded">
              {warning.tag}
            </span>
            <div className="flex-1 text-sm">
              <p className="text-amber-800">{warning.reason}</p>
              {warning.suggestion && (
                <p className="text-emerald-700 mt-1">
                  → Suggested:{" "}
                  <span className="font-mono font-semibold">
                    {warning.suggestion}
                  </span>
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      {onAutoReplace && (
        <div className="flex gap-2">
          <button
            onClick={onAutoReplace}
            className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 text-sm font-medium"
          >
            Auto-Replace Risky Tags
          </button>
          <p className="text-xs text-amber-600 self-center">
            Automatically replace problematic tags with safe alternatives
          </p>
        </div>
      )}
    </div>
  );
}
