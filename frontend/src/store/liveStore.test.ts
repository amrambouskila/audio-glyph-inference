import { beforeEach, describe, expect, it } from "vitest";
import { useLiveStore } from "./liveStore";

describe("useLiveStore", () => {
  beforeEach(() => {
    useLiveStore.setState({
      candidateId: "",
      glyphTargetId: "",
      status: "idle",
      selectedLetter: "",
      generated: [],
      target: [],
      scoreHistory: [],
      error: null
    });
  });

  it("preserves the live status when clearing an error", () => {
    useLiveStore.setState({ status: "connected", error: "catalog failed" });

    useLiveStore.getState().setError(null);

    expect(useLiveStore.getState().error).toBeNull();
    expect(useLiveStore.getState().status).toBe("connected");
  });

  it("marks the session errored when setting an error", () => {
    useLiveStore.setState({ status: "streaming" });

    useLiveStore.getState().setError("live socket error");

    expect(useLiveStore.getState().error).toBe("live socket error");
    expect(useLiveStore.getState().status).toBe("error");
  });

  it("accepts a score by clearing errors and entering streaming state", () => {
    useLiveStore.setState({ status: "error", error: "previous error" });

    useLiveStore.getState().acceptScore([{ x: 0, y: 0 }], [{ x: 1, y: 1 }], 0.25, 1000, "\u05d0");

    const state = useLiveStore.getState();
    expect(state.error).toBeNull();
    expect(state.status).toBe("streaming");
    expect(state.scoreHistory).toEqual([{ atMs: 1000, distance: 0.25, letter: "\u05d0" }]);
  });
});
