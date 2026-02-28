"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const TAB_MAP: Record<string, string> = {
  characters: "/admin/characters",
  voices: "/admin/voices",
  music: "/admin/music",
  tags: "/admin/tags",
  style: "/admin/styles",
  prompts: "/admin/prompts",
};

function LibraryRedirectInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const tab = searchParams.get("tab");
    const dest = (tab && TAB_MAP[tab]) || "/admin/characters";
    router.replace(dest);
  }, [router, searchParams]);

  return null;
}

export default function LibraryRedirect() {
  return (
    <Suspense>
      <LibraryRedirectInner />
    </Suspense>
  );
}
