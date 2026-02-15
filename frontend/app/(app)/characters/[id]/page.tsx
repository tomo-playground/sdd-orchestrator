"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import { CONTAINER_CLASSES } from "../../../components/ui/variants";

/**
 * Character Detail Page
 * 
 * Note: The full character editor has been temporarily disabled due to missing form components.
 * Users are redirected to the Library page where they can view character details.
 * 
 * TODO: Implement character editing using CharacterWizard or rebuild form sections.
 */
export default function CharacterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const rawId = params.id as string;

  useEffect(() => {
    // Redirect to library with character tab selected
    router.replace(`/library?tab=characters&id=${rawId}`);
  }, [rawId, router]);

  return (
    <div className={`${CONTAINER_CLASSES} flex items-center justify-center py-32`}>
      <LoadingSpinner size="md" />
    </div>
  );
}
