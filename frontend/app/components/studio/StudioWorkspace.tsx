"use client";

import { useUIStore } from "../../store/useUIStore";
import ScriptTab from "./ScriptTab";
import ScenesTab from "./ScenesTab";
import RenderTab from "./RenderTab";
import OutputTab from "./OutputTab";

export default function StudioWorkspace() {
  const activeTab = useUIStore((s) => s.activeTab);

  return (
    <div className="min-h-0 flex-1 overflow-hidden">
      {activeTab === "script" && (
        <div className="mx-auto h-full w-full max-w-7xl overflow-y-auto px-6 py-8">
          <ScriptTab />
        </div>
      )}

      {activeTab === "edit" && <ScenesTab />}

      {activeTab === "render" && (
        <div className="mx-auto h-full w-full max-w-7xl overflow-y-auto px-6 py-8">
          <RenderTab />
        </div>
      )}

      {activeTab === "output" && (
        <div className="mx-auto h-full w-full max-w-7xl overflow-y-auto px-6 py-8">
          <OutputTab />
        </div>
      )}
    </div>
  );
}
