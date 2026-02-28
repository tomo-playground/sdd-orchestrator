import Skeleton from "../../components/ui/Skeleton";

export default function VoiceCardSkeleton() {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm">
      {/* Header: name + badge */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-28 rounded" />
        <Skeleton className="h-5 w-14 rounded-full" />
      </div>
      {/* Description */}
      <Skeleton className="h-3 w-full rounded" />
      <Skeleton className="h-3 w-3/4 rounded" />
      {/* Prompt */}
      <Skeleton className="h-3 w-2/3 rounded" />
      {/* Footer */}
      <div className="mt-auto flex items-center justify-between pt-1">
        <Skeleton className="h-3 w-10 rounded" />
        <div className="flex gap-1.5">
          <Skeleton className="h-6 w-6 rounded-full" />
          <Skeleton className="h-6 w-6 rounded-full" />
        </div>
      </div>
    </div>
  );
}
