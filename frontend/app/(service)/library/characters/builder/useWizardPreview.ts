import { useCallback } from "react";
import axios from "axios";
import { ADMIN_API_BASE } from "../../../../constants";
import { useUIStore } from "../../../../store/useUIStore";
import { getErrorMsg } from "../../../../utils/error";
import type { Tag } from "../../../../types";
import type { WizardState, WizardAction } from "./wizardReducer";
import { GENDER_IDENTITY_TAGS } from "./wizardTemplates";
import { SD_REFERENCE_NUM_CANDIDATES } from "./previewConstants";

type UseWizardPreviewParams = {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
  allTagsFlat: Tag[];
};

/** Encapsulates preview generation + assign-preview logic for the wizard. */
export function useWizardPreview({ state, dispatch, allTagsFlat }: UseWizardPreviewParams) {
  const showToast = useUIStore((s) => s.showToast);

  const handleGeneratePreview = useCallback(async () => {
    if (state.selectedTags.length === 0) {
      showToast("Select at least one tag first", "warning");
      return;
    }

    dispatch({ type: "SET_GENERATING", isGenerating: true });

    try {
      const genderTagNames = GENDER_IDENTITY_TAGS[state.gender];
      const genderTagIds = genderTagNames
        .map((name) => allTagsFlat.find((t) => t.name === name)?.id)
        .filter((id): id is number => id != null);
      const selectedTagIds = state.selectedTags.map((t) => t.tagId);
      const tagIds = [...new Set([...genderTagIds, ...selectedTagIds])];

      const payload = {
        gender: state.gender,
        tag_ids: tagIds,
        loras:
          state.selectedLoras.length > 0
            ? state.selectedLoras.map((lr) => ({ lora_id: lr.loraId, weight: lr.weight }))
            : null,
        style_profile_id: state.style_profile_id,
        num_candidates: SD_REFERENCE_NUM_CANDIDATES,
      };

      const res = await axios.post(`${ADMIN_API_BASE}/characters/preview`, payload);
      const candidates = res.data.candidates ?? [{ image: res.data.image, seed: res.data.seed }];
      dispatch({ type: "SET_PREVIEW", image: res.data.image, seed: res.data.seed, candidates });
      const count = candidates.length;
      showToast(`${count} preview${count > 1 ? "s" : ""} generated!`, "success");
    } catch (err) {
      showToast(getErrorMsg(err, "Failed to generate preview"), "error");
      dispatch({ type: "SET_GENERATING", isGenerating: false });
    }
  }, [
    state.selectedTags,
    state.selectedLoras,
    state.gender,
    state.style_profile_id,
    allTagsFlat,
    showToast,
    dispatch,
  ]);

  const assignPreview = useCallback(
    async (characterId: number) => {
      if (!state.previewImage) return;
      try {
        await axios.post(`${ADMIN_API_BASE}/characters/${characterId}/assign-preview`, {
          image_base64: state.previewImage,
        });
      } catch {
        showToast("Preview could not be assigned", "warning");
      }
    },
    [state.previewImage, showToast]
  );

  return { handleGeneratePreview, assignPreview };
}
