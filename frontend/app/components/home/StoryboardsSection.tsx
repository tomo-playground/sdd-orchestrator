"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useStoryboards } from "../../hooks/useStoryboards";
import StoryboardCard, { DraftCard } from "../../(app)/storyboards/StoryboardCard";
import Button from "../ui/Button";
import LoadingSpinner from "../ui/LoadingSpinner";
import { LABEL_CLASSES } from "../ui/variants";

type Props = {
  projectId: number | null;
  groupId: number | null;
};

export default function StoryboardsSection({ projectId, groupId }: Props) {
  const router = useRouter();
  const { storyboards, isLoading } = useStoryboards(projectId, groupId);
  const recent = storyboards.slice(0, 3);

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className={LABEL_CLASSES}>
          Storyboards{!isLoading && storyboards.length > 0 ? ` (${storyboards.length})` : ""}
        </h2>
        <Link href="/storyboards">
          <Button size="sm" variant="ghost" className="shrink-0 rounded-full">
            View All &rarr;
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="md" />
        </div>
      ) : storyboards.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <svg
            className="h-12 w-12 text-zinc-200"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-1.5A1.125 1.125 0 0118 18.375M20.625 4.5H3.375m17.25 0c.621 0 1.125.504 1.125 1.125M20.625 4.5h-1.5C18.504 4.5 18 5.004 18 5.625m3.75 0v1.5c0 .621-.504 1.125-1.125 1.125M3.375 4.5c-.621 0-1.125.504-1.125 1.125M3.375 4.5h1.5C5.496 4.5 6 5.004 6 5.625m-3.75 0v1.5c0 .621.504 1.125 1.125 1.125m0 0h1.5m-1.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m1.5-3.75C5.496 8.25 6 7.746 6 7.125v-1.5M4.875 8.25C5.496 8.25 6 8.754 6 9.375v1.5m0-5.25v5.25m0-5.25C6 5.004 6.504 4.5 7.125 4.5h9.75c.621 0 1.125.504 1.125 1.125"
            />
          </svg>
          <div>
            <p className="text-sm font-medium text-zinc-500">No storyboards in this group</p>
            <p className="mt-1 text-xs text-zinc-400">
              Create a storyboard to start producing shorts
            </p>
          </div>
          <Button size="md" onClick={() => router.push("/studio?new=true")}>
            + New Storyboard
          </Button>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <DraftCard onClick={() => router.push("/studio")} />
          {recent.map((sb) => (
            <StoryboardCard
              key={sb.id}
              sb={sb}
              onClick={() => router.push(`/studio?id=${sb.id}`)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
