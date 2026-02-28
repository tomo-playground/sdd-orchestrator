"use client";

import { useState } from "react";
import { Bot, Clock, Globe, LayoutList, User, Check } from "lucide-react";
import Button from "../../ui/Button";
import type { ChatMessage, SettingsRecommendation } from "../../../types/chat";

type Props = {
  message: ChatMessage;
  onApply: (rec: SettingsRecommendation) => void;
  onApplyAndGenerate: (rec: SettingsRecommendation) => void;
};

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Clock;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 text-xs text-zinc-600">
      <Icon className="h-3.5 w-3.5 text-zinc-400" />
      <span className="font-medium text-zinc-500">{label}</span>
      <span className="text-zinc-800">{value}</span>
    </div>
  );
}

export default function SettingsRecommendCard({ message, onApply, onApplyAndGenerate }: Props) {
  const [applied, setApplied] = useState(false);
  const rec = message.recommendation;
  if (!rec) return null;

  const handleApply = () => {
    onApply(rec);
    setApplied(true);
  };

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100">
        <Bot className="h-4 w-4 text-violet-600" />
      </div>
      <div className="max-w-[85%] space-y-3 rounded-2xl border border-violet-200 bg-violet-50 p-4">
        {/* Reasoning */}
        <p className="text-sm text-zinc-700">{rec.reasoning}</p>

        {/* Settings grid */}
        <div className="space-y-1.5 rounded-xl bg-white p-3">
          <InfoRow icon={Clock} label="길이" value={`${rec.duration}초`} />
          <InfoRow icon={Globe} label="언어" value={rec.language} />
          <InfoRow icon={LayoutList} label="구성" value={rec.structure} />
          {rec.character_name && <InfoRow icon={User} label="캐릭터" value={rec.character_name} />}
          {rec.character_b_name && (
            <InfoRow icon={User} label="캐릭터 B" value={rec.character_b_name} />
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={applied ? "secondary" : "primary"}
            disabled={applied}
            onClick={handleApply}
          >
            {applied ? (
              <>
                <Check className="h-3.5 w-3.5" />
                반영 완료
              </>
            ) : (
              "사이드바에 반영"
            )}
          </Button>
          {!applied && (
            <Button
              size="sm"
              variant="primary"
              onClick={() => {
                onApplyAndGenerate(rec);
                setApplied(true);
              }}
            >
              반영하고 바로 생성
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
