import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { ref, nextTick } from "vue";
import { useFrameLogStore } from "./frameLog";
import { useLiveDockStore } from "./liveDock";

const FIXTURE_DIR = path.resolve(process.cwd(), "public/runs/mock-t0");
const REGISTRY_ENTRY_PATH = path.resolve(
  process.cwd(),
  "public/mock-fixtures/mock-t0.registry-entry.json",
);

/** Serves the committed mock-t0 fixture (+ its registry entry) with real Range semantics, and lets a test append to the growing files (LIVE tailing). */
function stubMockT0Fetch() {
  const files: Record<string, Buffer> = {
    "/runs/mock-t0/events.jsonl": readFileSync(path.join(FIXTURE_DIR, "events.jsonl")),
    "/runs/mock-t0/trace.jsonl": readFileSync(path.join(FIXTURE_DIR, "trace.jsonl")),
    "/runs/mock-t0/index.json": readFileSync(path.join(FIXTURE_DIR, "index.json")),
    "/mock-fixtures/mock-t0.registry-entry.json": readFileSync(REGISTRY_ENTRY_PATH),
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const pathname = new URL(url, "http://example").pathname;
      if (pathname === "/runs/index.json") return new Response(null, { status: 404 });
      const bytes = files[pathname];
      if (bytes === undefined) return new Response(null, { status: 404 });

      const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range;
      if (!rangeHeader) return new Response(new TextDecoder().decode(bytes), { status: 200 });

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
  return {
    appendTrace(more: string) {
      files["/runs/mock-t0/trace.jsonl"] = Buffer.concat([
        files["/runs/mock-t0/trace.jsonl"]!,
        Buffer.from(more),
      ]);
    },
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

beforeEach(() => {
  setActivePinia(createPinia());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("frameLog store, bound to urlState.run/urlState.t", () => {
  it("moving t reconstructs state at that tick (stepper -> keyframe+delta reconstruction)", async () => {
    stubMockT0Fetch();
    const run = ref<string | null>(null);
    const t = ref<number | null>(96);
    const frameLog = useFrameLogStore();
    frameLog.bindToUrlState(run, t);

    run.value = "mock-t0";
    await nextTick();
    await vi.waitFor(() => expect(frameLog.stateTick).toBe(96));

    expect(frameLog.claimCount).toBeGreaterThan(0);
    expect(frameLog.beliefCount).toBeGreaterThan(0); // includes bel-3 from the post-keyframe transmitted delta
  });

  it(
    "leaving t at null docks to LIVE and starts tailing -- an appended record surfaces within the poll cadence",
    async () => {
      const files = stubMockT0Fetch();
      const run = ref<string | null>("mock-t0");
      const t = ref<number | null>(null);
      const frameLog = useFrameLogStore();
      const liveDock = useLiveDockStore();
      frameLog.bindToUrlState(run, t);

      await vi.waitFor(() => expect(liveDock.docked).toBe(true));
      await vi.waitFor(() => expect(frameLog.stopLiveTail).not.toBeNull());
      // The initial dock reconstructs "latest known" -- nothing new yet.
      expect(liveDock.newEventCount).toBe(0);

      // The writer appends a new trace record while docked.
      files.appendTrace(
        JSON.stringify({
          schema_version: 1,
          seed_id: "mock-t0",
          save_uuid: "s0",
          generation: 0,
          tick: 100,
          stream: "trace",
          seq: 8,
          payload: { record_type: "nothing_salient", location_id: "loc-farm", npc_a: "npc-farmer", npc_b: "npc-smith", claim_id: null, reason: "neither-informed" },
        }) + "\n",
      );

      // ui-spec §1.3's ~1s LIVE-tailing cadence -- real time, no fake-timer
      // trickery: LiveTailPoller's setInterval and the fetch-stub's promise
      // chain both need to actually run.
      await sleep(1300);
      expect(liveDock.newEventCount).toBeGreaterThan(0);
    },
    5000,
  );

  it("scrubbing away from LIVE detaches the dock and stops tailing", async () => {
    stubMockT0Fetch();
    const run = ref<string | null>("mock-t0");
    const t = ref<number | null>(null);
    const frameLog = useFrameLogStore();
    const liveDock = useLiveDockStore();
    frameLog.bindToUrlState(run, t);
    await vi.waitFor(() => expect(liveDock.docked).toBe(true));
    await vi.waitFor(() => expect(frameLog.stopLiveTail).not.toBeNull());

    t.value = 3;
    await vi.waitFor(() => expect(frameLog.stateTick).toBe(3));
    expect(liveDock.docked).toBe(false);
    expect(frameLog.stopLiveTail).toBeNull();
  });
});
