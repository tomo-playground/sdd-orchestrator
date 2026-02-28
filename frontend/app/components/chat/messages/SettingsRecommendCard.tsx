"use client";

import { useState } from "react";
import { Bot, Check, Sparkles } from "lucide-react";
import { useCharacters } from "../../../hooks/useCharacters";
import { isMultiCharStructure } from "../../../utils/structure";
import ModeChips from "../ModeChips";
import Button from "../../ui/Button";
import type { ChatMessage, SettingsRecommendation } from "../../../types/chat";
import type { Preset, LangOption } from "../../../hooks/usePresets";
import type { ScriptMode } from "../ModeChips";

type Props = {
  message: ChatMessage;
  onApplyAndGenerate: (rec: SettingsRecommendation) => void;
  presets: Preset[];
  languages: LangOption[];
  durations: number[];
  currentMode: ScriptMode;
  onPresetChange: (preset: string, skipStages: string[]) => void;
};

const SELECT_CLS =
  "w-full rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-zinc-400";

function EditRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-16 shrink-0 text-xs font-medium text-zinc-500">{label}</span>
      <div className="flex-1">{children}</div>
    </div>
  );
}

export default function SettingsRecommendCard({
  message,
  onApplyAndGenerate,
  presets,
  languages,
  durations,
  currentMode,
  onPresetChange,
}: Props) {
  const rec = message.recommendation;
  const { characters } = useCharacters();

  const [applied, setApplied] = useState(false);
  const [localDuration, setLocalDuration] = useState(rec?.duration ?? 30);
  const [localLanguage, setLocalLanguage] = useState(rec?.language ?? "ko");
  const [localStructure, setLocalStructure] = useState(rec?.structure ?? "Monologue");
  const [localCharId, setLocalCharId] = useState<number | null>(rec?.character_id ?? null);
  const [localCharBId, setLocalCharBId] = useState<number | null>(rec?.character_b_id ?? null);

  if (!rec) return null;

  const charName = (id: number | null) => characters.find((c) => c.id === id)?.name ?? null;
  const isMultiChar = isMultiCharStructure(localStructure);

  const handleGenerate = () => {
    const merged: SettingsRecommendation = {
      ...rec,
      duration: localDuration,
      language: localLanguage,
      structure: localStructure,
      character_id: localCharId,
      character_name: charName(localCharId),
      character_b_id: isMultiChar ? localCharBId : null,
      character_b_name: isMultiChar ? charName(localCharBId) : null,
    };
    onApplyAndGenerate(merged);
    setApplied(true);
  };

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[85%] space-y-3 rounded-2xl border border-violet-200 bg-violet-50 p-4">
        <p className="text-sm text-zinc-700">{rec.reasoning}</p>

        <div className="space-y-2.5 rounded-xl bg-white p-3">
          <EditRow label="길이">
            <select
              value={localDuration}
              onChange={(e) => setLocalDuration(Number(e.target.value))}
              disabled={applied}
              className={SELECT_CLS}
            >
              {durations.map((d) => (
                <option key={d} value={d}>
                  {d}초
                </option>
              ))}
            </select>
          </EditRow>

          <EditRow label="언어">
            <select
              value={localLanguage}
              onChange={(e) => setLocalLanguage(e.target.value)}
              disabled={applied}
              className={SELECT_CLS}
            >
              {languages.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </EditRow>

          <EditRow label="구성">
            <select
              value={localStructure}
              onChange={(e) => {
                setLocalStructure(e.target.value);
                if (!isMultiCharStructure(e.target.value)) setLocalCharBId(null);
              }}
              disabled={applied}
              className={SELECT_CLS}
            >
              {presets.map((p) => (
                <option key={p.structure} value={p.structure}>
                  {p.name_ko}
                </option>
              ))}
            </select>
          </EditRow>

          <EditRow label="캐릭터">
            <select
              value={localCharId ?? ""}
              onChange={(e) => setLocalCharId(e.target.value ? Number(e.target.value) : null)}
              disabled={applied}
              className={SELECT_CLS}
            >
              <option value="">None</option>
              {characters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </EditRow>

          {isMultiChar && (
            <EditRow label="캐릭터 B">
              <select
                value={localCharBId ?? ""}
                onChange={(e) => setLocalCharBId(e.target.value ? Number(e.target.value) : null)}
                disabled={applied}
                className={SELECT_CLS}
              >
                <option value="">None</option>
                {characters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </EditRow>
          )}

          <EditRow label="모드">
            <ModeChips currentMode={currentMode} onPresetChange={onPresetChange} compact />
          </EditRow>
        </div>

        <Button
          size="sm"
          variant={applied ? "secondary" : "primary"}
          className="w-full"
          disabled={applied}
          onClick={handleGenerate}
        >
          {applied ? (
            <>
              <Check className="h-3.5 w-3.5" />
              생성 시작됨
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5" />
              스크립트 생성
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
