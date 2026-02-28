"use client";

import React from "react";
import type { ChannelDNA } from "../../types";
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

/* ── DnaField ── */

export type DnaFieldDef = {
  field: keyof ChannelDNA;
  label: string;
  placeholder: string;
  rows: number;
};

export const DNA_FIELDS: DnaFieldDef[] = [
  { field: "tone", label: "Tone", placeholder: "e.g. warm and nostalgic, dark humor", rows: 2 },
  {
    field: "target_audience",
    label: "Target Audience",
    placeholder: "e.g. teens 13-18, anime fans",
    rows: 2,
  },
  {
    field: "worldview",
    label: "Worldview",
    placeholder: "e.g. A fantasy world where magic and technology coexist",
    rows: 3,
  },
  {
    field: "guidelines",
    label: "Guidelines",
    placeholder: "e.g. No violence, keep stories under 60s",
    rows: 3,
  },
];

export function DnaField({
  label,
  value,
  placeholder,
  rows,
  onChange,
}: Omit<DnaFieldDef, "field"> & { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className={labelCls}>{label}</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className={inputCls}
      />
    </div>
  );
}
