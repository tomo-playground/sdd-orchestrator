import Skeleton from "../../../components/ui/Skeleton";

export default function CharacterCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl bg-zinc-900 shadow-lg">
      <div className="relative aspect-[3/4] w-full">
        <Skeleton className="h-full w-full rounded-none bg-zinc-800" />
        {/* Bottom info skeleton */}
        <div className="absolute inset-x-0 bottom-0 p-3">
          <Skeleton className="h-4 w-24 rounded bg-zinc-700" />
          <div className="mt-2 flex gap-2">
            <Skeleton className="h-5 w-14 rounded-full bg-zinc-700" />
            <Skeleton className="h-5 w-10 rounded-full bg-zinc-700" />
          </div>
        </div>
      </div>
    </div>
  );
}
