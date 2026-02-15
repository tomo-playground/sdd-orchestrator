"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { FORM_INPUT_COMPACT_CLASSES, FORM_LABEL_COMPACT_CLASSES } from "../ui/variants";

export type ProjectFormData = {
  name: string;
  handle: string;
  description: string;
};

type Props = {
  data: ProjectFormData;
  onChange: (data: ProjectFormData) => void;
};

export default function SetupWizardProjectStep({ data, onChange }: Props) {
  const [showMore, setShowMore] = useState(false);

  const inputCls = FORM_INPUT_COMPACT_CLASSES;
  const labelCls = FORM_LABEL_COMPACT_CLASSES;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-zinc-900">채널 만들기</h3>
        <p className="mt-1 text-xs text-zinc-500">콘텐츠를 발행할 채널을 설정합니다</p>
      </div>

      <div>
        <label htmlFor="wizard-project-name" className={labelCls}>
          채널 이름 *
        </label>
        <input
          id="wizard-project-name"
          value={data.name}
          onChange={(e) => onChange({ ...data, name: e.target.value })}
          placeholder="예: 내 애니메이션 채널"
          className={inputCls}
          autoFocus
        />
      </div>

      <button
        type="button"
        onClick={() => setShowMore((v) => !v)}
        className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-600"
      >
        {showMore ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        추가 옵션
      </button>

      {showMore && (
        <div className="space-y-3">
          <div>
            <label htmlFor="wizard-project-handle" className={labelCls}>
              Handle
            </label>
            <input
              id="wizard-project-handle"
              value={data.handle}
              onChange={(e) => onChange({ ...data, handle: e.target.value })}
              placeholder="@channel-handle"
              className={inputCls}
            />
          </div>
          <div>
            <label htmlFor="wizard-project-desc" className={labelCls}>
              설명
            </label>
            <input
              id="wizard-project-desc"
              value={data.description}
              onChange={(e) => onChange({ ...data, description: e.target.value })}
              placeholder="채널에 대한 간단한 설명"
              className={inputCls}
            />
          </div>
        </div>
      )}
    </div>
  );
}
