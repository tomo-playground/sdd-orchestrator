"use client";

import { Suspense } from "react";
import YouTubeConnectTab from "../../../components/settings/YouTubeConnectTab";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import { useContextStore } from "../../../store/useContextStore";

function YouTubeContent() {
  const projectId = useContextStore((s) => s.projectId);
  return <YouTubeConnectTab projectId={projectId} />;
}

export default function SettingsYouTubePage() {
  return (
    <div className="px-8 py-6">
      <Suspense
        fallback={
          <div className="flex h-64 items-center justify-center">
            <LoadingSpinner size="md" />
          </div>
        }
      >
        <YouTubeContent />
      </Suspense>
    </div>
  );
}
