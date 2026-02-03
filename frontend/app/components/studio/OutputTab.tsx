"use client";

import { useCallback, useState } from "react";
import axios from "axios";
import { useStudioStore } from "../../store/useStudioStore";
import { API_BASE } from "../../constants";
import { updateStoryboardMetadata } from "../../store/actions/storyboardActions";
import RenderedVideosSection from "../video/RenderedVideosSection";

export default function OutputTab() {
  const store = useStudioStore();
  const { setOutput, showToast, setMeta } = store;

  const videoUrl = useStudioStore((s) => s.videoUrl);
  const videoUrlFull = useStudioStore((s) => s.videoUrlFull);
  const videoUrlPost = useStudioStore((s) => s.videoUrlPost);
  const recentVideos = useStudioStore((s) => s.recentVideos);
  const videoCaption = useStudioStore((s) => s.videoCaption);
  const videoLikesCount = useStudioStore((s) => s.videoLikesCount);
  const [isExtractingCaption, setIsExtractingCaption] = useState(false);
  const [savedField, setSavedField] = useState<string | null>(null);

  const handleDeleteRecentVideo = useCallback(
    async (url: string) => {
      try {
        const filename = url.split("/").pop();
        if (!filename) return;
        await axios.post(`${API_BASE}/video/delete`, { filename });
        setOutput({
          recentVideos: recentVideos.filter((v) => v.url.split("/").pop() !== filename),
        });
        showToast("삭제 완료", "success");
      } catch {
        showToast("삭제 실패", "error");
      }
    },
    [recentVideos, setOutput, showToast]
  );

  // Extract caption using LLM
  const handleExtractCaption = async () => {
    if (!videoCaption || videoCaption.length <= 60) {
      showToast("캡션이 이미 60자 이내입니다", "success");
      return;
    }

    setIsExtractingCaption(true);
    try {
      const res = await axios.post(`${API_BASE}/video/extract-caption`, {
        text: videoCaption,
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
    } catch (err: unknown) {
      console.error("Caption extraction failed:", err);
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      showToast(axiosErr.response?.data?.detail || "캡션 요약 실패", "error");
    } finally {
      setIsExtractingCaption(false);
    }
  };

  const flashSaved = useCallback((field: string) => {
    setSavedField(field);
    setTimeout(() => setSavedField(null), 1500);
  }, []);

  const handleCaptionBlur = useCallback(
    async (value: string) => {
      await updateStoryboardMetadata({ default_caption: value });
      flashSaved("caption");
    },
    [flashSaved]
  );

  const handleLikesBlur = useCallback(() => flashSaved("likes"), [flashSaved]);

  const savedBadge = (
    <span className="text-[10px] font-medium text-emerald-500 transition-opacity duration-300">
      Saved
    </span>
  );

  return (
    <div className="space-y-6">
      {/* Rendered Videos */}
      <RenderedVideosSection
        videoUrl={videoUrl}
        videoUrlFull={videoUrlFull}
        videoUrlPost={videoUrlPost}
        recentVideos={recentVideos}
        onVideoPreview={(src) => setMeta({ videoPreviewSrc: src })}
        onDeleteRecentVideo={handleDeleteRecentVideo}
      />

      {/* Video Metadata */}
      <div className="space-y-3 rounded-2xl border border-zinc-200 bg-white p-4">
        <h3 className="text-sm font-bold text-zinc-800">영상 메타데이터</h3>
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="block text-xs font-semibold text-zinc-600">
              캡션 (이 영상) <span className="text-red-500">*</span>
            </label>
            <div className="flex items-center gap-2">
              {savedField === "caption" && savedBadge}
              {videoCaption.length > 60 && (
                <button
                  onClick={handleExtractCaption}
                  disabled={isExtractingCaption}
                  className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-600 transition-colors hover:bg-indigo-200 disabled:opacity-50"
                  title="LLM으로 캡션 요약"
                >
                  {isExtractingCaption ? "..." : "요약"}
                </button>
              )}
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                  videoCaption.length >= 60
                    ? "bg-red-100 text-red-600"
                    : videoCaption.length >= 50
                      ? "bg-amber-100 text-amber-600"
                      : "text-zinc-400"
                }`}
              >
                {videoCaption.length}/60
              </span>
            </div>
          </div>
          <input
            type="text"
            value={videoCaption}
            onChange={(e) => setOutput({ videoCaption: e.target.value })}
            onBlur={(e) => handleCaptionBlur(e.target.value)}
            placeholder={`예: ${store.topic || "AI 생성 영상"}`}
            className={`w-full rounded-xl border px-3 py-2 text-sm transition-colors outline-none focus:ring-2 ${
              videoCaption.length >= 60
                ? "border-red-300 bg-red-50/30 focus:border-red-400 focus:ring-red-50"
                : videoCaption.length >= 50
                  ? "border-amber-300 bg-amber-50/30 focus:border-amber-400 focus:ring-amber-50"
                  : "border-zinc-200 focus:border-indigo-400 focus:ring-indigo-50"
            }`}
          />
          <p
            className={`mt-1 text-[10px] ${
              videoCaption.length >= 60
                ? "font-medium text-red-600"
                : videoCaption.length >= 50
                  ? "font-medium text-amber-600"
                  : "text-zinc-400"
            }`}
          >
            {videoCaption.length >= 60
              ? "최대 60자 제한 (가로폭 초과 시 잘림)"
              : videoCaption.length >= 50
                ? "50자 초과 - 간결하게 작성 권장"
                : videoCaption
                  ? "가로폭 고려하여 60자 이내 권장"
                  : "비워두면 스토리보드 주제가 사용됩니다"}
          </p>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="text-xs font-semibold text-zinc-600">좋아요 수 (선택)</label>
            {savedField === "likes" && savedBadge}
          </div>
          <input
            type="text"
            value={videoLikesCount}
            onChange={(e) => setOutput({ videoLikesCount: e.target.value })}
            onBlur={handleLikesBlur}
            placeholder="예: 1.2K (비워두면 랜덤)"
            className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-50"
          />
        </div>
      </div>
    </div>
  );
}
