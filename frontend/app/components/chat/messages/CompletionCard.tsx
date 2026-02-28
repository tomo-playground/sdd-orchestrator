"use client";

import { Bot, CheckCircle, Pencil, Play } from "lucide-react";
import Button from "../../ui/Button";

type Props = {
  text: string;
  sceneCount: number;
  onNavigate: (tab: string) => void;
};

export default function CompletionCard({ text, sceneCount, onNavigate }: Props) {
  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100">
        <CheckCircle className="h-4 w-4 text-emerald-600" />
      </div>
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-emerald-700" />
          <p className="text-sm font-medium text-emerald-900">{text}</p>
        </div>
        <p className="mt-1 text-xs text-emerald-700">{sceneCount}개 씬이 준비되었습니다.</p>
        <div className="mt-3 flex gap-2">
          <Button size="sm" variant="outline" onClick={() => onNavigate("direct")}>
            <Pencil className="h-3.5 w-3.5" />씬 편집하기
          </Button>
          <Button size="sm" variant="success" onClick={() => onNavigate("publish")}>
            <Play className="h-3.5 w-3.5" />
            영상 제작 시작
          </Button>
        </div>
      </div>
    </div>
  );
}
