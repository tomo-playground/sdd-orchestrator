import { useCallback, useEffect, useRef, useState } from "react";

export type AudioPlayer = {
  playingUrl: string | null;
  play: (url: string) => void;
  stop: () => void;
};

export function useAudioPlayer(): AudioPlayer {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);
  const [playingUrl, setPlayingUrl] = useState<string | null>(null);

  const play = useCallback((url: string) => {
    // Stop current playback
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      const wasSameUrl = urlRef.current === url;
      urlRef.current = null;
      setPlayingUrl(null);
      if (wasSameUrl) return; // toggle off
    }
    // Start new playback
    const audio = new Audio(url);
    audioRef.current = audio;
    urlRef.current = url;
    setPlayingUrl(url);
    audio.play().catch(() => {
      setPlayingUrl(null);
      audioRef.current = null;
      urlRef.current = null;
    });
    audio.onended = () => {
      setPlayingUrl(null);
      audioRef.current = null;
      urlRef.current = null;
    };
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    urlRef.current = null;
    setPlayingUrl(null);
  }, []);

  useEffect(() => stop, [stop]);

  return { playingUrl, play, stop };
}
