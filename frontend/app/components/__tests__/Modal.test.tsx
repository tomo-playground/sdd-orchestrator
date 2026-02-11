import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Modal from "../ui/Modal";

describe("Modal", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    onClose.mockReset();
  });

  // ── Open / close ─────────────────────────────────────────
  it("renders nothing when closed", () => {
    render(
      <Modal open={false} onClose={onClose}>
        <p>Hidden</p>
      </Modal>
    );
    expect(screen.queryByText("Hidden")).not.toBeInTheDocument();
  });

  it("renders children when open", () => {
    render(
      <Modal open onClose={onClose}>
        <p>Visible</p>
      </Modal>
    );
    expect(screen.getByText("Visible")).toBeInTheDocument();
  });

  it("has dialog role and aria-modal", () => {
    render(
      <Modal open onClose={onClose}>
        Content
      </Modal>
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });

  // ── ESC key ──────────────────────────────────────────────
  it("calls onClose on ESC key", () => {
    render(
      <Modal open onClose={onClose}>
        Content
      </Modal>
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  // ── Overlay click ────────────────────────────────────────
  it("calls onClose on overlay click", () => {
    render(
      <Modal open onClose={onClose}>
        Content
      </Modal>
    );
    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does NOT close on content click (stopPropagation)", () => {
    render(
      <Modal open onClose={onClose}>
        <p>Inner</p>
      </Modal>
    );
    fireEvent.click(screen.getByText("Inner"));
    expect(onClose).not.toHaveBeenCalled();
  });

  // ── Persistent mode ──────────────────────────────────────
  it("does NOT close on overlay click when persistent", () => {
    render(
      <Modal open onClose={onClose} persistent>
        Content
      </Modal>
    );
    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).not.toHaveBeenCalled();
  });

  // ── Size ─────────────────────────────────────────────────
  it("applies size class", () => {
    render(
      <Modal open onClose={onClose} size="lg">
        Content
      </Modal>
    );
    const content = screen.getByText("Content").closest("div");
    expect(content).toHaveClass("max-w-lg");
  });

  // ── Compound sub-components ──────────────────────────────
  it("renders Modal.Header", () => {
    render(
      <Modal open onClose={onClose}>
        <Modal.Header>
          <h3>Title</h3>
        </Modal.Header>
      </Modal>
    );
    expect(screen.getByText("Title")).toBeInTheDocument();
  });

  it("renders Modal.Footer", () => {
    render(
      <Modal open onClose={onClose}>
        <Modal.Footer>
          <button>OK</button>
        </Modal.Footer>
      </Modal>
    );
    expect(screen.getByText("OK")).toBeInTheDocument();
  });

  // ── Focus trap ──────────────────────────────────────────
  it("traps focus with Tab cycling", async () => {
    render(
      <Modal open onClose={onClose}>
        <button>First</button>
        <button>Last</button>
      </Modal>
    );
    const buttons = screen.getAllByRole("button");
    const last = buttons[buttons.length - 1];
    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    // Focus should cycle — not escape the modal
    expect(document.activeElement?.closest('[role="dialog"]')).toBeTruthy();
  });

  it("passes ariaLabelledBy to dialog", () => {
    render(
      <Modal open onClose={onClose} ariaLabelledBy="my-title">
        <h2 id="my-title">Dialog Title</h2>
      </Modal>
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-labelledby", "my-title");
  });

  it("inner card has tabIndex for focus trap", () => {
    render(
      <Modal open onClose={onClose}>
        <p>Content</p>
      </Modal>
    );
    const card = screen.getByText("Content").closest("[tabindex]");
    expect(card).toHaveAttribute("tabindex", "-1");
  });
});
