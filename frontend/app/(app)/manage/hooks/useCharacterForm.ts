import { useState, useMemo, useEffect } from "react";
import axios from "axios";
import { API_BASE } from "../../../constants";
import { getErrorMsg } from "../../../utils/error";
import { useCharacterPreview } from "./useCharacterPreview";
import { parseRawTagText } from "./parseRawTagText";
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
  "background", "kitchen", "room", "outdoors", "indoors", "scenery",
  "nature", "mountain", "street", "office", "bedroom", "bathroom", "garden",
];

export type UseCharacterFormOptions = {
  character?: Character;
  allTags: Tag[];
  allLoras: LoRA[];
  onSave: (data: Partial<Character>, id?: number) => Promise<void>;
  onClose?: () => void;
  showToast: (message: string, type: "success" | "error" | "warning") => void;
  confirmDialog: (opts: {
    title?: string;
    message?: string;
    confirmLabel?: string;
  }) => Promise<boolean>;
};

export function useCharacterForm(options: UseCharacterFormOptions) {
  const { character, allTags, allLoras, onSave, onClose, showToast, confirmDialog } = options;
  const isCreateMode = !character;

  // --- Basic state ---
  const [name, setName] = useState(character?.name || "");
  const [description, setDescription] = useState(character?.description || "");
  const [gender, setGender] = useState<ActorGender>(character?.gender || "female");
  const [customBasePrompt, setCustomBasePrompt] = useState(character?.custom_base_prompt || "");
  const [customNegativePrompt, setCustomNegativePrompt] = useState(
    character?.custom_negative_prompt || ""
  );

  // --- Preview (delegated to useCharacterPreview) ---
  const preview = useCharacterPreview({
    characterId: character?.id,
    isCreateMode,
    initialPreviewUrl: character?.preview_image_url || "",
    showToast,
    confirmDialog,
  });

  // --- Prompt settings ---
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
      .then((res) => setVoicePresets(res.data))
      .catch((err) => console.warn("[useCharacterForm] Failed to load voice presets:", err));
  }, []);

  // --- LoRAs ---
  const [selectedLoras, setSelectedLoras] = useState<CharacterLoRA[]>(character?.loras || []);
  const [localLoras, setLocalLoras] = useState<LoRA[]>(allLoras);

  // --- Async flags ---
  const [isSaving, setIsSaving] = useState(false);

  // --- Sync prompt_mode from character ---
  useEffect(() => {
    if (character?.prompt_mode) setPromptMode(character.prompt_mode);
  }, [character]);

  // --- Derived: warnings ---
  const sceneIdentityWarning = useMemo(() => {
    const tokens = customBasePrompt.toLowerCase().split(/[,\s]+/).map((t) => t.trim());
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
      const { ids, notFound } = parseRawTagText(rawEditText, allTags);
      if (notFound.length > 0) {
        showToast(
          `Tags not found: ${notFound.join(", ")}. Use the Tag Manager to add new tags.`,
          "warning"
        );
      }
      if (type === "identity") setIdentityTagIds(ids);
      else setClothingTagIds(ids);
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
    } catch (error) {
      showToast(`LoRA update failed: ${getErrorMsg(error, "Unknown error")}`, "error");
    }
  };

  // --- Submit ---
  const handleSubmit = async () => {
    let finalIdentityTagIds = identityTagIds;
    let finalClothingTagIds = clothingTagIds;

    if (rawEditMode) {
      const { ids } = parseRawTagText(rawEditText, allTags);
      if (rawEditMode === "identity") {
        finalIdentityTagIds = ids;
        setIdentityTagIds(ids);
      } else {
        finalClothingTagIds = ids;
        setClothingTagIds(ids);
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

    setIsSaving(true);
    try {
      await onSave(payload, character?.id);
      onClose?.();
    } catch (error) {
      console.error("Failed to save character", error);
      showToast(`Save failed: ${getErrorMsg(error, "Unknown error")}`, "error");
    } finally {
      setIsSaving(false);
    }
  };

  return {
    isCreateMode,
    name, setName,
    description, setDescription,
    gender, setGender,
    customBasePrompt, setCustomBasePrompt,
    customNegativePrompt, setCustomNegativePrompt,
    // Preview (spread from useCharacterPreview)
    ...preview,
    previewLocked, setPreviewLocked,
    promptMode, setPromptMode,
    ipAdapterWeight, setIpAdapterWeight,
    ipAdapterModel, setIpAdapterModel,
    // Reference
    referenceBasePrompt, setReferenceBasePrompt,
    referenceNegativePrompt, setReferenceNegativePrompt,
    // Tags
    identityTagIds, clothingTagIds,
    tagSearch, setTagSearch,
    activeTagInput, setActiveTagInput,
    rawEditMode, rawEditText, setRawEditText,
    // Voice Preset
    defaultVoicePresetId, setDefaultVoicePresetId,
    voicePresets,
    // LoRAs
    selectedLoras, localLoras,
    // Async flags
    isSaving,
    // Derived
    sceneIdentityWarning, referenceProfileWarning,
    identityTags, clothingTags, filteredTags,
    // Handlers
    handleAddTag, handleRemoveTag, toggleRawEdit,
    handleAddLora, handleUpdateLora, handleRemoveLora, handleLoraTypeChange,
    handleSubmit,
  };
}
