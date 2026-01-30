import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Studio - Shorts Producer",
  description: "4-Tab workspace for creating shorts videos",
};

export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
