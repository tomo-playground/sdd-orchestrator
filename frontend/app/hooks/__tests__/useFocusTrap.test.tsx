import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { useRef } from "react";
import { useFocusTrap } from "../useFocusTrap";

function TrapHarness({ active }: { active: boolean }) {
  const trapRef = useFocusTrap(active);
  return (
    <div ref={trapRef} tabIndex={-1} data-testid="trap">
      <button data-testid="first">First</button>
      <button data-testid="second">Second</button>
      <button data-testid="last">Last</button>
    </div>
  );
}

function TrapWithInitialFocus({ active }: { active: boolean }) {
  const initialRef = useRef<HTMLButtonElement>(null);
  const trapRef = useFocusTrap(active, initialRef);
  return (
    <div ref={trapRef} tabIndex={-1}>
      <button>First</button>
      <button ref={initialRef} data-testid="target">
        Target
      </button>
    </div>
  );
}

describe("useFocusTrap", () => {
  it("cycles focus from last to first on Tab", () => {
    const { getByTestId } = render(<TrapHarness active />);
    const last = getByTestId("last");
    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    // After Tab on last element, focus should wrap to first
    expect(document.activeElement).toBe(getByTestId("first"));
  });

  it("cycles focus from first to last on Shift+Tab", () => {
    const { getByTestId } = render(<TrapHarness active />);
    const first = getByTestId("first");
    first.focus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(getByTestId("last"));
  });

  it("does not trap when inactive", () => {
    const { getByTestId } = render(<TrapHarness active={false} />);
    const last = getByTestId("last");
    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    // Should not prevent default — focus stays unchanged (no trap active)
    expect(document.activeElement).toBe(last);
  });

  it("restores focus on deactivation", () => {
    const outerBtn = document.createElement("button");
    outerBtn.textContent = "Outside";
    document.body.appendChild(outerBtn);
    outerBtn.focus();

    const { unmount } = render(<TrapHarness active />);
    unmount();

    expect(document.activeElement).toBe(outerBtn);
    document.body.removeChild(outerBtn);
  });

  it("focuses initialFocusRef when provided", async () => {
    const { getByTestId } = render(<TrapWithInitialFocus active />);
    // requestAnimationFrame used for initial focus
    await new Promise((r) => requestAnimationFrame(r));
    expect(document.activeElement).toBe(getByTestId("target"));
  });
});
