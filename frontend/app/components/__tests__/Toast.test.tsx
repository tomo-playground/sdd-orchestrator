import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Toast from "../ui/Toast";

describe("Toast", () => {
  it("has role=status and aria-live=polite for success type", () => {
    render(<Toast message="Saved" type="success" />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("aria-live", "polite");
    expect(el).toHaveAttribute("aria-atomic", "true");
  });

  it("has role=alert and aria-live=assertive for error type", () => {
    render(<Toast message="Failed" type="error" />);
    const el = screen.getByRole("alert");
    expect(el).toHaveAttribute("aria-live", "assertive");
    expect(el).toHaveAttribute("aria-atomic", "true");
  });

  it("close button has aria-label", () => {
    const onClose = vi.fn();
    render(<Toast message="Info" type="info" onClose={onClose} />);
    const btn = screen.getByLabelText("Close notification");
    expect(btn).toBeInTheDocument();
  });
});
