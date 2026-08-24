import { describe, expect, it } from "vitest";
import { computeScheduleDiff, extractOverlays, filterScheduleDiffs, type NpcScheduleDiff } from "./scheduleDiff";
import type { FrameRecord, KeyframeScheduleBlock } from "../log/types";

function block(npcId: string, locationId: string, startTick: number, endTick: number): KeyframeScheduleBlock {
  return { npc_id: npcId, location_id: locationId, start_tick: startTick, end_tick: endTick };
}

function rewriteRecord(
  tick: number,
  seq: number,
  npcId: string,
  locationId: string,
  startTick: number,
  endTick: number,
  rule = "schedule-write-back",
  cause = "mourning",
): FrameRecord {
  return {
    schema_version: 1,
    seed_id: "s",
    save_uuid: "save-1",
    generation: 0,
    tick,
    stream: "events",
    seq,
    payload: {
      event_type: "schedule_rewrite",
      gamets: tick,
      wall_ts: 0,
      origin: null,
      npc_id: npcId,
      location_id: locationId,
      start_tick: startTick,
      end_tick: endTick,
      cause,
      rule,
      trigger_event_key: { save_uuid: "save-1", generation: 0, seq: seq - 1 },
    },
  };
}

describe("extractOverlays", () => {
  it("pulls schedule_rewrite records out of a mixed events stream, skipping other event types", () => {
    const npcDied: FrameRecord = {
      schema_version: 1,
      seed_id: "s",
      save_uuid: "save-1",
      generation: 0,
      tick: 0,
      stream: "events",
      seq: 1,
      payload: { event_type: "npc_died", gamets: 0, wall_ts: 0, origin: null, npc_id: "priest" },
    };
    const rewrite = rewriteRecord(0, 2, "sven", "temple_of_kynareth", 0, 72);
    const overlays = extractOverlays([npcDied, rewrite]);
    expect(overlays).toHaveLength(1);
    expect(overlays[0]).toMatchObject({ npc_id: "sven", location_id: "temple_of_kynareth", cause: "mourning" });
  });
});

describe("computeScheduleDiff", () => {
  const base = [
    block("sven", "sven_house", 0, 144),
    block("erik", "sven_house", 0, 144),
    block("priest", "temple_of_kynareth", 0, 144),
  ];

  function bySvenAt(diffs: NpcScheduleDiff[]): NpcScheduleDiff {
    return diffs.find((d) => d.npcId === "sven")!;
  }

  it("with no overlays, before === after for every NPC, nothing inserted or removed", () => {
    const diffs = computeScheduleDiff(base, [], 10);
    expect(diffs).toHaveLength(3);
    for (const d of diffs) {
      expect(d.overridden).toBe(false);
      expect(d.inserted).toEqual([]);
      expect(d.removed).toEqual([]);
      expect(d.after).toEqual(d.before);
    }
  });

  it("an active overlay replaces the NPC's before block entirely in after (total override)", () => {
    const events = [rewriteRecord(0, 2, "sven", "temple_of_kynareth", 0, 72)];
    const diffs = computeScheduleDiff(base, events, 10);
    const sven = bySvenAt(diffs);
    expect(sven.overridden).toBe(true);
    expect(sven.before).toEqual([{ npcId: "sven", locationId: "sven_house", startTick: 0, endTick: 144 }]);
    expect(sven.after).toEqual([
      {
        npcId: "sven",
        locationId: "temple_of_kynareth",
        startTick: 0,
        endTick: 72,
        cause: "mourning",
        rule: "schedule-write-back",
        triggerEventKey: { save_uuid: "save-1", generation: 0, seq: 1 },
        recordTick: 0,
      },
    ]);
    expect(sven.removed).toEqual(sven.before);
    expect(sven.inserted).toEqual(sven.after);

    // Uninvolved NPCs are untouched.
    const erik = diffs.find((d) => d.npcId === "erik")!;
    expect(erik.overridden).toBe(false);
    expect(erik.after).toEqual(erik.before);
  });

  it("carries the causal link (trigger_event_key, rule) on the inserted block", () => {
    const events = [rewriteRecord(3, 5, "sven", "temple_of_kynareth", 3, 20, "grief-response", "bereavement")];
    const diffs = computeScheduleDiff(base, events, 10);
    const sven = bySvenAt(diffs);
    expect(sven.inserted[0]).toMatchObject({
      rule: "grief-response",
      cause: "bereavement",
      triggerEventKey: { save_uuid: "save-1", generation: 0, seq: 4 },
    });
  });

  it("automatic restoration past end_tick: after == before once the overlay expires", () => {
    const events = [rewriteRecord(0, 2, "sven", "temple_of_kynareth", 0, 72)];
    const active = computeScheduleDiff(base, events, 71);
    expect(bySvenAt(active).overridden).toBe(true);

    const restored = computeScheduleDiff(base, events, 72);
    const sven = bySvenAt(restored);
    expect(sven.overridden).toBe(false);
    expect(sven.after).toEqual(sven.before);
    expect(sven.inserted).toEqual([]);
    expect(sven.removed).toEqual([]);
  });

  it("older-run tolerance: empty base schedule and no schedule_rewrite events produce an empty, non-throwing result", () => {
    expect(computeScheduleDiff([], [], 10)).toEqual([]);
  });

  it("an explicit npcIds list restricts (and can include NPCs with no schedule at all)", () => {
    const diffs = computeScheduleDiff(base, [], 10, ["sven", "ghost"]);
    expect(diffs.map((d) => d.npcId)).toEqual(["sven", "ghost"]);
    const ghost = diffs.find((d) => d.npcId === "ghost")!;
    expect(ghost.before).toEqual([]);
    expect(ghost.after).toEqual([]);
  });
});

describe("filterScheduleDiffs", () => {
  it("filters to one NPC when an npc filter is set, passes through unfiltered otherwise", () => {
    const diffs = computeScheduleDiff(
      [block("sven", "sven_house", 0, 144), block("erik", "sven_house", 0, 144)],
      [],
      10,
    );
    expect(filterScheduleDiffs(diffs, {})).toHaveLength(2);
    expect(filterScheduleDiffs(diffs, { npc: "sven" }).map((d) => d.npcId)).toEqual(["sven"]);
  });
});
