// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TagBrowserTab from "../../app/admin/lab/tabs/TagBrowserTab";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockTags = [
  {
    id: 1,
    name: "smile",
    category: "scene",
    group_name: "expression",
    priority: 3,
    wd14_count: 125000,
    thumbnail_url: "http://localhost/thumb/smile.webp",
  },
  {
    id: 2,
    name: "angry",
    category: "scene",
    group_name: "expression",
    priority: 5,
    wd14_count: 8000,
    thumbnail_url: null,
  },
  {
    id: 3,
    name: "crying",
    category: "scene",
    group_name: "expression",
    priority: 4,
    wd14_count: 0,
    thumbnail_url: null,
  },
];

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  vi.clearAllMocks();
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => ({ tags: mockTags }),
  });
});

describe("TagBrowserTab", () => {
  it("renders 7 group buttons in sidebar", async () => {
    render(<TagBrowserTab />);
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    const groups = [
      "Expression",
      "Pose",
      "Camera",
      "Clothing Top",
      "Clothing Outfit",
      "Hair Color",
      "Hair Style",
    ];
    for (const label of groups) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("fetches tags for active group on mount", async () => {
    render(<TagBrowserTab />);
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("group_name=expression"),
      );
    });
  });

  it("fetches new tags when switching groups", async () => {
    render(<TagBrowserTab />);
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    fireEvent.click(screen.getByText("Pose"));
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("group_name=pose"),
      );
    });
  });

  it("filters tags by search input", async () => {
    render(<TagBrowserTab />);
    await waitFor(() =>
      expect(screen.getByText("smile")).toBeInTheDocument(),
    );

    const input = screen.getByPlaceholderText("Search tags...");
    fireEvent.change(input, { target: { value: "smile" } });

    expect(screen.getByText("smile")).toBeInTheDocument();
    expect(screen.queryByText("angry")).not.toBeInTheDocument();
  });

  it("renders tag cards with thumbnail and fallback", async () => {
    render(<TagBrowserTab />);
    await waitFor(() =>
      expect(screen.getByText("smile")).toBeInTheDocument(),
    );

    // Tag with thumbnail shows img
    const img = screen.getByAltText("smile");
    expect(img).toHaveAttribute("src", "http://localhost/thumb/smile.webp");

    // Tag without thumbnail shows text fallback (appears in both card image area and name label)
    expect(screen.getAllByText("angry").length).toBeGreaterThanOrEqual(1);
  });

  it("shows loading spinner while fetching", () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<TagBrowserTab />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
