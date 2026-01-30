"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../../constants";
import type { ChannelProfile } from "../../store/slices/profileSlice";

type ReferenceImage = {
  character_key: string;
  character_id?: number;
  filename?: string;
  preset?: {
    weight: number;
    model: string;
    description: string;
  };
};

type ChannelProfileModalProps = {
  onComplete: (profile: ChannelProfile) => void;
  initialProfile?: ChannelProfile | null;
};

export default function ChannelProfileModal({
  onComplete,
  initialProfile,
}: ChannelProfileModalProps) {
  const [channelName, setChannelName] = useState(initialProfile?.channel_name || "");
  const [avatarKey, setAvatarKey] = useState(initialProfile?.avatar_key || "");
  const [availableAvatars, setAvailableAvatars] = useState<ReferenceImage[]>([]);

  // Load available avatars
  useEffect(() => {
    axios
      .get(`${API_BASE}/controlnet/ip-adapter/references`)
      .then((res) => {
        const refs = res.data.references || [];
        setAvailableAvatars(refs);
        // Auto-select first avatar if none selected
        if (!avatarKey && refs.length > 0) {
          setAvatarKey(refs[0].character_key);
        }
      })
      .catch(() => {
        // Fallback to default
        setAvailableAvatars([{ character_key: "default_avatar" }]);
        if (!avatarKey) setAvatarKey("default_avatar");
      });
  }, []);

  const canSave = channelName.trim() && avatarKey;

  const handleSave = () => {
    if (!canSave) return;

    const profile: ChannelProfile = {
      channel_name: channelName.trim(),
      avatar_key: avatarKey,
      created_at: initialProfile?.created_at || Date.now(),
    };

    onComplete(profile);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-500 px-6 py-4">
          <h2 className="text-xl font-bold text-white">
            {initialProfile ? "채널 프로필 편집" : "채널 프로필 설정"}
          </h2>
          <p className="text-sm text-indigo-100 mt-1">
            한 번만 설정하면 모든 영상에 자동으로 적용됩니다
          </p>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {/* Channel Name */}
          <div>
            <label className="block text-xs font-semibold text-zinc-700 uppercase tracking-wider mb-2">
              채널명 *
            </label>
            <input
              type="text"
              value={channelName}
              onChange={(e) => setChannelName(e.target.value)}
              placeholder="예: 토모의 AI 채널"
              className="w-full rounded-xl border border-zinc-200 px-4 py-3 text-sm outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50 transition-all"
              autoFocus
            />
          </div>

          {/* Avatar */}
          <div>
            <label className="block text-xs font-semibold text-zinc-700 uppercase tracking-wider mb-2">
              아바타 *
            </label>
            {availableAvatars.length === 0 ? (
              <div className="text-xs text-zinc-400">아바타 로딩 중...</div>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                {availableAvatars.map((avatar) => (
                  <button
                    key={avatar.character_key}
                    type="button"
                    onClick={() => setAvatarKey(avatar.character_key)}
                    className={`relative rounded-xl border-2 p-2 transition-all ${
                      avatarKey === avatar.character_key
                        ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-200"
                        : "border-zinc-200 hover:border-zinc-300 bg-white"
                    }`}
                  >
                    <div className="aspect-square rounded-lg bg-zinc-100 flex items-center justify-center overflow-hidden">
                      <img
                        src={`${API_BASE}/controlnet/ip-adapter/reference/${avatar.character_key}/image`}
                        alt={avatar.character_key}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          // Fallback to initial
                          e.currentTarget.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%23e5e7eb' width='100' height='100'/%3E%3Ctext x='50' y='50' text-anchor='middle' dy='.3em' fill='%239ca3af' font-size='40'%3E%3F%3C/text%3E%3C/svg%3E";
                        }}
                      />
                    </div>
                    <p className="text-[10px] text-zinc-600 mt-1 truncate text-center">
                      {avatar.character_key.replace(/_/g, " ")}
                    </p>
                    {avatarKey === avatar.character_key && (
                      <div className="absolute top-1 right-1 bg-indigo-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs">
                        ✓
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-zinc-50 border-t border-zinc-100 flex justify-end gap-3">
          <button
            onClick={handleSave}
            disabled={!canSave}
            className="rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 px-6 py-3 text-sm font-semibold text-white hover:from-indigo-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-indigo-500/20"
          >
            {initialProfile ? "저장" : "저장하고 시작하기"}
          </button>
        </div>
      </div>
    </div>
  );
}
