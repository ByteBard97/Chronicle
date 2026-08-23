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
});
