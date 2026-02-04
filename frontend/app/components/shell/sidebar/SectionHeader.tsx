import type { ReactNode } from "react";
import { cx, LABEL_CLASSES } from "../../ui/variants";

type Props = {
  label: string;
  collapsed: boolean;
  badge?: ReactNode;
};

export default function SectionHeader({ label, collapsed, badge }: Props) {
  if (collapsed) return null;
  return (
    <h3 className={cx(LABEL_CLASSES, "flex items-center gap-2 px-3 pt-4 pb-1")}>
      {label}
      {badge}
    </h3>
  );
}
