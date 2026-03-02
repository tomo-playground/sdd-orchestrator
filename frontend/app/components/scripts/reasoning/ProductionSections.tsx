"use client";

import { useRenderStore } from "../../../store/useRenderStore";

type SectionProps = { data: Record<string, unknown> };

export function CinematographerSection({ data }: SectionProps) {
  // SSE payload: { result: { scenes: [...] }, tool_logs: [...] }
  const result = (data.result ?? {}) as Record<string, unknown>;
  const scenes = (result.scenes ?? []) as Array<Record<string, unknown>>;
  const toolLogs = (data.tool_logs ?? []) as Array<Record<string, unknown>>;

  if (scenes.length === 0) {
    return <p className="text-[11px] text-zinc-400">시각 설계 데이터 없음</p>;
  }

  return (
    <div className="space-y-2">
      <p className="text-[11px] text-zinc-500">
        {scenes.length}개 씬 시각 설계 완료
        {toolLogs.length > 0 && ` · ${toolLogs.length}회 도구 호출`}
      </p>
      <div className="space-y-1.5">
        {scenes.map((s, i) => {
          const camera = s.camera ? String(s.camera) : null;
          const env = s.environment ? String(s.environment) : null;
          const promptKo = s.image_prompt_ko ? String(s.image_prompt_ko) : null;
          const prompt = s.image_prompt ? String(s.image_prompt) : null;
          return (
            <div key={i} className="rounded-lg bg-zinc-50 px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-medium text-zinc-400">
                  #{String(s.order ?? i + 1)}
                </span>
                {camera && (
                  <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[11px] text-violet-700">
                    {camera}
                  </span>
                )}
                {env && (
                  <span className="rounded bg-sky-100 px-1.5 py-0.5 text-[11px] text-sky-700">
                    {env}
                  </span>
                )}
              </div>
              {promptKo && <p className="mt-1 text-xs leading-relaxed text-zinc-700">{promptKo}</p>}
              {prompt && (
                <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-zinc-400">
                  {prompt}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function TtsDesignerSection({ data }: SectionProps) {
  // SSE payload: { tts_designs: [...] }
  const designs = (data.tts_designs ?? []) as Array<Record<string, unknown>>;

  if (designs.length === 0) {
    return <p className="text-[11px] text-zinc-400">음성 설계 데이터 없음</p>;
  }

  return (
    <div className="space-y-1.5">
      <p className="text-[11px] text-zinc-500">{designs.length}개 씬 음성 설계</p>
      {designs.map((d, i) => {
        const pacing = d.pacing as Record<string, number> | undefined;
        const voicePrompt = d.voice_design_prompt ? String(d.voice_design_prompt) : null;
        const voicePromptKo = d.voice_design_prompt_ko ? String(d.voice_design_prompt_ko) : null;
        return (
          <div key={i} className="rounded-lg bg-zinc-50 px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-medium text-zinc-400">
                #{String(d.scene_id ?? i + 1)}
              </span>
              {pacing && (
                <span className="text-[11px] text-zinc-400">
                  pad: {pacing.head_padding ?? 0}s / {pacing.tail_padding ?? 0}s
                </span>
              )}
            </div>
            {voicePrompt && <p className="mt-0.5 text-[11px] leading-relaxed text-zinc-600">{voicePrompt}</p>}
            {voicePromptKo && <p className="mt-0.5 text-[11px] leading-relaxed text-zinc-400">{voicePromptKo}</p>}
          </div>
        );
      })}
    </div>
  );
}

export function SoundDesignerSection({ data }: SectionProps) {
  // SSE payload: { recommendation: { prompt, mood, duration, reasoning } }
  const rec = (data.recommendation ?? data) as Record<string, unknown>;
  const prompt = rec.prompt ? String(rec.prompt) : null;
  const mood = rec.mood ? String(rec.mood) : null;
  const duration = rec.duration as number | undefined;
  const reasoning = rec.reasoning ? String(rec.reasoning) : null;
  const setRender = useRenderStore((s) => s.set);

  if (!prompt && !mood) {
    return <p className="text-[11px] text-zinc-400">BGM 추천 데이터 없음</p>;
  }

  const handleApply = () => {
    setRender({
      bgmMode: "auto",
      bgmPrompt: prompt || "",
      bgmMood: mood || "",
    });
  };

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-2">
        {mood && (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-700">
            {mood}
          </span>
        )}
        {duration && <span className="text-[11px] text-zinc-400">{duration}초</span>}
      </div>
      {prompt && <p className="text-[11px] leading-relaxed text-zinc-600">{prompt}</p>}
      {reasoning && <p className="text-[11px] leading-relaxed text-zinc-400">{reasoning}</p>}
      {prompt && (
        <button
          type="button"
          onClick={handleApply}
          className="mt-1 rounded-lg border border-amber-300 bg-amber-50 px-3 py-1 text-[11px] font-medium text-amber-700 transition hover:bg-amber-100"
        >
          BGM 적용
        </button>
      )}
    </div>
  );
}

export function CopyrightReviewerSection({ data }: SectionProps) {
  // SSE payload: { overall, checks: [...], confidence }
  const overall = data.overall ? String(data.overall) : null;
  const checks = (data.checks ?? []) as Array<Record<string, unknown>>;
  const confidence = data.confidence as number | undefined;

  const statusColor = (status: string) => {
    if (status === "PASS") return "bg-emerald-100 text-emerald-700";
    if (status === "WARN") return "bg-amber-100 text-amber-700";
    return "bg-red-100 text-red-700";
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {overall && (
          <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${statusColor(overall)}`}>
            {overall}
          </span>
        )}
        {confidence != null && (
          <span className="text-[11px] text-zinc-400">신뢰도 {Math.round(confidence * 100)}%</span>
        )}
      </div>
      {checks.length > 0 && (
        <div className="space-y-1">
          {checks.map((c, i) => {
            const detail = c.detail ? String(c.detail) : null;
            const suggestion = c.suggestion ? String(c.suggestion) : null;
            return (
              <div key={i} className="flex items-start gap-2">
                <span
                  className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium ${statusColor(String(c.status ?? ""))}`}
                >
                  {String(c.status ?? "")}
                </span>
                <div>
                  <p className="text-[11px] text-zinc-600">
                    {String(c.type ?? "").replace(/_/g, " ")}
                  </p>
                  {detail && <p className="text-[11px] text-zinc-400">{detail}</p>}
                  {suggestion && <p className="text-[11px] text-amber-600">{suggestion}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
