"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import {
  CinematographerSection,
  TtsDesignerSection,
  SoundDesignerSection,
  CopyrightReviewerSection,
} from "../reasoning/ProductionSections";
import SnapshotSummaryHeader from "./SnapshotSummaryHeader";
import RevisionHistorySection from "./RevisionHistorySection";
import AgentMessagesSection from "./AgentMessagesSection";
import type { ProductionSnapshot } from "../../../types";

type Props = {
  snapshot: ProductionSnapshot;
};

type AccordionItem = {
  key: string;
  label: string;
  content: React.ReactNode;
};

const DECISION_COLORS: Record<string, string> = {
  APPROVED: "bg-emerald-100 text-emerald-700",
  REVISE: "bg-amber-100 text-amber-700",
  REJECT: "bg-red-100 text-red-700",
};

function DirectorDecisionSection({ data }: { data: NonNullable<ProductionSnapshot["director"]> }) {
  const colorCls = DECISION_COLORS[data.decision ?? ""] ?? "bg-zinc-100 text-zinc-700";

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {data.decision && (
          <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${colorCls}`}>
            {data.decision}
          </span>
        )}
      </div>
      {data.feedback && (
        <p className="text-[11px] leading-relaxed text-zinc-600">{data.feedback}</p>
      )}
      {data.reasoning_steps && data.reasoning_steps.length > 0 && (
        <div className="space-y-1">
          {data.reasoning_steps.map((step, i) => (
            <div key={i} className="rounded bg-zinc-50 px-2 py-1.5">
              {"agent" in step && step.agent != null && (
                <span className="text-[11px] font-medium text-zinc-500">{String(step.agent)}</span>
              )}
              {"message" in step && step.message != null && (
                <p className="text-[11px] text-zinc-500">{String(step.message)}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** DebateLog를 범용 렌더링하는 내부 컴포넌트 */
function DebateLogSection({ data }: { data: NonNullable<ProductionSnapshot["debate_log"]> }) {
  return (
    <div className="space-y-1.5">
      {data.map((entry, i) => (
        <div key={i} className="rounded bg-zinc-50 px-2 py-1.5">
          <span className="text-[11px] font-medium text-zinc-600">Round {entry.round}</span>
          {entry.action && <span className="ml-1.5 text-[11px] text-zinc-500">{entry.action}</span>}
          {entry.concepts && entry.concepts.length > 0 && (
            <div className="mt-1 space-y-0.5">
              {entry.concepts.map((c, j) => (
                <p key={j} className="text-[11px] text-zinc-400">
                  {("title" in c && typeof c.title === "string" && c.title) || JSON.stringify(c)}
                </p>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function ProductionSnapshotSummary({ snapshot }: Props) {
  const [openKeys, setOpenKeys] = useState<Set<string>>(new Set());

  const toggle = (key: string) => {
    setOpenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Build accordion items — production sections (typed) + new sections
  const items: AccordionItem[] = [];

  if (snapshot.cinematographer) {
    items.push({
      key: "cinematographer",
      label: "비주얼 디자인",
      content: <CinematographerSection data={snapshot.cinematographer} />,
    });
  }
  if (snapshot.tts_designer) {
    items.push({
      key: "tts_designer",
      label: "음성 디자인",
      content: <TtsDesignerSection data={snapshot.tts_designer} />,
    });
  }
  if (snapshot.sound_designer) {
    items.push({
      key: "sound_designer",
      label: "BGM 설계",
      content: <SoundDesignerSection data={snapshot.sound_designer} />,
    });
  }
  if (snapshot.copyright_reviewer) {
    items.push({
      key: "copyright_reviewer",
      label: "저작권 검토",
      content: <CopyrightReviewerSection data={snapshot.copyright_reviewer} />,
    });
  }
  if (snapshot.revision_history && snapshot.revision_history.length > 0) {
    items.push({
      key: "revision_history",
      label: `수정 이력 (${snapshot.revision_history.length})`,
      content: <RevisionHistorySection history={snapshot.revision_history} />,
    });
  }
  if (snapshot.debate_log && snapshot.debate_log.length > 0) {
    items.push({
      key: "debate_log",
      label: `컨셉 토론 (${snapshot.debate_log.length})`,
      content: <DebateLogSection data={snapshot.debate_log} />,
    });
  }
  if (snapshot.agent_messages && snapshot.agent_messages.length > 0) {
    items.push({
      key: "agent_messages",
      label: `Agent 메시지 (${snapshot.agent_messages.length})`,
      content: <AgentMessagesSection messages={snapshot.agent_messages} />,
    });
  }

  const hasContent = items.length > 0 || !!snapshot.director || !!snapshot.quality_gate;
  if (!hasContent) return null;

  return (
    <div className="mb-4 space-y-1">
      <p className="mb-1.5 text-[11px] font-medium text-zinc-500">Production 결과</p>

      {/* Quality Gate Summary Header */}
      <SnapshotSummaryHeader
        qualityGate={snapshot.quality_gate}
        revisionCount={snapshot.revision_history?.length}
      />

      {/* Director decision (always visible if present) */}
      {snapshot.director && (
        <div className="rounded-lg border border-zinc-100 bg-white px-3 py-2">
          <p className="mb-1.5 text-[11px] font-medium text-zinc-500">통합 검증</p>
          <DirectorDecisionSection data={snapshot.director} />
        </div>
      )}

      {/* Collapsible sections */}
      {items.map((item) => {
        const isOpen = openKeys.has(item.key);
        return (
          <div key={item.key} className="rounded-lg border border-zinc-100 bg-white">
            <button
              type="button"
              className="flex w-full items-center gap-1.5 px-3 py-2 text-left"
              onClick={() => toggle(item.key)}
            >
              {isOpen ? (
                <ChevronDown className="h-3 w-3 text-zinc-400" />
              ) : (
                <ChevronRight className="h-3 w-3 text-zinc-400" />
              )}
              <span className="text-[11px] font-medium text-zinc-600">{item.label}</span>
            </button>
            {isOpen && (
              <div className="border-t border-zinc-50 px-3 pt-1.5 pb-2">{item.content}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
