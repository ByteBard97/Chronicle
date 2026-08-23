import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchRunRegistry } from "./registry";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchRunRegistry", () => {
  it("reports 'missing' on a 404, not an error (schema §6: no run has been written yet)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));
    const result = await fetchRunRegistry();
    expect(result).toEqual({ status: "missing", entries: [], rejected: [] });
  });

  it("loads every well-formed entry", async () => {
    const body = {
      schema_version: 1,
      runs: [
        {
          run_id: "run-a",
          seed_id: "seed-a",
          created_wall_ts: 1,
          branches: [{ save_uuid: "s0", generation: 0 }],
          tick_range: { start: 0, end: 10 },
          streams: { events: "events.jsonl", trace: "trace.jsonl" },
          status: "complete",
        },
      ],
    };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })));
    const result = await fetchRunRegistry();
    expect(result.status).toBe("loaded");
    expect(result.entries).toHaveLength(1);
    expect(result.entries[0]?.run_id).toBe("run-a");
    expect(result.rejected).toHaveLength(0);
  });

  it("skips a malformed entry (missing run_id) without dropping the well-formed ones (schema §7 applied at the registry level)", async () => {
    const body = {
      schema_version: 1,
      runs: [
        { seed_id: "no-run-id", streams: { events: "events.jsonl" } },
        {
          run_id: "run-b",
          seed_id: "seed-b",
          streams: { events: "events.jsonl", trace: "trace.jsonl" },
        },
      ],
    };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })));
    const result = await fetchRunRegistry();
    expect(result.entries.map((e) => e.run_id)).toEqual(["run-b"]);
    expect(result.rejected).toHaveLength(1);
  });

  it("degrades a malformed top-level file (runs is not an array) to an empty, non-error list", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ runs: "oops" }), { status: 200 })));
    const result = await fetchRunRegistry();
    expect(result.status).toBe("loaded");
    expect(result.entries).toEqual([]);
  });

  it("reports a non-404 failure as 'error'", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 500 })));
    const result = await fetchRunRegistry();
    expect(result.status).toBe("error");
    expect(result.error).toContain("500");
  });

  describe("the mock-t0 fixture registration (independent of the real registry's contents)", () => {
    const mockEntry = {
      run_id: "mock-t0",
      seed_id: "mock-t0",
      created_wall_ts: 0,
      branches: [],
      tick_range: { start: 0, end: 96 },
      streams: { events: "events.jsonl", trace: "trace.jsonl" },
      status: "complete",
    };

    function stubTwoEndpoints(realRegistryResponse: Response) {
      vi.stubGlobal(
        "fetch",
        vi.fn(async (url: string) =>
          url.includes("mock-fixtures")
            ? new Response(JSON.stringify(mockEntry), { status: 200 })
            : realRegistryResponse,
        ),
      );
    }

    it("is present even when the real runs/index.json is entirely absent (a true fresh checkout)", async () => {
      stubTwoEndpoints(new Response(null, { status: 404 }));
      const result = await fetchRunRegistry();
      expect(result.entries.map((e) => e.run_id)).toEqual(["mock-t0"]);
    });

    it("is still present after a real run has been registered -- it never gets silently shadowed out", async () => {
      stubTwoEndpoints(
        new Response(
          JSON.stringify({
            schema_version: 1,
            runs: [{ run_id: "range-check-fixture", seed_id: "range-check", streams: { events: "events.jsonl", trace: "" } }],
          }),
          { status: 200 },
        ),
      );
      const result = await fetchRunRegistry();
      expect(result.entries.map((e) => e.run_id).sort()).toEqual(["mock-t0", "range-check-fixture"]);
    });

    it("does not duplicate itself if the real registry already lists mock-t0", async () => {
      stubTwoEndpoints(
        new Response(JSON.stringify({ schema_version: 1, runs: [mockEntry] }), { status: 200 }),
      );
      const result = await fetchRunRegistry();
      expect(result.entries.filter((e) => e.run_id === "mock-t0")).toHaveLength(1);
    });
  });
});
