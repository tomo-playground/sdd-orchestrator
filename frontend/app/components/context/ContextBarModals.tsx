"use client";

import type { ProjectItem } from "../../types";
import type { ConfirmDialogProps } from "../ui/ConfirmDialog";
import GroupConfigEditor from "./GroupConfigEditor";
import ProjectFormModal from "./ProjectFormModal";
import SetupWizard from "./SetupWizard";
import ConfirmDialog from "../ui/ConfirmDialog";

type ContextBarModalsProps = {
  configGroupId: number | null;
  onCloseGroupConfig: () => void;

  projectModalMode: "edit" | null;
  projectId: number | null;
  projects: ProjectItem[];
  onSaveProject: (data: {
    name: string;
    description?: string;
    handle?: string;
    avatar_media_asset_id?: number | null;
  }) => Promise<void>;
  onCloseProjectModal: () => void;

  showSetupWizard: boolean;
  setupWizardInitialStep: 1 | 2;
  existingProjectId?: number;
  onCloseSetupWizard: () => void;

  dialogProps: ConfirmDialogProps;
};

export default function ContextBarModals({
  configGroupId,
  onCloseGroupConfig,
  projectModalMode,
  projectId,
  projects,
  onSaveProject,
  onCloseProjectModal,
  showSetupWizard,
  setupWizardInitialStep,
  existingProjectId,
  onCloseSetupWizard,
  dialogProps,
}: ContextBarModalsProps) {
  return (
    <>
      {configGroupId && <GroupConfigEditor groupId={configGroupId} onClose={onCloseGroupConfig} />}

      {projectModalMode === "edit" && projectId && (
        <ProjectFormModal
          project={projects.find((p) => p.id === projectId)}
          onSave={onSaveProject}
          onClose={onCloseProjectModal}
        />
      )}

      {showSetupWizard && (
        <SetupWizard
          initialStep={setupWizardInitialStep}
          existingProjectId={existingProjectId}
          onClose={onCloseSetupWizard}
        />
      )}

      <ConfirmDialog {...dialogProps} />
    </>
  );
}
