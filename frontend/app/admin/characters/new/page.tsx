"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import CharacterWizard from "../builder/CharacterWizard";
import LoadingSpinner from "../../../components/ui/LoadingSpinner";
import { CONTAINER_CLASSES } from "../../../components/ui/variants";

function NewCharacterContent() {
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode");

  // Note: Full Editor mode temporarily disabled due to missing form components
  // Redirect to wizard regardless of mode parameter
  return <CharacterWizard />;
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
