import axios from "axios";
import { API_BASE } from "../../constants";
import type { YouTubeCredential, YouTubeUploadStatus } from "../../types";

export async function checkYouTubeConnection(projectId: number): Promise<YouTubeCredential | null> {
  try {
    const res = await axios.get<YouTubeCredential>(`${API_BASE}/youtube/credentials/${projectId}`);
    return res.data;
  } catch (err) {
    if (axios.isAxiosError(err) && (err.response?.status === 404 || !err.response)) return null;
    throw err;
  }
}

export async function getYouTubeAuthUrl(projectId: number): Promise<string | null> {
  try {
    const res = await axios.get<{ auth_url: string }>(`${API_BASE}/youtube/authorize/${projectId}`);
    return res.data.auth_url;
  } catch {
    return null;
  }
}

export async function exchangeYouTubeCode(
  code: string,
  state: string
): Promise<YouTubeCredential | null> {
  try {
    const res = await axios.post<YouTubeCredential>(`${API_BASE}/youtube/callback`, null, {
      params: { code, state },
    });
    return res.data;
  } catch {
    return null;
  }
}

export async function disconnectYouTube(projectId: number): Promise<boolean> {
  try {
    await axios.delete(`${API_BASE}/youtube/credentials/${projectId}`);
    return true;
  } catch {
    return false;
  }
}

export async function startYouTubeUpload(data: {
  project_id: number;
  render_history_id: number;
  title: string;
  description?: string;
  tags?: string[];
  privacy_status?: string;
}): Promise<YouTubeUploadStatus | null> {
  try {
    const res = await axios.post<YouTubeUploadStatus>(`${API_BASE}/youtube/upload`, data);
    return res.data;
  } catch {
    return null;
  }
}

export async function fetchYouTubeStatuses(
  videoUrls: string[]
): Promise<Record<string, { video_id: string; status: string }>> {
  try {
    const res = await axios.post<{
      statuses: Record<string, { video_id: string; status: string }>;
    }>(`${API_BASE}/video/youtube-statuses`, { video_urls: videoUrls });
    return res.data.statuses;
  } catch {
    return {};
  }
}

export async function lookupRenderHistoryId(videoUrl: string): Promise<number | null> {
  try {
    const res = await axios.get<{ render_history_id: number }>(
      `${API_BASE}/video/render-history-lookup`,
      { params: { video_url: videoUrl } }
    );
    return res.data.render_history_id;
  } catch {
    return null;
  }
}

export async function pollUploadStatus(
  renderHistoryId: number
): Promise<YouTubeUploadStatus | null> {
  try {
    const res = await axios.get<YouTubeUploadStatus>(
      `${API_BASE}/youtube/upload-status/${renderHistoryId}`
    );
    return res.data;
  } catch {
    return null;
  }
}
