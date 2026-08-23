import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useFeedStore } from "./feed";

function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return (
    JSON.stringify({
      schema_version: 1,
      seed_id: "jarl-death-demo",
      save_uuid: "s",
      generation: 0,
      tick,
      stream: "trace",
      seq,
      payload,
    }) + "\n"
  );
}

const rolledAgainst = (tick: number, seq: number) =>
  traceLine(tick, seq, {
    record_type: "encounter_rolled",
    roll_key: {},
    value: 0.5,
    threshold: 0.35,
    outcome: "no_encounter",
    location_id: "dragonsreach",
    npc_a: "irileth",
    npc_b: "proventus",
    encountered: false,
  });

const transmitted = (tick: number, seq: number) =>
  traceLine(tick, seq, {
    record_type: "transmitted",
    claim_id: "claim-jarl-death",
    teller_id: "irileth",
    hearer_id: "proventus",
    evidence_id: "e1",
    variant: { variant_id: "v1", parent_variant_id: null, slots: {}, mutated_slot: null },
    location_id: "dragonsreach",
  });

const nothingSalient = (tick: number, seq: number) =>
  traceLine(tick, seq, {
    record_type: "nothing_salient",
    location_id: "market",
    npc_a: "hulda",
    npc_b: "mikael",
    claim_id: null,
    reason: "neither-informed",
  });

describe("useFeedStore", () => {
  let traceContent: string;
  let tickOffsets: Record<string, number>;

  beforeEach(() => {
    setActivePinia(createPinia());

    const line0 = rolledAgainst(0, 0);
    const line1 = transmitted(1, 1);
    const line2 = nothingSalient(2, 2);
    traceContent = line0 + line1 + line2;
    tickOffsets = {
      "0": 0,
      "1": new TextEncoder().encode(line0).length,
      "2": new TextEncoder().encode(line0 + line1).length,
    };

    const registry = {
      schema_version: 1,
      runs: [
        {
          run_id: "whiterun-jarl-01",
          seed_id: "jarl-death-demo",
          created_wall_ts: 0,
          branches: [{ save_uuid: "s", generation: 0 }],
          tick_range: { start: 0, end: 2 },
          streams: { events: "events.jsonl", trace: "trace.jsonl" },
          status: "complete",
        },
      ],
    };
    const sidecar = {
      schema_version: 1,
      streams: {
        events: { tick_offsets: {} },
        trace: { tick_offsets: tickOffsets },
      },
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.includes("mock-fixtures")) return new Response(null, { status: 404 });
        if (url.endsWith("/runs/index.json")) return new Response(JSON.stringify(registry), { status: 200 });
        if (url.endsWith("/index.json")) return new Response(JSON.stringify(sidecar), { status: 200 });
        if (url.endsWith("trace.jsonl")) {
          const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
          const bytes = new TextEncoder().encode(traceContent);
          const match = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
          let start = 0;
          let end = bytes.length;
          if (match) {
            start = Number(match[1]);
            end = match[2] === "" ? bytes.length : Number(match[2]) + 1;
          }
          end = Math.min(end, bytes.length);
          const text = new TextDecoder().decode(bytes.slice(start, end));
          return new Response(text, {
            status: 206,
            headers: { "Content-Range": `bytes ${start}-${end - 1}/${bytes.length}` },
          });
        }
        return new Response(null, { status: 404 });
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("loads and maps the whole known tick range into rows", async () => {
    const feed = useFeedStore();
    await feed.load("whiterun-jarl-01");
    expect(feed.status).toBe("loaded");
    expect(feed.rows).toHaveLength(3);
    expect(feed.rows.map((r) => r.outcome)).toEqual(["rolled_against", "transmitted", "nothing_salient"]);
  });

  it("errors gracefully for a run id not in the registry", async () => {
    const feed = useFeedStore();
    await feed.load("does-not-exist");
    expect(feed.status).toBe("error");
    expect(feed.error).toContain("does-not-exist");
  });

  it("clears rows and goes idle when loaded with null", async () => {
    const feed = useFeedStore();
    await feed.load("whiterun-jarl-01");
    await feed.load(null);
    expect(feed.status).toBe("idle");
    expect(feed.rows).toHaveLength(0);
  });

  it("applies the filter pipeline via filteredRows", async () => {
    const feed = useFeedStore();
    await feed.load("whiterun-jarl-01");
    feed.setFilters({ outcome: "nothing_salient" });
    expect(feed.filteredRows).toHaveLength(1);
    expect(feed.filteredRows[0].participants).toEqual(["hulda", "mikael"]);
  });

  it("LIVE tail: appends a newly written trace row picked up on the next poll", async () => {
    vi.useFakeTimers();
    const feed = useFeedStore();
    await feed.load("whiterun-jarl-01");
    expect(feed.rows).toHaveLength(3);

    traceContent += transmitted(3, 3);

    await vi.advanceTimersByTimeAsync(1000);
    expect(feed.rows).toHaveLength(4);
    expect(feed.rows[3].tick).toBe(3);
  });
});
