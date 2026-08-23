import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useMapDataStore } from "./mapData";

function line(record: Record<string, unknown>): string {
  return JSON.stringify(record) + "\n";
}

function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return line({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "events", seq, payload });
}

function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return line({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload });
}

const KEYFRAME_STATE = {
  claims: [
    {
      id: "c1",
      kind: "npc_death",
      slots: {},
      canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
      truth_status: "unconfirmed",
    },
  ],
  variants: [],
  beliefs: [{ id: "b1", holder_id: "irileth", claim_id: "c1", variant_id: null, confidence: 0.9, verbatim_strength: 1, gist_strength: 1, first_learned: 0, last_rehearsed: 0 }],
  evidence: [],
  rumor_states: [{ npc_id: "irileth", claim_id: "c1", variant_id: null, stage: "heard", first_heard: 0, last_heard: 0, last_told: null, exposure_count: 1, distinct_source_count: 1 }],
};

describe("useMapDataStore", () => {
  let eventsContent: string;
  let traceContent: string;
  let eventTickOffsets: Record<string, number>;
  let traceTickOffsets: Record<string, number>;

  beforeEach(() => {
    setActivePinia(createPinia());

    const kfLine = eventLine(0, 0, { record_type: "keyframe", state: KEYFRAME_STATE });
    eventsContent = kfLine;
    eventTickOffsets = { "0": 0 };

    const t0 = traceLine(0, 0, { record_type: "encounter_rolled", npc_a: "irileth", npc_b: "proventus", location_id: "dragonsreach" });
    const t1 = traceLine(1, 1, { record_type: "relationship_formed", from_id: "irileth", to_id: "jarl_balgruuf" });
    traceContent = t0 + t1;
    traceTickOffsets = { "0": 0, "1": new TextEncoder().encode(t0).length };

    const registry = {
      schema_version: 1,
      runs: [
        {
          run_id: "whiterun-jarl-01",
          seed_id: "jarl-death-demo",
          created_wall_ts: 0,
          branches: [{ save_uuid: "s", generation: 0 }],
          tick_range: { start: 0, end: 1 },
          streams: { events: "events.jsonl", trace: "trace.jsonl" },
          status: "complete",
        },
      ],
    };
    const sidecar = {
      schema_version: 1,
      streams: {
        events: { tick_offsets: eventTickOffsets, keyframe_offsets: [{ tick: 0, offset: 0 }] },
        trace: { tick_offsets: traceTickOffsets },
      },
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.includes("mock-fixtures")) return new Response(null, { status: 404 });
        if (url.endsWith("/runs/index.json")) return new Response(JSON.stringify(registry), { status: 200 });
        if (url.endsWith("/index.json")) return new Response(JSON.stringify(sidecar), { status: 200 });
        if (url.endsWith("events.jsonl") || url.endsWith("trace.jsonl")) {
          const content = url.endsWith("events.jsonl") ? eventsContent : traceContent;
          const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
          const bytes = new TextEncoder().encode(content);
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

  it("loads the full trace/events streams and exposes them", async () => {
    const store = useMapDataStore();
    await store.load("whiterun-jarl-01");
    expect(store.status).toBe("loaded");
    expect(store.traceRecords).toHaveLength(2);
    expect(store.eventRecords).toHaveLength(0); // the only events-stream record is the keyframe, filtered out
  });

  it("setTick reconstructs SocialState at exactly T and stops the tail", async () => {
    const store = useMapDataStore();
    await store.load("whiterun-jarl-01");
    await store.setTick(0);
    expect(store.docked).toBe(false);
    expect(store.socialState.beliefs.get("b1")?.holder_id).toBe("irileth");
  });

  it("dockToLatest reconstructs at the newest known tick and starts tailing", async () => {
    const store = useMapDataStore();
    await store.load("whiterun-jarl-01");
    await store.dockToLatest();
    expect(store.docked).toBe(true);
    expect(store.socialState.beliefs.get("b1")).toBeDefined();
  });

  it("while docked, a new tail record is folded into traceRecords and re-runs the reconstruction", async () => {
    vi.useFakeTimers();
    const store = useMapDataStore();
    await store.load("whiterun-jarl-01");
    await store.dockToLatest();
    expect(store.traceRecords).toHaveLength(2);
    expect(store.socialState.beliefs.size).toBe(1); // just b1, from the keyframe

    // A transmitted record, not just any trace row: this actually changes
    // SocialState (a new belief for proventus), so the assertion below
    // fails if the docked re-fold were a no-op that only grew
    // traceRecords without re-running stateAtLatestKnown().
    traceContent += traceLine(2, 2, {
      record_type: "transmitted",
      claim_id: "c1",
      teller_id: "irileth",
      teller_belief_id: "b1",
      hearer_id: "proventus",
      hearer_belief_id: "b2",
      evidence_id: "e1",
      variant: { variant_id: "v1", parent_variant_id: null, slots: {}, mutated_slot: null },
      location_id: "dragonsreach",
    });

    await vi.advanceTimersByTimeAsync(1000);
    expect(store.traceRecords).toHaveLength(3);
    expect(store.socialState.beliefs.size).toBe(2);
    expect(store.socialState.beliefs.get("b2")?.holder_id).toBe("proventus");
  });

  it("errors gracefully for a run id not in the registry", async () => {
    const store = useMapDataStore();
    await store.load("does-not-exist");
    expect(store.status).toBe("error");
    expect(store.error).toContain("does-not-exist");
  });

  it("clears state and goes idle when loaded with null", async () => {
    const store = useMapDataStore();
    await store.load("whiterun-jarl-01");
    await store.load(null);
    expect(store.status).toBe("idle");
    expect(store.traceRecords).toHaveLength(0);
  });
});
