"use client";

import { useState } from "react";
import axios from "axios";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import { API_BASE } from "../../constants";

type SceneEditImageModalProps = {
  sceneId: number;
  currentImageUrl: string;
  onClose: () => void;
  onAccept: (imageUrl: string, assetId: number) => void;
  showToast: (message: string, type: "success" | "error") => void;
};

const EDIT_PRESETS = [
  "밝게 웃으면서 정면 보기",
  "눈을 감고 평온한 표정",
  "머리를 풀어헤치고 미소짓게",
  "뒤돌아서 어깨 너머로 보기",
];

export default function SceneEditImageModal({
  sceneId,
  currentImageUrl,
  onClose,
  onAccept,
  showToast,
}: SceneEditImageModalProps) {
  const trapRef = useFocusTrap(true);
  const [instruction, setInstruction] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [editedImageUrl, setEditedImageUrl] = useState<string | null>(null);
  const [editedAssetId, setEditedAssetId] = useState<number | null>(null);
  const [editType, setEditType] = useState<string | null>(null);
  const [costUsd, setCostUsd] = useState<number>(0);

  const handleSubmit = async () => {
    if (!instruction.trim()) {
      showToast("편집 지시를 입력하세요", "error");
      return;
    }
    setIsLoading(true);
    setEditedImageUrl(null);
    try {
      const res = await axios.post(`${API_BASE}/scenes/${sceneId}/edit-image`, {
        edit_instruction: instruction.trim(),
        image_url: currentImageUrl,
      });
      const data = res.data;
      if (data.ok && data.image_url) {
        setEditedImageUrl(data.image_url);
        setEditedAssetId(data.asset_id ?? null);
        setEditType(data.edit_type ?? null);
        setCostUsd(data.cost_usd ?? 0);
      } else {
        showToast("이미지 편집에 실패했습니다", "error");
      }
    } catch {
      showToast("이미지 편집 요청 실패", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAccept = () => {
    if (editedImageUrl && editedAssetId != null) {
      onAccept(editedImageUrl, editedAssetId);
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-image-title"
    >
      <div
        ref={trapRef}
        tabIndex={-1}
        className="w-full max-w-2xl rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl outline-none"
      >
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 id="edit-image-title" className="text-lg font-semibold text-zinc-800">
            이미지 편집
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600"
          >
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Instruction input */}
          <div>
            <label htmlFor="edit-instruction" className="mb-2 block text-sm font-semibold text-zinc-700">
              어떻게 바꿀까요? (자연어로 입력)
            </label>
            <div className="mb-2 flex flex-wrap gap-2">
              {EDIT_PRESETS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => setInstruction(preset)}
                  className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs text-zinc-600 transition hover:border-indigo-300 hover:bg-indigo-50"
                >
                  {preset}
                </button>
              ))}
            </div>
            <textarea
              id="edit-instruction"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="예: 머리를 풀어헤치고 미소짓게 / 눈을 크게 뜨고 놀란 표정"
              className="w-full rounded-xl border border-zinc-200 bg-white/80 px-4 py-3 text-sm outline-none focus:border-indigo-400"
              rows={2}
              disabled={isLoading}
            />
          </div>

          {/* Before / After comparison */}
          {(editedImageUrl || isLoading) && (
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col items-center gap-1">
                <span className="text-[12px] font-semibold text-zinc-500">BEFORE</span>
                <div className="aspect-[3/4] w-full overflow-hidden rounded-xl border border-zinc-200">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={currentImageUrl} alt="Before" className="h-full w-full object-cover" />
                </div>
              </div>
              <div className="flex flex-col items-center gap-1">
                <span className="text-[12px] font-semibold text-zinc-500">
                  AFTER{editType && ` (${editType})`}
                </span>
                <div className="aspect-[3/4] w-full overflow-hidden rounded-xl border border-zinc-200 bg-zinc-50">
                  {isLoading ? (
                    <div className="flex h-full items-center justify-center">
                      <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-200 border-t-indigo-500" />
                    </div>
                  ) : editedImageUrl ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img src={editedImageUrl} alt="After" className="h-full w-full object-cover" />
                  ) : null}
                </div>
              </div>
            </div>
          )}

          {/* Cost display */}
          {editedImageUrl && costUsd > 0 && (
            <p className="text-[12px] text-zinc-400 text-right">
              비용: ${costUsd.toFixed(3)}
            </p>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            {editedImageUrl ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setEditedImageUrl(null);
                    setEditedAssetId(null);
                  }}
                  className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
                >
                  다시 시도
                </button>
                <button
                  type="button"
                  onClick={handleAccept}
                  className="flex-1 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:from-indigo-600 hover:to-purple-600"
                >
                  적용
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 rounded-full border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:bg-zinc-50"
                >
                  취소
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!instruction.trim() || isLoading}
                  className="flex-1 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:from-indigo-600 hover:to-purple-600 disabled:cursor-not-allowed disabled:from-indigo-300 disabled:to-purple-300"
                >
                  {isLoading ? "편집 중..." : "편집 시작 (~$0.04)"}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
