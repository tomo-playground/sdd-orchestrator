/**
 * Tests for QualityDashboard component
 *
 * Note: These are basic structural tests. Full integration tests
 * with API mocking would require more setup.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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
    render(<QualityDashboard />);
    expect(screen.getByText("Quality Dashboard")).toBeInTheDocument();
  });

  it("renders project name input", () => {
    render(<QualityDashboard />);
    const input = screen.getByPlaceholderText("Project name");
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue("my_shorts"); // Default value
  });

  it("renders load button", () => {
    render(<QualityDashboard />);
    const button = screen.getByText("Load Quality");
    expect(button).toBeInTheDocument();
  });

  it("updates project name on input change", () => {
    render(<QualityDashboard />);
    const input = screen.getByPlaceholderText("Project name") as HTMLInputElement;

    fireEvent.change(input, { target: { value: "test_project" } });
    expect(input.value).toBe("test_project");
  });

  it("disables load button when project name is empty", () => {
    render(<QualityDashboard />);
    const input = screen.getByPlaceholderText("Project name") as HTMLInputElement;
    const button = screen.getByText("Load Quality");

    fireEvent.change(input, { target: { value: "" } });
    expect(button).toBeDisabled();
  });

  it("shows description text", () => {
    render(<QualityDashboard />);
    expect(
      screen.getByText("Automatic Match Rate tracking for scene validation")
    ).toBeInTheDocument();
  });
});

describe("QualityDashboard - Summary Display", () => {
  it("shows empty state message when no data", () => {
    render(<QualityDashboard />);
    // Initially no summary data, so no empty state shown yet
    // This would require loading data first
  });

  // Note: Full integration tests with API mocking would go here
  // These would test:
  // - Loading state display
  // - Error state display
  // - Summary stats display
  // - Scene quality bars rendering
  // - Badge color coding (✅ ⚠️ 🔴)
});
