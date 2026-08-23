import { describe, expect, it, beforeEach, vi, afterEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useRunsStore } from "./runs";

describe("runs store: tolerates an absent runs/index.json", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("treats a 404 as 'missing', not an error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 404 })),
    );
    const store = useRunsStore();
    await store.load();
    expect(store.status).toBe("missing");
    expect(store.runs).toEqual([]);
    expect(store.error).toBeNull();
  });

  it("loads runs from a present index.json", async () => {
    const body = {
      runs: [
        {
          run_id: "dummy-run",
          seed_id: "dummy",
          created: "2026-08-22T00:00:00Z",
          tick_range: [0, 499],
          streams: ["events.jsonl"],
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
    );
    const store = useRunsStore();
    await store.load();
    expect(store.status).toBe("loaded");
    expect(store.runs).toHaveLength(1);
    expect(store.runs[0]?.run_id).toBe("dummy-run");
  });

  it("records a fetch failure as an error, not a crash", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );
    const store = useRunsStore();
    await store.load();
    expect(store.status).toBe("error");
    expect(store.error).toContain("network down");
  });

  describe("pickableRuns (the mock-t0 fixture is always pickable)", () => {
    it("adds the mock-t0 fixture even when no real registry has been loaded (runs stays untouched)", () => {
      const store = useRunsStore();
      expect(store.runs).toEqual([]);
      expect(store.pickableRuns.map((r) => r.run_id)).toEqual(["mock-t0"]);
    });

    it("adds the mock-t0 fixture alongside real runs, without duplicating or mutating `runs`", async () => {
      const body = {
        runs: [
          {
            run_id: "dummy-run",
            seed_id: "dummy",
            created: "2026-08-22T00:00:00Z",
            tick_range: [0, 499],
            streams: ["events.jsonl"],
          },
        ],
      };
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
      );
      const store = useRunsStore();
      await store.load();
      expect(store.runs).toHaveLength(1); // Lane 5's original contract, unchanged
      expect(store.pickableRuns.map((r) => r.run_id).sort()).toEqual(["dummy-run", "mock-t0"]);
    });

    it("does not add a second mock-t0 if the real registry already lists one", async () => {
      const body = { runs: [{ run_id: "mock-t0", seed_id: "mock-t0", created: "x", tick_range: [0, 1], streams: [] }] };
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
      );
      const store = useRunsStore();
      await store.load();
      expect(store.pickableRuns.filter((r) => r.run_id === "mock-t0")).toHaveLength(1);
    });
  });
});
