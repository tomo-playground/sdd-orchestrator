"use client";

import { useCallback, useState } from "react";
import axios from "axios";
import { useRenderStore } from "../../store/useRenderStore";
import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import { useStoryboardStore } from "../../store/useStoryboardStore";
import { API_BASE } from "../../constants";
import { updateStoryboardMetadata } from "../../store/actions/storyboardActions";
import { useYouTubeUpload } from "../../hooks/useYouTubeUpload";
import RenderedVideosSection from "../video/RenderedVideosSection";
import YouTubeUploadModal from "../youtube/YouTubeUploadModal";
import { Input, Textarea } from "../ui";

/**
 * Caption/Likes/YouTube section for the Publish tab.
 * Renders: rendered videos (left column), caption+likes (right column), YouTube modal.
 */
export function PublishVideosSection({
  compact = false,
  variant = "card",
}: {
  compact?: boolean;
  variant?: "card" | "list";
}) {
  const setOutput = useRenderStore((s) => s.set);
  const showToast = useUIStore((s) => s.showToast);
  const setUI = useUIStore((s) => s.set);
  const projectId = useContextStore((s) => s.projectId);
  const recentVideos = useRenderStore((s) => s.recentVideos);
  const videoUrl = useRenderStore((s) => s.videoUrl);
  const videoUrlFull = useRenderStore((s) => s.videoUrlFull);
  const videoUrlPost = useRenderStore((s) => s.videoUrlPost);

  const { ytModalOpen, ytRenderHistoryId, ytUploaded, handleUploadToYouTube, closeModal } =
    useYouTubeUpload(projectId, recentVideos);

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

  const hasVideos = !!(videoUrl || videoUrlFull || videoUrlPost || recentVideos.length > 0);
  if (!hasVideos) return null;

  return (
    <>
      <RenderedVideosSection
        videoUrl={videoUrl}
        videoUrlFull={videoUrlFull}
        videoUrlPost={videoUrlPost}
        recentVideos={recentVideos}
        uploadedMap={ytUploaded}
        onVideoPreview={(src) => setUI({ videoPreviewSrc: src })}
        onDeleteRecentVideo={handleDeleteRecentVideo}
        onUploadToYouTube={handleUploadToYouTube}
        compact={compact}
        variant={variant}
      />
      <YouTubeUploadModal
        open={ytModalOpen}
        onClose={closeModal}
        renderHistoryId={ytRenderHistoryId}
        projectId={projectId}
      />
    </>
  );
}

/** Caption & Likes inputs for the Publish right panel. */
export function PublishCaptionLikes() {
  const setOutput = useRenderStore((s) => s.set);
  const showToast = useUIStore((s) => s.showToast);
  const topic = useStoryboardStore((s) => s.topic);
  const videoCaption = useRenderStore((s) => s.videoCaption);
  const videoLikesCount = useRenderStore((s) => s.videoLikesCount);
  const [isExtractingCaption, setIsExtractingCaption] = useState(false);
  const [savedField, setSavedField] = useState<string | null>(null);

  const handleExtractCaption = async () => {
    if (!videoCaption || videoCaption.length <= 60) return;
    setIsExtractingCaption(true);
    try {
      const res = await axios.post(`${API_BASE}/video/extract-caption`, {
        text: videoCaption,
      });
      if (res.data.caption) {
        setOutput({ videoCaption: res.data.caption });
        updateStoryboardMetadata({ caption: res.data.caption });
        showToast(
          res.data.fallback
            ? "캡션을 잘라냈습니다"
            : `캡션 요약 완료 (${res.data.original_length} → ${res.data.caption.length}자)`,
          "success"
        );
      }
    } catch (err: unknown) {
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
      await updateStoryboardMetadata({ caption: value });
      flashSaved("caption");
    },
    [flashSaved]
  );

  const handleLikesBlur = useCallback(() => flashSaved("likes"), [flashSaved]);

  const savedBadge = (
    <span className="text-[12px] font-medium text-emerald-500 transition-opacity duration-300">
      Saved
    </span>
  );

  return (
    <>
      {/* Caption */}
      <div>
        <div className="mb-1.5 flex items-center gap-2">
          <label className="text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
            캡션
          </label>
          <span
            className={`text-[12px] font-bold ${
              videoCaption.length >= 60
                ? "text-red-500"
                : videoCaption.length >= 50
                  ? "text-amber-500"
                  : "text-zinc-400"
            }`}
          >
            {videoCaption.length}/60
          </span>
          {savedField === "caption" && savedBadge}
        </div>

        <Textarea
          value={videoCaption}
          onChange={(e) => setOutput({ videoCaption: e.target.value })}
          onBlur={(e) => handleCaptionBlur(e.target.value)}
          placeholder={topic || "AI 생성 영상"}
          rows={3}
          error={videoCaption.length >= 60}
          className="text-xs"
        />
        {videoCaption.length > 60 && (
          <button
            onClick={handleExtractCaption}
            disabled={isExtractingCaption}
            className="mt-1 w-full rounded-lg bg-indigo-50 px-2 py-1 text-[12px] font-semibold text-indigo-600 transition hover:bg-indigo-100 disabled:opacity-50"
          >
            {isExtractingCaption ? "요약 중..." : "AI 요약"}
          </button>
        )}
      </div>

      {/* Likes */}
      <div>
        <div className="mb-1.5 flex items-center gap-2">
          <label className="text-[12px] font-semibold tracking-wider text-zinc-500 uppercase">
            좋아요
          </label>
          {savedField === "likes" && savedBadge}
        </div>
        <Input
          type="text"
          value={videoLikesCount}
          onChange={(e) => setOutput({ videoLikesCount: e.target.value })}
          onBlur={() => handleLikesBlur()}
          placeholder="1.2K"
          className="text-xs"
        />
      </div>
    </>
  );
}
