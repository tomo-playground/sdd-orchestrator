"use client";

import React from "react";
import { FORM_INPUT_COMPACT_CLASSES, FORM_LABEL_COMPACT_CLASSES } from "../ui/variants";

const labelCls = FORM_LABEL_COMPACT_CLASSES;
const inputCls = FORM_INPUT_COMPACT_CLASSES;
const disabledCls =
  "w-full rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs text-zinc-400 cursor-not-allowed";

export { labelCls, inputCls };

/* ── SelectField ── */

export function SelectField({
  label,
  value,
  options,
  onChange,
  placeholder,
  disabled,
  suffix,
}: {
  label: string;
  value: string | number | null;
  options: { value: string | number; label: string }[];
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  suffix?: React.ReactNode;
}) {
  return (
    <div>
      <label className={labelCls}>
        {label}
        {suffix && <> {suffix}</>}
      </label>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={disabled ? disabledCls : inputCls}
        disabled={disabled}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
