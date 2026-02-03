"use client";

import { useEffect, useState } from "react";
import { useStudioStore } from "../store/useStudioStore";
import { loadStyleProfileFromId } from "../store/actions/styleProfileActions";
import { hasValidProfile } from "../store/selectors/projectSelectors";

interface UseStudioOnboardingOptions {
  isLoadingDb: boolean;
  storyboardId: string | null;
  needsStyleProfile: boolean;
}

/**
 * Handles studio onboarding logic:
 * - Style profile modal for new storyboards
 * - Keyboard shortcuts (ArrowLeft/Right, Escape)
 */
export function useStudioOnboarding({
  isLoadingDb,
  storyboardId,
  needsStyleProfile,
}: UseStudioOnboardingOptions) {
  const [showStyleProfileModal, setShowStyleProfileModal] = useState(false);

  const currentStyleProfile = useStudioStore((s) => s.currentStyleProfile);
  const effectiveConfigLoaded = useStudioStore((s) => s.effectiveConfigLoaded);
  const effectiveStyleProfileId = useStudioStore((s) => s.effectiveStyleProfileId);

  // Style Profile Selection (DB-loaded storyboards only — new ones use inline selector)
  useEffect(() => {
    const hasProfile = hasValidProfile();

    // Wait for effective config to load (race condition prevention)
    if (isLoadingDb || !effectiveConfigLoaded) {
      return;
    }

    // New storyboard (no storyboardId) uses inline StyleProfileSelector — skip modal
    if (!storyboardId) return;

    // Show modal if profile exists but no style profile selected
    if (hasProfile && !currentStyleProfile) {
      // Cascade default available — auto-apply without modal
      if (effectiveStyleProfileId) {
        sessionStorage.setItem("style_onboarding_done", "true");
        loadStyleProfileFromId(effectiveStyleProfileId).catch(() => {
          setShowStyleProfileModal(true);
        });
        return;
      }

      // No cascade default — show modal (existing behavior)
      const styleOnboardingDone = sessionStorage.getItem(
        "style_onboarding_done"
      );
      if (!styleOnboardingDone) {
        setShowStyleProfileModal(true); // eslint-disable-line react-hooks/set-state-in-effect
        sessionStorage.setItem("style_onboarding_done", "true");
      }
    }
  }, [
    currentStyleProfile,
    isLoadingDb,
    storyboardId,
    effectiveConfigLoaded,
    effectiveStyleProfileId,
  ]);

  // DB-loaded storyboard without style profile — try cascade first
  useEffect(() => {
    if (!needsStyleProfile || isLoadingDb || !effectiveConfigLoaded) return;

    // Cascade default available — auto-apply without modal
    if (effectiveStyleProfileId) {
      loadStyleProfileFromId(effectiveStyleProfileId).catch(() => {
        setShowStyleProfileModal(true);
      });
      return;
    }

    // No cascade default — show modal
    setShowStyleProfileModal(true); // eslint-disable-line react-hooks/set-state-in-effect
  }, [needsStyleProfile, isLoadingDb, effectiveConfigLoaded, effectiveStyleProfileId]);

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
    showStyleProfileModal,
    setShowStyleProfileModal,
  };
}
