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

type StyleProfileModalProps = {
  defaultProfileId?: number | null;
  onComplete: (profile: {
    id: number;
    name: string;
    display_name: string | null;
    sd_model_name: string | null;
    loras: { name: string; trigger_words: string[]; weight: number }[];
    negative_embeddings: { name: string; trigger_word: string }[];
    positive_embeddings: { name: string; trigger_word: string }[];
    default_positive: string | null;
    default_negative: string | null;
  }) => void;
  onSkip?: () => void;
};

export default function StyleProfileModal({ defaultProfileId, onComplete, onSkip }: StyleProfileModalProps) {
  const [profiles, setProfiles] = useState<StyleProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchProfiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchProfiles = async () => {
    setIsLoading(true);
    try {
      const res = await axios.get<StyleProfile[]>(`${API_BASE}/style-profiles`);
      const profilesList = res.data || [];
      setProfiles(profilesList);

      // defaultProfileId가 있으면 그걸 선택, 없으면 첫 번째
      if (defaultProfileId && profilesList.find(p => p.id === defaultProfileId)) {
        setSelectedProfileId(defaultProfileId);
      } else if (profilesList.length > 0) {
        setSelectedProfileId(profilesList[0].id);
      }
    } catch (error) {
      console.error("Failed to fetch style profiles:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!selectedProfileId) return;

    const selected = profiles.find((p) => p.id === selectedProfileId);
    if (!selected) return;

    setIsSaving(true);

    try {
      // 프로필 상세 정보 조회 (sd_model 정보 포함)
      const res = await axios.get(`${API_BASE}/style-profiles/${selectedProfileId}`);
      const fullProfile = res.data;

      onComplete({
        id: selected.id,
        name: selected.name,
        display_name: selected.display_name,
        sd_model_name: fullProfile.sd_model?.name || fullProfile.sd_model?.display_name || null,
        loras: fullProfile.loras || [],
        negative_embeddings: fullProfile.negative_embeddings || [],
        positive_embeddings: fullProfile.positive_embeddings || [],
        default_positive: fullProfile.default_positive,
        default_negative: fullProfile.default_negative,
      });
    } catch (error) {
      console.error("Failed to load profile details:", error);
      // 에러가 나도 기본 정보로라도 진행
      onComplete({
        id: selected.id,
        name: selected.name,
        display_name: selected.display_name,
        sd_model_name: null,
        loras: [],
        negative_embeddings: [],
        positive_embeddings: [],
        default_positive: null,
        default_negative: null,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleSkip = () => {
    if (onSkip) {
      onSkip();
    }
  };

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl rounded-3xl border border-white/20 bg-white p-8 shadow-2xl">
        {/* Close Button */}
        {onSkip && (
          <button
            onClick={onSkip}
            className="absolute top-4 right-4 rounded-full p-2 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-zinc-900">스타일 프로필 선택</h2>
          <p className="mt-2 text-sm text-zinc-500">
            사용할 스타일 프로필을 선택하세요. Model + LoRAs + Embeddings가 세트로 로드됩니다.
          </p>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" color="text-zinc-400" />
          </div>
        ) : profiles.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-300 bg-zinc-50 p-12 text-center">
            <p className="text-sm text-zinc-500">등록된 스타일 프로필이 없습니다.</p>
            <p className="mt-2 text-xs text-zinc-400">
              Manage &gt; Style 페이지에서 프로필을 생성하세요.
            </p>
          </div>
        ) : (
          <>
            {/* Profile List */}
            <div className="mb-6 grid max-h-96 gap-3 overflow-y-auto">
              {profiles.map((profile) => (
                <button
                  key={profile.id}
                  onClick={() => setSelectedProfileId(profile.id)}
                  className={`group relative rounded-2xl border p-5 text-left transition-all duration-300 ${selectedProfileId === profile.id
                      ? "border-indigo-300 bg-indigo-50 shadow-lg shadow-indigo-500/10"
                      : "border-zinc-200 bg-white hover:border-indigo-200 hover:shadow-md"
                    }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <h3 className="text-sm font-bold text-zinc-900">
                          {profile.display_name || profile.name}
                        </h3>
                        {profile.is_default && (
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[8px] font-bold text-emerald-600 uppercase tracking-wider">
                            Default
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500 line-clamp-2">
                        {profile.description || "설명 없음"}
                      </p>
                    </div>
                    {/* Radio indicator */}
                    <div className={`shrink-0 h-5 w-5 rounded-full border-2 flex items-center justify-center transition-all ${selectedProfileId === profile.id
                        ? "border-indigo-500 bg-indigo-500"
                        : "border-zinc-300 bg-white"
                      }`}>
                      {selectedProfileId === profile.id && (
                        <div className="h-2 w-2 rounded-full bg-white" />
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}

        {/* Actions */}
        <div className="mt-6 flex gap-3">
          {onSkip && (
            <button
              onClick={handleSkip}
              disabled={isSaving}
              className="flex-1 rounded-full border border-zinc-300 bg-white px-6 py-3 text-sm font-semibold text-zinc-600 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              건너뛰기
            </button>
          )}
          <button
            onClick={handleConfirm}
            disabled={!selectedProfileId || isSaving || profiles.length === 0}
            className="flex-1 rounded-full bg-zinc-900 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isSaving ? (
              <div className="flex items-center justify-center gap-2">
                <LoadingSpinner size="sm" color="text-white/70" />
                <span>로딩 중...</span>
              </div>
            ) : (
              "선택 완료"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
