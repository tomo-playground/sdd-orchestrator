"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import axios from "axios";
import CharacterWizard from "../builder/CharacterWizard";
import { CharacterDetailForm } from "../[id]/page";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import { CONTAINER_CLASSES } from "../../../components/ui/variants";
import { API_BASE } from "../../../constants";
import { useUIStore } from "../../../store/useUIStore";
import type { Tag, LoRA, Character } from "../../../types";

function NewCharacterContent() {
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode");

  if (mode === "full") {
    return <FullEditorMode />;
  }

  return <CharacterWizard />;
}

/** Full Editor: reuses CharacterDetailForm for create mode */
function FullEditorMode() {
  const router = useRouter();
  const showToast = useUIStore((s) => s.showToast);

  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [allLoras, setAllLoras] = useState<LoRA[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    Promise.all([axios.get(`${API_BASE}/tags`), axios.get(`${API_BASE}/loras`)])
      .then(([tagsRes, lorasRes]) => {
        setAllTags(tagsRes.data);
        setAllLoras(lorasRes.data);
      })
      .catch(() => showToast("Failed to load data", "error"))
      .finally(() => setIsLoaded(true));
  }, [showToast]);

  const handleSave = useCallback(
    async (data: Partial<Character>) => {
      const res = await axios.post(`${API_BASE}/characters`, data);
      showToast("Character created", "success");
      router.push(`/characters/${res.data.id}`);
    },
    [showToast, router]
  );

  if (!isLoaded) {
    return (
      <div className={`${CONTAINER_CLASSES} flex items-center justify-center py-32`}>
        <LoadingSpinner size="md" />
      </div>
    );
  }

  return (
    <CharacterDetailForm
      character={undefined}
      allTags={allTags}
      allLoras={allLoras}
      isNew={true}
      onSave={handleSave}
    />
  );
}

export default function NewCharacterPage() {
  return (
    <Suspense
      fallback={
        <div className={`${CONTAINER_CLASSES} flex items-center justify-center py-32`}>
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <NewCharacterContent />
    </Suspense>
  );
}
