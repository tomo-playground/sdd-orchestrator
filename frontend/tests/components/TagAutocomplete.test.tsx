// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import TagAutocomplete from "../../app/components/ui/TagAutocomplete";

vi.mock("axios");

describe("TagAutocomplete", () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders textarea with initial value", () => {
    render(<TagAutocomplete value="initial text" onChange={mockOnChange} />);
    const textarea = screen.getByDisplayValue("initial text");
    expect(textarea).toBeInTheDocument();
  });

  it("calls onChange when typing", () => {
    render(<TagAutocomplete value="" onChange={mockOnChange} />);
    const textarea = screen.getByRole("combobox");
    fireEvent.change(textarea, { target: { value: "a" } });
    expect(mockOnChange).toHaveBeenCalledWith("a");
  });

  it("fetches suggestions when typing a word >= 2 chars", async () => {
    vi.useFakeTimers();
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [
        { id: 1, name: "girl", category: "character", priority: 1 },
        { id: 2, name: "1girl", category: "scene", priority: 2 },
      ],
    });

    render(<TagAutocomplete value="" onChange={mockOnChange} />);
    const textarea = screen.getByRole("combobox");

    // Type "gi"
    fireEvent.change(textarea, { target: { value: "gi", selectionStart: 2 } });

    vi.advanceTimersByTime(300);
    vi.useRealTimers();

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(
        expect.stringContaining("/tags/search"),
        expect.any(Object)
      );
    });

    // Suggestions should appear
    expect(await screen.findByText("girl")).toBeInTheDocument();
    expect(screen.getByText("1girl")).toBeInTheDocument();
  });

  it("inserts selected tag into text", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [{ id: 1, name: "smile", category: "expression" }],
    });

    // Simple render for unit test without wrapper logic complexity
    // Start with "look at that " and type "smi" to ensure change event fires
    render(<TagAutocomplete value="look at that " onChange={mockOnChange} />);
    const textarea = screen.getByRole("combobox") as HTMLTextAreaElement;

    // Trigger search by typing "smi"
    vi.useFakeTimers();
    fireEvent.change(textarea, { target: { value: "look at that smi", selectionStart: 16 } });
    vi.advanceTimersByTime(300);
    vi.useRealTimers();

    // Click suggestion
    const suggestion = await screen.findByText("smile");
    fireEvent.click(suggestion);

    // onChange should be called with completed text + comma separator
    expect(mockOnChange).toHaveBeenCalledWith("look at that smile, ");
  });

  // ── New tests (Phase 15-A-1) ──

  it("debounces API calls (300ms)", async () => {
    vi.useFakeTimers();
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [{ id: 1, name: "brown_hair", category: "character", priority: 1 }],
    });

    render(<TagAutocomplete value="" onChange={mockOnChange} />);
    const textarea = screen.getByRole("combobox");

    fireEvent.change(textarea, { target: { value: "bro", selectionStart: 3 } });

    // Not called immediately
    expect(axios.get).not.toHaveBeenCalled();

    // After 300ms
    vi.advanceTimersByTime(300);
    await vi.waitFor(() => {
      expect(axios.get).toHaveBeenCalledTimes(1);
    });

    vi.useRealTimers();
  });

  it("triggers search for Korean input with 1 char", async () => {
    vi.useFakeTimers();
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [
        {
          id: 1,
          name: "brown_hair",
          category: "character",
          ko_name: "갈색_머리",
          priority: 1,
        },
      ],
    });

    render(<TagAutocomplete value="" onChange={mockOnChange} />);
    const textarea = screen.getByRole("combobox");

    fireEvent.change(textarea, { target: { value: "갈", selectionStart: 1 } });

    vi.advanceTimersByTime(300);
    await vi.waitFor(() => {
      expect(axios.get).toHaveBeenCalledTimes(1);
    });

    vi.useRealTimers();
  });

  it("appends comma separator after tag selection", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [{ id: 1, name: "smile", category: "expression", priority: 1 }],
    });

    render(<TagAutocomplete value="" onChange={mockOnChange} />);
    const textarea = screen.getByRole("combobox");

    // Use fake timers for debounce
    vi.useFakeTimers();
    fireEvent.change(textarea, { target: { value: "smi", selectionStart: 3 } });
    vi.advanceTimersByTime(300);
    vi.useRealTimers();

    const suggestion = await screen.findByText("smile");
    fireEvent.click(suggestion);

    expect(mockOnChange).toHaveBeenCalledWith("smile, ");
  });

  it("displays wd14_count in dropdown", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [{ id: 1, name: "brown_hair", category: "character", priority: 1, wd14_count: 125000 }],
    });

    render(<TagAutocomplete value="" onChange={mockOnChange} />);
    const textarea = screen.getByRole("combobox");

    vi.useFakeTimers();
    fireEvent.change(textarea, { target: { value: "bro", selectionStart: 3 } });
    vi.advanceTimersByTime(300);
    vi.useRealTimers();

    expect(await screen.findByText("125K")).toBeInTheDocument();
  });

  it("shows deprecated tag with strikethrough", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [
        {
          id: 1,
          name: "medium_shot",
          category: "scene",
          priority: 100,
          is_active: false,
          deprecated_reason: "Use cowboy_shot",
          replacement_tag_name: "cowboy_shot",
        },
      ],
    });

    render(<TagAutocomplete value="" onChange={mockOnChange} />);
    const textarea = screen.getByRole("combobox");

    vi.useFakeTimers();
    fireEvent.change(textarea, { target: { value: "medium", selectionStart: 6 } });
    vi.advanceTimersByTime(300);
    vi.useRealTimers();

    const tagName = await screen.findByText("medium_shot");
    expect(tagName).toHaveClass("line-through");

    // Replacement arrow and deprecated reason should be visible
    const matches = screen.getAllByText(/cowboy_shot/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });
});
