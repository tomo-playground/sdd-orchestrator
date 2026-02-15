import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import ConfirmDialog from "../ui/ConfirmDialog";
import { useConfirm } from "../ui/ConfirmDialog";

describe("ConfirmDialog", () => {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();

  beforeEach(() => {
    onConfirm.mockReset();
    onCancel.mockReset();
  });

  it("renders title and message", () => {
    render(
      <ConfirmDialog
        open
        onConfirm={onConfirm}
        onCancel={onCancel}
        title="Delete Item"
        message="This cannot be undone."
      />,
    );
    expect(screen.getByText("Delete Item")).toBeInTheDocument();
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
  });

  it("uses default title and message", () => {
    render(
      <ConfirmDialog open onConfirm={onConfirm} onCancel={onCancel} />,
    );
    expect(screen.getByRole("heading", { name: "Confirm" })).toBeInTheDocument();
    expect(screen.getByText("Are you sure?")).toBeInTheDocument();
  });

  it("calls onConfirm when confirm button clicked", () => {
    render(
      <ConfirmDialog
        open
        onConfirm={onConfirm}
        onCancel={onCancel}
        confirmLabel="Yes"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Yes" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onCancel when cancel button clicked", () => {
    render(
      <ConfirmDialog
        open
        onConfirm={onConfirm}
        onCancel={onCancel}
        cancelLabel="Nope"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Nope" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("renders danger variant confirm button", () => {
    render(
      <ConfirmDialog
        open
        onConfirm={onConfirm}
        onCancel={onCancel}
        variant="danger"
        confirmLabel="Delete"
      />,
    );
    expect(screen.getByRole("button", { name: "Delete" })).toHaveClass(
      "bg-red-600",
    );
  });

  it("renders primary confirm button for default variant", () => {
    render(
      <ConfirmDialog
        open
        onConfirm={onConfirm}
        onCancel={onCancel}
        confirmLabel="OK"
      />,
    );
    expect(screen.getByRole("button", { name: "OK" })).toHaveClass(
      "bg-zinc-900",
    );
  });
});

// ── useConfirm hook ──────────────────────────────────────────
describe("useConfirm", () => {
  function TestHarness() {
    const { confirm, dialogProps } = useConfirm();

    return (
      <>
        <button
          onClick={async () => {
            const ok = await confirm({
              title: "Sure?",
              message: "Really?",
              variant: "danger",
            });
            document.title = ok ? "confirmed" : "cancelled";
          }}
        >
          Open
        </button>
        <ConfirmDialog {...dialogProps} />
      </>
    );
  }

  it("resolves true on confirm", async () => {
    render(<TestHarness />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Open" }));
    });
    expect(screen.getByText("Sure?")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    });
    expect(document.title).toBe("confirmed");
  });

  it("resolves false on cancel", async () => {
    render(<TestHarness />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Open" }));
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    });
    expect(document.title).toBe("cancelled");
  });
});
