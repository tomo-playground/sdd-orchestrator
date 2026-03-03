"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { API_BASE } from "../../../../constants";
import { useUIStore } from "../../../../store/useUIStore";
import { getErrorMsg } from "../../../../utils/error";
import type { CharacterFull, GroupItem } from "../../../../types";
import Modal from "../../../../components/ui/Modal";
import Button from "../../../../components/ui/Button";
import Input from "../../../../components/ui/Input";

type Props = {
  character: CharacterFull;
  groups: GroupItem[];
  onClose: () => void;
};

type DuplicateResponse = {
  id: number;
  name: string;
  group_id: number;
  group_name: string | null;
};

export default function DuplicateDialog({ character, groups, onClose }: Props) {
  const router = useRouter();
  const showToast = useUIStore((s) => s.showToast);

  const [targetGroupId, setTargetGroupId] = useState<number>(character.group_id);
  const [newName, setNewName] = useState(character.name);
  const [copyLoras, setCopyLoras] = useState(false);
  const [copyPreview, setCopyPreview] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!newName.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await axios.post<DuplicateResponse>(
        `${API_BASE}/characters/${character.id}/duplicate`,
        {
          target_group_id: targetGroupId,
          new_name: newName.trim(),
          copy_loras: copyLoras,
          copy_preview: copyPreview,
        }
      );
      showToast(`복제 완료: ${res.data.name}`, "success");
      onClose();
      router.push(`/library/characters/${res.data.id}`);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setError("같은 이름의 캐릭터가 이미 존재합니다");
      } else {
        setError(getErrorMsg(err, "복제 실패"));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal open onClose={onClose} size="sm" persistent>
      <Modal.Header>
        <h3 className="text-base font-semibold text-zinc-900">캐릭터 복제</h3>
      </Modal.Header>

      <div className="space-y-4 px-5 py-4">
        {/* Target series */}
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">대상 시리즈</label>
          <select
            value={targetGroupId}
            onChange={(e) => setTargetGroupId(Number(e.target.value))}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          >
            {groups.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
                {g.id === character.group_id ? " (현재)" : ""}
              </option>
            ))}
          </select>
        </div>

        {/* New name */}
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-500">새 이름</label>
          <Input
            value={newName}
            onChange={(e) => {
              setNewName(e.target.value);
              setError(null);
            }}
            placeholder="캐릭터 이름"
            maxLength={100}
            autoFocus
          />
          {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
        </div>

        {/* Copy options */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-zinc-500">복제 항목</p>
          <label className="flex items-center gap-2 text-sm text-zinc-600">
            <input type="checkbox" checked disabled className="accent-zinc-700" />
            기본 정보 + 태그 (항상 포함)
          </label>
          <label className="flex items-center gap-2 text-sm text-zinc-600">
            <input
              type="checkbox"
              checked={copyLoras}
              onChange={(e) => setCopyLoras(e.target.checked)}
              className="accent-zinc-700"
            />
            LoRA 설정
          </label>
          <label className="flex items-center gap-2 text-sm text-zinc-600">
            <input
              type="checkbox"
              checked={copyPreview}
              onChange={(e) => setCopyPreview(e.target.checked)}
              className="accent-zinc-700"
            />
            프리뷰 이미지
          </label>
        </div>
      </div>

      <Modal.Footer>
        <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
          취소
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={handleSubmit}
          loading={isSubmitting}
          disabled={!newName.trim() || isSubmitting}
        >
          복제
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
