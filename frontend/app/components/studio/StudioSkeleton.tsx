import Skeleton from "../ui/Skeleton";

/** Loading skeleton for Studio initial DB load */
export default function StudioSkeleton() {
  return (
    <div className="flex h-[calc(100vh-56px)] flex-col">
      <div className="flex h-12 items-center justify-between border-b border-zinc-100 px-8">
        <Skeleton className="h-4 w-40" />
        <div className="flex items-center gap-3">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-7 w-24 rounded-lg" />
      </div>
      <div className="flex flex-1 gap-4 p-8">
        <div className="flex w-72 flex-col gap-3">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-xl" />
          ))}
        </div>
        <div className="flex flex-1 flex-col gap-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-64 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      </div>
    </div>
  );
}
