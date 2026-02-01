"use client";

import { useEffect, useState } from "react";
import { useStudioStore } from "../store/useStudioStore";

interface UseStudioOnboardingOptions {
  isLoadingDb: boolean;
  storyboardId: string | null;
  needsStyleProfile: boolean;
}

/**
 * Handles studio onboarding logic:
 * - Channel profile modal on first visit
 * - Style profile modal for new storyboards
 * - Keyboard shortcuts (ArrowLeft/Right, Escape)
 */
export function useStudioOnboarding({
  isLoadingDb,
  storyboardId,
  needsStyleProfile,
}: UseStudioOnboardingOptions) {
  const [showChannelProfileModal, setShowChannelProfileModal] = useState(false);
  const [showStyleProfileModal, setShowStyleProfileModal] = useState(false);

  const hasValidProfile = useStudioStore((s) => s.hasValidProfile);
  const currentStyleProfile = useStudioStore((s) => s.currentStyleProfile);

  // Channel Profile Onboarding (first visit auto-show)
  useEffect(() => {
    const hasProfile = hasValidProfile();
    const hasSeenOnboarding = localStorage.getItem("channel_onboarding_done");

    if (!hasProfile && !hasSeenOnboarding) {
      setShowChannelProfileModal(true);
      localStorage.setItem("channel_onboarding_done", "true");
    }
  }, [hasValidProfile]);

  // Style Profile Selection (new storyboards only)
  useEffect(() => {
    const hasProfile = hasValidProfile();

    // Skip while loading DB or if channel profile modal is showing
    if (isLoadingDb || storyboardId || showChannelProfileModal) {
      return;
    }

    // Show modal if profile exists but no style profile selected
    if (hasProfile && !currentStyleProfile) {
      const styleOnboardingDone = sessionStorage.getItem(
        "style_onboarding_done"
      );
      if (!styleOnboardingDone) {
        setShowStyleProfileModal(true);
        sessionStorage.setItem("style_onboarding_done", "true");
      }
    }
  }, [
    hasValidProfile,
    currentStyleProfile,
    showChannelProfileModal,
    isLoadingDb,
    storyboardId,
  ]);

  // DB-loaded storyboard without style profile
  useEffect(() => {
    if (needsStyleProfile && !isLoadingDb) {
      setShowStyleProfileModal(true);
    }
  }, [needsStyleProfile, isLoadingDb]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      )
        return;

      const { scenes: sc, currentSceneIndex: idx } =
        useStudioStore.getState();
      if (e.key === "ArrowLeft" && sc.length > 0) {
        e.preventDefault();
        useStudioStore
          .getState()
          .setCurrentSceneIndex(Math.max(0, idx - 1));
      }
      if (e.key === "ArrowRight" && sc.length > 0) {
        e.preventDefault();
        useStudioStore
          .getState()
          .setCurrentSceneIndex(Math.min(sc.length - 1, idx + 1));
      }
      if (e.key === "Escape") {
        useStudioStore
          .getState()
          .setMeta({ imagePreviewSrc: null, videoPreviewSrc: null });
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return {
    showChannelProfileModal,
    setShowChannelProfileModal,
    showStyleProfileModal,
    setShowStyleProfileModal,
  };
}
