import { cx } from "./variants";

type SkeletonProps = {
  className?: string;
};

export default function Skeleton({ className }: SkeletonProps) {
  return <div aria-hidden="true" className={cx("animate-pulse rounded bg-zinc-200", className)} />;
}

type SkeletonGridProps = {
  count?: number;
  children: (index: number) => React.ReactNode;
};

export function SkeletonGrid({ count = 6, children }: SkeletonGridProps) {
  return (
    <div role="status" aria-label="Loading" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }, (_, i) => children(i))}
    </div>
  );
}
