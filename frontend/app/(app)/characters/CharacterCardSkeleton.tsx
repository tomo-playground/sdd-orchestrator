import Skeleton from "../../components/ui/Skeleton";

export default function CharacterCardSkeleton() {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-zinc-200/60 bg-white p-4 shadow-sm">
      {/* Image placeholder */}
      <Skeleton className="h-20 w-20 shrink-0 rounded-xl" />

      <div className="min-w-0 flex-1">
        {/* Name */}
        <Skeleton className="h-4 w-24 rounded" />
        {/* Gender */}
        <Skeleton className="mt-1.5 h-3 w-14 rounded" />
        {/* Badges */}
        <div className="mt-2 flex gap-1">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-12 rounded-full" />
        </div>
      </div>
    </div>
  );
}
