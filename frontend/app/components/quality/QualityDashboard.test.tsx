/**
 * Tests for QualityDashboard component
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import QualityDashboard from "./QualityDashboard";

// Mock axios
vi.mock("axios", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("QualityDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders dashboard title", () => {
    render(<QualityDashboard storyboardId={1} />);
    expect(screen.getByText("Quality Dashboard")).toBeInTheDocument();
  });

  it("renders refresh button when storyboardId provided", async () => {
    render(<QualityDashboard storyboardId={1} />);
    await waitFor(() => {
      expect(screen.getByText("Refresh")).toBeInTheDocument();
    });
  });

  it("shows description text", () => {
    render(<QualityDashboard storyboardId={1} />);
    expect(
      screen.getByText("Automatic Match Rate tracking for scene validation")
    ).toBeInTheDocument();
  });

  it("shows empty state when no storyboardId", () => {
    render(<QualityDashboard />);
    expect(screen.getByText("No quality data found for this storyboard.")).toBeInTheDocument();
  });
});
