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

  // Compact inline when profile is already selected
  if (currentProfileId && !isExpanded) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
          Style
        </span>
        <span className="text-xs font-bold text-zinc-900">
          {currentProfileName || "Selected"}
        </span>
        <button
          onClick={() => setIsExpanded(true)}
          className="rounded-md border border-zinc-200 px-2 py-0.5 text-[10px] font-medium text-zinc-500 transition hover:bg-zinc-50"
        >
          Change
        </button>
      </div>
    );
  }

  // Expanded profile picker
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-semibold text-zinc-700">Style Profile</h3>
          <p className="text-[10px] text-zinc-400">Model + LoRAs + Embeddings</p>
        </div>
        {currentProfileId && (
          <button
            onClick={() => setIsExpanded(false)}
            className="text-[10px] text-zinc-400 hover:text-zinc-600"
          >
            Cancel
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-6">
          <LoadingSpinner size="md" color="text-zinc-400" />
        </div>
      ) : profiles.length === 0 ? (
        <p className="py-4 text-center text-xs text-zinc-400">
          No profiles found. Create one in Manage.
        </p>
      ) : (
        <div className="grid gap-1.5 max-h-48 overflow-y-auto">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              onClick={() => handleSelect(profile.id)}
              disabled={isSelecting}
              className={`flex items-center justify-between rounded-lg border px-3 py-2.5 text-left transition ${
                currentProfileId === profile.id
                  ? "border-indigo-300 bg-indigo-50"
                  : "border-zinc-100 bg-white hover:border-indigo-200"
              } ${isSelecting ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <div className="min-w-0">
                <span className="text-xs font-bold text-zinc-900 truncate block">
                  {profile.display_name || profile.name}
                </span>
                {profile.description && (
                  <span className="text-[10px] text-zinc-400 line-clamp-1 block">
                    {profile.description}
                  </span>
                )}
              </div>
              {profile.is_default && (
                <span className="shrink-0 ml-2 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[8px] font-bold text-emerald-600 uppercase">
                  Default
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
