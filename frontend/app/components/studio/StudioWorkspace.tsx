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
      {/* 모든 탭을 항상 마운트하고 hidden toggle — 탭 전환 시 상태(TTS 캐시 등) 보존 */}
      <div className={`h-full w-full ${activeTab !== "script" ? "hidden" : ""}`}>
        <ScriptTab />
      </div>

      <div className={`h-full w-full ${activeTab !== "stage" ? "hidden" : ""}`}>
        <StageTab />
      </div>

      <div className={`h-full w-full ${activeTab !== "direct" ? "hidden" : ""}`}>
        <ScenesTab />
      </div>

      <div
        className={`scrollbar-hide h-full w-full overflow-y-auto px-8 py-8 ${activeTab !== "publish" ? "hidden" : ""}`}
      >
        <PublishTab />
      </div>
    </div>
  );
}
