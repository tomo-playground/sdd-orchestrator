"use client";

import { useState, useEffect } from "react";
import { Bot, Check, ChevronDown, Sparkles } from "lucide-react";
import Button from "../../ui/Button";
import type { SettingsRecommendMessage, SettingsRecommendation } from "../../../types/chat";

type Props = {
  message: SettingsRecommendMessage;
  onApplyAndGenerate: (rec: SettingsRecommendation) => void;
  /** 생성 실패 시 true → 버튼 재활성화 */
  hasError?: boolean;
};

const selectClass =
  "appearance-none rounded-lg border border-zinc-200 bg-white pl-2 pr-6 py-1 text-sm text-zinc-800 " +
  "outline-none cursor-pointer hover:border-violet-300 focus:border-violet-400 focus:ring-1 focus:ring-violet-400";

function InlineSelect({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled: boolean;
}) {
  return (
    <li className="flex items-center gap-2">
      <span className="w-16 shrink-0 font-medium text-zinc-500">{label}</span>
      <span className="relative inline-block">
        <select
          className={selectClass}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        {!disabled && (
          <ChevronDown className="pointer-events-none absolute top-1/2 right-1.5 h-3 w-3 -translate-y-1/2 text-zinc-400" />
        )}
      </span>
    </li>
  );
}

export default function SettingsRecommendCard({ message, onApplyAndGenerate, hasError }: Props) {
  const rec = message.recommendation;
  const opts = rec.available_options;
  const [local, setLocal] = useState({
    duration: rec.duration,
    language: rec.language,
  });
  const [applied, setApplied] = useState(false);

  // 생성 실패 시 버튼 재활성화
  useEffect(() => {
    if (hasError && applied) setApplied(false);
  }, [hasError, applied]);

  const patch = <K extends keyof typeof local>(key: K, val: (typeof local)[K]) =>
    setLocal((prev) => ({ ...prev, [key]: val }));

  const buildRec = (): SettingsRecommendation => ({
    ...rec,
    ...local,
  });

  const handleGenerate = () => {
    onApplyAndGenerate(buildRec());
    setApplied(true);
  };

  // 옵션 목록 구성 (구성/캐릭터는 Director SSOT → 여기서 표시하지 않음)
  const durationOpts: { value: string; label: string }[] = opts?.durations.map((d) => ({
    value: String(d),
    label: `${d}초`,
  })) ?? [{ value: String(rec.duration), label: `${rec.duration}초` }];
  const languageOpts = opts?.languages ?? [{ value: rec.language, label: rec.language }];

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[85%] space-y-3 rounded-2xl border border-violet-200 bg-violet-50 p-4">
        {rec.reasoning && <p className="text-sm text-zinc-700">{rec.reasoning}</p>}

        <ul className="space-y-2 rounded-xl bg-white p-3 text-sm text-zinc-700">
          <InlineSelect
            label="길이"
            value={String(local.duration)}
            options={durationOpts}
            onChange={(v) => patch("duration", Number(v))}
            disabled={applied}
          />
          <InlineSelect
            label="언어"
            value={local.language}
            options={languageOpts}
            onChange={(v) => patch("language", v)}
            disabled={applied}
          />
        </ul>

        {!applied ? (
          <Button size="sm" variant="primary" className="w-full" onClick={handleGenerate}>
            <Sparkles className="h-3.5 w-3.5" />
            스크립트 생성
          </Button>
        ) : (
          <Button size="sm" variant="secondary" className="w-full" disabled>
            <Check className="h-3.5 w-3.5" />
            생성 시작됨
          </Button>
        )}
      </div>
    </div>
  );
}
