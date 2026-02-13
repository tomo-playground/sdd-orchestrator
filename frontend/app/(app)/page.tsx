"use client";

import { Suspense } from "react";
import StudioKanbanView from "../components/studio/StudioKanbanView";
import LoadingSpinner from "../components/ui/LoadingSpinner";

function HomeContent() {
  return <StudioKanbanView />;
}

export default function HomePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <HomeContent />
    </Suspense>
  );
}
