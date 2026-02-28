"use client";

import { EXPRESS_SKIP_STAGES } from "../../utils/pipelineSteps";
import { TAB_ACTIVE, TAB_INACTIVE } from "../ui/variants";

const MODES = ["express", "standard", "creator"] as const;
export type ScriptMode = (typeof MODES)[number];

type Props = {
  currentMode: ScriptMode;
  onPresetChange: (preset: string, skipStages: string[]) => void;
  compact?: boolean;
};
const MODE_LABELS: Record<string, string> = {
  express: "Express",
  standard: "Standard",
  creator: "Creator",
};
const MODE_DESC: Record<string, string> = {
  express: "빠른 생성",
  standard: "리서치 + 검증 포함",
  creator: "컨셉 직접 선택",
};

const TAB_BASE = "px-3 py-1.5 text-xs font-semibold rounded-lg transition flex-1";

export default function ModeChips({ currentMode, onPresetChange, compact }: Props) {
  return (
    <div>
      <div className="flex gap-1 rounded-xl bg-zinc-100 p-1">
        {MODES.map((m) => (
          <button
            key={m}
            className={`${TAB_BASE} ${currentMode === m ? TAB_ACTIVE : TAB_INACTIVE}`}
            onClick={() => onPresetChange(m, m === "express" ? [...EXPRESS_SKIP_STAGES] : [])}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>
      {!compact && <p className="mt-1.5 text-[11px] text-zinc-400">{MODE_DESC[currentMode]}</p>}
    </div>
  );
}
