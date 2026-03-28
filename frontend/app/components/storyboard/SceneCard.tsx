"use client";

import { useState } from "react";
import type { Scene } from "../../types";
import { useSceneContext } from "./SceneContext";
import SceneImagePanel from "./SceneImagePanel";
import SceneActionBar from "./SceneActionBar";
import SceneGeminiModals from "./SceneGeminiModals";
import SceneClothingModal from "./SceneClothingModal";
import SceneEssentialFields from "./SceneEssentialFields";
import ScenePropertyPanel from "./ScenePropertyPanel";

type SceneCardProps = {
  scene: Scene;
  /** When true (3-panel mode), hides Tier 2~4 sections — rendered in the right panel instead. */
  compact?: boolean;
};

export default function SceneCard({ scene, compact = false }: SceneCardProps) {
  const { data, callbacks } = useSceneContext();

  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");
  const [clothingOpen, setClothingOpen] = useState(false);

  return (
    <div className="group relative grid gap-2 rounded-3xl border border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-200/30 transition hover:border-zinc-300">
      {/* Multi-character badge */}
      {scene.scene_mode === "multi" && (
        <span className="absolute top-4 right-4 z-30 rounded bg-indigo-100 px-1.5 py-0.5 text-[11px] font-semibold text-indigo-700">
          2P
        </span>
      )}

      {/* ── Tier 1: Essential (Image + Script + Basic Info) ── */}
      <div className="relative z-20 grid gap-6 md:grid-cols-[240px_1fr] lg:grid-cols-[280px_1fr]">
        {/* Left: Visuals */}
        <div className="relative z-30 flex flex-col gap-3">
          <SceneImagePanel
            scene={scene}
            onImageClick={(url) =>
              callbacks.onImagePreview(
                url,
                scene.candidates?.filter((c) => c.image_url).map((c) => c.image_url!)
              )
            }
            onCandidateSelect={(imageUrl) => callbacks.onUpdateScene({ image_url: imageUrl })}
          />
          {/* Action Bar (Buttons) moved here for easy access */}
          <SceneActionBar
            scene={scene}
            onGeminiEditOpen={() => setGeminiEditOpen(true)}
            onClothingOpen={() => setClothingOpen(true)}
            compact={true}
          />
        </div>

        {/* Right: Script & Details */}
        <div className="relative z-20 flex flex-col gap-4">
          <SceneEssentialFields scene={scene} />
        </div>
      </div>

      {/* ── Tier 2~4: Property Panel (Customize + Advanced) — hidden in 3-panel mode ── */}
      {!compact && <ScenePropertyPanel />}

      {/* Gemini Modals */}
      <SceneGeminiModals
        scene={scene}
        geminiEditOpen={geminiEditOpen}
        setGeminiEditOpen={setGeminiEditOpen}
        geminiTargetChange={geminiTargetChange}
        setGeminiTargetChange={setGeminiTargetChange}
        onApplyPromptEdit={(edited) => callbacks.onUpdateScene({ image_prompt: edited })}
      />

      {/* Clothing Override Modal */}
      {clothingOpen && (
        <SceneClothingModal
          scene={scene}
          onClose={() => setClothingOpen(false)}
          onSave={(clothingTags) => {
            callbacks.onUpdateScene({ clothing_tags: clothingTags });
            callbacks.showToast(
              "의상 태그가 저장되었습니다. 이미지를 재생성하면 반영됩니다.",
              "success"
            );
          }}
        />
      )}
    </div>
  );
}
