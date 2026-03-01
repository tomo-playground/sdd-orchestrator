"use client";

import { useState } from "react";
import { Bot, ChevronDown, ChevronRight, Check, X } from "lucide-react";
import { computeWordDiff, type TextDiffToken } from "../../../utils/textDiff";
import type { SceneEditResult } from "../../../types/chat";
import type { SceneItem } from "../../../hooks/scriptEditor/types";
import Button from "../../ui/Button";

type Props = {
  editResult: SceneEditResult;
  scenes: SceneItem[];
  onAccept: () => void;
  onReject: () => void;
  isApplied: boolean;
};

function DiffTokens({ tokens }: { tokens: TextDiffToken[] }) {
  return (
    <span className="flex flex-wrap gap-0.5">
      {tokens.map((t, i) => (
        <span
          key={i}
          className={
            t.type === "added"
              ? "rounded bg-emerald-100 px-0.5 text-emerald-800"
              : t.type === "removed"
                ? "rounded bg-red-100 px-0.5 text-red-600 line-through"
                : "text-zinc-700"
          }
        >
          {t.text}
        </span>
      ))}
    </span>
  );
}

function SceneDiffSection({
  edited,
  original,
  isOpen,
  onToggle,
}: {
  edited: Props["editResult"]["editedScenes"][number];
  original: SceneItem | undefined;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const changes: { label: string; tokens: TextDiffToken[] }[] = [];
  if (edited.script != null && original) {
    changes.push({
      label: "대사",
      tokens: computeWordDiff(original.script, edited.script ?? ""),
    });
  }
  if (edited.image_prompt != null && original) {
    changes.push({
      label: "비주얼",
      tokens: computeWordDiff(original.image_prompt, edited.image_prompt ?? ""),
    });
  }
  if (edited.speaker != null && original && edited.speaker !== original.speaker) {
    changes.push({
      label: "화자",
      tokens: computeWordDiff(original.speaker, edited.speaker ?? ""),
    });
  }
  if (edited.duration != null && original && edited.duration !== original.duration) {
    changes.push({
      label: "길이",
      tokens: [
        { text: `${original.duration}s`, type: "removed" },
        { text: `${edited.duration}s`, type: "added" },
      ],
    });
  }

  if (changes.length === 0) return null;

  const Chevron = isOpen ? ChevronDown : ChevronRight;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-xs font-medium text-zinc-700 hover:bg-zinc-50"
      >
        <Chevron className="h-3.5 w-3.5" />
        Scene {edited.scene_index + 1}
        <span className="text-zinc-400">— {changes.map((c) => c.label).join(", ")} 변경</span>
      </button>
      {isOpen && (
        <div className="space-y-2 border-t border-zinc-100 px-3 py-2">
          {changes.map((c) => (
            <div key={c.label}>
              <span className="text-[11px] font-medium text-zinc-500">{c.label}</span>
              <div className="mt-0.5 text-xs leading-relaxed">
                <DiffTokens tokens={c.tokens} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SceneEditDiffCard({
  editResult,
  scenes,
  onAccept,
  onReject,
  isApplied,
}: Props) {
  const [openSet, setOpenSet] = useState<Set<number>>(
    () => new Set(editResult.editedScenes.map((s) => s.scene_index))
  );

  const toggle = (idx: number) => {
    setOpenSet((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100">
        <Bot className="h-4 w-4 text-emerald-600" />
      </div>
      <div className="min-w-0 flex-1 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <p className="text-sm font-medium text-emerald-900">수정 제안</p>
        <p className="mt-1 text-xs text-emerald-700">{editResult.reasoning}</p>
        {editResult.unchangedCount > 0 && (
          <p className="mt-1 text-[11px] text-zinc-500">
            {editResult.unchangedCount}개 씬은 변경 없음
          </p>
        )}

        <div className="mt-3 space-y-2">
          {editResult.editedScenes.map((edited) => (
            <SceneDiffSection
              key={edited.scene_index}
              edited={edited}
              original={scenes.find((s) => s.order === edited.scene_index)}
              isOpen={openSet.has(edited.scene_index)}
              onToggle={() => toggle(edited.scene_index)}
            />
          ))}
        </div>

        <div className="mt-3 flex items-center gap-2">
          {isApplied ? (
            <span className="flex items-center gap-1 text-xs font-medium text-emerald-700">
              <Check className="h-3.5 w-3.5" /> 적용됨
            </span>
          ) : (
            <>
              <Button size="sm" variant="success" onClick={onAccept}>
                <Check className="h-3.5 w-3.5" /> 적용
              </Button>
              <Button size="sm" variant="outline" onClick={onReject}>
                <X className="h-3.5 w-3.5" /> 취소
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
