"use client";

import { useState, useRef, useEffect } from "react";
import { CheckCircle, RotateCcw, Send, Loader2 } from "lucide-react";
import type { CreativeSceneSummary, ReviewMessage, StepReview } from "../../types/creative";
import QCSummaryCard from "./QCSummaryCard";

type Props = {
  review: StepReview;
  messages: ReviewMessage[];
  sending: boolean;
  onSendMessage: (message: string) => void;
  onAction: (action: "approve" | "revise", feedback?: string) => void;
};

const STEP_LABELS: Record<string, string> = {
  scriptwriter: "대본 리뷰",
  cinematographer: "비주얼 리뷰",
  sound_designer: "사운드 리뷰",
};

const ROLE_STYLES: Record<string, string> = {
  system: "bg-zinc-100 text-zinc-600",
  user: "bg-blue-50 text-blue-700 ml-8",
  agent: "bg-amber-50 text-amber-700 mr-8",
};

const ROLE_LABELS: Record<string, string> = {
  system: "시스템",
  user: "사용자",
  agent: "AI",
};

export default function StepReviewView({
  review,
  messages,
  sending,
  onSendMessage,
  onAction,
}: Props) {
  const [input, setInput] = useState("");
  const [highlightScene, setHighlightScene] = useState<number | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scenes = (review.result?.scenes ?? []) as CreativeSceneSummary[];
  const label = STEP_LABELS[review.step] ?? review.step;

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const handleSend = () => {
    if (!input.trim() || sending) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <p className="text-xs font-semibold tracking-wider text-amber-600">{label}</p>
        <p className="mt-1 text-sm text-amber-800">
          아래 대본을 검토하고 승인 또는 수정을 요청하세요.
        </p>
      </div>

      {/* Scene table */}
      <div className="rounded-xl border border-zinc-200 bg-white p-4">
        <p className="mb-2 text-xs font-semibold tracking-wider text-zinc-400">
          장면 ({scenes.length}개)
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-xs font-semibold tracking-wider text-zinc-400">
                  #
                </th>
                <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-xs font-semibold tracking-wider text-zinc-400">
                  대사
                </th>
                <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-xs font-semibold tracking-wider text-zinc-400">
                  화자
                </th>
                <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-xs font-semibold tracking-wider text-zinc-400">
                  장면 설명
                </th>
                <th className="border-b border-zinc-100 px-3 py-1.5 text-left text-xs font-semibold tracking-wider text-zinc-400">
                  길이
                </th>
              </tr>
            </thead>
            <tbody>
              {scenes.map((s, i) => (
                <tr
                  key={i}
                  className={`border-b border-zinc-50 transition ${
                    highlightScene === s.order ? "bg-amber-50 ring-1 ring-amber-300" : ""
                  }`}
                >
                  <td className="px-3 py-2 font-mono text-xs text-zinc-400">{s.order}</td>
                  <td className="max-w-xs px-3 py-2 text-zinc-700">{s.script}</td>
                  <td className="px-3 py-2 text-zinc-500">{s.speaker}</td>
                  <td className="max-w-xs px-3 py-2 text-zinc-500">
                    {s.image_prompt_ko || "-"}
                  </td>
                  <td className="px-3 py-2 text-zinc-500">{s.duration}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* QC Analysis */}
      {review.qc_analysis && (
        <QCSummaryCard
          analysis={review.qc_analysis}
          onSceneClick={(scene) => setHighlightScene(scene)}
        />
      )}

      {/* Chat messages */}
      <div className="rounded-xl border border-zinc-200 bg-white p-4">
        <p className="mb-2 text-xs font-semibold tracking-wider text-zinc-400">리뷰 채팅</p>
        <div className="max-h-60 space-y-2 overflow-y-auto">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`rounded-lg px-3 py-2 text-sm ${ROLE_STYLES[msg.role] ?? "bg-zinc-50"}`}
            >
              <span className="mr-1.5 text-xs font-bold opacity-60">
                {ROLE_LABELS[msg.role] ?? msg.role}
              </span>
              <span>{msg.content}</span>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="피드백이나 질문을 입력하세요..."
            maxLength={2000}
            className="flex-1 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm focus:border-zinc-400 focus:outline-none"
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="flex items-center gap-1 rounded-lg bg-zinc-700 px-3 py-2 text-sm text-white transition hover:bg-zinc-600 disabled:bg-zinc-300"
          >
            {sending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex justify-end gap-3">
        <button
          onClick={() => {
            const feedback = review.qc_analysis
              ? review.qc_analysis.revision_suggestions.join("\n")
              : undefined;
            onAction("revise", feedback);
          }}
          disabled={sending}
          className="flex items-center gap-1.5 rounded-lg border border-amber-200 bg-white px-4 py-2 text-sm font-semibold text-amber-700 transition hover:bg-amber-50 disabled:opacity-50"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          수정 요청
        </button>
        <button
          onClick={() => onAction("approve")}
          disabled={sending}
          className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
        >
          <CheckCircle className="h-3.5 w-3.5" />
          승인
        </button>
      </div>
    </div>
  );
}
