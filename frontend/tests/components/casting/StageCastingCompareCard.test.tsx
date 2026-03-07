// @vitest-environment jsdom
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import StageCastingCompareCard from "../../../app/components/studio/StageCastingCompareCard";
import type { CastingRecommendation, Character } from "../../../app/types";

const CASTING: CastingRecommendation = {
  character_a_id: 2,
  character_a_name: "Eve",
  character_b_id: null,
  character_b_name: "",
  structure: "Monologue",
  reasoning: "Matches the topic well",
};

const CURRENT_CHAR: Character = {
  id: 1,
  name: "Alice",
  group_id: 1,
  group_name: "Default Group",
  description: null,
  gender: "female",
  identity_tags: null,
  clothing_tags: null,
  tags: null,
  loras: null,
  common_negative_prompts: null,
  scene_positive_prompt: null,
  scene_negative_prompt: null,
  reference_positive_prompt: null,
  reference_negative_prompt: null,
  reference_image_asset_id: null,
  reference_image_url: null,
  reference_key: null,
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
