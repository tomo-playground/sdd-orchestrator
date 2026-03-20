"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { PreValidateResponse } from "../../types";

type PreRenderReportProps = {
  storyboardId: number | null;
  onValidationComplete?: (isReady: boolean) => void;
  refreshTrigger?: number;
};

export default function PreRenderReport({
  storyboardId,
  onValidationComplete,
  refreshTrigger,
}: PreRenderReportProps) {
  const [report, setReport] = useState<PreValidateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const ranForId = useRef<number | null>(null);

  const runValidation = useCallback(async () => {
    if (!storyboardId) return;
    setIsLoading(true);
    try {
      const res = await axios.post<PreValidateResponse>(`${API_BASE}/preview/validate`, {
        storyboard_id: storyboardId,
      });
      setReport(res.data);
      onValidationComplete?.(res.data.is_ready);
    } catch {
      setReport(null);
      onValidationComplete?.(false);
    } finally {
      setIsLoading(false);
    }
  }, [storyboardId, onValidationComplete]);

  // refreshTrigger 변경 시 재검증 (예: TTS 완료 후)
  const prevTrigger = useRef<number | undefined>(undefined);

  // 스토리보드 ID 변경 시 자동 1회 실행 + null 리셋
  useEffect(() => {
    if (!storyboardId) {
      ranForId.current = null;
      prevTrigger.current = undefined;
      setReport(null);
      return;
    }
    if (storyboardId !== ranForId.current) {
      ranForId.current = storyboardId;
      prevTrigger.current = undefined;
      runValidation();
    }
  }, [storyboardId, runValidation]);
  useEffect(() => {
    if (refreshTrigger != null && refreshTrigger !== prevTrigger.current && storyboardId) {
      prevTrigger.current = refreshTrigger;
      runValidation();
    }
  }, [refreshTrigger, storyboardId, runValidation]);

  const errorCount = report?.issues.filter((i) => i.level === "error").length ?? 0;
  const warnCount = report?.issues.filter((i) => i.level === "warning").length ?? 0;
  const infoCount = report?.issues.filter((i) => i.level === "info").length ?? 0;

  const summaryParts: string[] = [];
  if (errorCount > 0) summaryParts.push(`${errorCount} error`);
  if (warnCount > 0) summaryParts.push(`${warnCount} warning`);
  if (infoCount > 0) summaryParts.push(`${infoCount} info`);

  return (
    <div className="space-y-3">
      <button
        onClick={runValidation}
        disabled={isLoading || !storyboardId}
        className={`w-full rounded-xl px-4 py-2 text-sm font-medium transition ${
          isLoading
            ? "bg-zinc-100 text-zinc-400"
            : "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
        }`}
      >
        {isLoading ? "검증 중..." : report ? "재검증" : "사전 검증"}
      </button>

      {report && (
        <div className="space-y-2 rounded-xl border border-zinc-200 bg-white p-4">
          {/* Summary */}
          <div className="flex items-center justify-between">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                report.is_ready ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
              }`}
            >
              {report.is_ready ? "Ready" : "Issues Found"}
            </span>
            <span className="text-xs text-zinc-400">
              {report.total_scenes}개 씬 / {report.total_duration?.toFixed(1)}s
            </span>
          </div>

          {/* Issue counts summary */}
          {summaryParts.length > 0 && (
            <p className="text-xs text-zinc-500">{summaryParts.join(", ")}</p>
          )}

          {/* TTS Cache */}
          {report.cached_tts_count > 0 && (
            <p className="text-xs text-emerald-600">
              TTS 캐시: {report.cached_tts_count}/{report.total_scenes}
            </p>
          )}

          {/* Issues */}
          {report.issues.length > 0 && (
            <ul className="space-y-1">
              {report.issues.map((issue, i) => (
                <li key={i} className="flex items-start gap-2 text-xs">
                  <span
                    className={`mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
                      issue.level === "error"
                        ? "bg-red-500"
                        : issue.level === "warning"
                          ? "bg-amber-500"
                          : "bg-blue-400"
                    }`}
                  />
                  <span className="text-zinc-600">{issue.message}</span>
                </li>
              ))}
            </ul>
          )}

          {report.issues.length === 0 && <p className="text-xs text-zinc-400">이슈 없음</p>}
        </div>
      )}
    </div>
  );
}
