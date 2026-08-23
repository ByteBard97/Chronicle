import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RunReader } from "./runReader";
import type { RunRegistryEntry } from "./types";

const FIXTURE_DIR = path.resolve(process.cwd(), "public/runs/mock-t0");

const registryEntry: RunRegistryEntry = {
  run_id: "mock-t0",
  seed_id: "mock-t0",
  created_wall_ts: 0,
  branches: [{ save_uuid: "s0", generation: 0 }],
  tick_range: { start: 0, end: 96 },
  streams: { events: "events.jsonl", trace: "trace.jsonl" },
  status: "complete",
};

/** Serves the committed mock-t0 fixture files exactly as serveRuns.ts would, Range included. */
function stubMockT0Fetch() {
  const files: Record<string, Buffer> = {
    "/runs/mock-t0/events.jsonl": readFileSync(path.join(FIXTURE_DIR, "events.jsonl")),
    "/runs/mock-t0/trace.jsonl": readFileSync(path.join(FIXTURE_DIR, "trace.jsonl")),
    "/runs/mock-t0/index.json": readFileSync(path.join(FIXTURE_DIR, "index.json")),
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const pathname = new URL(url, "http://example").pathname;
      const bytes = files[pathname];
      if (bytes === undefined) return new Response(null, { status: 404 });

      const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range;
      if (!rangeHeader) {
        return new Response(new TextDecoder().decode(bytes), { status: 200 });
      }
      const match = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
      let start = 0;
      let end = bytes.length;
      if (match) {
        start = Number(match[1]);
        end = match[2] === "" ? bytes.length : Number(match[2]) + 1;
      }
      end = Math.min(end, bytes.length);
      const slice = bytes.subarray(start, end);
      return new Response(new TextDecoder().decode(slice), {
        status: 206,
        headers: { "Content-Range": `bytes ${start}-${end - 1}/${bytes.length}` },
      });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RunReader.stateAt, against the committed mock-t0 fixture", () => {
  it("reconstructs pre-keyframe state (T=3) with no keyframe available yet", async () => {
    stubMockT0Fetch();
    const reader = new RunReader(registryEntry);
    const state = await reader.stateAt(3);
    expect(state.beliefs.get("bel-1")?.confidence).toBe(0.97); // post-corroboration (T6)
    expect(state.beliefs.get("bel-2")).toBeDefined();
  });

  it("reconstructs post-keyframe state (T=96) using the tick-24 keyframe's byte offset, not a scan from 0", async () => {
    stubMockT0Fetch();
    const reader = new RunReader(registryEntry);
    const state = await reader.stateAt(96);

    // The keyframe's authored bel-2 (confidence 0.6) is the base, not
    // whatever the pre-keyframe trace (T0-T6) would have derived --
    // proving the keyframe was actually used as the starting point.
    const bel2AtKeyframe = state.beliefs.get("bel-2");
    expect(bel2AtKeyframe?.last_rehearsed).toBeLessThanOrEqual(96);

    const bel3 = state.beliefs.get("bel-3");
    expect(bel3).toBeDefined();
    expect(bel3!.holder_id).toBe("npc-farmer");
    expect(state.variants.get("var-2")?.mutated_slot).toBe("cause");
  });

  it("fetches only a bounded byte range for the keyframe lookup, not the whole file from byte 0", async () => {
    stubMockT0Fetch();
    const reader = new RunReader(registryEntry);
    await reader.stateAt(96);

    const fetchMock = globalThis.fetch as unknown as { mock: { calls: [string, RequestInit | undefined][] } };
    const eventsRangeStarts = fetchMock.mock.calls
      .filter(([url]) => url.includes("events.jsonl"))
      .map(([, init]) => (init?.headers as Record<string, string> | undefined)?.Range);

    // At least one fetch against events.jsonl must start at the keyframe's
    // sidecar-recorded byte offset (970), not 0 -- the whole point of
    // reading the sidecar index before Range-fetching.
    expect(eventsRangeStarts.some((r) => r === "bytes=970-")).toBe(true);
  });
});
