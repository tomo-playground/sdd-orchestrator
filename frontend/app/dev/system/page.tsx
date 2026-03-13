"use client";

import { Suspense } from "react";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import GeneralSettingsTab from "../../components/settings/GeneralSettingsTab";

function SystemContent() {
  return (
    <div className="px-8 py-6">
      <GeneralSettingsTab />
    </div>
  );
}

export default function DevSystemPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <SystemContent />
    </Suspense>
  );
}
