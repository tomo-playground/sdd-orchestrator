"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Modal from "../ui/Modal";
import { useStudioStore } from "../../store/useStudioStore";
import { pollUploadStatus, startYouTubeUpload } from "../../store/actions/youtubeActions";

type Props = {
  open: boolean;
  onClose: () => void;
  renderHistoryId: number;
  projectId: number | null;
};

export default function YouTubeUploadModal({ open, onClose, renderHistoryId, projectId }: Props) {
  if (!open || !projectId) return null;
  return (
    <Modal open onClose={onClose} size="md">
      <YouTubeUploadForm
        onClose={onClose}
        renderHistoryId={renderHistoryId}
        projectId={projectId}
      />
    </Modal>
  );
}

/** Inner form — remounted on each open so state is always fresh. */
function YouTubeUploadForm({
  onClose,
  renderHistoryId,
  projectId,
}: {
  onClose: () => void;
  renderHistoryId: number;
  projectId: number;
}) {
  const videoCaption = useStudioStore((s) => s.videoCaption);
  const topic = useStudioStore((s) => s.topic);
  const showToast = useStudioStore((s) => s.showToast);

  const [title, setTitle] = useState(topic || "");
  const [description, setDescription] = useState(videoCaption || "");
  const [tags, setTags] = useState("");
  const [privacy, setPrivacy] = useState("private");
  const [uploading, setUploading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollCountRef = useRef(0);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleUpload = useCallback(async () => {
    if (!title.trim()) return;

    setUploading(true);
    const tagList = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const result = await startYouTubeUpload({
      project_id: projectId,
      render_history_id: renderHistoryId,
      title: title.trim(),
      description,
      tags: tagList,
      privacy_status: privacy,
    });

    if (!result) {
      showToast("Failed to start upload", "error");
      setUploading(false);
      return;
    }

    showToast("Upload started", "success");

    // Poll for completion (max 60 polls × 3s = 3 min timeout)
    pollCountRef.current = 0;
    pollRef.current = setInterval(async () => {
      pollCountRef.current += 1;
      if (pollCountRef.current >= 60) {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
        showToast("Upload timed out — check YouTube Studio", "warning");
        setUploading(false);
        return;
      }

      const status = await pollUploadStatus(renderHistoryId);
      if (!status) return;

      if (status.youtube_upload_status === "completed") {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
        showToast(`Uploaded to YouTube: ${status.youtube_video_id}`, "success");
        setUploading(false);
        onClose();
      } else if (status.youtube_upload_status === "failed") {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
        showToast("YouTube upload failed", "error");
        setUploading(false);
      }
    }, 3000);
  }, [title, description, tags, privacy, renderHistoryId, projectId, showToast, onClose]);

  return (
    <>
      <Modal.Header>
        <h3 className="text-sm font-semibold text-zinc-900">Upload to YouTube</h3>
        {!uploading && (
          <button onClick={onClose} className="text-zinc-400 transition hover:text-zinc-600">
            &#x2715;
          </button>
        )}
      </Modal.Header>

      <div className="grid gap-4 px-5 py-4">
        {/* Title */}
        <div>
          <label
            htmlFor="yt-title"
            className="mb-1 block text-[10px] font-semibold tracking-widest text-zinc-400 uppercase"
          >
            Title
          </label>
          <input
            id="yt-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={100}
            disabled={uploading}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-100 disabled:opacity-50"
            placeholder="Video title"
          />
          <span className="mt-0.5 block text-right text-[10px] text-zinc-300">
            {title.length}/100
          </span>
        </div>

        {/* Description */}
        <div>
          <label
            htmlFor="yt-desc"
            className="mb-1 block text-[10px] font-semibold tracking-widest text-zinc-400 uppercase"
          >
            Description
          </label>
          <textarea
            id="yt-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            disabled={uploading}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-100 disabled:opacity-50"
            placeholder="Video description"
          />
        </div>

        {/* Tags */}
        <div>
          <label
            htmlFor="yt-tags"
            className="mb-1 block text-[10px] font-semibold tracking-widest text-zinc-400 uppercase"
          >
            Tags (comma separated)
          </label>
          <input
            id="yt-tags"
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            disabled={uploading}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-100 disabled:opacity-50"
            placeholder="shorts, anime, AI"
          />
        </div>

        {/* Privacy */}
        <div>
          <label
            htmlFor="yt-privacy"
            className="mb-1 block text-[10px] font-semibold tracking-widest text-zinc-400 uppercase"
          >
            Privacy
          </label>
          <select
            id="yt-privacy"
            value={privacy}
            onChange={(e) => setPrivacy(e.target.value)}
            disabled={uploading}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-100 disabled:opacity-50"
          >
            <option value="private">Private</option>
            <option value="unlisted">Unlisted</option>
            <option value="public">Public</option>
          </select>
        </div>

        {/* Upload progress */}
        {uploading && (
          <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
            <div className="h-3 w-3 animate-spin rounded-full border-2 border-amber-300 border-t-amber-600" />
            Uploading to YouTube...
          </div>
        )}
      </div>

      <Modal.Footer>
        <button
          onClick={onClose}
          disabled={uploading}
          className="rounded-lg border border-zinc-200 px-3 py-1.5 text-xs text-zinc-500 transition hover:bg-zinc-50 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={handleUpload}
          disabled={uploading || !title.trim()}
          className="rounded-lg bg-red-600 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Upload"}
        </button>
      </Modal.Footer>
    </>
  );
}
