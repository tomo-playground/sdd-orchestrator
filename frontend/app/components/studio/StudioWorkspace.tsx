"use client";

import { useUIStore } from "../../store/useUIStore";
import ScriptTab from "./ScriptTab";
import ScenesTab from "./ScenesTab";
import PublishTab from "./PublishTab";

export default function StudioWorkspace() {
  const activeTab = useUIStore((s) => s.activeTab);

  return (
    <div className="min-h-0 flex-1 overflow-hidden">
      {activeTab === "script" && (
        <div className="h-full w-full overflow-y-auto px-6 py-8">
          <ScriptTab />
        </div>
      )}

      {activeTab === "edit" && <ScenesTab />}

      {activeTab === "publish" && (
        <div className="h-full w-full overflow-y-auto px-6 py-8">
          <PublishTab />
        </div>
      )}
    </div>
  );
}
