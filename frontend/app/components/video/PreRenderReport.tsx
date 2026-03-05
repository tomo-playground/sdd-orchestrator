"use client";

import { useCallback, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { PreValidateResponse } from "../../types";

type PreRenderReportProps = {
  storyboardId: number | null;
};

export default function PreRenderReport({ storyboardId }: PreRenderReportProps) {
  const [report, setReport] = useState<PreValidateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const runValidation = useCallback(async () => {
    if (!storyboardId) return;
    setIsLoading(true);
    try {
      const res = await axios.post<PreValidateResponse>(`${API_BASE}/preview/validate`, {
        storyboard_id: storyboardId,
      });
      setReport(res.data);
    } catch {
      setReport(null);
    } finally {
      setIsLoading(false);
    }
  }, [storyboardId]);

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
        {isLoading ? "검증 중..." : "사전 검증"}
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
