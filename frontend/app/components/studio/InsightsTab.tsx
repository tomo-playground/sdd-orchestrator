"use client";

import { useStudioStore } from "../../store/useStudioStore";
import QualityDashboard from "../quality/QualityDashboard";
import AnalyticsDashboard from "../analytics/AnalyticsDashboard";

export default function InsightsTab() {
  const storyboardId = useStudioStore((s) => s.storyboardId);

  return (
    <div className="space-y-10">
      <QualityDashboard storyboardId={storyboardId} />
      <AnalyticsDashboard storyboardId={storyboardId} />
    </div>
  );
}
