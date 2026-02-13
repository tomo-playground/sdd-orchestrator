"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import LoadingSpinner from "../../components/ui/LoadingSpinner";

function ScriptsRedirect() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const id = searchParams.get("id");
    const isNew = searchParams.get("new") === "true";

    if (id) {
      router.replace(`/studio?id=${id}`);
    } else if (isNew) {
      router.replace("/studio?new=true");
    } else {
      router.replace("/");
    }
  }, [searchParams, router]);

  return (
    <div className="flex h-64 items-center justify-center">
      <LoadingSpinner size="md" />
    </div>
  );
}

export default function ScriptsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner size="md" />
        </div>
      }
    >
      <ScriptsRedirect />
    </Suspense>
  );
}
