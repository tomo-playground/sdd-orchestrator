"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { createProject } from "../../store/actions/projectActions";
import { createGroup } from "../../store/actions/groupActions";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import SetupWizardStepIndicator from "./SetupWizardStepIndicator";
import SetupWizardProjectStep, { type ProjectFormData } from "./SetupWizardProjectStep";
import SetupWizardGroupStep, { type GroupFormData } from "./SetupWizardGroupStep";

type Props = {
  initialStep?: 1 | 2;
  existingProjectId?: number;
  onClose: () => void;
};

export default function SetupWizard({ initialStep = 1, existingProjectId, onClose }: Props) {
  const router = useRouter();
  const { selectProject, selectGroup } = useProjectGroups();

  const [currentStep, setCurrentStep] = useState<1 | 2>(initialStep);
  const [saving, setSaving] = useState(false);
  const [createdProjectId, setCreatedProjectId] = useState<number | undefined>(existingProjectId);

  const [projectData, setProjectData] = useState<ProjectFormData>({
    name: "",
    handle: "",
    description: "",
  });
  const [groupData, setGroupData] = useState<GroupFormData>({
    name: "",
    description: "",
  });

  const completedSteps = currentStep === 2 ? [1] : [];

  const handleNext = async () => {
    if (!projectData.name.trim()) return;
    setSaving(true);
    try {
      const payload: Parameters<typeof createProject>[0] = {
        name: projectData.name.trim(),
        ...(projectData.handle.trim() && { handle: projectData.handle.trim() }),
        ...(projectData.description.trim() && { description: projectData.description.trim() }),
      };
      const project = await createProject(payload);
      if (!project) return;
      selectProject(project.id);
      setCreatedProjectId(project.id);
      setCurrentStep(2);
    } finally {
      setSaving(false);
    }
  };

  const handleComplete = async () => {
    if (!groupData.name.trim() || !createdProjectId) return;
    setSaving(true);
    try {
      const payload: Parameters<typeof createGroup>[0] = {
        project_id: createdProjectId,
        name: groupData.name.trim(),
        ...(groupData.description.trim() && { description: groupData.description.trim() }),
      };
      const group = await createGroup(payload);
      if (!group) return;
      selectGroup(group.id);
      onClose();
      router.push("/studio?new=true");
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    if (currentStep === 2 && initialStep === 1) {
      setCurrentStep(1);
    }
  };

  const canGoNext = currentStep === 1 && projectData.name.trim().length > 0;
  const canComplete = currentStep === 2 && groupData.name.trim().length > 0;
  const showBackButton = currentStep === 2 && initialStep === 1;

  return (
    <Modal open onClose={onClose} size="sm">
      <div className="px-5 pt-4">
        <SetupWizardStepIndicator currentStep={currentStep} completedSteps={completedSteps} />
      </div>

      <div className="px-5 py-4">
        {currentStep === 1 ? (
          <SetupWizardProjectStep data={projectData} onChange={setProjectData} />
        ) : (
          <SetupWizardGroupStep data={groupData} onChange={setGroupData} />
        )}
      </div>

      <Modal.Footer>
        <div className="flex w-full items-center justify-between">
          <div>
            {showBackButton && (
              <Button variant="ghost" size="sm" onClick={handleBack} disabled={saving}>
                이전
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={saving}>
              취소
            </Button>
            {currentStep === 1 ? (
              <Button size="sm" loading={saving} disabled={!canGoNext} onClick={handleNext}>
                다음
              </Button>
            ) : (
              <Button size="sm" loading={saving} disabled={!canComplete} onClick={handleComplete}>
                완료 — 시작하기
              </Button>
            )}
          </div>
        </div>
      </Modal.Footer>
    </Modal>
  );
}
