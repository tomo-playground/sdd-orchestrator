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
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "a" } });
    expect(mockOnChange).toHaveBeenCalledWith("a");
  });

  it("fetches suggestions when typing a word >= 2 chars", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [
        { id: 1, name: "girl", category: "character", priority: 1 },
        { id: 2, name: "1girl", category: "scene", priority: 2 },
      ],
    });

    render(<TagAutocomplete value="" onChange={mockOnChange} />);
    const textarea = screen.getByRole("textbox");

    // Type "gi"
    fireEvent.change(textarea, { target: { value: "gi", selectionStart: 2 } });

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(expect.stringContaining("/tags/search"), expect.any(Object));
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
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;

    // Trigger search by typing "smi"
    fireEvent.change(textarea, { target: { value: "look at that smi", selectionStart: 16 } });

    // Click suggestion

    // Click suggestion
    const suggestion = await screen.findByText("smile");
    fireEvent.click(suggestion);

    // onChange should be called with completed text
    expect(mockOnChange).toHaveBeenCalledWith("look at that smile");
  });
});
