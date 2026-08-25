import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useLivePositionsStore } from "./livePositions";

describe("livePositions store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("starts with no snapshot and not enabled", () => {
    const store = useLivePositionsStore();
    expect(store.snapshot).toBeNull();
    expect(store.enabled).toBe(false);
  });

  it("poll() sets the snapshot from a successful fetch", async () => {
    const snapshot = { wall_ts: 1000, npcs: [{ id: "jarl_balgruuf", name: "Jarl Balgruuf", x: 1, y: 2 }] };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(snapshot) }),
    );
    const store = useLivePositionsStore();
    await store.poll();
    expect(store.snapshot).toEqual(snapshot);
  });

  it("poll() leaves the previous snapshot in place on a non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    const store = useLivePositionsStore();
    store.snapshot = { wall_ts: 1, npcs: [] };
    await store.poll();
    expect(store.snapshot).toEqual({ wall_ts: 1, npcs: [] });
  });

  it("poll() leaves the previous snapshot in place when fetch throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    const store = useLivePositionsStore();
    store.snapshot = { wall_ts: 1, npcs: [] };
    await store.poll();
    expect(store.snapshot).toEqual({ wall_ts: 1, npcs: [] });
  });

  it("start() polls immediately and then on the given interval; stop() halts it", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ wall_ts: 1, npcs: [] }) });
    vi.stubGlobal("fetch", fetchMock);
    const store = useLivePositionsStore();

    store.start(1000);
    expect(store.enabled).toBe(true);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    await vi.advanceTimersByTimeAsync(1000);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    store.stop();
    expect(store.enabled).toBe(false);
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("start() is a no-op if already started (no duplicate interval)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ wall_ts: 1, npcs: [] }) });
    vi.stubGlobal("fetch", fetchMock);
    const store = useLivePositionsStore();
    store.start(1000);
    store.start(1000);
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
