"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { FORM_INPUT_COMPACT_CLASSES, FORM_LABEL_COMPACT_CLASSES } from "../ui/variants";

export type GroupFormData = {
  name: string;
  description: string;
};

type Props = {
  data: GroupFormData;
  onChange: (data: GroupFormData) => void;
};

export default function SetupWizardGroupStep({ data, onChange }: Props) {
  const [showMore, setShowMore] = useState(false);

  const inputCls = FORM_INPUT_COMPACT_CLASSES;
  const labelCls = FORM_LABEL_COMPACT_CLASSES;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-zinc-900">시리즈 만들기</h3>
        <p className="mt-1 text-xs text-zinc-500">같은 스타일의 영상을 묶는 시리즈입니다</p>
      </div>

      <div>
        <label htmlFor="wizard-group-name" className={labelCls}>
          시리즈 이름 *
        </label>
        <input
          id="wizard-group-name"
          value={data.name}
          onChange={(e) => onChange({ ...data, name: e.target.value })}
          placeholder="예: 학교 일상 시리즈"
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
        <div>
          <label htmlFor="wizard-group-desc" className={labelCls}>
            설명
          </label>
          <input
            id="wizard-group-desc"
            value={data.description}
            onChange={(e) => onChange({ ...data, description: e.target.value })}
            placeholder="시리즈에 대한 간단한 설명"
            className={inputCls}
          />
        </div>
      )}
    </div>
  );
}
