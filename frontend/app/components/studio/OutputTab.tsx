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
      {/* Video Metadata — compact top bar */}
      <div className="flex items-end gap-3 rounded-xl border border-zinc-200 bg-white px-4 py-3">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <label className="text-[10px] font-semibold tracking-wider text-zinc-500 uppercase">
              캡션
            </label>
            <span
              className={`text-[10px] font-bold ${
                videoCaption.length >= 60
                  ? "text-red-500"
                  : videoCaption.length >= 50
                    ? "text-amber-500"
                    : "text-zinc-400"
              }`}
            >
              {videoCaption.length}/60
            </span>
            {videoCaption.length > 60 && (
              <button
                onClick={handleExtractCaption}
                disabled={isExtractingCaption}
                className="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-bold text-indigo-600 hover:bg-indigo-200 disabled:opacity-50"
              >
                {isExtractingCaption ? "..." : "요약"}
              </button>
            )}
            {savedField === "caption" && savedBadge}
          </div>
          <input
            type="text"
            value={videoCaption}
            onChange={(e) => setOutput({ videoCaption: e.target.value })}
            onBlur={(e) => handleCaptionBlur(e.target.value)}
            placeholder={store.topic || "AI 생성 영상"}
            className={`w-full rounded-lg border px-3 py-1.5 text-sm outline-none transition-colors focus:ring-1 ${
              videoCaption.length >= 60
                ? "border-red-300 bg-red-50/30 focus:ring-red-100"
                : "border-zinc-200 focus:border-zinc-400 focus:ring-zinc-100"
            }`}
          />
        </div>
        <div className="w-28 shrink-0">
          <div className="mb-1 flex items-center gap-2">
            <label className="text-[10px] font-semibold tracking-wider text-zinc-500 uppercase">
              좋아요
            </label>
            {savedField === "likes" && savedBadge}
          </div>
          <input
            type="text"
            value={videoLikesCount}
            onChange={(e) => setOutput({ videoLikesCount: e.target.value })}
            onBlur={handleLikesBlur}
            placeholder="1.2K"
            className="w-full rounded-lg border border-zinc-200 px-3 py-1.5 text-sm outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-100"
          />
        </div>
      </div>

      {/* Rendered Videos */}
      <RenderedVideosSection
        videoUrl={videoUrl}
        videoUrlFull={videoUrlFull}
        videoUrlPost={videoUrlPost}
        recentVideos={recentVideos}
        onVideoPreview={(src) => setMeta({ videoPreviewSrc: src })}
        onDeleteRecentVideo={handleDeleteRecentVideo}
      />
    </div>
  );
}
