"use client";

import { useUIStore } from "../../store/useUIStore";
import ScriptTab from "./ScriptTab";
import ScenesTab from "./ScenesTab";
import PublishTab from "./PublishTab";

export default function StudioWorkspace() {
  const activeTab = useUIStore((s) => s.activeTab);

  return (
    <div className="min-h-0 flex-1 overflow-hidden">
      {/* ScriptTab uses local useState — keep mounted to preserve state across tab switches */}
      <div
        className={`h-full w-full overflow-y-auto px-6 py-8 ${activeTab !== "script" ? "hidden" : ""}`}
      >
        <ScriptTab />
      </div>

      {activeTab === "edit" && <ScenesTab />}

      {activeTab === "publish" && (
        <div className="h-full w-full overflow-y-auto px-6 py-8">
          <PublishTab />
        </div>
      )}
    </div>
  );
}
