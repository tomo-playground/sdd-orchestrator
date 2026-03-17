"use client";

import { useUIStore } from "../../store/useUIStore";
import { useContextStore } from "../../store/useContextStore";
import ImagePreviewModal from "../ui/ImagePreviewModal";
import VideoPreviewModal from "../ui/VideoPreviewModal";
import StyleProfileModal from "../setup/StyleProfileModal";
import { GroupFormModal } from "../context";
import PreflightModal from "../common/PreflightModal";
import { createGroup } from "../../store/actions/groupActions";
import { persistStoryboard } from "../../store/actions/storyboardActions";
import { handleStyleProfileComplete } from "../../store/actions/styleProfileActions";
import { runPreflight, buildPreflightInput } from "../../utils/preflight";
import { runAutoRunFromStep } from "../../store/actions/autopilotActions";
import type { AutoRunStepId } from "../../utils/preflight";
import type { UseAutopilotReturn } from "../../hooks/useAutopilot";

interface StudioModalsProps {
  autopilot: UseAutopilotReturn;
  loadedProfileId: number | null;
  showStyleProfileModal: boolean;
  setShowStyleProfileModal: (v: boolean) => void;
  showGroupModal: boolean;
  setShowGroupModal: (v: boolean) => void;
}

export default function StudioModals({
  autopilot,
  loadedProfileId,
  showStyleProfileModal,
  setShowStyleProfileModal,
  showGroupModal,
  setShowGroupModal,
}: StudioModalsProps) {
  const setUI = useUIStore((s) => s.set);
  const imagePreviewSrc = useUIStore((s) => s.imagePreviewSrc);
  const imagePreviewCandidates = useUIStore((s) => s.imagePreviewCandidates);
  const videoPreviewSrc = useUIStore((s) => s.videoPreviewSrc);
  const showToast = useUIStore((s) => s.showToast);
  const showPreflightModal = useUIStore((s) => s.showPreflightModal);
  const projectId = useContextStore((s) => s.projectId);
  const setContext = useContextStore((s) => s.setContext);

  return (
    <>
      <ImagePreviewModal
        src={imagePreviewSrc}
        candidates={imagePreviewCandidates || undefined}
        onClose={() => setUI({ imagePreviewSrc: null, imagePreviewCandidates: null })}
      />

      <VideoPreviewModal src={videoPreviewSrc} onClose={() => setUI({ videoPreviewSrc: null })} />

      {showGroupModal && projectId && (
        <GroupFormModal
          projectId={projectId}
          onSave={async (data) => {
            const g = await createGroup(data as Parameters<typeof createGroup>[0]);
            if (g) setContext({ groupId: g.id });
          }}
          onClose={() => setShowGroupModal(false)}
        />
      )}

      {showStyleProfileModal && (
        <StyleProfileModal
          defaultProfileId={loadedProfileId}
          onComplete={(profile) =>
            handleStyleProfileComplete(profile, { setShowStyleProfileModal })
          }
          onSkip={() => {
            setShowStyleProfileModal(false);
            showToast("화풍 선택을 건너뛰었습니다", "success");
          }}
        />
      )}

      {showPreflightModal && (
        <PreflightModal
          isOpen
          preflight={runPreflight(buildPreflightInput())}
          onClose={() => setUI({ showPreflightModal: false })}
          onRun={async (stepsToRun: AutoRunStepId[]) => {
            setUI({ showPreflightModal: false });
            if (!useContextStore.getState().storyboardId) {
              const saved = await persistStoryboard();
              if (!saved) {
                showToast("스토리보드 저장에 실패했습니다.", "error");
                return;
              }
            }
            runAutoRunFromStep(stepsToRun[0] || "images", autopilot, stepsToRun);
          }}
        />
      )}
    </>
  );
}
