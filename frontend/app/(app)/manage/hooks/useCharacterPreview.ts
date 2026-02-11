import { useState } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import { getErrorMsg } from "../../../utils/error";

type ShowToastFn = (message: string, type: "success" | "error" | "warning") => void;
type ConfirmDialogFn = (opts: {
  title?: string;
  message?: string;
  confirmLabel?: string;
}) => Promise<boolean>;

export type UseCharacterPreviewOptions = {
  characterId?: number;
  isCreateMode: boolean;
  initialPreviewUrl: string;
  showToast: ShowToastFn;
  confirmDialog: ConfirmDialogFn;
};

export function useCharacterPreview(options: UseCharacterPreviewOptions) {
  const { characterId, isCreateMode, showToast, confirmDialog } = options;

  const [previewImageUrl, setPreviewImageUrl] = useState(options.initialPreviewUrl);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");
  const [previewImageOpen, setPreviewImageOpen] = useState(false);

  const handleGenerateReference = async () => {
    if (isCreateMode || !characterId) return;
    setIsGenerating(true);
    try {
      const res = await axios.post(`${API_BASE}/characters/${characterId}/regenerate-reference`);
      if (res.data.url) {
        setPreviewImageUrl(`${res.data.url}?t=${Date.now()}`);
        showToast("Reference image generated", "success");
      }
    } catch (error) {
      console.error("Failed to generate reference", error);
      showToast(`Generate failed: ${getErrorMsg(error, "Unknown error")}`, "error");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleEnhancePreview = async () => {
    if (isCreateMode || !characterId || !previewImageUrl) return;
    const ok = await confirmDialog({
      title: "Enhance Preview",
      message: "Enhance preview image with Gemini? (~$0.04 cost)",
      confirmLabel: "Enhance",
    });
    if (!ok) return;
    setIsEnhancing(true);
    try {
      const res = await axios.post(`${API_BASE}/characters/${characterId}/enhance-preview`);
      if (res.data.url) {
        setPreviewImageUrl(`${res.data.url}?t=${Date.now()}`);
        showToast(`Enhanced — $${res.data.cost_usd?.toFixed(4) ?? "?"}`, "success");
      }
    } catch (error) {
      console.error("Failed to enhance preview", error);
      showToast(`Enhance failed: ${getErrorMsg(error, "Unknown error")}`, "error");
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleEditPreview = async (instruction: string) => {
    if (isCreateMode || !characterId || !previewImageUrl || !instruction.trim()) return;
    setIsEditing(true);
    setGeminiEditOpen(false);
    try {
      const res = await axios.post(`${API_BASE}/characters/${characterId}/edit-preview`, {
        instruction: instruction.trim(),
      });
      if (res.data.url) {
        setPreviewImageUrl(`${res.data.url}?t=${Date.now()}`);
        setGeminiTargetChange("");
        showToast(
          `Gemini edit done${res.data.edit_type ? ` (${res.data.edit_type})` : ""} — $${res.data.cost_usd?.toFixed(4) ?? "?"}`,
          "success"
        );
      }
    } catch (error) {
      console.error("Failed to edit preview", error);
      showToast(`Edit failed: ${getErrorMsg(error, "Unknown error")}`, "error");
    } finally {
      setIsEditing(false);
    }
  };

  return {
    previewImageUrl,
    setPreviewImageUrl,
    isGenerating,
    isEnhancing,
    isEditing,
    geminiEditOpen,
    setGeminiEditOpen,
    geminiTargetChange,
    setGeminiTargetChange,
    previewImageOpen,
    setPreviewImageOpen,
    handleGenerateReference,
    handleEnhancePreview,
    handleEditPreview,
  };
}
