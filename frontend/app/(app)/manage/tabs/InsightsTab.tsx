"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import { useStudioStore } from "../../../store/useStudioStore";
import QualityDashboard from "../../../components/quality/QualityDashboard";
import AnalyticsDashboard from "../../../components/analytics/AnalyticsDashboard";

type StoryboardOption = {
  id: number;
  title: string;
};

export default function InsightsTab() {
  const groupId = useStudioStore((s) => s.groupId);
  const [storyboards, setStoryboards] = useState<StoryboardOption[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    if (!groupId) {
      setStoryboards([]);
      setSelectedId(null);
      return;
    }
    axios
      .get<StoryboardOption[]>(`${API_BASE}/storyboards`, { params: { group_id: groupId } })
      .then((r) => {
        setStoryboards(r.data);
        if (r.data.length > 0) setSelectedId(r.data[0].id);
        else setSelectedId(null);
      })
      .catch(() => {
        setStoryboards([]);
        setSelectedId(null);
      });
  }, [groupId]);

  return (
    <div className="space-y-6">
      {/* Storyboard selector */}
      <div className="flex items-center gap-3">
        <label className="text-xs font-semibold text-zinc-500">Storyboard</label>
        <select
          value={selectedId ?? ""}
          onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}
          className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-900 shadow-sm focus:border-zinc-400 focus:outline-none"
        >
          {storyboards.length === 0 && <option value="">No storyboards</option>}
          {storyboards.map((sb) => (
            <option key={sb.id} value={sb.id}>
              {sb.title || `Storyboard #${sb.id}`}
            </option>
          ))}
        </select>
      </div>

      {/* Dashboards */}
      <QualityDashboard storyboardId={selectedId} />
      <AnalyticsDashboard storyboardId={selectedId} />
    </div>
  );
}
