import { useCallback, useEffect, useState } from "react";
import { useUIStore } from "../store/useUIStore";
import {
  checkYouTubeConnection,
  fetchYouTubeStatuses,
  lookupRenderHistoryId,
} from "../store/actions/youtubeActions";
import type { RecentVideo } from "../types";

export function useYouTubeUpload(projectId: number | null, recentVideos: RecentVideo[]) {
  const showToast = useUIStore((s) => s.showToast);

  const [ytConnected, setYtConnected] = useState(false);
  const [ytModalOpen, setYtModalOpen] = useState(false);
  const [ytRenderHistoryId, setYtRenderHistoryId] = useState(0);
  const [ytUploaded, setYtUploaded] = useState<Map<string, string>>(new Map());

  // Check project YouTube connection
  useEffect(() => {
    const fetch = projectId ? () => checkYouTubeConnection(projectId) : () => Promise.resolve(null);

    fetch().then((cred) => setYtConnected(!!cred));
  }, [projectId]);

  const refreshStatuses = useCallback(() => {
    const urls = recentVideos.map((v) => v.url);
    if (urls.length === 0) return;
    fetchYouTubeStatuses(urls).then((statuses) => {
      const map = new Map<string, string>();
      for (const [url, info] of Object.entries(statuses)) {
        map.set(url, info.video_id);
      }
      setYtUploaded(map);
    });
  }, [recentVideos]);

  // Fetch YouTube upload statuses for recent videos
  useEffect(() => {
    refreshStatuses();
  }, [refreshStatuses]);

  const handleUploadToYouTube = useCallback(
    async (videoUrl: string, renderHistoryId?: number) => {
      if (!ytConnected || !projectId) {
        showToast("Manage > YouTube에서 먼저 연동하세요", "warning");
        return;
      }
      let rhId = renderHistoryId;
      if (!rhId) {
        rhId = (await lookupRenderHistoryId(videoUrl)) ?? undefined;
      }
      if (!rhId) {
        showToast("렌더 이력을 찾을 수 없습니다", "error");
        return;
      }
      setYtRenderHistoryId(rhId);
      setYtModalOpen(true);
    },
    [ytConnected, projectId, showToast]
  );

  const closeModal = useCallback(() => {
    setYtModalOpen(false);
    refreshStatuses();
  }, [refreshStatuses]);

  return {
    ytConnected,
    ytModalOpen,
    ytRenderHistoryId,
    ytUploaded,
    handleUploadToYouTube,
    closeModal,
  };
}
