"use client";

import type { Scene, Background } from "../../types";

type SceneBackgroundFieldProps = {
    scene: Scene;
    backgrounds: Background[];
    onUpdateScene: (updates: Partial<Scene>) => void;
};

export default function SceneBackgroundField({
    scene,
    backgrounds,
    onUpdateScene,
}: SceneBackgroundFieldProps) {
    if (backgrounds.length === 0) return null;

    const selectedBackground = backgrounds.find((bg) => bg.id === scene.background_id);

    return (
        <div className="grid gap-2">
            <label className="text-[12px] font-semibold tracking-[0.2em] text-zinc-500 uppercase">
                Background
            </label>
            <select
                value={scene.background_id ?? ""}
                onChange={(e) => {
                    const val = e.target.value;
                    onUpdateScene({ background_id: val ? Number(val) : null });
                }}
                className="w-full rounded-2xl border border-zinc-200 bg-white/80 px-3 py-2 text-sm outline-none focus:border-zinc-400"
            >
                <option value="">None</option>
                {backgrounds.map((bg) => (
                    <option key={bg.id} value={bg.id}>
                        {bg.name}
                        {bg.category ? ` (${bg.category})` : ""}
                    </option>
                ))}
            </select>
            {selectedBackground?.tags && selectedBackground.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                    {selectedBackground.tags.map((tag) => (
                        <span
                            key={tag}
                            className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700"
                        >
                            {tag}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
}
