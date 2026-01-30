"use client";

import { useStudioStore } from "../../store/useStudioStore";
import QualityDashboard from "../quality/QualityDashboard";
import AnalyticsDashboard from "../analytics/AnalyticsDashboard";

export default function InsightsTab() {
  const storyboardId = useStudioStore((s) => s.storyboardId);

  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-3 text-sm font-bold text-zinc-700">Quality Dashboard</h2>
        <QualityDashboard storyboardId={storyboardId} />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-bold text-zinc-700">Analytics</h2>
        <AnalyticsDashboard storyboardId={storyboardId} />
      </section>
    </div>
  );
}
