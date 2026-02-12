import Skeleton from "../../components/ui/Skeleton";

export default function BackgroundCardSkeleton() {
  return (
    <div className="flex flex-col rounded-2xl border border-zinc-200/60 bg-white shadow-sm">
      {/* Thumbnail */}
      <Skeleton className="aspect-video w-full rounded-t-2xl rounded-b-none" />

      <div className="flex flex-1 flex-col gap-1.5 p-4">
        {/* Name + category badge */}
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-28 rounded" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        {/* Tags */}
        <div className="flex gap-1">
          <Skeleton className="h-5 w-16 rounded" />
          <Skeleton className="h-5 w-12 rounded" />
          <Skeleton className="h-5 w-14 rounded" />
        </div>
        {/* Footer */}
        <div className="mt-auto flex items-center justify-between pt-1">
          <Skeleton className="h-3 w-16 rounded" />
          <div className="flex gap-1.5">
            <Skeleton className="h-6 w-6 rounded-full" />
            <Skeleton className="h-6 w-6 rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}
