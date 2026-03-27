import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { checkYouTubeConnection } from "../youtubeActions";

vi.mock("axios", async (importOriginal) => {
  const actual = await importOriginal<typeof import("axios")>();
  return {
    ...actual,
    default: {
      ...actual.default,
      get: vi.fn(),
      isAxiosError: actual.default.isAxiosError,
    },
  };
});

describe("checkYouTubeConnection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns credential on success", async () => {
    const cred = { channel_id: "UC123", channel_title: "Test" };
    (axios.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: cred });

    const result = await checkYouTubeConnection(1);
    expect(result).toEqual(cred);
  });

  it("returns null on 404", async () => {
    const err = new axios.AxiosError("Not Found", "ERR_BAD_REQUEST", undefined, {}, {
      status: 404,
      data: {},
      headers: {},
      statusText: "Not Found",
      config: {},
    } as never);
    (axios.get as ReturnType<typeof vi.fn>).mockRejectedValue(err);

    const result = await checkYouTubeConnection(1);
    expect(result).toBeNull();
  });

  it("returns null on network error (no response)", async () => {
    const err = new axios.AxiosError("Network Error", "ERR_NETWORK");
    (axios.get as ReturnType<typeof vi.fn>).mockRejectedValue(err);

    const result = await checkYouTubeConnection(1);
    expect(result).toBeNull();
  });

  it("throws on non-network server errors", async () => {
    const err = new axios.AxiosError("Server Error", "ERR_BAD_RESPONSE", undefined, {}, {
      status: 500,
      data: {},
      headers: {},
      statusText: "Internal Server Error",
      config: {},
    } as never);
    (axios.get as ReturnType<typeof vi.fn>).mockRejectedValue(err);

    await expect(checkYouTubeConnection(1)).rejects.toThrow("Server Error");
  });
});
