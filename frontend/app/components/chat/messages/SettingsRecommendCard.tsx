"use client";

import { useState } from "react";
import { Bot, Check, ChevronDown, Sparkles } from "lucide-react";
import Button from "../../ui/Button";
import type { ChatMessage, SettingsRecommendation } from "../../../types/chat";

type Props = {
  message: ChatMessage;
  onApplyAndGenerate: (rec: SettingsRecommendation) => void;
};

const selectClass =
  "appearance-none rounded-lg border border-zinc-200 bg-white pl-2 pr-6 py-1 text-sm text-zinc-800 " +
  "outline-none cursor-pointer hover:border-violet-300 focus:border-violet-400 focus:ring-1 focus:ring-violet-400";

const DIALOGUE_STRUCTURES = new Set(["Dialogue", "Narrated Dialogue"]);

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
          <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 text-zinc-400" />
        )}
      </span>
    </li>
  );
}

export default function SettingsRecommendCard({ message, onApplyAndGenerate }: Props) {
  const rec = message.recommendation;
  if (!rec) return null;

  const opts = rec.available_options;
  const [local, setLocal] = useState({
    structure: rec.structure,
    duration: rec.duration,
    language: rec.language,
    character_id: rec.character_id,
    character_b_id: rec.character_b_id,
  });
  const [applied, setApplied] = useState(false);

  const patch = <K extends keyof typeof local>(key: K, val: (typeof local)[K]) =>
    setLocal((prev) => ({ ...prev, [key]: val }));

  const isDialogue = DIALOGUE_STRUCTURES.has(local.structure);

  const buildRec = (): SettingsRecommendation => {
    const charName =
      opts?.characters.find((c) => c.id === local.character_id)?.name ?? rec.character_name;
    const charBName =
      opts?.characters.find((c) => c.id === local.character_b_id)?.name ?? rec.character_b_name;
    return {
      ...rec,
      ...local,
      character_name: charName,
      character_b_id: isDialogue ? local.character_b_id : null,
      character_b_name: isDialogue ? charBName : null,
    };
  };

  const handleGenerate = () => {
    onApplyAndGenerate(buildRec());
    setApplied(true);
  };

  // 옵션 목록 구성
  const structureOpts = opts?.structures ?? [{ value: rec.structure, label: rec.structure }];
  const durationOpts: { value: string; label: string }[] =
    opts?.durations.map((d) => ({
      value: String(d),
      label: `${d}초`,
    })) ?? [{ value: String(rec.duration), label: `${rec.duration}초` }];
  const languageOpts = opts?.languages ?? [{ value: rec.language, label: rec.language }];
  const characterOpts: { value: string; label: string }[] = [
    { value: "", label: "미정" },
    ...(opts?.characters.map((c) => ({ value: String(c.id), label: c.name })) ?? []),
  ];

  // character_b: character_a와 다른 캐릭터만 표시
  const characterBOpts = characterOpts.filter(
    (o) => o.value === "" || o.value !== String(local.character_id ?? "")
  );

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[85%] space-y-3 rounded-2xl border border-violet-200 bg-violet-50 p-4">
        {rec.reasoning && <p className="text-sm text-zinc-700">{rec.reasoning}</p>}

        <ul className="space-y-2 rounded-xl bg-white p-3 text-sm text-zinc-700">
          <InlineSelect
            label="구성"
            value={local.structure}
            options={structureOpts}
            onChange={(v) => patch("structure", v)}
            disabled={applied}
          />
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
          <InlineSelect
            label="캐릭터"
            value={String(local.character_id ?? "")}
            options={characterOpts}
            onChange={(v) => patch("character_id", v ? Number(v) : null)}
            disabled={applied}
          />
          {isDialogue && (
            <InlineSelect
              label="캐릭터B"
              value={String(local.character_b_id ?? "")}
              options={characterBOpts}
              onChange={(v) => patch("character_b_id", v ? Number(v) : null)}
              disabled={applied}
            />
          )}
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
