"use client";

import { useUIStore } from "../../store/useUIStore";
import ScriptTab from "./ScriptTab";
import StageTab from "./StageTab";
import ScenesTab from "./ScenesTab";
import PublishTab from "./PublishTab";

export default function StudioWorkspace() {
  const activeTab = useUIStore((s) => s.activeTab);

  return (
    <div className="min-h-0 flex-1 overflow-hidden">
      {/* ScriptTab: hybrid layout manages its own scroll & padding */}
      <div className={`h-full w-full ${activeTab !== "script" ? "hidden" : ""}`}>
        <ScriptTab />
      </div>

      {activeTab === "stage" && <StageTab />}

      {activeTab === "direct" && <ScenesTab />}

      {activeTab === "publish" && (
        <div className="h-full w-full overflow-y-auto px-8 py-8">
          <PublishTab />
        </div>
      )}
    </div>
  );
}
