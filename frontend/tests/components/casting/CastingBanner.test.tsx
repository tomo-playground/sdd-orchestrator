// @vitest-environment jsdom
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import CastingBanner from "../../../app/components/scripts/CastingBanner";
import type { CastingRecommendation } from "../../../app/types";

const CASTING: CastingRecommendation = {
  character_a_id: 1,
  character_a_name: "Alice",
  character_b_id: 2,
  character_b_name: "Bob",
  structure: "Dialogue",
  reasoning: "Good chemistry",
};

describe("CastingBanner", () => {
  it("renders character names and structure", () => {
    render(<CastingBanner casting={CASTING} onAccept={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.getByText(/Bob/)).toBeInTheDocument();
    expect(screen.getByText(/Dialogue/)).toBeInTheDocument();
  });

  it("renders reasoning text", () => {
    render(<CastingBanner casting={CASTING} onAccept={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.getByText("Good chemistry")).toBeInTheDocument();
  });

  it("calls onAccept when accept button clicked", () => {
    const onAccept = vi.fn();
    render(<CastingBanner casting={CASTING} onAccept={onAccept} onDismiss={vi.fn()} />);
    fireEvent.click(screen.getByText("수락"));
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it("calls onDismiss when dismiss button clicked", () => {
    const onDismiss = vi.fn();
    render(<CastingBanner casting={CASTING} onAccept={vi.fn()} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByText("무시"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("renders single character without ampersand", () => {
    const single: CastingRecommendation = {
      ...CASTING,
      character_b_id: null,
      character_b_name: "",
    };
    render(<CastingBanner casting={single} onAccept={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.queryByText(/&/)).not.toBeInTheDocument();
  });

  it("hides structure when null", () => {
    const noStructure: CastingRecommendation = { ...CASTING, structure: null };
    render(<CastingBanner casting={noStructure} onAccept={vi.fn()} onDismiss={vi.fn()} />);
    expect(screen.queryByText(/Dialogue/)).not.toBeInTheDocument();
  });
});
