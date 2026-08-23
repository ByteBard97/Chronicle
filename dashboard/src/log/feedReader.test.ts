import { afterEach, describe, expect, it, vi } from "vitest";
import {
  filterFeedRows,
  mapTraceRecordToFeedRow,
  readTicksInRange,
  sortedTicks,
  type FeedRow,
} from "./feedReader";
import type { FrameRecord } from "./types";

function record(tick: number, seq: number, payload: Record<string, unknown>): FrameRecord {
  return {
    schema_version: 1,
    seed_id: "s",
    save_uuid: "sv",
    generation: 0,
    tick,
    stream: "trace",
    seq,
    payload,
  };
}

describe("mapTraceRecordToFeedRow", () => {
  it("maps transmitted", () => {
    const r = record(1, 7, {
      record_type: "transmitted",
      claim_id: "claim-jarl-death",
      teller_id: "irileth",
      hearer_id: "proventus",
      evidence_id: "ev-1",
      variant: { variant_id: "variant-auto-1", parent_variant_id: null, slots: {}, mutated_slot: null },
      location_id: "dragonsreach",
    });
    expect(mapTraceRecordToFeedRow(r)).toEqual({
      tick: 1,
      seq: 7,
      location: "dragonsreach",
      participants: ["irileth", "proventus"],
      outcome: "transmitted",
      claimId: "claim-jarl-death",
      detail: { kind: "transmitted", variantId: "variant-auto-1", mutatedSlot: null },
    });
  });

  it("maps encounter_rolled with encountered:false to a rolled-against row with no claim id", () => {
    const r = record(0, 5, {
      record_type: "encounter_rolled",
      roll_key: { seed_id: "s", purpose: "encounter.co-presence", tick: 0, site: "dragonsreach", participants: ["irileth", "proventus"], draw: 0 },
      value: 0.5234255596324835,
      threshold: 0.35,
      outcome: "no_encounter",
      location_id: "dragonsreach",
      npc_a: "irileth",
      npc_b: "proventus",
      encountered: false,
    });
    expect(mapTraceRecordToFeedRow(r)).toEqual({
      tick: 0,
      seq: 5,
      location: "dragonsreach",
      participants: ["irileth", "proventus"],
      outcome: "rolled_against",
      claimId: null,
      detail: { kind: "rolled_against", value: 0.5234255596324835, threshold: 0.35 },
    });
  });

  it("elides encounter_rolled with encountered:true (not its own outcome row)", () => {
    const r = record(2, 3, {
      record_type: "encounter_rolled",
      roll_key: {},
      value: 0.1,
      threshold: 0.35,
      outcome: "encounter",
      location_id: "dragonsreach",
      npc_a: "irileth",
      npc_b: "proventus",
      encountered: true,
    });
    expect(mapTraceRecordToFeedRow(r)).toBeNull();
  });

  it("maps nothing_salient", () => {
    const r = record(7, 14, {
      record_type: "nothing_salient",
      location_id: "dragonsreach",
      npc_a: "irileth",
      npc_b: "proventus",
      claim_id: "claim-jarl-death",
      reason: "both-informed",
    });
    expect(mapTraceRecordToFeedRow(r)).toEqual({
      tick: 7,
      seq: 14,
      location: "dragonsreach",
      participants: ["irileth", "proventus"],
      outcome: "nothing_salient",
      claimId: "claim-jarl-death",
      detail: { kind: "nothing_salient", reason: "both-informed" },
    });
  });

  it("maps transmission_declined against a synthetic record (schema-reserved, no real records exist)", () => {
    const r = record(100, 1, {
      record_type: "transmission_declined",
      claim_id: "claim-jarl-death",
      teller_id: "irileth",
      hearer_id: "proventus",
      location_id: "dragonsreach",
      rule: "tell-decision.reluctant-source",
      roll_key: null,
    });
    expect(mapTraceRecordToFeedRow(r)).toEqual({
      tick: 100,
      seq: 1,
      location: "dragonsreach",
      participants: ["irileth", "proventus"],
      outcome: "declined",
      claimId: "claim-jarl-death",
      detail: { kind: "declined", rule: "tell-decision.reluctant-source" },
    });
  });

  it("returns null for trace record types outside the feed's four outcome states", () => {
    const r = record(0, 0, {
      record_type: "relationship_formed",
      id: "rel-1",
      from_id: "a",
      to_id: "b",
      basis: "faction",
      basis_id: null,
      strength: 0.5,
      formed_at: 0,
    });
    expect(mapTraceRecordToFeedRow(r)).toBeNull();
  });
});

describe("sortedTicks", () => {
  it("returns numeric keys ascending", () => {
    expect(sortedTicks({ "10": 100, "2": 20, "0": 0 })).toEqual([0, 2, 10]);
  });
});

describe("readTicksInRange", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubRangeServer(content: string) {
    const bytes = new TextEncoder().encode(content);
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
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
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  const line0 = JSON.stringify(record(0, 0, { record_type: "nothing_salient", npc_a: "a", npc_b: "b", location_id: "x", claim_id: null, reason: "neither-informed" }));
  const line1a = JSON.stringify(record(1, 1, { record_type: "nothing_salient", npc_a: "a", npc_b: "b", location_id: "x", claim_id: null, reason: "neither-informed" }));
  const line1b = JSON.stringify(record(1, 2, { record_type: "nothing_salient", npc_a: "a", npc_b: "b", location_id: "x", claim_id: null, reason: "neither-informed" }));
  const line2 = JSON.stringify(record(2, 3, { record_type: "nothing_salient", npc_a: "a", npc_b: "b", location_id: "x", claim_id: null, reason: "neither-informed" }));

  const content = `${line0}\n${line1a}\n${line1b}\n${line2}\n`;
  const offsetOf = (s: string) => new TextEncoder().encode(s).length;
  const tickOffsets = {
    "0": 0,
    "1": offsetOf(line0 + "\n"),
    "2": offsetOf(line0 + "\n" + line1a + "\n" + line1b + "\n"),
  };

  it("reads a single tick's rows using the next tick's offset as the bound", async () => {
    stubRangeServer(content);
    const result = await readTicksInRange("http://x/trace.jsonl", tickOffsets, 1, 1);
    expect(result.records.map((r) => r.seq)).toEqual([1, 2]);
  });

  it("reads a middle range spanning several ticks", async () => {
    stubRangeServer(content);
    const result = await readTicksInRange("http://x/trace.jsonl", tickOffsets, 0, 1);
    expect(result.records.map((r) => r.seq)).toEqual([0, 1, 2]);
  });

  it("edge case: reading the highest known tick omits `end` (reads to EOF) rather than computing a nonexistent next offset", async () => {
    const fetchMock = stubRangeServer(content);
    const result = await readTicksInRange("http://x/trace.jsonl", tickOffsets, 2, 2);
    // The last tick's row (seq 3) must not be silently dropped.
    expect(result.records.map((r) => r.seq)).toEqual([3]);
    const rangeHeader = (fetchMock.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(rangeHeader.Range).toMatch(/^bytes=\d+-$/); // open-ended, no upper bound
  });

  it("returns empty when the requested range has no known ticks", async () => {
    stubRangeServer(content);
    const result = await readTicksInRange("http://x/trace.jsonl", tickOffsets, 50, 60);
    expect(result.records).toEqual([]);
  });
});

describe("filterFeedRows", () => {
  const rows: FeedRow[] = [
    {
      tick: 1,
      seq: 0,
      location: "dragonsreach",
      participants: ["irileth", "proventus"],
      outcome: "transmitted",
      claimId: "claim-jarl-death",
      detail: { kind: "transmitted", variantId: "v1", mutatedSlot: null },
    },
    {
      tick: 0,
      seq: 1,
      location: "dragonsreach",
      participants: ["irileth", "proventus"],
      outcome: "rolled_against",
      claimId: null,
      detail: { kind: "rolled_against", value: 0.5, threshold: 0.35 },
    },
    {
      tick: 7,
      seq: 2,
      location: "market",
      participants: ["hulda", "mikael"],
      outcome: "nothing_salient",
      claimId: "claim-jarl-death",
      detail: { kind: "nothing_salient", reason: "both-informed" },
    },
  ];

  it("filters by NPC", () => {
    expect(filterFeedRows(rows, { npc: "hulda" }).map((r) => r.seq)).toEqual([2]);
  });

  it("filters by location", () => {
    expect(filterFeedRows(rows, { location: "market" }).map((r) => r.seq)).toEqual([2]);
  });

  it("filters by outcome", () => {
    expect(filterFeedRows(rows, { outcome: "rolled_against" }).map((r) => r.seq)).toEqual([1]);
  });

  it("filters by claim, structurally excluding rolled-against rows (no claim id on encounter rolls)", () => {
    const result = filterFeedRows(rows, { claim: "claim-jarl-death" });
    expect(result.map((r) => r.seq)).toEqual([0, 2]);
    expect(result.every((r) => r.outcome !== "rolled_against")).toBe(true);
  });

  it("combines filters", () => {
    expect(filterFeedRows(rows, { npc: "irileth", outcome: "transmitted" }).map((r) => r.seq)).toEqual([0]);
  });

  it("returns everything when no filters are set", () => {
    expect(filterFeedRows(rows, {})).toHaveLength(3);
  });
});
