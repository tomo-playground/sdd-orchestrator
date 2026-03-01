import { describe, it, expect, vi } from "vitest";
import axios, { AxiosError, AxiosHeaders } from "axios";
import { getErrorMsg } from "../error";

describe("getErrorMsg", () => {
  it("returns detail string from AxiosError response", () => {
    const error = new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, undefined, {
      data: { detail: "Invalid input" },
      status: 400,
      statusText: "Bad Request",
      headers: {},
      config: { headers: new AxiosHeaders() },
    });
    expect(getErrorMsg(error, "fallback")).toBe("Invalid input");
  });

  it("returns detail.message from structured AxiosError response", () => {
    const error = new AxiosError("Request failed", "ERR_BAD_REQUEST", undefined, undefined, {
      data: { detail: { message: "Structured error message", code: "ERR_001" } },
      status: 400,
      statusText: "Bad Request",
      headers: {},
      config: { headers: new AxiosHeaders() },
    });
    expect(getErrorMsg(error, "fallback")).toBe("Structured error message");
  });

  it("returns axios error.message when no detail", () => {
    const error = new AxiosError("Network Error", "ERR_NETWORK");
    expect(getErrorMsg(error, "fallback")).toBe("Network Error");
  });

  it("returns message from generic Error", () => {
    const error = new Error("Something went wrong");
    expect(getErrorMsg(error, "fallback")).toBe("Something went wrong");
  });

  it("returns fallback for non-Error values", () => {
    expect(getErrorMsg("string error", "fallback")).toBe("fallback");
    expect(getErrorMsg(42, "fallback")).toBe("fallback");
    expect(getErrorMsg(null, "fallback")).toBe("fallback");
    expect(getErrorMsg(undefined, "fallback")).toBe("fallback");
  });
});
