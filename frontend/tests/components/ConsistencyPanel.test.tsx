// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import type { ConsistencyResponse } from "../../app/types";

vi.mock("axios");
vi.mock("../../app/store/useContextStore", () => ({
  useContextStore: vi.fn(),
}));

import ConsistencyPanel from "../../app/components/studio/ConsistencyPanel";
import { useContextStore } from "../../app/store/useContextStore";

const MOCK_DATA: ConsistencyResponse = {
  storyboard_id: 1,
  overall_consistency: 0.85,
  scenes: [
    {
      scene_id: 10,
      scene_order: 1,
      character_id: 1,
      identity_score: 0.9,
      drift_score: 0.1,
      groups: [
        {
          group: "hair_color",
          baseline_tags: ["brown_hair"],
          detected_tags: ["brown_hair"],
          status: "match",
          weight: 1,
        },
        {
          group: "eye_color",
          baseline_tags: ["blue_eyes"],
          detected_tags: ["green_eyes"],
          status: "mismatch",
          weight: 1,
        },
        {
          group: "hair_length",
          baseline_tags: ["long_hair"],
          detected_tags: [],
          status: "missing",
          weight: 0.8,
        },
        {
          group: "hair_style",
          baseline_tags: [],
          detected_tags: [],
          status: "no_data",
          weight: 0.5,
        },
        {
          group: "appearance",
          baseline_tags: [],
          detected_tags: ["glasses"],
          status: "extra",
          weight: 0.6,
        },
        {
          group: "body_feature",
          baseline_tags: [],
          detected_tags: [],
          status: "no_data",
          weight: 0.4,
        },
        {
          group: "skin_color",
          baseline_tags: ["pale_skin"],
          detected_tags: ["pale_skin"],
          status: "match",
          weight: 0.7,
        },
      ],
    },
    {
      scene_id: 11,
      scene_order: 2,
      character_id: 1,
      identity_score: 0.6,
      drift_score: 0.4,
      groups: [
        {
          group: "hair_color",
          baseline_tags: ["brown_hair"],
          detected_tags: ["blonde_hair"],
          status: "mismatch",
          weight: 1,
        },
        {
          group: "eye_color",
          baseline_tags: ["blue_eyes"],
          detected_tags: ["blue_eyes"],
          status: "match",
          weight: 1,
        },
        {
          group: "hair_length",
          baseline_tags: ["long_hair"],
          detected_tags: ["long_hair"],
          status: "match",
          weight: 0.8,
        },
        {
          group: "hair_style",
          baseline_tags: [],
          detected_tags: [],
          status: "no_data",
          weight: 0.5,
        },
        {
          group: "appearance",
          baseline_tags: [],
          detected_tags: [],
          status: "no_data",
          weight: 0.6,
        },
        {
          group: "body_feature",
          baseline_tags: [],
          detected_tags: [],
          status: "no_data",
          weight: 0.4,
        },
        {
          group: "skin_color",
          baseline_tags: ["pale_skin"],
          detected_tags: ["pale_skin"],
          status: "match",
          weight: 0.7,
        },
      ],
    },
  ],
};

function mockStoryboardId(id: number | null) {
  (useContextStore as unknown as ReturnType<typeof vi.fn>).mockImplementation(
    (selector: (s: { storyboardId: number | null }) => unknown) => selector({ storyboardId: id })
  );
}

describe("ConsistencyPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when storyboardId is null", () => {
    mockStoryboardId(null);
    const { container } = render(<ConsistencyPanel />);
    expect(container.innerHTML).toBe("");
  });

  it("shows loading spinner while fetching", () => {
    mockStoryboardId(1);
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    render(<ConsistencyPanel />);
    expect(screen.getByTestId("consistency-loading")).toBeInTheDocument();
  });

  it("displays overall consistency percentage", async () => {
    mockStoryboardId(1);
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: MOCK_DATA });

    render(<ConsistencyPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("overall-consistency")).toHaveTextContent("85%");
    });
  });

  it("renders correct number of scene rows in heatmap", async () => {
    mockStoryboardId(1);
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: MOCK_DATA });

    render(<ConsistencyPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("drift-row-1")).toBeInTheDocument();
      expect(screen.getByTestId("drift-row-2")).toBeInTheDocument();
    });
  });

  it("maps cell colors correctly for each drift status", async () => {
    mockStoryboardId(1);
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: MOCK_DATA });

    render(<ConsistencyPanel />);
    await waitFor(() => {
      const matchCell = screen.getByTestId("cell-1-HC");
      expect(matchCell.dataset.status).toBe("match");
      expect(matchCell.className).toContain("bg-emerald-400");

      const mismatchCell = screen.getByTestId("cell-1-EC");
      expect(mismatchCell.dataset.status).toBe("mismatch");
      expect(mismatchCell.className).toContain("bg-red-400");

      const missingCell = screen.getByTestId("cell-1-HL");
      expect(missingCell.dataset.status).toBe("missing");
      expect(missingCell.className).toContain("bg-amber-400");

      const noDataCell = screen.getByTestId("cell-1-HS");
      expect(noDataCell.dataset.status).toBe("no_data");
      expect(noDataCell.className).toContain("bg-zinc-200");
    });
  });

  it("shows DriftDetailView when a scene row is clicked", async () => {
    mockStoryboardId(1);
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: MOCK_DATA });

    render(<ConsistencyPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("drift-row-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("drift-row-1"));
    expect(screen.getByTestId("drift-detail")).toBeInTheDocument();
  });

  it("shows baseline and detected tags in DriftDetailView", async () => {
    mockStoryboardId(1);
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: MOCK_DATA });

    render(<ConsistencyPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("drift-row-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("drift-row-1"));

    expect(screen.getByTestId("baseline-hair_color")).toHaveTextContent("brown_hair");
    expect(screen.getByTestId("detected-hair_color")).toHaveTextContent("brown_hair");
    expect(screen.getByTestId("baseline-eye_color")).toHaveTextContent("blue_eyes");
    expect(screen.getByTestId("detected-eye_color")).toHaveTextContent("green_eyes");
  });

  // DoD-6: Empty scenes shows "--" instead of percentage
  it("displays '--' when scenes array is empty", async () => {
    mockStoryboardId(1);
    const emptyData: ConsistencyResponse = {
      storyboard_id: 1,
      overall_consistency: 1.0,
      scenes: [],
    };
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: emptyData });

    render(<ConsistencyPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("overall-consistency")).toHaveTextContent("--");
    });
  });

  it("displays percentage when scenes have data", async () => {
    mockStoryboardId(1);
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: MOCK_DATA });

    render(<ConsistencyPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("overall-consistency")).toHaveTextContent("85%");
    });
  });

  it("shows error message on API failure", async () => {
    mockStoryboardId(1);
    const err = new Error("Server error");
    Object.assign(err, { isAxiosError: true, response: { data: { detail: "Server error" } } });
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(err);
    (axios.isAxiosError as unknown as ReturnType<typeof vi.fn>).mockReturnValue(true);

    render(<ConsistencyPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("consistency-error")).toHaveTextContent("Server error");
    });
  });
});
