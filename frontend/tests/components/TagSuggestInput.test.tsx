// @vitest-environment jsdom
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import TagSuggestInput from "../../app/components/ui/TagSuggestInput";

vi.mock("axios");

describe("TagSuggestInput", () => {
  const mockOnTagSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty input with placeholder", () => {
    render(<TagSuggestInput onTagSelect={mockOnTagSelect} placeholder="Add tag..." />);
    const input = screen.getByPlaceholderText("Add tag...");
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue("");
  });

  it("debounces API calls (300ms)", async () => {
    vi.useFakeTimers();
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [{ id: 1, name: "brown_hair", category: "character", priority: 1 }],
    });

    render(<TagSuggestInput onTagSelect={mockOnTagSelect} />);
    const input = screen.getByRole("combobox");

    fireEvent.change(input, { target: { value: "bro" } });

    // Not called immediately
    expect(axios.get).not.toHaveBeenCalled();

    // After 300ms
    vi.advanceTimersByTime(300);
    await vi.waitFor(() => {
      expect(axios.get).toHaveBeenCalledTimes(1);
    });

    vi.useRealTimers();
  });

  it("selects tag from dropdown and clears input", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [{ id: 1, name: "smile", category: "expression", priority: 1 }],
    });

    render(<TagSuggestInput onTagSelect={mockOnTagSelect} />);
    const input = screen.getByRole("combobox");

    vi.useFakeTimers();
    fireEvent.change(input, { target: { value: "smi" } });
    vi.advanceTimersByTime(300);
    vi.useRealTimers();

    const suggestion = await screen.findByText("smile");
    fireEvent.click(suggestion);

    expect(mockOnTagSelect).toHaveBeenCalledWith("smile");
    expect(input).toHaveValue("");
  });

  it("submits raw value on Enter when dropdown is closed", () => {
    render(<TagSuggestInput onTagSelect={mockOnTagSelect} />);
    const input = screen.getByRole("combobox");

    fireEvent.change(input, { target: { value: "custom_tag" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(mockOnTagSelect).toHaveBeenCalledWith("custom_tag");
    expect(input).toHaveValue("");
  });

  it("triggers search for Korean input with 1 char", async () => {
    vi.useFakeTimers();
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [
        { id: 1, name: "brown_hair", category: "character", ko_name: "갈색_머리", priority: 1 },
      ],
    });

    render(<TagSuggestInput onTagSelect={mockOnTagSelect} />);
    const input = screen.getByRole("combobox");

    fireEvent.change(input, { target: { value: "갈" } });

    vi.advanceTimersByTime(300);
    await vi.waitFor(() => {
      expect(axios.get).toHaveBeenCalledTimes(1);
    });

    vi.useRealTimers();
  });
});
