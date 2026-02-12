"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import ScriptListPanel from "../../components/scripts/ScriptListPanel";
import ScriptEditorPanel from "../../components/scripts/ScriptEditorPanel";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

function ScriptsContent() {
  const searchParams = useSearchParams();
  const idParam = searchParams.get("id");
  const selectedId = idParam ? Number(idParam) : null;

  return (
    <div className="flex h-full">
      {/* Left: list panel */}
      <div className="w-[360px] shrink-0">
        <ScriptListPanel selectedId={selectedId} />
      </div>

      {/* Right: editor panel */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl">
          <ScriptEditorPanel />
        </div>
      </div>
    </div>
  );
}

export default function ScriptsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <ScriptsContent />
    </Suspense>
  );
}
