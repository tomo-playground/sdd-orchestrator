import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";
import { fetchGroups, createGroup, updateGroup, deleteGroup } from "../groupActions";
import { useContextStore } from "../../useContextStore";
import { useUIStore } from "../../useUIStore";

vi.mock("axios");

describe("fetchGroups", () => {
  const mockSetContextLoading = vi.fn();
  const mockSetGroups = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useContextStore, "getState").mockReturnValue({
      setContextLoading: mockSetContextLoading,
      setGroups: mockSetGroups,
      projectId: 1,
    } as never);
  });

  it("fetches groups and stores them", async () => {
    const groups = [{ id: 1, name: "Group 1" }];
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: groups });

    await fetchGroups(1);

    expect(mockSetContextLoading).toHaveBeenCalledWith({ isLoadingGroups: true });
    expect(mockSetGroups).toHaveBeenCalledWith(groups);
    expect(mockSetContextLoading).toHaveBeenCalledWith({ isLoadingGroups: false });
  });

  it("sets loading to false on error", async () => {
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("fail"));

    await fetchGroups(1);

    expect(mockSetContextLoading).toHaveBeenCalledWith({ isLoadingGroups: false });
  });
});

describe("createGroup", () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useUIStore, "getState").mockReturnValue({ showToast: mockShowToast } as never);
    vi.spyOn(useContextStore, "getState").mockReturnValue({
      projectId: 1,
      setContextLoading: vi.fn(),
      setGroups: vi.fn(),
    } as never);
  });

  it("creates group and shows success toast", async () => {
    const group = { id: 1, name: "New Group" };
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: group });
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [group] });

    const result = await createGroup({ project_id: 1, name: "New Group" });

    expect(result).toEqual(group);
    expect(mockShowToast).toHaveBeenCalledWith("시리즈 생성됨", "success");
  });

  it("returns undefined and shows error on failure", async () => {
    (axios.post as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("fail"));

    const result = await createGroup({ project_id: 1, name: "Fail" });

    expect(result).toBeUndefined();
    expect(mockShowToast).toHaveBeenCalledWith("시리즈 생성 실패", "error");
  });
});

describe("updateGroup", () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useUIStore, "getState").mockReturnValue({ showToast: mockShowToast } as never);
    vi.spyOn(useContextStore, "getState").mockReturnValue({
      projectId: 1,
      setContextLoading: vi.fn(),
      setGroups: vi.fn(),
    } as never);
  });

  it("updates group and shows success toast", async () => {
    const group = { id: 1, name: "Updated" };
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: group });
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [group] });

    const result = await updateGroup(1, { name: "Updated" });

    expect(result).toEqual(group);
    expect(mockShowToast).toHaveBeenCalledWith("시리즈 수정됨", "success");
  });

  it("returns undefined on failure", async () => {
    (axios.put as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("fail"));

    const result = await updateGroup(1, { name: "Fail" });

    expect(result).toBeUndefined();
    expect(mockShowToast).toHaveBeenCalledWith("시리즈 수정 실패", "error");
  });
});

describe("deleteGroup", () => {
  const mockShowToast = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useUIStore, "getState").mockReturnValue({ showToast: mockShowToast } as never);
    vi.spyOn(useContextStore, "getState").mockReturnValue({
      projectId: 1,
      setContextLoading: vi.fn(),
      setGroups: vi.fn(),
    } as never);
  });

  it("deletes group and shows success toast", async () => {
    (axios.delete as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({});
    (axios.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [] });

    const result = await deleteGroup(1);

    expect(result).toBe(true);
    expect(mockShowToast).toHaveBeenCalledWith("시리즈 삭제됨", "success");
  });

  it("shows conflict message for 409 error", async () => {
    const error = {
      isAxiosError: true,
      response: { status: 409, data: { detail: "Has storyboards" } },
    };
    (axios.delete as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(error);
    vi.spyOn(axios, "isAxiosError").mockReturnValue(true);

    const result = await deleteGroup(1);

    expect(result).toBe(false);
    expect(mockShowToast).toHaveBeenCalledWith("삭제 불가: 영상이 존재합니다", "error");
  });

  it("shows generic error on other failures", async () => {
    (axios.delete as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("fail"));
    vi.spyOn(axios, "isAxiosError").mockReturnValue(false);

    const result = await deleteGroup(1);

    expect(result).toBe(false);
    expect(mockShowToast).toHaveBeenCalledWith("시리즈 삭제 실패", "error");
  });
});
