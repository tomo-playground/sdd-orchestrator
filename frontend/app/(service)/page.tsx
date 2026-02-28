"use client";

import { Suspense } from "react";
import HomeVideoFeed from "../components/home/HomeVideoFeed";
import LoadingSpinner from "../components/ui/LoadingSpinner";

function HomeContent() {
  return <HomeVideoFeed />;
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
