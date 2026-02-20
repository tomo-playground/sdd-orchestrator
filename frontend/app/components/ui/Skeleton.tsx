import { cx } from "./variants";

type SkeletonProps = {
  className?: string;
};

export default function Skeleton({ className }: SkeletonProps) {
  return <div aria-hidden="true" className={cx("animate-pulse rounded bg-zinc-200", className)} />;
}

type SkeletonGridProps = {
  count?: number;
  className?: string;
  children: (index: number) => React.ReactNode;
};

export function SkeletonGrid({ count = 6, className, children }: SkeletonGridProps) {
  const gridClasses = className ?? "gap-3 sm:grid-cols-2 lg:grid-cols-3";
  return (
    <div role="status" aria-label="Loading" className={cx("grid", gridClasses)}>
      {Array.from({ length: count }, (_, i) => children(i))}
    </div>
  );
}
