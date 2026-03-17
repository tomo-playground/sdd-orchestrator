import { describe, it, expect } from "vitest";

/**
 * Tests for video data restore logic from DB.
 * Validates that video URLs are correctly mapped by label (full/post).
 */

type RecentVideo = {
  url: string;
  label?: string;
  created_at: number;
};

/** Mirrors the logic in useStudioInitialization.ts video restore */
function restoreVideoOutput(data: { video_url: string | null; recent_videos: RecentVideo[] }) {
  const recentVideos = data.recent_videos || [];
  const latestFull = recentVideos.find((v) => v.label === "full");
  const latestPost = recentVideos.find((v) => v.label === "post");
  return {
    videoUrl: data.video_url || null,
    videoUrlFull: latestFull?.url || data.video_url || null,
    videoUrlPost: latestPost?.url || null,
    recentVideos,
  };
}

describe("restoreVideoOutput", () => {
  it("restores full video from recent_videos label", () => {
    const result = restoreVideoOutput({
      video_url: "http://minio/full.mp4",
      recent_videos: [
        { url: "http://minio/full.mp4", label: "full", created_at: 1000 },
        { url: "http://minio/post.mp4", label: "post", created_at: 900 },
      ],
    });
    expect(result.videoUrlFull).toBe("http://minio/full.mp4");
    expect(result.videoUrlPost).toBe("http://minio/post.mp4");
  });

  it("falls back to video_url for full when no label match", () => {
    const result = restoreVideoOutput({
      video_url: "http://minio/latest.mp4",
      recent_videos: [],
    });
    expect(result.videoUrlFull).toBe("http://minio/latest.mp4");
    expect(result.videoUrlPost).toBeNull();
  });

  it("handles null video_url with no recent_videos", () => {
    const result = restoreVideoOutput({
      video_url: null,
      recent_videos: [],
    });
    expect(result.videoUrl).toBeNull();
    expect(result.videoUrlFull).toBeNull();
    expect(result.videoUrlPost).toBeNull();
  });

  it("correctly separates post and full from recent_videos", () => {
    const result = restoreVideoOutput({
      video_url: "http://minio/post.mp4", // Most recent is post
      recent_videos: [
        { url: "http://minio/post.mp4", label: "post", created_at: 2000 },
        { url: "http://minio/full.mp4", label: "full", created_at: 1000 },
      ],
    });
    // video_url is the most recent (post), but videoUrlFull should still be the full one
    expect(result.videoUrl).toBe("http://minio/post.mp4");
    expect(result.videoUrlFull).toBe("http://minio/full.mp4");
    expect(result.videoUrlPost).toBe("http://minio/post.mp4");
  });

  it("preserves recentVideos array", () => {
    const videos = [
      { url: "http://minio/v1.mp4", label: "full", created_at: 1000 },
      { url: "http://minio/v2.mp4", label: "post", created_at: 900 },
    ];
    const result = restoreVideoOutput({
      video_url: "http://minio/v1.mp4",
      recent_videos: videos,
    });
    expect(result.recentVideos).toHaveLength(2);
  });
});
