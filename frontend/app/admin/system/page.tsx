"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";

function SystemRedirect() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const tab = searchParams.get("tab");

  useEffect(() => {
    if (tab === "presets") router.replace("/settings/presets");
    else if (tab === "youtube") router.replace("/settings/youtube");
    else if (tab === "trash") router.replace("/settings/trash");
    else router.replace("/dev/system");
  }, [tab, router]);

  return null;
}

export default function AdminSystemRedirect() {
  return (
    <Suspense>
      <SystemRedirect />
    </Suspense>
  );
}
