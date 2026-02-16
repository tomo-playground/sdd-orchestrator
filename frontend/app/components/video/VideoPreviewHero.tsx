"use client";

import { Film, Maximize2 } from "lucide-react";

type VideoPreviewHeroProps = {
  videoUrl: string | null;
  onClickFullscreen?: (url: string) => void;
};

export default function VideoPreviewHero({ videoUrl, onClickFullscreen }: VideoPreviewHeroProps) {
  if (!videoUrl) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-zinc-200 bg-white/70 py-16">
        <Film className="h-10 w-10 text-zinc-300" />
        <p className="text-sm font-medium text-zinc-400">렌더링된 영상 없음</p>
        <p className="text-xs text-zinc-400">좌측에서 Render 버튼을 눌러 영상을 생성하세요</p>
      </div>
    );
  }

  return (
    <div className="relative mx-auto max-w-sm">
      <div className="aspect-[9/16] overflow-hidden rounded-2xl bg-black shadow-lg">
        <video
          key={videoUrl}
          controls
          playsInline
          preload="metadata"
          src={videoUrl}
          className="h-full w-full object-contain"
        />
      </div>
      {onClickFullscreen && (
        <button
          type="button"
          onClick={() => onClickFullscreen(videoUrl)}
          className="absolute top-2 right-2 rounded-lg bg-black/50 p-1.5 text-white transition hover:bg-black/70"
          title="전체 화면"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
