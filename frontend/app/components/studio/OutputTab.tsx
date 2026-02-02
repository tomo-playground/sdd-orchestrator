"use client";

import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { API_BASE } from "../../constants";
import { updateStoryboardMetadata } from "../../store/actions/storyboardActions";

export default function OutputTab() {
  const store = useStudioStore();
  const { setOutput, showToast } = store;

  const videoCaption = useStudioStore((s) => s.videoCaption);
  const videoLikesCount = useStudioStore((s) => s.videoLikesCount);
  const captionInitialized = useRef(false);
  const [isExtractingCaption, setIsExtractingCaption] = useState(false);
  const likesInitialized = useRef(false);

  // Auto-populate video metadata with smart defaults (only once)
  useEffect(() => {
    if (!captionInitialized.current && !videoCaption && store.topic) {
      captionInitialized.current = true;
      axios
        .post(`${API_BASE}/video/extract-hashtags`, { text: store.topic })
        .then((res) => {
          if (res.data.caption) {
            setOutput({ videoCaption: res.data.caption });
            updateStoryboardMetadata({ default_caption: res.data.caption });
          }
        })
        .catch(() => {
          setOutput({ videoCaption: store.topic });
        });
    }
    if (!likesInitialized.current && !videoLikesCount) {
      setOutput({ videoLikesCount: `${Math.floor(Math.random() * 50 + 10)}K` });
      likesInitialized.current = true;
    }
  }, [store.topic, videoCaption, videoLikesCount, setOutput]);

  // Extract caption using LLM
  const handleExtractCaption = async () => {
    if (!videoCaption || videoCaption.length <= 60) {
      showToast("캡션이 이미 60자 이내입니다", "success");
      return;
    }

    setIsExtractingCaption(true);
    try {
      const res = await axios.post(`${API_BASE}/video/extract-caption`, {
        text: videoCaption
      });

      if (res.data.caption) {
        setOutput({ videoCaption: res.data.caption });
        updateStoryboardMetadata({ default_caption: res.data.caption });
        showToast(
          res.data.fallback
            ? "캡션을 잘라냈습니다"
            : `캡션 요약 완료 (${res.data.original_length} → ${res.data.caption.length}자)`,
          "success"
        );
      }
    } catch (err: any) {
      console.error("Caption extraction failed:", err);
      showToast(err.response?.data?.detail || "캡션 요약 실패", "error");
    } finally {
      setIsExtractingCaption(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Video Metadata */}
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 space-y-3">
        <h3 className="text-sm font-bold text-zinc-800">영상 메타데이터</h3>
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-semibold text-zinc-600">
              캡션 (이 영상) <span className="text-red-500">*</span>
            </label>
            <div className="flex items-center gap-2">
              {videoCaption.length > 60 && (
                <button
                  onClick={handleExtractCaption}
                  disabled={isExtractingCaption}
                  className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-600 hover:bg-indigo-200 disabled:opacity-50 transition-colors"
                  title="LLM으로 캡션 요약"
                >
                  {isExtractingCaption ? "..." : "요약"}
                </button>
              )}
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${videoCaption.length >= 60 ? 'bg-red-100 text-red-600' :
                videoCaption.length >= 50 ? 'bg-amber-100 text-amber-600' :
                  'text-zinc-400'
                }`}>
                {videoCaption.length}/60
              </span>
            </div>
          </div>
          <input
            type="text"
            value={videoCaption}
            onChange={(e) => setOutput({ videoCaption: e.target.value })}
            onBlur={(e) => updateStoryboardMetadata({ default_caption: e.target.value })}
            placeholder={`예: ${store.topic || "AI 생성 영상"}`}
            className={`w-full rounded-xl border px-3 py-2 text-sm outline-none focus:ring-2 transition-colors ${videoCaption.length >= 60
              ? 'border-red-300 focus:border-red-400 focus:ring-red-50 bg-red-50/30'
              : videoCaption.length >= 50
                ? 'border-amber-300 focus:border-amber-400 focus:ring-amber-50 bg-amber-50/30'
                : 'border-zinc-200 focus:border-indigo-400 focus:ring-indigo-50'
              }`}
          />
          <div className="flex items-start gap-1 mt-1">
            {videoCaption.length >= 60 ? (
              <p className="text-[10px] text-red-600 font-medium">
                최대 60자 제한 (가로폭 초과 시 잘림)
              </p>
            ) : videoCaption.length >= 50 ? (
              <p className="text-[10px] text-amber-600 font-medium">
                50자 초과 - 간결하게 작성 권장
              </p>
            ) : videoCaption ? (
              <p className="text-[10px] text-zinc-400">
                가로폭 고려하여 60자 이내 권장
              </p>
            ) : (
              <p className="text-[10px] text-zinc-400">
                비워두면 스토리보드 주제가 사용됩니다
              </p>
            )}
          </div>
        </div>
        <div>
          <label className="block text-xs font-semibold text-zinc-600 mb-1">
            좋아요 수 (선택)
          </label>
          <input
            type="text"
            value={videoLikesCount}
            onChange={(e) => setOutput({ videoLikesCount: e.target.value })}
            placeholder="예: 1.2K (비워두면 랜덤)"
            className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-50"
          />
        </div>
      </div>
    </div>
  );
}
