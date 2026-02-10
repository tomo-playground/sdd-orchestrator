import { useState, useMemo, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import {
  Character,
  CharacterLoRA,
  Tag,
  LoRA,
  ActorGender,
  PromptMode,
  VoicePreset,
} from "../../../types";

const RESTRICTED_KEYWORDS = [
  "background",
  "kitchen",
  "room",
  "outdoors",
  "indoors",
  "scenery",
  "nature",
  "mountain",
  "street",
  "office",
  "bedroom",
  "bathroom",
  "garden",
];

export function useCharacterForm(
  character: Character | undefined,
  allTags: Tag[],
  allLoras: LoRA[],
  onSave: (data: Partial<Character>, id?: number) => Promise<void>,
  onClose: () => void,
  showToast: (message: string, type: "success" | "error" | "warning") => void,
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
  }) => Promise<boolean>
) {
  const isCreateMode = !character;

  // --- Basic state ---
  const [name, setName] = useState(character?.name || "");
  const [description, setDescription] = useState(character?.description || "");
  const [gender, setGender] = useState<ActorGender>(character?.gender || "female");
  const [customBasePrompt, setCustomBasePrompt] = useState(character?.custom_base_prompt || "");
  const [customNegativePrompt, setCustomNegativePrompt] = useState(
    character?.custom_negative_prompt || ""
  );

  // --- Preview ---
  const [previewImageUrl, setPreviewImageUrl] = useState(character?.preview_image_url || "");
  const [previewLocked, setPreviewLocked] = useState(character?.preview_locked ?? false);
  const [promptMode, setPromptMode] = useState<PromptMode>(character?.prompt_mode || "auto");
  const [ipAdapterWeight, setIpAdapterWeight] = useState<number>(
    character?.ip_adapter_weight || 0.75
  );
  const [ipAdapterModel, setIpAdapterModel] = useState<string>(
    character?.ip_adapter_model || "clip_face"
  );

  // --- Reference prompts ---
  const [referenceBasePrompt, setReferenceBasePrompt] = useState(
    isCreateMode ? customBasePrompt : character?.reference_base_prompt || ""
  );
  const [referenceNegativePrompt, setReferenceNegativePrompt] = useState(
    isCreateMode ? customNegativePrompt : character?.reference_negative_prompt || ""
  );

  // --- Tags ---
  const [identityTagIds, setIdentityTagIds] = useState<number[]>(
    character?.tags?.filter((t) => t.is_permanent).map((t) => t.tag_id) || []
  );
  const [clothingTagIds, setClothingTagIds] = useState<number[]>(
    character?.tags?.filter((t) => !t.is_permanent).map((t) => t.tag_id) || []
  );
  const [tagSearch, setTagSearch] = useState("");
  const [activeTagInput, setActiveTagInput] = useState<"identity" | "clothing" | null>(null);

  // --- Raw edit ---
  const [rawEditMode, setRawEditMode] = useState<"identity" | "clothing" | null>(null);
  const [rawEditText, setRawEditText] = useState("");

  // --- Voice Preset ---
  const [defaultVoicePresetId, setDefaultVoicePresetId] = useState<number | null>(
    character?.voice_preset_id ?? null
  );
  const [voicePresets, setVoicePresets] = useState<VoicePreset[]>([]);
  useEffect(() => {
    axios
      .get(`${API_BASE}/voice-presets`)
      .then((res) => {
        setVoicePresets(res.data);
      })
      .catch(() => {});
  }, []);

  // --- LoRAs ---
  const [selectedLoras, setSelectedLoras] = useState<CharacterLoRA[]>(character?.loras || []);
  const [localLoras, setLocalLoras] = useState<LoRA[]>(allLoras);

  // --- Async flags ---
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // --- Gemini edit ---
  const [geminiEditOpen, setGeminiEditOpen] = useState(false);
  const [geminiTargetChange, setGeminiTargetChange] = useState("");

  // --- Preview modal ---
  const [previewImageOpen, setPreviewImageOpen] = useState(false);

  // --- Sync prompt_mode from character ---
  useEffect(() => {
    if (character?.prompt_mode) {
      setPromptMode(character.prompt_mode);
    }
  }, [character]);

  // --- Derived: warnings ---
  const sceneIdentityWarning = useMemo(() => {
    const tokens = customBasePrompt
      .toLowerCase()
      .split(/[,\s]+/)
      .map((t) => t.trim());
    const found = tokens.filter((t) => RESTRICTED_KEYWORDS.includes(t));
    return found.length > 0
      ? `Warning: Background tags detected (${found.join(", ")}). Please remove them for better consistency.`
      : null;
  }, [customBasePrompt]);

  const referenceProfileWarning = useMemo(() => {
    const lower = referenceBasePrompt.toLowerCase();
    if (
      !lower.includes("white background") &&
      !lower.includes("simple background") &&
      !lower.includes("plain background")
    ) {
      return "Tip: Adding 'white background' is recommended for cleaner character reference.";
    }
    return null;
  }, [referenceBasePrompt]);

  // --- Derived: tags ---
  const identityTags = useMemo(
    () => identityTagIds.map((id) => allTags.find((t) => t.id === id)).filter(Boolean) as Tag[],
    [identityTagIds, allTags]
  );

  const clothingTags = useMemo(
    () => clothingTagIds.map((id) => allTags.find((t) => t.id === id)).filter(Boolean) as Tag[],
    [clothingTagIds, allTags]
  );

  const filteredTags = useMemo(() => {
    if (!tagSearch.trim()) return [];
    const search = tagSearch.toLowerCase();
    return allTags.filter((t) => t.name.toLowerCase().includes(search)).slice(0, 10);
  }, [allTags, tagSearch]);

  // --- Handlers: preview image ---
  const handleGenerateReference = async () => {
    if (isCreateMode || !character?.id) return;
    setIsGenerating(true);
    try {
      const res = await axios.post(`${API_BASE}/characters/${character.id}/regenerate-reference`);
      if (res.data.url) setPreviewImageUrl(res.data.url);
    } catch (error) {
      console.error("Failed to generate reference", error);
      showToast("Failed to generate reference image.", "error");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleEnhancePreview = async () => {
    if (isCreateMode || !character?.id || !previewImageUrl) return;
    const ok = await confirmDialog({
      title: "Enhance Preview",
      message: "Enhance preview image with Gemini? (~$0.04 cost)",
      confirmLabel: "Enhance",
    });
    if (!ok) return;
    setIsEnhancing(true);
    try {
      const res = await axios.post(`${API_BASE}/characters/${character.id}/enhance-preview`);
      if (res.data.url) setPreviewImageUrl(res.data.url);
    } catch (error) {
      console.error("Failed to enhance preview", error);
      showToast("Failed to enhance preview image.", "error");
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleEditPreview = async (instruction: string) => {
    if (isCreateMode || !character?.id || !previewImageUrl || !instruction.trim()) return;
    setIsEditing(true);
    setGeminiEditOpen(false);
    try {
      const res = await axios.post(`${API_BASE}/characters/${character.id}/edit-preview`, {
        instruction: instruction.trim(),
      });
      if (res.data.url) {
        setPreviewImageUrl(res.data.url);
        setGeminiTargetChange("");
      }
    } catch (error) {
      console.error("Failed to edit preview", error);
      showToast("Failed to edit preview image.", "error");
    } finally {
      setIsEditing(false);
    }
  };

  // --- Handlers: tags ---
  const handleAddTag = (tag: Tag) => {
    if (activeTagInput === "identity") {
      if (!identityTagIds.includes(tag.id)) setIdentityTagIds([...identityTagIds, tag.id]);
    } else if (activeTagInput === "clothing") {
      if (!clothingTagIds.includes(tag.id)) setClothingTagIds([...clothingTagIds, tag.id]);
    }
    setTagSearch("");
  };

  const handleRemoveTag = (id: number, type: "identity" | "clothing") => {
    if (type === "identity") {
      setIdentityTagIds(identityTagIds.filter((t) => t !== id));
    } else {
      setClothingTagIds(clothingTagIds.filter((t) => t !== id));
    }
  };

  const toggleRawEdit = (type: "identity" | "clothing") => {
    if (rawEditMode === type) {
      const parsed = rawEditText
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);
      const newIds: number[] = [];
      const notFound: string[] = [];

      parsed.forEach((tagName) => {
        let tag = allTags.find((t) => t.name === tagName);
        if (!tag) tag = allTags.find((t) => t.name.toLowerCase() === tagName.toLowerCase());
        if (tag) {
          if (!newIds.includes(tag.id)) newIds.push(tag.id);
        } else {
          notFound.push(tagName);
        }
      });

      if (notFound.length > 0) {
        showToast(
          `Tags not found: ${notFound.join(", ")}. Use the Tag Manager to add new tags.`,
          "warning"
        );
      }

      if (type === "identity") setIdentityTagIds(newIds);
      else setClothingTagIds(newIds);
      setRawEditMode(null);
    } else {
      const tags = type === "identity" ? identityTags : clothingTags;
      setRawEditText(tags.map((t) => t.name).join(", "));
      setRawEditMode(type);
    }
  };

  // --- Handlers: LoRAs ---
  const handleAddLora = () => {
    if (allLoras.length > 0) {
      const first = allLoras[0];
      if (!selectedLoras.find((l) => l.lora_id === first.id)) {
        setSelectedLoras([...selectedLoras, { lora_id: first.id, weight: 1.0 }]);
      }
    }
  };

  const handleUpdateLora = (index: number, field: "lora_id" | "weight", value: number) => {
    const newLoras = [...selectedLoras];
    newLoras[index] = { ...newLoras[index], [field]: value };
    setSelectedLoras(newLoras);
  };

  const handleRemoveLora = (index: number) => {
    setSelectedLoras(selectedLoras.filter((_, i) => i !== index));
  };

  const handleLoraTypeChange = async (loraId: number, newType: string) => {
    try {
      await axios.put(`${API_BASE}/loras/${loraId}`, { lora_type: newType });
      setLocalLoras((prev) =>
        prev.map((l) => (l.id === loraId ? { ...l, lora_type: newType } : l))
      );
    } catch {
      showToast("Failed to update LoRA type.", "error");
    }
  };

  // --- Submit ---
  const handleSubmit = async () => {
    let finalIdentityTagIds = identityTagIds;
    let finalClothingTagIds = clothingTagIds;

    if (rawEditMode) {
      const parsed = rawEditText
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);
      const newIds: number[] = [];
      parsed.forEach((tagName) => {
        const tag = allTags.find((t) => t.name.toLowerCase() === tagName.toLowerCase());
        if (tag && !newIds.includes(tag.id)) newIds.push(tag.id);
      });
      if (rawEditMode === "identity") {
        finalIdentityTagIds = newIds;
        setIdentityTagIds(newIds);
      } else {
        finalClothingTagIds = newIds;
        setClothingTagIds(newIds);
      }
      setRawEditMode(null);
    }

    const payload = {
      name,
      description,
      gender,
      tags: [
        ...finalIdentityTagIds.map((id) => ({ tag_id: id, weight: 1.0, is_permanent: true })),
        ...finalClothingTagIds.map((id) => ({ tag_id: id, weight: 1.0, is_permanent: false })),
      ],
      loras: selectedLoras,
      prompt_mode: promptMode,
      custom_base_prompt: customBasePrompt,
      custom_negative_prompt: customNegativePrompt,
      reference_base_prompt: referenceBasePrompt,
      reference_negative_prompt: referenceNegativePrompt,
      ip_adapter_weight: ipAdapterWeight,
      ip_adapter_model: ipAdapterModel,
      preview_locked: previewLocked,
      voice_preset_id: defaultVoicePresetId,
    };

    console.log("[CharacterEditModal] Saving character:", payload);
    setIsSaving(true);
    try {
      await onSave(payload, character?.id);
      onClose();
    } catch (error) {
      console.error("Failed to save character", error);
      showToast("Failed to save changes.", "error");
    } finally {
      setIsSaving(false);
    }
  };

  return {
    // Basic
    isCreateMode,
    name,
    setName,
    description,
    setDescription,
    gender,
    setGender,
    customBasePrompt,
    setCustomBasePrompt,
    customNegativePrompt,
    setCustomNegativePrompt,
    // Preview
    previewImageUrl,
    setPreviewImageUrl,
    previewLocked,
    setPreviewLocked,
    promptMode,
    setPromptMode,
    ipAdapterWeight,
    setIpAdapterWeight,
    ipAdapterModel,
    setIpAdapterModel,
    // Reference
    referenceBasePrompt,
    setReferenceBasePrompt,
    referenceNegativePrompt,
    setReferenceNegativePrompt,
    // Tags
    identityTagIds,
    clothingTagIds,
    tagSearch,
    setTagSearch,
    activeTagInput,
    setActiveTagInput,
    rawEditMode,
    rawEditText,
    setRawEditText,
    // Voice Preset
    defaultVoicePresetId,
    setDefaultVoicePresetId,
    voicePresets,
    // LoRAs
    selectedLoras,
    localLoras,
    // Async flags
    isSaving,
    isGenerating,
    isEnhancing,
    isEditing,
    // Gemini edit
    geminiEditOpen,
    setGeminiEditOpen,
    geminiTargetChange,
    setGeminiTargetChange,
    // Preview modal
    previewImageOpen,
    setPreviewImageOpen,
    // Derived
    sceneIdentityWarning,
    referenceProfileWarning,
    identityTags,
    clothingTags,
    filteredTags,
    // Handlers
    handleGenerateReference,
    handleEnhancePreview,
    handleEditPreview,
    handleAddTag,
    handleRemoveTag,
    toggleRawEdit,
    handleAddLora,
    handleUpdateLora,
    handleRemoveLora,
    handleLoraTypeChange,
    handleSubmit,
  };
}
