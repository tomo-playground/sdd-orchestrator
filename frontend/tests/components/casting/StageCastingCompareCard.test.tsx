// @vitest-environment jsdom
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import StageCastingCompareCard from "../../../app/components/studio/StageCastingCompareCard";
import type { CastingRecommendation, Character } from "../../../app/types";

const CASTING: CastingRecommendation = {
  character_id: 2,
  character_name: "Eve",
  character_b_id: null,
  character_b_name: "",
  structure: "Monologue",
  style_profile_id: null,
  reasoning: "Matches the topic well",
};

const CURRENT_CHAR: Character = {
  id: 1,
  name: "Alice",
  style_profile_id: null,
  style_profile_name: null,
  description: null,
  gender: "female",
  identity_tags: null,
  clothing_tags: null,
  tags: null,
  loras: null,
  recommended_negative: null,
  custom_base_prompt: null,
  custom_negative_prompt: null,
  reference_base_prompt: null,
  reference_negative_prompt: null,
  preview_image_asset_id: null,
  preview_image_url: null,
  preview_key: null,
  preview_locked: false,
  ip_adapter_weight: null,
  ip_adapter_model: null,
  voice_preset_id: null,
};

describe("StageCastingCompareCard", () => {
  it("shows current character name and recommended name", () => {
    render(
      <StageCastingCompareCard
        casting={CASTING}
        currentChar={CURRENT_CHAR}
        onAccept={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Eve")).toBeInTheDocument();
  });

  it("shows '미선택' when no current character", () => {
    render(
      <StageCastingCompareCard
        casting={CASTING}
        currentChar={null}
        onAccept={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText("미선택")).toBeInTheDocument();
  });

  it("displays reasoning text", () => {
    render(
      <StageCastingCompareCard
        casting={CASTING}
        currentChar={null}
        onAccept={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText("Matches the topic well")).toBeInTheDocument();
  });

  it("calls onAccept on accept button click", () => {
    const onAccept = vi.fn();
    render(
      <StageCastingCompareCard
        casting={CASTING}
        currentChar={null}
        onAccept={onAccept}
        onDismiss={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText("수락"));
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it("calls onDismiss on dismiss button click", () => {
    const onDismiss = vi.fn();
    render(
      <StageCastingCompareCard
        casting={CASTING}
        currentChar={null}
        onAccept={vi.fn()}
        onDismiss={onDismiss}
      />
    );
    fireEvent.click(screen.getByText("무시"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("shows structure label when present", () => {
    render(
      <StageCastingCompareCard
        casting={CASTING}
        currentChar={null}
        onAccept={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText("Monologue")).toBeInTheDocument();
  });
});
