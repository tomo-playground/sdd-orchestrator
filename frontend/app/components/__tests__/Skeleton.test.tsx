import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Skeleton, { SkeletonGrid } from "../ui/Skeleton";

describe("Skeleton", () => {
  it("renders with animate-pulse", () => {
    const { container } = render(<Skeleton />);
    const el = container.firstElementChild!;
    expect(el).toHaveClass("animate-pulse");
  });

  it("is aria-hidden", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
  });

  it("merges custom className", () => {
    const { container } = render(<Skeleton className="h-10 w-10" />);
    const el = container.firstElementChild!;
    expect(el).toHaveClass("animate-pulse");
    expect(el).toHaveClass("h-10");
    expect(el).toHaveClass("w-10");
  });
});

describe("SkeletonGrid", () => {
  it("renders 6 items by default", () => {
    render(<SkeletonGrid>{(i) => <div key={i} data-testid="item" />}</SkeletonGrid>);
    expect(screen.getAllByTestId("item")).toHaveLength(6);
  });

  it("renders custom count", () => {
    render(<SkeletonGrid count={3}>{(i) => <div key={i} data-testid="item" />}</SkeletonGrid>);
    expect(screen.getAllByTestId("item")).toHaveLength(3);
  });

  it("has role=status", () => {
    render(<SkeletonGrid>{(i) => <div key={i} />}</SkeletonGrid>);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("uses 3-column grid layout", () => {
    render(<SkeletonGrid>{(i) => <div key={i} />}</SkeletonGrid>);
    const grid = screen.getByRole("status");
    expect(grid).toHaveClass("grid");
    expect(grid).toHaveClass("lg:grid-cols-3");
  });
});
