"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import LoadingSpinner from "../ui/LoadingSpinner";

type StyleProfile = {
  id: number;
  name: string;
  display_name: string | null;
  description: string | null;
  is_default: boolean;
  sd_model_name?: string;
};

type Props = {
  currentProfileId: number | null;
  currentProfileName: string | null;
  onSelect: (profileId: number) => Promise<void>;
};

export default function StyleProfileSelector({
  currentProfileId,
  currentProfileName,
  onSelect,
}: Props) {
  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSelecting, setIsSelecting] = useState(false);
  const [isExpanded, setIsExpanded] = useState(!currentProfileId);

  useEffect(() => {
    axios
      .get<StyleProfile[]>(`${API_BASE}/style-profiles`)
      .then((res) => setProfiles(res.data || []))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const handleSelect = async (profileId: number) => {
    setIsSelecting(true);
    try {
      await onSelect(profileId);
      setIsExpanded(false);
    } finally {
      setIsSelecting(false);
    }
  };

  // Compact summary when profile is already selected
  if (currentProfileId && !isExpanded) {
    return (
      <div className="rounded-2xl border border-zinc-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Style Profile
            </h3>
            <p className="mt-1 text-sm font-bold text-zinc-900">
              {currentProfileName || "Selected"}
            </p>
          </div>
          <button
            onClick={() => setIsExpanded(true)}
            className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-600 transition hover:bg-zinc-50"
          >
            Change
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Style Profile
          </h3>
          <p className="mt-1 text-xs text-zinc-500">
            Model + LoRAs + Embeddings
          </p>
        </div>
        {currentProfileId && (
          <button
            onClick={() => setIsExpanded(false)}
            className="text-xs text-zinc-400 hover:text-zinc-600"
          >
            Cancel
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="md" color="text-zinc-400" />
        </div>
      ) : profiles.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-300 bg-zinc-50 p-6 text-center">
          <p className="text-xs text-zinc-500">No style profiles found.</p>
          <p className="mt-1 text-[10px] text-zinc-400">
            Create one in Manage &gt; Style
          </p>
        </div>
      ) : (
        <div className="grid gap-2 max-h-64 overflow-y-auto">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              onClick={() => handleSelect(profile.id)}
              disabled={isSelecting}
              className={`group relative rounded-xl border p-4 text-left transition-all ${
                currentProfileId === profile.id
                  ? "border-indigo-300 bg-indigo-50"
                  : "border-zinc-200 bg-white hover:border-indigo-200 hover:shadow-sm"
              } ${isSelecting ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-zinc-900 truncate">
                      {profile.display_name || profile.name}
                    </span>
                    {profile.is_default && (
                      <span className="shrink-0 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[8px] font-bold text-emerald-600 uppercase">
                        Default
                      </span>
                    )}
                  </div>
                  {profile.description && (
                    <p className="mt-0.5 text-xs text-zinc-500 line-clamp-1">
                      {profile.description}
                    </p>
                  )}
                </div>
                <div
                  className={`shrink-0 h-4 w-4 rounded-full border-2 flex items-center justify-center ${
                    currentProfileId === profile.id
                      ? "border-indigo-500 bg-indigo-500"
                      : "border-zinc-300"
                  }`}
                >
                  {currentProfileId === profile.id && (
                    <div className="h-1.5 w-1.5 rounded-full bg-white" />
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
