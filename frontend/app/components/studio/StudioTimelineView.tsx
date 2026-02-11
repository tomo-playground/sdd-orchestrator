"use client";

import { useContextStore } from "../../store/useContextStore";
import PipelineProgressBar from "./PipelineProgressBar";
import MaterialsCheckSection from "./MaterialsCheckSection";
import ImageSettingsSection from "./ImageSettingsSection";
import ScenesTab from "./ScenesTab";
import RenderTab from "./RenderTab";
import OutputTab from "./OutputTab";
import { CONTAINER_CLASSES, cx } from "../ui/variants";

interface StudioTimelineViewProps {
  storyboardId: number;
}

export default function StudioTimelineView({ storyboardId }: StudioTimelineViewProps) {
  const dbStoryboardId = useContextStore((s) => s.storyboardId);

  return (
    <div className={cx(CONTAINER_CLASSES, "space-y-6 py-8 pb-32")}>
      {/* 1. Pipeline Progress */}
      <PipelineProgressBar />

      {/* 2. Materials Check */}
      <MaterialsCheckSection storyboardId={dbStoryboardId ?? storyboardId} />

      {/* 3. Image Settings */}
      <ImageSettingsSection />

      {/* 4. Scenes */}
      <section>
        <SectionHeader title="Scenes" />
        <ScenesTab />
      </section>

      {/* 5. Render */}
      <section>
        <SectionHeader title="Render" />
        <RenderTab />
      </section>

      {/* 6. Output */}
      <section>
        <SectionHeader title="Output" />
        <OutputTab />
      </section>
    </div>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h3 className="mb-3 text-[13px] font-bold tracking-widest text-zinc-400 uppercase">{title}</h3>
  );
}
