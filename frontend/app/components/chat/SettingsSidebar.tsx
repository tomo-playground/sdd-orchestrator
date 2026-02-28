"use client";

import { Loader2, Sparkles } from "lucide-react";
import CharacterSelectSection from "../scripts/CharacterSelectSection";
import Button from "../ui/Button";
import { FORM_INPUT_CLASSES, TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";
import { EXPRESS_SKIP_STAGES } from "../../utils/pipelineSteps";
import type { ScriptEditorActions } from "../../hooks/useScriptEditor";
import type { Preset, LangOption } from "../../hooks/usePresets";

type Props = {
  editor: ScriptEditorActions;
  presets: Preset[];
  languages: LangOption[];
  durations: number[];
  onPresetChange: (preset: string, skipStages: string[]) => void;
  onGenerate: () => void;
};

const H3 = "mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-400";
const TAB_BASE = "px-3 py-1.5 text-xs font-semibold rounded-lg transition flex-1";
const MODES = ["express", "standard", "creator"] as const;
const MODE_LABELS: Record<string, string> = {
  express: "Express",
  standard: "Standard",
  creator: "Creator",
};

function isActiveMode(mode: string, e: ScriptEditorActions) {
  if (mode === "express") return e.skipStages.length > 0;
  if (mode === "creator") return e.skipStages.length === 0 && e.preset === "creator";
  return e.skipStages.length === 0 && e.preset !== "creator";
}

function Select<T extends { key: string; label: string }>({
  value,
  onChange,
  items,
}: {
  value: string | number;
  onChange: (v: string) => void;
  items: T[];
}) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={FORM_INPUT_CLASSES}>
      {items.map((i) => (
        <option key={i.key} value={i.key}>
          {i.label}
        </option>
      ))}
    </select>
  );
}

export default function SettingsSidebar({
  editor,
  presets,
  languages,
  durations,
  onPresetChange,
  onGenerate,
}: Props) {
  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-zinc-200 bg-zinc-50/50">
      <div className="flex-1 space-y-5 overflow-y-auto p-4">
        <div>
          <h3 className={H3}>Video</h3>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-[12px] font-medium text-zinc-500">영상 길이</label>
              <Select
                value={editor.duration}
                onChange={(v) => editor.setField("duration", Number(v))}
                items={durations.map((d) => ({ key: String(d), label: `${d}s` }))}
              />
            </div>
            <div>
              <label className="mb-1 block text-[12px] font-medium text-zinc-500">언어</label>
              <Select
                value={editor.language}
                onChange={(v) => editor.setField("language", v)}
                items={languages.map((l) => ({ key: l.value, label: l.label }))}
              />
            </div>
            <div>
              <label className="mb-1 block text-[12px] font-medium text-zinc-500">스토리 구조</label>
              <Select
                value={editor.structure}
                onChange={(v) => editor.setField("structure", v)}
                items={presets.map((p) => ({ key: p.structure, label: p.name_ko }))}
              />
            </div>
          </div>
        </div>
        <div>
          <h3 className={H3}>Character</h3>
          <CharacterSelectSection
            embedded
            structure={editor.structure}
            characterId={editor.characterId}
            characterBId={editor.characterBId}
            onChangeA={(id, name) => {
              editor.setField("characterId", id);
              editor.setField("characterName", name);
            }}
            onChangeB={(id, name) => {
              editor.setField("characterBId", id);
              editor.setField("characterBName", name);
            }}
          />
        </div>
        <div>
          <h3 className={H3}>Mode</h3>
          <div className="flex gap-1 rounded-xl bg-zinc-100 p-1">
            {MODES.map((m) => (
              <button
                key={m}
                className={`${TAB_BASE} ${isActiveMode(m, editor) ? TAB_ACTIVE : TAB_INACTIVE}`}
                onClick={() => onPresetChange(m, m === "express" ? [...EXPRESS_SKIP_STAGES] : [])}
              >
                {MODE_LABELS[m]}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-[11px] text-zinc-400">
            {isActiveMode("express", editor)
              ? "빠른 생성"
              : isActiveMode("creator", editor)
                ? "컨셉 직접 선택"
                : "리서치 + 검증 포함"}
          </p>
        </div>
      </div>
      <div className="border-t border-zinc-200 p-4">
        <Button
          size="md"
          variant="primary"
          className="w-full"
          disabled={!editor.topic.trim() || editor.isGenerating}
          onClick={onGenerate}
        >
          {editor.isGenerating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {editor.isGenerating ? editor.progress?.label || "생성 중..." : "스크립트 생성"}
        </Button>
      </div>
    </aside>
  );
}
