"use client";
import type { ReactNode } from "react";
import {
  SUCCESS_BG,
  SUCCESS_TEXT,
  SUCCESS_BORDER,
  WARNING_BG,
  WARNING_TEXT,
  WARNING_BORDER,
  ERROR_BG,
  ERROR_TEXT,
  ERROR_BORDER,
} from "../ui/variants";
/** Reusable sub-components for SceneToolsContent right panel. */

/* ---- OverrideToggleRow ---- */

export function OverrideToggleRow({
  label,
  checked,
  hasOverride,
  onChange,
  onReset,
  disabled = false,
  disabledReason,
  tooltip,
}: {
  label: string;
  checked: boolean;
  hasOverride: boolean;
  onChange: (v: boolean) => void;
  onReset: () => void;
  accent?: string;
  disabled?: boolean;
  disabledReason?: string;
  tooltip?: ReactNode;
}) {
  const isOn = disabled ? false : checked;
  return (
    <div className="flex items-center justify-between">
      <span
        className={`text-[13px] font-medium ${disabled ? "text-zinc-300" : "text-zinc-600"}`}
        title={disabled ? disabledReason : undefined}
      >
        {label}
        {tooltip && <span className="ml-1 inline-flex align-middle">{tooltip}</span>}
        {hasOverride && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onReset();
            }}
            className="ml-1 inline-flex items-center rounded bg-blue-100 px-1 text-[11px] font-bold text-blue-600 hover:bg-blue-200"
            title="씬 오버라이드 활성. 클릭하면 글로벌 값으로 복원"
          >
            Scene
          </button>
        )}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={isOn}
        onClick={() => !disabled && onChange(!isOn)}
        disabled={disabled}
        className={`relative inline-flex h-4 w-7 shrink-0 items-center rounded-full transition-colors ${
          disabled ? "cursor-not-allowed opacity-30" : "cursor-pointer"
        } ${isOn ? "bg-zinc-900" : "bg-zinc-200"}`}
      >
        <span
          className={`inline-block h-3 w-3 rounded-full bg-white shadow transition-transform ${
            isOn ? "translate-x-3.5" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}

/* ---- SliderRow ---- */

export function SliderRow({
  value,
  onChange,
  min,
  max,
  step,
}: {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  accent?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="h-1 flex-1 accent-zinc-600"
      />
      <span className="w-8 text-right text-[12px] font-semibold text-zinc-600">
        {value.toFixed(step < 0.1 ? 2 : 1)}
      </span>
    </div>
  );
}

/* ---- StatBadge ---- */

const STAT_BADGE_COLORS = {
  emerald: `${SUCCESS_BORDER} ${SUCCESS_BG} ${SUCCESS_TEXT} [&>:last-child]:${SUCCESS_TEXT}`,
  amber: `${WARNING_BORDER} ${WARNING_BG} ${WARNING_TEXT} [&>:last-child]:${WARNING_TEXT}`,
  rose: `${ERROR_BORDER} ${ERROR_BG} ${ERROR_TEXT} [&>:last-child]:${ERROR_TEXT}`,
} as const;

export function StatBadge({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: keyof typeof STAT_BADGE_COLORS;
}) {
  return (
    <div
      className={`flex flex-col items-center rounded-lg border px-2 py-1.5 ${STAT_BADGE_COLORS[color]}`}
    >
      <span className="text-xs font-bold">{count}</span>
      <span className="text-[11px]">{label}</span>
    </div>
  );
}
