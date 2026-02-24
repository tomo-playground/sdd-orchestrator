// @vitest-environment jsdom
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import TagSuggestionDropdown from "../../app/components/ui/TagSuggestionDropdown";
import type { Tag } from "../../app/types";
import React from "react";

const baseMock = {
  highlightedIndex: -1,
  onSelect: vi.fn(),
  onHighlight: vi.fn(),
  dropdownRef: { current: null } as React.RefObject<HTMLDivElement | null>,
  listboxId: "test-listbox",
};

const tagWithThumb: Tag = {
  id: 1,
  name: "smile",
  category: "scene",
  group_name: "expression",
  priority: 3,
  thumbnail_url: "http://localhost/thumb/smile.webp",
};

const tagNoThumb: Tag = {
  id: 2,
  name: "cowboy_shot",
  category: "scene",
  group_name: "camera",
  priority: 5,
  thumbnail_url: null,
};

describe("TagSuggestionDropdown thumbnails", () => {
  it("renders <img> when thumbnail_url is present", () => {
    render(
      <TagSuggestionDropdown {...baseMock} suggestions={[tagWithThumb]} />,
    );
    const img = screen.getByRole("img", { name: "smile" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", tagWithThumb.thumbnail_url);
  });

  it("renders color block fallback when no thumbnail", () => {
    const { container } = render(
      <TagSuggestionDropdown {...baseMock} suggestions={[tagNoThumb]} />,
    );
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    const fallback = container.querySelector(".bg-purple-200");
    expect(fallback).toBeInTheDocument();
  });

  it("falls back to color block on image error", () => {
    const { container } = render(
      <TagSuggestionDropdown {...baseMock} suggestions={[tagWithThumb]} />,
    );
    const img = screen.getByRole("img", { name: "smile" });
    fireEvent.error(img);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    const fallback = container.querySelector(".bg-amber-200");
    expect(fallback).toBeInTheDocument();
  });
});
