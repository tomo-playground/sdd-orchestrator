import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WelcomeBar from "../home/WelcomeBar";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock axios
vi.mock("axios", () => ({
  default: {
    post: vi.fn(),
  },
}));
import axios from "axios";

// Mock stores
const mockContextState = { projectId: null as number | null, groupId: null as number | null };
vi.mock("../../store/useContextStore", () => ({
  useContextStore: (selector: (s: typeof mockContextState) => unknown) => selector(mockContextState),
}));

const mockShowToast = vi.fn();
vi.mock("../../store/useUIStore", () => ({
  useUIStore: (selector: (s: { showToast: typeof mockShowToast }) => unknown) =>
    selector({ showToast: mockShowToast }),
}));

// Mock fetch for storyboard count
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve({ total: 5, items: [] }),
});

beforeEach(() => {
  vi.clearAllMocks();
  mockContextState.projectId = null;
  mockContextState.groupId = null;
});

describe("WelcomeBar Quick Start", () => {
  it("hides quick start input when projectId is null", () => {
    mockContextState.projectId = null;
    mockContextState.groupId = 1;
    render(<WelcomeBar />);
    expect(screen.queryByPlaceholderText("어떤 영상을 만들까요?")).not.toBeInTheDocument();
  });

  it("hides quick start input when groupId is null", () => {
    mockContextState.projectId = 1;
    mockContextState.groupId = null;
    render(<WelcomeBar />);
    expect(screen.queryByPlaceholderText("어떤 영상을 만들까요?")).not.toBeInTheDocument();
  });

  it("shows quick start input when projectId and groupId both exist", () => {
    mockContextState.projectId = 1;
    mockContextState.groupId = 2;
    render(<WelcomeBar />);
    expect(screen.getByPlaceholderText("어떤 영상을 만들까요?")).toBeInTheDocument();
  });

  it("does not call API when submitting empty topic", () => {
    mockContextState.projectId = 1;
    mockContextState.groupId = 2;
    render(<WelcomeBar />);
    const form = screen.getByPlaceholderText("어떤 영상을 만들까요?").closest("form")!;
    fireEvent.submit(form);
    expect(axios.post).not.toHaveBeenCalled();
  });

  it("calls draft API and navigates on submit", async () => {
    mockContextState.projectId = 1;
    mockContextState.groupId = 2;
    vi.mocked(axios.post).mockResolvedValueOnce({ data: { storyboard_id: 42 } });

    render(<WelcomeBar />);
    const input = screen.getByPlaceholderText("어떤 영상을 만들까요?");
    fireEvent.change(input, { target: { value: "고양이 영상" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("/storyboards/draft"),
        { title: "고양이 영상", group_id: 2 },
        expect.any(Object),
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        expect.stringContaining("/studio?id=42&topic="),
      );
    });
  });

  it("shows toast on API error", async () => {
    mockContextState.projectId = 1;
    mockContextState.groupId = 2;
    vi.mocked(axios.post).mockRejectedValueOnce(new Error("fail"));

    render(<WelcomeBar />);
    const input = screen.getByPlaceholderText("어떤 영상을 만들까요?");
    fireEvent.change(input, { target: { value: "테스트" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith("영상 생성에 실패했습니다", "error");
    });
  });
});
