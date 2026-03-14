import { useState, useEffect, useRef, type InputHTMLAttributes } from "react";
import type { StyleProfileFull } from "../../../types";

const DEBOUNCE_MS = 400;

const numInputCls =
  "w-full rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1.5 text-xs text-zinc-700 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100";

/** Input that keeps local state and debounces onChange calls. */
export function DebouncedInput({
  value: externalValue,
  onDebouncedChange,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, "onChange"> & {
  value: string;
  onDebouncedChange: (v: string) => void;
}) {
  const [local, setLocal] = useState(externalValue);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    setLocal(externalValue);
  }, [externalValue]);
  useEffect(() => () => clearTimeout(timerRef.current), []);
  return (
    <input
      {...props}
      value={local}
      onChange={(e) => {
        setLocal(e.target.value);
        clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => onDebouncedChange(e.target.value), DEBOUNCE_MS);
      }}
    />
  );
}

type Props = {
  profile: StyleProfileFull;
  onUpdateStyle: (id: number, data: Record<string, unknown>) => void;
  labelCls: string;
};

export default function GenerationParameters({ profile, onUpdateStyle, labelCls }: Props) {
  return (
    <div className="mt-6 space-y-2">
      <label className={labelCls}>Generation Parameters</label>
      <p className="text-[11px] text-zinc-400">
        Override global defaults per style. Leave empty to use system defaults.
      </p>
      <div className="grid gap-3 sm:grid-cols-4">
        <div className="space-y-1">
          <label className="text-[11px] font-medium text-zinc-500">Steps</label>
          <input
            type="number"
            min={1}
            max={100}
            value={profile.default_steps ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              onUpdateStyle(profile.id, { default_steps: v ? Number(v) : null });
            }}
            placeholder="28"
            className={numInputCls}
          />
        </div>
        <div className="space-y-1">
          <label className="text-[11px] font-medium text-zinc-500">CFG Scale</label>
          <input
            type="number"
            min={0}
            max={30}
            step={0.5}
            value={profile.default_cfg_scale ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              onUpdateStyle(profile.id, { default_cfg_scale: v ? Number(v) : null });
            }}
            placeholder="4.5"
            className={numInputCls}
          />
        </div>
        <div className="space-y-1">
          <label className="text-[11px] font-medium text-zinc-500">Sampler</label>
          <DebouncedInput
            type="text"
            value={profile.default_sampler_name || ""}
            onDebouncedChange={(v) =>
              onUpdateStyle(profile.id, { default_sampler_name: v || null })
            }
            placeholder="Euler"
            className={numInputCls}
          />
        </div>
        <div className="space-y-1">
          <label className="text-[11px] font-medium text-zinc-500">CLIP Skip</label>
          <input
            type="number"
            min={1}
            max={4}
            value={profile.default_clip_skip ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              onUpdateStyle(profile.id, { default_clip_skip: v ? Number(v) : null });
            }}
            placeholder="2"
            className={numInputCls}
          />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-1.5">
          <input
            type="checkbox"
            checked={profile.default_enable_hr ?? false}
            onChange={(e) =>
              onUpdateStyle(profile.id, { default_enable_hr: e.target.checked || null })
            }
            className="h-3.5 w-3.5 rounded accent-indigo-600"
          />
          <span className="text-xs font-medium text-zinc-600">Hi-Res (Hires Fix)</span>
        </label>
        <span className="text-[11px] text-zinc-400">
          Auto-enable upscaling for this style (SDXL 832&times;1216 base)
        </span>
      </div>
    </div>
  );
}
