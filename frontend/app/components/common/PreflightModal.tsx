"use client";

import React, { useState } from "react";
import type { PreflightResult, AutoRunStepId } from "../../utils/preflight";
import { estimateTime, getStepsToExecute } from "../../utils/preflight";

interface PreflightModalProps {
  isOpen: boolean;
  preflight: PreflightResult;
  onClose: () => void;
  onRun: (stepsToRun: AutoRunStepId[]) => void;
}

const STEP_LABELS: Record<AutoRunStepId, string> = {
  storyboard: "Storyboard",
  fix: "Auto Fix",
  images: "Images",
  validate: "Validate",
  render: "Render",
};

export default function PreflightModal({
  isOpen,
  preflight,
  onClose,
  onRun,
}: PreflightModalProps) {
  // User can override step selection
  const [stepOverrides, setStepOverrides] = useState<
    Partial<Record<AutoRunStepId, boolean>>
  >({});

  if (!isOpen) return null;

  const toggleStep = (stepId: AutoRunStepId) => {
    setStepOverrides((prev) => ({
      ...prev,
      [stepId]: prev[stepId] === undefined
        ? !preflight.steps[stepId].needed
        : !prev[stepId],
    }));
  };

  const isStepEnabled = (stepId: AutoRunStepId): boolean => {
    if (stepId in stepOverrides) {
      return stepOverrides[stepId]!;
    }
    return preflight.steps[stepId].needed;
  };

  const stepsToRun = getStepsToExecute(preflight, stepOverrides);
  const hasStepsToRun = stepsToRun.length > 0;

  const handleRun = () => {
    onRun(stepsToRun);
  };

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <span>🚀</span>
            <span>AutoRun Pre-flight Check</span>
          </h2>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto max-h-[60vh] space-y-4">
          {/* Errors */}
          {preflight.errors.length > 0 && (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-3">
              <div className="text-red-700 dark:text-red-300 font-medium mb-1">
                ❌ 실행 불가 - 필수 설정 누락
              </div>
              <ul className="text-sm text-red-600 dark:text-red-400 space-y-1">
                {preflight.errors.map((err, i) => (
                  <li key={i}>• {err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {preflight.warnings.length > 0 && (
            <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
              <ul className="text-sm text-yellow-700 dark:text-yellow-400 space-y-1">
                {preflight.warnings.map((warn, i) => (
                  <li key={i}>⚠️ {warn}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Settings Section */}
          <div>
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              📋 설정 검증
            </h3>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg divide-y divide-gray-200 dark:divide-gray-600">
              <SettingRow
                label="Character"
                check={preflight.settings.character}
              />
              <SettingRow label="Topic" check={preflight.settings.topic} />
              <SettingRow label="Voice" check={preflight.settings.voice} />
              <SettingRow label="BGM" check={preflight.settings.bgm} />
              <SettingRow
                label="ControlNet"
                check={preflight.settings.controlnet}
              />
              <SettingRow
                label="IP-Adapter"
                check={preflight.settings.ipAdapter}
              />
            </div>
          </div>

          {/* SD Parameters Section */}
          <div>
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              🔧 SD 파라미터
            </h3>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <div className="flex flex-wrap gap-3 text-sm">
                <span className="px-2 py-1 bg-white dark:bg-gray-600 rounded">
                  Steps: {preflight.sdParams.steps}
                </span>
                <span className="px-2 py-1 bg-white dark:bg-gray-600 rounded">
                  CFG: {preflight.sdParams.cfgScale}
                </span>
                <span className="px-2 py-1 bg-white dark:bg-gray-600 rounded">
                  Sampler: {preflight.sdParams.sampler}
                </span>
                <span className="px-2 py-1 bg-white dark:bg-gray-600 rounded">
                  Seed: {preflight.sdParams.seed === -1 ? "랜덤" : preflight.sdParams.seed}
                </span>
                <span className="px-2 py-1 bg-white dark:bg-gray-600 rounded">
                  Clip Skip: {preflight.sdParams.clipSkip}
                </span>
              </div>
            </div>
          </div>

          {/* Steps Section */}
          <div>
            <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              📌 실행 단계
            </h3>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg divide-y divide-gray-200 dark:divide-gray-600">
              {(Object.keys(STEP_LABELS) as AutoRunStepId[]).map((stepId) => (
                <StepRow
                  key={stepId}
                  stepId={stepId}
                  label={STEP_LABELS[stepId]}
                  check={preflight.steps[stepId]}
                  enabled={isStepEnabled(stepId)}
                  onToggle={() => toggleStep(stepId)}
                  disabled={!preflight.canRun}
                />
              ))}
            </div>
          </div>

          {/* Estimated Time */}
          {hasStepsToRun && preflight.canRun && (
            <div className="text-sm text-gray-500 dark:text-gray-400">
              예상 시간: {estimateTime({
                ...preflight,
                steps: {
                  storyboard: { ...preflight.steps.storyboard, needed: isStepEnabled("storyboard") },
                  fix: { ...preflight.steps.fix, needed: isStepEnabled("fix") },
                  images: { ...preflight.steps.images, needed: isStepEnabled("images") },
                  validate: { ...preflight.steps.validate, needed: isStepEnabled("validate") },
                  render: { ...preflight.steps.render, needed: isStepEnabled("render") },
                },
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            취소
          </button>
          <button
            onClick={handleRun}
            disabled={!preflight.canRun || !hasStepsToRun}
            className={`px-6 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${preflight.canRun && hasStepsToRun
                ? "bg-blue-600 hover:bg-blue-700 text-white"
                : "bg-gray-300 dark:bg-gray-600 text-gray-500 cursor-not-allowed"
              }`}
          >
            <span>▶</span>
            <span>실행 ({stepsToRun.length}단계)</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Sub-components
// ============================================================

function SettingRow({
  label,
  check,
}: {
  label: string;
  check: { valid: boolean; value: string | null; required: boolean; message?: string };
}) {
  const icon = check.valid ? "✓" : check.required ? "❌" : "⚠";
  const iconColor = check.valid
    ? "text-green-500"
    : check.required
      ? "text-red-500"
      : "text-yellow-500";

  return (
    <div className="flex items-center justify-between px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span className={iconColor}>{icon}</span>
        <span className="text-gray-700 dark:text-gray-300">{label}</span>
      </div>
      <div className="text-gray-500 dark:text-gray-400 text-right">
        {check.value || check.message || "-"}
      </div>
    </div>
  );
}

function StepRow({
  label,
  check,
  enabled,
  onToggle,
  disabled,
}: {
  stepId: AutoRunStepId;
  label: string;
  check: { needed: boolean; reason: string; count?: number };
  enabled: boolean;
  onToggle: () => void;
  disabled: boolean;
}) {
  return (
    <div className="flex items-center justify-between px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={enabled}
          onChange={onToggle}
          disabled={disabled}
          className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
        />
        <span className="text-gray-700 dark:text-gray-300">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        {check.count !== undefined && (
          <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs rounded-full">
            {check.count}개
          </span>
        )}
        <span
          className={`text-xs ${check.needed
              ? "text-blue-600 dark:text-blue-400"
              : "text-gray-400 dark:text-gray-500"
            }`}
        >
          {check.needed ? check.reason : `✓ ${check.reason}`}
        </span>
      </div>
    </div>
  );
}
