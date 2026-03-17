import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useUIStore } from "../store/useUIStore";
import type { YouTubeCredential } from "../types";
import {
  checkYouTubeConnection,
  disconnectYouTube,
  getYouTubeAuthUrl,
  exchangeYouTubeCode,
} from "../store/actions/youtubeActions";

// ── Types ──────────────────────────────────────────────

type UseYouTubeTabParams = {
  projectId: number | null;
  oauthCode: string | null;
  oauthState: string | null;
};

// ── Hook ───────────────────────────────────────────────

export function useYouTubeTab({ projectId, oauthCode, oauthState }: UseYouTubeTabParams) {
  const showToast = useUIStore((s) => s.showToast);
  const router = useRouter();

  const [credential, setCredential] = useState<YouTubeCredential | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(!!oauthCode);
  const exchangeRef = useRef(false);

  // Check project YouTube connection
  useEffect(() => {
    const fetch = projectId ? () => checkYouTubeConnection(projectId) : () => Promise.resolve(null);

    fetch().then((cred) => {
      setCredential(cred);
      setIsLoading(false);
    });
  }, [projectId]);

  // Handle OAuth callback (code + state from URL)
  useEffect(() => {
    if (!oauthCode || !oauthState || exchangeRef.current) return;
    exchangeRef.current = true;

    exchangeYouTubeCode(oauthCode, oauthState).then((cred) => {
      setIsConnecting(false);
      if (cred) {
        setCredential(cred);
        showToast("YouTube 연동 완료", "success");
      } else {
        showToast("YouTube 연동에 실패했습니다", "error");
      }
      router.replace("/settings/youtube", { scroll: false });
    });
  }, [oauthCode, oauthState, showToast, router]);

  const handleConnect = useCallback(async () => {
    if (!projectId) return;
    const url = await getYouTubeAuthUrl(projectId);
    if (url) {
      window.location.href = url;
    } else {
      showToast("인증 URL 가져오기에 실패했습니다", "error");
    }
  }, [projectId, showToast]);

  const handleDisconnect = useCallback(async () => {
    if (!projectId) return;
    const ok = await disconnectYouTube(projectId);
    if (ok) {
      setCredential(null);
      showToast("YouTube 연동 해제 완료", "success");
    } else {
      showToast("연동 해제에 실패했습니다", "error");
    }
  }, [projectId, showToast]);

  return {
    credential,
    isLoading,
    isConnecting,
    handleConnect,
    handleDisconnect,
  };
}
