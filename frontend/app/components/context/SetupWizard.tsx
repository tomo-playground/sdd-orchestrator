"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { useProjectGroups } from "../../hooks/useProjectGroups";
import { createProject, fetchProjects } from "../../store/actions/projectActions";
import { createGroup } from "../../store/actions/groupActions";
import { useUIStore } from "../../store/useUIStore";
import { API_BASE } from "../../constants";
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

  const handleQuickStart = async () => {
    setSaving(true);
    const { showToast } = useUIStore.getState();
    try {
      const res = await axios.post<{ project_id: number; group_id: number }>(
        `${API_BASE}/projects/quick-start`
      );
      await fetchProjects();
      selectProject(res.data.project_id);
      selectGroup(res.data.group_id);
      onClose();
      router.push("/studio?new=true");
    } catch {
      showToast("빠른 시작에 실패했습니다", "error");
    } finally {
      setSaving(false);
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
          <>
            <SetupWizardProjectStep data={projectData} onChange={setProjectData} />
            <div className="mt-4 flex items-center gap-3">
              <div className="h-px flex-1 bg-zinc-700" />
              <span className="text-xs text-zinc-500">또는</span>
              <div className="h-px flex-1 bg-zinc-700" />
            </div>
            <div className="mt-3 text-center">
              <Button
                variant="outline"
                size="sm"
                loading={saving}
                onClick={handleQuickStart}
              >
                빠른 시작
              </Button>
              <p className="mt-1.5 text-xs text-zinc-500">
                기본 설정으로 바로 시작합니다
              </p>
            </div>
          </>
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
