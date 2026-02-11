"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { Clapperboard } from "lucide-react";
import { useStoryboards } from "../../hooks/useStoryboards";
import StoryboardCard, { DraftCard } from "../../(app)/storyboards/StoryboardCard";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
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
        <EmptyState
          icon={Clapperboard}
          title="No storyboards in this group"
          description="Create a storyboard to start producing shorts"
          action={
            <Button size="md" onClick={() => router.push("/studio?new=true")}>
              + New Storyboard
            </Button>
          }
        />
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
