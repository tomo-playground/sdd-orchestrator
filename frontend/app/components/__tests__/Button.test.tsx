import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Button from "../ui/Button";

describe("Button", () => {
  // ── Variant tests ────────────────────────────────────────
  it("renders primary variant by default", () => {
    render(<Button>Click</Button>);
    const btn = screen.getByRole("button", { name: "Click" });
    expect(btn).toHaveClass("bg-zinc-900", "text-white");
  });

  it("renders secondary variant", () => {
    render(<Button variant="secondary">Sec</Button>);
    expect(screen.getByRole("button")).toHaveClass("bg-zinc-100");
  });

  it("renders danger variant", () => {
    render(<Button variant="danger">Del</Button>);
    expect(screen.getByRole("button")).toHaveClass("bg-rose-500");
  });

  it("renders ghost variant", () => {
    render(<Button variant="ghost">Ghost</Button>);
    expect(screen.getByRole("button")).toHaveClass("bg-transparent");
  });

  it("renders gradient variant", () => {
    render(<Button variant="gradient">Grad</Button>);
    expect(screen.getByRole("button")).toHaveClass("bg-gradient-to-r");
  });

  // ── Size tests ───────────────────────────────────────────
  it("applies md size by default", () => {
    render(<Button>Mid</Button>);
    expect(screen.getByRole("button")).toHaveClass("text-sm", "px-4", "py-2");
  });

  it("applies sm size", () => {
    render(<Button size="sm">Sm</Button>);
    expect(screen.getByRole("button")).toHaveClass("text-xs", "px-3");
  });

  it("applies lg size", () => {
    render(<Button size="lg">Lg</Button>);
    expect(screen.getByRole("button")).toHaveClass("px-6", "py-3");
  });

  // ── Icon mode ────────────────────────────────────────────
  it("uses square padding in icon mode", () => {
    render(<Button icon>X</Button>);
    const btn = screen.getByRole("button");
    expect(btn).toHaveClass("p-2");
    expect(btn).not.toHaveClass("px-4");
  });

  // ── Loading state ────────────────────────────────────────
  it("disables button when loading", () => {
    render(<Button loading>Save</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("shows spinner when loading", () => {
    render(<Button loading>Save</Button>);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  // ── Disabled state ───────────────────────────────────────
  it("respects disabled prop", () => {
    render(<Button disabled>No</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  // ── HTML attribute passthrough ───────────────────────────
  it("passes through onClick", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("passes through type attribute", () => {
    render(<Button type="submit">Submit</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "submit");
  });

  it("merges custom className", () => {
    render(<Button className="w-full">Full</Button>);
    expect(screen.getByRole("button")).toHaveClass("w-full");
  });
});
