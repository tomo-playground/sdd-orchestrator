import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Badge from "../ui/Badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies default variant classes", () => {
    render(<Badge>Tag</Badge>);
    const el = screen.getByText("Tag");
    expect(el).toHaveClass("bg-zinc-100", "text-zinc-600");
  });

  it("applies success variant classes", () => {
    render(<Badge variant="success">Done</Badge>);
    const el = screen.getByText("Done");
    expect(el).toHaveClass("bg-emerald-100", "text-emerald-700");
  });

  it("applies warning variant classes", () => {
    render(<Badge variant="warning">Warn</Badge>);
    expect(screen.getByText("Warn")).toHaveClass("bg-amber-100");
  });

  it("applies error variant classes", () => {
    render(<Badge variant="error">Err</Badge>);
    expect(screen.getByText("Err")).toHaveClass("bg-rose-100");
  });

  it("applies info variant classes", () => {
    render(<Badge variant="info">Info</Badge>);
    expect(screen.getByText("Info")).toHaveClass("bg-blue-100");
  });

  it("applies sm size by default", () => {
    render(<Badge>Small</Badge>);
    expect(screen.getByText("Small")).toHaveClass("text-[10px]");
  });

  it("applies md size classes", () => {
    render(<Badge size="md">Medium</Badge>);
    expect(screen.getByText("Medium")).toHaveClass("text-xs", "px-2");
  });

  it("merges custom className", () => {
    render(<Badge className="ml-2">Custom</Badge>);
    expect(screen.getByText("Custom")).toHaveClass("ml-2");
  });
});
