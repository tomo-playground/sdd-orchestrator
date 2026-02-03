import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import AnalyticsDashboard from "../AnalyticsDashboard";
import axios from "axios";

// Mock axios
vi.mock("axios", () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockedAxios = axios as unknown as { get: ReturnType<typeof vi.fn> };

describe("AnalyticsDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders initial state with button and starts loading", async () => {
    mockedAxios.get.mockResolvedValue({ data: { summary: {}, combinations_by_category: {}, suggested_combinations: [] } });
    render(<AnalyticsDashboard storyboardId={1} />);

    expect(screen.getByText("Analytics Dashboard")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
    });
  });

  it("shows idle state when no storyboardId provided", async () => {
    render(<AnalyticsDashboard />);
    expect(screen.getByText("Select a storyboard to view insights")).toBeInTheDocument();
  });

  it("disables button when loading", async () => {
    mockedAxios.get.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({
        data: {
          summary: { total_success: 0, analyzed_tags: 0, categories_found: 0 },
          combinations_by_category: {},
          suggested_combinations: [],
        }
      }), 100))
    );

    render(<AnalyticsDashboard storyboardId={1} />);

    // Initially should be loading
    expect(screen.getByText("Loading...")).toBeInTheDocument();

    // Wait for it to finish
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it("displays summary stats after successful data load", async () => {
    const mockData = {
      summary: {
        total_success: 75,
        analyzed_tags: 120,
        categories_found: 8,
      },
      combinations_by_category: {},
      suggested_combinations: [],
    };

    mockedAxios.get.mockResolvedValue({ data: mockData });

    render(<AnalyticsDashboard storyboardId={1} />);

    await waitFor(() => {
      expect(screen.getByText("75")).toBeInTheDocument();
      expect(screen.getByText("120")).toBeInTheDocument();
      expect(screen.getByText("8")).toBeInTheDocument();
    });

    expect(screen.getByText("Success Cases")).toBeInTheDocument();
    expect(screen.getByText("Tags Analyzed")).toBeInTheDocument();
    expect(screen.getByText("Categories")).toBeInTheDocument();
  });

  it("displays suggested combinations", async () => {
    const mockData = {
      summary: {
        total_success: 50,
        analyzed_tags: 80,
        categories_found: 4,
      },
      combinations_by_category: {},
      suggested_combinations: [
        {
          tags: ["smile", "standing", "cowboy shot", "classroom"],
          categories: ["expression", "pose", "camera", "environment"],
          avg_success_rate: 0.92,
          conflict_free: true,
        },
      ],
    };

    mockedAxios.get.mockResolvedValue({ data: mockData });

    render(<AnalyticsDashboard storyboardId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Suggested Combinations")).toBeInTheDocument();
      expect(screen.getByText("smile")).toBeInTheDocument();
      expect(screen.getByText("standing")).toBeInTheDocument();
      expect(screen.getByText("cowboy shot")).toBeInTheDocument();
      expect(screen.getByText("classroom")).toBeInTheDocument();
      expect(screen.getByText("92.0%", { exact: false })).toBeInTheDocument();
      expect(screen.getByText("✓ Conflict-Free")).toBeInTheDocument();
    });
  });

  it("displays top tags by category", async () => {
    const mockData = {
      summary: {
        total_success: 30,
        analyzed_tags: 50,
        categories_found: 2,
      },
      combinations_by_category: {
        expression: [
          {
            tag: "smile",
            success_rate: 0.95,
            occurrences: 25,
            avg_match_rate: 0.88,
          },
          {
            tag: "happy",
            success_rate: 0.85,
            occurrences: 20,
            avg_match_rate: 0.82,
          },
        ],
        pose: [
          {
            tag: "standing",
            success_rate: 0.90,
            occurrences: 22,
            avg_match_rate: 0.85,
          },
        ],
      },
      suggested_combinations: [],
    };

    mockedAxios.get.mockResolvedValue({ data: mockData });

    render(<AnalyticsDashboard storyboardId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Top Tags by Category")).toBeInTheDocument();
      expect(screen.getByText("expression")).toBeInTheDocument();
      expect(screen.getByText("pose")).toBeInTheDocument();
      expect(screen.getByText("smile")).toBeInTheDocument();
      expect(screen.getByText("happy")).toBeInTheDocument();
      expect(screen.getByText("standing")).toBeInTheDocument();
    });

    // Check statistics
    expect(screen.getByText("95% success", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("25x used", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("88% match", { exact: false })).toBeInTheDocument();
  });

  it("handles API error gracefully", async () => {
    mockedAxios.get.mockRejectedValue({
      response: { data: { detail: "Data not found" } },
    });

    render(<AnalyticsDashboard storyboardId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Data not found")).toBeInTheDocument();
    });
  });

  it("makes API call with correct parameters", async () => {
    mockedAxios.get.mockResolvedValue({
      data: {
        summary: { total_success: 0, analyzed_tags: 0, categories_found: 0 },
        combinations_by_category: {},
        suggested_combinations: [],
      },
    });

    render(<AnalyticsDashboard storyboardId={1} />);

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.stringContaining("/activity-logs/success-combinations"),
        expect.objectContaining({
          params: expect.objectContaining({
            storyboard_id: 1,
            match_rate_threshold: 0.7,
            min_occurrences: 2,
            top_n_per_category: 10,
          }),
        })
      );
    });
  });
});
