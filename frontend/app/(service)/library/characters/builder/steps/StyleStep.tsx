"use client";

import { useState, useEffect } from "react";
import { Palette, Check } from "lucide-react";
import axios from "axios";
import { API_BASE, ADMIN_API_BASE } from "../../../../../constants";
import type { StyleProfile, SDModelEntry } from "../../../../../types";
import LoadingSpinner from "../../../../../components/ui/LoadingSpinner";

type StyleStepProps = {
  selectedId: number | null;
  onSelect: (id: number, baseModel: string | null) => void;
};

export default function StyleStep({ selectedId, onSelect }: StyleStepProps) {
  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const [sdModels, setSdModels] = useState<Map<number, SDModelEntry>>(new Map());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [profilesRes, modelsRes] = await Promise.all([
          axios.get<StyleProfile[]>(`${API_BASE}/style-profiles`),
          axios.get<SDModelEntry[]>(`${ADMIN_API_BASE}/sd-models`),
        ]);
        setProfiles(profilesRes.data);
        const modelMap = new Map<number, SDModelEntry>();
        for (const m of modelsRes.data) modelMap.set(m.id, m);
        setSdModels(modelMap);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-zinc-800">Select Style</h2>
        <p className="mt-0.5 text-xs text-zinc-400">
          Choose a visual style for this character. LoRAs will be filtered by compatibility.
        </p>
      </div>

      {profiles.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {profiles.map((profile) => {
            const isSelected = selectedId === profile.id;
            const sdModel = profile.sd_model_id ? sdModels.get(profile.sd_model_id) : null;
            const baseModel = sdModel?.base_model ?? null;

            return (
              <button
                key={profile.id}
                onClick={() => onSelect(profile.id, baseModel)}
                className={`relative flex flex-col items-start gap-2 rounded-xl border-2 p-4 text-left transition ${
                  isSelected
                    ? "border-zinc-900 bg-zinc-50 shadow-sm"
                    : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50/50"
                }`}
              >
                {/* Selection badge */}
                {isSelected && (
                  <div className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-zinc-900">
                    <Check className="h-3 w-3 text-white" />
                  </div>
                )}

                {/* Icon */}
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-lg ${
                    isSelected ? "bg-zinc-900 text-white" : "bg-zinc-100 text-zinc-500"
                  }`}
                >
                  <Palette className="h-4.5 w-4.5" />
                </div>

                {/* Name */}
                <div>
                  <p className="text-sm font-semibold text-zinc-800">
                    {profile.display_name || profile.name}
                  </p>
                  {profile.description && (
                    <p className="mt-0.5 line-clamp-2 text-xs text-zinc-400">
                      {profile.description}
                    </p>
                  )}
                </div>

                {/* Base model badge */}
                {baseModel && (
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500">
                    {baseModel}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-200 py-12">
          <Palette className="mb-2 h-8 w-8 text-zinc-300" />
          <p className="text-sm text-zinc-400">No style profiles available</p>
        </div>
      )}
    </div>
  );
}
