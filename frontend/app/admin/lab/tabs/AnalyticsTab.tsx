"use client";

import { useState, useCallback, useEffect } from "react";
import axios from "axios";
import { RefreshCw, Loader2, ArrowUpRight } from "lucide-react";
import { ADMIN_API_BASE } from "../../../constants";
import QualityDashboard from "../../../components/quality/QualityDashboard";
import Button from "../../../components/ui/Button";
import { SUCCESS_TEXT, WARNING_TEXT, ERROR_TEXT, ERROR_BG } from "../../../components/ui/variants";

// ── Types ──────────────────────────────────────────────────────

type TagEffectivenessItem = {
  tag_name: string;
  tag_id: number;
  use_count: number;
  match_count: number;
  effectiveness: number;
};

type TagEffectivenessReport = {
  items: TagEffectivenessItem[];
  total_experiments: number;
  avg_match_rate: number | null;
};

// ── Component ──────────────────────────────────────────────────

export default function AnalyticsTab() {
  const [report, setReport] = useState<TagEffectivenessReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await axios.get<TagEffectivenessReport>(
        `${ADMIN_API_BASE}/lab/analytics/tag-effectiveness`
      );
      setReport(res.data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(axiosErr.response?.data?.detail || axiosErr.message || "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      await axios.post(`${ADMIN_API_BASE}/lab/analytics/sync-effectiveness`);
      await loadReport();
    } catch {
      /* sync errors are non-critical */
    } finally {
      setSyncing(false);
    }
  }, [loadReport]);

  const effectivenessColor = (ratio: number) => {
    if (ratio >= 0.8) return SUCCESS_TEXT;
    if (ratio >= 0.5) return WARNING_TEXT;
    return ERROR_TEXT;
  };

  return (
    <div className="space-y-6">
      {/* ── Purpose Section ── */}
      <div className="rounded-2xl border border-amber-100 bg-gradient-to-br from-amber-50 to-white p-5">
        <h2 className="mb-2 text-base font-bold text-zinc-800">Analytics</h2>
        <p className="text-xs leading-relaxed text-zinc-600">
          <strong className="text-zinc-700">목표:</strong> 이미지 생성 품질과 태그 효과성을 데이터
          기반으로 분석합니다.
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
          Lab 실험 결과를 집계하여 어떤 태그가 높은 Match Rate를 보이는지, 프롬프트 패턴별 성공률
          등을 시각화합니다. 데이터 기반 프롬프트 최적화를 지원합니다.
        </p>

        {/* Collapsible Details */}
        <details className="mt-3">
          <summary className="cursor-pointer text-xs font-semibold text-amber-700 hover:text-amber-800">
            📖 자세히 보기
          </summary>
          <div className="mt-3 space-y-3 rounded-lg border border-amber-100 bg-white p-3 text-xs">
            <div>
              <strong className="text-zinc-700">💡 사용 시나리오:</strong>
              <ul className="mt-1 ml-4 list-disc space-y-0.5 text-zinc-600">
                <li>어떤 태그가 가장 안정적으로 렌더링되는지 데이터 확인</li>
                <li>Match Rate 낮은 태그 패턴 분석 및 개선</li>
                <li>프롬프트 구성 전략 수립 (효과적인 태그 우선 배치)</li>
              </ul>
            </div>
            <div>
              <strong className="text-zinc-700">✅ 성공 기준:</strong>
              <span className="ml-1 text-zinc-600">
                Effectiveness <strong className="text-emerald-600">70% 이상</strong> 태그를 우선
                사용
              </span>
            </div>
            <div>
              <strong className="text-zinc-700">📊 주요 메트릭:</strong>
              <span className="ml-1 text-zinc-600">
                Avg Match Rate, Tag Effectiveness, Experiment Count
              </span>
            </div>
            <div>
              <strong className="text-zinc-700">🔄 워크플로우:</strong>
              <span className="ml-1 text-zinc-600">
                Analytics → 데이터 기반 의사결정 → 프롬프트 최적화
              </span>
            </div>
            <div>
              <strong className="text-zinc-700">⚡ 빠른 팁:</strong>
              <ul className="mt-1 ml-4 list-disc space-y-0.5 text-zinc-600">
                <li>Sync 버튼으로 최신 실험 결과 반영</li>
                <li>Low Effectiveness 태그는 프롬프트에서 제외 고려</li>
              </ul>
            </div>
          </div>
        </details>
      </div>

      {/* Quality Dashboard (reused) */}
      <QualityDashboard />

      {/* Tag Effectiveness Section */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-zinc-800">Tag Effectiveness</h3>
            {report && (
              <p className="mt-0.5 text-[12px] text-zinc-400">
                {report.total_experiments} experiments
                {report.avg_match_rate != null &&
                  ` / ${(report.avg_match_rate * 100).toFixed(0)}% avg`}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleSync}
              disabled={syncing}
              loading={syncing}
              variant="outline"
              size="sm"
            >
              {!syncing && <ArrowUpRight className="h-3 w-3" />}
              Sync to Studio
            </Button>
            <Button
              onClick={loadReport}
              disabled={loading}
              loading={loading}
              variant="outline"
              size="sm"
            >
              {!loading && <RefreshCw className="h-3 w-3" />}
              Refresh
            </Button>
          </div>
        </div>

        {error && (
          <p className={`mb-3 rounded-lg px-3 py-2 text-xs ${ERROR_BG} ${ERROR_TEXT}`}>{error}</p>
        )}

        {!report && !loading && !error && (
          <p className="py-6 text-center text-xs text-zinc-400">No effectiveness data available.</p>
        )}

        {report && report.items.length === 0 && (
          <p className="py-6 text-center text-xs text-zinc-400">
            Run experiments in Tag Lab to populate effectiveness data.
          </p>
        )}

        {report && report.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-100 text-left text-[12px] font-semibold tracking-wider text-zinc-400 uppercase">
                  <th className="pr-4 pb-2">Tag</th>
                  <th className="pr-4 pb-2">Uses</th>
                  <th className="pr-4 pb-2">Matches</th>
                  <th className="pb-2">Effectiveness</th>
                </tr>
              </thead>
              <tbody>
                {report.items.map((item, idx) => (
                  <tr
                    key={`${item.tag_id}-${idx}`}
                    className="border-b border-zinc-50 text-zinc-600"
                  >
                    <td className="py-2 pr-4 font-medium">{item.tag_name}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{item.use_count}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{item.match_count}</td>
                    <td className={`py-2 font-bold ${effectivenessColor(item.effectiveness)}`}>
                      {(item.effectiveness * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
